"""Reverse DCF engine.

A forward DCF assumes growth and outputs a price. A *reverse* DCF inverts that:
it takes today's market price and solves for the assumption the market must be
making. Because implied price is monotonically increasing in both revenue growth
and terminal growth, a simple bisection converges reliably.

Two modes (``ReverseDCFInputs.solve_for``):

* ``REVENUE_GROWTH`` — hold the terminal growth from the inputs and solve for the
  constant explicit-horizon revenue growth that reproduces the market price.
* ``TERMINAL_GROWTH`` — hold explicit-horizon revenue flat and solve for the
  terminal growth (bounded strictly below WACC) that reproduces the price.

The valuation each candidate implies uses the same FCFF-discounting mechanics as
the forward DCF: FCFF = ``fcf_margin * revenue`` each year, discounted at WACC,
plus a Gordon terminal value, bridged to equity via net debt.
"""
from __future__ import annotations

from ..models.valuation import ReverseDCFInputs, ReverseDCFResult, ReverseDCFTarget

MAX_ITERATIONS = 200


def _implied_price(assumption: float, inputs: ReverseDCFInputs) -> float:
    """Implied share price for a candidate growth/terminal-growth assumption."""
    wacc = inputs.wacc
    horizon = inputs.horizon_years
    margin = inputs.fcf_margin
    base_revenue = inputs.base_revenue

    if inputs.solve_for == ReverseDCFTarget.REVENUE_GROWTH:
        growth = assumption
        terminal_growth = inputs.terminal_growth
        revenues = [base_revenue * (1.0 + growth) ** t for t in range(1, horizon + 1)]
    else:  # TERMINAL_GROWTH: explicit horizon flat, solve terminal growth
        growth = 0.0
        terminal_growth = assumption
        revenues = [base_revenue for _ in range(1, horizon + 1)]

    fcffs = [margin * rev for rev in revenues]

    sum_pv = sum(
        fcff / (1.0 + wacc) ** t for t, fcff in enumerate(fcffs, start=1)
    )
    terminal_value = fcffs[-1] * (1.0 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1.0 + wacc) ** horizon

    enterprise_value = sum_pv + pv_terminal
    equity_value = enterprise_value - inputs.net_debt
    return equity_value / inputs.shares_outstanding


def _bounds(inputs: ReverseDCFInputs) -> tuple[float, float]:
    if inputs.solve_for == ReverseDCFTarget.REVENUE_GROWTH:
        return -0.90, 2.00
    # terminal growth must stay below WACC for a finite terminal value
    return -0.05, min(inputs.wacc - 1e-6, 0.50)


def solve_reverse_dcf(
    inputs: ReverseDCFInputs, *, tolerance: float = 1e-6, max_iterations: int = MAX_ITERATIONS
) -> ReverseDCFResult:
    """Solve for the market-implied assumption by bisection."""
    target = inputs.current_price
    low, high = _bounds(inputs)
    price_low = _implied_price(low, inputs)
    price_high = _implied_price(high, inputs)

    abs_tol = max(tolerance * target, 1e-9)

    # If the target lies outside the achievable range, report the nearest bound.
    if target <= price_low:
        return ReverseDCFResult(
            solved_for=inputs.solve_for,
            implied_value=low,
            target_price=target,
            achieved_price=price_low,
            converged=abs(price_low - target) <= abs_tol,
            iterations=0,
        )
    if target >= price_high:
        return ReverseDCFResult(
            solved_for=inputs.solve_for,
            implied_value=high,
            target_price=target,
            achieved_price=price_high,
            converged=abs(price_high - target) <= abs_tol,
            iterations=0,
        )

    converged = False
    mid = 0.5 * (low + high)
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        mid = 0.5 * (low + high)
        price_mid = _implied_price(mid, inputs)
        if abs(price_mid - target) <= abs_tol or (high - low) < 1e-12:
            converged = True
            break
        if price_mid < target:
            low = mid
        else:
            high = mid

    return ReverseDCFResult(
        solved_for=inputs.solve_for,
        implied_value=mid,
        target_price=target,
        achieved_price=_implied_price(mid, inputs),
        converged=converged,
        iterations=iterations,
    )


def build_reverse_dcf_inputs(
    dataset,
    *,
    wacc: float,
    terminal_growth: float = 0.025,
    horizon_years: int = 5,
    fcf_margin: float | None = None,
    solve_for: ReverseDCFTarget = ReverseDCFTarget.REVENUE_GROWTH,
    default_fcf_margin: float = 0.15,
) -> ReverseDCFInputs:
    """Assemble :class:`ReverseDCFInputs` from a :class:`CompanyDataset`."""
    market = dataset.market_data
    income = dataset.financials.latest_income()
    balance = dataset.financials.latest_balance()
    cash_flow = dataset.financials.latest_cash_flow()

    if market is None or market.price is None or market.price <= 0:
        raise ValueError("A positive market price is required for a reverse DCF.")
    if not market.shares_outstanding or market.shares_outstanding <= 0:
        raise ValueError("Shares outstanding are required for a reverse DCF.")
    if income is None or income.revenue in (None, 0):
        raise ValueError("Base revenue is required for a reverse DCF.")

    if fcf_margin is None:
        if cash_flow and cash_flow.free_cash_flow is not None and income.revenue:
            fcf_margin = cash_flow.free_cash_flow / income.revenue
        else:
            fcf_margin = default_fcf_margin
    # Keep the margin inside the model's valid range.
    fcf_margin = max(min(fcf_margin, 1.0), -1.0 + 1e-9)

    net_debt = 0.0
    if market.net_debt is not None:
        net_debt = market.net_debt
    elif balance is not None and balance.net_debt is not None:
        net_debt = balance.net_debt

    return ReverseDCFInputs(
        current_price=market.price,
        shares_outstanding=market.shares_outstanding,
        net_debt=net_debt,
        wacc=wacc,
        terminal_growth=terminal_growth,
        base_revenue=income.revenue,
        horizon_years=horizon_years,
        fcf_margin=fcf_margin,
        solve_for=solve_for,
    )


def reverse_dcf_valuation(
    dataset,
    *,
    wacc: float | None = None,
    terminal_growth: float = 0.025,
    horizon_years: int = 5,
    fcf_margin: float | None = None,
    solve_for: ReverseDCFTarget = ReverseDCFTarget.REVENUE_GROWTH,
    risk_free_rate: float = 0.04,
    equity_risk_premium: float = 0.055,
    tax_rate: float = 0.21,
) -> ReverseDCFResult:
    """End-to-end reverse DCF from a dataset (computing WACC if not supplied)."""
    if wacc is None:
        from .wacc import build_wacc_inputs, compute_wacc

        wacc = compute_wacc(
            build_wacc_inputs(
                dataset,
                risk_free_rate=risk_free_rate,
                equity_risk_premium=equity_risk_premium,
                tax_rate=tax_rate,
            )
        ).wacc

    inputs = build_reverse_dcf_inputs(
        dataset,
        wacc=wacc,
        terminal_growth=terminal_growth,
        horizon_years=horizon_years,
        fcf_margin=fcf_margin,
        solve_for=solve_for,
    )
    return solve_reverse_dcf(inputs)
