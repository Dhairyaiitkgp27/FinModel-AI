"""Tests for the WACC and DCF valuation engines."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.data import LocalSampleProvider
from core.forecasting import build_scenario_from_history, forecast_statements
from core.models import DCFInputs, WACCInputs
from core.valuation import (
    build_dcf_inputs,
    build_wacc_inputs,
    compute_dcf,
    compute_wacc,
    dcf_valuation,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


# --------------------------------------------------------------------------- #
# WACC                                                                        #
# --------------------------------------------------------------------------- #
def test_wacc_exact():
    result = compute_wacc(
        WACCInputs(
            risk_free_rate=0.04,
            beta=1.2,
            equity_risk_premium=0.05,
            pretax_cost_of_debt=0.06,
            tax_rate=0.25,
            equity_value=800.0,
            debt_value=200.0,
        )
    )
    assert result.cost_of_equity == pytest.approx(0.10)  # 0.04 + 1.2 * 0.05
    assert result.after_tax_cost_of_debt == pytest.approx(0.045)  # 0.06 * 0.75
    assert result.equity_weight == pytest.approx(0.8)
    assert result.debt_weight == pytest.approx(0.2)
    assert result.wacc == pytest.approx(0.089)  # 0.8*0.10 + 0.2*0.045


def test_wacc_all_equity_equals_cost_of_equity():
    result = compute_wacc(
        WACCInputs(
            risk_free_rate=0.03,
            beta=1.0,
            equity_risk_premium=0.05,
            pretax_cost_of_debt=0.06,
            tax_rate=0.25,
            equity_value=1000.0,
            debt_value=0.0,
        )
    )
    assert result.debt_weight == pytest.approx(0.0)
    assert result.wacc == pytest.approx(result.cost_of_equity)


# --------------------------------------------------------------------------- #
# DCF                                                                         #
# --------------------------------------------------------------------------- #
def test_dcf_exact_flat_fcf():
    result = compute_dcf(
        DCFInputs(
            free_cash_flows=[100.0, 100.0, 100.0, 100.0, 100.0],
            wacc=0.10,
            terminal_growth=0.0,
            net_debt=200.0,
            shares_outstanding=50.0,
        )
    )
    assert result.discount_factors[0] == pytest.approx(1 / 1.1)
    assert result.discount_factors[4] == pytest.approx(1 / 1.1**5)
    # annuity of 100 for 5 years at 10% = 379.0787
    assert result.sum_pv_explicit == pytest.approx(379.0787, abs=1e-3)
    assert result.terminal_value == pytest.approx(1000.0)  # 100 / (0.10 - 0)
    assert result.pv_terminal_value == pytest.approx(1000.0 / 1.1**5, abs=1e-3)
    assert result.enterprise_value == pytest.approx(1000.0, abs=1e-3)
    assert result.equity_value == pytest.approx(800.0, abs=1e-3)
    assert result.implied_share_price == pytest.approx(16.0, abs=1e-4)
    assert result.terminal_value_pct == pytest.approx(0.620921, abs=1e-4)


def test_dcf_constant_pv_when_growth_equals_wacc():
    # FCF growing at exactly WACC -> each discounted value is identical.
    result = compute_dcf(
        DCFInputs(
            free_cash_flows=[100.0, 110.0, 121.0, 133.1, 146.41],
            wacc=0.10,
            terminal_growth=0.02,
            shares_outstanding=100.0,
        )
    )
    for pv in result.present_values:
        assert pv == pytest.approx(100.0 / 1.1, abs=1e-6)
    assert result.sum_pv_explicit == pytest.approx(5 * 100.0 / 1.1, abs=1e-4)


def test_dcf_mid_year_convention_reduces_discounting():
    common = dict(free_cash_flows=[100.0] * 5, wacc=0.10, terminal_growth=0.0, shares_outstanding=50.0)
    year_end = compute_dcf(DCFInputs(**common, mid_year_convention=False))
    mid_year = compute_dcf(DCFInputs(**common, mid_year_convention=True))
    # mid-year discounts less, so factors and implied price are higher
    assert mid_year.discount_factors[0] == pytest.approx(1 / 1.1**0.5)
    assert mid_year.discount_factors[0] > year_end.discount_factors[0]
    assert mid_year.implied_share_price > year_end.implied_share_price


def test_dcf_net_debt_reduces_equity():
    base = dict(free_cash_flows=[100.0] * 5, wacc=0.10, terminal_growth=0.0, shares_outstanding=100.0)
    no_debt = compute_dcf(DCFInputs(**base, net_debt=0.0))
    with_debt = compute_dcf(DCFInputs(**base, net_debt=300.0))
    assert no_debt.enterprise_value == pytest.approx(with_debt.enterprise_value)
    assert no_debt.equity_value - with_debt.equity_value == pytest.approx(300.0)
    assert no_debt.implied_share_price - with_debt.implied_share_price == pytest.approx(3.0)


# --------------------------------------------------------------------------- #
# Builders / orchestration                                                    #
# --------------------------------------------------------------------------- #
def test_build_wacc_inputs_from_sample():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    inputs = build_wacc_inputs(ds, risk_free_rate=0.04, equity_risk_premium=0.055, tax_rate=0.21)
    assert inputs.beta == pytest.approx(1.29)
    # equity value should equal the (backfilled) market cap
    assert inputs.equity_value == pytest.approx(ds.market_data.market_cap)
    result = compute_wacc(inputs)
    assert 0.10 < result.wacc < 0.12


def test_build_dcf_inputs_requires_shares():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    scenario = build_scenario_from_history(ds.financials, revenue_growth=0.06, horizon_years=5)
    forecast = forecast_statements(ds.financials, scenario)
    ds.market_data.shares_outstanding = None  # simulate missing share count
    with pytest.raises(ValueError):
        build_dcf_inputs(forecast, ds, wacc=0.09, terminal_growth=0.025)


def test_dcf_valuation_end_to_end():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    result = dcf_valuation(ds, base_growth=0.06, horizon_years=5, terminal_growth=0.025)
    assert 0.0 < result.wacc < 1.0
    assert result.implied_share_price > 0
    assert 0.0 < result.terminal_value_pct < 1.0
    assert result.enterprise_value > result.equity_value  # Apple has positive net debt
    assert len(result.discount_factors) == 5


def test_dcf_valuation_higher_growth_gives_higher_value():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("MSFT")
    low = dcf_valuation(ds, base_growth=0.04, horizon_years=5, terminal_growth=0.025)
    high = dcf_valuation(ds, base_growth=0.10, horizon_years=5, terminal_growth=0.025)
    assert high.implied_share_price > low.implied_share_price
