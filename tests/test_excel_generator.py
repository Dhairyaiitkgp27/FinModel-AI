from openpyxl import load_workbook

from core.output.excel_generator import (
    create_financial_model_workbook,
    populate_analysis_sheets,
    populate_forecast_summary,
)


def test_create_financial_model_workbook(tmp_path):

    output_file = (
        tmp_path / "financial_model.xlsx"
    )

    result = create_financial_model_workbook(
        output_path=output_file,
        company_name="Demo Company",
    )

    assert result == output_file

    workbook = load_workbook(output_file)

    expected_sheets = [
        "Cover",
        "Assumptions",
        "Historical Financials",
        "Income Statement",
        "Balance Sheet",
        "Cash Flow",
        "Free Cash Flow",
        "DCF Valuation",
        "Sensitivity",
        "Scenarios",
    ]

    assert workbook.sheetnames == expected_sheets

    assert (
        workbook["Cover"]["A1"].value
        == "Demo Company"
    )

    assert (
        workbook["Cover"]["A2"].value
        == "Automated Financial Model"
    )

    workbook.close()
from openpyxl import Workbook

from core.data.historical_financials import HistoricalFinancials
from core.output.excel_generator import write_historical_financials


def test_write_historical_financials():

    workbook = Workbook()

    # Remove the default worksheet
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Historical Financials")

    financials = [
        HistoricalFinancials(
            year=2023,
            revenue=850,
            cogs=340,
            operating_expenses=170,
            depreciation=42,
            interest_expense=18,
            taxes=70,
            cash=120,
            total_debt=280,
            total_assets=1050,
            shareholders_equity=450,
        ),
        HistoricalFinancials(
            year=2024,
            revenue=920,
            cogs=368,
            operating_expenses=184,
            depreciation=46,
            interest_expense=19,
            taxes=76,
            cash=135,
            total_debt=290,
            total_assets=1120,
            shareholders_equity=470,
        ),
    ]

    sheet = write_historical_financials(
        workbook=workbook,
        financials=financials,
    )

    assert sheet["A1"].value == "Year"
    assert sheet["B1"].value == "Revenue"

    assert sheet["A2"].value == 2023
    assert sheet["B2"].value == 850

    assert sheet["A3"].value == 2024
    assert sheet["B3"].value == 920

    assert sheet["K3"].value == 470
from core.forecasting.assumptions import ForecastAssumptions
from core.output.excel_generator import write_assumptions


def test_write_assumptions():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Assumptions")

    assumptions = ForecastAssumptions(
        revenue_growth=0.10,
        cogs_margin=0.40,
        operating_expense_margin=0.20,
        depreciation_margin=0.05,
        interest_expense=20,
        tax_rate=0.25,
    )

    sheet = write_assumptions(
        workbook=workbook,
        assumptions=assumptions,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )

    assert sheet["A1"].value == "Assumption"
    assert sheet["B1"].value == "Value"

    assert sheet["A2"].value == "Revenue Growth"
    assert sheet["B2"].value == 0.10

    assert sheet["A7"].value == "Tax Rate"
    assert sheet["B7"].value == 0.25

    assert sheet["A8"].value == "Discount Rate / WACC"
    assert sheet["B8"].value == 0.10

    assert sheet["A9"].value == "Terminal Growth Rate"
    assert sheet["B9"].value == 0.03
from core.output.excel_generator import write_income_statement


def test_write_income_statement():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Income Statement")

    financials = [
        HistoricalFinancials(
            year=2023,
            revenue=850,
            cogs=340,
            operating_expenses=170,
            depreciation=42,
            interest_expense=18,
            taxes=70,
            cash=120,
            total_debt=280,
            total_assets=1050,
            shareholders_equity=450,
        ),
        HistoricalFinancials(
            year=2024,
            revenue=920,
            cogs=368,
            operating_expenses=184,
            depreciation=46,
            interest_expense=19,
            taxes=76,
            cash=135,
            total_debt=290,
            total_assets=1120,
            shareholders_equity=470,
        ),
    ]

    sheet = write_income_statement(
        workbook=workbook,
        financials=financials,
    )

    assert sheet["A1"].value == "Income Statement"

    assert sheet["B2"].value == 2023
    assert sheet["C2"].value == 2024

    # 2023
    assert sheet["B3"].value == 850
    assert sheet["B4"].value == 340
    assert sheet["B5"].value == 510
    assert sheet["B6"].value == 170
    assert sheet["B7"].value == 340
    assert sheet["B8"].value == 42
    assert sheet["B9"].value == 298
    assert sheet["B10"].value == 18
    assert sheet["B11"].value == 280
    assert sheet["B12"].value == 70
    assert sheet["B13"].value == 210

    # 2024
    assert sheet["C5"].value == 552
    assert sheet["C7"].value == 368
    assert sheet["C9"].value == 322
    assert sheet["C11"].value == 303
    assert sheet["C13"].value == 227
