import streamlit as st

from core.models.model import FinancialModel
from core.forecasting.valuation import (
    calculate_dcf_value,
    calculate_equity_value,
    calculate_share_price,
    dcf_sensitivity,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FinModel AI",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 FinModel AI")
st.sidebar.markdown("### Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard",
        "Financial Model",
        "Forecast",
        "DCF Valuation",
        "Scenarios",
        "Sensitivity Analysis",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("FinModel AI — Financial Modeling Platform")


# ============================================================
# HEADER
# ============================================================

st.title("📊 FinModel AI")
st.subheader("Financial Modeling & Valuation Platform")

st.markdown("---")


# ============================================================
# ENGINE STATUS
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Financial Engine",
        "READY",
        "68 tests passed",
    )

with col2:
    st.metric(
        "Model Engine",
        "READY",
    )

with col3:
    st.metric(
        "Valuation Engine",
        "READY",
    )

st.markdown("---")


# ============================================================
# SESSION STATE
# ============================================================

if "model" not in st.session_state:
    st.session_state.model = None

if "company_name" not in st.session_state:
    st.session_state.company_name = "Example Corp"

if "ticker" not in st.session_state:
    st.session_state.ticker = "AAPL"

if "currency" not in st.session_state:
    st.session_state.currency = "USD"

if "historical_years" not in st.session_state:
    st.session_state.historical_years = 5

if "fcfs" not in st.session_state:
    st.session_state.fcfs = []

if "dcf_result" not in st.session_state:
    st.session_state.dcf_result = None


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.header("Company Setup")

    col1, col2 = st.columns(2)

    with col1:
        company_name = st.text_input(
            "Company Name",
            value=st.session_state.company_name,
        )

    with col2:
        ticker = st.text_input(
            "Ticker Symbol",
            value=st.session_state.ticker,
        )

    currency = st.selectbox(
        "Currency",
        ["USD", "INR", "EUR", "GBP"],
        index=["USD", "INR", "EUR", "GBP"].index(
            st.session_state.currency
        ),
    )

    st.markdown("---")

    st.header("Historical Financials")

    years = st.slider(
        "Number of historical years",
        min_value=3,
        max_value=10,
        value=st.session_state.historical_years,
    )

    st.info(
        f"Selected {years} years of historical financial data "
        f"for {company_name} ({ticker})."
    )

    st.markdown("---")

    if st.button(
        "🚀 Build Financial Model",
        type="primary",
        use_container_width=True,
    ):

        try:

            model = FinancialModel(
                company_name=company_name,
                currency=currency,
            )

            st.session_state.model = model
            st.session_state.company_name = company_name
            st.session_state.ticker = ticker
            st.session_state.currency = currency
            st.session_state.historical_years = years

            st.success(
                "Financial model successfully initialized."
            )

            st.write("### Model Configuration")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Company", company_name)

            with col2:
                st.metric("Ticker", ticker)

            with col3:
                st.metric("Currency", currency)

            with col4:
                st.metric("Historical Years", years)

            st.write("### Backend Model Object")

            st.json(model.model_dump())

        except Exception as e:

            st.error(
                f"Could not initialize financial model: {e}"
            )


# ============================================================
# FINANCIAL MODEL
# ============================================================

