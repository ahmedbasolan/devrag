"""Unit tests for the regression check in eval_external."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_external import regressions


def _report(ranks: list[int | None]) -> dict:
    n = len(ranks)
    return {
        "hit_rate_at_5": sum(1 for r in ranks if r and r <= 5) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
        "results": [{"query": f"q{i}", "rank": r} for i, r in enumerate(ranks)],
    }


BASELINE = _report([1, 2, 3, 6])


def test_same_scores_pass():
    assert regressions(_report([1, 2, 3, 6]), BASELINE, 0.02) == []


def test_better_scores_pass():
    assert regressions(_report([1, 1, 1, 1]), BASELINE, 0.02) == []


def test_question_leaving_top_5_fails_and_is_named():
    problems = regressions(_report([1, 2, 7, 6]), BASELINE, 0.02)
    assert problems[0].startswith("Hit@5")
    assert any("rank 3 -> 7: q2" in p for p in problems)


def test_mrr_drop_beyond_tolerance_fails():
    problems = regressions(_report([2, 2, 3, 6]), BASELINE, 0.02)
    assert len(problems) == 2
    assert problems[0].startswith("MRR")
    assert "rank 1 -> 2: q0" in problems[1]


def test_small_mrr_drop_within_tolerance_passes():
    # 3rd -> 4th costs 1/3 - 1/4 = 0.083 over 4 questions, about 0.021
    assert regressions(_report([1, 2, 4, 6]), BASELINE, 0.025) == []


def test_question_dropping_out_entirely_is_named():
    problems = regressions(_report([1, 2, 3, None]), BASELINE, 0.02)
    assert any("rank 6 -> None: q3" in p for p in problems)
