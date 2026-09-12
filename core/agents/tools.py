"""Typed tools that expose the deterministic engines to the research agent.

Each tool has a name, a natural-language description, a JSON-schema parameter
spec (used directly as an OpenAI function-calling schema), and a handler that
calls into the Phase 2-10 engines. Handlers return compact, JSON-serialisable
dictionaries so results can be fed back to the model and stored in
:class:`ToolResult`.

The agent never does arithmetic: every number a tool returns comes from the
deterministic Python engines. The LLM only decides which tools to call and how
to narrate their results.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..analysis import compute_ratios
from ..data import load_company_dataset
from ..forecasting import (
    build_and_compare,
    build_scenario_from_history,
    forecast_statements,
    terminal_values,
)
from ..valuation import (
    build_comps_from_dataset,
    build_dcf_sensitivity,
    build_precedent_from_dataset,
    dcf_valuation,
    driver_sensitivity,
    monte_carlo_valuation,
    reverse_dcf_valuation,
)


class AgentContext:
    """Shared state for a research session: the loaded dataset and optional RAG."""

    def __init__(
        self,
        *,
        provider: str = "local",
        sample_dir: str | Path | None = None,
        settings: Any = None,
        rag_engine: Any = None,
    ):
        self.provider = provider
        self.sample_dir = sample_dir
        self.settings = settings
        self.rag_engine = rag_engine
        self.ticker: str | None = None
        self.dataset: Any = None

    def ensure_dataset(self, ticker: str | None = None) -> Any:
        """Load the dataset for ``ticker`` (or the session ticker) if not already loaded."""
        ticker = (ticker or self.ticker or "").strip().upper()
        if not ticker:
            raise ValueError("No ticker specified for this research session.")
        if self.dataset is None or self.ticker != ticker:
            self.dataset = load_company_dataset(
                ticker, provider=self.provider, sample_dir=self.sample_dir
            )
            self.ticker = ticker
        return self.dataset


@dataclass
class ToolSpec:
    """A single agent tool: schema plus handler."""

    name: str
    description: str
    parameters: dict
    handler: Callable[[AgentContext, dict], Any]

    def openai_schema(self) -> dict:
        """Return the OpenAI function-calling schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# --------------------------------------------------------------------------- #
# Small argument helpers                                                       #
# --------------------------------------------------------------------------- #
def _num(args: dict, key: str, default: float) -> float:
    value = args.get(key, default)
    return float(value) if value is not None else default


def _int(args: dict, key: str, default: int) -> int:
    value = args.get(key, default)
    return int(value) if value is not None else default


