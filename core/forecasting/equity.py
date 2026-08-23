def roll_forward_equity(
    beginning_equity,
    net_income,
    dividends,
):
    """
    Roll forward shareholders' equity.

    Ending Equity =
        Beginning Equity
        + Net Income
        - Dividends
    """

    beginning_equity = beginning_equity or 0.0
    net_income = net_income or 0.0
    dividends = dividends or 0.0

    ending_equity = (
        beginning_equity
        + net_income
        - dividends
    )

    return {
        "beginning_equity": beginning_equity,
        "net_income": net_income,
        "dividends": dividends,
        "ending_equity": ending_equity,
    }