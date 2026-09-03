"""
FDE Quality & Evaluation module.

Evaluates retrieval accuracy using Hit Rate @ k and MRR
against sample codebase queries.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import ingest_directory
from src.retriever import HybridRetriever


@dataclass
class EvalQuery:
    query: str
    expected_files: List[str]
    expected_names: List[str] = field(default_factory=list)


@dataclass
class EvalResult:
    query: str
    hit_at_5: bool
    hit_at_10: bool
    mrr: float
    top_results: List[dict]


SAMPLE_QUERIES = [
    # ── Original 5 ──────────────────────────────────────────
    EvalQuery(
        query="How do I parse Python AST and extract functions?",
        expected_files=["src/parser.py"],
        expected_names=["parse_python_file", "_parse_function"],
    ),
    EvalQuery(
        query="How does the hybrid retrieval work with BM25 and vector search?",
        expected_files=["src/retriever.py"],
        expected_names=["HybridRetriever", "search_rrf"],
    ),
    EvalQuery(
        query="How to build a Streamlit UI with search and citations?",
        expected_files=["src/app.py"],
        expected_names=["main", "generate_response"],
    ),
    EvalQuery(
        query="How are markdown files chunked and parsed?",
        expected_files=["src/parser.py"],
        expected_names=["parse_markdown_file", "_split_long_section"],
    ),
    EvalQuery(
        query="How are code chunks indexed into ChromaDB?",
        expected_files=["src/retriever.py"],
        expected_names=["_index_chroma", "index_chunks"],
    ),
    # ── Functional (specific functions/classes) ─────────────
    EvalQuery(
        query="How does user authentication work with JWT tokens?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["login", "register", "User"],
    ),
    EvalQuery(
        query="How does the payment processing service handle transactions?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["PaymentService", "process_payment"],
    ),
    EvalQuery(
        query="How does the Redis cache manager handle invalidation?",
        expected_files=["mock_data/src/cache.py"],
        expected_names=["CacheManager", "invalidate_user", "invalidate_product"],
    ),
    EvalQuery(
        query="How are database migrations created and applied?",
        expected_files=["mock_data/src/db_migration.py"],
        expected_names=["MigrationManager", "create_migration", "migrate_up"],
    ),
    EvalQuery(
        query="How does the rate limiting decorator prevent abuse?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["rate_limit", "rate_limit_store"],
    ),
    EvalQuery(
        query="How are customer orders created from cart items?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["create_order", "Order", "OrderItem"],
    ),
    EvalQuery(
        query="How does the product search endpoint filter results?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["search_products"],
    ),
    EvalQuery(
        query="How does the notification service send emails?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["NotificationService", "send_order_confirmation"],
    ),
    EvalQuery(
        query="How does the admin dashboard aggregate store statistics?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["admin_stats"],
    ),
    EvalQuery(
        query="How does the cache warming pre-populate frequently accessed data?",
        expected_files=["mock_data/src/cache.py"],
        expected_names=["CacheWarmer", "warm_products"],
    ),
    # ── Cross-file / conceptual ─────────────────────────────
    EvalQuery(
        query="How does authentication flow across the entire application?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["User", "login", "jwt_required"],
    ),
    EvalQuery(
        query="How does a product go from listing to being delivered to a customer?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["Product", "Order", "create_order", "update_order_status"],
    ),
    EvalQuery(
        query="How does the caching layer interact with the database?",
        expected_files=["mock_data/src/cache.py"],
        expected_names=["CacheManager", "get_or_set"],
    ),
    # ── Design decisions ────────────────────────────────────
    EvalQuery(
        query="Why was Flask chosen over Django for this project?",
        expected_files=["mock_data/docs/decisions.md"],
        expected_names=["ADR-001"],
    ),
    EvalQuery(
        query="What is the cache invalidation strategy and why was it chosen?",
        expected_files=["mock_data/docs/decisions.md"],
        expected_names=["ADR-004"],
    ),
    # ── Edge cases ──────────────────────────────────────────
    EvalQuery(
        query="What happens when a product is out of stock during checkout?",
        expected_files=["mock_data/src/app.py"],
        expected_names=["create_order"],
    ),
]


def evaluate_retrieval(
    retriever: HybridRetriever,
    eval_queries: List[EvalQuery],
    top_k: int = 10,
) -> List[EvalResult]:
    """Evaluate retrieval accuracy against expected results."""
    results = []

    for eq in eval_queries:
        search_results = retriever.search_rrf(eq.query, top_k=top_k)

        hit_at_5 = False
        hit_at_10 = False
        mrr = 0.0

        for i, sr in enumerate(search_results):
            is_match = _is_expected_match(sr.chunk, eq)
            if is_match:
                if i < 5:
                    hit_at_5 = True
                if i < 10:
                    hit_at_10 = True
                if mrr == 0.0:
                    mrr = 1.0 / (i + 1)
                break

        top_result_dicts = [
            {
                "rank": i + 1,
                "file": sr.chunk.source_file,
                "name": sr.chunk.name,
                "type": sr.chunk.chunk_type,
                "score": sr.score,
                "source": sr.source,
            }
            for i, sr in enumerate(search_results[:5])
        ]

        results.append(EvalResult(
            query=eq.query,
            hit_at_5=hit_at_5,
            hit_at_10=hit_at_10,
            mrr=mrr,
            top_results=top_result_dicts,
        ))

    return results


def _is_expected_match(chunk, eq: EvalQuery) -> bool:
    """Check if a chunk matches expected file or name."""
    chunk_file = chunk.source_file.replace("\\", "/")
    for ef in eq.expected_files:
        if ef in chunk_file:
            return True
    for en in eq.expected_names:
        if en == chunk.name:
            return True
    return False


def compute_metrics(results: List[EvalResult]) -> dict:
    """Compute aggregate metrics from evaluation results."""
    n = len(results)
    if n == 0:
        return {}

    return {
        "hit_rate_at_5": sum(r.hit_at_5 for r in results) / n,
        "hit_rate_at_10": sum(r.hit_at_10 for r in results) / n,
        "mrr": sum(r.mrr for r in results) / n,
        "total_queries": n,
    }


def run_evaluation(repo_path: str = None) -> dict:
    """Run full evaluation and return metrics."""
    if repo_path is None:
        repo_path = str(Path(__file__).parent.parent)

    print(f"=== DevRAG - RAG Evaluation ===\n")
    print(f"Indexing: {repo_path}")

    chunks = ingest_directory(repo_path)
    print(f"Indexed {len(chunks)} chunks\n")

    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    print("Running evaluation queries...\n")
    results = evaluate_retrieval(retriever, SAMPLE_QUERIES, top_k=10)

    metrics = compute_metrics(results)

    print(f"{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}\n")

    for er in results:
        status_5 = "HIT" if er.hit_at_5 else "MISS"
        status_10 = "HIT" if er.hit_at_10 else "MISS"
        print(f"Query: {er.query}")
        print(f"  Hit@5: {status_5} | Hit@10: {status_10} | MRR: {er.mrr:.3f}")
        if er.top_results:
            top = er.top_results[0]
            print(f"  Top-1: {top['file']} > {top['name']} ({top['type']})")
        print()

    print(f"{'='*60}")
    print(f"AGGREGATE METRICS")
    print(f"{'='*60}")
    print(f"  Hit Rate @5:  {metrics['hit_rate_at_5']:.1%}")
    print(f"  Hit Rate @10: {metrics['hit_rate_at_10']:.1%}")
    print(f"  MRR:          {metrics['mrr']:.3f}")
    print(f"  Queries:      {metrics['total_queries']}")
    print(f"{'='*60}\n")

    output_file = os.path.join(repo_path, "tests", "eval_results.json")
    with open(output_file, "w") as f:
        json.dump(
            {
                "metrics": metrics,
                "results": [
                    {
                        "query": er.query,
                        "hit_at_5": er.hit_at_5,
                        "hit_at_10": er.hit_at_10,
                        "mrr": er.mrr,
                        "top_results": er.top_results,
                    }
                    for er in results
                ],
            },
            f,
            indent=2,
        )
    print(f"Results saved to {output_file}")

    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality")
    parser.add_argument("--repo-path", type=str, default=None, help="Path to repo")
    args = parser.parse_args()

    run_evaluation(args.repo_path)
