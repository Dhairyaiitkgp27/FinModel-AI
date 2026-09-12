"""The data-provider contract.

Every source of company data (live or sample) implements :class:`DataProvider`.
Subclasses supply the four granular fetch methods; the base class composes them
into a :class:`CompanyDataset` via :meth:`get_company_dataset`, tagging it with
the provider's name and sample flag. This keeps ingestion code provider-agnostic
and makes each piece independently testable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ...models.company import CompanyProfile, MarketData
from ...models.financials import FinancialStatements
from ...models.prices import PriceHistory
from ...models.valuation import PeerCompany, PrecedentTransaction
from ..dataset import CompanyDataset


class DataProviderError(RuntimeError):
    """Raised when a provider cannot retrieve or parse data for a ticker."""


class DataProvider(ABC):
    """Abstract base class for all company-data providers."""

    #: Short identifier recorded on datasets this provider produces.
    name: str = "provider"
    #: Whether datasets from this provider are bundled sample data.
    is_sample: bool = False

    # --- Granular fetch methods (implemented by subclasses) ------------- #
    @abstractmethod
    def get_company_profile(self, ticker: str) -> CompanyProfile:
        """Return static descriptive information for ``ticker``."""

    @abstractmethod
    def get_market_data(self, ticker: str) -> MarketData:
        """Return point-in-time market data for ``ticker``."""

    @abstractmethod
    def get_financials(self, ticker: str) -> FinancialStatements:
        """Return the three financial statements across available periods."""

    @abstractmethod
    def get_price_history(self, ticker: str) -> PriceHistory:
        """Return a historical price series (may be empty if unavailable)."""

    # --- Optional comparables data (default: none) ---------------------- #
    def get_peers(self, ticker: str) -> list[PeerCompany]:
        """Return trading-comparable peers for ``ticker`` (empty by default)."""
        return []

    def get_precedents(self, ticker: str) -> list[PrecedentTransaction]:
        """Return precedent M&A transactions relevant to ``ticker`` (empty by default)."""
        return []

    # --- Composed convenience ------------------------------------------- #
    def get_company_dataset(self, ticker: str, note: str | None = None) -> CompanyDataset:
        """Assemble a full :class:`CompanyDataset` from the granular methods."""
        profile = self.get_company_profile(ticker)
        try:
            market_data = self.get_market_data(ticker)
        except DataProviderError:
            market_data = None
        financials = self.get_financials(ticker)
        prices = self.get_price_history(ticker)
        return CompanyDataset(
            profile=profile,
            market_data=market_data,
            financials=financials,
            prices=prices,
            peers=self.get_peers(ticker),
            precedents=self.get_precedents(ticker),
            source=self.name,
            is_sample=self.is_sample,
            note=note,
        )
