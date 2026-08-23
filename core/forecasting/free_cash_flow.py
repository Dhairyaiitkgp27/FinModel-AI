def calculate_free_cash_flow(
    net_income,
    depreciation,
    capex,
    change_in_working_capital,
):
    """
    Calculate Free Cash Flow to the Firm (FCFF)
    using a simplified approach.

    FCFF =
        Net Income
        + Depreciation
        - CapEx
        - Change in Working Capital
    """

    free_cash_flow = (
        net_income
        + depreciation
        - capex
        - change_in_working_capital
    )

    return round(free_cash_flow, 2)
def calculate_free_cash_flow_series(
    net_incomes,
    depreciations,
    capex_values,
    working_capital_changes,
):
    """
    Calculate free cash flow across multiple forecast years.
    """

    lengths = {
        len(net_incomes),
        len(depreciations),
        len(capex_values),
        len(working_capital_changes),
    }

    if len(lengths) != 1:
        raise ValueError(
            "All forecast series must have the same length."
        )

    free_cash_flows = []

    for net_income, depreciation, capex, change_wc in zip(
        net_incomes,
        depreciations,
        capex_values,
        working_capital_changes,
    ):
        free_cash_flow = calculate_free_cash_flow(
            net_income=net_income,
            depreciation=depreciation,
            capex=capex,
            change_in_working_capital=change_wc,
        )

        free_cash_flows.append(free_cash_flow)

    return free_cash_flows