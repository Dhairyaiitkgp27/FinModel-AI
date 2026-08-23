from core.models.financials import FinancialPeriod
from core.forecasting.assumptions import ForecastAssumptions
from core.forecasting.model_engine import (
    run_financial_model,
    run_complete_financial_model,
)


def test_run_financial_model():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cogs=400,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=80,
        cash=150,
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
        cogs_margin=0.40,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        interest_expense=20,
        tax_rate=0.25,
    )

    result = run_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=2026,
    )

    assert "income_statement" in result
    assert "balance_sheet" in result
    assert "cash_flow" in result
    assert "model_checks" in result

    assert result["income_statement"].year == 2026
    assert result["balance_sheet"].year == 2026

    assert result["income_statement"].revenue == 1100
from core.forecasting.model_engine import run_valuation_model


def test_run_valuation_model():

    financial_model = {
        "income_statement": type(
            "IncomeStatement",
            (),
            {
                "revenue": 1000,
                "cogs": 400,
                "operating_expenses": 200,
                "depreciation": 50,
                "interest_expense": 20,
                "taxes": 80,
            },
        )(),
        "balance_sheet": type(
            "BalanceSheet",
            (),
            {
                "accounts_receivable": 100,
                "inventory": 50,
            },
        )(),
        "cash_flow": {
            "cfi": -70,
        },
    }

    result = run_valuation_model(
        financial_model=financial_model,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )

    assert "free_cash_flow" in result
    assert "valuation" in result

    assert result["free_cash_flow"] > 0
    assert result["valuation"].enterprise_value > 0
from core.forecasting.model_engine import run_equity_valuation


def test_run_equity_valuation():

    result = run_equity_valuation(
        enterprise_value=1000,
        total_debt=300,
        cash=100,
        shares_outstanding=10,
    )

    assert result["equity_value"] == 800
    assert result["share_price"] == 80
from core.forecasting.model_engine import run_multi_year_valuation


def test_run_multi_year_valuation():

    free_cash_flows = [
        80,
        88,
        96.8,
        106.48,
        117.13,
    ]

    result = run_multi_year_valuation(
        free_cash_flows=free_cash_flows,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )

    assert result["free_cash_flows"] == free_cash_flows

    assert len(
        result["valuation"].present_values
    ) == 5

    assert (
        result["valuation"].enterprise_value > 0
    )

    assert (
        result["valuation"].terminal_value > 0
    )
def test_run_complete_financial_model():

    historical = FinancialPeriod(
    year=2025,
    revenue=1000,
    cogs=400,
    operating_expenses=200,
    depreciation=50,
    interest_expense=20,
    taxes=80,
    cash=300,

    accounts_receivable=100,
    inventory=150,
    ppe=400,
    accounts_payable=80,

    debt=500,
    equity=500,
    capex=50,

    total_debt=500,
    total_assets=1200,
    shareholders_equity=500,
      
    )

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.40,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        tax_rate=0.25,
        interest_rate=0.05,
    )

    result = run_complete_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=2026,
    )

    assert result is not None
def run_complete_financial_model(
    historical,
    assumptions,
    forecast_year,
):
    """
    Run the complete financial model for one
    forecast year.
    """

    model = run_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=forecast_year,
    )

    return model
def test_inspect_complete_model_output():

    historical = FinancialPeriod(
        year=2025,
        revenue=1000,
        cogs=400,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=80,
        cash=300,
        accounts_receivable=100,
        inventory=150,
        ppe=400,
        accounts_payable=80,
        debt=500,
        equity=500,
        capex=50,
        total_debt=500,
        total_assets=1200,
        shareholders_equity=500,
    )

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.40,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        tax_rate=0.25,
        interest_rate=0.05,
    )

    result = run_complete_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=2026,
    )

    print("\n\nMODEL OUTPUT TYPE:", type(result))

    if isinstance(result, dict):

     print("\nMODEL OUTPUT STRUCTURE:")

    for key, value in result.items():

        print(f"\n--- {key} ---")
        print("TYPE:", type(value))

        if isinstance(value, dict):
            print("KEYS:", list(value.keys()))

        elif hasattr(value, "__dict__"):
            print("ATTRIBUTES:", list(value.__dict__.keys()))

    assert result is not None