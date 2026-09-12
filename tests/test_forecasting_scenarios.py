"""Tests for scenario construction and comparison."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.data import LocalSampleProvider
from core.forecasting import (
    build_and_compare,
    build_scenarios,
    compare_scenarios,
    forecast_statements,
    terminal_values,
)
from core.models import FinancialStatements, ScenarioComparison, ScenarioType

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def test_build_scenarios_types_and_count(statements: FinancialStatements):
    scenarios = build_scenarios(statements, base_growth=0.06, horizon_years=5)
    assert len(scenarios) == 3
    assert [s.scenario_type for s in scenarios] == [
        ScenarioType.BASE,
        ScenarioType.BULL,
        ScenarioType.BEAR,
    ]
    assert all(s.horizon_years == 5 for s in scenarios)


def test_bull_and_bear_flex_drivers(statements: FinancialStatements):
    base, bull, bear = build_scenarios(
        statements, base_growth=0.06, horizon_years=3, growth_step=0.03, margin_step=0.02
    )
    b = base.driver_for_year(0)
    up = bull.driver_for_year(0)
    down = bear.driver_for_year(0)

    # growth: bull > base > bear
    assert up.revenue_growth == pytest.approx(0.09)
    assert b.revenue_growth == pytest.approx(0.06)
    assert down.revenue_growth == pytest.approx(0.03)
    # margins: bull has lower COGS %, bear higher
    assert up.cogs_pct_revenue == pytest.approx(b.cogs_pct_revenue - 0.02)
    assert down.cogs_pct_revenue == pytest.approx(b.cogs_pct_revenue + 0.02)


def test_compare_scenarios_ordering(statements: FinancialStatements):
    comparison = compare_scenarios(
        statements, build_scenarios(statements, base_growth=0.06, horizon_years=5)
    )
    assert isinstance(comparison, ScenarioComparison)
    assert comparison.ticker == "TEST"
    assert comparison.horizon_years == 5

    rev = terminal_values(comparison, "revenue")
    fcf = terminal_values(comparison, "free_cash_flow")
    ni = terminal_values(comparison, "net_income")
    # bull dominates base dominates bear on every metric
    assert rev["Bull"] > rev["Base"] > rev["Bear"]
    assert fcf["Bull"] > fcf["Base"] > fcf["Bear"]
    assert ni["Bull"] > ni["Base"] > ni["Bear"]


def test_scenario_lines_have_full_horizon(statements: FinancialStatements):
    comparison = build_and_compare(statements, base_growth=0.05, horizon_years=4)
    for line in comparison.lines:
        assert len(line.revenue) == 4
        assert len(line.ebitda) == 4
        assert len(line.free_cash_flow) == 4


def test_terminal_revenue_exact(statements: FinancialStatements):
    comparison = build_and_compare(
        statements, base_growth=0.06, horizon_years=5, growth_step=0.03
    )
    rev = terminal_values(comparison, "revenue")
    # base 1000 * 1.06^5, bull *1.09^5, bear *1.03^5
    assert rev["Base"] == pytest.approx(1000 * 1.06**5)
    assert rev["Bull"] == pytest.approx(1000 * 1.09**5)
    assert rev["Bear"] == pytest.approx(1000 * 1.03**5)


def test_terminal_values_unknown_metric_raises(statements: FinancialStatements):
    comparison = build_and_compare(statements, base_growth=0.05, horizon_years=3)
    with pytest.raises(ValueError):
        terminal_values(comparison, "ebit_margin")


def test_growth_clamped_to_minus_one(statements: FinancialStatements):
    # An extreme bear step must clamp revenue growth to the -1.0 floor.
    _, _, bear = build_scenarios(
        statements, base_growth=-0.98, horizon_years=2, growth_step=0.05
    )
    assert bear.driver_for_year(0).revenue_growth == pytest.approx(-1.0)


def test_empty_scenarios_raises(statements: FinancialStatements):
    with pytest.raises(ValueError):
        compare_scenarios(statements, [])


def test_all_scenarios_balance_on_sample():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    scenarios = build_scenarios(ds.financials, base_growth=0.06, horizon_years=5)
    for scenario in scenarios:
        result = forecast_statements(ds.financials, scenario)
        assert result.balance_checks_passed is True

    comparison = compare_scenarios(ds.financials, scenarios)
    rev = terminal_values(comparison, "revenue")
    assert rev["Bull"] > rev["Base"] > rev["Bear"]
