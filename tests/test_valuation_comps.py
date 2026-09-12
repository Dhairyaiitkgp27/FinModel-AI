"""Tests for the comparables and precedent-transaction engines."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.data import LocalSampleProvider
from core.models import PeerCompany, PrecedentTransaction
from core.valuation import (
    build_comps_from_dataset,
    build_precedent_from_dataset,
    compute_comps,
    compute_peer_multiples,
    compute_precedent,
    summarize_multiples,
)
from core.valuation.comps import _valuation_for_multiple  # noqa: F401 (import check)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


# --------------------------------------------------------------------------- #
# Peer multiples                                                              #
# --------------------------------------------------------------------------- #
def test_compute_peer_multiples_fills_from_components():
    peer = PeerCompany(
        ticker="X",
        enterprise_value=1000.0,
        revenue=100.0,
        ebitda=200.0,
        market_cap=600.0,
        net_income=30.0,
        book_value=300.0,
    )
    enriched = compute_peer_multiples(peer)
    assert enriched.ev_to_revenue == pytest.approx(10.0)
    assert enriched.ev_to_ebitda == pytest.approx(5.0)
    assert enriched.pe == pytest.approx(20.0)
    assert enriched.pb == pytest.approx(2.0)


def test_compute_peer_multiples_preserves_provided():
    peer = PeerCompany(ticker="X", enterprise_value=1000.0, revenue=100.0, ev_to_revenue=7.5)
    assert compute_peer_multiples(peer).ev_to_revenue == pytest.approx(7.5)


# --------------------------------------------------------------------------- #
# Summary statistics                                                          #
# --------------------------------------------------------------------------- #
def test_summarize_multiples_exact_and_filters():
    peers = [
        PeerCompany(ticker="A", ev_to_revenue=10.0),
        PeerCompany(ticker="B", ev_to_revenue=20.0),
        PeerCompany(ticker="C", ev_to_revenue=30.0),
        PeerCompany(ticker="D", ev_to_revenue=None),  # excluded
        PeerCompany(ticker="E", ev_to_revenue=-5.0),  # excluded (non-positive)
    ]
    stats = summarize_multiples(peers, "ev_to_revenue")
    assert stats.count == 3
    assert stats.mean == pytest.approx(20.0)
    assert stats.median == pytest.approx(20.0)
    assert stats.p25 == pytest.approx(15.0)
    assert stats.p75 == pytest.approx(25.0)
    assert stats.minimum == pytest.approx(10.0)
    assert stats.maximum == pytest.approx(30.0)


def test_summarize_empty_is_zero_count():
    stats = summarize_multiples([], "pe")
    assert stats.count == 0
    assert stats.median is None


# --------------------------------------------------------------------------- #
# Comps valuation                                                             #
# --------------------------------------------------------------------------- #
def test_compute_comps_ev_and_equity_bridges():
    peers = [
        PeerCompany(ticker="A", ev_to_revenue=8.0, pe=15.0),
        PeerCompany(ticker="B", ev_to_revenue=10.0, pe=20.0),
        PeerCompany(ticker="C", ev_to_revenue=12.0, pe=25.0),
    ]
    result = compute_comps(
        "TGT",
        peers,
        target_revenue=1000.0,
        target_net_income=500.0,
        net_debt=200.0,
        shares_outstanding=100.0,
        statistic="median",
        metrics=("ev_to_revenue", "pe"),
    )
    by_metric = {v.metric: v for v in result.valuations}

    ev_val = by_metric["ev_to_revenue"]  # EV-based
    assert ev_val.applied_multiple == pytest.approx(10.0)
    assert ev_val.implied_enterprise_value == pytest.approx(10000.0)
    assert ev_val.implied_equity_value == pytest.approx(9800.0)  # EV - net debt
    assert ev_val.implied_share_price == pytest.approx(98.0)

    pe_val = by_metric["pe"]  # equity-based
    assert pe_val.applied_multiple == pytest.approx(20.0)
    assert pe_val.implied_equity_value == pytest.approx(10000.0)  # 20 * 500
    assert pe_val.implied_enterprise_value == pytest.approx(10200.0)  # equity + net debt
    assert pe_val.implied_share_price == pytest.approx(100.0)


def test_comps_mean_statistic():
    peers = [PeerCompany(ticker="A", ev_to_revenue=10.0), PeerCompany(ticker="B", ev_to_revenue=20.0)]
    result = compute_comps(
        "TGT", peers, target_revenue=100.0, shares_outstanding=10.0, statistic="mean",
        metrics=("ev_to_revenue",),
    )
    assert result.valuations[0].applied_multiple == pytest.approx(15.0)  # (10+20)/2


def test_build_comps_from_sample_dataset():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    result = build_comps_from_dataset(ds, statistic="median")
    assert result.target_ticker == "AAPL"
    assert len(result.peers) == 3
    ev_rev = next(s for s in result.stats if s.metric == "ev_to_revenue")
    # peers: MSFT 2.56T/211.9B=12.08, GOOGL 1.6T/307.4B=5.21, META 0.87T/134.9B=6.45 -> median 6.45
    assert ev_rev.median == pytest.approx(6.45, abs=0.02)


# --------------------------------------------------------------------------- #
# Precedent transactions                                                      #
# --------------------------------------------------------------------------- #
def test_compute_precedent_exact():
    txns = [
        PrecedentTransaction(target="a", acquirer="x", ev_to_revenue=4.0, ev_to_ebitda=12.0),
        PrecedentTransaction(target="b", acquirer="y", ev_to_revenue=6.0, ev_to_ebitda=16.0),
        PrecedentTransaction(target="c", acquirer="z", ev_to_revenue=8.0, ev_to_ebitda=20.0),
    ]
    result = compute_precedent(
        "TGT", txns, target_revenue=1000.0, target_ebitda=300.0,
        net_debt=100.0, shares_outstanding=50.0, statistic="median",
    )
    by_metric = {v.metric: v for v in result.valuations}
    rev = by_metric["ev_to_revenue"]
    assert rev.applied_multiple == pytest.approx(6.0)  # median of 4,6,8
    assert rev.implied_enterprise_value == pytest.approx(6000.0)
    assert rev.implied_equity_value == pytest.approx(5900.0)
    assert rev.implied_share_price == pytest.approx(118.0)

    ebitda = by_metric["ev_to_ebitda"]
    assert ebitda.applied_multiple == pytest.approx(16.0)
    assert ebitda.implied_enterprise_value == pytest.approx(4800.0)


def test_precedent_flags_sample_data():
    txns = [PrecedentTransaction(target="a", acquirer="x", ev_to_revenue=5.0, is_sample=True)]
    result = compute_precedent("TGT", txns, target_revenue=1000.0, shares_outstanding=10.0)
    assert result.contains_sample_data is True


def test_build_precedent_from_sample_dataset():
    ds = LocalSampleProvider(SAMPLE_DIR).get_company_dataset("AAPL")
    result = build_precedent_from_dataset(ds, statistic="median")
    assert result.contains_sample_data is True
    ev_rev = next(s for s in result.stats if s.metric == "ev_to_revenue")
    # sample deal EV/Revenue multiples 8,6.5,4,3 -> median (6.5+4)/2 = 5.25
    assert ev_rev.median == pytest.approx(5.25)


# --------------------------------------------------------------------------- #
# Provider loads comparables data                                             #
# --------------------------------------------------------------------------- #
def test_provider_loads_and_scales_peers():
    provider = LocalSampleProvider(SAMPLE_DIR)
    peers = provider.get_peers("AAPL")
    assert len(peers) == 3
    msft = next(p for p in peers if p.ticker == "MSFT")
    # market cap authored as 2,600,000 (millions) -> scaled to absolute
    assert msft.market_cap == pytest.approx(2_600_000e6)


def test_provider_loads_precedents():
    provider = LocalSampleProvider(SAMPLE_DIR)
    precedents = provider.get_precedents("MSFT")
    assert len(precedents) == 4
    assert all(t.is_sample for t in precedents)
    # multiples are not scaled
    assert precedents[0].ev_to_revenue == pytest.approx(8.0)
