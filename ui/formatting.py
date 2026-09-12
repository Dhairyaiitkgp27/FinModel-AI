"""Display formatting helpers for the dashboard.

Pure functions with no UI dependencies, so they are trivially testable and can be
reused anywhere a human-readable number is needed.
"""
from __future__ import annotations


def format_large(value: float | None, currency: str = "$", decimals: int = 1) -> str:
    """Format a large monetary value with a T/B/M/K suffix (e.g. ``$2.7T``)."""
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if magnitude >= threshold:
            return f"{sign}{currency}{magnitude / threshold:,.{decimals}f}{suffix}"
    return f"{sign}{currency}{magnitude:,.0f}"


def format_currency(value: float | None, currency: str = "$", decimals: int = 2) -> str:
    """Format a per-share or small monetary value (e.g. ``$176.65``)."""
    if value is None:
        return "—"
    return f"{currency}{value:,.{decimals}f}"


def format_pct(value: float | None, decimals: int = 1, already_pct: bool = False) -> str:
    """Format a ratio as a percentage. ``value=0.44`` -> ``44.0%``."""
    if value is None:
        return "—"
    scaled = value if already_pct else value * 100.0
    return f"{scaled:,.{decimals}f}%"


def format_multiple(value: float | None, decimals: int = 1) -> str:
    """Format a valuation multiple (e.g. ``16.8x``)."""
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}x"


def format_signed_pct(value: float | None, decimals: int = 1) -> str:
    """Format a signed percentage change with an explicit +/- sign."""
    if value is None:
        return "—"
    return f"{value * 100:+,.{decimals}f}%"


def upside_label(implied: float | None, market: float | None) -> str:
    """Describe implied price versus market as an upside/downside percentage."""
    if implied is None or market is None or market == 0:
        return "—"
    change = (implied - market) / market
    direction = "upside" if change >= 0 else "downside"
    return f"{abs(change) * 100:,.0f}% {direction}"
