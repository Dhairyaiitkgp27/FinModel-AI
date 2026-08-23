import pytest

from core.analysis.financial_analysis import (
    calculate_profitability_ratios,
    calculate_leverage_ratios,
    calculate_liquidity_ratios,
    calculate_efficiency_ratios,
    calculate_growth_metrics,
    calculate_margin_change,
    calculate_cagr,
)


def test_profitability_ratios():

    ratios = calculate_profitability_ratios(
        revenue=1000,
        cogs=400,
        operating_expenses=200,
        depreciation=50,
        net_income=250,
    )

    assert ratios["gross_margin"] == pytest.approx(0.60)
    assert ratios["ebitda_margin"] == pytest.approx(0.40)
    assert ratios["ebit_margin"] == pytest.approx(0.35)
    assert ratios["net_margin"] == pytest.approx(0.25)


def test_profitability_zero_revenue():

    with pytest.raises(ValueError):
        calculate_profitability_ratios(
            revenue=0,
            cogs=400,
            operating_expenses=200,
            depreciation=50,
            net_income=250,
        )


def test_leverage_ratios():

    ratios = calculate_leverage_ratios(
        total_debt=500,
        cash=100,
        ebitda=200,
        interest_expense=50,
    )

    assert ratios["net_debt"] == 400
    assert ratios["debt_to_ebitda"] == pytest.approx(2.5)
    assert ratios["net_debt_to_ebitda"] == pytest.approx(2.0)
    assert ratios["interest_coverage"] == pytest.approx(4.0)


def test_leverage_zero_ebitda():

    ratios = calculate_leverage_ratios(
        total_debt=500,
        cash=100,
        ebitda=0,
        interest_expense=50,
    )

    assert ratios["debt_to_ebitda"] == float("inf")
    assert ratios["net_debt_to_ebitda"] == float("inf")


def test_liquidity_ratios():

    ratios = calculate_liquidity_ratios(
        cash=300,
        accounts_receivable=100,
        inventory=150,
        current_liabilities=200,
    )

    assert ratios["current_ratio"] == pytest.approx(2.75)
    assert ratios["quick_ratio"] == pytest.approx(2.0)


def test_liquidity_zero_liabilities():

    with pytest.raises(ValueError):
        calculate_liquidity_ratios(
            cash=300,
            accounts_receivable=100,
            inventory=150,
            current_liabilities=0,
        )


def test_efficiency_ratios():

    ratios = calculate_efficiency_ratios(
        revenue=1000,
        accounts_receivable=100,
        inventory=200,
        cogs=400,
    )

    assert ratios["receivables_turnover"] == pytest.approx(10.0)
    assert ratios["inventory_turnover"] == pytest.approx(2.0)


def test_efficiency_zero_balances():

    ratios = calculate_efficiency_ratios(
        revenue=1000,
        accounts_receivable=0,
        inventory=0,
        cogs=400,
    )

    assert ratios["receivables_turnover"] == float("inf")
    assert ratios["inventory_turnover"] == float("inf")
def test_growth_metrics():

    metrics = calculate_growth_metrics(
        current_revenue=1200,
        previous_revenue=1000,
        current_ebitda=360,
        previous_ebitda=300,
        current_ebit=300,
        previous_ebit=250,
        current_net_income=180,
        previous_net_income=150,
    )

    assert metrics["revenue_growth"] == pytest.approx(0.20)
    assert metrics["ebitda_growth"] == pytest.approx(0.20)
    assert metrics["ebit_growth"] == pytest.approx(0.20)
    assert metrics["net_income_growth"] == pytest.approx(0.20)


def test_growth_from_zero():

    metrics = calculate_growth_metrics(
        current_revenue=100,
        previous_revenue=0,
        current_ebitda=50,
        previous_ebitda=0,
        current_ebit=40,
        previous_ebit=0,
        current_net_income=20,
        previous_net_income=0,
    )

    assert metrics["revenue_growth"] == float("inf")
    assert metrics["ebitda_growth"] == float("inf")


def test_margin_change():

    metrics = calculate_margin_change(
        current_revenue=1200,
        previous_revenue=1000,
        current_ebitda=360,
        previous_ebitda=300,
        current_ebit=300,
        previous_ebit=250,
    )

    assert metrics["ebitda_margin_change"] == pytest.approx(0)
    assert metrics["ebit_margin_change"] == pytest.approx(0)


def test_margin_expansion():

    metrics = calculate_margin_change(
        current_revenue=1200,
        previous_revenue=1000,
        current_ebitda=420,
        previous_ebitda=300,
        current_ebit=330,
        previous_ebit=250,
    )

    assert metrics["ebitda_margin_change"] == pytest.approx(0.05)
    assert metrics["ebit_margin_change"] == pytest.approx(0.025)


def test_margin_zero_revenue():

    with pytest.raises(ValueError):

     calculate_margin_change(
            current_revenue=0,
            previous_revenue=1000,
            current_ebitda=300,
            previous_ebitda=250,
            current_ebit=200,
            previous_ebit=180,
        )


def test_cagr():

    cagr = calculate_cagr(
        beginning_value=100,
        ending_value=121,
        years=2,
    )

    assert cagr == pytest.approx(0.10)


def test_cagr_invalid_years():

    with pytest.raises(ValueError):

        calculate_cagr(
            beginning_value=100,
            ending_value=121,
            years=0,
        )


def test_cagr_invalid_beginning_value():

    with pytest.raises(ValueError):

        calculate_cagr(
            beginning_value=0,
            ending_value=121,
            years=2,
        )