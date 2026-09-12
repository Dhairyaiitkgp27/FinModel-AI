"""Weighted-average cost of capital (WACC) engine.

Computes WACC deterministically from a :class:`WACCInputs`:

* Cost of equity via CAPM: ``risk_free_rate + beta * equity_risk_premium``.
* After-tax cost of debt: ``pretax_cost_of_debt * (1 - tax_rate)``.
* Capital-structure weights from market values of equity and debt.
* ``WACC = w_e * cost_of_equity + w_d * after_tax_cost_of_debt``.

The input model already guarantees a non-degenerate capital structure
(equity + debt > 0), so no division-by-zero can occur here.
"""
from __future__ import annotations

from ..models.valuation import WACCInputs, WACCResult
from ..utils.math import clamp, safe_div

DEFAULT_COST_OF_DEBT = 0.05


def compute_wacc(inputs: WACCInputs) -> WACCResult:
    """Compute a :class:`WACCResult` from WACC inputs."""
    cost_of_equity = inputs.risk_free_rate + inputs.beta * inputs.equity_risk_premium
    after_tax_cost_of_debt = inputs.pretax_cost_of_debt * (1.0 - inputs.tax_rate)

    total_capital = inputs.equity_value + inputs.debt_value
    equity_weight = inputs.equity_value / total_capital
    debt_weight = inputs.debt_value / total_capital

    wacc = equity_weight * cost_of_equity + debt_weight * after_tax_cost_of_debt

    return WACCResult(
        cost_of_equity=cost_of_equity,
        pretax_cost_of_debt=inputs.pretax_cost_of_debt,
        after_tax_cost_of_debt=after_tax_cost_of_debt,
        equity_weight=equity_weight,
        debt_weight=debt_weight,
        wacc=wacc,
    )


def build_wacc_inputs(
    dataset,
    *,
    risk_free_rate: float = 0.04,
    equity_risk_premium: float = 0.055,
    tax_rate: float = 0.21,
    cost_of_debt: float | None = None,
    default_beta: float = 1.0,
) -> WACCInputs:
    """Assemble :class:`WACCInputs` from a :class:`CompanyDataset`.

    Equity value comes from market cap (or price x shares); debt value from the
    latest reported total debt. When ``cost_of_debt`` is not supplied it is
    inferred from the latest interest expense over total debt, falling back to a
    default. Beta comes from market data, defaulting to 1.0.
    """
    market = dataset.market_data
    balance = dataset.financials.latest_balance()
    income = dataset.financials.latest_income()

    beta = market.beta if market and market.beta is not None else default_beta

    equity_value = None
    if market is not None:
        if market.market_cap is not None:
            equity_value = market.market_cap
        elif market.price is not None and market.shares_outstanding is not None:
            equity_value = market.price * market.shares_outstanding
    if equity_value is None or equity_value <= 0:
        raise ValueError("Equity value (market cap) is required to build WACC inputs.")

    debt_value = balance.total_debt if balance and balance.total_debt is not None else 0.0

    if cost_of_debt is None:
        implied = safe_div(
            income.interest_expense if income else None,
            balance.total_debt if balance else None,
        )
        cost_of_debt = implied if implied is not None and implied > 0 else DEFAULT_COST_OF_DEBT
    cost_of_debt = clamp(cost_of_debt, 0.0, 0.5) or 0.0

    return WACCInputs(
        risk_free_rate=risk_free_rate,
        beta=clamp(beta, 0.0, 5.0) or 0.0,
        equity_risk_premium=equity_risk_premium,
        pretax_cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        equity_value=equity_value,
        debt_value=debt_value,
    )
