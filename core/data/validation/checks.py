"""Post-normalisation validation of a :class:`CompanyDataset`.

These checks catch data-quality problems before the analysis and valuation
engines run: missing statements, non-balancing balance sheets, absent headline
figures, and so on. Each problem becomes a :class:`ValidationIssue` with a
severity; the collected :class:`ValidationReport` tells callers whether the data
is fit to model.

Validation is descriptive, not destructive — it never mutates the dataset.
"""
from __future__ import annotations

from ...models.base import FinBaseModel, Severity
from ..dataset import CompanyDataset

# Balance-sheet identity tolerance as a fraction of total assets.
_BALANCE_TOLERANCE = 0.01


class ValidationIssue(FinBaseModel):
    """A single data-quality finding."""

    code: str
    severity: Severity
    message: str
    period: str | None = None


class ValidationReport(FinBaseModel):
    """The collected result of validating a dataset."""

    ticker: str
    issues: list[ValidationIssue] = []

    @property
    def is_valid(self) -> bool:
        """True when there are no high-severity issues."""
        return not any(i.severity == Severity.HIGH for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity in (Severity.MEDIUM, Severity.LOW) for i in self.issues)

    def by_severity(self, severity: Severity) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == severity]

    def summary(self) -> str:
        if not self.issues:
            return f"{self.ticker}: no issues found"
        counts = {s: len(self.by_severity(s)) for s in Severity}
        return (
            f"{self.ticker}: {counts[Severity.HIGH]} high, "
            f"{counts[Severity.MEDIUM]} medium, {counts[Severity.LOW]} low"
        )


def validate_dataset(dataset: CompanyDataset) -> ValidationReport:
    """Run all data-quality checks and return a :class:`ValidationReport`."""
    issues: list[ValidationIssue] = []
    fin = dataset.financials

    # --- Presence of statements ---------------------------------------- #
    if not fin.income_statements:
        issues.append(
            ValidationIssue(
                code="no_income_statements",
                severity=Severity.HIGH,
                message="No income statements available; valuation cannot proceed.",
            )
        )
    if not fin.balance_sheets:
        issues.append(
            ValidationIssue(
                code="no_balance_sheets",
                severity=Severity.MEDIUM,
                message="No balance sheets available; leverage and returns metrics will be limited.",
            )
        )
    if not fin.cash_flow_statements:
        issues.append(
            ValidationIssue(
                code="no_cash_flow_statements",
                severity=Severity.MEDIUM,
                message="No cash flow statements available; DCF inputs will be limited.",
            )
        )

    # --- Latest income statement sanity -------------------------------- #
    latest_income = fin.latest_income()
    if latest_income is not None:
        label = latest_income.period.label()
        if latest_income.revenue is None or latest_income.revenue <= 0:
            issues.append(
                ValidationIssue(
                    code="missing_revenue",
                    severity=Severity.HIGH,
                    message="Latest period has no positive revenue.",
                    period=label,
                )
            )
        if latest_income.net_income is None:
            issues.append(
                ValidationIssue(
                    code="missing_net_income",
                    severity=Severity.LOW,
                    message="Latest period has no net income figure.",
                    period=label,
                )
            )

    # --- Balance-sheet identity ---------------------------------------- #
    for bs in fin.balance_sheets:
        balanced = bs.is_balanced(tolerance_ratio=_BALANCE_TOLERANCE)
        if balanced is False:
            residual = bs.balance_residual()
            issues.append(
                ValidationIssue(
                    code="balance_sheet_unbalanced",
                    severity=Severity.MEDIUM,
                    message=(
                        "Assets do not equal liabilities plus equity "
                        f"(residual {residual:,.0f})."
                    ),
                    period=bs.period.label(),
                )
            )

    # --- Cash flow sanity ---------------------------------------------- #
    latest_cf = fin.latest_cash_flow()
    if latest_cf is not None and latest_cf.cash_from_operations is None:
        issues.append(
            ValidationIssue(
                code="missing_cfo",
                severity=Severity.LOW,
                message="Latest cash flow statement has no operating cash flow.",
                period=latest_cf.period.label(),
            )
        )

    # --- Market data --------------------------------------------------- #
    if dataset.market_data is None:
        issues.append(
            ValidationIssue(
                code="no_market_data",
                severity=Severity.MEDIUM,
                message="No market data available; per-share valuation will be limited.",
            )
        )
    elif dataset.market_data.shares_outstanding is None:
        issues.append(
            ValidationIssue(
                code="missing_shares_outstanding",
                severity=Severity.MEDIUM,
                message="Shares outstanding is unknown; implied share price cannot be computed.",
            )
        )

    return ValidationReport(ticker=dataset.ticker, issues=issues)
