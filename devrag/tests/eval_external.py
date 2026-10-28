"""Retrieval quality on codebases DevRAG was not developed against.

The built-in suite (eval_rag.py) indexes DevRAG's own source and its mock
data, so a high score there says little about "ask questions about any
codebase". This scores the same retriever on other repositories, pinned to a
commit, with each question's answer file chosen from the code by hand.

The corpus is built exactly as the app builds it for a user's folder
(ingest_directory defaults: Python and Markdown, tests left out). A question
counts as a hit only when one of its expected *source* files is in the top-k;
a README or doc ranking first is a miss, because the README promises answers
about the code.

  python tests/eval_external.py tests/external/motor_claims_triage.json --repo-path ../motor-claims-triage

The repo must be checked out at the pinned commit; the script refuses
otherwise, since a moved file would score as a miss.

Sets carry a "split": "dev" was used while developing retrieval changes, so its
score is optimistic; "held-out" was written before a change and run once after.

With --baseline (CI passes each set's committed .results.json), the run fails
when Hit@5 falls below the baseline or MRR falls more than --mrr-tolerance
below it, and lists the questions that ranked worse. A change that improves
the scores should commit the new results with --out, so the floor moves up.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.parser import ingest_directory  # noqa: E402
from src.retriever import HybridRetriever  # noqa: E402


def head_commit(repo_path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def score(eval_set: dict, repo_path: Path, top_k: int = 10) -> dict:
    root = repo_path.resolve()
    chunks = ingest_directory(str(root))
    retriever = HybridRetriever(chroma_dir=tempfile.mkdtemp())
    retriever.index_chunks(chunks)

    results = []
    for q in eval_set["queries"]:
        ranked = retriever.search_rrf(q["query"], top_k=top_k)
        files = [Path(r.chunk.source_file).resolve().relative_to(root).as_posix() for r in ranked]
        rank = next((i + 1 for i, f in enumerate(files) if f in q["expected_files"]), None)
        results.append(
            {
                "query": q["query"],
                "expected_files": q["expected_files"],
                "rank": rank,
                "top_files": files[:5],
            }
        )

    n = len(results)
    return {
        "split": eval_set["split"],
        "repo": eval_set["repo"],
        "commit": eval_set["commit"],
        "chunks": len(chunks),
        "hit_rate_at_5": sum(1 for r in results if r["rank"] and r["rank"] <= 5) / n,
        "hit_rate_at_10": sum(1 for r in results if r["rank"]) / n,
        "mrr": sum(1 / r["rank"] for r in results if r["rank"]) / n,
        "total_queries": n,
        "results": results,
    }


def regressions(report: dict, baseline: dict, mrr_tolerance: float) -> list[str]:
    """What got worse than the baseline run; empty when the scores held."""
    problems = []
    if report["hit_rate_at_5"] < baseline["hit_rate_at_5"] - 1e-9:
        problems.append(
            f"Hit@5 {report['hit_rate_at_5']:.2f} is below the baseline {baseline['hit_rate_at_5']:.2f}"
        )
    if report["mrr"] < baseline["mrr"] - mrr_tolerance:
        problems.append(
            f"MRR {report['mrr']:.3f} is more than {mrr_tolerance} below the baseline {baseline['mrr']:.3f}"
        )
    if problems:
        before = {r["query"]: r["rank"] for r in baseline["results"]}
        for r in report["results"]:
            old = before.get(r["query"])
            if old and (r["rank"] is None or r["rank"] > old):
                problems.append(f"  rank {old} -> {r['rank']}: {r['query']}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("eval_set", type=Path)
    parser.add_argument("--repo-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None, help="write results JSON here")
    parser.add_argument(
        "--baseline", type=Path, default=None, help="fail if worse than this results JSON"
    )
    parser.add_argument("--mrr-tolerance", type=float, default=0.02)
    args = parser.parse_args()

    eval_set = json.loads(args.eval_set.read_text(encoding="utf-8"))
    commit = head_commit(args.repo_path)
    if not commit.startswith(eval_set["commit"]):
        print(
            f"{args.repo_path} is at {commit[:7]}; this set is pinned to {eval_set['commit']}. "
            f"Run: git -C {args.repo_path} checkout {eval_set['commit']}"
        )
        return 2

    report = score(eval_set, args.repo_path)
    for r in report["results"]:
        mark = "HIT " if r["rank"] and r["rank"] <= 5 else "MISS"
        print(f"{mark} rank={r['rank']}  {r['query']}\n      top: {r['top_files'][:3]}")
    print(
        f"\n[{report['split']}] {Path(report['repo']).name}@{report['commit']}: "
        f"Hit@5 {report['hit_rate_at_5']:.2f}  Hit@10 {report['hit_rate_at_10']:.2f}  "
        f"MRR {report['mrr']:.2f}  (n={report['total_queries']}, {report['chunks']} chunks)"
    )
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        problems = regressions(report, baseline, args.mrr_tolerance)
        if problems:
            print("\nRetrieval got worse than " + args.baseline.as_posix() + ":")
            print("\n".join(problems))
            return 1
        print(f"Held against {args.baseline.as_posix()}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