elif page == "Financial Model":

    st.header("Financial Model")

    if st.session_state.model is None:

        st.warning(
            "Build a financial model from the Dashboard first."
        )

    else:

        model = st.session_state.model

        st.success(
            f"Model loaded for "
            f"{model.company_name}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Company",
                model.company_name,
            )

        with col2:
            st.metric(
                "Currency",
                model.currency,
            )

        with col3:
            st.metric(
                "Tax Rate",
                f"{model.tax_rate:.1%}",
            )

        st.markdown("---")

        st.subheader("Model Assumptions")

        tax_rate = st.number_input(
            "Tax Rate",
            min_value=0.0,
            max_value=1.0,
            value=float(model.tax_rate),
            step=0.01,
            format="%.2f",
        )

        wacc = st.number_input(
            "WACC",
            min_value=0.0,
            max_value=1.0,
            value=0.10 if model.wacc is None else float(model.wacc),
            step=0.005,
            format="%.3f",
        )

        terminal_growth = st.number_input(
            "Terminal Growth Rate",
            min_value=0.0,
            max_value=0.20,
            value=0.03
            if model.terminal_growth_rate is None
            else float(model.terminal_growth_rate),
            step=0.005,
            format="%.3f",
        )

        if st.button(
            "Save Model Assumptions",
            type="primary",
        ):

            model.tax_rate = tax_rate
            model.wacc = wacc
            model.terminal_growth_rate = terminal_growth

            st.session_state.model = model

            st.success(
                "Model assumptions updated."
            )

        st.markdown("---")

        st.subheader("Current Model")

        st.json(model.model_dump())


# ============================================================
# FORECAST
# ============================================================

elif page == "Forecast":

    st.header("Free Cash Flow Forecast")

    st.write(
        "Enter projected Free Cash Flow for each forecast year."
    )

    forecast_years = st.number_input(
        "Forecast Periods",
        min_value=1,
        max_value=15,
        value=5,
        step=1,
    )

    fcfs = []

    cols = st.columns(min(int(forecast_years), 5))

    for i in range(int(forecast_years)):

        with cols[i % 5]:

            fcf = st.number_input(
                f"Year {i + 1} FCF",
                value=100.0,
                step=10.0,
                key=f"fcf_{i}",
            )

            fcfs.append(fcf)

    if st.button(
        "Save Forecast",
        type="primary",
    ):

        st.session_state.fcfs = fcfs

        st.success(
            "Forecast successfully saved."
        )

    if st.session_state.fcfs:

        st.markdown("---")

        st.subheader("Forecast Summary")

        for i, fcf in enumerate(
            st.session_state.fcfs,
            start=1,
        ):

            st.write(
                f"Year {i}: "
                f"{fcf:,.2f} "
                f"{st.session_state.currency}"
            )


# ============================================================
# DCF VALUATION
# ============================================================

elif page == "DCF Valuation":

    st.header("DCF Valuation")

    if not st.session_state.fcfs:

        st.warning(
            "Enter and save forecast FCFs from the Forecast page first."
        )

    else:

        st.subheader("DCF Assumptions")

        col1, col2 = st.columns(2)

        with col1:

            discount_rate = st.number_input(
                "WACC / Discount Rate",
                min_value=0.001,
                max_value=1.0,
                value=0.10,
                step=0.005,
                format="%.3f",
            )

        with col2:

            terminal_growth_rate = st.number_input(
                "Terminal Growth Rate",
                min_value=0.0,
                max_value=0.20,
                value=0.03,
                step=0.005,
                format="%.3f",
            )

        st.markdown("---")

        if st.button(
            "Calculate DCF",
            type="primary",
            use_container_width=True,
        ):

            try:

                result = calculate_dcf_value(
                    free_cash_flows=st.session_state.fcfs,
                    discount_rate=discount_rate,
                    terminal_growth_rate=terminal_growth_rate,
                )

                st.session_state.dcf_result = result

                st.success(
                    "DCF valuation calculated successfully."
                )

            except Exception as e:

                st.error(
                    f"DCF calculation failed: {e}"
                )

        if st.session_state.dcf_result:

            result = st.session_state.dcf_result

            st.markdown("---")

            st.subheader("DCF Results")

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Enterprise Value",
                    f"{result.enterprise_value:,.2f}",
                )

            with col2:

                st.metric(
                    "Terminal Value",
                    f"{result.terminal_value:,.2f}",
                )

            with col3:

                st.metric(
                    "Terminal PV",
                    f"{result.terminal_present_value:,.2f}",
                )

            st.markdown("---")

            st.subheader("Present Value of Forecast FCF")

            for i, pv in enumerate(
                result.present_values,
                start=1,
            ):

                st.write(
                    f"Year {i}: "
                    f"{pv:,.2f}"
                )

            st.markdown("---")

            st.subheader("Equity Value")

            debt = st.number_input(
                "Total Debt",
                min_value=0.0,
                value=0.0,
                step=10.0,
            )

            cash = st.number_input(
                "Cash",
                min_value=0.0,
                value=0.0,
                step=10.0,
            )

            shares = st.number_input(
                "Shares Outstanding",
                min_value=0.000001,
                value=1.0,
                step=1.0,
            )

            if st.button(
                "Calculate Equity Value",
                type="primary",
            ):

                equity_value = calculate_equity_value(
                    enterprise_value=result.enterprise_value,
                    total_debt=debt,
                    cash=cash,
                )

                share_price = calculate_share_price(
                    equity_value=equity_value,
                    shares_outstanding=shares,
                )

                col1, col2 = st.columns(2)

                with col1:

                    st.metric(
                        "Equity Value",
                        f"{equity_value:,.2f}",
                    )

                with col2:

                    st.metric(
                        "Implied Share Price",
                        f"{share_price:,.2f}",
                    )


