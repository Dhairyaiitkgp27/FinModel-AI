"""A live data provider backed by yfinance.

yfinance is imported lazily inside the methods so that the rest of the data layer
imports cleanly in environments where yfinance (and its dependency tree) is not
installed — for example a light, sample-only setup. Attempting to actually fetch
without the package installed raises a clear :class:`DataProviderError`.

All parsing is delegated to :mod:`core.data.normalization.yfinance`, keeping this
class a thin adapter over the yfinance API surface.
"""
from __future__ import annotations

from typing import Any

from ...models.base import Currency
from ...models.company import CompanyProfile, MarketData
from ...models.financials import FinancialStatements
from ...models.prices import PriceHistory
from ..normalization import yfinance as norm
from .base import DataProvider, DataProviderError


class YFinanceProvider(DataProvider):
    """Fetch company data live from Yahoo Finance via the ``yfinance`` package."""

    name = "yfinance"
    is_sample = False

    def __init__(self, price_period: str = "1y", price_interval: str = "1d"):
        self.price_period = price_period
        self.price_interval = price_interval
        self._ticker_cache: dict[str, Any] = {}

    # --- yfinance handles ----------------------------------------------- #
    @staticmethod
    def _import_yf() -> Any:
        try:
            import yfinance as yf  # noqa: PLC0415 - intentional lazy import
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise DataProviderError(
                "The 'yfinance' package is required for live data. "
                "Install it with `pip install yfinance`, or use the local sample provider."
            ) from exc
        return yf

    def _handle(self, ticker: str) -> Any:
        key = ticker.strip().upper()
        if key not in self._ticker_cache:
            yf = self._import_yf()
            self._ticker_cache[key] = yf.Ticker(key)
        return self._ticker_cache[key]

    def _info(self, ticker: str) -> dict[str, Any]:
        handle = self._handle(ticker)
        try:
            info = handle.info
        except Exception as exc:  # pragma: no cover - network dependent
            raise DataProviderError(f"yfinance could not fetch info for '{ticker}': {exc}") from exc
        return info or {}

    # --- DataProvider interface ----------------------------------------- #
    def get_company_profile(self, ticker: str) -> CompanyProfile:
        return norm.normalize_profile(self._info(ticker), ticker)

    def get_market_data(self, ticker: str) -> MarketData:
        return norm.normalize_market_data(self._info(ticker), ticker)

    def get_financials(self, ticker: str) -> FinancialStatements:
        handle = self._handle(ticker)
        currency = self._currency_from_info(ticker)
        try:
            income_frame = handle.income_stmt
            balance_frame = handle.balance_sheet
            cashflow_frame = handle.cashflow
        except Exception as exc:  # pragma: no cover - network dependent
            raise DataProviderError(
                f"yfinance could not fetch statements for '{ticker}': {exc}"
            ) from exc
        return norm.normalize_financials(
            ticker,
            income_frame=income_frame,
            balance_frame=balance_frame,
            cashflow_frame=cashflow_frame,
            currency=currency,
        )

    def get_price_history(self, ticker: str) -> PriceHistory:
        handle = self._handle(ticker)
        currency = self._currency_from_info(ticker)
        try:
            frame = handle.history(period=self.price_period, interval=self.price_interval)
        except Exception as exc:  # pragma: no cover - network dependent
            raise DataProviderError(
                f"yfinance could not fetch price history for '{ticker}': {exc}"
            ) from exc
        return norm.normalize_price_history(frame, ticker, currency)

    def _currency_from_info(self, ticker: str) -> Currency:
        info = self._info(ticker)
        code = info.get("financialCurrency") or info.get("currency") or "USD"
        try:
            return Currency(str(code).strip().upper())
        except ValueError:
            return Currency.OTHER
