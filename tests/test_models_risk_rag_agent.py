"""Tests for risk, RAG, and agent models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import (
    AgentResponse,
    AgentStep,
    DocumentChunk,
    RAGAnswer,
    RetrievedChunk,
    RiskAnalysis,
    RiskFlag,
    Severity,
    ToolCall,
    ToolResult,
)


# --------------------------------------------------------------------------- #
# Risk                                                                        #
# --------------------------------------------------------------------------- #
def test_risk_analysis_by_severity():
    analysis = RiskAnalysis(
        ticker="TEST",
        flags=[
            RiskFlag(category="leverage", severity=Severity.HIGH, metric="net_debt_to_ebitda",
                     value=5.2, threshold=4.0, message="Elevated leverage"),
            RiskFlag(category="liquidity", severity=Severity.LOW, metric="current_ratio",
                     value=2.1, threshold=1.0, message="Comfortable liquidity"),
        ],
        overall_score=55.0,
    )
    assert analysis.high_severity_count == 1
    assert len(analysis.by_severity(Severity.LOW)) == 1


def test_risk_score_range_enforced():
    with pytest.raises(ValidationError):
        RiskAnalysis(ticker="TEST", overall_score=150.0)


# --------------------------------------------------------------------------- #
# RAG                                                                         #
# --------------------------------------------------------------------------- #
def test_document_chunk_citation_with_page():
    chunk = DocumentChunk(
        doc_id="d1", document_name="AAPL 10-K 2023", text="Revenue grew...", page_number=42
    )
    assert chunk.citation() == "AAPL 10-K 2023, p.42"


def test_document_chunk_citation_without_page():
    chunk = DocumentChunk(doc_id="d1", document_name="AAPL 10-K", text="...")
    assert chunk.citation() == "AAPL 10-K"


def test_rag_answer_citations():
    answer = RAGAnswer(
        question="Why did margins fall?",
        answer="Because of higher input costs.",
        sources=[
            RetrievedChunk(
                chunk=DocumentChunk(doc_id="d1", document_name="10-K", text="...", page_number=10),
                score=0.88,
            )
        ],
    )
    assert answer.citations == ["10-K, p.10"]


# --------------------------------------------------------------------------- #
# Agent                                                                       #
# --------------------------------------------------------------------------- #
def test_tool_result_helpers():
    ok = ToolResult.success("calculate_dcf", {"price": 100})
    err = ToolResult.failure("calculate_dcf", "bad inputs")
    assert ok.ok is True and ok.result == {"price": 100}
    assert err.ok is False and err.error == "bad inputs"


def test_agent_response_tools_used_deduped_in_order():
    resp = AgentResponse(
        query="Analyze NVDA",
        answer="...",
        steps=[
            AgentStep(call=ToolCall(tool_name="get_company_data"), result=ToolResult(tool_name="get_company_data")),
            AgentStep(call=ToolCall(tool_name="calculate_dcf"), result=ToolResult(tool_name="calculate_dcf")),
            AgentStep(call=ToolCall(tool_name="get_company_data"), result=ToolResult(tool_name="get_company_data")),
        ],
    )
    assert resp.tools_used == ["get_company_data", "calculate_dcf"]


def test_tool_call_default_arguments():
    call = ToolCall(tool_name="run_monte_carlo")
    assert call.arguments == {}
