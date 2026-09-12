"""Centralised logging configuration for FinModel AI.

A single :func:`configure_logging` call sets up a consistent format; modules
obtain loggers via :func:`get_logger`. Configuration is idempotent so importing
it from multiple entry points (Streamlit, tests, CLI) is safe.
"""
from __future__ import annotations

import logging

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str = "INFO", *, force: bool = False) -> None:
    """Configure the root logger once with the project format.

    Parameters
    ----------
    level:
        Logging level name (``"DEBUG"``, ``"INFO"``, ...). Unknown names fall
        back to ``INFO``.
    force:
        Re-apply configuration even if it has already been set up.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format=_FORMAT, datefmt=_DATEFMT, force=True)
    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced logger, configuring logging on first use."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name if name else "finmodel")
