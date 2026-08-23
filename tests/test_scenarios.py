from core.forecasting.scenarios import run_scenario


def test_run_scenario():

    result = run_scenario(
        name="Base Case",
        free_cash_flows=[
            80,
            88,
            96.8,
            106.48,
            117.13,
        ],
        discount_rate=0.10,
        terminal_growth_rate=0.03,
    )

    assert result["name"] == "Base Case"

    assert result["discount_rate"] == 0.10

    assert result["terminal_growth_rate"] == 0.03

    assert len(result["free_cash_flows"]) == 5

    assert result["enterprise_value"] > 0
from core.forecasting.scenarios import run_scenario_set


def test_run_scenario_set():

    scenarios = [
        {
            "name": "Bear Case",
            "free_cash_flows": [70, 75, 80, 85, 90],
            "discount_rate": 0.12,
            "terminal_growth_rate": 0.02,
        },
        {
            "name": "Base Case",
            "free_cash_flows": [80, 88, 96.8, 106.48, 117.13],
            "discount_rate": 0.10,
            "terminal_growth_rate": 0.03,
        },
        {
            "name": "Bull Case",
            "free_cash_flows": [90, 101, 113.12, 126.69, 141.89],
            "discount_rate": 0.09,
            "terminal_growth_rate": 0.04,
        },
    ]

    results = run_scenario_set(scenarios)

    assert len(results) == 3

    assert results[0]["name"] == "Bear Case"
    assert results[1]["name"] == "Base Case"
    assert results[2]["name"] == "Bull Case"

    assert results[0]["enterprise_value"] > 0
    assert results[1]["enterprise_value"] > 0
    assert results[2]["enterprise_value"] > 0

    assert (
        results[2]["enterprise_value"]
        > results[1]["enterprise_value"]
        > results[0]["enterprise_value"]
    )
from openpyxl import Workbook

from core.output.scenario_writer import (
    write_scenario_analysis,
)


def test_write_scenario_analysis():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Scenario Analysis")

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

    sheet = write_scenario_analysis(
        workbook=workbook,
        scenarios=scenarios,
    )

    assert sheet["A1"].value == "Scenario Analysis"

    assert sheet["A3"].value == "Assumption"
    assert sheet["B3"].value == "Bear"
    assert sheet["C3"].value == "Base"
    assert sheet["D3"].value == "Bull"

    assert sheet["A4"].value == "Revenue Growth"

    assert sheet["B4"].value == 0.05
    assert sheet["C4"].value == 0.10
    assert sheet["D4"].value == 0.15

    assert sheet["B5"].value == 0.45
    assert sheet["C5"].value == 0.40
    assert sheet["D5"].value == 0.35

    assert sheet["B9"].value == 0.02
    assert sheet["C9"].value == 0.03
    assert sheet["D9"].value == 0.04

    assert sheet["B10"].value == 0.12
    assert sheet["C10"].value == 0.10
    assert sheet["D10"].value == 0.08