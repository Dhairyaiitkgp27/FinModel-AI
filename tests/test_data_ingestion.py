"""Tests for the ingestion loader and provider factory."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.data import (
    DataProviderError,
    LocalSampleProvider,
    YFinanceProvider,
    available_sample_tickers,
    load_and_validate,
    load_company_dataset,
    make_provider,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def test_make_provider_local():
    provider = make_provider("local", SAMPLE_DIR)
    assert isinstance(provider, LocalSampleProvider)


def test_make_provider_yfinance():
    assert isinstance(make_provider("yfinance"), YFinanceProvider)


def test_make_provider_unknown_raises():
    with pytest.raises(ValueError):
        make_provider("nasa")


def test_available_sample_tickers():
    tickers = available_sample_tickers(SAMPLE_DIR)
    assert "AAPL" in tickers and "MSFT" in tickers


def test_load_local_dataset():
    ds = load_company_dataset("MSFT", provider="local", sample_dir=SAMPLE_DIR)
    assert ds.ticker == "MSFT"
    assert ds.is_sample is True


def test_local_unknown_ticker_raises_without_fallback():
    # provider is already local; a missing ticker must raise, not silently fall back
    with pytest.raises(DataProviderError):
        load_company_dataset("NOPE", provider="local", sample_dir=SAMPLE_DIR)


def test_live_falls_back_to_sample_when_unavailable():
    # yfinance is not installed / network blocked here, so the live provider fails
    # and ingestion should fall back to the bundled sample for AAPL.
    ds = load_company_dataset("AAPL", provider="yfinance", sample_dir=SAMPLE_DIR)
    assert ds.is_sample is True
    assert ds.source == "local_sample"
    assert ds.note is not None  # fallback note recorded


def test_live_failure_without_sample_raises():
    with pytest.raises(DataProviderError):
        load_company_dataset("ZZZZ", provider="yfinance", sample_dir=SAMPLE_DIR)


def test_fallback_disabled_propagates_error():
    with pytest.raises(DataProviderError):
        load_company_dataset(
            "AAPL", provider="yfinance", sample_dir=SAMPLE_DIR, fallback_to_sample=False
        )


def test_load_and_validate_returns_report():
    ds, report = load_and_validate("AAPL", provider="local", sample_dir=SAMPLE_DIR)
    assert ds.ticker == "AAPL"
    assert report.is_valid is True


def test_yfinance_provider_missing_package_message():
    # Directly calling the live provider should give a clear, actionable error
    provider = YFinanceProvider()
    with pytest.raises(DataProviderError):
        provider.get_company_profile("AAPL")
