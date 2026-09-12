"""Shared base model, enumerations, and the :class:`FiscalPeriod` value object.

Everything in the platform derives from :class:`FinBaseModel`, which fixes a
project-wide Pydantic configuration:

* ``extra="ignore"`` — external providers (yfinance) return many fields we do
  not model; silently drop them rather than error.
* ``populate_by_name=True`` — allow population by field name or alias.
* ``str_strip_whitespace=True`` — tidy up provider strings.

We deliberately leave ``validate_assignment`` at its default (off). Several
models backfill derived quantities inside ``model_validator(mode="after")`` via
plain assignment; enabling assignment validation would re-trigger those
validators recursively. Validation still runs fully at construction time, which
is where data enters the system.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class FinBaseModel(BaseModel):
    """Project-wide base model with a consistent configuration."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class Currency(str, Enum):
    """ISO-style currency codes we commonly encounter."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CNY = "CNY"
    INR = "INR"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    KRW = "KRW"
    OTHER = "OTHER"


class PeriodType(str, Enum):
    """Granularity of a reporting period."""

    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TTM = "ttm"


class ScenarioType(str, Enum):
    """Forecast scenario families."""

    BASE = "base"
    BULL = "bull"
    BEAR = "bear"
    CUSTOM = "custom"


class StatementType(str, Enum):
    """The three financial statements."""

    INCOME = "income_statement"
    BALANCE = "balance_sheet"
    CASH_FLOW = "cash_flow_statement"


class ValuationMethod(str, Enum):
    """Supported valuation methodologies."""

    DCF = "dcf"
    COMPARABLES = "comparable_companies"
    PRECEDENT = "precedent_transactions"
    REVERSE_DCF = "reverse_dcf"
    MONTE_CARLO = "monte_carlo"


class Severity(str, Enum):
    """Severity levels for risk flags."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FiscalPeriod(FinBaseModel):
    """Identifies a single reporting period.

    Immutable and hashable so it can be used as a dictionary key and sorted.
    Ordering is chronological via :attr:`sort_key`.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    fiscal_year: int
    period_type: PeriodType = PeriodType.ANNUAL
    fiscal_quarter: int | None = None
    period_end: date | None = None

    @field_validator("fiscal_quarter")
    @classmethod
    def _validate_quarter(cls, value: int | None) -> int | None:
        if value is not None and not (1 <= value <= 4):
            raise ValueError("fiscal_quarter must be between 1 and 4")
        return value

    @property
    def sort_key(self) -> tuple[int, int]:
        """Chronological sort key ``(year, quarter)``; annual periods sort first."""
        return (self.fiscal_year, self.fiscal_quarter or 0)

    def label(self) -> str:
        """Human-readable label such as ``FY2023`` or ``Q3 2023``."""
        if self.period_type == PeriodType.QUARTERLY and self.fiscal_quarter:
            return f"Q{self.fiscal_quarter} {self.fiscal_year}"
        if self.period_type == PeriodType.TTM:
            return f"TTM {self.fiscal_year}"
        return f"FY{self.fiscal_year}"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, FiscalPeriod):
            return NotImplemented
        return self.sort_key < other.sort_key

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.label()
