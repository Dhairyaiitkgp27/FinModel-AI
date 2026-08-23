from core.forecasting.forecast_engine import forecast_financials


def test_forecast_financials():
    result = forecast_financials(
        starting_revenue=1000,
        revenue_growth_rates=[0.10, 0.10],
        cogs_margin=0.40,
        operating_expense_margin=0.20,
        tax_rate=0.25,
    )

    assert len(result) == 2

    # Year 1
    assert result[0]["revenue"] == 1100
    assert result[0]["cogs"] == 440
    assert result[0]["operating_expenses"] == 220
    assert result[0]["operating_income"] == 440
    assert result[0]["taxes"] == 110
    assert result[0]["net_income"] == 330

    # Year 2
    assert result[1]["revenue"] == 1210
    assert result[1]["cogs"] == 484
    assert result[1]["operating_expenses"] == 242
    assert result[1]["operating_income"] == 484
    assert result[1]["taxes"] == 121
    assert result[1]["net_income"] == 363
from openpyxl import Workbook

from core.output.forecast_writer import (
    write_forecast_summary,
)


def test_write_forecast_summary():

    workbook = Workbook()

    workbook.active.title = "Cover"

    results = [
        {
            "year": 2026,
            "revenue": 1100,
            "ebitda": 330,
            "ebit": 275,
            "free_cash_flow": 200,
        },
        {
            "year": 2027,
            "revenue": 1210,
            "ebitda": 363,
            "ebit": 303,
            "free_cash_flow": 220,
        },
        {
            "year": 2028,
            "revenue": 1331,
            "ebitda": 399.3,
            "ebit": 333.3,
            "free_cash_flow": 242,
        },
    ]

    sheet = write_forecast_summary(
        workbook=workbook,
        results=results,
    )

    assert sheet["A1"].value == "Multi-Year Forecast"

    assert sheet["A3"].value == "Forecast Year"
    assert sheet["B3"].value == "Revenue"
    assert sheet["C3"].value == "EBITDA"
    assert sheet["D3"].value == "EBIT"
    assert sheet["E3"].value == "Free Cash Flow"

    assert sheet["A4"].value == 2026
    assert sheet["B4"].value == 1100
    assert sheet["C4"].value == 330

    assert sheet["A5"].value == 2027
    assert sheet["B5"].value == 1210

    assert sheet["A6"].value == 2028
    assert sheet["E6"].value == 242
from openpyxl import Workbook

from core.output.forecast_writer import (
    write_model_forecast_summary,
)


def test_write_model_forecast_summary():

    workbook = Workbook()

    workbook.active.title = "Cover"

    income_statement = type(
        "FinancialPeriod",
        (),
        {
            "year": 2026,
            "revenue": 1100,
            "cogs": 440,
            "operating_expenses": 220,
            "depreciation": 55,
        },
    )()

    results = [
        {
            "income_statement": income_statement,
            "cash_flow": {
                "cfo": 200,
                "cfi": -50,
                "cff": 0,
                "net_change_in_cash": 150,
                "ending_cash": 450,
            },
        }
    ]

    sheet = write_model_forecast_summary(
        workbook=workbook,
        results=results,
    )

    assert sheet["A1"].value == (
        "Multi-Year Financial Forecast"
    )

    assert sheet["A3"].value == "Forecast Year"
    assert sheet["B3"].value == "Revenue"
    assert sheet["E3"].value == "EBITDA"
    assert sheet["H3"].value == "CFO"

    assert sheet["A4"].value == 2026
    assert sheet["B4"].value == 1100

    # EBITDA = Revenue - COGS - Operating Expenses
    assert sheet["E4"].value == 440

    # EBIT = EBITDA - Depreciation
    assert sheet["G4"].value == 385

    assert sheet["H4"].value == 200
    assert sheet["I4"].value == -50
    assert sheet["J4"].value == 0
    assert sheet["K4"].value == 150
    assert sheet["L4"].value == 450