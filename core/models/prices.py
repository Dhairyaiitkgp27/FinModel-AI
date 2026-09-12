"""Historical price models."""
from __future__ import annotations

from datetime import date

from pydantic import field_validator, model_validator

from ..utils.math import pct_change
from .base import Currency, FinBaseModel


class PriceBar(FinBaseModel):
    """A single OHLCV price observation."""

    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    adj_close: float | None = None
    volume: float | None = None

    @field_validator("close")
    @classmethod
    def _close_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("close price must be positive")
        return value


class PriceHistory(FinBaseModel):
    """An ordered series of price bars for a single ticker.

    Bars are sorted chronologically and de-duplicated by date on construction,
    keeping the last observation for any duplicated date.
    """

    ticker: str
    currency: Currency = Currency.USD
    bars: list[PriceBar] = []

    @field_validator("ticker")
    @classmethod
    def _normalise_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def _sort_and_dedupe(self) -> PriceHistory:
        by_date: dict[date, PriceBar] = {}
        for bar in self.bars:
            by_date[bar.date] = bar  # later duplicate wins
        self.bars = [by_date[d] for d in sorted(by_date)]
        return self

    # ------------------------------------------------------------------ #
    # Convenience accessors                                              #
    # ------------------------------------------------------------------ #
    def latest(self) -> PriceBar | None:
        """Most recent bar, or ``None`` if the series is empty."""
        return self.bars[-1] if self.bars else None

    def latest_close(self) -> float | None:
        last = self.latest()
        return last.close if last else None

    def closes(self) -> list[float]:
        """Chronological list of close prices."""
        return [bar.close for bar in self.bars]

    def simple_returns(self) -> list[float]:
        """Period-over-period simple returns of the close series."""
        closes = self.closes()
        out: list[float] = []
        for prev, curr in zip(closes, closes[1:]):
            change = pct_change(curr, prev)
            if change is not None:
                out.append(change)
        return out
