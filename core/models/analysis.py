"""Structured output models for the financial analysis engine.

These are *result* schemas. The deterministic analysis engine (Phase 3)
populates them from :class:`~core.models.financials.FinancialStatements`. The
LLM never computes these values — it only narrates them.
"""
from __future__ import annotations

from pydantic import Field

from .base import FinBaseModel, FiscalPeriod


class PeriodRatios(FinBaseModel):
    """Computed ratios for a single fiscal period."""

    period: FiscalPeriod

    # Growth
    revenue_growth: float | None = None

    # Profitability / margins
    gross_margin: float | None = None
    ebitda_margin: float | None = None
    ebit_margin: float | None = None
    net_margin: float | None = None
    fcf_margin: float | None = None

    # Returns
    roe: float | None = None
    roic: float | None = None

    # Liquidity
    current_ratio: float | None = None
    quick_ratio: float | None = None

    # Leverage
    debt_to_ebitda: float | None = None
    net_debt_to_ebitda: float | None = None

    # Working capital / cash conversion
    working_capital: float | None = None
    cash_conversion: float | None = None  # FCF / net income
    days_sales_outstanding: float | None = None
    days_inventory_outstanding: float | None = None
    days_payable_outstanding: float | None = None
    cash_conversion_cycle: float | None = None


class RatioAnalysis(FinBaseModel):
    """A time series of period ratios plus convenience access to the latest."""

    ticker: str
    periods: list[PeriodRatios] = Field(default_factory=list)

    @property
    def latest(self) -> PeriodRatios | None:
        return self.periods[-1] if self.periods else None

    def series(self, field: str) -> list[float | None]:
        """Extract one ratio across all periods, chronologically."""
        return [getattr(p, field, None) for p in self.periods]
