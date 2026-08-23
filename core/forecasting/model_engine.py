from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions
from core.forecasting.three_statement import build_three_statement_model
from core.forecasting.free_cash_flow import calculate_free_cash_flow
from core.forecasting.valuation import value_from_free_cash_flows
from core.forecasting.valuation import calculate_equity_value
from core.forecasting.valuation import calculate_share_price
class FinancialModelOutput(dict):
    """Dictionary-backed model output supporting both [] and .attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"'FinancialModelOutput' object has no attribute '{name}'"
            )


def run_financial_model(
    historical: FinancialPeriod,
    assumptions: ForecastAssumptions,
    forecast_year: int,
) -> dict:
    """
    Run the complete financial model for one forecast year.
    """

    model = build_three_statement_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=forecast_year,
    )

    return model
def run_valuation_model(
    financial_model,
    discount_rate,
    terminal_growth_rate,
):
    """
    Convert a financial model into a DCF valuation.
    """

    income_statement = financial_model[
        "income_statement"
    ]

    cash_flow = financial_model[
        "cash_flow"
    ]

    net_income = (
        income_statement.revenue
        - income_statement.cogs
        - income_statement.operating_expenses
        - income_statement.depreciation
        - income_statement.interest_expense
        - income_statement.taxes
    )

    depreciation = income_statement.depreciation

    capex = cash_flow["cfi"] * -1

    change_in_working_capital = (
        financial_model["balance_sheet"].accounts_receivable
        + financial_model["balance_sheet"].inventory
    )

    free_cash_flow = calculate_free_cash_flow(
        net_income=net_income,
        depreciation=depreciation,
        capex=capex,
        change_in_working_capital=change_in_working_capital,
    )

    valuation = value_from_free_cash_flows(
        free_cash_flows=[free_cash_flow],
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
    )

    return {
        "free_cash_flow": free_cash_flow,
        "valuation": valuation,
    }
def run_equity_valuation(
    enterprise_value,
    total_debt,
    cash,
    shares_outstanding,
):
    """
    Convert enterprise value into equity value
    and implied share price.
    """

    equity_value = calculate_equity_value(
        enterprise_value=enterprise_value,
        total_debt=total_debt,
        cash=cash,
    )

    share_price = calculate_share_price(
        equity_value=equity_value,
        shares_outstanding=shares_outstanding,
    )

    return {
        "equity_value": equity_value,
        "share_price": share_price,
    }
def run_multi_year_valuation(
    free_cash_flows,
    discount_rate,
    terminal_growth_rate,
):
    """
    Value multiple years of forecast free cash flows.
    """

    valuation = value_from_free_cash_flows(
        free_cash_flows=free_cash_flows,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
    )

    return {
        "free_cash_flows": free_cash_flows,
        "valuation": valuation,
    }
def run_complete_financial_model(
    historical,
    assumptions,
    forecast_year,
):
    """
    Run the complete financial model for one
    forecast year.

    Pipeline:

    Historical Financials
            ↓
    3-Statement Model
            ↓
    Free Cash Flow
            ↓
    Valuation
    """

    model = run_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=forecast_year,
    )

    return FinancialModelOutput(model)