def write_scenario_analysis(
    workbook,
    scenarios,
):
    """
    Write scenario assumptions into the
    Scenario Analysis worksheet.
    """

    if "Scenarios" in workbook.sheetnames:
     sheet = workbook["Scenarios"]
    else:
     sheet = workbook["Scenario Analysis"]

    sheet["A1"] = "Scenario Analysis"

    headers = [
        "Assumption",
        "Bear",
        "Base",
        "Bull",
    ]

    for column, header in enumerate(
        headers,
        start=1,
    ):
        sheet.cell(
            row=3,
            column=column,
            value=header,
        )

    assumptions = [
        "Revenue Growth",
        "COGS Margin",
        "Operating Expense Margin",
        "Depreciation Margin",
        "Tax Rate",
        "Terminal Growth Rate",
        "Discount Rate",
    ]

    for row, assumption in enumerate(
        assumptions,
        start=4,
    ):
        sheet.cell(
            row=row,
            column=1,
            value=assumption,
        )

    for column, scenario_name in enumerate(
        ["bear", "base", "bull"],
        start=2,
    ):
        scenario = scenarios[scenario_name]

        values = [
            scenario.revenue_growth,
            scenario.cogs_margin,
            scenario.operating_expense_margin,
            scenario.depreciation_margin,
            scenario.tax_rate,
            scenario.terminal_growth_rate,
            scenario.discount_rate,
        ]

        for row, value in enumerate(
            values,
            start=4,
        ):
            sheet.cell(
                row=row,
                column=column,
                value=value,
            )

    return sheet