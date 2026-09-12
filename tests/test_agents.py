"""Tests for the tool-calling research agent."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.agents import (
    TOOLS,
    AgentContext,
    ResearchAgent,
    RuleBasedLLM,
    build_agent,
)
from core.agents.tools import _get_company_data  # noqa: F401 (import check)
from core.models import AgentResponse, ToolCall

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def _agent(**kwargs) -> ResearchAgent:
    return build_agent(provider="local", sample_dir=SAMPLE_DIR, **kwargs)


# --------------------------------------------------------------------------- #
# Tool registry                                                               #
# --------------------------------------------------------------------------- #
def test_at_least_eight_tools_registered():
    assert len(TOOLS) >= 8  # CV target: 8+ typed tool-calls
    names = {t.name for t in TOOLS}
    assert {"get_company_data", "calculate_dcf", "run_monte_carlo", "retrieve_filing_evidence"} <= names


def test_tool_schemas_are_well_formed():
    for tool in TOOLS:
        schema = tool.openai_schema()
        assert schema["type"] == "function"
        fn = schema["function"]
        assert fn["name"] == tool.name
        assert fn["description"]
        assert fn["parameters"]["type"] == "object"


# --------------------------------------------------------------------------- #
# Planning (rule-based)                                                        #
# --------------------------------------------------------------------------- #
def test_plan_always_starts_with_company_data():
    llm = RuleBasedLLM()
    names = {t.name for t in TOOLS}
    plan = llm._plan("what is the dcf value", names)
    assert plan[0] == "get_company_data"
    assert "calculate_dcf" in plan


def test_full_valuation_triggers_comprehensive_plan():
    llm = RuleBasedLLM()
    plan = llm._plan("give me a full valuation", {t.name for t in TOOLS})
    for tool in ["calculate_dcf", "calculate_comps", "calculate_precedent", "reverse_dcf", "run_monte_carlo"]:
        assert tool in plan


def test_competition_does_not_trigger_comps():
    llm = RuleBasedLLM()
    plan = llm._plan("what are the competition risks", {t.name for t in TOOLS})
    assert "calculate_comps" not in plan
    assert "retrieve_filing_evidence" in plan


def test_generic_query_uses_default_plan():
    llm = RuleBasedLLM()
    plan = llm._plan("tell me about this company", {t.name for t in TOOLS})
    assert plan[0] == "get_company_data"
    assert "calculate_dcf" in plan  # default plan includes a valuation


# --------------------------------------------------------------------------- #
# Dispatch & error handling                                                   #
# --------------------------------------------------------------------------- #
def test_execute_unknown_tool_returns_failure():
    agent = _agent()
    result = agent._execute(ToolCall(tool_name="does_not_exist"))
    assert result.ok is False
    assert "Unknown tool" in result.error


def test_execute_handler_error_is_captured():
    # A tool needing a dataset, run against a context with no loadable ticker.
    context = AgentContext(provider="local", sample_dir=SAMPLE_DIR)
    agent = ResearchAgent(context, RuleBasedLLM(), TOOLS)
    result = agent._execute(ToolCall(tool_name="calculate_dcf"))
    assert result.ok is False  # ensure_dataset raises -> captured, not propagated


# --------------------------------------------------------------------------- #
# Context                                                                     #
# --------------------------------------------------------------------------- #
def test_context_reloads_on_ticker_switch():
    ctx = AgentContext(provider="local", sample_dir=SAMPLE_DIR)
    a = ctx.ensure_dataset("AAPL")
    assert a.ticker == "AAPL"
    b = ctx.ensure_dataset("MSFT")
    assert b.ticker == "MSFT"
    assert ctx.ticker == "MSFT"


# --------------------------------------------------------------------------- #
# End-to-end runs                                                             #
# --------------------------------------------------------------------------- #
def test_agent_full_valuation_run():
    agent = _agent()
    resp = agent.run("AAPL", "give me a full valuation")
    assert isinstance(resp, AgentResponse)
    assert resp.answer
    assert "AAPL" in resp.answer or "Apple" in resp.answer
    assert "not investment advice" in resp.answer.lower()
    # every tool call succeeded on valid sample data
    assert all(step.result.ok for step in resp.steps)
    # a full valuation exercises several distinct tools
    assert len(resp.tools_used) >= 5
    assert resp.tools_used[0] == "get_company_data"


def test_agent_dcf_run_uses_expected_tools():
    agent = _agent()
    resp = agent.run("AAPL", "what does the dcf say and what growth is priced in")
    assert "calculate_dcf" in resp.tools_used
    assert "reverse_dcf" in resp.tools_used
    dcf_step = next(s for s in resp.steps if s.call.tool_name == "calculate_dcf")
    assert dcf_step.result.result["implied_share_price"] > 0
    assert dcf_step.result.result["market_price"] == pytest.approx(176.65)


def test_agent_reused_across_tickers():
    agent = _agent()
    aapl = agent.run("AAPL", "full valuation")
    msft = agent.run("MSFT", "full valuation")
    assert "Apple" in aapl.answer
    assert "Microsoft" in msft.answer


def test_agent_filing_evidence_run():
    agent = _agent(index_sample_filing=True)
    resp = agent.run("AAPL", "what are the risk factors")
    assert "retrieve_filing_evidence" in resp.tools_used
    evidence_step = next(s for s in resp.steps if s.call.tool_name == "retrieve_filing_evidence")
    assert evidence_step.result.ok
    assert evidence_step.result.result.get("citations")


def test_build_agent_defaults_to_rule_based():
    agent = _agent()
    assert isinstance(agent.llm, RuleBasedLLM)
