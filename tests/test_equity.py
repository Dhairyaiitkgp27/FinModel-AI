from core.forecasting.equity import roll_forward_equity


def test_equity_roll_forward():

    result = roll_forward_equity(
        beginning_equity=430,
        net_income=75,
        dividends=10,
    )

    assert result["beginning_equity"] == 430
    assert result["net_income"] == 75
    assert result["dividends"] == 10

    assert result["ending_equity"] == 495