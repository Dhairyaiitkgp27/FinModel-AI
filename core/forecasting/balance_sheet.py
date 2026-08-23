from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions


def forecast_balance_sheet(
    historical: FinancialPeriod,
    forecast_revenue: float,
    assumptions: ForecastAssumptions,
) -> FinancialPeriod:
    """
    Forecast the balance sheet using operating assumptions.

    Current version models:
    - Accounts receivable
    - Inventory
    - PP&E
    - Accounts payable
    - Debt
    - Equity
    - Cash

    All monetary values are assumed to be in millions.
    """

    # Working capital assumptions
    accounts_receivable = (
        historical.accounts_receivable
        / historical.revenue
        * forecast_revenue
    )

    inventory = (
        historical.inventory
        / historical.revenue
        * forecast_revenue
    )

    accounts_payable = (
        historical.accounts_payable
        / historical.revenue
        * forecast_revenue
    )

    # PP&E grows based on historical PP&E
    # and the relationship between capex and depreciation.
    capex = historical.capex or 0
    depreciation = historical.depreciation or 0
    historical_ppe = historical.ppe or 0

    ppe = historical_ppe + capex - depreciation

    # For now, keep debt unchanged.
    debt = historical.debt

    # Equity will initially roll forward from historical equity.
    equity = historical.equity

    # Cash is temporarily carried forward.
    # The cash-flow engine will later determine
    # the actual forecast cash balance.
    cash = historical.cash

    return FinancialPeriod(
        year=historical.year + 1,
        revenue=forecast_revenue,
        cash=cash,
        accounts_receivable=accounts_receivable,
        inventory=inventory,
        ppe=ppe,
        accounts_payable=accounts_payable,
        debt=debt,
        equity=equity,
        capex=capex,
    )