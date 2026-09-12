"""Plotly chart builders for the dashboard.

Each function takes deterministic analysis outputs and returns a Plotly
``Figure``. They contain no Streamlit code, so they can be unit-tested directly
(a figure with the expected traces is produced).
"""
from __future__ import annotations

import plotly.graph_objects as go

from core.models.analysis import RatioAnalysis
from core.models.forecast import ScenarioComparison
from core.models.valuation import (
    DriverSensitivityRanking,
    MonteCarloResult,
    SensitivityResult,
)
from ui.analysis import AnalysisBundle, valuation_ranges

# A restrained, consistent palette.
_PRIMARY = "#2563eb"
_ACCENT = "#059669"
_WARN = "#dc2626"
_MUTED = "#94a3b8"
_TEMPLATE = "plotly_white"


def _layout(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=title,
        template=_TEMPLATE,
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(size=13),
    )
    return fig


def revenue_forecast_chart(bundle: AnalysisBundle) -> go.Figure:
    """Historical vs projected revenue as a bar chart."""
    fig = go.Figure()
    incomes = bundle.dataset.financials.income_statements
    hist_labels = [s.period.label() for s in incomes]
    hist_values = [s.revenue for s in incomes]
    fig.add_bar(x=hist_labels, y=hist_values, name="Historical", marker_color=_PRIMARY)

    if bundle.forecast is not None:
        proj = bundle.forecast.statements.income_statements
        fig.add_bar(
            x=[s.period.label() for s in proj],
            y=[s.revenue for s in proj],
            name="Projected",
            marker_color=_ACCENT,
        )
    return _layout(fig, "Revenue: historical vs projected")


def margin_trend_chart(ratios: RatioAnalysis) -> go.Figure:
    """Gross, EBITDA, and net margin trends across periods."""
    labels = [r.period.label() for r in ratios.periods]
    fig = go.Figure()
    for field_name, name, color in (
        ("gross_margin", "Gross margin", _PRIMARY),
        ("ebitda_margin", "EBITDA margin", _ACCENT),
        ("net_margin", "Net margin", _MUTED),
    ):
        values = [
            (getattr(r, field_name) * 100 if getattr(r, field_name) is not None else None)
            for r in ratios.periods
        ]
        fig.add_scatter(x=labels, y=values, mode="lines+markers", name=name, line=dict(color=color))
    fig.update_yaxes(title="%")
    return _layout(fig, "Margin trends")


def valuation_football_field(bundle: AnalysisBundle) -> go.Figure:
    """Implied share-price ranges by method, with the market price marked."""
    rows = valuation_ranges(bundle)
    fig = go.Figure()
    for method, low, mid, high in rows:
        fig.add_scatter(
            x=[low, high],
            y=[method, method],
            mode="lines",
            line=dict(color=_PRIMARY, width=10),
            showlegend=False,
        )
        fig.add_scatter(
            x=[mid],
            y=[method],
            mode="markers",
            marker=dict(color=_ACCENT, size=12, symbol="diamond"),
            name="Midpoint",
            showlegend=False,
        )
    market = bundle.market_price
    if market is not None:
        fig.add_vline(x=market, line=dict(color=_WARN, dash="dash"))
        fig.add_annotation(x=market, y=1.05, yref="paper", text=f"Market ${market:,.0f}",
                           showarrow=False, font=dict(color=_WARN))
    fig.update_xaxes(title="Implied share price")
    return _layout(fig, "Valuation summary (football field)")


def scenario_revenue_chart(comparison: ScenarioComparison) -> go.Figure:
    """Revenue trajectory per scenario."""
    fig = go.Figure()
    years = [f"Y{i + 1}" for i in range(comparison.horizon_years)]
    colors = {"base": _PRIMARY, "bull": _ACCENT, "bear": _WARN}
    for line in comparison.lines:
        fig.add_scatter(
            x=years,
            y=line.revenue,
            mode="lines+markers",
            name=line.scenario_name,
            line=dict(color=colors.get(line.scenario_type.value, _MUTED)),
        )
    fig.update_yaxes(title="Revenue")
    return _layout(fig, "Scenario revenue paths")


def sensitivity_heatmap(sensitivity: SensitivityResult) -> go.Figure:
    """WACC x terminal-growth heatmap of implied prices."""
    fig = go.Figure(
        data=go.Heatmap(
            z=sensitivity.matrix,
            x=[f"{g * 100:.1f}%" for g in sensitivity.col_axis.values],
            y=[f"{w * 100:.1f}%" for w in sensitivity.row_axis.values],
            colorscale="Blues",
            colorbar=dict(title="Price"),
        )
    )
    fig.update_xaxes(title=sensitivity.col_axis.name)
    fig.update_yaxes(title=sensitivity.row_axis.name)
    return _layout(fig, "DCF sensitivity: WACC vs terminal growth")


def monte_carlo_histogram(mc: MonteCarloResult) -> go.Figure:
    """Monte Carlo implied-price distribution with P10/P50/P90 markers."""
    edges = mc.histogram_edges
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
    fig = go.Figure()
    fig.add_bar(x=centers, y=mc.histogram_counts, marker_color=_PRIMARY, name="Simulations")
    for value, label, color in (
        (mc.p10, "P10", _MUTED),
        (mc.p50, "P50", _ACCENT),
        (mc.p90, "P90", _MUTED),
    ):
        fig.add_vline(x=value, line=dict(color=color, dash="dash"))
        fig.add_annotation(x=value, y=1.02, yref="paper", text=label, showarrow=False,
                           font=dict(color=color, size=11))
    if mc.current_price is not None:
        fig.add_vline(x=mc.current_price, line=dict(color=_WARN, width=2))
    fig.update_xaxes(title="Implied share price")
    fig.update_yaxes(title="Frequency")
    return _layout(fig, f"Monte Carlo distribution ({mc.n_simulations:,} simulations)")


def driver_tornado_chart(ranking: DriverSensitivityRanking) -> go.Figure:
    """Tornado chart of price swing by driver."""
    ranked = ranking.ranked()
    drivers = [d.driver for d in ranked][::-1]
    swings = [d.swing for d in ranked][::-1]
    fig = go.Figure(go.Bar(x=swings, y=drivers, orientation="h", marker_color=_PRIMARY))
    fig.update_xaxes(title="Implied price swing ($)")
    return _layout(fig, "Value-driver sensitivity (tornado)", height=300)


def price_history_chart(bundle: AnalysisBundle) -> go.Figure | None:
    """Closing-price history, when price bars are available."""
    bars = bundle.dataset.prices.bars
    if not bars:
        return None
    fig = go.Figure()
    fig.add_scatter(
        x=[b.date for b in bars],
        y=[b.close for b in bars],
        mode="lines",
        line=dict(color=_PRIMARY),
        name="Close",
    )
    fig.update_yaxes(title="Price")
    return _layout(fig, "Price history")
