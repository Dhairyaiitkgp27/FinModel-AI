"""Sensitivity analysis for DCF valuations.

Two views:

* A two-dimensional **WACC x terminal-growth** grid of implied share prices. The
  forecast (and therefore the FCFF path) is fixed; only the discounting inputs
  vary, so the grid isolates how the two most influential valuation parameters
  move the answer. Cells where ``WACC <= terminal growth`` are marked ``NaN``.
* A **driver ranking** (tornado analysis) that flexes each key assumption —
  revenue growth, terminal growth, and WACC — low/high around the base case and
  records the resulting swing in implied price, so the biggest value drivers are
  obvious.
"""
from __future__ import annotations

import math

from ..models.valuation import (
    DCFInputs,
    DriverSensitivity,
    DriverSensitivityRanking,
    SensitivityAxis,
    SensitivityResult,
)
from .dcf import build_dcf_inputs, compute_dcf
from .wacc import build_wacc_inputs, compute_wacc


def _price_for(base_inputs: DCFInputs, wacc: float, terminal_growth: float) -> float:
    """Implied price for the fixed FCFF path at a given WACC / terminal growth.

    Returns ``NaN`` for the degenerate ``WACC <= terminal growth`` region.
    """
    if wacc <= terminal_growth:
        return math.nan
    try:
        inputs = base_inputs.model_copy(
            update={"wacc": wacc, "terminal_growth": terminal_growth}
        )
    except Exception:  # pragma: no cover - out-of-range axis value
        return math.nan
    return compute_dcf(inputs).implied_share_price


def dcf_sensitivity(
    base_inputs: DCFInputs,
    wacc_values: list[float],
    terminal_growth_values: list[float],
) -> SensitivityResult:
    """Build a WACC (rows) x terminal-growth (cols) grid of implied prices."""
    matrix: list[list[float]] = [
        [_price_for(base_inputs, wacc, g) for g in terminal_growth_values]
        for wacc in wacc_values
    ]
    base_value = compute_dcf(base_inputs).implied_share_price
    return SensitivityResult(
        row_axis=SensitivityAxis(name="WACC", values=list(wacc_values)),
        col_axis=SensitivityAxis(name="Terminal Growth", values=list(terminal_growth_values)),
        matrix=matrix,
        base_value=base_value,
    )


def _forecast_dcf_inputs(
    dataset, base_growth: float, horizon_years: int, wacc: float, terminal_growth: float
) -> DCFInputs:
    """Forecast at ``base_growth`` and assemble DCF inputs at the given WACC/g."""
    from ..forecasting import build_scenario_from_history, forecast_statements

    scenario = build_scenario_from_history(dataset.financials, base_growth, horizon_years)
    forecast = forecast_statements(dataset.financials, scenario)
    return build_dcf_inputs(
        forecast, dataset, wacc=wacc, terminal_growth=terminal_growth
    )


def build_dcf_sensitivity(
    dataset,
    base_growth: float,
    horizon_years: int = 5,
    *,
    wacc: float | None = None,
    terminal_growth: float = 0.025,
    wacc_offsets: tuple[float, ...] = (-0.02, -0.01, 0.0, 0.01, 0.02),
    terminal_growth_values: tuple[float, ...] = (0.015, 0.02, 0.025, 0.03, 0.035),
    risk_free_rate: float = 0.04,
    equity_risk_premium: float = 0.055,
    tax_rate: float = 0.21,
) -> SensitivityResult:
    """WACC x terminal-growth sensitivity grid for a dataset's base-case forecast.

    The WACC axis is centred on the computed (or supplied) WACC using
    ``wacc_offsets``; the terminal-growth axis is given explicitly.
    """
    if wacc is None:
        wacc = compute_wacc(
            build_wacc_inputs(
                dataset,
                risk_free_rate=risk_free_rate,
                equity_risk_premium=equity_risk_premium,
                tax_rate=tax_rate,
            )
        ).wacc

    base_inputs = _forecast_dcf_inputs(dataset, base_growth, horizon_years, wacc, terminal_growth)
    wacc_values = [wacc + off for off in wacc_offsets]
    return dcf_sensitivity(base_inputs, wacc_values, list(terminal_growth_values))


def driver_sensitivity(
    dataset,
    base_growth: float,
    horizon_years: int = 5,
    *,
    terminal_growth: float = 0.025,
    wacc: float | None = None,
    growth_step: float = 0.02,
    terminal_growth_step: float = 0.01,
    wacc_step: float = 0.01,
    risk_free_rate: float = 0.04,
    equity_risk_premium: float = 0.055,
    tax_rate: float = 0.21,
) -> DriverSensitivityRanking:
    """Rank drivers by the implied-price swing they produce (tornado analysis)."""
    if wacc is None:
        wacc = compute_wacc(
            build_wacc_inputs(
                dataset,
                risk_free_rate=risk_free_rate,
                equity_risk_premium=equity_risk_premium,
                tax_rate=tax_rate,
            )
        ).wacc

    def price(growth: float, tg: float, discount: float) -> float:
        inputs = _forecast_dcf_inputs(dataset, growth, horizon_years, discount, tg)
        return compute_dcf(inputs).implied_share_price

    base_value = price(base_growth, terminal_growth, wacc)

    drivers: list[DriverSensitivity] = []

    # Revenue growth
    drivers.append(
        DriverSensitivity(
            driver="revenue_growth",
            low_value=base_growth - growth_step,
            high_value=base_growth + growth_step,
            low_result=price(base_growth - growth_step, terminal_growth, wacc),
            high_result=price(base_growth + growth_step, terminal_growth, wacc),
        )
    )

    # Terminal growth (kept strictly below WACC)
    tg_low = terminal_growth - terminal_growth_step
    tg_high = min(terminal_growth + terminal_growth_step, wacc - 1e-4)
    drivers.append(
        DriverSensitivity(
            driver="terminal_growth",
            low_value=tg_low,
            high_value=tg_high,
            low_result=price(base_growth, tg_low, wacc),
            high_result=price(base_growth, tg_high, wacc),
        )
    )

    # WACC (higher WACC lowers value; swing is direction-agnostic)
    wacc_low = max(wacc - wacc_step, terminal_growth + 1e-4)
    wacc_high = wacc + wacc_step
    drivers.append(
        DriverSensitivity(
            driver="wacc",
            low_value=wacc_low,
            high_value=wacc_high,
            low_result=price(base_growth, terminal_growth, wacc_low),
            high_result=price(base_growth, terminal_growth, wacc_high),
        )
    )

    return DriverSensitivityRanking(base_value=base_value, drivers=drivers)
