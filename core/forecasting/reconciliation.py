from core.models.financials import FinancialPeriod


def reconcile_balance_sheet(
    financials: FinancialPeriod,
) -> dict:
    """
    Reconcile the balance sheet.

    Accounting identity:

        Assets = Liabilities + Equity

    Returns totals, difference, and balance status.
    """

    total_assets = (
        (financials.cash or 0)
        + (financials.accounts_receivable or 0)
        + (financials.inventory or 0)
        + (financials.ppe or 0)
    )

    total_liabilities = (
        (financials.accounts_payable or 0)
        + (financials.debt or 0)
    )

    total_liabilities_and_equity = (
        total_liabilities
        + (financials.equity or 0)
    )

    difference = (
        total_assets
        - total_liabilities_and_equity
    )

    is_balanced = abs(difference) < 1e-6

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": financials.equity or 0,
        "total_liabilities_and_equity": total_liabilities_and_equity,
        "difference": difference,
        "is_balanced": is_balanced,
    }