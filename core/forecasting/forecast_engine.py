def forecast_value(
    current_value,
    growth_rate,
):
    """
    Forecast a financial value using a simple growth assumption.
    """

    return round(current_value * (1 + growth_rate), 2)
def forecast_series(
    starting_value,
    growth_rates,
):
    """
    Forecast a value across multiple years.
    """

    forecasts = []
    current_value = starting_value

    for growth_rate in growth_rates:
        current_value = forecast_value(
            current_value=current_value,
            growth_rate=growth_rate,
        )

        forecasts.append(current_value)

    return forecasts
def forecast_financials(
    starting_revenue,
    revenue_growth_rates,
    cogs_margin,
    operating_expense_margin,
    tax_rate,
):
    """
    Forecast basic financial statement items.
    """

    revenues = forecast_series(
        starting_value=starting_revenue,
        growth_rates=revenue_growth_rates,
    )

    forecasts = []

    for revenue in revenues:
        cogs = round(revenue * cogs_margin, 2)
        operating_expenses = round(
            revenue * operating_expense_margin,
            2,
        )

        operating_income = round(
            revenue - cogs - operating_expenses,
            2,
        )

        taxes = round(
            operating_income * tax_rate,
            2,
        )

        net_income = round(
            operating_income - taxes,
            2,
        )

        forecasts.append(
            {
                "revenue": revenue,
                "cogs": cogs,
                "operating_expenses": operating_expenses,
                "operating_income": operating_income,
                "taxes": taxes,
                "net_income": net_income,
            }
        )

    return forecasts