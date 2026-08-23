from core.forecasting.valuation import calculate_dcf_value


def test_dcf_valuation():

    free_cash_flows = [
        100,
        110,
        121,
    ]

    result = calculate_dcf_value(
        free_cash_flows=free_cash_flows,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )

    assert len(result.present_values) == 3

    assert result.terminal_value > 0

    assert result.terminal_present_value > 0

    assert result.enterprise_value > 0

from core.forecasting.valuation import calculate_equity_value


def test_equity_value():

    enterprise_value = 1000
    total_debt = 300
    cash = 100

    equity_value = calculate_equity_value(
        enterprise_value=enterprise_value,
        total_debt=total_debt,
        cash=cash,
    )

    assert equity_value == 800
from core.forecasting.valuation import calculate_share_price


def test_share_price():

    equity_value = 800
    shares_outstanding = 10

    share_price = calculate_share_price(
        equity_value=equity_value,
        shares_outstanding=shares_outstanding,
    )

    assert share_price == 80
from core.forecasting.valuation import dcf_sensitivity


def test_dcf_sensitivity():

    free_cash_flows = [
        100,
        110,
        121,
    ]

    sensitivity = dcf_sensitivity(
        free_cash_flows=free_cash_flows,
        discount_rates=[0.08, 0.10, 0.12],
        terminal_growth_rates=[0.02, 0.03, 0.04],
    )

    # 3 discount rates × 3 growth rates
    assert len(sensitivity) == 3

    for discount_rate in [0.08, 0.10, 0.12]:
        assert discount_rate in sensitivity

        assert len(sensitivity[discount_rate]) == 3

    # Higher terminal growth should increase valuation
    assert (
        sensitivity[0.10][0.04]
        > sensitivity[0.10][0.02]
    )

    # Higher discount rate should decrease valuation
    assert (
        sensitivity[0.12][0.03]
        < sensitivity[0.08][0.03]
    )
from core.forecasting.valuation import value_from_free_cash_flows


def test_value_from_free_cash_flows():

    result = value_from_free_cash_flows(
        free_cash_flows=[80, 88, 96.8],
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )

    assert result.enterprise_value > 0
    assert len(result.present_values) == 3
    assert result.terminal_value > 0
    assert result.terminal_present_value > 0
import pytest


def test_dcf_empty_cash_flows():

    with pytest.raises(ValueError):
        calculate_dcf_value(
            free_cash_flows=[],
            discount_rate=0.10,
            terminal_growth_rate=0.03,
        )


def test_dcf_invalid_discount_rate():

    with pytest.raises(ValueError):
        calculate_dcf_value(
            free_cash_flows=[100, 110, 121],
            discount_rate=0.03,
            terminal_growth_rate=0.03,
        )


def test_value_from_fcf_invalid_rate():

    with pytest.raises(ValueError):
        value_from_free_cash_flows(
            free_cash_flows=[100, 110, 121],
            discount_rate=0.02,
            terminal_growth_rate=0.03,
        )


def test_share_price_zero_shares():

    with pytest.raises(ValueError):
        calculate_share_price(
            equity_value=800,
            shares_outstanding=0,
        )


def test_share_price_negative_shares():

    with pytest.raises(ValueError):
        calculate_share_price(
            equity_value=800,
            shares_outstanding=-10,
        )  