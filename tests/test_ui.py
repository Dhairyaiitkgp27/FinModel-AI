"""Tests for the dashboard UI layer (formatting, analysis, charts)."""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import pytest

from core.models import CompanyProfile, FinancialStatements, PriceHistory
from ui import charts
from ui.analysis import AnalysisAssumptions, AnalysisBundle, run_full_analysis, valuation_ranges
from ui.formatting import (
    format_currency,
    format_large,
    format_multiple,
    format_pct,
    format_signed_pct,
    upside_label,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


# --------------------------------------------------------------------------- #
# Formatting                                                                  #
# --------------------------------------------------------------------------- #
def test_format_large_suffixes():
    assert format_large(2_747_000_000_000) == "$2.7T"
    assert format_large(383_285_000_000) == "$383.3B"
    assert format_large(5_000_000) == "$5.0M"
    assert format_large(2_500) == "$2.5K"
    assert format_large(-1_000_000_000) == "-$1.0B"
    assert format_large(None) == "—"


def test_format_currency_and_pct():
    assert format_currency(176.65) == "$176.65"
    assert format_currency(None) == "—"
    assert format_pct(0.441) == "44.1%"
    assert format_pct(None) == "—"
    assert format_signed_pct(0.078) == "+7.8%"
    assert format_signed_pct(-0.028) == "-2.8%"


def test_format_multiple_and_upside():
    assert format_multiple(16.84) == "16.8x"
    assert upside_label(79.0, 176.65).endswith("downside")
    assert upside_label(200.0, 176.65).endswith("upside")
    assert upside_label(None, 100.0) == "—"


# --------------------------------------------------------------------------- #
# Analysis orchestration                                                       #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def bundle() -> AnalysisBundle:
    return run_full_analysis("AAPL", provider="local", sample_dir=SAMPLE_DIR)


def test_full_analysis_populates_all_sections(bundle: AnalysisBundle):
    assert bundle.warnings == []
    assert bundle.ratios.latest is not None
    assert bundle.forecast is not None and bundle.forecast.balance_checks_passed
    assert bundle.scenarios is not None
    assert bundle.dcf is not None and bundle.dcf.implied_share_price > 0
    assert bundle.comps is not None
    assert bundle.precedent is not None
    assert bundle.reverse_dcf is not None
    assert bundle.sensitivity is not None
    assert bundle.driver_ranking is not None
    assert bundle.monte_carlo is not None
    assert bundle.market_price == pytest.approx(176.65)


def test_assumptions_flow_through():
    a = AnalysisAssumptions(base_growth=0.10, horizon_years=7, n_simulations=2000)
    b = run_full_analysis("MSFT", provider="local", sample_dir=SAMPLE_DIR, assumptions=a)
    assert len(b.forecast.free_cash_flows) == 7
    assert b.monte_carlo.n_simulations == 2000


def test_valuation_ranges_ordered(bundle: AnalysisBundle):
    rows = valuation_ranges(bundle)
    methods = {r[0] for r in rows}
    assert {"DCF", "Comps", "Precedent", "Monte Carlo"} <= methods
    for method, low, mid, high in rows:
        assert low <= mid <= high, f"{method} range not ordered"


def test_valuation_ranges_handles_empty_bundle():
    # A bundle with no valuations should yield no ranges, not raise.
    empty = AnalysisBundle(
        dataset=_stub_dataset(),
        assumptions=AnalysisAssumptions(),
        validation=_stub_report(),
        ratios=_stub_ratios(),
    )
    assert valuation_ranges(empty) == []


# --------------------------------------------------------------------------- #
# Charts                                                                       #
# --------------------------------------------------------------------------- #
def test_charts_build_figures(bundle: AnalysisBundle):
    assert isinstance(charts.revenue_forecast_chart(bundle), go.Figure)
    assert len(charts.revenue_forecast_chart(bundle).data) == 2  # historical + projected
    assert len(charts.margin_trend_chart(bundle.ratios).data) == 3  # three margins
    assert isinstance(charts.valuation_football_field(bundle), go.Figure)
    assert isinstance(charts.scenario_revenue_chart(bundle.scenarios), go.Figure)


def test_sensitivity_heatmap_is_heatmap(bundle: AnalysisBundle):
    fig = charts.sensitivity_heatmap(bundle.sensitivity)
    assert any(isinstance(trace, go.Heatmap) for trace in fig.data)


def test_monte_carlo_histogram_has_bars(bundle: AnalysisBundle):
    fig = charts.monte_carlo_histogram(bundle.monte_carlo)
    assert any(isinstance(trace, go.Bar) for trace in fig.data)


def test_tornado_chart_is_horizontal_bar(bundle: AnalysisBundle):
    fig = charts.driver_tornado_chart(bundle.driver_ranking)
    bar = next(t for t in fig.data if isinstance(t, go.Bar))
    assert bar.orientation == "h"


def test_price_history_chart_none_when_no_bars(bundle: AnalysisBundle):
    # Bundled sample data carries no price bars.
    assert charts.price_history_chart(bundle) is None


# --------------------------------------------------------------------------- #
# Stubs                                                                       #
# --------------------------------------------------------------------------- #
def _stub_dataset():
    from core.data.dataset import CompanyDataset

    return CompanyDataset(
        profile=CompanyProfile(ticker="TST"),
        financials=FinancialStatements(ticker="TST"),
        prices=PriceHistory(ticker="TST"),
        source="test",
    )


def _stub_report():
    from core.data.validation.checks import ValidationReport

    return ValidationReport(ticker="TST")


def _stub_ratios():
    from core.models.analysis import RatioAnalysis

    return RatioAnalysis(ticker="TST")
