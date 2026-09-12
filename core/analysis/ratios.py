"""Deterministic financial-ratio engine.

Given a :class:`~core.models.financials.FinancialStatements` container, this
module computes a :class:`~core.models.analysis.RatioAnalysis`: a chronological
series of per-period profitability, return, liquidity, leverage, and
working-capital ratios. Every figure is derived here in plain Python from the
reported statements — the LLM never performs these calculations.

All arithmetic is ``None``-safe via :mod:`core.utils.math`: a ratio is ``None``
whenever its inputs are missing, rather than raising or guessing. Definitions
are documented on each helper so downstream consumers know exactly what a field
means.
"""
from __future__ import annotations

from ..models.analysis import PeriodRatios, RatioAnalysis
from ..models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from ..utils.math import clamp, pct_change, safe_div

# Days in a year used for working-capital day metrics (DSO/DIO/DPO).
DAYS_IN_YEAR = 365.0


def _effective_tax_rate(income: IncomeStatement, default_tax_rate: float) -> float:
    """Effective tax rate clamped to [0, 1], falling back to ``default_tax_rate``."""
    etr = income.effective_tax_rate
    if etr is None:
        return default_tax_rate
    clamped = clamp(etr, 0.0, 1.0)
    return clamped if clamped is not None else default_tax_rate


def _returns(
    income: IncomeStatement | None,
    balance: BalanceSheet | None,
    prior_balance: BalanceSheet | None,
    default_tax_rate: float,
) -> tuple[float | None, float | None]:
    """Return on equity and return on invested capital.

    * ROE = net income / average equity (ending equity when no prior period).
    * ROIC = NOPAT / invested capital, where NOPAT = EBIT x (1 - tax rate) and
      invested capital = total debt + total equity - cash & investments
      (excess cash netted out).
    """
    roe: float | None = None
    roic: float | None = None
    if income is None or balance is None:
        return roe, roic

    # ROE -------------------------------------------------------------- #
    equity = balance.total_equity
    if equity is not None and prior_balance is not None and prior_balance.total_equity is not None:
        equity = (equity + prior_balance.total_equity) / 2.0
    roe = safe_div(income.net_income, equity)

    # ROIC ------------------------------------------------------------- #
    if income.ebit is not None and balance.total_equity is not None:
        tax_rate = _effective_tax_rate(income, default_tax_rate)
        nopat = income.ebit * (1.0 - tax_rate)
        invested = balance.total_equity + (balance.total_debt or 0.0)
        invested -= balance.cash_and_investments or 0.0
        roic = safe_div(nopat, invested)

    return roe, roic


def _quick_ratio(balance: BalanceSheet) -> float | None:
    """Acid-test ratio: (current assets - inventory) / current liabilities."""
    if balance.total_current_assets is None:
        return None
    liquid = balance.total_current_assets - (balance.inventory or 0.0)
    return safe_div(liquid, balance.total_current_liabilities)


def _working_capital_days(
    income: IncomeStatement | None, balance: BalanceSheet | None
) -> tuple[float | None, float | None, float | None, float | None]:
    """Return (DSO, DIO, DPO, cash-conversion-cycle)."""
    if income is None or balance is None:
        return None, None, None, None

    dso = safe_div(balance.accounts_receivable, income.revenue)
    dso = dso * DAYS_IN_YEAR if dso is not None else None

    dio = safe_div(balance.inventory, income.cost_of_revenue)
    dio = dio * DAYS_IN_YEAR if dio is not None else None

    dpo = safe_div(balance.accounts_payable, income.cost_of_revenue)
    dpo = dpo * DAYS_IN_YEAR if dpo is not None else None

    ccc: float | None = None
    if dso is not None and dio is not None and dpo is not None:
        ccc = dso + dio - dpo

    return dso, dio, dpo, ccc


def _period_ratios(
    period,
    income: IncomeStatement | None,
    balance: BalanceSheet | None,
    cash_flow: CashFlowStatement | None,
    prior_income: IncomeStatement | None,
    prior_balance: BalanceSheet | None,
    default_tax_rate: float,
) -> PeriodRatios:
    # Growth (needs a prior period's revenue) -------------------------- #
    revenue_growth = None
    if income is not None and prior_income is not None:
        revenue_growth = pct_change(income.revenue, prior_income.revenue)

    # Margins (reuse the statement's own margin properties) ------------ #
    gross_margin = income.gross_margin if income else None
    ebitda_margin = income.ebitda_margin if income else None
    ebit_margin = income.ebit_margin if income else None
    net_margin = income.net_margin if income else None

    fcf = cash_flow.free_cash_flow if cash_flow else None
    fcf_margin = safe_div(fcf, income.revenue) if income else None
    cash_conversion = safe_div(fcf, income.net_income) if income else None

    # Returns ---------------------------------------------------------- #
    roe, roic = _returns(income, balance, prior_balance, default_tax_rate)

    # Liquidity / leverage / working capital --------------------------- #
    current_ratio = quick_ratio = None
    debt_to_ebitda = net_debt_to_ebitda = working_capital = None
    if balance is not None:
        current_ratio = safe_div(balance.total_current_assets, balance.total_current_liabilities)
        quick_ratio = _quick_ratio(balance)
        working_capital = balance.working_capital
        if income is not None:
            debt_to_ebitda = safe_div(balance.total_debt, income.ebitda)
            net_debt_to_ebitda = safe_div(balance.net_debt, income.ebitda)

    dso, dio, dpo, ccc = _working_capital_days(income, balance)

    return PeriodRatios(
        period=period,
        revenue_growth=revenue_growth,
        gross_margin=gross_margin,
        ebitda_margin=ebitda_margin,
        ebit_margin=ebit_margin,
        net_margin=net_margin,
        fcf_margin=fcf_margin,
        roe=roe,
        roic=roic,
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        debt_to_ebitda=debt_to_ebitda,
        net_debt_to_ebitda=net_debt_to_ebitda,
        working_capital=working_capital,
        cash_conversion=cash_conversion,
        days_sales_outstanding=dso,
        days_inventory_outstanding=dio,
        days_payable_outstanding=dpo,
        cash_conversion_cycle=ccc,
    )


def compute_ratios(
    statements: FinancialStatements, default_tax_rate: float = 0.21
) -> RatioAnalysis:
    """Compute a chronological :class:`RatioAnalysis` for one company.

    Periods are taken from the union of all statements and processed in
    chronological order so that growth and average-equity metrics reference the
    immediately preceding available period.
    """
    results: list[PeriodRatios] = []
    prior_income: IncomeStatement | None = None
    prior_balance: BalanceSheet | None = None

    for period in statements.periods():
        income = statements.income_for(period)
        balance = statements.balance_for(period)
        cash_flow = statements.cash_flow_for(period)

        results.append(
            _period_ratios(
                period,
                income,
                balance,
                cash_flow,
                prior_income,
                prior_balance,
                default_tax_rate,
            )
        )

        if income is not None:
            prior_income = income
        if balance is not None:
            prior_balance = balance

    return RatioAnalysis(ticker=statements.ticker, periods=results)


def compute_ratios_for_dataset(dataset, default_tax_rate: float = 0.21) -> RatioAnalysis:
    """Convenience wrapper computing ratios from a :class:`CompanyDataset`."""
    return compute_ratios(dataset.financials, default_tax_rate=default_tax_rate)
