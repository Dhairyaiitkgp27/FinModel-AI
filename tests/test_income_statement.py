from core.models.financials import FinancialPeriod
from core.forecasting.income_statement import forecast_income_statement
from core.forecasting.assumptions import ForecastAssumptions


def test_income_statement_forecast():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cogs=600,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=30,
    )

    forecast = assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.60,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        interest_expense=20,
        tax_rate=0.25,
    )

    forecast = forecast_income_statement(
        historical=historical,
        assumptions=assumptions,
        forecast_year=2026,
    
    )

    assert forecast.year == 2026
    assert forecast.revenue == 1100
    assert forecast.cogs == 660
    assert forecast.operating_expenses == 220
    assert forecast.depreciation == 55
    assert forecast.interest_expense == 20