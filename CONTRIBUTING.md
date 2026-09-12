# Contributing to FinModel AI

Thanks for your interest in the project. This guide covers local setup, the
development workflow, and the conventions that keep the codebase consistent.

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
make install-dev        # runtime deps + ruff
cp .env.example .env     # optional; set OPENAI_API_KEY to enable the LLM agent
```

Verify everything works:

```bash
make smoke   # loads sample data and runs the full analysis stack
make test    # the full test suite
make eval    # the agent-evaluation suite
make lint    # ruff
```

## Architecture at a glance

The single most important rule: **the deterministic Python engine performs every
calculation; the LLM only orchestrates and narrates.** Keep new numerical logic
in the engines (`core/analysis`, `core/forecasting`, `core/valuation`, …) with
tests, and expose it to the agent as a typed tool rather than letting the model
compute anything.

Layering (imports point downward):

```
ui / core.outputs  →  core.agents  →  core.valuation / forecasting / analysis / rag
                                   →  core.data  →  core.models / core.utils / config
```

- `core/models` — Pydantic schemas; no business logic.
- `core/data` — providers, normalisation, validation, ingestion.
- `core/analysis`, `core/forecasting`, `core/valuation`, `core/rag` — the engines.
- `core/agents` — typed tools + the tool-calling loop.
- `core/outputs` — Excel/PDF reports.
- `ui` — Streamlit dashboard and Plotly charts (framework-agnostic pieces are tested).
- `evals` — the agent-evaluation suite.

## Conventions

- **Determinism.** No fabricated numbers, no placeholder return values, no
  hardcoded valuation outputs. Sample data is always clearly flagged
  (`is_sample=True`).
- **`None`-safety.** Numerical helpers return `None` when inputs are missing
  rather than raising or guessing.
- **Optional heavy dependencies** (yfinance, FAISS, PyMuPDF, OpenAI) are imported
  lazily so the core remains importable and testable without them.
- **Style.** `from __future__ import annotations` at the top of every module;
  PEP 604 unions (`X | None`); ruff-clean (`make lint`).

## Adding a feature

1. Implement the logic in the appropriate engine with unit tests that assert
   exact, hand-computed values where possible.
2. If it should be agent-accessible, add a `ToolSpec` in `core/agents/tools.py`
   and a routing keyword in `core/agents/llm.py`.
3. Add an evaluation case in `evals/cases.py` if it introduces a new query type.
4. Run `make lint test eval` before opening a pull request.

## Tests

- Unit tests live in `tests/` and mirror the package layout.
- Prefer exact assertions (hand-computed expected values) over smoke assertions.
- The agent-evaluation suite (`evals/`) checks tool selection and answer quality
  and runs deterministically against the offline agent.

## Disclaimer

FinModel AI is for research and educational purposes and does not constitute
investment advice.
