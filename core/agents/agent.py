"""The research agent loop.

:class:`ResearchAgent` drives an :class:`LLM` through a tool-calling loop: ask
the model for the next action, execute any requested tools against the
deterministic engines, feed the results back, and repeat until the model returns
a final answer (or a step budget is exhausted). Every tool call and its result
are recorded as an :class:`AgentStep`, so the returned :class:`AgentResponse`
is a fully auditable trace of which tools produced which numbers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.agent import AgentResponse, AgentStep, ToolCall, ToolResult
from .llm import LLM, OpenAILLM, RuleBasedLLM
from .tools import TOOLS, TOOLS_BY_NAME, AgentContext, ToolSpec

DEFAULT_MAX_STEPS = 12


class ResearchAgent:
    """An LLM-driven agent that answers equity-research questions with tools."""

    def __init__(
        self,
        context: AgentContext,
        llm: LLM,
        tools: list[ToolSpec] | None = None,
        *,
        max_steps: int = DEFAULT_MAX_STEPS,
    ):
        self.context = context
        self.llm = llm
        self.tools = tools if tools is not None else TOOLS
        self._tools_by_name = {t.name: t for t in self.tools}
        self.max_steps = max_steps

    def _execute(self, call: ToolCall) -> ToolResult:
        """Run one tool call, capturing success or failure in a :class:`ToolResult`."""
        tool = self._tools_by_name.get(call.tool_name)
        if tool is None:
            return ToolResult.failure(call.tool_name, f"Unknown tool '{call.tool_name}'.")
        try:
            result = tool.handler(self.context, call.arguments)
            return ToolResult.success(call.tool_name, result)
        except Exception as exc:  # noqa: BLE001 - surface any engine error to the model
            return ToolResult.failure(call.tool_name, f"{type(exc).__name__}: {exc}")

    def run(self, ticker: str, query: str) -> AgentResponse:
        """Answer ``query`` about ``ticker``, returning the full tool-call trace."""
        # Load (or switch to) the requested ticker; this sets the session ticker
        # that tools default to. Done here so a reused agent reloads on a new ticker.
        self.context.ensure_dataset(ticker)

        steps: list[AgentStep] = []
        answer: str | None = None

        for _ in range(self.max_steps):
            proposal = self.llm.propose(query, steps, self.tools)
            if proposal.is_final:
                answer = proposal.final_answer
                break
            if not proposal.tool_calls:
                break
            for call in proposal.tool_calls:
                steps.append(AgentStep(call=call, result=self._execute(call)))

        if answer is None:
            # Step budget exhausted without a final answer; ask once more for a summary.
            final = self.llm.propose(query, steps, self.tools)
            answer = final.final_answer or "Analysis incomplete: step budget exhausted."

        return AgentResponse(query=query, answer=answer, steps=steps)


def build_agent(
    *,
    provider: str = "local",
    sample_dir: str | Path | None = None,
    settings: Any = None,
    use_openai: bool = False,
    rag_engine: Any = None,
    index_sample_filing: bool = False,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> ResearchAgent:
    """Construct a :class:`ResearchAgent`, wiring OpenAI when requested and available.

    Defaults to the fully-offline stack (rule-based planner + local data). When
    ``index_sample_filing`` is set and no RAG engine is supplied, a RAG engine is
    built and the bundled sample filing is ingested so filing-evidence questions
    can be answered offline.
    """
    if rag_engine is None and index_sample_filing:
        from ..rag import build_rag_engine

        sample_doc = (
            Path(__file__).resolve().parents[2] / "data" / "sample" / "SAMPLE_10K.txt"
        )
        if sample_doc.exists():
            rag_engine = build_rag_engine(settings=settings)
            rag_engine.ingest_file(
                sample_doc, doc_id="SAMPLE", document_name="Sample 10-K"
            )

    context = AgentContext(
        provider=provider, sample_dir=sample_dir, settings=settings, rag_engine=rag_engine
    )

    if use_openai and settings is not None and getattr(settings, "has_openai", lambda: False)():
        llm: LLM = OpenAILLM(model=getattr(settings, "openai_model", "gpt-4o-mini"))
    else:
        llm = RuleBasedLLM()

    return ResearchAgent(context, llm, TOOLS, max_steps=max_steps)


__all__ = ["ResearchAgent", "build_agent", "TOOLS", "TOOLS_BY_NAME"]
