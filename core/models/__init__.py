"""FinModel AI internal data models.

Import everything from here, e.g. ``from core.models import IncomeStatement``.
"""
from __future__ import annotations

from .agent import AgentResponse, AgentStep, ToolCall, ToolResult
from .analysis import PeriodRatios, RatioAnalysis
from .base import (
    Currency,
    FinBaseModel,
    FiscalPeriod,
    PeriodType,
    ScenarioType,
    Severity,
    StatementType,
    ValuationMethod,
)
from .company import CompanyProfile, MarketData
from .financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from .forecast import (
    DriverAssumptions,
    ForecastResult,
    Scenario,
    ScenarioComparison,
    ScenarioLine,
)
from .prices import PriceBar, PriceHistory
from .rag import DocumentChunk, RAGAnswer, RetrievedChunk
from .risk import RiskAnalysis, RiskFlag
from .valuation import (
    AssumptionDistribution,
    CompsResult,
    CompsValuation,
    DCFInputs,
    DCFResult,
    DistributionType,
    DriverSensitivity,
    DriverSensitivityRanking,
    MonteCarloInputs,
    MonteCarloResult,
    MultipleStats,
    PeerCompany,
    PrecedentResult,
    PrecedentTransaction,
    ReverseDCFInputs,
    ReverseDCFResult,
    ReverseDCFTarget,
    SensitivityAxis,
    SensitivityResult,
    WACCInputs,
    WACCResult,
)

__all__ = [
    # base
    "FinBaseModel",
    "Currency",
    "PeriodType",
    "ScenarioType",
    "StatementType",
    "ValuationMethod",
    "Severity",
    "FiscalPeriod",
    # company / prices
    "CompanyProfile",
    "MarketData",
    "PriceBar",
    "PriceHistory",
    # financials
    "IncomeStatement",
    "BalanceSheet",
    "CashFlowStatement",
    "FinancialStatements",
    # analysis
    "PeriodRatios",
    "RatioAnalysis",
    # forecast
    "DriverAssumptions",
    "Scenario",
    "ForecastResult",
    "ScenarioLine",
    "ScenarioComparison",
    # valuation
    "WACCInputs",
    "WACCResult",
    "DCFInputs",
    "DCFResult",
    "PeerCompany",
    "MultipleStats",
    "CompsValuation",
    "CompsResult",
    "PrecedentTransaction",
    "PrecedentResult",
    "ReverseDCFTarget",
    "ReverseDCFInputs",
    "ReverseDCFResult",
    "SensitivityAxis",
    "SensitivityResult",
    "DriverSensitivity",
    "DriverSensitivityRanking",
    "DistributionType",
    "AssumptionDistribution",
    "MonteCarloInputs",
    "MonteCarloResult",
    # risk
    "RiskFlag",
    "RiskAnalysis",
    # rag
    "DocumentChunk",
    "RetrievedChunk",
    "RAGAnswer",
    # agent
    "ToolCall",
    "ToolResult",
    "AgentStep",
    "AgentResponse",
]
