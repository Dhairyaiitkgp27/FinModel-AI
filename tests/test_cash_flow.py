from core.models.financials import FinancialPeriod
from core.forecasting.cash_flow import forecast_cash_flow


def test_cash_flow_forecast():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cash=100,
        accounts_receivable=150,
        inventory=100,
        ppe=500,
        accounts_payable=120,
        debt=300,
        equity=430,
        capex=70,
        depreciation=50,
    )

    forecast = FinancialPeriod(
        year=2026,
        revenue=1100,
        cash=100,
        accounts_receivable=165,
        inventory=110,
        ppe=520,
        accounts_payable=132,
        debt=300,
        equity=430,
        capex=70,
        depreciation=55,
    )

    result = forecast_cash_flow(
        historical=historical,
        forecast=forecast,
        net_income=50,
    )

    assert result["cfo"] == 92
    assert result["cfi"] == -70
    assert result["cff"] == 0
    assert result["net_change_in_cash"] == 22
    assert result["ending_cash"] == 122