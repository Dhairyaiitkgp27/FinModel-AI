"""Tests for price models."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from core.models import PriceBar, PriceHistory


def test_price_bar_requires_positive_close():
    with pytest.raises(ValidationError):
        PriceBar(date=date(2023, 1, 1), close=0.0)


def test_price_history_sorted_on_construction():
    hist = PriceHistory(
        ticker="AAPL",
        bars=[
            PriceBar(date=date(2023, 1, 3), close=12.0),
            PriceBar(date=date(2023, 1, 1), close=10.0),
            PriceBar(date=date(2023, 1, 2), close=11.0),
        ],
    )
    assert [b.date.day for b in hist.bars] == [1, 2, 3]
    assert hist.closes() == [10.0, 11.0, 12.0]


def test_price_history_dedupes_keeping_last():
    hist = PriceHistory(
        ticker="AAPL",
        bars=[
            PriceBar(date=date(2023, 1, 1), close=10.0),
            PriceBar(date=date(2023, 1, 1), close=99.0),
        ],
    )
    assert len(hist.bars) == 1
    assert hist.latest_close() == 99.0


def test_price_history_latest_and_empty():
    empty = PriceHistory(ticker="AAPL", bars=[])
    assert empty.latest() is None
    assert empty.latest_close() is None


def test_price_history_simple_returns():
    hist = PriceHistory(
        ticker="AAPL",
        bars=[
            PriceBar(date=date(2023, 1, 1), close=100.0),
            PriceBar(date=date(2023, 1, 2), close=110.0),
            PriceBar(date=date(2023, 1, 3), close=99.0),
        ],
    )
    rets = hist.simple_returns()
    assert rets[0] == pytest.approx(0.10)
    assert rets[1] == pytest.approx(-0.10)


def test_price_history_ticker_normalised():
    hist = PriceHistory(ticker="nvda", bars=[])
    assert hist.ticker == "NVDA"
