"""Tests for core.utils.math helpers."""
from __future__ import annotations

import math

import pytest

from core.utils.math import (
    cagr,
    clamp,
    mean,
    median,
    pct_change,
    percentile,
    safe_div,
    stdev,
)


def test_safe_div_normal():
    assert safe_div(10, 4) == 2.5


def test_safe_div_zero_denominator_returns_none():
    assert safe_div(10, 0) is None


def test_safe_div_none_inputs_return_none():
    assert safe_div(None, 5) is None
    assert safe_div(5, None) is None


def test_pct_change():
    assert pct_change(110, 100) == pytest.approx(0.10)


def test_pct_change_uses_abs_of_previous():
    # Growth relative to a negative base uses |previous|
    assert pct_change(-50, -100) == pytest.approx(0.5)


def test_pct_change_zero_previous_returns_none():
    assert pct_change(10, 0) is None


def test_cagr_basic():
    # 100 -> 200 over 2 years ~ 41.42%
    assert cagr(100, 200, 2) == pytest.approx(math.sqrt(2) - 1)


def test_cagr_rejects_non_positive_endpoints():
    assert cagr(-100, 200, 2) is None
    assert cagr(100, 200, 0) is None


def test_mean_ignores_none():
    assert mean([2, 4, None, 6]) == pytest.approx(4.0)


def test_mean_empty_returns_none():
    assert mean([None, None]) is None


def test_median_odd_and_even():
    assert median([3, 1, 2]) == 2
    assert median([1, 2, 3, 4]) == pytest.approx(2.5)


def test_stdev_sample():
    # sample stdev of [2,4,6] = 2.0
    assert stdev([2, 4, 6]) == pytest.approx(2.0)


def test_stdev_single_value_sample_returns_none():
    assert stdev([5.0]) is None


def test_percentile_matches_linear_interpolation():
    data = [1, 2, 3, 4]
    assert percentile(data, 0) == 1
    assert percentile(data, 100) == 4
    assert percentile(data, 50) == pytest.approx(2.5)
    assert percentile(data, 25) == pytest.approx(1.75)


def test_percentile_out_of_range_raises():
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 150)


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(99, 0, 10) == 10
