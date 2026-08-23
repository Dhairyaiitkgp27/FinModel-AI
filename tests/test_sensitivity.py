from core.forecasting.sensitivity import build_sensitivity_matrix


def test_build_sensitivity_matrix():

    matrix = build_sensitivity_matrix(
        free_cash_flows=[
            80,
            88,
            96.8,
            106.48,
            117.13,
        ],
        discount_rates=[0.08, 0.10, 0.12],
        terminal_growth_rates=[0.02, 0.03, 0.04],
    )

    assert len(matrix) == 3

    assert matrix[0]["discount_rate"] == 0.08
    assert matrix[1]["discount_rate"] == 0.10
    assert matrix[2]["discount_rate"] == 0.12

    assert len(matrix[0]["values"]) == 3

    assert (
        matrix[0]["values"][0]["terminal_growth_rate"]
        == 0.02
    )

    assert (
        matrix[1]["values"][1]["enterprise_value"]
        > 0
    )

    # Higher growth should increase valuation
    assert (
        matrix[1]["values"][2]["enterprise_value"]
        > matrix[1]["values"][0]["enterprise_value"]
    )

    # Higher discount rate should decrease valuation
    assert (
        matrix[2]["values"][1]["enterprise_value"]
        < matrix[0]["values"][1]["enterprise_value"]
    )
from openpyxl import Workbook

from core.output.sensitivity_writer import (
    write_sensitivity_matrix,
)


def test_write_sensitivity_matrix():

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    workbook.create_sheet("Sensitivity")

    matrix = [
        {
            "discount_rate": 0.08,
            "values": [
                {
                    "terminal_growth_rate": 0.02,
                    "enterprise_value": 1000,
                },
                {
                    "terminal_growth_rate": 0.03,
                    "enterprise_value": 1100,
                },
                {
                    "terminal_growth_rate": 0.04,
                    "enterprise_value": 1250,
                },
            ],
        },
        {
            "discount_rate": 0.10,
            "values": [
                {
                    "terminal_growth_rate": 0.02,
                    "enterprise_value": 850,
                },
                {
                    "terminal_growth_rate": 0.03,
                    "enterprise_value": 950,
                },
                {
                    "terminal_growth_rate": 0.04,
                    "enterprise_value": 1050,
                },
            ],
        },
        {
            "discount_rate": 0.12,
            "values": [
                {
                    "terminal_growth_rate": 0.02,
                    "enterprise_value": 750,
                },
                {
                    "terminal_growth_rate": 0.03,
                    "enterprise_value": 820,
                },
                {
                    "terminal_growth_rate": 0.04,
                    "enterprise_value": 900,
                },
            ],
        },
    ]

    sheet = write_sensitivity_matrix(
        workbook=workbook,
        matrix=matrix,
    )

    assert sheet["A1"].value == "DCF Sensitivity Analysis"

    assert sheet["A3"].value == "WACC / Terminal Growth"

    assert sheet["B3"].value == 0.02
    assert sheet["C3"].value == 0.03
    assert sheet["D3"].value == 0.04

    assert sheet["A4"].value == 0.08
    assert sheet["A5"].value == 0.10
    assert sheet["A6"].value == 0.12

    assert sheet["B4"].value == 1000
    assert sheet["C5"].value == 950
    assert sheet["D6"].value == 900