from core.output.excel_generator import write_balance_sheet


def test_write_balance_sheet():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Balance Sheet")

    financials = [
        HistoricalFinancials(
            year=2023,
            revenue=850,
            cogs=340,
            operating_expenses=170,
            depreciation=42,
            interest_expense=18,
            taxes=70,
            cash=120,
            total_debt=280,
            total_assets=1050,
            shareholders_equity=450,
        ),
        HistoricalFinancials(
            year=2024,
            revenue=920,
            cogs=368,
            operating_expenses=184,
            depreciation=46,
            interest_expense=19,
            taxes=76,
            cash=135,
            total_debt=290,
            total_assets=1120,
            shareholders_equity=470,
        ),
    ]

    sheet = write_balance_sheet(
        workbook=workbook,
        financials=financials,
    )

    assert sheet["A1"].value == "Balance Sheet"

    assert sheet["B2"].value == 2023
    assert sheet["C2"].value == 2024

    assert sheet["B3"].value == 120
    assert sheet["B4"].value == 1050
    assert sheet["B5"].value == 280
    assert sheet["B6"].value == 450

    assert sheet["C3"].value == 135
    assert sheet["C4"].value == 1120
    assert sheet["C5"].value == 290
    assert sheet["C6"].value == 470
from core.output.excel_generator import write_cash_flow


def test_write_cash_flow():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Cash Flow")

    financials = [
        HistoricalFinancials(
            year=2023,
            revenue=850,
            cogs=340,
            operating_expenses=170,
            depreciation=42,
            interest_expense=18,
            taxes=70,
            cash=120,
            total_debt=280,
            total_assets=1050,
            shareholders_equity=450,
        ),
        HistoricalFinancials(
            year=2024,
            revenue=920,
            cogs=368,
            operating_expenses=184,
            depreciation=46,
            interest_expense=19,
            taxes=76,
            cash=135,
            total_debt=290,
            total_assets=1120,
            shareholders_equity=470,
        ),
    ]

    sheet = write_cash_flow(
        workbook=workbook,
        financials=financials,
    )

    assert sheet["A1"].value == "Cash Flow Statement"

    assert sheet["B2"].value == 2023
    assert sheet["C2"].value == 2024

    # 2023:
    # EBITDA = 850 - 340 - 170 = 340
    # EBIT = 340 - 42 = 298
    # EBT = 298 - 18 = 280
    # Net Income = 280 - 70 = 210
    assert sheet["B3"].value == 210
    assert sheet["B4"].value == 42
    assert sheet["B5"].value == 42
    assert sheet["B6"].value == 210

    # 2024:
    # EBITDA = 920 - 368 - 184 = 368
    # EBIT = 368 - 46 = 322
    # EBT = 322 - 19 = 303
    # Net Income = 303 - 76 = 227
    assert sheet["C3"].value == 227
    assert sheet["C4"].value == 46
    assert sheet["C5"].value == 46
    assert sheet["C6"].value == 227
from core.output.excel_generator import write_free_cash_flow


def test_write_free_cash_flow():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Free Cash Flow")

    sheet = write_free_cash_flow(
        workbook=workbook,
        free_cash_flows=[
            80,
            88,
            96.8,
            106.48,
            117.13,
        ],
        forecast_years=[
            2026,
            2027,
            2028,
            2029,
            2030,
        ],
    )

    assert sheet["A1"].value == "Free Cash Flow"

    assert sheet["A2"].value == "Metric"

    assert sheet["B2"].value == 2026
    assert sheet["C2"].value == 2027
    assert sheet["F2"].value == 2030

    assert sheet["A3"].value == "Free Cash Flow"

    assert sheet["B3"].value == 80
    assert sheet["C3"].value == 88
    assert sheet["D3"].value == 96.8
    assert sheet["E3"].value == 106.48
    assert sheet["F3"].value == 117.13
