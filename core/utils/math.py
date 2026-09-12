"""Small, dependency-free numeric helpers.

These are deliberately implemented in pure Python (no NumPy) so that the model
layer and lightweight utilities can be imported without pulling in the heavy
scientific stack. The Monte Carlo and forecasting engines in later phases use
NumPy/SciPy directly where vectorised performance matters.

Every helper is *None-safe*: missing inputs yield ``None`` rather than raising,
which matches the reality of sparse financial data from external providers.
"""
from __future__ import annotations

import math
from collections.abc import Iterable

Number = float | None


def safe_div(numerator: Number, denominator: Number) -> Number:
    """Divide two numbers, returning ``None`` on missing data or zero divisor."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def pct_change(current: Number, previous: Number) -> Number:
    """Percentage change from ``previous`` to ``current`` (e.g. 0.12 == +12%)."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def cagr(begin: Number, end: Number, periods: float) -> Number:
    """Compound annual growth rate over ``periods`` years.

    Returns ``None`` if either endpoint is missing or non-positive (a CAGR is
    undefined when the series crosses zero).
    """
    if begin is None or end is None or periods <= 0:
        return None
    if begin <= 0 or end <= 0:
        return None
    return (end / begin) ** (1.0 / periods) - 1.0


def _clean(values: Iterable[Number]) -> list[float]:
    return [float(v) for v in values if v is not None]


def mean(values: Iterable[Number]) -> Number:
    vals = _clean(values)
    return sum(vals) / len(vals) if vals else None


def median(values: Iterable[Number]) -> Number:
    vals = sorted(_clean(values))
    n = len(vals)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def stdev(values: Iterable[Number], sample: bool = True) -> Number:
    """Standard deviation. Sample (n-1) by default, population when ``sample`` is False."""
    vals = _clean(values)
    n = len(vals)
    if n < 2 if sample else n < 1:
        return None
    m = sum(vals) / n
    denom = (n - 1) if sample else n
    var = sum((x - m) ** 2 for x in vals) / denom
    return math.sqrt(var)


def percentile(values: Iterable[Number], q: float) -> Number:
    """Linear-interpolation percentile matching NumPy's default method.

    ``q`` is expressed on a 0-100 scale.
    """
    if not 0.0 <= q <= 100.0:
        raise ValueError("percentile q must be between 0 and 100")
    vals = sorted(_clean(values))
    n = len(vals)
    if n == 0:
        return None
    if n == 1:
        return vals[0]
    rank = (n - 1) * (q / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return vals[int(rank)]
    return vals[low] + (vals[high] - vals[low]) * (rank - low)


def clamp(value: float, lower: float, upper: float) -> float:
    """Constrain ``value`` to the inclusive ``[lower, upper]`` range."""
    return max(lower, min(upper, value))
