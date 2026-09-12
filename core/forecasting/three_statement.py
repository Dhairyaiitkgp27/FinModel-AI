"""Linked three-statement forecasting engine.

Given a company's historical :class:`FinancialStatements` and a
:class:`~core.models.forecast.Scenario` of per-year operating drivers, this
engine projects a fully-linked income statement, balance sheet, and cash flow
statement for each forecast year, and returns the unlevered free-cash-flow path
used by the DCF (Phase 6).

**Why the projected balance sheet always balances.** The projection is built so
that Assets = Liabilities + Equity holds by accounting identity every year:

* Revenue-driven operating lines flow to net income.
* Working-capital items (AR/inventory/AP) are set from DSO/DIO/DPO; their change
  is the working-capital line in the cash flow statement.
* Net PP&E rolls forward as ``opening + capex - D&A``.
* The cash flow statement ties operating, investing, and financing flows to the
  change in cash, which becomes the ending cash balance (cash is the plug).
* Equity rolls forward by retained earnings (net income less distributions).
* Every line the engine does not model (other assets/liabilities, goodwill,
  short-term investments, debt) is held constant, and opening equity is set to
  ``opening assets - opening liabilities`` so the very first period reconciles.

Under those rules the year-over-year change in assets equals net income plus the
change in payables, which is exactly the change in liabilities plus equity — so
the sheet balances to the penny. The engine still verifies this numerically and
reports it via :attr:`ForecastResult.balance_checks_passed`.
"""
from __future__ import annotations

from datetime import date

from ..models.base import FiscalPeriod, PeriodType
from ..models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from ..models.forecast import DriverAssumptions, ForecastResult, Scenario
from ..utils.math import clamp, safe_div

DAYS_IN_YEAR = 365.0
DEFAULT_INTEREST_RATE = 0.05
BALANCE_TOLERANCE = 0.01


def _advance_year(d: date | None, years: int) -> date | None:
    if d is None:
        return None
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb in a non-leap target year
        return d.replace(year=d.year + years, day=28)


class _Opening:
    """Opening balance-sheet state used to seed the projection."""

    def __init__(self, balance: BalanceSheet, base_interest_expense: float | None):
        self.cash = balance.cash_and_equivalents or 0.0
        self.sti = balance.short_term_investments or 0.0
        self.ar = balance.accounts_receivable or 0.0
        self.inventory = balance.inventory or 0.0
        self.ppe = balance.net_ppe or 0.0
        self.goodwill = balance.goodwill_and_intangibles or 0.0
        self.ap = balance.accounts_payable or 0.0
        self.short_term_debt = balance.short_term_debt or 0.0
        self.long_term_debt = balance.long_term_debt or 0.0
        self.retained_earnings = balance.retained_earnings

        modeled_current_assets = self.cash + self.sti + self.ar + self.inventory
        total_current_assets = (
            balance.total_current_assets
            if balance.total_current_assets is not None
            else modeled_current_assets
        )
        self.other_current_assets = total_current_assets - modeled_current_assets

        total_assets = (
            balance.total_assets
            if balance.total_assets is not None
            else total_current_assets + self.ppe + self.goodwill
        )
        self.other_non_current_assets = (
            total_assets - total_current_assets - self.ppe - self.goodwill
        )

        modeled_current_liabilities = self.ap + self.short_term_debt
        total_current_liabilities = (
            balance.total_current_liabilities
            if balance.total_current_liabilities is not None
            else modeled_current_liabilities
        )
        self.other_current_liabilities = (
            total_current_liabilities - modeled_current_liabilities
        )

        total_liabilities = (
            balance.total_liabilities
            if balance.total_liabilities is not None
            else total_current_liabilities + self.long_term_debt
        )
        self.other_non_current_liabilities = (
            total_liabilities - total_current_liabilities - self.long_term_debt
        )

        # Opening equity is the balancing figure so the projection reconciles.
        self.equity = total_assets - total_liabilities
        self.total_debt = self.short_term_debt + self.long_term_debt
        self.nwc = self.ar + self.inventory - self.ap
        self.implied_interest_rate = safe_div(base_interest_expense, self.total_debt)


