"""Tests for configuration management."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from config import Settings, get_settings


def test_defaults(monkeypatch: pytest.MonkeyPatch):
    # Ensure a clean environment for the fields under test
    for var in ["OPENAI_API_KEY", "DATA_PROVIDER", "RISK_FREE_RATE", "FORECAST_YEARS"]:
        monkeypatch.delenv(var, raising=False)
    s = Settings()
    assert s.data_provider == "yfinance"
    assert s.forecast_years == 5
    assert s.monte_carlo_simulations == 10_000
    assert s.risk_free_rate == pytest.approx(0.04)


def test_has_openai_false_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert Settings().has_openai() is False


def test_has_openai_true_when_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    s = Settings()
    assert s.has_openai() is True
    assert s.openai_api_key == "sk-test-123"


def test_env_override_numeric(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FORECAST_YEARS", "7")
    monkeypatch.setenv("RISK_FREE_RATE", "0.045")
    s = Settings()
    assert s.forecast_years == 7
    assert s.risk_free_rate == pytest.approx(0.045)


def test_use_live_data_property(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATA_PROVIDER", "local")
    assert Settings().use_live_data is False
    monkeypatch.setenv("DATA_PROVIDER", "yfinance")
    assert Settings().use_live_data is True


def test_out_of_range_value_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEFAULT_TAX_RATE", "1.5")
    with pytest.raises(ValidationError):
        Settings()


def test_get_settings_is_cached():
    a = get_settings()
    b = get_settings()
    assert a is b  # lru_cache singleton
