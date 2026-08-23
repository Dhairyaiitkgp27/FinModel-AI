from core.models.financials import FinancialPeriod


def forecast_cash_flow(
    historical: FinancialPeriod,
    forecast: FinancialPeriod,
    net_income: float,
) -> dict:
    """
    Forecast the cash flow statement for one period.

    Returns a dictionary containing:
    - Cash Flow from Operations (CFO)
    - Cash Flow from Investing (CFI)
    - Cash Flow from Financing (CFF)
    - Net Change in Cash
    - Ending Cash
    """

    # -----------------------------
    # 1. Cash Flow from Operations
    # -----------------------------

    depreciation = forecast.depreciation or 0

    # Changes in working capital
    change_ar = (
        (forecast.accounts_receivable or 0)
        - (historical.accounts_receivable or 0)
    )

    change_inventory = (
        (forecast.inventory or 0)
        - (historical.inventory or 0)
    )

    change_ap = (
        (forecast.accounts_payable or 0)
        - (historical.accounts_payable or 0)
    )

    cfo = (
        net_income
        + depreciation
        - change_ar
        - change_inventory
        + change_ap
    )

    # -----------------------------
    # 2. Cash Flow from Investing
    # -----------------------------

    capex = forecast.capex or 0

    cfi = -capex

    # -----------------------------
    # 3. Cash Flow from Financing
    # -----------------------------

    debt_change = (
        (forecast.debt or 0)
        - (historical.debt or 0)
    )

    cff = debt_change

    # -----------------------------
    # 4. Net Change in Cash
    # -----------------------------

    net_change_in_cash = cfo + cfi + cff

    # -----------------------------
    # 5. Ending Cash
    # -----------------------------

    beginning_cash = historical.cash or 0

    ending_cash = beginning_cash + net_change_in_cash

    return {
        "cfo": cfo,
        "cfi": cfi,
        "cff": cff,
        "net_change_in_cash": net_change_in_cash,
        "ending_cash": ending_cash,
    }