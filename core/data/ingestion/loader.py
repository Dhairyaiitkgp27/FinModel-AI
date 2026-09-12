"""Ingestion entry point: turn a ticker into a validated :class:`CompanyDataset`.

This module wires configuration to the right provider and applies a graceful
fallback: if live retrieval is selected but fails (network error, unknown
ticker, missing package), and a bundled sample exists for the ticker, we fall
back to the sample rather than erroring out — logging a clear warning so the
caller knows the data is illustrative.
"""
from __future__ import annotations

from pathlib import Path

from ...utils.logging import get_logger
from ..dataset import CompanyDataset
from ..providers.base import DataProvider, DataProviderError
from ..providers.local import LocalSampleProvider
from ..providers.yfinance_provider import YFinanceProvider
from ..validation.checks import ValidationReport, validate_dataset

logger = get_logger("finmodel.ingestion")

# Resolve the default sample directory relative to the project root.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLE_DIR = _PROJECT_ROOT / "data" / "sample"


def make_provider(
    provider: str = "yfinance",
    sample_dir: Path | str | None = None,
) -> DataProvider:
    """Construct a provider by name (``'yfinance'`` or ``'local'``/``'sample'``)."""
    name = (provider or "yfinance").strip().lower()
    if name in ("local", "sample", "local_sample"):
        return LocalSampleProvider(sample_dir or DEFAULT_SAMPLE_DIR)
    if name in ("yfinance", "yahoo", "live"):
        return YFinanceProvider()
    raise ValueError(f"Unknown data provider '{provider}'")


def available_sample_tickers(sample_dir: Path | str | None = None) -> list[str]:
    """Tickers for which a bundled sample dataset exists."""
    return LocalSampleProvider(sample_dir or DEFAULT_SAMPLE_DIR).available_tickers()


def load_company_dataset(
    ticker: str,
    provider: str = "yfinance",
    *,
    sample_dir: Path | str | None = None,
    fallback_to_sample: bool = True,
) -> CompanyDataset:
    """Load a company dataset, falling back to bundled sample data on failure.

    Parameters
    ----------
    ticker:
        The company ticker (case-insensitive).
    provider:
        ``'yfinance'`` for live data or ``'local'`` to force sample data.
    sample_dir:
        Override for the sample directory (defaults to ``data/sample``).
    fallback_to_sample:
        When live retrieval fails and a sample exists, use it instead of raising.
    """
    sample_directory = sample_dir or DEFAULT_SAMPLE_DIR
    selected = make_provider(provider, sample_directory)

    try:
        dataset = selected.get_company_dataset(ticker)
        logger.info("Loaded %s from %s", ticker.upper(), selected.name)
        return dataset
    except DataProviderError as exc:
        if isinstance(selected, LocalSampleProvider) or not fallback_to_sample:
            raise
        logger.warning("Live retrieval for %s failed (%s); trying sample data", ticker.upper(), exc)

    sample_provider = LocalSampleProvider(sample_directory)
    if ticker.strip().upper() not in sample_provider.available_tickers():
        raise DataProviderError(
            f"Live retrieval failed for '{ticker}' and no bundled sample is available."
        )
    dataset = sample_provider.get_company_dataset(
        ticker, note="Live data unavailable; using bundled sample data."
    )
    logger.info("Loaded %s from bundled sample data (fallback)", ticker.upper())
    return dataset


def load_and_validate(
    ticker: str,
    provider: str = "yfinance",
    *,
    sample_dir: Path | str | None = None,
    fallback_to_sample: bool = True,
) -> tuple[CompanyDataset, ValidationReport]:
    """Load a dataset and run data-quality validation, logging any issues."""
    dataset = load_company_dataset(
        ticker,
        provider,
        sample_dir=sample_dir,
        fallback_to_sample=fallback_to_sample,
    )
    report = validate_dataset(dataset)
    if not report.is_valid:
        logger.warning("Validation issues for %s: %s", ticker.upper(), report.summary())
    return dataset, report
