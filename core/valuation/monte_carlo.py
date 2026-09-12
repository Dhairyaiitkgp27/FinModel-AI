"""Monte Carlo valuation engine.

Samples the key DCF assumptions — revenue growth, terminal growth, WACC, and FCF
margin — from their distributions and runs *every* sampled set through the DCF,
then summarises the resulting distribution of implied share prices (P10-P90,
mean/std, probability of upside versus the current price).

Crucially, randomness enters only through the *assumptions*: each draw is priced
by the same deterministic DCF used elsewhere, vectorised across all simulations
with NumPy for speed. The engine never samples prices directly.

Distributions are matched to assumptions by name; recognised names are
``revenue_growth``, ``terminal_growth``, ``wacc``, and ``fcf_margin``. Any
assumption without a supplied distribution is held at its base value. Draws where
``WACC <= terminal growth`` (a divergent terminal value) are discarded, and the
reported simulation count reflects the valid draws used.
"""
from __future__ import annotations

import math
from typing import Any

from ..models.valuation import (
    AssumptionDistribution,
    DistributionType,
    MonteCarloInputs,
    MonteCarloResult,
)

RECOGNISED_ASSUMPTIONS = ("revenue_growth", "terminal_growth", "wacc", "fcf_margin")
DEFAULT_HISTOGRAM_BINS = 30


def _sample(dist: AssumptionDistribution, n: int, rng: Any) -> Any:
    """Draw ``n`` samples from one assumption distribution."""

    kind = dist.distribution
    if kind == DistributionType.NORMAL:
        return rng.normal(dist.mean, dist.std, n)
    if kind == DistributionType.UNIFORM:
        return rng.uniform(dist.low, dist.high, n)
    if kind == DistributionType.TRIANGULAR:
        mode = dist.mode if dist.mode is not None else (dist.low + dist.high) / 2.0
        mode = min(max(mode, dist.low), dist.high)
        return rng.triangular(dist.low, mode, dist.high, n)
    if kind == DistributionType.LOGNORMAL:
        # Interpret mean/std as the desired moments of the lognormal variable and
        # convert to the underlying normal's parameters.
        m, s = dist.mean, dist.std
        if m is None or m <= 0:
            raise ValueError("lognormal distribution requires a positive mean")
        sigma_sq = math.log(1.0 + (s / m) ** 2)
        mu = math.log(m) - sigma_sq / 2.0
        return rng.lognormal(mu, math.sqrt(sigma_sq), n)
    raise ValueError(f"Unsupported distribution type: {kind}")


def monte_carlo_dcf(
    *,
    base_revenue: float,
    horizon_years: int,
    net_debt: float,
    shares_outstanding: float,
    current_price: float | None,
    base_growth: float,
    base_terminal_growth: float,
    base_wacc: float,
    base_fcf_margin: float,
    inputs: MonteCarloInputs,
) -> MonteCarloResult:
    """Run the Monte Carlo DCF and summarise the implied-price distribution."""
    import numpy as np

    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be positive")

    n = inputs.n_simulations
    rng = np.random.default_rng(inputs.seed)

    # Start every assumption at its base value, then overlay sampled distributions.
    values = {
        "revenue_growth": np.full(n, base_growth, dtype=float),
        "terminal_growth": np.full(n, base_terminal_growth, dtype=float),
        "wacc": np.full(n, base_wacc, dtype=float),
        "fcf_margin": np.full(n, base_fcf_margin, dtype=float),
    }
    for dist in inputs.distributions:
        if dist.name in values:
            values[dist.name] = _sample(dist, n, rng)

    g = values["revenue_growth"]
    tg = values["terminal_growth"]
    wacc = values["wacc"]
    margin = values["fcf_margin"]

    # Vectorised DCF across all simulations.
    t = np.arange(1, horizon_years + 1)
    revenue = base_revenue * (1.0 + g)[:, None] ** t[None, :]
    fcff = margin[:, None] * revenue
    discount = (1.0 + wacc)[:, None] ** t[None, :]
    sum_pv = (fcff / discount).sum(axis=1)

    fcff_final = fcff[:, -1]
    with np.errstate(divide="ignore", invalid="ignore"):
        terminal_value = fcff_final * (1.0 + tg) / (wacc - tg)
        pv_terminal = terminal_value / (1.0 + wacc) ** horizon_years
        enterprise_value = sum_pv + pv_terminal
        price = (enterprise_value - net_debt) / shares_outstanding

    valid = (wacc > tg) & (wacc > 0) & np.isfinite(price)
    prices = price[valid]
    if prices.size == 0:
        raise ValueError("No valid Monte Carlo draws (check assumption distributions).")

    p10, p25, p50, p75, p90 = (float(x) for x in np.percentile(prices, [10, 25, 50, 75, 90]))
    std = float(prices.std(ddof=1)) if prices.size > 1 else 0.0

    prob_upside = prob_downside = None
    if current_price is not None:
        prob_upside = float((prices > current_price).mean())
        prob_downside = float((prices < current_price).mean())

    counts, edges = np.histogram(prices, bins=DEFAULT_HISTOGRAM_BINS)

    return MonteCarloResult(
        n_simulations=int(prices.size),
        seed=inputs.seed,
        mean=float(prices.mean()),
        median=p50,
        std=std,
        p10=p10,
        p25=p25,
        p50=p50,
        p75=p75,
        p90=p90,
        current_price=current_price,
        prob_upside=prob_upside,
        prob_downside=prob_downside,
        histogram_edges=[float(e) for e in edges],
        histogram_counts=[int(c) for c in counts],
    )


