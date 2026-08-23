from core.forecasting.forecast_engine import forecast_series


def test_forecast_series():
    result = forecast_series(
        starting_value=100,
        growth_rates=[0.10, 0.10, 0.10],
    )

    assert result == [110, 121, 133.1]