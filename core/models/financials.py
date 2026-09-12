"""Normalised financial statement models.

All external provider data is normalised into these schemas so the rest of the
platform never touches raw yfinance frames. Each statement carries a
:class:`FiscalPeriod` and gently backfills derived line items (gross profit,
EBIT/EBITDA bridge, free cash flow) *only when the inputs exist and the field
is missing* — never overwriting reported values.

Sign conventions (documented so downstream engines can rely on them):

* ``interest_expense`` is stored as a positive expense magnitude.
* ``other_income_expense`` is positive when it is net income.
* ``capital_expenditures`` is stored as reported (typically negative). Use
  :meth:`CashFlowStatement.capex_abs` for the positive magnitude.
"""
from __future__ import annotations

from pydantic import model_validator

from ..utils.math import safe_div
from .base import Currency, FinBaseModel, FiscalPeriod, PeriodType


class IncomeStatement(FinBaseModel):
    """A single-period income statement."""

    period: FiscalPeriod
    currency: Currency = Currency.USD

    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    research_development: float | None = None
    selling_general_admin: float | None = None
    operating_expenses: float | None = None
    ebitda: float | None = None
    depreciation_amortization: float | None = None
    ebit: float | None = None  # operating income
    interest_expense: float | None = None
    other_income_expense: float | None = None
    pretax_income: float | None = None
    tax_expense: float | None = None
    net_income: float | None = None
    shares_basic: float | None = None
    shares_diluted: float | None = None

    @model_validator(mode="after")
    def _derive(self) -> IncomeStatement:
        if self.gross_profit is None and self.revenue is not None and self.cost_of_revenue is not None:
            self.gross_profit = self.revenue - self.cost_of_revenue
        if self.operating_expenses is None:
            parts = [p for p in (self.research_development, self.selling_general_admin) if p is not None]
            if parts:
                self.operating_expenses = sum(parts)
        if self.ebit is None and self.ebitda is not None and self.depreciation_amortization is not None:
            self.ebit = self.ebitda - self.depreciation_amortization
        if self.ebitda is None and self.ebit is not None and self.depreciation_amortization is not None:
            self.ebitda = self.ebit + self.depreciation_amortization
        if self.pretax_income is None and self.ebit is not None and self.interest_expense is not None:
            self.pretax_income = self.ebit - self.interest_expense + (self.other_income_expense or 0.0)
        if self.net_income is None and self.pretax_income is not None and self.tax_expense is not None:
            self.net_income = self.pretax_income - self.tax_expense
        return self

    # Margin helpers -------------------------------------------------- #
    @property
    def gross_margin(self) -> float | None:
        return safe_div(self.gross_profit, self.revenue)

    @property
    def ebitda_margin(self) -> float | None:
        return safe_div(self.ebitda, self.revenue)

    @property
    def ebit_margin(self) -> float | None:
        return safe_div(self.ebit, self.revenue)

    @property
    def net_margin(self) -> float | None:
        return safe_div(self.net_income, self.revenue)

    @property
    def effective_tax_rate(self) -> float | None:
        return safe_div(self.tax_expense, self.pretax_income)


class BalanceSheet(FinBaseModel):
    """A single-period balance sheet."""

    period: FiscalPeriod
    currency: Currency = Currency.USD

    # Assets
    cash_and_equivalents: float | None = None
    short_term_investments: float | None = None
    accounts_receivable: float | None = None
    inventory: float | None = None
    other_current_assets: float | None = None
    total_current_assets: float | None = None
    net_ppe: float | None = None
    goodwill_and_intangibles: float | None = None
    other_non_current_assets: float | None = None
    total_assets: float | None = None

    # Liabilities
    accounts_payable: float | None = None
    short_term_debt: float | None = None
    other_current_liabilities: float | None = None
    total_current_liabilities: float | None = None
    long_term_debt: float | None = None
    other_non_current_liabilities: float | None = None
    total_liabilities: float | None = None

    # Equity
    total_equity: float | None = None
    retained_earnings: float | None = None

    @property
    def total_debt(self) -> float | None:
        parts = [d for d in (self.short_term_debt, self.long_term_debt) if d is not None]
        return sum(parts) if parts else None

    @property
    def cash_and_investments(self) -> float | None:
        parts = [c for c in (self.cash_and_equivalents, self.short_term_investments) if c is not None]
        return sum(parts) if parts else None

    @property
    def net_debt(self) -> float | None:
        debt = self.total_debt
        cash = self.cash_and_investments
        if debt is None and cash is None:
            return None
        return (debt or 0.0) - (cash or 0.0)

    @property
    def working_capital(self) -> float | None:
        if self.total_current_assets is None or self.total_current_liabilities is None:
            return None
        return self.total_current_assets - self.total_current_liabilities

    def balance_residual(self) -> float | None:
        """Assets - (Liabilities + Equity). Should be ~0 for a clean balance sheet."""
        if self.total_assets is None or self.total_liabilities is None or self.total_equity is None:
            return None
        return self.total_assets - (self.total_liabilities + self.total_equity)

    def is_balanced(self, tolerance_ratio: float = 0.01) -> bool | None:
        """Whether Assets == Liabilities + Equity within ``tolerance_ratio`` of assets."""
        residual = self.balance_residual()
        if residual is None or self.total_assets in (None, 0):
            return None
        return abs(residual) <= abs(self.total_assets) * tolerance_ratio


