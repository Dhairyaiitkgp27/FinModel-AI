"""The OpenAI tool-calling research agent.

Wraps the deterministic engines as typed tools and drives an LLM (real OpenAI or
an offline rule-based planner) through a tool-calling loop to answer equity
research questions. Every number originates from the deterministic engines.
"""
from __future__ import annotations

from .agent import ResearchAgent, build_agent
from .llm import LLM, OpenAILLM, Proposal, RuleBasedLLM
from .tools import TOOLS, TOOLS_BY_NAME, AgentContext, ToolSpec

__all__ = [
    "ResearchAgent",
    "build_agent",
    "AgentContext",
    "ToolSpec",
    "TOOLS",
    "TOOLS_BY_NAME",
    "LLM",
    "RuleBasedLLM",
    "OpenAILLM",
    "Proposal",
]
