"""Company identity and market-data models."""
from __future__ import annotations

from datetime import date

from pydantic import field_validator, model_validator

from .base import Currency, FinBaseModel


class CompanyProfile(FinBaseModel):
    """Static descriptive information about a company."""

    ticker: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: Currency = Currency.USD
    description: str | None = None
    website: str | None = None
    employees: int | None = None

    @field_validator("ticker")
    @classmethod
    def _normalise_ticker(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("ticker must not be empty")
        return cleaned


class MarketData(FinBaseModel):
    """Point-in-time market data and headline valuation multiples.

    ``market_cap`` and ``enterprise_value`` are backfilled from their
    components when omitted, so downstream code can rely on them being present
    whenever the underlying inputs exist.
    """

    ticker: str
    as_of: date | None = None
    price: float | None = None
    shares_outstanding: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    net_debt: float | None = None
    beta: float | None = None
    currency: Currency = Currency.USD

    trailing_pe: float | None = None
    forward_pe: float | None = None
    ev_to_revenue: float | None = None
    ev_to_ebitda: float | None = None
    price_to_book: float | None = None

    @field_validator("ticker")
    @classmethod
    def _normalise_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("shares_outstanding", "market_cap")
    @classmethod
    def _non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("shares outstanding and market cap cannot be negative")
        return value

    @model_validator(mode="after")
    def _backfill(self) -> MarketData:
        if (
            self.market_cap is None
            and self.price is not None
            and self.shares_outstanding is not None
        ):
            self.market_cap = self.price * self.shares_outstanding
        if (
            self.enterprise_value is None
            and self.market_cap is not None
            and self.net_debt is not None
        ):
            self.enterprise_value = self.market_cap + self.net_debt
        return self
