"""The reasoning layer that drives the agent's tool-calling loop.

Two implementations behind a common :class:`LLM` interface:

* :class:`RuleBasedLLM` — a deterministic planner that inspects the query for
  intent, emits an ordered plan of tool calls, and synthesises a final answer
  from the collected tool results. It requires no network or API key, so the
  agent's tool dispatch, argument handling, and response assembly are genuinely
  exercised (and tested) offline.
* :class:`OpenAILLM` — runs the real OpenAI tool-calling loop (lazy import),
  letting the model choose tools and write the narrative.

Both are driven by the same :class:`ResearchAgent` loop via ``propose``.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from ..models.agent import AgentStep, ToolCall
from .tools import ToolSpec


class Proposal:
    """One decision from the LLM: either call tools next, or give a final answer."""

    def __init__(
        self,
        tool_calls: list[ToolCall] | None = None,
        final_answer: str | None = None,
    ):
        self.tool_calls = tool_calls or []
        self.final_answer = final_answer

    @property
    def is_final(self) -> bool:
        return self.final_answer is not None


class LLM(ABC):
    """Abstract reasoning driver for the agent loop."""

    @abstractmethod
    def propose(
        self, query: str, prior_steps: list[AgentStep], tools: list[ToolSpec]
    ) -> Proposal:
        ...


# --------------------------------------------------------------------------- #
# Rule-based (offline) planner                                                 #
# --------------------------------------------------------------------------- #
# Keyword -> tool intent mapping. Order of checks does not matter; the plan is
# assembled in a fixed, sensible sequence afterwards.
_INTENT_KEYWORDS = {
    "calculate_ratios": ["ratio", "margin", "profitab", "roe", "roic", "leverage"],
    "forecast_financials": ["forecast", "project", "three-statement", "3-statement"],
    "run_scenarios": ["scenario", "bull", "bear", "upside case", "downside case"],
    "calculate_dcf": ["dcf", "discounted cash", "intrinsic", "fair value", "worth", "value", "valuation"],
    "calculate_comps": ["comparable", "comps", "peer", "multiple", "trading multiple"],
    "calculate_precedent": ["precedent", "transaction", "acquisition", "m&a", "takeover"],
    "reverse_dcf": ["reverse", "implied growth", "priced in", "market expect", "market imply"],
    "run_sensitivity": ["sensitiv", "driv", "tornado", "what if"],
    "run_monte_carlo": ["monte carlo", "simulat", "probability", "distribution", "p10", "p90", "range"],
    "retrieve_filing_evidence": ["risk", "filing", "10-k", "10k", "disclos", "segment", "competition", "management said"],
}

# Phrases that request the full multi-method analysis.
_FULL_ANALYSIS_TRIGGERS = ["full valuation", "complete valuation", "comprehensive", "all method", "everything", "full analysis"]

# The order tools appear in a plan when multiple intents match.
_PLAN_ORDER = [
    "get_company_data",
    "calculate_ratios",
    "forecast_financials",
    "run_scenarios",
    "calculate_dcf",
    "calculate_comps",
    "calculate_precedent",
    "reverse_dcf",
    "run_sensitivity",
    "run_monte_carlo",
    "retrieve_filing_evidence",
]

# A comprehensive default plan for open-ended "analyse this company" queries.
_DEFAULT_PLAN = [
    "get_company_data",
    "calculate_ratios",
    "calculate_dcf",
    "calculate_comps",
    "reverse_dcf",
    "run_monte_carlo",
]


class RuleBasedLLM(LLM):
    """Deterministic keyword planner used for offline operation and testing."""

    def _plan(self, query: str, tool_names: set[str]) -> list[str]:
        q = query.lower()
        if any(trigger in q for trigger in _FULL_ANALYSIS_TRIGGERS):
            plan = [
                "get_company_data", "calculate_ratios", "calculate_dcf",
                "calculate_comps", "calculate_precedent", "reverse_dcf", "run_monte_carlo",
            ]
        else:
            matched = {
                tool
                for tool, keywords in _INTENT_KEYWORDS.items()
                if any(k in q for k in keywords)
            }
            if not matched:
                plan = list(_DEFAULT_PLAN)
            else:
                plan = ["get_company_data"] + [t for t in _PLAN_ORDER if t in matched]
        # Keep only available tools, dedupe, preserve order.
        seen: set[str] = set()
        ordered = []
        for tool in plan:
            if tool in tool_names and tool not in seen:
                ordered.append(tool)
                seen.add(tool)
        return ordered

    def _arguments_for(self, tool: str, query: str) -> dict:
        if tool == "retrieve_filing_evidence":
            return {"query": query, "top_k": 3}
        return {}

    def propose(
        self, query: str, prior_steps: list[AgentStep], tools: list[ToolSpec]
    ) -> Proposal:
        tool_names = {t.name for t in tools}
        plan = self._plan(query, tool_names)
        n_done = len(prior_steps)
        if n_done < len(plan):
            tool = plan[n_done]
            return Proposal(
                tool_calls=[ToolCall(tool_name=tool, arguments=self._arguments_for(tool, query))]
            )
        return Proposal(final_answer=self._summarize(query, prior_steps))

    # --- Answer synthesis ---------------------------------------------- #
    @staticmethod
    def _summarize(query: str, steps: list[AgentStep]) -> str:
        results = {s.call.tool_name: s.result.result for s in steps if s.result.ok}
        lines: list[str] = []

        company = results.get("get_company_data")
        if company:
            name = company.get("name") or company.get("ticker")
            price = company.get("price")
            head = f"{name} ({company.get('ticker')})"
            if price is not None:
                head += f" trades at ${price:,.2f}"
            lines.append(head + ".")

        ratios = results.get("calculate_ratios")
        if ratios:
            gm = ratios.get("gross_margin")
            roe = ratios.get("roe")
            bits = []
            if gm is not None:
                bits.append(f"gross margin {gm * 100:.0f}%")
            if roe is not None:
                bits.append(f"ROE {roe * 100:.0f}%")
            if bits:
                lines.append("Profitability: " + ", ".join(bits) + ".")

        dcf = results.get("calculate_dcf")
        if dcf and dcf.get("implied_share_price") is not None:
            msg = f"DCF implies ${dcf['implied_share_price']:,.2f}/share"
            up = dcf.get("upside_vs_market")
            if up is not None:
                direction = "above" if up >= 0 else "below"
                msg += f" ({abs(up) * 100:.0f}% {direction} the market price)"
            lines.append(msg + ".")

        comps = results.get("calculate_comps")
        if comps and comps.get("implied_prices"):
            prices = [p for p in comps["implied_prices"].values() if p is not None]
            if prices:
                lines.append(
                    f"Trading comps imply roughly ${min(prices):,.0f}-${max(prices):,.0f}/share."
                )

        precedent = results.get("calculate_precedent")
        if precedent and precedent.get("implied_prices"):
            prices = [p for p in precedent["implied_prices"].values() if p is not None]
            if prices:
                lines.append(
                    f"Precedent transactions (sample) imply ${min(prices):,.0f}-${max(prices):,.0f}/share."
                )

        reverse = results.get("reverse_dcf")
        if reverse and reverse.get("implied_value") is not None and reverse.get("converged"):
            lines.append(
                f"The current price implies about {reverse['implied_value'] * 100:.0f}%/yr revenue growth (reverse DCF)."
            )

        scenarios = results.get("run_scenarios")
        if scenarios and scenarios.get("terminal_revenue"):
            tr = scenarios["terminal_revenue"]
            if "Bear" in tr and "Bull" in tr:
                lines.append(
                    f"Scenario terminal revenue spans ${tr['Bear'] / 1e9:,.0f}B (bear) to ${tr['Bull'] / 1e9:,.0f}B (bull)."
                )

        mc = results.get("run_monte_carlo")
        if mc and mc.get("p50") is not None:
            msg = f"Monte Carlo P10-P90 is ${mc['p10']:,.0f}-${mc['p90']:,.0f} (median ${mc['p50']:,.0f})"
            if mc.get("prob_upside") is not None:
                msg += f", with a {mc['prob_upside'] * 100:.0f}% probability of upside"
            lines.append(msg + ".")

        sensitivity = results.get("run_sensitivity")
        if sensitivity and sensitivity.get("top_driver"):
            lines.append(f"The valuation is most sensitive to {sensitivity['top_driver']}.")

        evidence = results.get("retrieve_filing_evidence")
        if evidence and evidence.get("citations"):
            sections = [s for s in evidence.get("sections", []) if s]
            where = sections[0] if sections else evidence["citations"][0]
            lines.append(
                f"Relevant filing evidence was found in '{where}' (see {evidence['citations'][0]})."
            )

        if not lines:
            lines.append("I was unable to gather enough data to answer that.")
        lines.append("This analysis is for research purposes only and is not investment advice.")
        return " ".join(lines)


# --------------------------------------------------------------------------- #
# OpenAI tool-calling client                                                   #
# --------------------------------------------------------------------------- #
class OpenAILLM(LLM):
    """Runs the real OpenAI tool-calling loop (lazy import)."""

    SYSTEM_PROMPT = (
        "You are FinModel AI, an equity research analyst. Use the provided tools to "
        "gather data and run valuations; never compute figures yourself. Call tools as "
        "needed, then give a concise, balanced summary. All numbers must come from tools. "
        "End with a brief note that this is not investment advice."
    )

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI  # noqa: PLC0415 - lazy import
            except ImportError as exc:  # pragma: no cover - depends on environment
                raise ImportError(
                    "The 'openai' package is required for OpenAILLM. "
                    "Install it with `pip install openai`, or use RuleBasedLLM."
                ) from exc
            self._client = OpenAI()
        return self._client

    def _messages(self, query: str, prior_steps: list[AgentStep]) -> list[dict]:  # pragma: no cover
        messages: list[dict] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        for i, step in enumerate(prior_steps):
            call_id = f"call_{i}"
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": step.call.tool_name,
                                "arguments": json.dumps(step.call.arguments),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(step.result.result if step.result.ok else {"error": step.result.error}),
                }
            )
        return messages

    def propose(  # pragma: no cover - requires network/key
        self, query: str, prior_steps: list[AgentStep], tools: list[ToolSpec]
    ) -> Proposal:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=self._messages(query, prior_steps),
            tools=[t.openai_schema() for t in tools],
            tool_choice="auto",
        )
        message = response.choices[0].message
        if message.tool_calls:
            calls = [
                ToolCall(
                    tool_name=tc.function.name,
                    arguments=json.loads(tc.function.arguments or "{}"),
                )
                for tc in message.tool_calls
            ]
            return Proposal(tool_calls=calls)
        return Proposal(final_answer=message.content or "")
