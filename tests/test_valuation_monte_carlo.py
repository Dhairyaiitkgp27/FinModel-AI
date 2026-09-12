"""Tests for the Monte Carlo valuation engine."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from core.data import LocalSampleProvider
from core.models import AssumptionDistribution, DistributionType, MonteCarloInputs
from core.valuation import monte_carlo_dcf, monte_carlo_valuation
from core.valuation.monte_carlo import _sample, default_distributions

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def _mc_inputs(distributions, n=2000, seed=42) -> MonteCarloInputs:
    return MonteCarloInputs(n_simulations=n, seed=seed, distributions=distributions)


# --------------------------------------------------------------------------- #
# Deterministic core                                                          #
# --------------------------------------------------------------------------- #
def test_empty_distributions_are_deterministic():
    # No distributions -> every draw uses the base values -> a single price.
    # Flat FCFF of 100 for 5 years at 10% + terminal 100/(0.10) discounted = EV 1000.
    result = monte_carlo_dcf(
        base_revenue=1000.0, horizon_years=5, net_debt=0.0, shares_outstanding=100.0,
        current_price=None, base_growth=0.0, base_terminal_growth=0.0,
        base_wacc=0.10, base_fcf_margin=0.10, inputs=_mc_inputs([]),
    )
    assert result.mean == pytest.approx(10.0)
    assert result.p10 == pytest.approx(10.0)
    assert result.p50 == pytest.approx(10.0)
    assert result.p90 == pytest.approx(10.0)
    assert result.std == pytest.approx(0.0, abs=1e-9)


def test_net_debt_shifts_price():
    common = dict(
        base_revenue=1000.0, horizon_years=5, shares_outstanding=100.0, current_price=None,
        base_growth=0.0, base_terminal_growth=0.0, base_wacc=0.10, base_fcf_margin=0.10,
        inputs=_mc_inputs([]),
    )
    no_debt = monte_carlo_dcf(net_debt=0.0, **common)
    with_debt = monte_carlo_dcf(net_debt=300.0, **common)
    assert no_debt.p50 - with_debt.p50 == pytest.approx(3.0)  # 300 / 100 shares


# --------------------------------------------------------------------------- #
# Stochastic behaviour                                                        #
# --------------------------------------------------------------------------- #
def test_reproducible_with_same_seed():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    a = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=3000, seed=42)
    b = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=3000, seed=42)
    assert a.p50 == b.p50
    assert a.mean == b.mean
    assert a.p90 == b.p90


def test_different_seed_changes_draws():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    a = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=3000, seed=42)
    b = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=3000, seed=123)
    assert a.p50 != b.p50


def test_percentiles_are_ordered():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    r = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=5000, seed=42)
    assert r.p10 <= r.p25 <= r.p50 <= r.p75 <= r.p90


def test_probabilities_sum_to_one():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    r = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=5000, seed=42)
    assert r.prob_upside is not None and r.prob_downside is not None
    assert r.prob_upside + r.prob_downside == pytest.approx(1.0, abs=1e-6)


def test_histogram_counts_sum_to_valid_draws():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    r = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=4000, seed=42)
    assert sum(r.histogram_counts) == r.n_simulations
    assert len(r.histogram_edges) == len(r.histogram_counts) + 1


def test_valid_draw_count_reported():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    # With WACC ~10.8% and terminal growth ~2.5% (tight spreads), all draws are valid.
    r = monte_carlo_valuation(ds, base_growth=0.06, n_simulations=6000, seed=42)
    assert r.n_simulations == 6000


def test_higher_growth_distribution_raises_median():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("MSFT")
    low = monte_carlo_valuation(ds, base_growth=0.04, n_simulations=4000, seed=1)
    high = monte_carlo_valuation(ds, base_growth=0.12, n_simulations=4000, seed=1)
    assert high.p50 > low.p50


# --------------------------------------------------------------------------- #
# Distribution sampling                                                       #
# --------------------------------------------------------------------------- #
def test_sample_normal_moments():
    rng = np.random.default_rng(0)
    dist = AssumptionDistribution(name="x", distribution=DistributionType.NORMAL, mean=0.1, std=0.02)
    draws = _sample(dist, 50_000, rng)
    assert draws.mean() == pytest.approx(0.1, abs=0.002)
    assert draws.std() == pytest.approx(0.02, abs=0.002)


def test_sample_uniform_within_bounds():
    rng = np.random.default_rng(0)
    dist = AssumptionDistribution(name="x", distribution=DistributionType.UNIFORM, low=0.02, high=0.05)
    draws = _sample(dist, 10_000, rng)
    assert draws.min() >= 0.02
    assert draws.max() <= 0.05


def test_sample_triangular_within_bounds():
    rng = np.random.default_rng(0)
    dist = AssumptionDistribution(
        name="x", distribution=DistributionType.TRIANGULAR, low=0.0, mode=0.05, high=0.10
    )
    draws = _sample(dist, 10_000, rng)
    assert draws.min() >= 0.0
    assert draws.max() <= 0.10


def test_sample_lognormal_positive_and_mean():
    rng = np.random.default_rng(0)
    dist = AssumptionDistribution(
        name="x", distribution=DistributionType.LOGNORMAL, mean=0.15, std=0.03
    )
    draws = _sample(dist, 50_000, rng)
    assert (draws > 0).all()
    assert draws.mean() == pytest.approx(0.15, abs=0.005)


def test_default_distributions_cover_all_assumptions():
    dists = default_distributions(0.06, 0.025, 0.10, 0.15)
    names = {d.name for d in dists}
    assert names == {"revenue_growth", "terminal_growth", "wacc", "fcf_margin"}


def test_monte_carlo_requires_shares():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    ds.market_data.shares_outstanding = None
    with pytest.raises(ValueError):
        monte_carlo_valuation(ds, base_growth=0.06)
