"""Forecasting engine: linked three-statement projection and scenarios."""
from __future__ import annotations

from .scenarios import (
    build_and_compare,
    build_scenarios,
    compare_scenarios,
    terminal_values,
)
from .three_statement import (
    build_scenario_from_history,
    derive_base_drivers,
    forecast_statements,
)

__all__ = [
    # Three-statement engine
    "forecast_statements",
    "derive_base_drivers",
    "build_scenario_from_history",
    # Scenarios
    "build_scenarios",
    "compare_scenarios",
    "build_and_compare",
    "terminal_values",
]
