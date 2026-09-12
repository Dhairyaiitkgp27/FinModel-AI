"""Runs the agent-evaluation suite as part of the test suite.

Each case in :data:`evals.cases.CASES` becomes a parametrised test; the suite is
also checked for size (the 50+ target) and category coverage.
"""
from __future__ import annotations

import pytest

from evals import CASES, make_eval_agent, run_eval_case, summarize


@pytest.fixture(scope="module")
def eval_agent():
    return make_eval_agent()


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_eval_case(eval_agent, case):
    result = run_eval_case(eval_agent, case)
    assert result.passed, f"{case.name} failed: {result.failures} | tools_used={result.tools_used}"


def test_suite_has_fifty_plus_cases():
    assert len(CASES) >= 50


def test_category_coverage():
    categories = {c.category for c in CASES}
    required = {
        "overview", "ratios", "dcf", "comps", "precedent", "reverse_dcf",
        "scenarios", "forecast", "sensitivity", "monte_carlo", "filings",
        "comprehensive", "edge",
    }
    assert required <= categories


def test_summarize_reports_pass_rate(eval_agent):
    # Run a small subset and confirm the summary aggregates correctly.
    subset = CASES[:5]
    results = [run_eval_case(eval_agent, c) for c in subset]
    summary = summarize(results)
    assert summary["total"] == 5
    assert 0.0 <= summary["pass_rate"] <= 1.0
    assert "by_category" in summary
