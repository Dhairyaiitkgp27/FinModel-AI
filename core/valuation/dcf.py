"""Discounted-cash-flow (DCF) engine.

Values a company by discounting its explicit-horizon unlevered free cash flows
(FCFF) at the WACC and adding a Gordon-growth terminal value, then bridging
enterprise value to equity value and an implied share price.

Discounting conventions:

* Year *i* (1-indexed) is discounted at ``1 / (1 + wacc) ** period``, where
  ``period`` is *i* (year-end) or *i - 0.5* under the mid-year convention.
* The terminal value is computed at the end of the final explicit year and
  discounted at the year-end factor ``1 / (1 + wacc) ** n`` regardless of the
  mid-year convention.

The input model guarantees ``wacc > terminal_growth`` and a positive share
count, so the terminal value is finite and the per-share bridge is well-defined.
"""
from __future__ import annotations

from ..models.valuation import DCFInputs, DCFResult
from .wacc import build_wacc_inputs, compute_wacc


def compute_dcf(inputs: DCFInputs) -> DCFResult:
    """Compute a :class:`DCFResult` from DCF inputs."""
    wacc = inputs.wacc
    g = inputs.terminal_growth
    fcfs = inputs.free_cash_flows
    n = len(fcfs)

    discount_factors: list[float] = []
    present_values: list[float] = []
    for i, fcf in enumerate(fcfs, start=1):
        period = (i - 0.5) if inputs.mid_year_convention else float(i)
        factor = 1.0 / (1.0 + wacc) ** period
        discount_factors.append(factor)
        present_values.append(fcf * factor)

    sum_pv_explicit = sum(present_values)

    # Gordon-growth terminal value on the final explicit FCF, discounted at the
    # year-end factor for period n.
    terminal_value = fcfs[-1] * (1.0 + g) / (wacc - g)
    year_end_factor = 1.0 / (1.0 + wacc) ** n
    pv_terminal_value = terminal_value * year_end_factor

    enterprise_value = sum_pv_explicit + pv_terminal_value
    equity_value = enterprise_value - inputs.net_debt
    implied_share_price = equity_value / inputs.shares_outstanding

    return DCFResult(
        discount_factors=discount_factors,
        present_values=present_values,
        sum_pv_explicit=sum_pv_explicit,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal_value,
        enterprise_value=enterprise_value,
        net_debt=inputs.net_debt,
        equity_value=equity_value,
        shares_outstanding=inputs.shares_outstanding,
        implied_share_price=implied_share_price,
        wacc=wacc,
        terminal_growth=g,
    )


def build_dcf_inputs(
    forecast,
    dataset,
    *,
    wacc: float,
    terminal_growth: float,
    mid_year_convention: bool = False,
) -> DCFInputs:
    """Assemble :class:`DCFInputs` from a forecast and a dataset.

    Free cash flows come from the forecast's unlevered FCFF path; net debt and
    share count come from the dataset's market data (falling back to the latest
    balance sheet for net debt).
    """
    market = dataset.market_data
    shares = market.shares_outstanding if market else None
    if not shares or shares <= 0:
        raise ValueError("Shares outstanding are required to compute an implied share price.")

    net_debt: float | None = market.net_debt if market and market.net_debt is not None else None
    if net_debt is None:
        balance = dataset.financials.latest_balance()
        net_debt = balance.net_debt if balance and balance.net_debt is not None else 0.0

    return DCFInputs(
        free_cash_flows=list(forecast.free_cash_flows),
        wacc=wacc,
        terminal_growth=terminal_growth,
        net_debt=net_debt,
        shares_outstanding=shares,
        mid_year_convention=mid_year_convention,
    )


def dcf_valuation(
    dataset,
    base_growth: float,
    horizon_years: int = 5,
    terminal_growth: float = 0.025,
    *,
    risk_free_rate: float = 0.04,
    equity_risk_premium: float = 0.055,
    tax_rate: float = 0.21,
    cost_of_debt: float | None = None,
    mid_year_convention: bool = False,
) -> DCFResult:
    """End-to-end DCF: forecast -> WACC -> discounted valuation, from a dataset.

    Builds a base-case three-statement forecast, computes WACC from market data,
    and discounts the resulting FCFF path to an implied share price.
    """
    # Imported here to avoid a package-level import cycle (valuation <- forecasting).
    from ..forecasting import build_scenario_from_history, forecast_statements

    scenario = build_scenario_from_history(dataset.financials, base_growth, horizon_years)
    forecast = forecast_statements(dataset.financials, scenario)

    wacc_inputs = build_wacc_inputs(
        dataset,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=equity_risk_premium,
        tax_rate=tax_rate,
        cost_of_debt=cost_of_debt,
    )
    wacc_result = compute_wacc(wacc_inputs)

    dcf_inputs = build_dcf_inputs(
        forecast,
        dataset,
        wacc=wacc_result.wacc,
        terminal_growth=terminal_growth,
        mid_year_convention=mid_year_convention,
    )
    return compute_dcf(dcf_inputs)
