from core.models.financials import FinancialPeriod
from core.forecasting.reconciliation import reconcile_balance_sheet


def test_balanced_balance_sheet():

    financials = FinancialPeriod(
        year=2026,
        cash=100,
        accounts_receivable=150,
        inventory=100,
        ppe=500,
        accounts_payable=120,
        debt=300,
        equity=430,
    )

    result = reconcile_balance_sheet(financials)

    assert result["total_assets"] == 850
    assert result["total_liabilities"] == 420
    assert result["total_liabilities_and_equity"] == 850

    assert result["difference"] == 0
    assert result["is_balanced"] is True


def test_unbalanced_balance_sheet():

    financials = FinancialPeriod(
        year=2026,
        cash=100,
        accounts_receivable=150,
        inventory=100,
        ppe=500,
        accounts_payable=120,
        debt=300,
        equity=400,
    )

    result = reconcile_balance_sheet(financials)

    assert result["difference"] == 30
    assert result["is_balanced"] is False