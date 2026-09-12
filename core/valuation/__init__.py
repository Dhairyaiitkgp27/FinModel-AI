"""Valuation engines.

Phase 6: DCF + WACC. Phase 7: comps + precedents. Phase 8: reverse DCF +
sensitivity. Phase 9: Monte Carlo.
"""
from __future__ import annotations

from .comps import (
    build_comps_from_dataset,
    compute_comps,
    compute_peer_multiples,
    summarize_multiples,
)
from .dcf import build_dcf_inputs, compute_dcf, dcf_valuation
from .monte_carlo import (
    default_distributions,
    monte_carlo_dcf,
    monte_carlo_valuation,
)
from .precedent import (
    build_precedent_from_dataset,
    compute_precedent,
    compute_transaction_multiples,
)
from .reverse_dcf import (
    build_reverse_dcf_inputs,
    reverse_dcf_valuation,
    solve_reverse_dcf,
)
from .sensitivity import (
    build_dcf_sensitivity,
    dcf_sensitivity,
    driver_sensitivity,
)
from .wacc import build_wacc_inputs, compute_wacc

__all__ = [
    # DCF / WACC
    "compute_wacc",
    "build_wacc_inputs",
    "compute_dcf",
    "build_dcf_inputs",
    "dcf_valuation",
    # Comps
    "compute_comps",
    "compute_peer_multiples",
    "summarize_multiples",
    "build_comps_from_dataset",
    # Precedents
    "compute_precedent",
    "compute_transaction_multiples",
    "build_precedent_from_dataset",
    # Reverse DCF
    "solve_reverse_dcf",
    "build_reverse_dcf_inputs",
    "reverse_dcf_valuation",
    # Sensitivity
    "dcf_sensitivity",
    "build_dcf_sensitivity",
    "driver_sensitivity",
    # Monte Carlo
    "monte_carlo_dcf",
    "monte_carlo_valuation",
    "default_distributions",
]
