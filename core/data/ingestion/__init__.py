"""Ingestion: ticker -> validated CompanyDataset."""
from __future__ import annotations

from .loader import (
    available_sample_tickers,
    load_and_validate,
    load_company_dataset,
    make_provider,
)

__all__ = [
    "load_company_dataset",
    "load_and_validate",
    "make_provider",
    "available_sample_tickers",
]
