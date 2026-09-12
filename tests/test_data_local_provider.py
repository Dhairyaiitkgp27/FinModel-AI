"""Tests for the bundled sample-data provider."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.data import CompanyDataset, DataProviderError, LocalSampleProvider

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


@pytest.fixture
def provider() -> LocalSampleProvider:
    return LocalSampleProvider(SAMPLE_DIR)


def test_available_tickers_includes_bundled(provider: LocalSampleProvider):
    tickers = provider.available_tickers()
    assert "AAPL" in tickers
    assert "MSFT" in tickers


def test_get_company_dataset_shape(provider: LocalSampleProvider):
    ds = provider.get_company_dataset("aapl")
    assert isinstance(ds, CompanyDataset)
    assert ds.ticker == "AAPL"
    assert ds.is_sample is True
    assert ds.source == "local_sample"
    assert ds.has_financials()
    assert len(ds.financials.income_statements) == 3


def test_unit_scale_applied_to_financials(provider: LocalSampleProvider):
    fin = provider.get_financials("AAPL")
    latest = fin.latest_income()
    # 383,285 million -> 3.83285e11 absolute
    assert latest.revenue == pytest.approx(383_285e6)


def test_price_not_scaled_but_shares_are(provider: LocalSampleProvider):
    md = provider.get_market_data("AAPL")
    assert md.price == pytest.approx(176.65)  # per-share, unscaled
    assert md.shares_outstanding == pytest.approx(15_550.061e6)  # scaled to absolute
    # market cap backfilled from price * shares
    assert md.market_cap == pytest.approx(176.65 * 15_550.061e6)


def test_derived_fields_flow_through(provider: LocalSampleProvider):
    latest = provider.get_financials("AAPL").latest_income()
    # gross profit and margins derive from revenue/COGS
    assert latest.gross_profit == pytest.approx((383_285 - 214_137) * 1e6)
    assert latest.gross_margin == pytest.approx(0.441, abs=0.01)


def test_balance_sheets_balance(provider: LocalSampleProvider):
    for bs in provider.get_financials("MSFT").balance_sheets:
        assert bs.is_balanced() is True


def test_missing_ticker_raises(provider: LocalSampleProvider):
    with pytest.raises(DataProviderError):
        provider.get_company_dataset("NOTREAL")


def test_prices_empty_when_absent(provider: LocalSampleProvider):
    # sample files carry no price bars; history should be a valid empty series
    hist = provider.get_price_history("AAPL")
    assert hist.ticker == "AAPL"
    assert hist.bars == []


def test_scale_defaults_to_one(tmp_path: Path):
    payload = {
        "currency": "USD",
        "period_type": "annual",
        "profile": {"ticker": "TST", "name": "Test Co"},
        "income_statements": [
            {
                "period": {"fiscal_year": 2023, "period_type": "annual"},
                "revenue": 100.0,
                "cost_of_revenue": 60.0,
            }
        ],
    }
    (tmp_path / "TST.json").write_text(json.dumps(payload), encoding="utf-8")
    provider = LocalSampleProvider(tmp_path)
    latest = provider.get_financials("TST").latest_income()
    assert latest.revenue == pytest.approx(100.0)  # no unit_scale -> unchanged
    assert latest.gross_profit == pytest.approx(40.0)
