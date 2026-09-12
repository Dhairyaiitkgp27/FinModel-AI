"""Tests for the post-normalisation validation layer."""
from __future__ import annotations

from pathlib import Path

from core.data import LocalSampleProvider, validate_dataset
from core.data.dataset import CompanyDataset
from core.models import (
    BalanceSheet,
    CompanyProfile,
    FinancialStatements,
    FiscalPeriod,
    IncomeStatement,
    PriceHistory,
    Severity,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def test_sample_dataset_is_valid():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    report = validate_dataset(ds)
    assert report.is_valid is True
    assert report.issues == []


def _dataset_with(income=None, balance=None, market_data=None) -> CompanyDataset:
    return CompanyDataset(
        profile=CompanyProfile(ticker="TST"),
        market_data=market_data,
        financials=FinancialStatements(
            ticker="TST",
            income_statements=income or [],
            balance_sheets=balance or [],
        ),
        prices=PriceHistory(ticker="TST"),
        source="test",
    )


def test_no_income_statements_is_high_severity():
    report = validate_dataset(_dataset_with(income=[]))
    codes = {i.code: i.severity for i in report.issues}
    assert codes.get("no_income_statements") == Severity.HIGH
    assert report.is_valid is False


def test_missing_revenue_flagged():
    period = FiscalPeriod(fiscal_year=2023)
    income = [IncomeStatement(period=period, net_income=10.0)]  # no revenue
    report = validate_dataset(_dataset_with(income=income))
    assert any(i.code == "missing_revenue" and i.severity == Severity.HIGH for i in report.issues)


def test_unbalanced_balance_sheet_flagged():
    period = FiscalPeriod(fiscal_year=2023)
    income = [IncomeStatement(period=period, revenue=100.0, net_income=10.0)]
    bad_bs = BalanceSheet(
        period=period,
        total_assets=1000.0,
        total_liabilities=500.0,
        total_equity=400.0,  # 500 + 400 != 1000
    )
    report = validate_dataset(_dataset_with(income=income, balance=[bad_bs]))
    issue = next((i for i in report.issues if i.code == "balance_sheet_unbalanced"), None)
    assert issue is not None
    assert issue.severity == Severity.MEDIUM
    assert issue.period == "FY2023"


def test_no_market_data_flagged_medium():
    period = FiscalPeriod(fiscal_year=2023)
    income = [IncomeStatement(period=period, revenue=100.0, net_income=10.0)]
    report = validate_dataset(_dataset_with(income=income, market_data=None))
    assert any(i.code == "no_market_data" and i.severity == Severity.MEDIUM for i in report.issues)
    # medium issues alone do not make the dataset invalid
    assert report.is_valid is True


def test_report_summary_counts():
    report = validate_dataset(_dataset_with(income=[]))
    summary = report.summary()
    assert "TST" in summary
    assert "high" in summary
