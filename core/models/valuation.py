from pydantic import BaseModel, Field
from typing import List


class DCFValuation(BaseModel):
    """
    Structured output of a DCF valuation.
    """

    present_values: List[float] = Field(
        default_factory=list
    )

    terminal_value: float

    terminal_present_value: float

    enterprise_value: float

    total_debt: float = 0.0

    cash: float = 0.0

    equity_value: float

    shares_outstanding: float = 0.0

    implied_share_price: float = 0.0