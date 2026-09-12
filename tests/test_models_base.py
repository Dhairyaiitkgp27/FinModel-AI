"""Tests for base models: enums and FiscalPeriod."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from core.models import Currency, FiscalPeriod, PeriodType, ScenarioType


def test_fiscal_period_annual_label():
    p = FiscalPeriod(fiscal_year=2023)
    assert p.label() == "FY2023"
    assert str(p) == "FY2023"
    assert p.period_type == PeriodType.ANNUAL


def test_fiscal_period_quarterly_label():
    p = FiscalPeriod(fiscal_year=2023, period_type=PeriodType.QUARTERLY, fiscal_quarter=3)
    assert p.label() == "Q3 2023"


def test_fiscal_period_ttm_label():
    p = FiscalPeriod(fiscal_year=2024, period_type=PeriodType.TTM)
    assert p.label() == "TTM 2024"


def test_fiscal_period_is_frozen_and_hashable():
    p = FiscalPeriod(fiscal_year=2023)
    with pytest.raises(ValidationError):
        p.fiscal_year = 2024  # frozen models reject mutation
    # hashable -> usable as dict key / set member
    assert {p: "x"}[p] == "x"


def test_fiscal_period_equality():
    a = FiscalPeriod(fiscal_year=2023, period_end=date(2023, 12, 31))
    b = FiscalPeriod(fiscal_year=2023, period_end=date(2023, 12, 31))
    assert a == b
    assert hash(a) == hash(b)


def test_fiscal_period_ordering_and_sort():
    periods = [
        FiscalPeriod(fiscal_year=2023),
        FiscalPeriod(fiscal_year=2021),
        FiscalPeriod(fiscal_year=2022),
    ]
    ordered = sorted(periods)
    assert [p.fiscal_year for p in ordered] == [2021, 2022, 2023]


def test_fiscal_period_quarter_ordering():
    q1 = FiscalPeriod(fiscal_year=2023, period_type=PeriodType.QUARTERLY, fiscal_quarter=1)
    q4 = FiscalPeriod(fiscal_year=2023, period_type=PeriodType.QUARTERLY, fiscal_quarter=4)
    assert q1 < q4


def test_fiscal_period_invalid_quarter_rejected():
    with pytest.raises(ValidationError):
        FiscalPeriod(fiscal_year=2023, fiscal_quarter=5)


def test_enum_values():
    assert Currency.USD.value == "USD"
    assert ScenarioType.BULL.value == "bull"
    assert PeriodType.ANNUAL.value == "annual"
