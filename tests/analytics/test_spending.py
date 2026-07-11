"""Unit suite for the Dashboard chart aggregations (Story 5.4, services/analytics/spending.py).

Asserts the numbers behind the donut and the pace trend: debits only (credits never net
against spend), uncategorized debits collapse into one honest slice, and months sort
chronologically. All totals are ``Decimal`` (AD-8) — formatting is the UI's job, not this
module's.
"""
from __future__ import annotations

from decimal import Decimal

from services.analytics import (
    CategorySlice,
    MonthPoint,
    monthly_spend,
    spending_by_category,
)
from services.ingestion.schema import Transaction
from services.utils.enums import Direction


def _txn(date, amount, *, direction=Direction.debit, category=None) -> Transaction:
    return Transaction(
        date=date,
        description_raw="x",
        amount=Decimal(amount),
        direction=direction,
        category=category,
    )


def test_spending_by_category_sums_debits_largest_first() -> None:
    txns = [
        _txn("2026-06-01", "3000", category="Dining"),
        _txn("2026-06-02", "1000", category="Dining"),
        _txn("2026-06-03", "5000", category="Rent"),
    ]
    result = spending_by_category(txns)

    assert result == [
        CategorySlice("Rent", Decimal("5000")),
        CategorySlice("Dining", Decimal("4000")),
    ]


def test_credits_never_net_against_category_spend() -> None:
    txns = [
        _txn("2026-06-01", "3000", category="Dining"),
        _txn("2026-06-05", "50000", direction=Direction.credit, category="Dining"),  # salary
    ]
    result = spending_by_category(txns)

    assert result == [CategorySlice("Dining", Decimal("3000"))]


def test_uncategorised_debits_collapse_into_one_slice() -> None:
    txns = [
        _txn("2026-06-01", "200", category=None),
        _txn("2026-06-02", "300", category=None),
    ]
    result = spending_by_category(txns)

    assert result == [CategorySlice("Uncategorised", Decimal("500"))]


def test_zero_total_categories_are_omitted() -> None:
    # Only a credit for this category — nothing to draw.
    txns = [_txn("2026-06-01", "999", direction=Direction.credit, category="Refunds")]
    assert spending_by_category(txns) == []


def test_monthly_spend_groups_by_month_oldest_first() -> None:
    txns = [
        _txn("2026-06-20", "1000"),
        _txn("2026-04-02", "500"),
        _txn("2026-06-01", "2000"),
        _txn("2026-05-15", "700"),
    ]
    result = monthly_spend(txns)

    assert result == [
        MonthPoint("2026-04", Decimal("500")),
        MonthPoint("2026-05", Decimal("700")),
        MonthPoint("2026-06", Decimal("3000")),
    ]


def test_monthly_spend_excludes_credits() -> None:
    txns = [
        _txn("2026-06-01", "1000"),
        _txn("2026-06-05", "50000", direction=Direction.credit),
    ]
    assert monthly_spend(txns) == [MonthPoint("2026-06", Decimal("1000"))]


def test_empty_input_yields_empty_aggregations() -> None:
    assert spending_by_category([]) == []
    assert monthly_spend([]) == []
