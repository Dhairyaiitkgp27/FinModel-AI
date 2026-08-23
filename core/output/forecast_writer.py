def write_forecast_summary(
    workbook,
    results,
):
    """
    Write multi-year forecast results into
    the Forecast Summary worksheet.
    """

    if "Forecast Summary" in workbook.sheetnames:
        sheet = workbook["Forecast Summary"]
    else:
        sheet = workbook.create_sheet("Forecast Summary")

    sheet["A1"] = "Multi-Year Forecast"

    sheet["A3"] = "Forecast Year"
    sheet["B3"] = "Revenue"
    sheet["C3"] = "EBITDA"
    sheet["D3"] = "EBIT"
    sheet["E3"] = "Free Cash Flow"

    for row, result in enumerate(results, start=4):

        sheet.cell(
            row=row,
            column=1,
            value=result["year"],
        )

        sheet.cell(
            row=row,
            column=2,
            value=result["revenue"],
        )

        sheet.cell(
            row=row,
            column=3,
            value=result["ebitda"],
        )

        sheet.cell(
            row=row,
            column=4,
            value=result["ebit"],
        )

        sheet.cell(
            row=row,
            column=5,
            value=result["free_cash_flow"],
        )

    return sheet
def write_model_forecast_summary(
    workbook,
    results,
):
    """
    Write actual multi-year financial model results
    into the Forecast Summary worksheet.
    """

    if "Forecast Summary" in workbook.sheetnames:
        sheet = workbook["Forecast Summary"]
    else:
        sheet = workbook.create_sheet("Forecast Summary")

    sheet["A1"] = "Multi-Year Financial Forecast"

    headers = [
        "Forecast Year",
        "Revenue",
        "COGS",
        "Operating Expenses",
        "EBITDA",
        "Depreciation",
        "EBIT",
        "CFO",
        "CFI",
        "CFF",
        "Net Change in Cash",
        "Ending Cash",
    ]

    for column, header in enumerate(headers, start=1):
        sheet.cell(
            row=3,
            column=column,
            value=header,
        )

    for row, result in enumerate(results, start=4):

        income_statement = result[
            "income_statement"
        ]

        cash_flow = result[
            "cash_flow"
        ]

        revenue = income_statement.revenue
        cogs = income_statement.cogs
        operating_expenses = (
            income_statement.operating_expenses
        )
        depreciation = income_statement.depreciation

        ebitda = (
            revenue
            - cogs
            - operating_expenses
        )

        ebit = ebitda - depreciation

        values = [
            income_statement.year,
            revenue,
            cogs,
            operating_expenses,
            ebitda,
            depreciation,
            ebit,
            cash_flow["cfo"],
            cash_flow["cfi"],
            cash_flow["cff"],
            cash_flow["net_change_in_cash"],
            cash_flow["ending_cash"],
        ]

        for column, value in enumerate(
            values,
            start=1,
        ):
            sheet.cell(
                row=row,
                column=column,
                value=value,
            )

    return sheet