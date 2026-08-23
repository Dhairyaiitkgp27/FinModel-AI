from core.models.financials import FinancialPeriod

from core.forecasting.assumptions import ForecastAssumptions

from core.forecasting.model_engine import run_financial_model

from core.forecasting.free_cash_flow import calculate_free_cash_flow

from core.forecasting.valuation import value_from_free_cash_flows


def test_end_to_end_financial_model():

    # -----------------------------
    # 1. Historical financials
    # -----------------------------

    historical = FinancialPeriod(
        year=2024,
        revenue=1000,
        cogs=600,
        operating_expenses=200,
        depreciation=50,
        interest_expense=20,
        taxes=30,
        cash=100,
        accounts_receivable=120,
        inventory=150,
        accounts_payable=100,
        capex=60,
        debt=300,
    )

    # -----------------------------
    # 2. Forecast assumptions
    # -----------------------------

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_percent_revenue=0.60,
        operating_expenses_percent_revenue=0.20,
        depreciation_percent_revenue=0.05,
        capex_percent_revenue=0.06,
        tax_rate=0.25,
        accounts_receivable_days=40,
        inventory_days=60,
        accounts_payable_days=45,
    )

    # -----------------------------
    # 3. Run financial model
    # -----------------------------

    model = run_financial_model(
        historical=historical,
        assumptions=assumptions,
        forecast_year=2025,
    )

    assert model is not None

    # -----------------------------
    # 4. Basic model validation
    # -----------------------------

    assert model["balance_sheet"] is not None
    assert model["cash_flow"] is not None
    assert model["income_statement"] is not None

    # -----------------------------
    # 5. Calculate Net Income
    # -----------------------------

        # -----------------------------
    # 5. Calculate Net Income
    # -----------------------------

    income_statement = model["income_statement"]

    ebitda = (
        income_statement.revenue
        - income_statement.cogs
        - income_statement.operating_expenses
    )

    ebit = (
        ebitda
        - income_statement.depreciation
    )

    ebt = (
        ebit
        - income_statement.interest_expense
    )

    net_income = (
        ebt
        - income_statement.taxes
    )

    # -----------------------------
    # 6. Free Cash Flow
    # -----------------------------

    cash_flow = model["cash_flow"]
    balance_sheet = model["balance_sheet"]

    # Capital expenditure comes from the forecast balance sheet
    capex = balance_sheet.capex or 0

    # Calculate change in working capital
    change_in_working_capital = (
        (balance_sheet.accounts_receivable or 0)
        - (historical.accounts_receivable or 0)
        + (balance_sheet.inventory or 0)
        - (historical.inventory or 0)
        - (
            (balance_sheet.accounts_payable or 0)
            - (historical.accounts_payable or 0)
        )
    )

    fcf = calculate_free_cash_flow(
        net_income=net_income,
        depreciation=income_statement.depreciation,
        capex=capex,
        change_in_working_capital=change_in_working_capital,
    )

    assert isinstance(fcf, (int, float))

    # -----------------------------
    # 7. DCF Valuation
    # -----------------------------

    valuation = value_from_free_cash_flows(
        free_cash_flows=[
            fcf,
            fcf * 1.08,
            fcf * 1.08 * 1.08,
        ],
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )

    assert valuation.enterprise_value > 0
    assert valuation.terminal_value > 0