def forecast_statements(
    base: FinancialStatements,
    scenario: Scenario,
    *,
    default_interest_rate: float = DEFAULT_INTEREST_RATE,
    balance_tolerance: float = BALANCE_TOLERANCE,
) -> ForecastResult:
    """Project a linked three-statement model over ``scenario``'s horizon."""
    base_income = base.latest_income()
    base_balance = base.latest_balance()
    if base_income is None or base_income.revenue is None:
        raise ValueError("A base income statement with revenue is required to forecast.")
    if base_balance is None:
        raise ValueError("A base balance sheet is required to build a linked forecast.")

    currency = base.currency
    base_year = base_income.period.fiscal_year
    base_end = base_income.period.period_end or base_balance.period.period_end
    base_shares = base_income.shares_diluted or base_income.shares_basic

    opening = _Opening(base_balance, base_income.interest_expense)

    income_statements: list[IncomeStatement] = []
    balance_sheets: list[BalanceSheet] = []
    cash_flow_statements: list[CashFlowStatement] = []
    revenue_path: list[float] = []
    fcff_path: list[float] = []

    prev_revenue = base_income.revenue
    prev_cash = opening.cash
    prev_ppe = opening.ppe
    prev_nwc = opening.nwc
    prev_equity = opening.equity
    prev_re = opening.retained_earnings

    for i in range(scenario.horizon_years):
        drv: DriverAssumptions = scenario.driver_for_year(i)
        period = FiscalPeriod(
            fiscal_year=base_year + i + 1,
            period_type=PeriodType.ANNUAL,
            period_end=_advance_year(base_end, i + 1),
        )

        # --- Income statement ------------------------------------------ #
        revenue = prev_revenue * (1.0 + drv.revenue_growth)
        cogs = drv.cogs_pct_revenue * revenue
        opex = drv.opex_pct_revenue * revenue
        da = drv.da_pct_revenue * revenue
        ebitda = revenue - cogs - opex
        ebit = ebitda - da

        rate = drv.interest_rate_on_debt
        if rate is None:
            rate = opening.implied_interest_rate
        if rate is None:
            rate = default_interest_rate
        interest = rate * opening.total_debt
        pretax = ebit - interest
        tax = drv.tax_rate * pretax if pretax > 0 else 0.0
        net_income = pretax - tax

        # --- Working capital ------------------------------------------- #
        ar = drv.dso / DAYS_IN_YEAR * revenue
        inventory = drv.dio / DAYS_IN_YEAR * cogs
        ap = drv.dpo / DAYS_IN_YEAR * cogs
        nwc = ar + inventory - ap
        change_nwc = nwc - prev_nwc

        # --- CapEx & PP&E schedule ------------------------------------- #
        capex = drv.capex_pct_revenue * revenue  # positive magnitude
        net_ppe = prev_ppe + capex - da

        # --- Cash flow statement --------------------------------------- #
        cfo = net_income + da - change_nwc
        cfi = -capex
        cff = 0.0  # base engine assumes no dividends, buybacks, or debt change
        net_change_cash = cfo + cfi + cff
        cash = prev_cash + net_change_cash
        fcf_levered = cfo - capex

        # Unlevered free cash flow to the firm, for the DCF engine.
        fcff = ebit * (1.0 - drv.tax_rate) + da - capex - change_nwc

        # --- Equity roll-forward --------------------------------------- #
        equity = prev_equity + net_income  # less distributions (zero here)
        retained_earnings = prev_re + net_income if prev_re is not None else None

        # --- Assemble balance-sheet subtotals -------------------------- #
        total_current_assets = cash + opening.sti + ar + inventory + opening.other_current_assets
        total_assets = (
            total_current_assets + net_ppe + opening.goodwill + opening.other_non_current_assets
        )
        total_current_liabilities = ap + opening.short_term_debt + opening.other_current_liabilities
        total_liabilities = (
            total_current_liabilities + opening.long_term_debt + opening.other_non_current_liabilities
        )

        income_statements.append(
            IncomeStatement(
                period=period,
                currency=currency,
                revenue=revenue,
                cost_of_revenue=cogs,
                operating_expenses=opex,
                ebitda=ebitda,
                depreciation_amortization=da,
                ebit=ebit,
                interest_expense=interest,
                other_income_expense=0.0,
                pretax_income=pretax,
                tax_expense=tax,
                net_income=net_income,
                shares_diluted=base_shares,
                shares_basic=base_shares,
            )
        )
        balance_sheets.append(
            BalanceSheet(
                period=period,
                currency=currency,
                cash_and_equivalents=cash,
                short_term_investments=opening.sti,
                accounts_receivable=ar,
                inventory=inventory,
                other_current_assets=opening.other_current_assets,
                total_current_assets=total_current_assets,
                net_ppe=net_ppe,
                goodwill_and_intangibles=opening.goodwill,
                other_non_current_assets=opening.other_non_current_assets,
                total_assets=total_assets,
                accounts_payable=ap,
                short_term_debt=opening.short_term_debt,
                other_current_liabilities=opening.other_current_liabilities,
                total_current_liabilities=total_current_liabilities,
                long_term_debt=opening.long_term_debt,
                other_non_current_liabilities=opening.other_non_current_liabilities,
                total_liabilities=total_liabilities,
                total_equity=equity,
                retained_earnings=retained_earnings,
            )
        )
        cash_flow_statements.append(
            CashFlowStatement(
                period=period,
                currency=currency,
                net_income=net_income,
                depreciation_amortization=da,
                change_in_working_capital=-change_nwc,  # cash-flow impact
                cash_from_operations=cfo,
                capital_expenditures=-capex,  # as reported (negative)
                cash_from_investing=cfi,
                cash_from_financing=cff,
                free_cash_flow=fcf_levered,
            )
        )

        revenue_path.append(revenue)
        fcff_path.append(fcff)

        prev_revenue = revenue
        prev_cash = cash
        prev_ppe = net_ppe
        prev_nwc = nwc
        prev_equity = equity
        prev_re = retained_earnings

    statements = FinancialStatements(
        ticker=base.ticker,
        currency=currency,
        period_type=PeriodType.ANNUAL,
        income_statements=income_statements,
        balance_sheets=balance_sheets,
        cash_flow_statements=cash_flow_statements,
    )
    balance_checks_passed = all(
        bs.is_balanced(tolerance_ratio=balance_tolerance) is True for bs in balance_sheets
    )

    return ForecastResult(
        ticker=base.ticker,
        scenario=scenario,
        statements=statements,
        free_cash_flows=fcff_path,
        revenue_path=revenue_path,
        balance_checks_passed=balance_checks_passed,
    )


