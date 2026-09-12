"""Dashboard UI layer.

The testable, framework-agnostic pieces (formatting, analysis orchestration, and
Plotly chart builders) are exported here. The Streamlit page modules and the app
entry point import Streamlit directly and are wired up in ``app.py``.
"""
from __future__ import annotations

from ui import charts, formatting
from ui.analysis import (
    AnalysisAssumptions,
    AnalysisBundle,
    run_full_analysis,
    valuation_ranges,
)

__all__ = [
    "formatting",
    "charts",
    "AnalysisAssumptions",
    "AnalysisBundle",
    "run_full_analysis",
    "valuation_ranges",
]
