from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions
from core.forecasting.balance_sheet import forecast_balance_sheet


def test_balance_sheet_forecast():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cash=100,
        accounts_receivable=150,
        inventory=100,
        ppe=500,
        accounts_payable=120,
        debt=300,
        equity=430,
        capex=70,
        depreciation=50,
    )

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.60,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        interest_expense=20,
        tax_rate=0.25,
    )

    forecast = forecast_balance_sheet(
        historical=historical,
        forecast_revenue=1100,
        assumptions=assumptions,
    )

    assert forecast.year == 2026

    assert forecast.accounts_receivable == 165
    assert forecast.inventory == 110
    assert forecast.accounts_payable == 132

    assert forecast.ppe == 520

    assert forecast.debt == 300
    assert forecast.equity == 430
    assert forecast.cash == 100