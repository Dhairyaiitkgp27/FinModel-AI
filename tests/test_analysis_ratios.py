"""Tests for the deterministic ratio engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.analysis import compute_ratios, compute_ratios_for_dataset
from core.data import LocalSampleProvider
from core.models import (
    BalanceSheet,
    FinancialStatements,
    FiscalPeriod,
    IncomeStatement,
    PeriodType,
    RatioAnalysis,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def test_single_period_ratios_exact(statements: FinancialStatements):
    analysis = compute_ratios(statements)
    assert isinstance(analysis, RatioAnalysis)
    r = analysis.latest
    assert r is not None

    # Margins
    assert r.gross_margin == pytest.approx(0.40)
    assert r.ebitda_margin == pytest.approx(0.25)
    assert r.ebit_margin == pytest.approx(0.20)
    assert r.net_margin == pytest.approx(0.144)
    assert r.fcf_margin == pytest.approx(0.14)

    # Liquidity
    assert r.current_ratio == pytest.approx(2.25)
    assert r.quick_ratio == pytest.approx((450 - 80) / 200)

    # Leverage (EBITDA = 250; total debt = 360; net debt = 110)
    assert r.debt_to_ebitda == pytest.approx(360 / 250)
    assert r.net_debt_to_ebitda == pytest.approx(110 / 250)
    assert r.working_capital == pytest.approx(250.0)

    # Cash conversion (FCF 140 / NI 144)
    assert r.cash_conversion == pytest.approx(140 / 144)


def test_returns_exact(statements: FinancialStatements):
    r = compute_ratios(statements).latest
    # ROE = net income 144 / ending equity 400 (single period, no averaging)
    assert r.roe == pytest.approx(144 / 400)
    # ROIC = NOPAT / invested capital
    #   effective tax = 36/180 = 0.20 -> NOPAT = 200 * 0.80 = 160
    #   invested = equity 400 + debt 360 - cash&investments 250 = 510
    assert r.roic == pytest.approx(160 / 510)


def test_working_capital_days_exact(statements: FinancialStatements):
    r = compute_ratios(statements).latest
    assert r.days_sales_outstanding == pytest.approx(365 * 120 / 1000)
    assert r.days_inventory_outstanding == pytest.approx(365 * 80 / 600)
    assert r.days_payable_outstanding == pytest.approx(365 * 90 / 600)
    assert r.cash_conversion_cycle == pytest.approx(
        365 * 120 / 1000 + 365 * 80 / 600 - 365 * 90 / 600
    )


def test_single_period_growth_is_none(statements: FinancialStatements):
    r = compute_ratios(statements).latest
    assert r.revenue_growth is None


def test_revenue_growth_across_periods():
    fy22 = FiscalPeriod(fiscal_year=2022, period_type=PeriodType.ANNUAL)
    fy23 = FiscalPeriod(fiscal_year=2023, period_type=PeriodType.ANNUAL)
    stmts = FinancialStatements(
        ticker="TEST",
        income_statements=[
            IncomeStatement(period=fy22, revenue=1000.0, cost_of_revenue=600.0),
            IncomeStatement(period=fy23, revenue=1100.0, cost_of_revenue=650.0),
        ],
    )
    analysis = compute_ratios(stmts)
    assert analysis.periods[0].revenue_growth is None  # first period
    assert analysis.periods[1].revenue_growth == pytest.approx(0.10)  # 1000 -> 1100
    # series extractor returns values chronologically
    assert analysis.series("revenue_growth") == [None, pytest.approx(0.10)]


def test_missing_inputs_yield_none():
    period = FiscalPeriod(fiscal_year=2023)
    # income with no balance/cash flow -> leverage & liquidity undefined
    stmts = FinancialStatements(
        ticker="TEST",
        income_statements=[IncomeStatement(period=period, revenue=500.0, cost_of_revenue=300.0)],
    )
    r = compute_ratios(stmts).latest
    assert r.gross_margin == pytest.approx(0.40)
    assert r.current_ratio is None
    assert r.debt_to_ebitda is None
    assert r.roe is None
    assert r.days_sales_outstanding is None


def test_roe_uses_average_equity_when_prior_available():
    fy22 = FiscalPeriod(fiscal_year=2022)
    fy23 = FiscalPeriod(fiscal_year=2023)
    stmts = FinancialStatements(
        ticker="TEST",
        income_statements=[
            IncomeStatement(period=fy22, revenue=1000.0, net_income=100.0),
            IncomeStatement(period=fy23, revenue=1100.0, net_income=120.0),
        ],
        balance_sheets=[
            BalanceSheet(period=fy22, total_equity=400.0, total_assets=800.0, total_liabilities=400.0),
            BalanceSheet(period=fy23, total_equity=600.0, total_assets=1000.0, total_liabilities=400.0),
        ],
    )
    r = compute_ratios(stmts).periods[1]
    # average equity = (400 + 600) / 2 = 500 -> ROE = 120 / 500
    assert r.roe == pytest.approx(120 / 500)


def test_ratios_on_sample_dataset_are_reasonable():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    analysis = compute_ratios_for_dataset(ds)
    assert len(analysis.periods) == 3
    latest = analysis.latest
    # Apple FY2023 sanity: ~44% gross margin, positive growth from FY2022 is negative
    # (revenue fell 394bn -> 383bn), current ratio < 1, strong returns.
    assert latest.gross_margin == pytest.approx(0.441, abs=0.01)
    assert latest.revenue_growth == pytest.approx((383285 - 394328) / 394328, abs=1e-4)
    assert latest.roe is not None and latest.roe > 0.5  # Apple's ROE is very high
    assert latest.days_sales_outstanding is not None
