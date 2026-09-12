"""Tests for the linked three-statement forecasting engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.data import LocalSampleProvider
from core.forecasting import (
    build_scenario_from_history,
    derive_base_drivers,
    forecast_statements,
)
from core.models import (
    BalanceSheet,
    DriverAssumptions,
    FinancialStatements,
    FiscalPeriod,
    IncomeStatement,
    PeriodType,
    Scenario,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


@pytest.fixture
def base() -> FinancialStatements:
    """A small, balanced one-period history to project from."""
    period = FiscalPeriod(fiscal_year=2023, period_type=PeriodType.ANNUAL)
    income = IncomeStatement(
        period=period, revenue=1000.0, interest_expense=20.0, shares_diluted=100.0
    )
    balance = BalanceSheet(
        period=period,
        cash_and_equivalents=100.0,
        accounts_receivable=100.0,
        inventory=50.0,
        total_current_assets=300.0,  # implies 50 "other current assets"
        net_ppe=500.0,
        total_assets=1000.0,  # implies 200 "other non-current assets"
        accounts_payable=80.0,
        total_current_liabilities=200.0,  # implies 120 "other current liabilities"
        long_term_debt=300.0,
        total_liabilities=600.0,  # implies 100 "other non-current liabilities"
        total_equity=400.0,
    )
    return FinancialStatements(
        ticker="TEST", income_statements=[income], balance_sheets=[balance]
    )


@pytest.fixture
def drivers() -> DriverAssumptions:
    return DriverAssumptions(
        revenue_growth=0.10,
        cogs_pct_revenue=0.60,
        opex_pct_revenue=0.20,
        da_pct_revenue=0.05,
        tax_rate=0.25,
        capex_pct_revenue=0.08,
        dso=36.5,  # 36.5/365 = 0.1 of revenue
        dio=36.5,
        dpo=36.5,
        interest_rate_on_debt=0.05,
    )


@pytest.fixture
def scenario(drivers: DriverAssumptions) -> Scenario:
    return Scenario.from_constant("Base", drivers, horizon_years=3)


def test_income_statement_year1_mechanics(base, scenario):
    result = forecast_statements(base, scenario)
    inc = result.statements.income_statements[0]
    assert inc.period.label() == "FY2024"
    assert inc.revenue == pytest.approx(1100.0)  # 1000 * 1.10
    assert inc.cost_of_revenue == pytest.approx(660.0)
    assert inc.operating_expenses == pytest.approx(220.0)
    assert inc.depreciation_amortization == pytest.approx(55.0)
    assert inc.ebitda == pytest.approx(220.0)  # 1100 - 660 - 220
    assert inc.ebit == pytest.approx(165.0)  # 220 - 55
    assert inc.interest_expense == pytest.approx(15.0)  # 5% of 300 debt
    assert inc.pretax_income == pytest.approx(150.0)
    assert inc.tax_expense == pytest.approx(37.5)  # 25% of 150
    assert inc.net_income == pytest.approx(112.5)


def test_working_capital_and_ppe_schedule(base, scenario):
    result = forecast_statements(base, scenario)
    bs = result.statements.balance_sheets[0]
    assert bs.accounts_receivable == pytest.approx(110.0)  # 0.1 * revenue 1100
    assert bs.inventory == pytest.approx(66.0)  # 0.1 * COGS 660
    assert bs.accounts_payable == pytest.approx(66.0)  # 0.1 * COGS 660
    # PP&E rolls forward: opening 500 + capex 88 - D&A 55 = 533
    assert bs.net_ppe == pytest.approx(533.0)


def test_cash_flow_and_fcff(base, scenario):
    result = forecast_statements(base, scenario)
    cf = result.statements.cash_flow_statements[0]
    bs = result.statements.balance_sheets[0]
    # CFO = NI 112.5 + D&A 55 - change in NWC 40 = 127.5
    assert cf.cash_from_operations == pytest.approx(127.5)
    assert cf.capital_expenditures == pytest.approx(-88.0)
    # ending cash = opening 100 + (127.5 - 88) = 139.5
    assert bs.cash_and_equivalents == pytest.approx(139.5)
    # unlevered FCFF = EBIT*(1-tax) + D&A - capex - dNWC = 165*0.75 + 55 - 88 - 40
    assert result.free_cash_flows[0] == pytest.approx(50.75)


def test_every_projected_year_balances(base, scenario):
    result = forecast_statements(base, scenario)
    assert result.balance_checks_passed is True
    for bs in result.statements.balance_sheets:
        residual = bs.balance_residual()
        assert residual is not None
        assert abs(residual) < 1e-6  # balances to the penny
        assert bs.is_balanced() is True


def test_revenue_path_compounds(base, scenario):
    result = forecast_statements(base, scenario)
    assert result.revenue_path == [
        pytest.approx(1100.0),
        pytest.approx(1210.0),  # 1100 * 1.10
        pytest.approx(1331.0),  # 1210 * 1.10
    ]
    assert len(result.statements.income_statements) == 3


def test_equity_rolls_by_net_income(base, scenario):
    result = forecast_statements(base, scenario)
    bs0 = result.statements.balance_sheets[0]
    # opening equity 400 + year-1 net income 112.5 = 512.5
    assert bs0.total_equity == pytest.approx(512.5)


def test_missing_base_balance_raises():
    period = FiscalPeriod(fiscal_year=2023)
    base = FinancialStatements(
        ticker="TEST",
        income_statements=[IncomeStatement(period=period, revenue=1000.0)],
    )
    drivers = DriverAssumptions(
        revenue_growth=0.05, cogs_pct_revenue=0.6, opex_pct_revenue=0.2,
        da_pct_revenue=0.05, tax_rate=0.2, capex_pct_revenue=0.05, dso=45, dio=60, dpo=40,
    )
    with pytest.raises(ValueError):
        forecast_statements(base, Scenario.from_constant("Base", drivers, 3))


def test_derive_base_drivers_from_history(statements: FinancialStatements):
    drv = derive_base_drivers(statements, revenue_growth=0.05)
    assert drv.revenue_growth == pytest.approx(0.05)
    assert drv.cogs_pct_revenue == pytest.approx(0.60)  # 600 / 1000
    assert drv.opex_pct_revenue == pytest.approx(0.20)  # (80 + 120) / 1000
    assert drv.da_pct_revenue == pytest.approx(0.05)  # 50 / 1000
    assert drv.tax_rate == pytest.approx(0.20)  # effective 36 / 180
    assert drv.capex_pct_revenue == pytest.approx(0.06)  # 60 / 1000
    assert drv.dso == pytest.approx(365 * 120 / 1000)
    assert drv.dio == pytest.approx(365 * 80 / 600)
    assert drv.dpo == pytest.approx(365 * 90 / 600)


def test_forecast_on_sample_dataset_balances():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    scenario = build_scenario_from_history(ds.financials, revenue_growth=0.06, horizon_years=5)
    result = forecast_statements(ds.financials, scenario)
    assert result.balance_checks_passed is True
    assert len(result.statements.income_statements) == 5
    assert len(result.free_cash_flows) == 5
    # revenue should grow at 6% off the ~383bn base
    assert result.revenue_path[0] == pytest.approx(383_285e6 * 1.06, rel=1e-6)
    assert all(f > 0 for f in result.free_cash_flows)