class CashFlowStatement(FinBaseModel):
    """A single-period cash flow statement."""

    period: FiscalPeriod
    currency: Currency = Currency.USD

    net_income: float | None = None
    depreciation_amortization: float | None = None
    change_in_working_capital: float | None = None
    stock_based_compensation: float | None = None
    cash_from_operations: float | None = None
    capital_expenditures: float | None = None  # as reported (usually negative)
    cash_from_investing: float | None = None
    debt_issued: float | None = None
    debt_repaid: float | None = None
    dividends_paid: float | None = None
    share_repurchase: float | None = None
    cash_from_financing: float | None = None
    free_cash_flow: float | None = None

    @model_validator(mode="after")
    def _derive(self) -> CashFlowStatement:
        if (
            self.free_cash_flow is None
            and self.cash_from_operations is not None
            and self.capital_expenditures is not None
        ):
            # capex stored as reported; subtract its magnitude
            self.free_cash_flow = self.cash_from_operations - abs(self.capital_expenditures)
        return self

    @property
    def capex_abs(self) -> float | None:
        """Capital expenditure as a positive magnitude."""
        return abs(self.capital_expenditures) if self.capital_expenditures is not None else None


class FinancialStatements(FinBaseModel):
    """Container aligning the three statements across periods for one company."""

    ticker: str
    currency: Currency = Currency.USD
    period_type: PeriodType = PeriodType.ANNUAL
    income_statements: list[IncomeStatement] = []
    balance_sheets: list[BalanceSheet] = []
    cash_flow_statements: list[CashFlowStatement] = []

    @model_validator(mode="after")
    def _sort(self) -> FinancialStatements:
        self.ticker = self.ticker.strip().upper()
        self.income_statements = sorted(self.income_statements, key=lambda s: s.period.sort_key)
        self.balance_sheets = sorted(self.balance_sheets, key=lambda s: s.period.sort_key)
        self.cash_flow_statements = sorted(self.cash_flow_statements, key=lambda s: s.period.sort_key)
        return self

    # Accessors ------------------------------------------------------- #
    def periods(self) -> list[FiscalPeriod]:
        """Union of all periods present in any statement, chronologically sorted."""
        seen = {s.period for s in self.income_statements}
        seen |= {s.period for s in self.balance_sheets}
        seen |= {s.period for s in self.cash_flow_statements}
        return sorted(seen, key=lambda p: p.sort_key)

    def income_for(self, period: FiscalPeriod) -> IncomeStatement | None:
        return next((s for s in self.income_statements if s.period == period), None)

    def balance_for(self, period: FiscalPeriod) -> BalanceSheet | None:
        return next((s for s in self.balance_sheets if s.period == period), None)

    def cash_flow_for(self, period: FiscalPeriod) -> CashFlowStatement | None:
        return next((s for s in self.cash_flow_statements if s.period == period), None)

    def latest_income(self) -> IncomeStatement | None:
        return self.income_statements[-1] if self.income_statements else None

    def latest_balance(self) -> BalanceSheet | None:
        return self.balance_sheets[-1] if self.balance_sheets else None

    def latest_cash_flow(self) -> CashFlowStatement | None:
        return self.cash_flow_statements[-1] if self.cash_flow_statements else None
