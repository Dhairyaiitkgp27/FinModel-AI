from core.forecasting.model_engine import run_multi_year_valuation


def run_scenario(
    name,
    free_cash_flows,
    discount_rate,
    terminal_growth_rate,
):
    """
    Run a single valuation scenario.
    """

    result = run_multi_year_valuation(
        free_cash_flows=free_cash_flows,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
    )

    return {
        "name": name,
        "discount_rate": discount_rate,
        "terminal_growth_rate": terminal_growth_rate,
        "free_cash_flows": free_cash_flows,
        "enterprise_value": (
            result["valuation"].enterprise_value
        ),
    }
def run_scenario_set(
    scenarios,
):
    """
    Run multiple valuation scenarios.

    scenarios should be a list of dictionaries
    containing:
        name
        free_cash_flows
        discount_rate
        terminal_growth_rate
    """

    results = []

    for scenario in scenarios:

        result = run_scenario(
            name=scenario["name"],
            free_cash_flows=scenario["free_cash_flows"],
            discount_rate=scenario["discount_rate"],
            terminal_growth_rate=scenario[
                "terminal_growth_rate"
            ],
        )

        results.append(result)

    return results