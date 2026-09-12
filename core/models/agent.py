"""Agent orchestration models.

These envelopes make the research agent's behaviour inspectable and testable:
every tool invocation is a :class:`ToolCall`, every outcome a
:class:`ToolResult`, and the full trajectory is captured in
:class:`AgentResponse` so the UI can show exactly which deterministic tools
produced which numbers.
"""
from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import FinBaseModel


class ToolCall(FinBaseModel):
    """A request to invoke a named tool with structured arguments."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(FinBaseModel):
    """The outcome of a tool invocation."""

    tool_name: str
    ok: bool = True
    result: Any | None = None
    error: str | None = None

    @classmethod
    def success(cls, tool_name: str, result: Any) -> ToolResult:
        return cls(tool_name=tool_name, ok=True, result=result)

    @classmethod
    def failure(cls, tool_name: str, error: str) -> ToolResult:
        return cls(tool_name=tool_name, ok=False, error=error)


class AgentStep(FinBaseModel):
    """A single call/result pair in an agent trajectory."""

    call: ToolCall
    result: ToolResult


class AgentResponse(FinBaseModel):
    """The full result of an agent run, including its tool trajectory."""

    query: str
    answer: str = ""
    steps: list[AgentStep] = Field(default_factory=list)

    @property
    def tools_used(self) -> list[str]:
        """Ordered, de-duplicated list of tool names the agent invoked."""
        seen: list[str] = []
        for step in self.steps:
            if step.call.tool_name not in seen:
                seen.append(step.call.tool_name)
        return seen
