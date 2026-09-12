"""Shared fixtures for the FinModel AI test suite."""
from __future__ import annotations

import pytest

from core.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    FiscalPeriod,
    IncomeStatement,
    PeriodType,
)


@pytest.fixture
def fy2022() -> FiscalPeriod:
    return FiscalPeriod(fiscal_year=2022, period_type=PeriodType.ANNUAL)


@pytest.fixture
def fy2023() -> FiscalPeriod:
    return FiscalPeriod(fiscal_year=2023, period_type=PeriodType.ANNUAL)


@pytest.fixture
def income_2023(fy2023: FiscalPeriod) -> IncomeStatement:
    return IncomeStatement(
        period=fy2023,
        revenue=1000.0,
        cost_of_revenue=600.0,
        research_development=80.0,
        selling_general_admin=120.0,
        ebitda=250.0,
        depreciation_amortization=50.0,
        interest_expense=20.0,
        tax_expense=36.0,
        shares_diluted=100.0,
    )


@pytest.fixture
def balance_2023(fy2023: FiscalPeriod) -> BalanceSheet:
    return BalanceSheet(
        period=fy2023,
        cash_and_equivalents=200.0,
        short_term_investments=50.0,
        accounts_receivable=120.0,
        inventory=80.0,
        total_current_assets=450.0,
        net_ppe=400.0,
        total_assets=900.0,
        accounts_payable=90.0,
        short_term_debt=60.0,
        total_current_liabilities=200.0,
        long_term_debt=300.0,
        total_liabilities=500.0,
        total_equity=400.0,
        retained_earnings=250.0,
    )


@pytest.fixture
def cashflow_2023(fy2023: FiscalPeriod) -> CashFlowStatement:
    return CashFlowStatement(
        period=fy2023,
        net_income=144.0,
        depreciation_amortization=50.0,
        change_in_working_capital=-10.0,
        cash_from_operations=200.0,
        capital_expenditures=-60.0,
    )


@pytest.fixture
def statements(
    income_2023: IncomeStatement,
    balance_2023: BalanceSheet,
    cashflow_2023: CashFlowStatement,
) -> FinancialStatements:
    return FinancialStatements(
        ticker="TEST",
        income_statements=[income_2023],
        balance_sheets=[balance_2023],
        cash_flow_statements=[cashflow_2023],
    )
