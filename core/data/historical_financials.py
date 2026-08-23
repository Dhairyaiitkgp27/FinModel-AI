from pydantic import BaseModel


class HistoricalFinancials(BaseModel):
    """
    Historical financial data for one fiscal year.

    Monetary values are assumed to be in millions.
    """

    year: int

    # Income Statement
    revenue: float
    cogs: float
    operating_expenses: float
    depreciation: float
    interest_expense: float
    taxes: float

    # Balance Sheet
    cash: float
    total_debt: float
    total_assets: float
    shareholders_equity: float