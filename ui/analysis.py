"""Facade re-exporting the core analysis orchestrator for the UI.

The orchestration itself lives in :mod:`core.analysis.bundle` (core business
logic, no UI dependency). This module keeps the ``ui.analysis`` import path
stable for the dashboard and chart layer.
"""
from __future__ import annotations

from core.analysis.bundle import (
    AnalysisAssumptions,
    AnalysisBundle,
    run_full_analysis,
    valuation_ranges,
)

__all__ = [
    "AnalysisAssumptions",
    "AnalysisBundle",
    "run_full_analysis",
    "valuation_ranges",
]
