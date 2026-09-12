"""FinModel AI entry point.

Run ``streamlit run app.py`` to launch the interactive dashboard (Phase 12).
Run ``python app.py`` for a lightweight smoke test that verifies the package
imports, configuration loads, and the full analysis stack executes end-to-end on
bundled sample data — keeping the project runnable at every phase.
"""
from __future__ import annotations

from config import get_settings
from core import __version__
from core.data import available_sample_tickers, load_and_validate
from core.utils import get_logger

logger = get_logger("finmodel.app")


def smoke_test() -> None:
    """Load a sample company through the data layer and print a short report."""
    settings = get_settings()

    logger.info("FinModel AI v%s", __version__)
    logger.info("Data provider: %s (live=%s)", settings.data_provider, settings.use_live_data)
    logger.info("OpenAI configured: %s", settings.has_openai())

    print(
        f"FinModel AI v{__version__} — Provider={settings.data_provider}, "
        f"OpenAI={'yes' if settings.has_openai() else 'no'}."
    )

    # Phase 2: exercise the data layer against bundled sample data. Force the
    # local provider so the smoke test never depends on the network.
    samples = available_sample_tickers()
    print(f"Bundled sample tickers: {', '.join(samples) or 'none'}")

    for ticker in samples:
        dataset, report = load_and_validate(ticker, provider="local")
        income = dataset.financials.latest_income()
        balance = dataset.financials.latest_balance()
        cash_flow = dataset.financials.latest_cash_flow()
        market = dataset.market_data

        revenue_b = (income.revenue or 0) / 1e9
        gross_margin = (income.gross_margin or 0) * 100
        fcf_b = (cash_flow.free_cash_flow or 0) / 1e9 if cash_flow else 0.0
        market_cap_t = (market.market_cap or 0) / 1e12 if market else 0.0
        balanced = balance.is_balanced() if balance else None

        print(
            f"  {ticker}: {income.period.label()} revenue ${revenue_b:,.0f}B, "
            f"gross margin {gross_margin:.1f}%, FCF ${fcf_b:,.0f}B, "
            f"market cap ${market_cap_t:.2f}T, balance ok={balanced}, "
            f"validation={'clean' if report.is_valid else 'issues'}"
        )

    # Phase 4: project a linked three-statement model for the first sample and
    # confirm the projected balance sheets balance.
    if samples:
        from core.forecasting import build_scenario_from_history, forecast_statements

        ticker = samples[0]
        dataset, _ = load_and_validate(ticker, provider="local")
        scenario = build_scenario_from_history(
            dataset.financials, revenue_growth=0.06, horizon_years=5, name="Base"
        )
        forecast = forecast_statements(dataset.financials, scenario)
        final = forecast.statements.income_statements[-1]
        print(
            f"5y forecast ({ticker}, +6%/yr): "
            f"{final.period.label()} revenue ${(final.revenue or 0) / 1e9:,.0f}B, "
            f"terminal-year FCFF ${forecast.free_cash_flows[-1] / 1e9:,.0f}B, "
            f"balance sheets balance every year: {forecast.balance_checks_passed}"
        )

        # Phase 5: bull/base/bear scenario spread on terminal-year revenue.
        from core.forecasting import build_and_compare, terminal_values

        comparison = build_and_compare(dataset.financials, base_growth=0.06, horizon_years=5)
        rev = terminal_values(comparison, "revenue")
        print(
            f"Scenario spread ({ticker}, {final.period.label()} revenue): "
            f"bear ${rev['Bear'] / 1e9:,.0f}B / base ${rev['Base'] / 1e9:,.0f}B / "
            f"bull ${rev['Bull'] / 1e9:,.0f}B"
        )

        # Phase 6: end-to-end DCF valuation from the same dataset.
        from core.valuation import dcf_valuation

        dcf = dcf_valuation(
            dataset, base_growth=0.06, horizon_years=5, terminal_growth=0.025
        )
        market_price = dataset.market_data.price if dataset.market_data else None
        vs_market = f" vs market ${market_price:,.2f}" if market_price else ""
        print(
            f"DCF ({ticker}): WACC {dcf.wacc * 100:.1f}%, "
            f"implied ${dcf.implied_share_price:,.2f}/share{vs_market}, "
            f"terminal value {dcf.terminal_value_pct * 100:.0f}% of EV"
        )

        # Phase 7: market-based valuation methods (comps + precedents).
        from core.valuation import build_comps_from_dataset, build_precedent_from_dataset

        comps = build_comps_from_dataset(dataset, statistic="median")
        comps_prices = [
            v.implied_share_price for v in comps.valuations if v.implied_share_price
        ]
        precedent = build_precedent_from_dataset(dataset, statistic="median")
        prec_prices = [
            v.implied_share_price for v in precedent.valuations if v.implied_share_price
        ]
        if comps_prices:
            print(
                f"Comps ({ticker}, {len(comps.peers)} peers): implied "
                f"${min(comps_prices):,.0f}–${max(comps_prices):,.0f}/share (median multiples)"
            )
        if prec_prices:
            print(
                f"Precedents ({ticker}, sample): implied "
                f"${min(prec_prices):,.0f}–${max(prec_prices):,.0f}/share"
            )

        # Phase 8: reverse DCF (what growth does today's price imply?).
        from core.valuation import reverse_dcf_valuation

        reverse = reverse_dcf_valuation(dataset, terminal_growth=0.025, horizon_years=5)
        if reverse.converged:
            print(
                f"Reverse DCF ({ticker}): market price implies "
                f"{reverse.implied_value * 100:.1f}%/yr revenue growth"
            )

        # Phase 9: Monte Carlo valuation distribution.
        from core.valuation import monte_carlo_valuation

        mc = monte_carlo_valuation(
            dataset, base_growth=0.06, horizon_years=5, terminal_growth=0.025,
            n_simulations=10_000, seed=42,
        )
        upside = f", P(upside) {mc.prob_upside * 100:.0f}%" if mc.prob_upside is not None else ""
        print(
            f"Monte Carlo ({ticker}, {mc.n_simulations:,} sims): "
            f"P10 ${mc.p10:,.0f} / P50 ${mc.p50:,.0f} / P90 ${mc.p90:,.0f}{upside}"
        )

    # Phase 10: document RAG over a bundled sample filing (fully offline).
    from pathlib import Path

    from core.rag import build_rag_engine

    sample_doc = Path(__file__).resolve().parent / "data" / "sample" / "SAMPLE_10K.txt"
    if sample_doc.exists():
        rag = build_rag_engine()
        n_chunks = rag.ingest_file(sample_doc, doc_id="NMBS", document_name="Nimbus 10-K (sample)")
        result = rag.answer("What are the main risk factors?", top_k=1)
        top = result.sources[0]
        print(
            f"RAG (sample 10-K, {n_chunks} chunks): top match for 'risk factors' is "
            f"section '{top.chunk.section}' — cited as {result.citations[0]}"
        )

    # Phase 11: the research agent orchestrating the engines end-to-end.
    if samples:
        from core.agents import build_agent

        agent = build_agent(provider="local", index_sample_filing=True)
        response = agent.run(samples[0], "Give me a full valuation")
        print(
            f"Agent ({samples[0]}): ran {len(response.steps)} tools "
            f"({', '.join(response.tools_used)})"
        )
        print(f"  {response.answer}")

    # Phase 13: generate Excel + PDF reports for the first sample company.
    if samples:
        import tempfile

        from core.analysis import run_full_analysis
        from core.outputs import build_excel_report, build_pdf_report

        bundle = run_full_analysis(samples[0], provider="local")
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = build_excel_report(bundle, Path(tmp) / f"{samples[0]}.xlsx")
            pdf = build_pdf_report(bundle, Path(tmp) / f"{samples[0]}.pdf")
            print(
                f"Reports ({samples[0]}): Excel {xlsx.stat().st_size:,} bytes, "
                f"PDF {pdf.stat().st_size:,} bytes generated."
            )

    print("Interactive dashboard: run `streamlit run app.py` (requires `pip install -r requirements.txt`).")


def _running_in_streamlit() -> bool:
    """True when this module is being executed by ``streamlit run``."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__":
    if _running_in_streamlit():
        from ui.dashboard import main

        main()
    else:
        smoke_test()
