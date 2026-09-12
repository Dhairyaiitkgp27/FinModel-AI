"""The agent-evaluation case library.

Fifty-seven cases spanning every kind of research query the agent should handle:
company overviews, ratios, each valuation method, forecasting, scenarios,
sensitivity, Monte Carlo, filing evidence, comprehensive analyses, and mixed /
edge cases. Each case asserts the tools the agent must call and phrases its
answer must contain.
"""
from __future__ import annotations

from evals.harness import EvalCase

_DISCLAIMER = "not investment advice"

CASES: list[EvalCase] = [
    # --- Company overview ------------------------------------------------ #
    EvalCase("overview_basic", "AAPL", "Tell me about AAPL", "overview",
             expected_tools=("get_company_data",), answer_contains=("Apple", _DISCLAIMER)),
    EvalCase("overview_price", "AAPL", "What is AAPL's stock price and market cap?", "overview",
             expected_tools=("get_company_data",), answer_contains=("Apple",)),
    EvalCase("overview_msft", "MSFT", "Give me an overview of MSFT", "overview",
             expected_tools=("get_company_data",), answer_contains=("Microsoft",)),
    EvalCase("overview_summary", "MSFT", "Summarize MSFT for me", "overview",
             expected_tools=("get_company_data",), answer_contains=(_DISCLAIMER,)),
    EvalCase("overview_what_does", "AAPL", "What does AAPL do as a business?", "overview",
             expected_tools=("get_company_data",)),

    # --- Ratios ---------------------------------------------------------- #
    EvalCase("ratios_margins", "AAPL", "What are AAPL's margins?", "ratios",
             expected_tools=("calculate_ratios",), answer_contains=("Profitability",)),
    EvalCase("ratios_profitability", "AAPL", "Show me AAPL profitability ratios", "ratios",
             expected_tools=("calculate_ratios",)),
    EvalCase("ratios_roe", "AAPL", "What is AAPL's ROE and ROIC?", "ratios",
             expected_tools=("calculate_ratios",)),
    EvalCase("ratios_leverage", "MSFT", "How leveraged is MSFT?", "ratios",
             expected_tools=("calculate_ratios",)),
    EvalCase("ratios_gross_margin", "AAPL", "What's AAPL's gross margin trend?", "ratios",
             expected_tools=("calculate_ratios",)),

    # --- DCF ------------------------------------------------------------- #
    EvalCase("dcf_worth", "AAPL", "What is AAPL worth?", "dcf",
             expected_tools=("calculate_dcf",), answer_contains=("DCF implies",)),
    EvalCase("dcf_run", "AAPL", "Run a DCF on AAPL", "dcf",
             expected_tools=("calculate_dcf",)),
    EvalCase("dcf_intrinsic", "MSFT", "What's the intrinsic value of MSFT?", "dcf",
             expected_tools=("calculate_dcf",), answer_contains=("DCF implies",)),
    EvalCase("dcf_fair_value", "AAPL", "Give me a fair value for AAPL", "dcf",
             expected_tools=("calculate_dcf",)),
    EvalCase("dcf_discounted", "MSFT", "Calculate the discounted cash flow value of MSFT", "dcf",
             expected_tools=("calculate_dcf",)),
    EvalCase("dcf_attractive", "AAPL", "Is AAPL's valuation attractive?", "dcf",
             expected_tools=("calculate_dcf",)),

    # --- Comparables ----------------------------------------------------- #
    EvalCase("comps_peers", "AAPL", "How does AAPL compare to its peers?", "comps",
             expected_tools=("calculate_comps",), answer_contains=("Trading comps",)),
    EvalCase("comps_multiples", "AAPL", "What are AAPL's trading multiples?", "comps",
             expected_tools=("calculate_comps",)),
    EvalCase("comps_value", "MSFT", "Value MSFT using comparables", "comps",
             expected_tools=("calculate_comps",)),
    EvalCase("comps_run", "AAPL", "Run comps for AAPL", "comps",
             expected_tools=("calculate_comps",)),

    # --- Precedent transactions ----------------------------------------- #
    EvalCase("precedent_apply", "AAPL", "What precedent transactions apply to AAPL?", "precedent",
             expected_tools=("calculate_precedent",), answer_contains=("Precedent transactions",)),
    EvalCase("precedent_acquirer", "AAPL", "What would an acquirer pay for AAPL based on precedent deals?",
             "precedent", expected_tools=("calculate_precedent",)),
    EvalCase("precedent_takeover", "MSFT", "Value MSFT on a takeover basis", "precedent",
             expected_tools=("calculate_precedent",)),

    # --- Reverse DCF ----------------------------------------------------- #
    EvalCase("reverse_priced_in", "AAPL", "What growth is priced into AAPL?", "reverse_dcf",
             expected_tools=("reverse_dcf",), answer_contains=("reverse DCF",)),
    EvalCase("reverse_market_expect", "MSFT", "What does the market expect for MSFT's growth?",
             "reverse_dcf", expected_tools=("reverse_dcf",)),
    EvalCase("reverse_run", "AAPL", "Run a reverse DCF on AAPL", "reverse_dcf",
             expected_tools=("reverse_dcf",)),
    EvalCase("reverse_implied", "AAPL", "What implied growth does AAPL's price suggest?", "reverse_dcf",
             expected_tools=("reverse_dcf",), answer_contains=("reverse DCF",)),

    # --- Scenarios ------------------------------------------------------- #
    EvalCase("scenarios_bull_bear", "AAPL", "Run bull and bear scenarios for AAPL", "scenarios",
             expected_tools=("run_scenarios",), answer_contains=("Scenario terminal revenue",)),
    EvalCase("scenarios_upside", "MSFT", "What's the upside case for MSFT?", "scenarios",
             expected_tools=("run_scenarios",)),
    EvalCase("scenarios_analysis", "AAPL", "Show me scenario analysis for AAPL", "scenarios",
             expected_tools=("run_scenarios",)),
    EvalCase("scenarios_bear", "AAPL", "How does AAPL look in a bear case?", "scenarios",
             expected_tools=("run_scenarios",)),

    # --- Forecasting ----------------------------------------------------- #
    EvalCase("forecast_financials", "AAPL", "Forecast AAPL's financials", "forecast",
             expected_tools=("forecast_financials",)),
    EvalCase("forecast_project", "MSFT", "Project MSFT revenue over the next few years", "forecast",
             expected_tools=("forecast_financials",)),
    EvalCase("forecast_three_statement", "AAPL", "Build a three-statement model for AAPL", "forecast",
             expected_tools=("forecast_financials",)),

    # --- Sensitivity ----------------------------------------------------- #
    EvalCase("sensitivity_drivers", "AAPL", "What drives AAPL's valuation the most?", "sensitivity",
             expected_tools=("run_sensitivity",), answer_contains=("most sensitive to",)),
    EvalCase("sensitivity_run", "MSFT", "Run a sensitivity analysis on MSFT", "sensitivity",
             expected_tools=("run_sensitivity",)),
    EvalCase("sensitivity_wacc", "AAPL", "How sensitive is AAPL to the WACC? What if it changes?",
             "sensitivity", expected_tools=("run_sensitivity",)),

    # --- Monte Carlo ----------------------------------------------------- #
    EvalCase("mc_run", "AAPL", "Run a Monte Carlo simulation for AAPL", "monte_carlo",
             expected_tools=("run_monte_carlo",), answer_contains=("Monte Carlo P10-P90",)),
    EvalCase("mc_probability", "AAPL", "What's the probability AAPL is undervalued?", "monte_carlo",
             expected_tools=("run_monte_carlo",)),
    EvalCase("mc_range", "MSFT", "Give me a P10 to P90 range for MSFT", "monte_carlo",
             expected_tools=("run_monte_carlo",)),
    EvalCase("mc_distribution", "AAPL", "Simulate AAPL's valuation distribution", "monte_carlo",
             expected_tools=("run_monte_carlo",), answer_contains=("Monte Carlo P10-P90",)),

    # --- Filing evidence (RAG) ------------------------------------------ #
    EvalCase("rag_risk", "AAPL", "What are the main risk factors?", "filings",
             expected_tools=("retrieve_filing_evidence",), answer_contains=("filing evidence",)),
    EvalCase("rag_10k_competition", "MSFT", "What does the 10-K say about competition?", "filings",
             expected_tools=("retrieve_filing_evidence",)),
    EvalCase("rag_segments", "AAPL", "Summarize the business segments disclosed in the filing", "filings",
             expected_tools=("retrieve_filing_evidence",)),
    EvalCase("rag_disclose", "MSFT", "What risks does the company disclose?", "filings",
             expected_tools=("retrieve_filing_evidence",), answer_contains=("filing evidence",)),

    # --- Comprehensive --------------------------------------------------- #
    EvalCase("full_valuation", "AAPL", "Give me a full valuation of AAPL", "comprehensive",
             expected_tools=("calculate_dcf", "calculate_comps", "calculate_precedent",
                             "reverse_dcf", "run_monte_carlo"),
             answer_contains=("DCF implies", "Monte Carlo P10-P90"), min_steps=5),
    EvalCase("full_comprehensive", "MSFT", "Do a comprehensive analysis of MSFT", "comprehensive",
             expected_tools=("calculate_dcf", "calculate_comps", "reverse_dcf", "run_monte_carlo"),
             min_steps=5),
    EvalCase("full_all_methods", "AAPL", "Value AAPL using all methods", "comprehensive",
             expected_tools=("calculate_dcf", "calculate_comps", "calculate_precedent"), min_steps=5),
    EvalCase("full_everything", "MSFT", "Tell me everything about MSFT's valuation", "comprehensive",
             expected_tools=("calculate_dcf", "run_monte_carlo"), min_steps=5),
    EvalCase("full_complete", "AAPL", "Complete valuation of AAPL please", "comprehensive",
             expected_tools=("calculate_dcf", "calculate_comps", "reverse_dcf"), min_steps=5),

    # --- Mixed / edge ---------------------------------------------------- #
    EvalCase("edge_ticker_only", "AAPL", "AAPL", "edge",
             expected_tools=("get_company_data",), answer_contains=(_DISCLAIMER,)),
    EvalCase("edge_should_invest", "MSFT", "Should I invest in MSFT?", "edge",
             expected_tools=("get_company_data",), answer_contains=(_DISCLAIMER,)),
    EvalCase("edge_value_and_risk", "AAPL", "What is the value and the risks of AAPL?", "edge",
             expected_tools=("calculate_dcf", "retrieve_filing_evidence")),
    EvalCase("edge_dcf_and_comps", "AAPL", "Give me a DCF and a comps valuation for AAPL", "edge",
             expected_tools=("calculate_dcf", "calculate_comps")),
    EvalCase("edge_growth_and_scenarios", "MSFT",
             "What growth is priced in, and run bull/bear scenarios for MSFT", "edge",
             expected_tools=("reverse_dcf", "run_scenarios")),
]
