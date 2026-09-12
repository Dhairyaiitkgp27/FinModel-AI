"""The Streamlit dashboard for FinModel AI.

This module is imported only at runtime under ``streamlit run app.py``; it depends
on Streamlit and is therefore not imported by the test suite (its syntax is still
validated by compilation). It wires the deterministic engines and Plotly charts
into an interactive, tabbed dashboard with an assumptions sidebar and a chat box
to the research agent.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from core.outputs import build_excel_report, build_pdf_report
from ui import charts
from ui.analysis import AnalysisAssumptions, AnalysisBundle, run_full_analysis
from ui.formatting import (
    format_currency,
    format_large,
    format_multiple,
    format_pct,
    format_signed_pct,
    upside_label,
)

PAGE_TITLE = "FinModel AI — Equity Research & Valuation"


# --------------------------------------------------------------------------- #
# Cached analysis (keyed on primitive arguments)                              #
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Running valuation engines…")
def _cached_analysis(
    ticker: str,
    provider: str,
    base_growth: float,
    horizon_years: int,
    terminal_growth: float,
    n_simulations: int,
    seed: int,
    comps_statistic: str,
) -> AnalysisBundle:
    return run_full_analysis(
        ticker,
        provider=provider,
        assumptions=AnalysisAssumptions(
            base_growth=base_growth,
            horizon_years=horizon_years,
            terminal_growth=terminal_growth,
            n_simulations=n_simulations,
            seed=seed,
            comps_statistic=comps_statistic,
        ),
    )


# --------------------------------------------------------------------------- #
# Sidebar                                                                     #
# --------------------------------------------------------------------------- #
def render_sidebar() -> tuple[str, str, AnalysisAssumptions]:
    st.sidebar.title("FinModel AI")
    st.sidebar.caption("AI-powered equity research & valuation")

    ticker = st.sidebar.text_input("Ticker", value="AAPL").strip().upper()
    provider = st.sidebar.selectbox(
        "Data source",
        options=["local", "yfinance"],
        index=0,
        help="'local' uses bundled sample data; 'yfinance' fetches live data (network required).",
    )

    st.sidebar.subheader("Assumptions")
    base_growth = st.sidebar.slider("Revenue growth", -0.10, 0.30, 0.06, 0.01)
    horizon_years = st.sidebar.slider("Forecast years", 3, 10, 5)
    terminal_growth = st.sidebar.slider("Terminal growth", 0.0, 0.05, 0.025, 0.005)
    n_simulations = st.sidebar.select_slider(
        "Monte Carlo simulations", options=[1_000, 5_000, 10_000, 25_000, 50_000], value=10_000
    )
    comps_statistic = st.sidebar.radio("Comps statistic", ["median", "mean"], horizontal=True)

    assumptions = AnalysisAssumptions(
        base_growth=base_growth,
        horizon_years=horizon_years,
        terminal_growth=terminal_growth,
        n_simulations=n_simulations,
        comps_statistic=comps_statistic,
    )
    return ticker, provider, assumptions


# --------------------------------------------------------------------------- #
# Tabs                                                                        #
# --------------------------------------------------------------------------- #
def render_overview(bundle: AnalysisBundle) -> None:
    ds = bundle.dataset
    st.subheader(f"{ds.profile.name or ds.ticker} ({ds.ticker})")
    meta = " · ".join(x for x in [ds.profile.sector, ds.profile.industry, ds.profile.country] if x)
    if meta:
        st.caption(meta)
    if ds.is_sample:
        st.info("Showing bundled **sample data** (approximate figures from public filings).")

    market = ds.market_data
    dcf = bundle.dcf
    cols = st.columns(4)
    cols[0].metric("Price", format_currency(bundle.market_price))
    cols[1].metric("Market cap", format_large(market.market_cap) if market else "—")
    latest = ds.financials.latest_income()
    cols[2].metric("Revenue", format_large(latest.revenue) if latest else "—")
    if dcf is not None:
        cols[3].metric(
            "DCF value",
            format_currency(dcf.implied_share_price),
            upside_label(dcf.implied_share_price, bundle.market_price),
        )

    if not bundle.validation.is_valid:
        st.warning(f"Data quality: {bundle.validation.summary()}")

    fig = charts.price_history_chart(bundle)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    if bundle.warnings:
        with st.expander("Analysis warnings"):
            for w in bundle.warnings:
                st.text(w)

    st.markdown("**Export**")
    c1, c2 = st.columns(2)
    c1.download_button(
        "⬇️ Excel report",
        data=_report_bytes(build_excel_report, bundle, ".xlsx"),
        file_name=f"{ds.ticker}_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    c2.download_button(
        "⬇️ PDF report",
        data=_report_bytes(build_pdf_report, bundle, ".pdf"),
        file_name=f"{ds.ticker}_report.pdf",
        mime="application/pdf",
    )


def _report_bytes(builder, bundle: AnalysisBundle, suffix: str) -> bytes:
    """Generate a report to a temp file and return its bytes for download."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = tmp.name
    try:
        builder(bundle, path)
        return Path(path).read_bytes()
    finally:
        if os.path.exists(path):
            os.unlink(path)


