from core.forecasting.forecast_engine import forecast_value


def test_forecast_value():
    result = forecast_value(
        current_value=100,
        growth_rate=0.10,
    )

    assert result == 110