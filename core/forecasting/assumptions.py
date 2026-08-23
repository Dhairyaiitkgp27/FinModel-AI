from pydantic import BaseModel, Field


class ForecastAssumptions(BaseModel):
    """
    Assumptions used to forecast a company's financial statements.
    """

    revenue_growth: float = Field(
        default=0.08,
        description="Expected annual revenue growth"
    )

    cogs_margin: float = Field(
        default=0.60,
        description="COGS as a percentage of revenue"
    )

    operating_expense_margin: float = Field(
        default=0.20,
        description="Operating expenses as a percentage of revenue"
    )

    depreciation_margin: float = Field(
        default=0.05,
        description="Depreciation as a percentage of revenue"
    )

    interest_expense: float = Field(
        default=20.0,
        description="Annual interest expense"
    )

    tax_rate: float = Field(
        default=0.25,
        description="Corporate tax rate"
    )