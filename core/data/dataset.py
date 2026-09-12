"""The :class:`CompanyDataset` aggregate returned by every data provider.

A dataset bundles everything the analysis and valuation engines need for one
company: identity, point-in-time market data, the three financial statements
across periods, and (optionally) a price history.

**Unit convention.** All monetary values in the platform are stored in *absolute
units of the reporting currency* (e.g. dollars, not millions). ``price`` is a
per-share value in the same currency, and share counts are absolute. Providers
are responsible for converting their source data into this convention so the
rest of the platform never has to reason about scale.
"""
from __future__ import annotations

from pydantic import Field

from ..models.base import Currency, FinBaseModel
from ..models.company import CompanyProfile, MarketData
from ..models.financials import FinancialStatements
from ..models.prices import PriceHistory
from ..models.valuation import PeerCompany, PrecedentTransaction


class CompanyDataset(FinBaseModel):
    """Everything known about a single company from one data source."""

    profile: CompanyProfile
    market_data: MarketData | None = None
    financials: FinancialStatements
    prices: PriceHistory
    peers: list[PeerCompany] = Field(default_factory=list)
    precedents: list[PrecedentTransaction] = Field(default_factory=list)

    source: str = Field(description="Identifier of the provider that produced this dataset")
    is_sample: bool = Field(
        default=False,
        description="True when the data is bundled sample/illustrative data rather than live",
    )
    note: str | None = None

    @property
    def ticker(self) -> str:
        return self.profile.ticker

    @property
    def currency(self) -> Currency:
        return self.profile.currency

    def has_financials(self) -> bool:
        """Whether at least one income statement is present."""
        return bool(self.financials.income_statements)