# --------------------------------------------------------------------------- #
# Deriving a base scenario from historical statements                          #
# --------------------------------------------------------------------------- #
def derive_base_drivers(
    base: FinancialStatements,
    revenue_growth: float,
    *,
    default_tax_rate: float = 0.21,
) -> DriverAssumptions:
    """Infer a plausible driver set from the latest historical period.

    Cost, D&A, CapEx and working-capital ratios are taken from the most recent
    reported year; ``revenue_growth`` is supplied by the caller (it is a
    forward-looking assumption, not a historical fact). Missing inputs fall back
    to conservative defaults so the result is always a valid driver set.
    """
    income = base.latest_income()
    balance = base.latest_balance()
    cash_flow = base.latest_cash_flow()
    if income is None or income.revenue in (None, 0):
        raise ValueError("Cannot derive drivers without a base income statement with revenue.")

    revenue = income.revenue
    cogs_pct = _bounded(safe_div(income.cost_of_revenue, revenue), 0.0, 2.0, 0.6)
    opex_pct = _bounded(safe_div(income.operating_expenses, revenue), 0.0, 2.0, 0.2)
    da_pct = _bounded(safe_div(income.depreciation_amortization, revenue), 0.0, 1.0, 0.03)

    etr = income.effective_tax_rate
    tax_rate = clamp(etr, 0.0, 1.0) if etr is not None else default_tax_rate
    if tax_rate is None:
        tax_rate = default_tax_rate

    capex = cash_flow.capex_abs if cash_flow else None
    capex_pct = _bounded(safe_div(capex, revenue), 0.0, 1.0, 0.04)

    dso = _days(balance.accounts_receivable if balance else None, revenue, 45.0)
    dio = _days(balance.inventory if balance else None, income.cost_of_revenue, 60.0)
    dpo = _days(balance.accounts_payable if balance else None, income.cost_of_revenue, 40.0)

    return DriverAssumptions(
        revenue_growth=revenue_growth,
        cogs_pct_revenue=cogs_pct,
        opex_pct_revenue=opex_pct,
        da_pct_revenue=da_pct,
        tax_rate=tax_rate,
        capex_pct_revenue=capex_pct,
        dso=dso,
        dio=dio,
        dpo=dpo,
    )


def build_scenario_from_history(
    base: FinancialStatements,
    revenue_growth: float,
    horizon_years: int = 5,
    *,
    name: str = "Base",
    default_tax_rate: float = 0.21,
) -> Scenario:
    """Convenience: a constant-driver scenario derived from historicals."""
    drivers = derive_base_drivers(base, revenue_growth, default_tax_rate=default_tax_rate)
    return Scenario.from_constant(name, drivers, horizon_years)


def _bounded(value: float | None, low: float, high: float, default: float) -> float:
    if value is None:
        return default
    bounded = clamp(value, low, high)
    return bounded if bounded is not None else default


def _days(numerator: float | None, denominator: float | None, default: float) -> float:
    ratio = safe_div(numerator, denominator)
    if ratio is None:
        return default
    days = ratio * DAYS_IN_YEAR
    return max(days, 0.0)
