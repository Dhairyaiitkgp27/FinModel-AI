from core.models.valuation import DCFValuation
def calculate_dcf_value(
    free_cash_flows,
    discount_rate,
    terminal_growth_rate,
):
    """
    Calculate enterprise value using a basic DCF approach.
    """
    if not free_cash_flows:
         raise ValueError(
            "At least one free cash flow is required."
        )

    if discount_rate <= terminal_growth_rate:
         raise ValueError(
            "Discount rate must be greater than "
            "terminal growth rate."
        )

    present_values = []

    for year, fcf in enumerate(free_cash_flows, start=1):
        discount_factor = (1 + discount_rate) ** year
        present_value = fcf / discount_factor
        present_values.append(present_value)

    terminal_fcf = free_cash_flows[-1]

    terminal_value = (
        terminal_fcf * (1 + terminal_growth_rate)
        / (discount_rate - terminal_growth_rate)
    )

    terminal_present_value = (
        terminal_value
        / (1 + discount_rate) ** len(free_cash_flows)
    )

    enterprise_value = (
        sum(present_values)
        + terminal_present_value
    )

    return DCFValuation(
    present_values=present_values,
    terminal_value=terminal_value,
    terminal_present_value=terminal_present_value,
    enterprise_value=enterprise_value,
    equity_value=enterprise_value,
)


def calculate_equity_value(
    enterprise_value,
    total_debt,
    cash,
):
    """
    Convert enterprise value into equity value.
    """

    equity_value = (
        enterprise_value
        - total_debt
        + cash
    )

    return equity_value
def calculate_share_price(
    equity_value,
    shares_outstanding,
):
    """
    Calculate implied share price.
    """

    if shares_outstanding <= 0:
        raise ValueError(
            "Shares outstanding must be greater than zero."
        )

    return equity_value / shares_outstanding
def dcf_sensitivity(
    free_cash_flows,
    discount_rates,
    terminal_growth_rates,
):
    """
    Calculate enterprise value across different
    discount rate and terminal growth assumptions.
    """

    sensitivity = {}

    for discount_rate in discount_rates:

        sensitivity[discount_rate] = {}

        for growth_rate in terminal_growth_rates:

            result = calculate_dcf_value(
                free_cash_flows=free_cash_flows,
                discount_rate=discount_rate,
                terminal_growth_rate=growth_rate,
            )

            sensitivity[discount_rate][growth_rate] = (
                result.enterprise_value
            )

    return sensitivity
def value_from_free_cash_flows(
    free_cash_flows,
    discount_rate,
    terminal_growth_rate,
):
    """
    Calculate DCF valuation directly from forecast
    free cash flows.
    """

    if not free_cash_flows:
        raise ValueError(
            "At least one free cash flow is required."
        )

    if discount_rate <= terminal_growth_rate:
        raise ValueError(
            "Discount rate must be greater than "
            "terminal growth rate."
        )

    return calculate_dcf_value(
        free_cash_flows=free_cash_flows,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
    )