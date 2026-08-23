from typing import Dict


def calculate_profitability_ratios(
    revenue: float,
    cogs: float,
    operating_expenses: float,
    depreciation: float,
    net_income: float,
) -> Dict[str, float]:
    """
    Calculate core profitability ratios.
    """

    if revenue == 0:
        raise ValueError("Revenue cannot be zero.")

    gross_profit = revenue - cogs

    ebitda = (
        revenue
        - cogs
        - operating_expenses
    )

    ebit = ebitda - depreciation

    return {
        "gross_margin": gross_profit / revenue,
        "ebitda_margin": ebitda / revenue,
        "ebit_margin": ebit / revenue,
        "net_margin": net_income / revenue,
    }


def calculate_leverage_ratios(
    total_debt: float,
    cash: float,
    ebitda: float,
    interest_expense: float,
) -> Dict[str, float]:
    """
    Calculate core leverage and debt-service ratios.
    """

    net_debt = total_debt - cash

    ratios = {
        "net_debt": net_debt,
        "debt_to_ebitda": (
            total_debt / ebitda
            if ebitda != 0
            else float("inf")
        ),
        "net_debt_to_ebitda": (
            net_debt / ebitda
            if ebitda != 0
            else float("inf")
        ),
        "interest_coverage": (
            ebitda / interest_expense
            if interest_expense != 0
            else float("inf")
        ),
    }

    return ratios


def calculate_liquidity_ratios(
    cash: float,
    accounts_receivable: float,
    inventory: float,
    current_liabilities: float,
) -> Dict[str, float]:
    """
    Calculate liquidity ratios.
    """

    if current_liabilities == 0:
        raise ValueError(
            "Current liabilities cannot be zero."
        )

    current_assets = (
        cash
        + accounts_receivable
        + inventory
    )

    quick_assets = (
        cash
        + accounts_receivable
    )

    return {
        "current_ratio": (
            current_assets / current_liabilities
        ),
        "quick_ratio": (
            quick_assets / current_liabilities
        ),
    }


def calculate_efficiency_ratios(
    revenue: float,
    accounts_receivable: float,
    inventory: float,
    cogs: float,
) -> Dict[str, float]:
    """
    Calculate operating efficiency ratios.
    """

    if accounts_receivable == 0:
        receivables_turnover = float("inf")
    else:
        receivables_turnover = (
            revenue / accounts_receivable
        )

    if inventory == 0:
        inventory_turnover = float("inf")
    else:
        inventory_turnover = (
            cogs / inventory
        )

    return {
        "receivables_turnover": receivables_turnover,
        "inventory_turnover": inventory_turnover,
    }
def calculate_growth_metrics(
    current_revenue: float,
    previous_revenue: float,
    current_ebitda: float,
    previous_ebitda: float,
    current_ebit: float,
    previous_ebit: float,
    current_net_income: float,
    previous_net_income: float,
) -> Dict[str, float]:
    """
    Calculate year-over-year growth metrics.
    """

    def growth(current, previous):
        if previous == 0:
            return float("inf")
        return (current - previous) / previous

    return {
        "revenue_growth": growth(
            current_revenue,
            previous_revenue,
        ),
        "ebitda_growth": growth(
            current_ebitda,
            previous_ebitda,
        ),
        "ebit_growth": growth(
            current_ebit,
            previous_ebit,
        ),
        "net_income_growth": growth(
            current_net_income,
            previous_net_income,
        ),
    }


def calculate_margin_change(
    current_revenue: float,
    previous_revenue: float,
    current_ebitda: float,
    previous_ebitda: float,
    current_ebit: float,
    previous_ebit: float,
) -> Dict[str, float]:
    """
    Calculate year-over-year changes in operating margins.
    """

    if current_revenue == 0:
        raise ValueError(
            "Current revenue cannot be zero."
        )

    if previous_revenue == 0:
        raise ValueError(
            "Previous revenue cannot be zero."
        )

    current_ebitda_margin = (
        current_ebitda / current_revenue
    )

    previous_ebitda_margin = (
        previous_ebitda / previous_revenue
    )

    current_ebit_margin = (
        current_ebit / current_revenue
    )

    previous_ebit_margin = (
        previous_ebit / previous_revenue
    )

    return {
        "ebitda_margin_change": (
            current_ebitda_margin
            - previous_ebitda_margin
        ),
        "ebit_margin_change": (
            current_ebit_margin
            - previous_ebit_margin
        ),
    }


def calculate_cagr(
    beginning_value: float,
    ending_value: float,
    years: int,
) -> float:
    """
    Calculate compound annual growth rate.
    """

    if years <= 0:
        raise ValueError(
            "Years must be greater than zero."
        )

    if beginning_value <= 0:
        raise ValueError(
            "Beginning value must be positive."
        )

    if ending_value < 0:
        raise ValueError(
            "Ending value cannot be negative."
        )

    return (
        ending_value / beginning_value
    ) ** (1 / years) - 1