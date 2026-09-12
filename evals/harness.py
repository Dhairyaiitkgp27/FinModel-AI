"""Agent evaluation harness.

Defines a small, declarative :class:`EvalCase` format and a runner that executes
the research agent against each case and checks: that the expected tools were
called (and forbidden ones were not), that every tool call succeeded, that the
answer contains the expected phrases, and that a minimum amount of work was done.

The suite (see :mod:`evals.cases`) is the platform's agent-evaluation set. It runs
against the offline rule-based agent by default — so it is deterministic and
requires no API key — and the same cases validate the OpenAI agent when one is
configured.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.agents import ResearchAgent, build_agent

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


@dataclass(frozen=True)
class EvalCase:
    """One declarative agent-evaluation case."""

    name: str
    ticker: str
    query: str
    category: str
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    answer_contains: tuple[str, ...] = ()
    min_steps: int = 1


@dataclass
class EvalResult:
    """The outcome of running one case."""

    case: EvalCase
    passed: bool
    tools_used: list[str]
    answer: str
    failures: list[str] = field(default_factory=list)


def make_eval_agent(**kwargs) -> ResearchAgent:
    """Build the agent used for evaluation (offline, with the sample filing indexed)."""
    return build_agent(
        provider="local", sample_dir=SAMPLE_DIR, index_sample_filing=True, **kwargs
    )


def run_eval_case(agent: ResearchAgent, case: EvalCase) -> EvalResult:
    """Run a single case and collect any assertion failures."""
    response = agent.run(case.ticker, case.query)
    tools_used = response.tools_used
    failures: list[str] = []

    for tool in case.expected_tools:
        if tool not in tools_used:
            failures.append(f"expected tool '{tool}' was not called")
    for tool in case.forbidden_tools:
        if tool in tools_used:
            failures.append(f"forbidden tool '{tool}' was called")

    answer_lower = response.answer.lower()
    for phrase in case.answer_contains:
        if phrase.lower() not in answer_lower:
            failures.append(f"answer missing phrase '{phrase}'")

    if len(response.steps) < case.min_steps:
        failures.append(f"only {len(response.steps)} steps (< {case.min_steps})")

    for step in response.steps:
        if not step.result.ok:
            failures.append(f"tool '{step.call.tool_name}' errored: {step.result.error}")

    return EvalResult(
        case=case,
        passed=not failures,
        tools_used=tools_used,
        answer=response.answer,
        failures=failures,
    )


def run_suite(
    cases: list[EvalCase], agent: ResearchAgent | None = None
) -> list[EvalResult]:
    """Run every case, reusing a single agent."""
    agent = agent or make_eval_agent()
    return [run_eval_case(agent, case) for case in cases]


def summarize(results: list[EvalResult]) -> dict:
    """Aggregate pass rate overall and by category."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        stats = by_category.setdefault(r.case.category, {"passed": 0, "total": 0})
        stats["total"] += 1
        stats["passed"] += int(r.passed)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "by_category": by_category,
    }
