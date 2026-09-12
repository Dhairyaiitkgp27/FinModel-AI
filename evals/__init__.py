"""FinModel AI agent-evaluation suite."""
from __future__ import annotations

from evals.cases import CASES
from evals.harness import (
    EvalCase,
    EvalResult,
    make_eval_agent,
    run_eval_case,
    run_suite,
    summarize,
)

__all__ = [
    "CASES",
    "EvalCase",
    "EvalResult",
    "make_eval_agent",
    "run_eval_case",
    "run_suite",
    "summarize",
]