from core.models.valuation import DCFValuation
from core.output.excel_generator import write_dcf_valuation


def test_write_dcf_valuation():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("DCF Valuation")

    valuation = DCFValuation(
        present_values=[
            72.73,
            72.73,
            72.73,
        ],
        terminal_value=1731.43,
        terminal_present_value=1299.72,
        enterprise_value=1518.91,
        total_debt=300,
        cash=150,
        equity_value=1368.91,
        shares_outstanding=10,
        implied_share_price=136.891,
    )

    sheet = write_dcf_valuation(
        workbook=workbook,
        valuation=valuation,
    )

    assert sheet["A1"].value == "DCF Valuation"

    assert sheet["A3"].value == "Enterprise Value"
    assert sheet["B3"].value == 1518.91

    assert sheet["A4"].value == "Terminal Value"
    assert sheet["B4"].value == 1731.43

    assert sheet["A6"].value == "PV of Forecast FCF"
    assert round(sheet["B6"].value, 2) == 218.19

    assert sheet["A10"].value == "Equity Value"
    assert sheet["B10"].value == 1368.91

    assert sheet["A12"].value == "Implied Share Price"
    assert sheet["B12"].value == 136.891
from core.output.excel_generator import (
    populate_analysis_sheets,
)


def test_populate_analysis_sheets():

    from openpyxl import load_workbook

    output_path = "test_model.xlsx"

    create_financial_model_workbook(
        output_path=output_path,
        company_name="Test Company",
    )

    workbook = load_workbook(output_path)

    sensitivity_matrix = [
        {
            "discount_rate": 0.10,
            "values": [
                {
                    "terminal_growth_rate": 0.02,
                    "enterprise_value": 900,
                },
                {
                    "terminal_growth_rate": 0.03,
                    "enterprise_value": 1000,
                },
            ],
        },
    ]

    scenarios = {
        "bear": type(
            "Scenario",
            (),
            {
                "revenue_growth": 0.05,
                "cogs_margin": 0.45,
                "operating_expense_margin": 0.25,
                "depreciation_margin": 0.06,
                "tax_rate": 0.25,
                "terminal_growth_rate": 0.02,
                "discount_rate": 0.12,
            },
        )(),
        "base": type(
            "Scenario",
            (),
            {
                "revenue_growth": 0.10,
                "cogs_margin": 0.40,
                "operating_expense_margin": 0.20,
                "depreciation_margin": 0.05,
                "tax_rate": 0.25,
                "terminal_growth_rate": 0.03,
                "discount_rate": 0.10,
            },
        )(),
        "bull": type(
            "Scenario",
            (),
            {
                "revenue_growth": 0.15,
                "cogs_margin": 0.35,
                "operating_expense_margin": 0.18,
                "depreciation_margin": 0.04,
                "tax_rate": 0.25,
                "terminal_growth_rate": 0.04,
                "discount_rate": 0.08,
            },
        )(),
    }

    populate_analysis_sheets(
        workbook=workbook,
        sensitivity_matrix=sensitivity_matrix,
        scenarios=scenarios,
    )

    sensitivity = workbook["Sensitivity"]
    scenarios_sheet = workbook["Scenarios"]

    assert sensitivity["A1"].value == "DCF Sensitivity Analysis"

    assert sensitivity["B3"].value == 0.02
    assert sensitivity["C3"].value == 0.03

    assert scenarios_sheet["A1"].value == "Scenario Analysis"

    assert scenarios_sheet["B4"].value == 0.05
    assert scenarios_sheet["C4"].value == 0.10
    assert scenarios_sheet["D4"].value == 0.15
def test_populate_forecast_summary():

    from openpyxl import load_workbook

    output_path = "test_forecast_model.xlsx"

    create_financial_model_workbook(
        output_path=output_path,
        company_name="Forecast Test Company",
    )

    workbook = load_workbook(output_path)

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
    ]

    populate_forecast_summary(
        workbook=workbook,
        results=results,
    )

    sheet = workbook["Forecast Summary"]

    assert sheet["A1"].value == "Multi-Year Forecast"

    assert sheet["A3"].value == "Forecast Year"
    assert sheet["B3"].value == "Revenue"

    assert sheet["A4"].value == 2026
    assert sheet["B4"].value == 1100

    assert sheet["A5"].value == 2027
    assert sheet["E5"].value == 220