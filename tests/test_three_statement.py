from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions
from core.forecasting.three_statement import build_three_statement_model


def test_three_statement_model():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cogs=600,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=30,
        cash=100,
        accounts_receivable=150,
        inventory=100,
        ppe=500,
        accounts_payable=120,
        debt=300,
        equity=430,
        capex=70,
    )

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.60,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        interest_expense=20,
        tax_rate=0.25,
    )

    model = build_three_statement_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=2026,
    )

    assert model["income_statement"].year == 2026
    assert model["balance_sheet"].year == 2026

    print("Integrated ending cash:", model["cash_flow"]["ending_cash"])
    assert model["cash_flow"]["ending_cash"] == 125.75

    assert model["balance_sheet"].cash == 125.75

    assert "balance_sheet_balances" in model["model_checks"]
    assert "equity_roll_forward" in model

    assert model["equity_roll_forward"]["beginning_equity"] == 430

    assert (
    model["equity_roll_forward"]["ending_equity"]
    == model["balance_sheet"].equity
)