"""Forecasting models: driver assumptions, scenarios, and results.

The three-statement forecast (Phase 4/5) is driver-based. A
:class:`DriverAssumptions` object holds one year's operating drivers; a
:class:`Scenario` holds an ordered list of them (one per forecast year) under a
named case (base/bull/bear/custom). Results are returned as
:class:`ForecastResult`, wrapping projected statements plus the FCF path.
"""
from __future__ import annotations

from pydantic import Field, model_validator

from .base import FinBaseModel, ScenarioType
from .financials import FinancialStatements


class DriverAssumptions(FinBaseModel):
    """Operating drivers for a single forecast year.

    Percentages are expressed as decimals (0.08 == 8%). Field constraints reject
    obviously invalid inputs (e.g. a tax rate above 100%) while still allowing
    legitimate edge cases such as negative revenue growth.
    """

    revenue_growth: float = Field(ge=-1.0, description="YoY revenue growth (decimal)")
    cogs_pct_revenue: float = Field(ge=0.0, le=2.0, description="COGS as % of revenue")
    opex_pct_revenue: float = Field(ge=0.0, le=2.0, description="Operating expense as % of revenue")
    da_pct_revenue: float = Field(ge=0.0, le=1.0, description="D&A as % of revenue")
    tax_rate: float = Field(ge=0.0, le=1.0, description="Effective tax rate")
    capex_pct_revenue: float = Field(ge=0.0, le=1.0, description="CapEx as % of revenue")
    dso: float = Field(ge=0.0, description="Days sales outstanding")
    dio: float = Field(ge=0.0, description="Days inventory outstanding")
    dpo: float = Field(ge=0.0, description="Days payable outstanding")
    interest_rate_on_debt: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Average interest rate on debt"
    )


class Scenario(FinBaseModel):
    """A named forecast scenario over a fixed horizon.

    ``drivers_by_year`` must contain exactly ``horizon_years`` entries. Use
    :meth:`from_constant` to build a scenario that repeats a single driver set.
    """

    name: str
    scenario_type: ScenarioType = ScenarioType.BASE
    horizon_years: int = Field(ge=1, le=20)
    drivers_by_year: list[DriverAssumptions]

    @model_validator(mode="after")
    def _check_length(self) -> Scenario:
        if len(self.drivers_by_year) != self.horizon_years:
            raise ValueError(
                f"drivers_by_year has {len(self.drivers_by_year)} entries but "
                f"horizon_years is {self.horizon_years}"
            )
        return self

    @classmethod
    def from_constant(
        cls,
        name: str,
        drivers: DriverAssumptions,
        horizon_years: int,
        scenario_type: ScenarioType = ScenarioType.BASE,
    ) -> Scenario:
        """Build a scenario that applies the same drivers to every year."""
        return cls(
            name=name,
            scenario_type=scenario_type,
            horizon_years=horizon_years,
            drivers_by_year=[drivers.model_copy() for _ in range(horizon_years)],
        )

    def driver_for_year(self, index: int) -> DriverAssumptions:
        """Zero-based accessor for a forecast year's drivers."""
        return self.drivers_by_year[index]


class ForecastResult(FinBaseModel):
    """Projected statements and cash flows produced by the forecasting engine."""

    ticker: str
    scenario: Scenario
    statements: FinancialStatements
    free_cash_flows: list[float] = Field(default_factory=list)
    revenue_path: list[float] = Field(default_factory=list)
    balance_checks_passed: bool | None = None


class ScenarioLine(FinBaseModel):
    """One metric's trajectory under a single scenario, for comparison tables."""

    scenario_name: str
    scenario_type: ScenarioType
    revenue: list[float] = Field(default_factory=list)
    ebitda: list[float] = Field(default_factory=list)
    ebit: list[float] = Field(default_factory=list)
    net_income: list[float] = Field(default_factory=list)
    free_cash_flow: list[float] = Field(default_factory=list)


class ScenarioComparison(FinBaseModel):
    """Side-by-side comparison of base/bull/bear (and custom) scenarios."""

    ticker: str
    horizon_years: int
    lines: list[ScenarioLine] = Field(default_factory=list)
