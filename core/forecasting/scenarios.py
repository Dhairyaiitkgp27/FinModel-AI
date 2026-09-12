"""Scenario construction and side-by-side comparison.

Phase 4 projects one scenario. This module builds a *set* of scenarios — a base
case plus optimistic (bull) and pessimistic (bear) variants — by flexing the
base drivers, runs the three-statement engine under each, and collects the
resulting metric trajectories into a :class:`ScenarioComparison`.

The bull/bear transform is deliberately simple and transparent: the bull case
raises revenue growth and improves margins (lower COGS and opex as a share of
revenue); the bear case does the reverse. All adjusted drivers are clamped back
into their valid ranges, so the variants are always well-formed.

Free-cash-flow trajectories in the comparison are the *unlevered* FCFF the DCF
consumes, keeping the forecast-to-valuation chain consistent across scenarios.
"""
from __future__ import annotations

from ..models.financials import FinancialStatements
from ..models.forecast import (
    DriverAssumptions,
    Scenario,
    ScenarioComparison,
    ScenarioLine,
    ScenarioType,
)
from ..utils.math import clamp
from .three_statement import derive_base_drivers, forecast_statements

# Default magnitude of the bull/bear flex.
DEFAULT_GROWTH_STEP = 0.03
DEFAULT_MARGIN_STEP = 0.02


def _adjust(
    drivers: DriverAssumptions,
    *,
    growth_delta: float = 0.0,
    cogs_delta: float = 0.0,
    opex_delta: float = 0.0,
    tax_delta: float = 0.0,
) -> DriverAssumptions:
    """Return a copy of ``drivers`` with deltas applied and clamped to valid ranges."""
    return drivers.model_copy(
        update={
            "revenue_growth": max(drivers.revenue_growth + growth_delta, -1.0),
            "cogs_pct_revenue": clamp(drivers.cogs_pct_revenue + cogs_delta, 0.0, 2.0),
            "opex_pct_revenue": clamp(drivers.opex_pct_revenue + opex_delta, 0.0, 2.0),
            "tax_rate": clamp(drivers.tax_rate + tax_delta, 0.0, 1.0),
        }
    )


def build_scenarios(
    base: FinancialStatements,
    base_growth: float,
    horizon_years: int = 5,
    *,
    growth_step: float = DEFAULT_GROWTH_STEP,
    margin_step: float = DEFAULT_MARGIN_STEP,
    default_tax_rate: float = 0.21,
) -> list[Scenario]:
    """Build ``[base, bull, bear]`` scenarios from a company's history.

    ``base_growth`` is the base-case revenue growth assumption; the bull and bear
    cases flex growth by ``growth_step`` and margins by ``margin_step`` around it.
    """
    base_drivers = derive_base_drivers(base, base_growth, default_tax_rate=default_tax_rate)

    base_scenario = Scenario.from_constant(
        "Base", base_drivers, horizon_years, ScenarioType.BASE
    )
    bull_scenario = Scenario.from_constant(
        "Bull",
        _adjust(
            base_drivers,
            growth_delta=+growth_step,
            cogs_delta=-margin_step,
            opex_delta=-margin_step / 2.0,
        ),
        horizon_years,
        ScenarioType.BULL,
    )
    bear_scenario = Scenario.from_constant(
        "Bear",
        _adjust(
            base_drivers,
            growth_delta=-growth_step,
            cogs_delta=+margin_step,
            opex_delta=+margin_step / 2.0,
        ),
        horizon_years,
        ScenarioType.BEAR,
    )
    return [base_scenario, bull_scenario, bear_scenario]


def compare_scenarios(
    base: FinancialStatements, scenarios: list[Scenario]
) -> ScenarioComparison:
    """Run each scenario through the three-statement engine and collect trajectories."""
    if not scenarios:
        raise ValueError("At least one scenario is required for comparison.")

    horizon = scenarios[0].horizon_years
    lines: list[ScenarioLine] = []

    for scenario in scenarios:
        result = forecast_statements(base, scenario)
        incomes = result.statements.income_statements
        lines.append(
            ScenarioLine(
                scenario_name=scenario.name,
                scenario_type=scenario.scenario_type,
                revenue=[s.revenue or 0.0 for s in incomes],
                ebitda=[s.ebitda or 0.0 for s in incomes],
                ebit=[s.ebit or 0.0 for s in incomes],
                net_income=[s.net_income or 0.0 for s in incomes],
                free_cash_flow=list(result.free_cash_flows),  # unlevered FCFF
            )
        )

    return ScenarioComparison(ticker=base.ticker, horizon_years=horizon, lines=lines)


def build_and_compare(
    base: FinancialStatements,
    base_growth: float,
    horizon_years: int = 5,
    *,
    growth_step: float = DEFAULT_GROWTH_STEP,
    margin_step: float = DEFAULT_MARGIN_STEP,
    default_tax_rate: float = 0.21,
) -> ScenarioComparison:
    """Convenience: build the default bull/base/bear set and compare in one call."""
    scenarios = build_scenarios(
        base,
        base_growth,
        horizon_years,
        growth_step=growth_step,
        margin_step=margin_step,
        default_tax_rate=default_tax_rate,
    )
    return compare_scenarios(base, scenarios)


def terminal_values(comparison: ScenarioComparison, metric: str) -> dict[str, float]:
    """Terminal-year value of ``metric`` for each scenario, keyed by scenario name.

    ``metric`` is one of ``revenue``, ``ebitda``, ``ebit``, ``net_income``, or
    ``free_cash_flow``.
    """
    out: dict[str, float] = {}
    for line in comparison.lines:
        series = getattr(line, metric, None)
        if series is None:
            raise ValueError(f"Unknown scenario metric '{metric}'")
        out[line.scenario_name] = series[-1] if series else float("nan")
    return out
