from core.forecasting.free_cash_flow import calculate_free_cash_flow


def test_free_cash_flow():

    result = calculate_free_cash_flow(
        net_income=100,
        depreciation=20,
        capex=30,
        change_in_working_capital=10,
    )

    assert result == 80
from core.forecasting.free_cash_flow import calculate_free_cash_flow_series


def test_free_cash_flow_series():

    result = calculate_free_cash_flow_series(
        net_incomes=[100, 110, 121],
        depreciations=[20, 22, 24.2],
        capex_values=[30, 33, 36.3],
        working_capital_changes=[10, 11, 12.1],
    )

    assert result == [80, 88, 96.8]