def _round(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


# --------------------------------------------------------------------------- #
# Tool handlers                                                                #
# --------------------------------------------------------------------------- #
def _get_company_data(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    income = ds.financials.latest_income()
    market = ds.market_data
    return {
        "ticker": ds.ticker,
        "name": ds.profile.name,
        "sector": ds.profile.sector,
        "currency": ds.currency.value,
        "price": _round(market.price, 2) if market else None,
        "market_cap": _round(market.market_cap, 0) if market else None,
        "latest_period": income.period.label() if income else None,
        "revenue": _round(income.revenue, 0) if income else None,
        "net_income": _round(income.net_income, 0) if income else None,
        "is_sample": ds.is_sample,
    }


def _calculate_ratios(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    latest = compute_ratios(ds.financials).latest
    if latest is None:
        return {"error": "No ratios could be computed."}
    return {
        "period": latest.period.label(),
        "gross_margin": _round(latest.gross_margin),
        "ebitda_margin": _round(latest.ebitda_margin),
        "net_margin": _round(latest.net_margin),
        "roe": _round(latest.roe),
        "roic": _round(latest.roic),
        "current_ratio": _round(latest.current_ratio),
        "net_debt_to_ebitda": _round(latest.net_debt_to_ebitda),
        "revenue_growth": _round(latest.revenue_growth),
    }


def _forecast_financials(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    growth = _num(args, "revenue_growth", 0.06)
    horizon = _int(args, "horizon_years", 5)
    scenario = build_scenario_from_history(ds.financials, growth, horizon)
    result = forecast_statements(ds.financials, scenario)
    return {
        "revenue_growth": growth,
        "horizon_years": horizon,
        "terminal_year": result.statements.income_statements[-1].period.label(),
        "terminal_revenue": _round(result.revenue_path[-1], 0),
        "terminal_fcff": _round(result.free_cash_flows[-1], 0),
        "balance_checks_passed": result.balance_checks_passed,
    }


def _run_scenarios(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    growth = _num(args, "base_growth", 0.06)
    horizon = _int(args, "horizon_years", 5)
    comparison = build_and_compare(ds.financials, growth, horizon)
    revenue = terminal_values(comparison, "revenue")
    fcff = terminal_values(comparison, "free_cash_flow")
    return {
        "horizon_years": horizon,
        "terminal_revenue": {k: _round(v, 0) for k, v in revenue.items()},
        "terminal_fcff": {k: _round(v, 0) for k, v in fcff.items()},
    }


def _calculate_dcf(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    result = dcf_valuation(
        ds,
        base_growth=_num(args, "revenue_growth", 0.06),
        horizon_years=_int(args, "horizon_years", 5),
        terminal_growth=_num(args, "terminal_growth", 0.025),
    )
    market = ds.market_data.price if ds.market_data else None
    upside = None
    if market:
        upside = (result.implied_share_price - market) / market
    return {
        "implied_share_price": _round(result.implied_share_price, 2),
        "market_price": _round(market, 2) if market else None,
        "upside_vs_market": _round(upside),
        "wacc": _round(result.wacc),
        "enterprise_value": _round(result.enterprise_value, 0),
        "terminal_value_pct": _round(result.terminal_value_pct),
    }


def _calculate_comps(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    statistic = str(args.get("statistic", "median"))
    result = build_comps_from_dataset(ds, statistic=statistic)
    return {
        "statistic": statistic,
        "peer_count": len(result.peers),
        "implied_prices": {
            v.metric: _round(v.implied_share_price, 2)
            for v in result.valuations
            if v.implied_share_price is not None
        },
    }


def _calculate_precedent(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    statistic = str(args.get("statistic", "median"))
    result = build_precedent_from_dataset(ds, statistic=statistic)
    return {
        "statistic": statistic,
        "contains_sample_data": result.contains_sample_data,
        "implied_prices": {
            v.metric: _round(v.implied_share_price, 2)
            for v in result.valuations
            if v.implied_share_price is not None
        },
    }


def _reverse_dcf(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    result = reverse_dcf_valuation(
        ds,
        terminal_growth=_num(args, "terminal_growth", 0.025),
        horizon_years=_int(args, "horizon_years", 5),
    )
    return {
        "solved_for": result.solved_for.value,
        "implied_value": _round(result.implied_value),
        "market_price": _round(result.target_price, 2),
        "converged": result.converged,
    }


def _run_sensitivity(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    growth = _num(args, "revenue_growth", 0.06)
    horizon = _int(args, "horizon_years", 5)
    terminal_growth = _num(args, "terminal_growth", 0.025)
    grid = build_dcf_sensitivity(
        ds, base_growth=growth, horizon_years=horizon, terminal_growth=terminal_growth
    )
    ranking = driver_sensitivity(
        ds, base_growth=growth, horizon_years=horizon, terminal_growth=terminal_growth
    )
    ranked = ranking.ranked()
    return {
        "base_value": _round(grid.base_value, 2),
        "wacc_axis": [_round(v) for v in grid.row_axis.values],
        "terminal_growth_axis": [_round(v) for v in grid.col_axis.values],
        "top_driver": ranked[0].driver if ranked else None,
        "driver_swings": {d.driver: _round(d.swing, 2) for d in ranked},
    }


def _run_monte_carlo(ctx: AgentContext, args: dict) -> dict:
    ds = ctx.ensure_dataset(args.get("ticker"))
    result = monte_carlo_valuation(
        ds,
        base_growth=_num(args, "revenue_growth", 0.06),
        horizon_years=_int(args, "horizon_years", 5),
        terminal_growth=_num(args, "terminal_growth", 0.025),
        n_simulations=_int(args, "n_simulations", 10_000),
        seed=_int(args, "seed", 42),
    )
    return {
        "n_simulations": result.n_simulations,
        "p10": _round(result.p10, 2),
        "p50": _round(result.p50, 2),
        "p90": _round(result.p90, 2),
        "prob_upside": _round(result.prob_upside),
        "current_price": _round(result.current_price, 2) if result.current_price else None,
    }


def _retrieve_filing_evidence(ctx: AgentContext, args: dict) -> dict:
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "A 'query' string is required."}
    if ctx.rag_engine is None or len(ctx.rag_engine) == 0:
        return {"note": "No filings are indexed for this session."}
    top_k = _int(args, "top_k", 3)
    answer = ctx.rag_engine.answer(query, top_k=top_k)
    return {
        "answer": answer.answer,
        "citations": answer.citations,
        "sections": [s.chunk.section for s in answer.sources],
    }


# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #
_TICKER_PROP = {"ticker": {"type": "string", "description": "Company ticker (optional; defaults to the session ticker)."}}
_GROWTH_PROPS = {
    "revenue_growth": {"type": "number", "description": "Annual revenue growth assumption (e.g. 0.06)."},
    "horizon_years": {"type": "integer", "description": "Forecast horizon in years."},
    "terminal_growth": {"type": "number", "description": "Perpetuity growth rate (e.g. 0.025)."},
}

TOOLS: list[ToolSpec] = [
    ToolSpec(
        "get_company_data",
        "Load a company's profile, latest market data, and headline financials.",
        {"type": "object", "properties": dict(_TICKER_PROP), "required": []},
        _get_company_data,
    ),
    ToolSpec(
        "calculate_ratios",
        "Compute the latest profitability, return, liquidity, and leverage ratios.",
        {"type": "object", "properties": dict(_TICKER_PROP), "required": []},
        _calculate_ratios,
    ),
    ToolSpec(
        "forecast_financials",
        "Project a linked three-statement model and return the terminal-year summary.",
        {"type": "object", "properties": {**_TICKER_PROP,
            "revenue_growth": _GROWTH_PROPS["revenue_growth"],
            "horizon_years": _GROWTH_PROPS["horizon_years"]}, "required": []},
        _forecast_financials,
    ),
    ToolSpec(
        "run_scenarios",
        "Run bull/base/bear scenarios and return terminal-year revenue and free cash flow.",
        {"type": "object", "properties": {**_TICKER_PROP,
            "base_growth": {"type": "number", "description": "Base-case revenue growth."},
            "horizon_years": _GROWTH_PROPS["horizon_years"]}, "required": []},
        _run_scenarios,
    ),
    ToolSpec(
        "calculate_dcf",
        "Run a discounted cash flow valuation and return the implied share price.",
        {"type": "object", "properties": {**_TICKER_PROP, **_GROWTH_PROPS}, "required": []},
        _calculate_dcf,
    ),
    ToolSpec(
        "calculate_comps",
        "Value the company against trading peers using EV/Revenue, EV/EBITDA, P/E, and P/B.",
        {"type": "object", "properties": {**_TICKER_PROP,
            "statistic": {"type": "string", "enum": ["median", "mean"], "description": "Summary statistic."}},
         "required": []},
        _calculate_comps,
    ),
    ToolSpec(
        "calculate_precedent",
        "Value the company against precedent M&A transaction multiples (illustrative sample data).",
        {"type": "object", "properties": {**_TICKER_PROP,
            "statistic": {"type": "string", "enum": ["median", "mean"]}}, "required": []},
        _calculate_precedent,
    ),
    ToolSpec(
        "reverse_dcf",
        "Solve for the revenue growth the current market price implies.",
        {"type": "object", "properties": {**_TICKER_PROP,
            "terminal_growth": _GROWTH_PROPS["terminal_growth"],
            "horizon_years": _GROWTH_PROPS["horizon_years"]}, "required": []},
        _reverse_dcf,
    ),
    ToolSpec(
        "run_sensitivity",
        "Build a WACC x terminal-growth sensitivity grid and rank the value drivers.",
        {"type": "object", "properties": {**_TICKER_PROP, **_GROWTH_PROPS}, "required": []},
        _run_sensitivity,
    ),
    ToolSpec(
        "run_monte_carlo",
        "Run a Monte Carlo valuation and return the P10/P50/P90 range and upside probability.",
        {"type": "object", "properties": {**_TICKER_PROP, **_GROWTH_PROPS,
            "n_simulations": {"type": "integer", "description": "Number of simulations."}},
         "required": []},
        _run_monte_carlo,
    ),
    ToolSpec(
        "retrieve_filing_evidence",
        "Retrieve and cite relevant passages from indexed filings to answer a qualitative question.",
        {"type": "object", "properties": {
            "query": {"type": "string", "description": "The question to search the filings for."},
            "top_k": {"type": "integer", "description": "Number of passages to retrieve."}},
         "required": ["query"]},
        _retrieve_filing_evidence,
    ),
]

TOOLS_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}
