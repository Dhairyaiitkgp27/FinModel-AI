"""A provider backed by bundled sample datasets on disk.

Sample data lives as one JSON file per ticker (e.g. ``AAPL.json``) under a
sample directory. Files are authored in *millions* of the reporting currency for
readability and carry a ``unit_scale`` (typically 1,000,000); this provider
multiplies monetary line items and share counts by that scale so the models it
returns follow the platform's absolute-units convention. Per-share prices and
ratio-style fields are never scaled.

The sample figures are approximate values compiled from companies' public annual
reports, bundled purely so the platform runs end-to-end without network access.
Every dataset this provider returns is flagged ``is_sample=True``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...models.base import Currency, PeriodType
from ...models.company import CompanyProfile, MarketData
from ...models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from ...models.prices import PriceBar, PriceHistory
from ...models.valuation import PeerCompany, PrecedentTransaction
from .base import DataProvider, DataProviderError

# Fields on market data that are per-share or ratios and must NOT be scaled.
_UNSCALED_MARKET_FIELDS = frozenset(
    {"ticker", "as_of", "price", "beta", "currency",
     "trailing_pe", "forward_pe", "ev_to_revenue", "ev_to_ebitda", "price_to_book"}
)

# Fields on peers / precedents that are multiples or labels and must NOT be scaled.
_UNSCALED_PEER_FIELDS = frozenset(
    {"ticker", "name", "ev_to_revenue", "ev_to_ebitda", "pe", "pb"}
)
_UNSCALED_PRECEDENT_FIELDS = frozenset(
    {"target", "acquirer", "announced_date", "ev_to_revenue", "ev_to_ebitda", "is_sample"}
)


class LocalSampleProvider(DataProvider):
    """Serve company data from bundled JSON sample files."""

    name = "local_sample"
    is_sample = True

    def __init__(self, sample_dir: Path | str):
        self.sample_dir = Path(sample_dir)
        self._cache: dict[str, dict[str, Any]] = {}

    # --- Raw file access ------------------------------------------------ #
    def _path_for(self, ticker: str) -> Path:
        return self.sample_dir / f"{ticker.strip().upper()}.json"

    def _load_raw(self, ticker: str) -> dict[str, Any]:
        key = ticker.strip().upper()
        if key in self._cache:
            return self._cache[key]
        path = self._path_for(key)
        if not path.exists():
            raise DataProviderError(
                f"No sample dataset for '{key}' at {path}. "
                f"Available: {', '.join(self.available_tickers()) or 'none'}"
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - corrupt file
            raise DataProviderError(f"Sample dataset for '{key}' is not valid JSON: {exc}") from exc
        self._cache[key] = data
        return data

    def available_tickers(self) -> list[str]:
        """Sorted list of tickers with a bundled sample file."""
        if not self.sample_dir.exists():
            return []
        return sorted(p.stem.upper() for p in self.sample_dir.glob("*.json"))

    # --- Scaling helpers ------------------------------------------------ #
    @staticmethod
    def _scale_statement(raw: dict[str, Any], scale: float) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for field_name, value in raw.items():
            if field_name == "period":
                out[field_name] = value
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                out[field_name] = value * scale
            else:
                out[field_name] = value
        return out

    @staticmethod
    def _scale_market(raw: dict[str, Any], scale: float) -> dict[str, Any]:
        return LocalSampleProvider._scale_fields(raw, scale, _UNSCALED_MARKET_FIELDS)

    @staticmethod
    def _scale_fields(
        raw: dict[str, Any], scale: float, unscaled: frozenset[str]
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for field_name, value in raw.items():
            if (
                field_name not in unscaled
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                out[field_name] = value * scale
            else:
                out[field_name] = value
        return out

    # --- DataProvider interface ----------------------------------------- #
    def get_company_profile(self, ticker: str) -> CompanyProfile:
        raw = self._load_raw(ticker)
        profile_raw = dict(raw.get("profile", {}))
        profile_raw.setdefault("ticker", ticker)
        return CompanyProfile(**profile_raw)

    def get_market_data(self, ticker: str) -> MarketData:
        raw = self._load_raw(ticker)
        market_raw = raw.get("market_data")
        if not market_raw:
            raise DataProviderError(f"Sample dataset for '{ticker}' has no market_data")
        scale = float(raw.get("unit_scale", 1) or 1)
        market_raw = dict(market_raw)
        market_raw.setdefault("ticker", ticker)
        return MarketData(**self._scale_market(market_raw, scale))

    def get_financials(self, ticker: str) -> FinancialStatements:
        raw = self._load_raw(ticker)
        scale = float(raw.get("unit_scale", 1) or 1)
        currency = self._currency(raw)
        period_type = PeriodType(raw.get("period_type", "annual"))

        income = [
            IncomeStatement(**self._scale_statement(s, scale))
            for s in raw.get("income_statements", [])
        ]
        balance = [
            BalanceSheet(**self._scale_statement(s, scale))
            for s in raw.get("balance_sheets", [])
        ]
        cash_flow = [
            CashFlowStatement(**self._scale_statement(s, scale))
            for s in raw.get("cash_flow_statements", [])
        ]
        return FinancialStatements(
            ticker=ticker,
            currency=currency,
            period_type=period_type,
            income_statements=income,
            balance_sheets=balance,
            cash_flow_statements=cash_flow,
        )

    def get_price_history(self, ticker: str) -> PriceHistory:
        raw = self._load_raw(ticker)
        currency = self._currency(raw)
        bars = [PriceBar(**bar) for bar in raw.get("prices", [])]
        return PriceHistory(ticker=ticker, currency=currency, bars=bars)

    def get_peers(self, ticker: str) -> list[PeerCompany]:
        raw = self._load_raw(ticker)
        scale = float(raw.get("unit_scale", 1) or 1)
        return [
            PeerCompany(**self._scale_fields(peer, scale, _UNSCALED_PEER_FIELDS))
            for peer in raw.get("peers", [])
        ]

    def get_precedents(self, ticker: str) -> list[PrecedentTransaction]:
        raw = self._load_raw(ticker)
        scale = float(raw.get("unit_scale", 1) or 1)
        return [
            PrecedentTransaction(**self._scale_fields(tx, scale, _UNSCALED_PRECEDENT_FIELDS))
            for tx in raw.get("precedent_transactions", [])
        ]

    @staticmethod
    def _currency(raw: dict[str, Any]) -> Currency:
        code = raw.get("currency") or (raw.get("profile", {}) or {}).get("currency") or "USD"
        try:
            return Currency(str(code).strip().upper())
        except ValueError:
            return Currency.OTHER