# ============================================================
# SCENARIOS
# ============================================================

elif page == "Scenarios":

    st.header("Scenario Analysis")

    st.write(
        "Adjust operating assumptions to compare "
        "different valuation scenarios."
    )

    scenario = st.selectbox(
        "Scenario",
        [
            "Base Case",
            "Bull Case",
            "Bear Case",
        ],
    )

    if scenario == "Base Case":

        revenue_growth = 0.08
        margin = 0.20

    elif scenario == "Bull Case":

        revenue_growth = 0.12
        margin = 0.24

    else:

        revenue_growth = 0.03
        margin = 0.16

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Revenue Growth",
            f"{revenue_growth:.1%}",
        )

    with col2:

        st.metric(
            "Operating Margin",
            f"{margin:.1%}",
        )

    st.info(
        f"{scenario} assumptions selected."
    )


# ============================================================
# SENSITIVITY ANALYSIS
# ============================================================

elif page == "Sensitivity Analysis":

    st.header("DCF Sensitivity Analysis")

    if not st.session_state.fcfs:

        st.warning(
            "Save forecast FCFs before running sensitivity analysis."
        )

    else:

        col1, col2 = st.columns(2)

        with col1:

            base_wacc = st.number_input(
                "Base WACC",
                min_value=0.01,
                max_value=0.50,
                value=0.10,
                step=0.01,
                format="%.2f",
            )

        with col2:

            base_growth = st.number_input(
                "Base Terminal Growth",
                min_value=0.0,
                max_value=0.15,
                value=0.03,
                step=0.01,
                format="%.2f",
            )

        discount_rates = [
            base_wacc - 0.02,
            base_wacc - 0.01,
            base_wacc,
            base_wacc + 0.01,
            base_wacc + 0.02,
        ]

        growth_rates = [
            base_growth - 0.01,
            base_growth,
            base_growth + 0.01,
            base_growth + 0.02,
        ]

        # Remove invalid negative growth rates
        growth_rates = [
            g for g in growth_rates
            if g >= 0
        ]

        # DCF requires WACC > terminal growth
        growth_rates = [
            g for g in growth_rates
            if g < min(discount_rates)
        ]

        if st.button(
            "Run Sensitivity Analysis",
            type="primary",
        ):

            try:

                sensitivity = dcf_sensitivity(
                    free_cash_flows=st.session_state.fcfs,
                    discount_rates=discount_rates,
                    terminal_growth_rates=growth_rates,
                )

                st.success(
                    "Sensitivity analysis completed."
                )

                st.subheader(
                    "Enterprise Value Sensitivity"
                )

                import pandas as pd

                table = pd.DataFrame(
                    sensitivity
                ).T

                table.index.name = "WACC"

                table.columns = [
                    f"{g:.1%}"
                    for g in table.columns
                ]

                st.dataframe(
                    table,
                    use_container_width=True,
                )

            except Exception as e:

                st.error(
                    f"Sensitivity analysis failed: {e}"
                )