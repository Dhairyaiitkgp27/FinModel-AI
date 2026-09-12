"""Valuation models for every methodology the platform supports.

These schemas define the *inputs* and *verified outputs* of the deterministic
valuation engines (Phases 6-9). Input models enforce the invariants that make a
valuation well-posed — most importantly that WACC exceeds the terminal growth
rate in any Gordon-growth terminal value — so the engines can assume clean
inputs and callers get meaningful errors early.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import Field, model_validator

from .base import FinBaseModel


# --------------------------------------------------------------------------- #
# WACC                                                                        #
# --------------------------------------------------------------------------- #
class WACCInputs(FinBaseModel):
    """Inputs to the weighted-average cost of capital calculation.

    Capital-structure weights are derived from ``equity_value`` and
    ``debt_value`` (market values preferred). Both must be non-negative and not
    both zero.
    """

    risk_free_rate: float = Field(ge=-0.05, le=0.25)
    beta: float = Field(ge=0.0, le=5.0)
    equity_risk_premium: float = Field(gt=0.0, le=0.25)
    pretax_cost_of_debt: float = Field(ge=0.0, le=0.5)
    tax_rate: float = Field(ge=0.0, le=1.0)
    equity_value: float = Field(ge=0.0)
    debt_value: float = Field(ge=0.0)

    @model_validator(mode="after")
    def _check_capital_structure(self) -> WACCInputs:
        if self.equity_value + self.debt_value <= 0:
            raise ValueError("equity_value + debt_value must be positive")
        return self


class WACCResult(FinBaseModel):
    """Verified WACC output."""

    cost_of_equity: float
    pretax_cost_of_debt: float
    after_tax_cost_of_debt: float
    equity_weight: float
    debt_weight: float
    wacc: float


# --------------------------------------------------------------------------- #
# DCF                                                                          #
# --------------------------------------------------------------------------- #
class DCFInputs(FinBaseModel):
    """Inputs to an unlevered (FCFF) discounted-cash-flow valuation."""

    free_cash_flows: list[float] = Field(min_length=1, description="Explicit-horizon FCFF")
    wacc: float = Field(gt=0.0, lt=1.0)
    terminal_growth: float = Field(ge=-0.05, lt=0.20)
    net_debt: float = 0.0
    shares_outstanding: float = Field(gt=0.0)
    mid_year_convention: bool = False

    @model_validator(mode="after")
    def _wacc_above_terminal_growth(self) -> DCFInputs:
        if self.wacc <= self.terminal_growth:
            raise ValueError(
                f"WACC ({self.wacc:.4f}) must exceed terminal growth "
                f"({self.terminal_growth:.4f}); the Gordon terminal value diverges otherwise"
            )
        return self


class DCFResult(FinBaseModel):
    """Verified DCF output with the full valuation bridge."""

    discount_factors: list[float]
    present_values: list[float]
    sum_pv_explicit: float
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    shares_outstanding: float
    implied_share_price: float
    wacc: float
    terminal_growth: float

    @property
    def terminal_value_pct(self) -> float | None:
        """Share of enterprise value coming from the terminal value."""
        if self.enterprise_value == 0:
            return None
        return self.pv_terminal_value / self.enterprise_value


# --------------------------------------------------------------------------- #
# Comparable companies                                                        #
# --------------------------------------------------------------------------- #
class PeerCompany(FinBaseModel):
    """A single peer used in trading-comparable analysis."""

    ticker: str
    name: str | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    book_value: float | None = None

    ev_to_revenue: float | None = None
    ev_to_ebitda: float | None = None
    pe: float | None = None
    pb: float | None = None


class MultipleStats(FinBaseModel):
    """Descriptive statistics for one multiple across a peer set."""

    metric: str
    count: int
    mean: float | None = None
    median: float | None = None
    p25: float | None = None
    p75: float | None = None
    minimum: float | None = None
    maximum: float | None = None


class CompsValuation(FinBaseModel):
    """Implied valuation from applying a chosen multiple statistic."""

    metric: str
    applied_multiple: float
    basis_value: float  # the target metric the multiple is applied to
    implied_enterprise_value: float | None = None
    implied_equity_value: float | None = None
    implied_share_price: float | None = None


class CompsResult(FinBaseModel):
    """Full trading-comparables output for a target company."""

    target_ticker: str
    peers: list[PeerCompany] = Field(default_factory=list)
    stats: list[MultipleStats] = Field(default_factory=list)
    valuations: list[CompsValuation] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Precedent transactions                                                       #
# --------------------------------------------------------------------------- #
class PrecedentTransaction(FinBaseModel):
    """A single M&A precedent transaction record.

    ``is_sample`` flags illustrative data. The platform never fabricates real
    transaction figures; sample datasets are clearly labelled.
    """

    target: str
    acquirer: str
    announced_date: date | None = None
    transaction_value: float | None = None
    target_revenue: float | None = None
    target_ebitda: float | None = None
    ev_to_revenue: float | None = None
    ev_to_ebitda: float | None = None
    is_sample: bool = True


class PrecedentResult(FinBaseModel):
    """Precedent-transaction statistics and implied valuation."""

    target_ticker: str
    transactions: list[PrecedentTransaction] = Field(default_factory=list)
    stats: list[MultipleStats] = Field(default_factory=list)
    valuations: list[CompsValuation] = Field(default_factory=list)
    contains_sample_data: bool = True


# --------------------------------------------------------------------------- #
# Reverse DCF                                                                  #
# --------------------------------------------------------------------------- #
class ReverseDCFTarget(str, Enum):
    """Which assumption a reverse DCF solves for."""

    REVENUE_GROWTH = "revenue_growth"
    TERMINAL_GROWTH = "terminal_growth"


class ReverseDCFInputs(FinBaseModel):
    """Inputs to a reverse DCF that solves for a market-implied assumption."""

    current_price: float = Field(gt=0.0)
    shares_outstanding: float = Field(gt=0.0)
    net_debt: float = 0.0
    wacc: float = Field(gt=0.0, lt=1.0)
    terminal_growth: float = Field(ge=-0.05, lt=0.20)
    base_revenue: float = Field(gt=0.0)
    horizon_years: int = Field(ge=1, le=20)
    fcf_margin: float = Field(gt=-1.0, le=1.0, description="FCFF as % of revenue")
    solve_for: ReverseDCFTarget = ReverseDCFTarget.REVENUE_GROWTH


class ReverseDCFResult(FinBaseModel):
    """Market-implied assumption recovered by numerical solving."""

    solved_for: ReverseDCFTarget
    implied_value: float
    target_price: float
    achieved_price: float
    converged: bool
    iterations: int


# --------------------------------------------------------------------------- #
# Sensitivity                                                                  #
# --------------------------------------------------------------------------- #
class SensitivityAxis(FinBaseModel):
    """A named axis of parameter values for a sensitivity grid."""

    name: str
    values: list[float] = Field(min_length=1)


class SensitivityResult(FinBaseModel):
    """A 2-D sensitivity grid (e.g. WACC x terminal growth) of implied prices."""

    row_axis: SensitivityAxis
    col_axis: SensitivityAxis
    matrix: list[list[float]]
    base_value: float | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> SensitivityResult:
        expected_rows = len(self.row_axis.values)
        expected_cols = len(self.col_axis.values)
        if len(self.matrix) != expected_rows:
            raise ValueError("matrix row count does not match row_axis length")
        if any(len(row) != expected_cols for row in self.matrix):
            raise ValueError("matrix column count does not match col_axis length")
        return self


class DriverSensitivity(FinBaseModel):
    """Effect of perturbing a single driver on implied valuation."""

    driver: str
    low_value: float
    high_value: float
    low_result: float
    high_result: float

    @property
    def swing(self) -> float:
        """Absolute spread in implied value across the driver's range."""
        return abs(self.high_result - self.low_result)


