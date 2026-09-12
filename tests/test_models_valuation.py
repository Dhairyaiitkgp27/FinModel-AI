"""Tests for valuation input/output models and their invariants."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import (
    AssumptionDistribution,
    DCFInputs,
    DCFResult,
    DistributionType,
    DriverSensitivity,
    DriverSensitivityRanking,
    MonteCarloInputs,
    MonteCarloResult,
    PrecedentTransaction,
    ReverseDCFInputs,
    ReverseDCFTarget,
    SensitivityAxis,
    SensitivityResult,
    WACCInputs,
)


# --------------------------------------------------------------------------- #
# WACC                                                                        #
# --------------------------------------------------------------------------- #
def test_wacc_inputs_valid():
    w = WACCInputs(
        risk_free_rate=0.04,
        beta=1.1,
        equity_risk_premium=0.055,
        pretax_cost_of_debt=0.05,
        tax_rate=0.21,
        equity_value=800.0,
        debt_value=200.0,
    )
    assert w.beta == 1.1


def test_wacc_inputs_reject_zero_capital_structure():
    with pytest.raises(ValidationError):
        WACCInputs(
            risk_free_rate=0.04,
            beta=1.0,
            equity_risk_premium=0.055,
            pretax_cost_of_debt=0.05,
            tax_rate=0.21,
            equity_value=0.0,
            debt_value=0.0,
        )


def test_wacc_inputs_reject_negative_beta():
    with pytest.raises(ValidationError):
        WACCInputs(
            risk_free_rate=0.04,
            beta=-0.1,
            equity_risk_premium=0.055,
            pretax_cost_of_debt=0.05,
            tax_rate=0.21,
            equity_value=800.0,
            debt_value=200.0,
        )


# --------------------------------------------------------------------------- #
# DCF                                                                         #
# --------------------------------------------------------------------------- #
def test_dcf_inputs_valid():
    d = DCFInputs(
        free_cash_flows=[100, 110, 120, 130, 140],
        wacc=0.09,
        terminal_growth=0.025,
        net_debt=50.0,
        shares_outstanding=100.0,
    )
    assert len(d.free_cash_flows) == 5


def test_dcf_inputs_reject_wacc_le_terminal_growth():
    with pytest.raises(ValidationError):
        DCFInputs(
            free_cash_flows=[100],
            wacc=0.02,
            terminal_growth=0.03,  # exceeds WACC -> divergent terminal value
            shares_outstanding=100.0,
        )


def test_dcf_inputs_reject_empty_fcf():
    with pytest.raises(ValidationError):
        DCFInputs(free_cash_flows=[], wacc=0.09, terminal_growth=0.02, shares_outstanding=100.0)


def test_dcf_inputs_reject_nonpositive_shares():
    with pytest.raises(ValidationError):
        DCFInputs(
            free_cash_flows=[100], wacc=0.09, terminal_growth=0.02, shares_outstanding=0.0
        )


def test_dcf_result_terminal_value_pct():
    r = DCFResult(
        discount_factors=[0.9],
        present_values=[90.0],
        sum_pv_explicit=90.0,
        terminal_value=1000.0,
        pv_terminal_value=810.0,
        enterprise_value=900.0,
        net_debt=0.0,
        equity_value=900.0,
        shares_outstanding=100.0,
        implied_share_price=9.0,
        wacc=0.09,
        terminal_growth=0.025,
    )
    assert r.terminal_value_pct == pytest.approx(0.9)


# --------------------------------------------------------------------------- #
# Reverse DCF                                                                 #
# --------------------------------------------------------------------------- #
def test_reverse_dcf_inputs_default_solves_for_revenue_growth():
    r = ReverseDCFInputs(
        current_price=150.0,
        shares_outstanding=100.0,
        net_debt=0.0,
        wacc=0.09,
        terminal_growth=0.025,
        base_revenue=1000.0,
        horizon_years=5,
        fcf_margin=0.15,
    )
    assert r.solve_for == ReverseDCFTarget.REVENUE_GROWTH


def test_reverse_dcf_rejects_nonpositive_price():
    with pytest.raises(ValidationError):
        ReverseDCFInputs(
            current_price=0.0,
            shares_outstanding=100.0,
            wacc=0.09,
            terminal_growth=0.025,
            base_revenue=1000.0,
            horizon_years=5,
            fcf_margin=0.15,
        )


# --------------------------------------------------------------------------- #
# Sensitivity                                                                 #
# --------------------------------------------------------------------------- #
def test_sensitivity_result_valid_shape():
    res = SensitivityResult(
        row_axis=SensitivityAxis(name="WACC", values=[0.08, 0.09]),
        col_axis=SensitivityAxis(name="g", values=[0.02, 0.025, 0.03]),
        matrix=[[10, 11, 12], [9, 10, 11]],
    )
    assert len(res.matrix) == 2
    assert len(res.matrix[0]) == 3


def test_sensitivity_result_bad_shape_rejected():
    with pytest.raises(ValidationError):
        SensitivityResult(
            row_axis=SensitivityAxis(name="WACC", values=[0.08, 0.09]),
            col_axis=SensitivityAxis(name="g", values=[0.02, 0.03]),
            matrix=[[10, 11]],  # only one row, need two
        )


def test_driver_sensitivity_swing_and_ranking():
    ranking = DriverSensitivityRanking(
        base_value=100.0,
        drivers=[
            DriverSensitivity(
                driver="wacc", low_value=0.08, high_value=0.10, low_result=120, high_result=90
            ),
            DriverSensitivity(
                driver="growth", low_value=0.05, high_value=0.10, low_result=95, high_result=110
            ),
        ],
    )
    assert ranking.drivers[0].swing == pytest.approx(30.0)
    ranked = ranking.ranked()
    assert ranked[0].driver == "wacc"  # bigger swing first


# --------------------------------------------------------------------------- #
# Distributions / Monte Carlo                                                 #
# --------------------------------------------------------------------------- #
def test_normal_distribution_requires_mean_and_std():
    with pytest.raises(ValidationError):
        AssumptionDistribution(name="wacc", distribution=DistributionType.NORMAL, mean=0.09)


def test_uniform_distribution_requires_low_high():
    with pytest.raises(ValidationError):
        AssumptionDistribution(name="g", distribution=DistributionType.UNIFORM, low=0.02)


def test_distribution_rejects_low_above_high():
    with pytest.raises(ValidationError):
        AssumptionDistribution(
            name="g", distribution=DistributionType.UNIFORM, low=0.05, high=0.02
        )


def test_triangular_distribution_valid():
    dist = AssumptionDistribution(
        name="growth",
        distribution=DistributionType.TRIANGULAR,
        low=0.02,
        mode=0.05,
        high=0.10,
    )
    assert dist.mode == 0.05


def test_monte_carlo_inputs_defaults():
    mc = MonteCarloInputs()
    assert mc.n_simulations == 10_000
    assert mc.seed == 42


def test_monte_carlo_inputs_reject_too_few_sims():
    with pytest.raises(ValidationError):
        MonteCarloInputs(n_simulations=10)


def test_monte_carlo_result_fields():
    res = MonteCarloResult(
        n_simulations=10_000,
        seed=42,
        mean=150.0,
        median=148.0,
        std=20.0,
        p10=120.0,
        p25=135.0,
        p50=148.0,
        p75=165.0,
        p90=180.0,
        current_price=140.0,
        prob_upside=0.62,
        prob_downside=0.38,
    )
    assert res.p90 > res.p10
    assert res.prob_upside + res.prob_downside == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# Precedent transactions                                                      #
# --------------------------------------------------------------------------- #
def test_precedent_transaction_sample_flag_default():
    tx = PrecedentTransaction(target="TargetCo", acquirer="BuyerCo", ev_to_ebitda=12.0)
    assert tx.is_sample is True
