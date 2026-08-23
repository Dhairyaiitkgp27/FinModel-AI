from core.data.historical_financials import HistoricalFinancials


def test_historical_financials_creation():

    financials = HistoricalFinancials(
        year=2025,
        revenue=1000,
        cogs=400,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=80,
        cash=150,
        total_debt=300,
        total_assets=1200,
        shareholders_equity=500,
    )

    assert financials.year == 2025
    assert financials.revenue == 1000
    assert financials.cogs == 400
    assert financials.cash == 150
    assert financials.total_debt == 300