class DriverSensitivityRanking(FinBaseModel):
    """Drivers ranked by their impact on implied valuation (tornado analysis)."""

    base_value: float
    drivers: list[DriverSensitivity] = Field(default_factory=list)

    def ranked(self) -> list[DriverSensitivity]:
        """Drivers sorted by descending swing."""
        return sorted(self.drivers, key=lambda d: d.swing, reverse=True)


# --------------------------------------------------------------------------- #
# Monte Carlo                                                                  #
# --------------------------------------------------------------------------- #
class DistributionType(str, Enum):
    NORMAL = "normal"
    TRIANGULAR = "triangular"
    UNIFORM = "uniform"
    LOGNORMAL = "lognormal"


class AssumptionDistribution(FinBaseModel):
    """Distribution spec for one Monte Carlo input.

    Parameter meaning depends on ``distribution``:

    * ``normal`` / ``lognormal`` — use ``mean`` and ``std``.
    * ``uniform`` — use ``low`` and ``high``.
    * ``triangular`` — use ``low``, ``mode`` (or ``mean``), ``high``.
    """

    name: str
    distribution: DistributionType = DistributionType.NORMAL
    mean: float | None = None
    std: float | None = None
    low: float | None = None
    high: float | None = None
    mode: float | None = None

    @model_validator(mode="after")
    def _check_params(self) -> AssumptionDistribution:
        d = self.distribution
        if d in (DistributionType.NORMAL, DistributionType.LOGNORMAL):
            if self.mean is None or self.std is None:
                raise ValueError(f"{d.value} distribution requires mean and std")
            if self.std < 0:
                raise ValueError("std must be non-negative")
        elif d == DistributionType.UNIFORM:
            if self.low is None or self.high is None:
                raise ValueError("uniform distribution requires low and high")
        elif d == DistributionType.TRIANGULAR:
            if self.low is None or self.high is None:
                raise ValueError("triangular distribution requires low and high")
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("low must not exceed high")
        return self


class MonteCarloInputs(FinBaseModel):
    """Configuration for a Monte Carlo DCF simulation."""

    n_simulations: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int | None = 42
    distributions: list[AssumptionDistribution] = Field(default_factory=list)


class MonteCarloResult(FinBaseModel):
    """Summary statistics from a Monte Carlo valuation run."""

    n_simulations: int
    seed: int | None = None
    mean: float
    median: float
    std: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    current_price: float | None = None
    prob_upside: float | None = None
    prob_downside: float | None = None
    # Optional coarse histogram for plotting (bin edges + counts), kept small.
    histogram_edges: list[float] = Field(default_factory=list)
    histogram_counts: list[int] = Field(default_factory=list)