def default_distributions(
    base_growth: float,
    terminal_growth: float,
    wacc: float,
    fcf_margin: float,
    *,
    growth_std: float = 0.03,
    terminal_growth_std: float = 0.005,
    wacc_std: float = 0.01,
    fcf_margin_std: float = 0.02,
) -> list[AssumptionDistribution]:
    """Normal distributions centred on the base assumptions."""
    return [
        AssumptionDistribution(
            name="revenue_growth", distribution=DistributionType.NORMAL,
            mean=base_growth, std=growth_std,
        ),
        AssumptionDistribution(
            name="terminal_growth", distribution=DistributionType.NORMAL,
            mean=terminal_growth, std=terminal_growth_std,
        ),
        AssumptionDistribution(
            name="wacc", distribution=DistributionType.NORMAL, mean=wacc, std=wacc_std,
        ),
        AssumptionDistribution(
            name="fcf_margin", distribution=DistributionType.NORMAL,
            mean=fcf_margin, std=fcf_margin_std,
        ),
    ]


def monte_carlo_valuation(
    dataset,
    base_growth: float,
    horizon_years: int = 5,
    terminal_growth: float = 0.025,
    *,
    wacc: float | None = None,
    fcf_margin: float | None = None,
    n_simulations: int = 10_000,
    seed: int | None = 42,
    distributions: list[AssumptionDistribution] | None = None,
    risk_free_rate: float = 0.04,
    equity_risk_premium: float = 0.055,
    tax_rate: float = 0.21,
    default_fcf_margin: float = 0.15,
) -> MonteCarloResult:
    """End-to-end Monte Carlo valuation from a :class:`CompanyDataset`."""
    market = dataset.market_data
    income = dataset.financials.latest_income()
    balance = dataset.financials.latest_balance()
    cash_flow = dataset.financials.latest_cash_flow()

    if income is None or income.revenue in (None, 0):
        raise ValueError("Base revenue is required for a Monte Carlo valuation.")
    if market is None or not market.shares_outstanding or market.shares_outstanding <= 0:
        raise ValueError("Shares outstanding are required for a Monte Carlo valuation.")

    base_revenue = income.revenue
    shares = market.shares_outstanding
    current_price = market.price

    net_debt = 0.0
    if market.net_debt is not None:
        net_debt = market.net_debt
    elif balance is not None and balance.net_debt is not None:
        net_debt = balance.net_debt

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

    if fcf_margin is None:
        if cash_flow and cash_flow.free_cash_flow is not None and base_revenue:
            fcf_margin = cash_flow.free_cash_flow / base_revenue
        else:
            fcf_margin = default_fcf_margin
    fcf_margin = max(min(fcf_margin, 1.0), -1.0 + 1e-9)

    if distributions is None:
        distributions = default_distributions(base_growth, terminal_growth, wacc, fcf_margin)

    inputs = MonteCarloInputs(
        n_simulations=n_simulations, seed=seed, distributions=distributions
    )
    return monte_carlo_dcf(
        base_revenue=base_revenue,
        horizon_years=horizon_years,
        net_debt=net_debt,
        shares_outstanding=shares,
        current_price=current_price,
        base_growth=base_growth,
        base_terminal_growth=terminal_growth,
        base_wacc=wacc,
        base_fcf_margin=fcf_margin,
        inputs=inputs,
    )
