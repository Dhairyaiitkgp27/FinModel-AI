from pydantic import BaseModel
from typing import Optional


class FinancialPeriod(BaseModel):
    """
    Represents the financial data for one fiscal year.
    All monetary values are stored in millions of the reporting currency.
    """

    year: int

    # Income Statement
    revenue: Optional[float] = None
    cogs: Optional[float] = None
    operating_expenses: Optional[float] = None
    depreciation: Optional[float] = None
    interest_expense: Optional[float] = None
    taxes: Optional[float] = None

    # Balance Sheet
    cash: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    ppe: Optional[float] = None

    accounts_payable: Optional[float] = None
    debt: Optional[float] = None
    equity: Optional[float] = None

    # Cash Flow
    capex: Optional[float] = None