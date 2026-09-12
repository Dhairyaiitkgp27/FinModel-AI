"""Precedent-transactions valuation engine.

Applies the same multiple machinery as trading comps, but to a set of M&A
transactions rather than public peers. Precedent deals are valued on EV-based
multiples only (EV/Revenue and EV/EBITDA), which is standard: a transaction's
equity/earnings multiples are rarely comparable across deals with different
capital structures.

Sample transactions are always flagged (``is_sample=True``) and the result
records whether any sample data contributed, so downstream narration can be
transparent that these are illustrative rather than a real deal database.
"""
from __future__ import annotations

from ..models.valuation import (
    CompsValuation,
    MultipleStats,
    PrecedentResult,
    PrecedentTransaction,
)
from ..utils.math import mean, median, percentile, safe_div

# Precedent analysis uses EV-based multiples only.
PRECEDENT_MULTIPLES = ("ev_to_revenue", "ev_to_ebitda")

_BASIS_ATTR = {"ev_to_revenue": "revenue", "ev_to_ebitda": "ebitda"}


def compute_transaction_multiples(tx: PrecedentTransaction) -> PrecedentTransaction:
    """Fill missing deal multiples from transaction value and target metrics."""
    updates: dict[str, float | None] = {}
    if tx.ev_to_revenue is None:
        updates["ev_to_revenue"] = safe_div(tx.transaction_value, tx.target_revenue)
    if tx.ev_to_ebitda is None:
        updates["ev_to_ebitda"] = safe_div(tx.transaction_value, tx.target_ebitda)
    return tx.model_copy(update=updates) if updates else tx


def summarize_transaction_multiples(
    transactions: list[PrecedentTransaction], metric: str
) -> MultipleStats:
    """Summary statistics for one deal multiple across the transaction set."""
    values = [
        getattr(t, metric)
        for t in transactions
        if getattr(t, metric, None) is not None and getattr(t, metric) > 0
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


def compute_precedent(
    target_ticker: str,
    transactions: list[PrecedentTransaction],
    *,
    target_revenue: float | None = None,
    target_ebitda: float | None = None,
    net_debt: float = 0.0,
    shares_outstanding: float | None = None,
    statistic: str = "median",
) -> PrecedentResult:
    """Run a precedent-transactions valuation for a target company."""
    enriched = [compute_transaction_multiples(t) for t in transactions]
    basis_values = {"revenue": target_revenue, "ebitda": target_ebitda}

    stats: list[MultipleStats] = []
    valuations: list[CompsValuation] = []
    for metric in PRECEDENT_MULTIPLES:
        metric_stats = summarize_transaction_multiples(enriched, metric)
        stats.append(metric_stats)

        applied = getattr(metric_stats, statistic, None)
        basis = basis_values.get(_BASIS_ATTR[metric])
        if applied is not None and applied > 0 and basis is not None:
            implied_ev = applied * basis
            implied_equity = implied_ev - net_debt
            valuations.append(
                CompsValuation(
                    metric=metric,
                    applied_multiple=applied,
                    basis_value=basis,
                    implied_enterprise_value=implied_ev,
                    implied_equity_value=implied_equity,
                    implied_share_price=safe_div(implied_equity, shares_outstanding),
                )
            )

    return PrecedentResult(
        target_ticker=target_ticker,
        transactions=enriched,
        stats=stats,
        valuations=valuations,
        contains_sample_data=any(t.is_sample for t in enriched),
    )


def build_precedent_from_dataset(dataset, *, statistic: str = "median") -> PrecedentResult:
    """Run precedent analysis for a :class:`CompanyDataset` using its bundled deals."""
    income = dataset.financials.latest_income()
    balance = dataset.financials.latest_balance()
    market = dataset.market_data

    net_debt = 0.0
    if market is not None and market.net_debt is not None:
        net_debt = market.net_debt
    elif balance is not None and balance.net_debt is not None:
        net_debt = balance.net_debt

    return compute_precedent(
        dataset.ticker,
        dataset.precedents,
        target_revenue=income.revenue if income else None,
        target_ebitda=income.ebitda if income else None,
        net_debt=net_debt,
        shares_outstanding=market.shares_outstanding if market else None,
        statistic=statistic,
    )
