from core.data.csv_loader import load_historical_financials


def test_csv_financial_loader():

    file_path = "data/sample/historical_financials.csv"

    financials = load_historical_financials(
        file_path
    )

    assert len(financials) == 3

    assert financials[0].year == 2023
    assert financials[1].year == 2024
    assert financials[2].year == 2025

    assert financials[2].revenue == 1000
    assert financials[2].cash == 150
    assert financials[2].total_debt == 300