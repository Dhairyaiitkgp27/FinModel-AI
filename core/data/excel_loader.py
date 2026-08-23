import pandas as pd

from core.data.historical_financials import HistoricalFinancials


def load_historical_financials_from_excel(
    file_path: str,
) -> list[HistoricalFinancials]:
    """
    Load historical financial data from an Excel file.
    """

    dataframe = pd.read_excel(file_path)

    required_columns = {
        "year",
        "revenue",
        "cogs",
        "operating_expenses",
        "depreciation",
        "interest_expense",
        "taxes",
        "cash",
        "total_debt",
        "total_assets",
        "shareholders_equity",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    financials = []

    for _, row in dataframe.iterrows():

        financial_period = HistoricalFinancials(
            year=int(row["year"]),
            revenue=float(row["revenue"]),
            cogs=float(row["cogs"]),
            operating_expenses=float(
                row["operating_expenses"]
            ),
            depreciation=float(row["depreciation"]),
            interest_expense=float(
                row["interest_expense"]
            ),
            taxes=float(row["taxes"]),
            cash=float(row["cash"]),
            total_debt=float(row["total_debt"]),
            total_assets=float(row["total_assets"]),
            shareholders_equity=float(
                row["shareholders_equity"]
            ),
        )

        financials.append(financial_period)

    return financials