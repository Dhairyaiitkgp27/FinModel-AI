"""Trading-comparables ("comps") valuation engine.

Computes each peer's valuation multiples (EV/Revenue, EV/EBITDA, P/E, P/B),
summarises them across the peer set (mean, median, quartiles, range), and
applies a chosen summary statistic to the target company's own metrics to imply
a valuation.

EV-based multiples imply an enterprise value (then bridged to equity by
subtracting net debt); equity-based multiples (P/E, P/B) imply an equity value
directly. Non-positive or missing multiples are excluded from the statistics so
that, for example, a loss-making peer does not contaminate the P/E set.
"""
from __future__ import annotations

from ..models.valuation import CompsResult, CompsValuation, MultipleStats, PeerCompany
from ..utils.math import mean, median, percentile, safe_div

# Multiples the engine knows about and whether each is EV-based or equity-based.
_EV_MULTIPLES = ("ev_to_revenue", "ev_to_ebitda")
_EQUITY_MULTIPLES = ("pe", "pb")
ALL_MULTIPLES = _EV_MULTIPLES + _EQUITY_MULTIPLES

# For each multiple, the target metric its statistic is applied to.
_BASIS_ATTR = {
    "ev_to_revenue": "revenue",
    "ev_to_ebitda": "ebitda",
    "pe": "net_income",
    "pb": "book_value",
}


def compute_peer_multiples(peer: PeerCompany) -> PeerCompany:
    """Return a copy of ``peer`` with any missing multiples filled from components."""
    updates: dict[str, float | None] = {}
    if peer.ev_to_revenue is None:
        updates["ev_to_revenue"] = safe_div(peer.enterprise_value, peer.revenue)
    if peer.ev_to_ebitda is None:
        updates["ev_to_ebitda"] = safe_div(peer.enterprise_value, peer.ebitda)
    if peer.pe is None:
        updates["pe"] = safe_div(peer.market_cap, peer.net_income)
    if peer.pb is None:
        updates["pb"] = safe_div(peer.market_cap, peer.book_value)
    return peer.model_copy(update=updates) if updates else peer


def summarize_multiples(peers: list[PeerCompany], metric: str) -> MultipleStats:
    """Summary statistics for one multiple across the peer set (positives only)."""
    values = [
        getattr(p, metric)
        for p in peers
        if getattr(p, metric, None) is not None and getattr(p, metric) > 0
    ]
    return MultipleStats(
        metric=metric,
        count=len(values),
        mean=mean(values),
        median=median(values),
        p25=percentile(values, 25) if values else None,
        p75=percentile(values, 75) if values else None,
        minimum=min(values) if values else None,
        maximum=max(values) if values else None,
    )


def _statistic_value(stats: MultipleStats, statistic: str) -> float | None:
    return getattr(stats, statistic, None)


def _valuation_for_multiple(
    metric: str,
    applied_multiple: float,
    basis_value: float,
    net_debt: float,
    shares: float | None,
) -> CompsValuation:
    implied_ev: float | None = None
    implied_equity: float | None = None
    if metric in _EV_MULTIPLES:
        implied_ev = applied_multiple * basis_value
        implied_equity = implied_ev - net_debt
    else:  # equity-based multiple
        implied_equity = applied_multiple * basis_value
        implied_ev = implied_equity + net_debt
    implied_price = safe_div(implied_equity, shares)
    return CompsValuation(
        metric=metric,
        applied_multiple=applied_multiple,
        basis_value=basis_value,
        implied_enterprise_value=implied_ev,
        implied_equity_value=implied_equity,
        implied_share_price=implied_price,
    )


def compute_comps(
    target_ticker: str,
    peers: list[PeerCompany],
    *,
    target_revenue: float | None = None,
    target_ebitda: float | None = None,
    target_net_income: float | None = None,
    target_book_value: float | None = None,
    net_debt: float = 0.0,
    shares_outstanding: float | None = None,
    statistic: str = "median",
    metrics: tuple[str, ...] = ALL_MULTIPLES,
) -> CompsResult:
    """Run a full trading-comparables analysis for a target company."""
    enriched = [compute_peer_multiples(p) for p in peers]
    basis_values = {
        "revenue": target_revenue,
        "ebitda": target_ebitda,
        "net_income": target_net_income,
        "book_value": target_book_value,
    }

    stats: list[MultipleStats] = []
    valuations: list[CompsValuation] = []
    for metric in metrics:
        metric_stats = summarize_multiples(enriched, metric)
        stats.append(metric_stats)

        applied = _statistic_value(metric_stats, statistic)
        basis = basis_values.get(_BASIS_ATTR[metric])
        if applied is not None and applied > 0 and basis is not None:
            valuations.append(
                _valuation_for_multiple(metric, applied, basis, net_debt, shares_outstanding)
            )

    return CompsResult(
        target_ticker=target_ticker, peers=enriched, stats=stats, valuations=valuations
    )


def build_comps_from_dataset(
    dataset, *, statistic: str = "median", metrics: tuple[str, ...] = ALL_MULTIPLES
) -> CompsResult:
    """Run comps for a :class:`CompanyDataset` using its bundled peers."""
    income = dataset.financials.latest_income()
    balance = dataset.financials.latest_balance()
    market = dataset.market_data

    net_debt = 0.0
    if market is not None and market.net_debt is not None:
        net_debt = market.net_debt
    elif balance is not None and balance.net_debt is not None:
        net_debt = balance.net_debt

    return compute_comps(
        dataset.ticker,
        dataset.peers,
        target_revenue=income.revenue if income else None,
        target_ebitda=income.ebitda if income else None,
        target_net_income=income.net_income if income else None,
        target_book_value=balance.total_equity if balance else None,
        net_debt=net_debt,
        shares_outstanding=market.shares_outstanding if market else None,
        statistic=statistic,
        metrics=metrics,
    )
