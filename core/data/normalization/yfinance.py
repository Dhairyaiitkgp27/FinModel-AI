"""Normalise raw yfinance objects into the platform's typed models.

yfinance exposes company data as a ``.info`` dict and several statement
DataFrames (``income_stmt``, ``balance_sheet``, ``cashflow``) whose rows are
line-item labels and whose columns are period-end timestamps. The exact labels
drift between yfinance versions, so every field maps to a *list of candidate
labels* and we take the first that is present.

These functions deliberately avoid importing pandas: they operate structurally
on the frame objects passed in (``.index``/``.columns`` and label lookup),
treating NaN via self-inequality. That keeps the local-only install path free of
a hard pandas dependency while remaining correct against real yfinance frames.

All monetary values are passed through unchanged: yfinance already reports in
absolute currency units, which is the platform's convention.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from ...models.base import Currency, FiscalPeriod, PeriodType
from ...models.company import CompanyProfile, MarketData
from ...models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from ...models.prices import PriceBar, PriceHistory


# --------------------------------------------------------------------------- #
# Small structural helpers                                                     #
# --------------------------------------------------------------------------- #
def _is_missing(value: Any) -> bool:
    """True for ``None`` or NaN (which is not equal to itself)."""
    if value is None:
        return True
    return value != value  # noqa: PLR0124 - NaN check without importing pandas


def _to_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_currency(code: Any) -> Currency:
    if isinstance(code, str):
        try:
            return Currency(code.strip().upper())
        except ValueError:
            return Currency.OTHER
    return Currency.OTHER


def _to_date(value: Any) -> date | None:
    if _is_missing(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # pandas Timestamp and similar expose .date()
    to_date = getattr(value, "date", None)
    if callable(to_date):
        try:
            return to_date()
        except Exception:  # pragma: no cover - defensive
            return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _cell(frame: Any, labels: Iterable[str], column: Any) -> float | None:
    """First present, non-NaN value among ``labels`` for ``column`` in ``frame``."""
    if frame is None:
        return None
    try:
        index = frame.index
    except AttributeError:
        return None
    for label in labels:
        if label in index:
            try:
                value = frame.at[label, column]
            except (KeyError, TypeError):
                continue
            f = _to_float(value)
            if f is not None:
                return f
    return None


def _columns(frame: Any) -> list[Any]:
    if frame is None:
        return []
    try:
        return list(frame.columns)
    except AttributeError:
        return []


def _period_for(column: Any, period_type: PeriodType) -> FiscalPeriod:
    period_end = _to_date(column)
    fiscal_year = period_end.year if period_end else 0
    return FiscalPeriod(
        fiscal_year=fiscal_year,
        period_type=period_type,
        period_end=period_end,
    )


# --------------------------------------------------------------------------- #
# Field -> candidate yfinance label maps                                       #
# --------------------------------------------------------------------------- #
_INCOME_LABELS: dict[str, list[str]] = {
    "revenue": ["Total Revenue", "Operating Revenue", "Revenue"],
    "cost_of_revenue": ["Cost Of Revenue", "Reconciled Cost Of Revenue"],
    "gross_profit": ["Gross Profit"],
    "research_development": ["Research And Development", "Research Development"],
    "selling_general_admin": [
        "Selling General And Administration",
        "Selling General And Administrative",
        "Selling General Administrative",
    ],
    "operating_expenses": ["Operating Expense", "Total Operating Expenses"],
    "ebitda": ["EBITDA", "Normalized EBITDA"],
    "depreciation_amortization": [
        "Reconciled Depreciation",
        "Depreciation And Amortization In Income Statement",
        "Depreciation Amortization Depletion Income Statement",
    ],
    "ebit": ["Operating Income", "Total Operating Income As Reported", "EBIT"],
    "interest_expense": ["Interest Expense", "Interest Expense Non Operating"],
    "other_income_expense": [
        "Other Income Expense",
        "Total Other Finance Cost",
        "Other Non Operating Income Expenses",
    ],
    "pretax_income": ["Pretax Income", "Pre Tax Income"],
    "tax_expense": ["Tax Provision", "Income Tax Expense"],
    "net_income": [
        "Net Income",
        "Net Income Common Stockholders",
        "Net Income Continuous Operations",
    ],
    "shares_basic": ["Basic Average Shares", "Basic EPS Shares"],
    "shares_diluted": ["Diluted Average Shares", "Diluted EPS Shares"],
}

_BALANCE_LABELS: dict[str, list[str]] = {
    "cash_and_equivalents": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
    "short_term_investments": ["Other Short Term Investments", "Short Term Investments"],
    "accounts_receivable": ["Accounts Receivable", "Receivables"],
    "inventory": ["Inventory"],
    "other_current_assets": ["Other Current Assets"],
    "total_current_assets": ["Current Assets", "Total Current Assets"],
    "net_ppe": ["Net PPE", "Net Property Plant And Equipment"],
    "goodwill_and_intangibles": [
        "Goodwill And Other Intangible Assets",
        "Goodwill",
    ],
    "other_non_current_assets": ["Other Non Current Assets"],
    "total_assets": ["Total Assets"],
    "accounts_payable": ["Accounts Payable", "Payables"],
    "short_term_debt": ["Current Debt", "Current Debt And Capital Lease Obligation"],
    "other_current_liabilities": ["Other Current Liabilities"],
    "total_current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
    "long_term_debt": ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"],
    "other_non_current_liabilities": ["Other Non Current Liabilities"],
    "total_liabilities": [
        "Total Liabilities Net Minority Interest",
        "Total Liabilities",
    ],
    "total_equity": [
        "Stockholders Equity",
        "Total Equity Gross Minority Interest",
        "Common Stock Equity",
    ],
    "retained_earnings": ["Retained Earnings"],
}

_CASHFLOW_LABELS: dict[str, list[str]] = {
    "net_income": ["Net Income From Continuing Operations", "Net Income"],
    "depreciation_amortization": [
        "Depreciation And Amortization",
        "Depreciation Amortization Depletion",
    ],
    "change_in_working_capital": ["Change In Working Capital"],
    "stock_based_compensation": ["Stock Based Compensation"],
    "cash_from_operations": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    "capital_expenditures": ["Capital Expenditure", "Purchase Of PPE"],
    "cash_from_investing": ["Investing Cash Flow", "Cash Flow From Continuing Investing Activities"],
    "debt_issued": ["Issuance Of Debt", "Long Term Debt Issuance"],
    "debt_repaid": ["Repayment Of Debt", "Long Term Debt Payments"],
    "dividends_paid": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "share_repurchase": ["Repurchase Of Capital Stock", "Common Stock Payments"],
    "cash_from_financing": ["Financing Cash Flow", "Cash Flow From Continuing Financing Activities"],
    "free_cash_flow": ["Free Cash Flow"],
}


def _row_kwargs(frame: Any, labels: dict[str, list[str]], column: Any) -> dict[str, float | None]:
    return {field: _cell(frame, candidates, column) for field, candidates in labels.items()}


# --------------------------------------------------------------------------- #
# Public normalisation functions                                              #
# --------------------------------------------------------------------------- #
def normalize_profile(info: dict[str, Any], ticker: str) -> CompanyProfile:
    """Build a :class:`CompanyProfile` from a yfinance ``.info`` dict."""
    info = info or {}
    return CompanyProfile(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName"),
        exchange=info.get("exchange") or info.get("fullExchangeName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        country=info.get("country"),
        currency=_to_currency(info.get("currency") or info.get("financialCurrency")),
        description=info.get("longBusinessSummary"),
        website=info.get("website"),
        employees=info.get("fullTimeEmployees"),
    )


def normalize_market_data(info: dict[str, Any], ticker: str) -> MarketData:
    """Build :class:`MarketData` from a yfinance ``.info`` dict."""
    info = info or {}
    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )
    total_debt = _to_float(info.get("totalDebt"))
    total_cash = _to_float(info.get("totalCash"))
    net_debt = None
    if total_debt is not None or total_cash is not None:
        net_debt = (total_debt or 0.0) - (total_cash or 0.0)

    return MarketData(
        ticker=ticker,
        price=_to_float(price),
        shares_outstanding=_to_float(info.get("sharesOutstanding")),
        market_cap=_to_float(info.get("marketCap")),
        enterprise_value=_to_float(info.get("enterpriseValue")),
        net_debt=net_debt,
        beta=_to_float(info.get("beta")),
        currency=_to_currency(info.get("currency")),
        trailing_pe=_to_float(info.get("trailingPE")),
        forward_pe=_to_float(info.get("forwardPE")),
        ev_to_revenue=_to_float(info.get("enterpriseToRevenue")),
        ev_to_ebitda=_to_float(info.get("enterpriseToEbitda")),
        price_to_book=_to_float(info.get("priceToBook")),
    )


def normalize_income_statements(
    frame: Any, currency: Currency = Currency.USD, period_type: PeriodType = PeriodType.ANNUAL
) -> list[IncomeStatement]:
    out: list[IncomeStatement] = []
    for column in _columns(frame):
        kwargs = _row_kwargs(frame, _INCOME_LABELS, column)
        if all(v is None for v in kwargs.values()):
            continue
        out.append(
            IncomeStatement(period=_period_for(column, period_type), currency=currency, **kwargs)
        )
    return out


def normalize_balance_sheets(
    frame: Any, currency: Currency = Currency.USD, period_type: PeriodType = PeriodType.ANNUAL
) -> list[BalanceSheet]:
    out: list[BalanceSheet] = []
    for column in _columns(frame):
        kwargs = _row_kwargs(frame, _BALANCE_LABELS, column)
        if all(v is None for v in kwargs.values()):
            continue
        out.append(
            BalanceSheet(period=_period_for(column, period_type), currency=currency, **kwargs)
        )
    return out


def normalize_cash_flows(
    frame: Any, currency: Currency = Currency.USD, period_type: PeriodType = PeriodType.ANNUAL
) -> list[CashFlowStatement]:
    out: list[CashFlowStatement] = []
    for column in _columns(frame):
        kwargs = _row_kwargs(frame, _CASHFLOW_LABELS, column)
        if all(v is None for v in kwargs.values()):
            continue
        out.append(
            CashFlowStatement(period=_period_for(column, period_type), currency=currency, **kwargs)
        )
    return out


def normalize_financials(
    ticker: str,
    income_frame: Any = None,
    balance_frame: Any = None,
    cashflow_frame: Any = None,
    currency: Currency = Currency.USD,
    period_type: PeriodType = PeriodType.ANNUAL,
) -> FinancialStatements:
    """Assemble a :class:`FinancialStatements` container from the three frames."""
    return FinancialStatements(
        ticker=ticker,
        currency=currency,
        period_type=period_type,
        income_statements=normalize_income_statements(income_frame, currency, period_type),
        balance_sheets=normalize_balance_sheets(balance_frame, currency, period_type),
        cash_flow_statements=normalize_cash_flows(cashflow_frame, currency, period_type),
    )


def normalize_price_history(
    frame: Any, ticker: str, currency: Currency = Currency.USD
) -> PriceHistory:
    """Build a :class:`PriceHistory` from a yfinance ``history()`` DataFrame."""
    bars: list[PriceBar] = []
    if frame is not None:
        try:
            rows = frame.iterrows()
        except AttributeError:
            rows = []
        for index, row in rows:
            bar_date = _to_date(index)
            close = _to_float(_row_get(row, "Close"))
            if bar_date is None or close is None or close <= 0:
                continue
            bars.append(
                PriceBar(
                    date=bar_date,
                    open=_to_float(_row_get(row, "Open")),
                    high=_to_float(_row_get(row, "High")),
                    low=_to_float(_row_get(row, "Low")),
                    close=close,
                    adj_close=_to_float(_row_get(row, "Adj Close")),
                    volume=_to_float(_row_get(row, "Volume")),
                )
            )
    return PriceHistory(ticker=ticker, currency=currency, bars=bars)


def _row_get(row: Any, key: str) -> Any:
    """Fetch ``key`` from a row that may be a mapping or a pandas Series."""
    try:
        if key in row:
            return row[key]
    except TypeError:
        pass
    getter = getattr(row, "get", None)
    if callable(getter):
        return getter(key)
    return None
