"""Tests for the financial statement models."""
from __future__ import annotations

import pytest

from core.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    FiscalPeriod,
    IncomeStatement,
)


# --------------------------------------------------------------------------- #
# Income statement                                                            #
# --------------------------------------------------------------------------- #
def test_income_derives_gross_profit_and_opex(income_2023: IncomeStatement):
    assert income_2023.gross_profit == pytest.approx(400.0)  # 1000 - 600
    assert income_2023.operating_expenses == pytest.approx(200.0)  # 80 + 120


def test_income_derives_ebit_from_ebitda_and_da(income_2023: IncomeStatement):
    assert income_2023.ebit == pytest.approx(200.0)  # 250 - 50


def test_income_derives_pretax_and_net_income(income_2023: IncomeStatement):
    assert income_2023.pretax_income == pytest.approx(180.0)  # 200 - 20
    assert income_2023.net_income == pytest.approx(144.0)  # 180 - 36


def test_income_margins(income_2023: IncomeStatement):
    assert income_2023.gross_margin == pytest.approx(0.40)
    assert income_2023.ebitda_margin == pytest.approx(0.25)
    assert income_2023.ebit_margin == pytest.approx(0.20)
    assert income_2023.net_margin == pytest.approx(0.144)
    assert income_2023.effective_tax_rate == pytest.approx(0.20)


def test_income_ebitda_derived_from_ebit(fy2023: FiscalPeriod):
    stmt = IncomeStatement(period=fy2023, revenue=1000, ebit=200, depreciation_amortization=50)
    assert stmt.ebitda == pytest.approx(250.0)


def test_income_does_not_overwrite_provided_gross_profit(fy2023: FiscalPeriod):
    stmt = IncomeStatement(period=fy2023, revenue=1000, cost_of_revenue=600, gross_profit=123.0)
    assert stmt.gross_profit == 123.0  # explicit value preserved


def test_income_margins_none_when_no_revenue(fy2023: FiscalPeriod):
    stmt = IncomeStatement(period=fy2023, gross_profit=100.0)
    assert stmt.gross_margin is None


# --------------------------------------------------------------------------- #
# Balance sheet                                                               #
# --------------------------------------------------------------------------- #
def test_balance_total_and_net_debt(balance_2023: BalanceSheet):
    assert balance_2023.total_debt == pytest.approx(360.0)  # 60 + 300
    assert balance_2023.cash_and_investments == pytest.approx(250.0)  # 200 + 50
    assert balance_2023.net_debt == pytest.approx(110.0)  # 360 - 250


def test_balance_working_capital(balance_2023: BalanceSheet):
    assert balance_2023.working_capital == pytest.approx(250.0)  # 450 - 200


def test_balance_identity_holds(balance_2023: BalanceSheet):
    assert balance_2023.balance_residual() == pytest.approx(0.0)
    assert balance_2023.is_balanced() is True


def test_balance_detects_imbalance(fy2023: FiscalPeriod):
    bad = BalanceSheet(
        period=fy2023, total_assets=1000.0, total_liabilities=500.0, total_equity=400.0
    )
    # residual 100 on 1000 assets = 10% > 1% tolerance
    assert bad.is_balanced() is False
    assert bad.balance_residual() == pytest.approx(100.0)


def test_balance_missing_data_returns_none(fy2023: FiscalPeriod):
    empty = BalanceSheet(period=fy2023)
    assert empty.total_debt is None
    assert empty.net_debt is None
    assert empty.balance_residual() is None


# --------------------------------------------------------------------------- #
# Cash flow                                                                   #
# --------------------------------------------------------------------------- #
def test_cashflow_fcf_derived(cashflow_2023: CashFlowStatement):
    assert cashflow_2023.free_cash_flow == pytest.approx(140.0)  # 200 - |−60|
    assert cashflow_2023.capex_abs == pytest.approx(60.0)


def test_cashflow_fcf_not_overwritten(fy2023: FiscalPeriod):
    cf = CashFlowStatement(
        period=fy2023, cash_from_operations=200, capital_expenditures=-60, free_cash_flow=1.0
    )
    assert cf.free_cash_flow == 1.0


# --------------------------------------------------------------------------- #
# Container                                                                   #
# --------------------------------------------------------------------------- #
def test_statements_sorted_and_accessors(statements: FinancialStatements, fy2023: FiscalPeriod):
    assert statements.ticker == "TEST"
    assert statements.periods() == [fy2023]
    assert statements.latest_income().revenue == pytest.approx(1000.0)
    assert statements.income_for(fy2023) is not None
    assert statements.balance_for(fy2023) is not None
    assert statements.cash_flow_for(fy2023) is not None


def test_statements_sorts_multiple_periods(fy2022: FiscalPeriod, fy2023: FiscalPeriod):
    fs = FinancialStatements(
        ticker="test",
        income_statements=[
            IncomeStatement(period=fy2023, revenue=1100),
            IncomeStatement(period=fy2022, revenue=1000),
        ],
    )
    years = [s.period.fiscal_year for s in fs.income_statements]
    assert years == [2022, 2023]  # sorted ascending
    assert fs.latest_income().period.fiscal_year == 2023
