"""Tests for the reverse DCF and sensitivity engines."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from core.data import LocalSampleProvider
from core.models import DCFInputs, ReverseDCFInputs, ReverseDCFTarget
from core.valuation import (
    build_dcf_sensitivity,
    dcf_sensitivity,
    driver_sensitivity,
    reverse_dcf_valuation,
    solve_reverse_dcf,
)
from core.valuation.reverse_dcf import _implied_price

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def _reverse_inputs(price: float, **overrides) -> ReverseDCFInputs:
    params = dict(
        current_price=price,
        shares_outstanding=100.0,
        net_debt=0.0,
        wacc=0.10,
        terminal_growth=0.025,
        base_revenue=1000.0,
        horizon_years=5,
        fcf_margin=0.15,
        solve_for=ReverseDCFTarget.REVENUE_GROWTH,
    )
    params.update(overrides)
    return ReverseDCFInputs(**params)


# --------------------------------------------------------------------------- #
# Reverse DCF                                                                  #
# --------------------------------------------------------------------------- #
def test_reverse_dcf_round_trip():
    template = _reverse_inputs(price=1.0)
    known_price = _implied_price(0.08, template)  # price at exactly 8% growth
    result = solve_reverse_dcf(template.model_copy(update={"current_price": known_price}))
    assert result.converged is True
    assert result.implied_value == pytest.approx(0.08, abs=1e-4)
    assert result.achieved_price == pytest.approx(known_price, rel=1e-5)


def test_reverse_dcf_higher_price_implies_higher_growth():
    low_price = _implied_price(0.05, _reverse_inputs(price=1.0))
    high_price = _implied_price(0.15, _reverse_inputs(price=1.0))
    low = solve_reverse_dcf(_reverse_inputs(price=low_price))
    high = solve_reverse_dcf(_reverse_inputs(price=high_price))
    assert high.implied_value > low.implied_value


def test_reverse_dcf_price_above_range_returns_upper_bound():
    # An absurdly high price cannot be reached; report the upper bound, not converged.
    result = solve_reverse_dcf(_reverse_inputs(price=1e12))
    assert result.converged is False
    assert result.implied_value == pytest.approx(2.0)  # REVENUE_GROWTH upper bound


def test_reverse_dcf_terminal_growth_mode():
    inputs = _reverse_inputs(price=1.0, solve_for=ReverseDCFTarget.TERMINAL_GROWTH)
    target = _implied_price(0.03, inputs)  # price at 3% terminal growth
    result = solve_reverse_dcf(inputs.model_copy(update={"current_price": target}))
    assert result.solved_for == ReverseDCFTarget.TERMINAL_GROWTH
    assert result.converged is True
    assert result.implied_value == pytest.approx(0.03, abs=1e-4)


def test_reverse_dcf_end_to_end_on_sample():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    result = reverse_dcf_valuation(ds, terminal_growth=0.025, horizon_years=5)
    assert result.converged is True
    assert result.achieved_price == pytest.approx(result.target_price, rel=1e-4)
    assert result.target_price == pytest.approx(ds.market_data.price)


def test_reverse_dcf_requires_price():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    ds.market_data.price = None
    with pytest.raises(ValueError):
        reverse_dcf_valuation(ds)


# --------------------------------------------------------------------------- #
# Sensitivity grid                                                            #
# --------------------------------------------------------------------------- #
def _base_dcf_inputs() -> DCFInputs:
    return DCFInputs(
        free_cash_flows=[100.0] * 5, wacc=0.10, terminal_growth=0.02,
        net_debt=0.0, shares_outstanding=100.0,
    )


def test_sensitivity_grid_shape_and_center():
    grid = dcf_sensitivity(_base_dcf_inputs(), [0.08, 0.10, 0.12], [0.01, 0.02, 0.03])
    assert len(grid.matrix) == 3
    assert all(len(row) == 3 for row in grid.matrix)
    # centre cell uses the base inputs' own WACC (0.10) and terminal growth (0.02)
    assert grid.matrix[1][1] == pytest.approx(grid.base_value)


def test_sensitivity_grid_is_monotonic():
    grid = dcf_sensitivity(_base_dcf_inputs(), [0.08, 0.10, 0.12], [0.01, 0.02, 0.03])
    # Down a column (rising WACC) price falls; across a row (rising g) price rises.
    for col in range(3):
        assert grid.matrix[0][col] > grid.matrix[1][col] > grid.matrix[2][col]
    for row in range(3):
        assert grid.matrix[row][0] < grid.matrix[row][1] < grid.matrix[row][2]


def test_sensitivity_grid_nan_where_wacc_le_growth():
    grid = dcf_sensitivity(_base_dcf_inputs(), [0.02], [0.03])
    assert math.isnan(grid.matrix[0][0])  # WACC 0.02 <= growth 0.03


def test_build_dcf_sensitivity_from_sample():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    grid = build_dcf_sensitivity(ds, base_growth=0.06, horizon_years=5, terminal_growth=0.025)
    assert len(grid.row_axis.values) == 5
    assert len(grid.col_axis.values) == 5
    assert grid.base_value > 0


# --------------------------------------------------------------------------- #
# Driver sensitivity (tornado)                                                #
# --------------------------------------------------------------------------- #
def test_driver_sensitivity_ranks_by_swing():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    ranking = driver_sensitivity(ds, base_growth=0.06, horizon_years=5, terminal_growth=0.025)
    assert ranking.base_value > 0
    assert {d.driver for d in ranking.drivers} == {"revenue_growth", "terminal_growth", "wacc"}
    ranked = ranking.ranked()
    # ranked() is sorted by descending swing
    swings = [d.swing for d in ranked]
    assert swings == sorted(swings, reverse=True)
    assert all(d.swing >= 0 for d in ranked)
