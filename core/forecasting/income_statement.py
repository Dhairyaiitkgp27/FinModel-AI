from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions


def forecast_income_statement(
    historical: FinancialPeriod,
    assumptions: ForecastAssumptions,
    forecast_year: int,
) -> FinancialPeriod:
    """
    Forecast an income statement using a historical period
    and a structured set of assumptions.
    """

    # Revenue
    revenue = historical.revenue * (
        1 + assumptions.revenue_growth
    )

    # COGS
    cogs = revenue * assumptions.cogs_margin

    # Operating expenses
    operating_expenses = (
        revenue * assumptions.operating_expense_margin
    )

    # Depreciation
    depreciation = (
        revenue * assumptions.depreciation_margin
    )

    # EBITDA
    ebitda = revenue - cogs - operating_expenses

    # EBIT
    ebit = ebitda - depreciation

    # Earnings before tax
    ebt = ebit - assumptions.interest_expense

    # Taxes
    taxes = max(ebt, 0) * assumptions.tax_rate

    # Net income
    net_income = ebt - taxes

    return FinancialPeriod(
        year=forecast_year,
        revenue=revenue,
        cogs=cogs,
        operating_expenses=operating_expenses,
        depreciation=depreciation,
        interest_expense=assumptions.interest_expense,
        taxes=taxes,
    )