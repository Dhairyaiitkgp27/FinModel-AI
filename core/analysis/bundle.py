"""Dashboard analysis orchestration.

Runs the full deterministic analysis for one company — ratios, forecast,
scenarios, and all valuation methods — and bundles the results into a single
:class:`AnalysisBundle` the UI can render. Each valuation step is wrapped so a
failure degrades gracefully (the result is ``None`` and a warning is recorded)
rather than breaking the whole dashboard.

This lives in the core layer (no UI dependency) so both the dashboard and the
report generators can consume it.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..data import CompanyDataset, load_company_dataset, validate_dataset
from ..data.validation.checks import ValidationReport
from ..forecasting import (
    build_and_compare,
    build_scenario_from_history,
    forecast_statements,
)
from ..models.analysis import RatioAnalysis
from ..models.forecast import ForecastResult, ScenarioComparison
from ..models.valuation import (
    CompsResult,
    DCFResult,
    DriverSensitivityRanking,
    MonteCarloResult,
    PrecedentResult,
    ReverseDCFResult,
    SensitivityResult,
)
from ..valuation import (
    build_comps_from_dataset,
    build_dcf_sensitivity,
    build_precedent_from_dataset,
    dcf_valuation,
    driver_sensitivity,
    monte_carlo_valuation,
    reverse_dcf_valuation,
)
from .ratios import compute_ratios


@dataclass
class AnalysisAssumptions:
    """User-tunable assumptions driving the dashboard analysis."""

    base_growth: float = 0.06
    horizon_years: int = 5
    terminal_growth: float = 0.025
    n_simulations: int = 10_000
    seed: int = 42
    comps_statistic: str = "median"


@dataclass
class AnalysisBundle:
    """The full set of analysis outputs for one company."""

    dataset: CompanyDataset
    assumptions: AnalysisAssumptions
    validation: ValidationReport
    ratios: RatioAnalysis
    forecast: ForecastResult | None = None
    scenarios: ScenarioComparison | None = None
    dcf: DCFResult | None = None
    comps: CompsResult | None = None
    precedent: PrecedentResult | None = None
    reverse_dcf: ReverseDCFResult | None = None
    sensitivity: SensitivityResult | None = None
    driver_ranking: DriverSensitivityRanking | None = None
    monte_carlo: MonteCarloResult | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def market_price(self) -> float | None:
        return self.dataset.market_data.price if self.dataset.market_data else None


def run_full_analysis(
    ticker: str,
    *,
    provider: str = "local",
    sample_dir: str | Path | None = None,
    assumptions: AnalysisAssumptions | None = None,
) -> AnalysisBundle:
    """Load a company and run the complete analysis, returning a bundle."""
    a = assumptions or AnalysisAssumptions()
    dataset = load_company_dataset(ticker, provider=provider, sample_dir=sample_dir)
    report = validate_dataset(dataset)
    ratios = compute_ratios(dataset.financials)

    warnings: list[str] = []

    def _try(fn: Callable, label: str):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - degrade gracefully per section
            warnings.append(f"{label}: {type(exc).__name__}: {exc}")
            return None

    forecast = _try(
        lambda: forecast_statements(
            dataset.financials,
            build_scenario_from_history(dataset.financials, a.base_growth, a.horizon_years),
        ),
        "forecast",
    )
    scenarios = _try(
        lambda: build_and_compare(dataset.financials, a.base_growth, a.horizon_years), "scenarios"
    )
    dcf = _try(
        lambda: dcf_valuation(
            dataset, base_growth=a.base_growth, horizon_years=a.horizon_years,
            terminal_growth=a.terminal_growth,
        ),
        "dcf",
    )
    comps = _try(
        lambda: build_comps_from_dataset(dataset, statistic=a.comps_statistic), "comps"
    )
    precedent = _try(
        lambda: build_precedent_from_dataset(dataset, statistic=a.comps_statistic), "precedent"
    )
    reverse = _try(
        lambda: reverse_dcf_valuation(
            dataset, terminal_growth=a.terminal_growth, horizon_years=a.horizon_years
        ),
        "reverse_dcf",
    )
    sensitivity = _try(
        lambda: build_dcf_sensitivity(
            dataset, base_growth=a.base_growth, horizon_years=a.horizon_years,
            terminal_growth=a.terminal_growth,
        ),
        "sensitivity",
    )
    driver_ranking = _try(
        lambda: driver_sensitivity(
            dataset, base_growth=a.base_growth, horizon_years=a.horizon_years,
            terminal_growth=a.terminal_growth,
        ),
        "driver_sensitivity",
    )
    monte_carlo = _try(
        lambda: monte_carlo_valuation(
            dataset, base_growth=a.base_growth, horizon_years=a.horizon_years,
            terminal_growth=a.terminal_growth, n_simulations=a.n_simulations, seed=a.seed,
        ),
        "monte_carlo",
    )

    return AnalysisBundle(
        dataset=dataset,
        assumptions=a,
        validation=report,
        ratios=ratios,
        forecast=forecast,
        scenarios=scenarios,
        dcf=dcf,
        comps=comps,
        precedent=precedent,
        reverse_dcf=reverse,
        sensitivity=sensitivity,
        driver_ranking=driver_ranking,
        monte_carlo=monte_carlo,
        warnings=warnings,
    )


def valuation_ranges(bundle: AnalysisBundle) -> list[tuple[str, float, float, float]]:
    """Return ``(method, low, mid, high)`` implied-price ranges for the football field.

    DCF uses the sensitivity grid for its range; comps and precedents use the
    spread of their metric-level implied prices; Monte Carlo uses P10/P50/P90.
    """
    rows: list[tuple[str, float, float, float]] = []

    if bundle.dcf is not None:
        mid = bundle.dcf.implied_share_price
        low = high = mid
        if bundle.sensitivity is not None:
            finite = [c for row in bundle.sensitivity.matrix for c in row if c == c]
            if finite:
                low, high = min(finite), max(finite)
        rows.append(("DCF", low, mid, high))

    if bundle.comps is not None:
        prices = [
            v.implied_share_price for v in bundle.comps.valuations if v.implied_share_price is not None
        ]
        if prices:
            prices.sort()
            mid = prices[len(prices) // 2]
            rows.append(("Comps", min(prices), mid, max(prices)))

    if bundle.precedent is not None:
        prices = [
            v.implied_share_price for v in bundle.precedent.valuations if v.implied_share_price is not None
        ]
        if prices:
            prices.sort()
            mid = prices[len(prices) // 2]
            rows.append(("Precedent", min(prices), mid, max(prices)))

    if bundle.monte_carlo is not None:
        rows.append(("Monte Carlo", bundle.monte_carlo.p10, bundle.monte_carlo.p50, bundle.monte_carlo.p90))

    return rows
