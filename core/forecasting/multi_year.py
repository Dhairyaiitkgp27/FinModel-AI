from typing import List

from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions
from core.forecasting.income_statement import forecast_income_statement
from core.forecasting.model_engine import (
    run_complete_financial_model,
)


def forecast_multiple_years(
    historical: FinancialPeriod,
    assumptions: ForecastAssumptions,
    forecast_years: List[int],
) -> List[FinancialPeriod]:
    """
    Generate a multi-year income statement forecast.

    Each year's revenue becomes the base for the following year.
    """

    forecasts = []

    previous_period = historical

    for year in forecast_years:

        forecast = forecast_income_statement(
            historical=previous_period,
            assumptions=assumptions,
            forecast_year=year,
        )

        forecasts.append(forecast)

        # The current forecast becomes the base
        # for the following year.
        previous_period = forecast

    return forecasts
def run_multi_year_financial_model(
    historical,
    assumptions,
    forecast_years,
):
    """
    Run the financial model across multiple
    forecast years.
    """

    results = []

    current_historical = historical

    for forecast_year in forecast_years:
        result = run_complete_financial_model(
            historical=current_historical,
            assumptions=assumptions,
            forecast_year=forecast_year,
        )

        results.append(result)

        if isinstance(result, dict):
         current_historical = result[
        "balance_sheet"
    ]

    return results