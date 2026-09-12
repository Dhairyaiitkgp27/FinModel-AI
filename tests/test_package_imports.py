"""Import-level smoke tests: the whole package must import cleanly.

These guard against broken imports, circular dependencies, and drift between
the ``__all__`` export list and the actual model classes.
"""
from __future__ import annotations

import importlib

import pytest

MODULES = [
    "config",
    "config.settings",
    "core",
    "core.utils",
    "core.utils.math",
    "core.utils.logging",
    "core.models",
    "core.models.base",
    "core.models.company",
    "core.models.prices",
    "core.models.financials",
    "core.models.analysis",
    "core.models.forecast",
    "core.models.valuation",
    "core.models.risk",
    "core.models.rag",
    "core.models.agent",
    # Data layer (Phase 2)
    "core.data",
    "core.data.dataset",
    "core.data.providers",
    "core.data.providers.base",
    "core.data.providers.local",
    "core.data.providers.yfinance_provider",
    "core.data.normalization",
    "core.data.normalization.yfinance",
    "core.data.validation",
    "core.data.validation.checks",
    "core.data.ingestion",
    "core.data.ingestion.loader",
    # Analysis layer (Phase 3)
    "core.analysis",
    "core.analysis.ratios",
    "core.analysis.bundle",
    # Forecasting layer (Phase 4)
    "core.forecasting",
    "core.forecasting.three_statement",
    "core.forecasting.scenarios",
    # Valuation layer (Phase 6)
    "core.valuation",
    "core.valuation.wacc",
    "core.valuation.dcf",
    "core.valuation.comps",
    "core.valuation.precedent",
    "core.valuation.reverse_dcf",
    "core.valuation.sensitivity",
    "core.valuation.monte_carlo",
    # RAG layer (Phase 10)
    "core.rag",
    "core.rag.chunking",
    "core.rag.embeddings",
    "core.rag.index",
    "core.rag.pdf",
    "core.rag.engine",
    # Agent layer (Phase 11)
    "core.agents",
    "core.agents.tools",
    "core.agents.llm",
    "core.agents.agent",
    # Reporting layer (Phase 13)
    "core.outputs",
    "core.outputs.excel",
    "core.outputs.pdf",
    # Package placeholders for later phases must at least import
    "core.risk",
    "core.outputs",
    # UI layer (Phase 12) — testable modules only; ui.dashboard needs Streamlit
    "ui",
    "ui.formatting",
    "ui.analysis",
    "ui.charts",
    # Agent evaluation suite (Phase 14)
    "evals",
    "evals.harness",
    "evals.cases",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name: str):
    assert importlib.import_module(module_name) is not None


def test_core_version_present():
    import core

    assert isinstance(core.__version__, str)
    assert core.__version__


def test_models_all_are_importable():
    import core.models as models

    for name in models.__all__:
        assert hasattr(models, name), f"{name} listed in __all__ but not importable"


def test_app_module_imports():
    # app.py should import without side effects (smoke_test only runs under __main__)
    app = importlib.import_module("app")
    assert hasattr(app, "smoke_test")
