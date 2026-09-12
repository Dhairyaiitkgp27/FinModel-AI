"""Data layer: providers, normalisation, validation, and ingestion.

The public entry point is :func:`load_company_dataset` (and
:func:`load_and_validate`), which turn a ticker into a typed
:class:`CompanyDataset` using live or bundled-sample data.
"""
from __future__ import annotations

from .dataset import CompanyDataset
from .ingestion import (
    available_sample_tickers,
    load_and_validate,
    load_company_dataset,
    make_provider,
)
from .providers import (
    DataProvider,
    DataProviderError,
    LocalSampleProvider,
    YFinanceProvider,
)
from .validation import ValidationIssue, ValidationReport, validate_dataset

__all__ = [
    "CompanyDataset",
    "DataProvider",
    "DataProviderError",
    "LocalSampleProvider",
    "YFinanceProvider",
    "ValidationIssue",
    "ValidationReport",
    "validate_dataset",
    "load_company_dataset",
    "load_and_validate",
    "make_provider",
    "available_sample_tickers",
]
