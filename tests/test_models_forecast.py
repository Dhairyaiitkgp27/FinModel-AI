"""Tests for forecasting models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import (
    DriverAssumptions,
    FinancialStatements,
    ForecastResult,
    Scenario,
    ScenarioType,
)


def _drivers(**overrides) -> DriverAssumptions:
    base = dict(
        revenue_growth=0.08,
        cogs_pct_revenue=0.60,
        opex_pct_revenue=0.20,
        da_pct_revenue=0.05,
        tax_rate=0.21,
        capex_pct_revenue=0.06,
        dso=45.0,
        dio=60.0,
        dpo=40.0,
    )
    base.update(overrides)
    return DriverAssumptions(**base)


def test_drivers_valid():
    d = _drivers()
    assert d.revenue_growth == 0.08
    assert d.interest_rate_on_debt is None


def test_drivers_tax_rate_above_one_rejected():
    with pytest.raises(ValidationError):
        _drivers(tax_rate=1.5)


def test_drivers_allows_negative_growth():
    d = _drivers(revenue_growth=-0.10)
    assert d.revenue_growth == -0.10


def test_drivers_growth_below_minus_one_rejected():
    with pytest.raises(ValidationError):
        _drivers(revenue_growth=-1.5)


def test_drivers_negative_dso_rejected():
    with pytest.raises(ValidationError):
        _drivers(dso=-1.0)


def test_scenario_length_must_match_horizon():
    with pytest.raises(ValidationError):
        Scenario(
            name="Base",
            horizon_years=3,
            drivers_by_year=[_drivers(), _drivers()],  # only 2, need 3
        )


def test_scenario_from_constant_builds_correct_length():
    s = Scenario.from_constant("Base", _drivers(), horizon_years=5)
    assert s.horizon_years == 5
    assert len(s.drivers_by_year) == 5
    assert s.scenario_type == ScenarioType.BASE
    assert s.driver_for_year(0).revenue_growth == 0.08


def test_scenario_from_constant_copies_drivers():
    d = _drivers()
    s = Scenario.from_constant("Bull", d, horizon_years=2, scenario_type=ScenarioType.BULL)
    # mutating one year must not affect another (independent copies)
    assert s.drivers_by_year[0] is not s.drivers_by_year[1]
    assert s.scenario_type == ScenarioType.BULL


def test_forecast_result_holds_statements():
    s = Scenario.from_constant("Base", _drivers(), horizon_years=5)
    result = ForecastResult(
        ticker="TEST",
        scenario=s,
        statements=FinancialStatements(ticker="TEST"),
        free_cash_flows=[10.0, 12.0, 14.0, 16.0, 18.0],
        revenue_path=[100, 108, 116, 126, 136],
    )
    assert len(result.free_cash_flows) == 5
    assert result.scenario.horizon_years == 5
