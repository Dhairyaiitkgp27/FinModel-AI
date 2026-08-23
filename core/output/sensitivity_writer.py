def write_sensitivity_matrix(
    workbook,
    matrix,
):
    """
    Write a DCF sensitivity matrix into the
    Sensitivity worksheet.
    """

    sheet = workbook["Sensitivity"]

    sheet["A1"] = "DCF Sensitivity Analysis"

    sheet["A3"] = "WACC / Terminal Growth"

    if not matrix:
        return sheet

    growth_rates = [
        item["terminal_growth_rate"]
        for item in matrix[0]["values"]
    ]

    for column, growth_rate in enumerate(
        growth_rates,
        start=2,
    ):
        sheet.cell(
            row=3,
            column=column,
            value=growth_rate,
        )

    for row, sensitivity_row in enumerate(
        matrix,
        start=4,
    ):
        discount_rate = sensitivity_row[
            "discount_rate"
        ]

        sheet.cell(
            row=row,
            column=1,
            value=discount_rate,
        )

        for column, value_data in enumerate(
            sensitivity_row["values"],
            start=2,
        ):
            sheet.cell(
                row=row,
                column=column,
                value=round(
                    value_data["enterprise_value"],
                    2,
                ),
            )

    return sheet