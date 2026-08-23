from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions
from core.forecasting.multi_year import (
    forecast_multiple_years,
    run_multi_year_financial_model,
)


def test_multi_year_forecast():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cogs=600,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=30,
    )

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.60,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        interest_expense=20,
        tax_rate=0.25,
    )

    forecasts = forecast_multiple_years(
        historical=historical,
        assumptions=assumptions,
        forecast_years=[2026, 2027, 2028],
    )

    assert len(forecasts) == 3

    assert forecasts[0].year == 2026
    assert forecasts[1].year == 2027
    assert forecasts[2].year == 2028

    assert forecasts[0].revenue == 1100
    assert forecasts[1].revenue == 1210
    assert forecasts[2].revenue == 1331
def test_run_multi_year_financial_model():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cogs=400,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=80,
        cash=300,
        accounts_receivable=100,
        inventory=150,
        ppe=400,
        accounts_payable=80,
        debt=500,
        equity=500,
        capex=50,
        total_debt=500,
        total_assets=1200,
        shareholders_equity=500,
    )

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.40,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        tax_rate=0.25,
        interest_rate=0.05,
    )

    results = run_multi_year_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_years=[2026, 2027, 2028],
    )

    assert len(results) == 3

    assert results[0] is not None
    assert results[1] is not None
    assert results[2] is not None
def test_multi_year_model_rolls_forward():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cogs=400,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=80,
        cash=300,
        accounts_receivable=100,
        inventory=150,
        ppe=400,
        accounts_payable=80,
        debt=500,
        equity=500,
        capex=50,
        total_debt=500,
        total_assets=1200,
        shareholders_equity=500,
    )

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.40,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        tax_rate=0.25,
        interest_rate=0.05,
    )

    results = run_multi_year_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_years=[2026, 2027, 2028],
    )

    assert len(results) == 3

    revenue_2026 = results[0]["income_statement"].revenue
    revenue_2027 = results[1]["income_statement"].revenue
    revenue_2028 = results[2]["income_statement"].revenue

    assert revenue_2026 == 1100
    assert revenue_2027 == 1210
    assert revenue_2028 == 1331