def render_financials(bundle: AnalysisBundle) -> None:
    ratios = bundle.ratios
    st.plotly_chart(charts.margin_trend_chart(ratios), use_container_width=True)
    st.plotly_chart(charts.revenue_forecast_chart(bundle), use_container_width=True)

    if bundle.forecast is not None:
        ok = bundle.forecast.balance_checks_passed
        st.caption(
            f"Projected balance sheets balance every year: **{'yes' if ok else 'no'}**."
        )

    st.markdown("**Key ratios by period**")
    rows = []
    for r in ratios.periods:
        rows.append(
            {
                "Period": r.period.label(),
                "Rev growth": format_signed_pct(r.revenue_growth),
                "Gross margin": format_pct(r.gross_margin),
                "EBITDA margin": format_pct(r.ebitda_margin),
                "Net margin": format_pct(r.net_margin),
                "ROE": format_pct(r.roe),
                "ROIC": format_pct(r.roic),
                "Net debt/EBITDA": format_multiple(r.net_debt_to_ebitda),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_valuation(bundle: AnalysisBundle) -> None:
    st.plotly_chart(charts.valuation_football_field(bundle), use_container_width=True)

    dcf = bundle.dcf
    reverse = bundle.reverse_dcf
    cols = st.columns(4)
    if dcf is not None:
        cols[0].metric("DCF value", format_currency(dcf.implied_share_price))
        cols[1].metric("WACC", format_pct(dcf.wacc))
        cols[2].metric("Terminal value", format_pct(dcf.terminal_value_pct))
    if reverse is not None and reverse.converged:
        cols[3].metric("Market-implied growth", format_pct(reverse.implied_value))

    if bundle.comps is not None:
        st.markdown("**Trading comparables**")
        rows = []
        stats_by_metric = {s.metric: s for s in bundle.comps.stats}
        for v in bundle.comps.valuations:
            s = stats_by_metric.get(v.metric)
            rows.append(
                {
                    "Metric": v.metric,
                    "Peer median": format_multiple(s.median if s else None),
                    "Applied": format_multiple(v.applied_multiple),
                    "Implied price": format_currency(v.implied_share_price),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(f"{len(bundle.comps.peers)} peers.")

    if bundle.precedent is not None and bundle.precedent.contains_sample_data:
        st.caption("Precedent transactions use **illustrative sample** deal multiples.")


def render_scenarios_sensitivity(bundle: AnalysisBundle) -> None:
    if bundle.scenarios is not None:
        st.plotly_chart(charts.scenario_revenue_chart(bundle.scenarios), use_container_width=True)

    col1, col2 = st.columns(2)
    if bundle.sensitivity is not None:
        with col1:
            st.plotly_chart(charts.sensitivity_heatmap(bundle.sensitivity), use_container_width=True)
    if bundle.driver_ranking is not None:
        with col2:
            st.plotly_chart(charts.driver_tornado_chart(bundle.driver_ranking), use_container_width=True)

    mc = bundle.monte_carlo
    if mc is not None:
        st.plotly_chart(charts.monte_carlo_histogram(mc), use_container_width=True)
        cols = st.columns(5)
        cols[0].metric("P10", format_currency(mc.p10))
        cols[1].metric("P50", format_currency(mc.p50))
        cols[2].metric("P90", format_currency(mc.p90))
        cols[3].metric("Mean", format_currency(mc.mean))
        if mc.prob_upside is not None:
            cols[4].metric("P(upside)", format_pct(mc.prob_upside))


def render_research(ticker: str, provider: str) -> None:
    st.markdown(
        "Ask the research agent a question. It selects and runs the valuation tools, "
        "then summarises the results — every number comes from the deterministic engines."
    )
    settings = _get_settings()
    if settings is not None and settings.has_openai():
        st.caption("Using the OpenAI tool-calling agent.")
    else:
        st.caption("Using the offline rule-based agent (set OPENAI_API_KEY for LLM narration).")

    question = st.text_input(
        "Your question", value=f"Give me a full valuation of {ticker}", key="agent_question"
    )
    if st.button("Run analysis", type="primary") and question:
        from core.agents import build_agent

        agent = build_agent(
            provider=provider, settings=settings, use_openai=True, index_sample_filing=True
        )
        with st.spinner("The agent is working…"):
            response = agent.run(ticker, question)
        st.markdown(f"**Answer**\n\n{response.answer}")
        with st.expander(f"Tool trace ({len(response.steps)} steps)"):
            for i, step in enumerate(response.steps, start=1):
                status = "✅" if step.result.ok else "⚠️"
                st.markdown(f"{status} **{i}. {step.call.tool_name}**")
                st.json(step.result.result if step.result.ok else {"error": step.result.error})


def _get_settings():
    try:
        from config import get_settings

        return get_settings()
    except Exception:  # pragma: no cover - config always importable
        return None


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="📈", layout="wide")
    st.title("FinModel AI")
    st.caption("AI-powered equity research & valuation — deterministic engine, LLM orchestration")

    ticker, provider, assumptions = render_sidebar()
    if not ticker:
        st.info("Enter a ticker in the sidebar to begin.")
        return

    try:
        bundle = _cached_analysis(
            ticker,
            provider,
            assumptions.base_growth,
            assumptions.horizon_years,
            assumptions.terminal_growth,
            assumptions.n_simulations,
            assumptions.seed,
            assumptions.comps_statistic,
        )
    except Exception as exc:  # noqa: BLE001 - surface load/analysis errors to the user
        st.error(f"Could not analyse {ticker}: {exc}")
        return

    tabs = st.tabs(
        ["Overview", "Financials", "Valuation", "Scenarios & Sensitivity", "Research Assistant"]
    )
    with tabs[0]:
        render_overview(bundle)
    with tabs[1]:
        render_financials(bundle)
    with tabs[2]:
        render_valuation(bundle)
    with tabs[3]:
        render_scenarios_sensitivity(bundle)
    with tabs[4]:
        render_research(ticker, provider)

    st.divider()
    st.caption("For research and educational purposes only. Not investment advice.")
