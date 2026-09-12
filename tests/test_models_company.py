"""Tests for company and market-data models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import CompanyProfile, Currency, MarketData


def test_company_profile_ticker_normalised():
    c = CompanyProfile(ticker="  aapl ", name="Apple")
    assert c.ticker == "AAPL"
    assert c.currency == Currency.USD


def test_company_profile_empty_ticker_rejected():
    with pytest.raises(ValidationError):
        CompanyProfile(ticker="   ")


def test_market_cap_backfilled_from_price_and_shares():
    m = MarketData(ticker="AAPL", price=150.0, shares_outstanding=1_000_000.0)
    assert m.market_cap == pytest.approx(150_000_000.0)


def test_enterprise_value_backfilled_from_market_cap_and_net_debt():
    m = MarketData(ticker="AAPL", market_cap=1_000.0, net_debt=250.0)
    assert m.enterprise_value == pytest.approx(1_250.0)


def test_market_cap_not_overwritten_when_provided():
    m = MarketData(ticker="AAPL", price=10.0, shares_outstanding=5.0, market_cap=999.0)
    assert m.market_cap == 999.0  # explicit value preserved


def test_negative_shares_rejected():
    with pytest.raises(ValidationError):
        MarketData(ticker="AAPL", shares_outstanding=-1.0)


def test_market_data_ticker_normalised():
    m = MarketData(ticker="msft")
    assert m.ticker == "MSFT"
