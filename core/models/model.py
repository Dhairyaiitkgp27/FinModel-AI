from pydantic import BaseModel, Field
from typing import List

from .financials import FinancialPeriod


class FinancialModel(BaseModel):
    """
    Canonical representation of a company's financial model.
    """

    company_name: str
    currency: str = "USD"

    historical_periods: List[FinancialPeriod] = Field(
        default_factory=list
    )

    forecast_periods: List[FinancialPeriod] = Field(
        default_factory=list
    )

    revenue_growth_assumptions: List[float] = Field(
        default_factory=list
    )

    tax_rate: float = 0.25

    wacc: float | None = None

    terminal_growth_rate: float | None = None