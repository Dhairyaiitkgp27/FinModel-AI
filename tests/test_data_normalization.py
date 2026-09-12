"""Tests for the yfinance normalisation layer.

These feed the normaliser pandas DataFrames shaped exactly like yfinance's
``income_stmt`` / ``balance_sheet`` / ``cashflow`` / ``history`` output, so the
mapping logic is exercised against realistic inputs without any network access.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.data.normalization import yfinance as norm
from core.models import Currency


@pytest.fixture
def periods() -> list[pd.Timestamp]:
    # yfinance orders columns most-recent-first
    return [pd.Timestamp("2023-09-30"), pd.Timestamp("2022-09-24")]


def _frame(rows: dict[str, list[float]], cols: list[pd.Timestamp]) -> pd.DataFrame:
    return pd.DataFrame({c: {k: v[i] for k, v in rows.items()} for i, c in enumerate(cols)})


def test_normalize_income_statements(periods):
    frame = _frame(
        {
            "Total Revenue": [383285.0, 394328.0],
            "Cost Of Revenue": [214137.0, 223546.0],
            "Research And Development": [29915.0, 26251.0],
            "Selling General And Administration": [24932.0, 25094.0],
            "Operating Income": [114301.0, 119437.0],
            "Reconciled Depreciation": [11519.0, 11104.0],
            "Tax Provision": [16741.0, 19300.0],
            "Pretax Income": [113736.0, 119103.0],
            "Net Income": [96995.0, 99803.0],
            "Basic Average Shares": [15744.231, 16215.963],
            # a row we don't model, must be ignored:
            "Total Unusual Items": [0.0, 0.0],
        },
        periods,
    )
    statements = norm.normalize_income_statements(frame, currency=Currency.USD)
    assert len(statements) == 2
    # results are sorted chronologically inside the container/model consumer;
    # here we get them in frame column order, so find FY2023 explicitly
    fy23 = next(s for s in statements if s.period.fiscal_year == 2023)
    assert fy23.revenue == pytest.approx(383285.0)
    assert fy23.period.period_end.year == 2023
    # derived fields flow through the model
    assert fy23.gross_profit == pytest.approx(169148.0)
    assert fy23.ebitda == pytest.approx(114301.0 + 11519.0)
    assert fy23.gross_margin == pytest.approx(0.4413, abs=1e-3)


def test_income_handles_label_variants_and_nan(periods):
    frame = _frame(
        {
            "Operating Revenue": [100.0, 90.0],  # variant label for revenue
            "Cost Of Revenue": [60.0, np.nan],  # NaN must become None
        },
        periods,
    )
    statements = norm.normalize_income_statements(frame)
    fy23 = next(s for s in statements if s.period.fiscal_year == 2023)
    fy22 = next(s for s in statements if s.period.fiscal_year == 2022)
    assert fy23.revenue == pytest.approx(100.0)
    assert fy23.gross_profit == pytest.approx(40.0)
    assert fy22.cost_of_revenue is None  # NaN dropped
    assert fy22.gross_profit is None  # cannot derive without COGS


def test_normalize_balance_sheet(periods):
    frame = _frame(
        {
            "Total Assets": [352583.0, 352755.0],
            "Current Assets": [143566.0, 135405.0],
            "Cash And Cash Equivalents": [29965.0, 23646.0],
            "Current Debt": [15807.0, 21110.0],
            "Long Term Debt": [95281.0, 98959.0],
            "Current Liabilities": [145308.0, 153982.0],
            "Total Liabilities Net Minority Interest": [290437.0, 302083.0],
            "Stockholders Equity": [62146.0, 50672.0],
        },
        periods,
    )
    sheets = norm.normalize_balance_sheets(frame)
    fy23 = next(s for s in sheets if s.period.fiscal_year == 2023)
    assert fy23.total_debt == pytest.approx(15807.0 + 95281.0)
    assert fy23.is_balanced() is True


def test_normalize_cash_flow(periods):
    frame = _frame(
        {
            "Operating Cash Flow": [110543.0, 122151.0],
            "Capital Expenditure": [-10959.0, -10708.0],
            "Net Income From Continuing Operations": [96995.0, 99803.0],
            "Depreciation And Amortization": [11519.0, 11104.0],
        },
        periods,
    )
    flows = norm.normalize_cash_flows(frame)
    fy23 = next(s for s in flows if s.period.fiscal_year == 2023)
    # free cash flow derives from CFO - |capex|
    assert fy23.free_cash_flow == pytest.approx(110543.0 - 10959.0)
    assert fy23.capex_abs == pytest.approx(10959.0)


def test_normalize_profile_and_market_data():
    info = {
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "currency": "USD",
        "website": "https://www.apple.com",
        "fullTimeEmployees": 161000,
        "currentPrice": 176.65,
        "sharesOutstanding": 15_550_061_000,
        "marketCap": 2_747_000_000_000,
        "beta": 1.29,
        "trailingPE": 28.7,
        "totalDebt": 111_088_000_000,
        "totalCash": 61_555_000_000,
    }
    profile = norm.normalize_profile(info, "aapl")
    assert profile.ticker == "AAPL"
    assert profile.name == "Apple Inc."
    assert profile.currency == Currency.USD

    md = norm.normalize_market_data(info, "aapl")
    assert md.price == pytest.approx(176.65)
    assert md.beta == pytest.approx(1.29)
    # net debt computed from totalDebt - totalCash
    assert md.net_debt == pytest.approx(111_088e6 - 61_555e6)


def test_unknown_currency_falls_back_to_other():
    md = norm.normalize_market_data({"currency": "XYZ", "currentPrice": 10.0}, "TST")
    assert md.currency == Currency.OTHER


def test_normalize_price_history():
    idx = pd.to_datetime(["2023-01-03", "2023-01-04", "2023-01-05"])
    frame = pd.DataFrame(
        {
            "Open": [125.0, 126.0, 127.0],
            "High": [126.0, 127.5, 128.0],
            "Low": [124.0, 125.5, 126.5],
            "Close": [125.5, 127.0, 126.0],
            "Volume": [1000, 1100, 900],
        },
        index=idx,
    )
    hist = norm.normalize_price_history(frame, "aapl", Currency.USD)
    assert hist.ticker == "AAPL"
    assert len(hist.bars) == 3
    assert hist.latest_close() == pytest.approx(126.0)
    assert hist.closes()[0] == pytest.approx(125.5)


def test_empty_frame_yields_no_statements():
    empty = pd.DataFrame()
    assert norm.normalize_income_statements(empty) == []
    assert norm.normalize_price_history(empty, "TST") .bars == []
