"""Risk analysis models.

The deterministic risk engine (Phase 16) emits :class:`RiskFlag` objects from
leverage, liquidity, margin, FCF, concentration, and valuation-sensitivity
signals. The LLM narrates these; it never invents risk metrics.
"""
from __future__ import annotations

from pydantic import Field

from .base import FinBaseModel, Severity


class RiskFlag(FinBaseModel):
    """A single identified risk with its supporting metric."""

    category: str  # e.g. "leverage", "liquidity", "margin", "fcf", "valuation"
    severity: Severity
    metric: str
    value: float | None = None
    threshold: float | None = None
    message: str


class RiskAnalysis(FinBaseModel):
    """Aggregated risk assessment for a company."""

    ticker: str
    flags: list[RiskFlag] = Field(default_factory=list)
    overall_score: float | None = Field(
        default=None, ge=0.0, le=100.0, description="0 (low risk) to 100 (high risk)"
    )

    def by_severity(self, severity: Severity) -> list[RiskFlag]:
        return [f for f in self.flags if f.severity == severity]

    @property
    def high_severity_count(self) -> int:
        return len(self.by_severity(Severity.HIGH))
