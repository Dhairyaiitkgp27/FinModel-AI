from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions
from core.forecasting.income_statement import forecast_income_statement
from core.forecasting.balance_sheet import forecast_balance_sheet
from core.forecasting.cash_flow import forecast_cash_flow
from core.forecasting.equity import roll_forward_equity

def build_three_statement_model(
    historical: FinancialPeriod,
    assumptions: ForecastAssumptions,
    forecast_year: int,
) -> dict:
    """
    Build a linked three-statement model for one forecast year.

    Returns:
        A dictionary containing:
        - income_statement
        - balance_sheet
        - cash_flow
        - model_checks
    """

    # -------------------------------------------------
    # 1. Income Statement
    # -------------------------------------------------

    income_statement = forecast_income_statement(
        historical=historical,
        assumptions=assumptions,
        forecast_year=forecast_year,
    )

    forecast_revenue = income_statement.revenue

    # -------------------------------------------------
    # 2. Balance Sheet
    # -------------------------------------------------

    balance_sheet = forecast_balance_sheet(
        historical=historical,
        forecast_revenue=forecast_revenue,
        assumptions=assumptions,
    )

    # -------------------------------------------------
    # 3. Calculate Net Income
    # -------------------------------------------------

    ebitda = (
        income_statement.revenue
        - income_statement.cogs
        - income_statement.operating_expenses
    )

    ebit = ebitda - income_statement.depreciation

    ebt = (
        ebit
        - income_statement.interest_expense
    )

    net_income = ebt - income_statement.taxes
    # -------------------------------------------------
# 4. Equity Roll-Forward
# -------------------------------------------------

    equity_roll_forward = roll_forward_equity(
    beginning_equity=historical.equity,
    net_income=net_income,
    dividends=0,
)

    balance_sheet.equity = equity_roll_forward["ending_equity"]
    # -------------------------------------------------
    # 5. Cash Flow Statement
    # -------------------------------------------------

    cash_flow = forecast_cash_flow(
        historical=historical,
        forecast=balance_sheet,
        net_income=net_income,
    )

    # -------------------------------------------------
    # 6. Link Ending Cash to Balance Sheet
    # -------------------------------------------------

    balance_sheet.cash = cash_flow["ending_cash"]

    # -------------------------------------------------
    # 7. Basic Balance Sheet Check
    # -------------------------------------------------

    total_assets = (
        (balance_sheet.cash or 0)
        + (balance_sheet.accounts_receivable or 0)
        + (balance_sheet.inventory or 0)
        + (balance_sheet.ppe or 0)
    )

    total_liabilities_and_equity = (
        (balance_sheet.accounts_payable or 0)
        + (balance_sheet.debt or 0)
        + (balance_sheet.equity or 0)
    )

    balance_difference = (
        total_assets
        - total_liabilities_and_equity
    )

    balance_sheet_balances = (
        abs(balance_difference) < 1e-6
    )

    model_checks = {
        "balance_sheet_balances": balance_sheet_balances,
        "balance_difference": balance_difference,
    }

    return {
    "income_statement": income_statement,
    "balance_sheet": balance_sheet,
    "cash_flow": cash_flow,
    "equity_roll_forward": equity_roll_forward,
    "model_checks": model_checks,
}