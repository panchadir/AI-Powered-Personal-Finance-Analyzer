"""Spending aggregation for the Dashboard charts (Story 5.4 / FR-6.1 supporting evidence).

Two aggregations feed the below-the-fold charts:

* :func:`spending_by_category` — total debit spend per category (the donut).
* :func:`monthly_spend` — total debit spend per calendar month (the pace trend).

**Debits only.** A chart of "where your money went" must never net income against spend, or a
salary credit would silently shrink a category and mislead. Credits are dropped up front.

Pure and framework-agnostic (AD-2): no ``reflex`` / ``finance_app`` import. All money is
``Decimal`` (AD-8). The caller (``dashboard_state``) formats these with ``formatINR`` /
month labels — this module returns raw numbers only, never display strings.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from services.ingestion.schema import Transaction
from services.utils.enums import Direction

_ZERO = Decimal("0")

#: Label for debits Epic 3 could not categorize. Matches the Copilot tool's wording so the two
#: surfaces agree.
UNCATEGORISED = "Uncategorised"


@dataclass(frozen=True)
class CategorySlice:
    """One donut slice: a category and its total debit spend (``Decimal``, not formatted)."""

    category: str
    total: Decimal


@dataclass(frozen=True)
class MonthPoint:
    """One point on the monthly-pace trend. ``month`` is an ISO ``'YYYY-MM'`` key so points
    sort chronologically; the UI turns it into a ``"Jun 2026"`` label."""

    month: str
    total: Decimal


def _is_debit(txn: Transaction) -> bool:
    """True for a spend. Tolerates a plain-string ``direction`` as well as the enum."""
    value = txn.direction.value if isinstance(txn.direction, Direction) else txn.direction
    return value == Direction.debit.value


def spending_by_category(transactions: Iterable[Transaction]) -> list[CategorySlice]:
    """Total debit spend per category, largest first.

    Uncategorized debits collapse into a single ``"Uncategorised"`` slice rather than being
    dropped — hiding them would make the donut's total quietly disagree with the statement.
    Zero-total categories are omitted (a donut slice of ₹0 is noise, not information).
    """
    totals: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    for txn in transactions:
        if not _is_debit(txn):
            continue
        totals[txn.category or UNCATEGORISED] += txn.amount

    slices = [CategorySlice(category, total) for category, total in totals.items() if total > _ZERO]
    # Sort by total desc, then category name for a stable order when totals tie.
    return sorted(slices, key=lambda s: (-s.total, s.category))


def monthly_spend(transactions: Iterable[Transaction]) -> list[MonthPoint]:
    """Total debit spend per calendar month, oldest month first.

    Groups on the ``'YYYY-MM'`` prefix of the already-ISO-normalized ``date`` (Story 2.1
    guarantees the format), so no date parsing or arithmetic is needed here.
    """
    totals: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    for txn in transactions:
        if not _is_debit(txn):
            continue
        totals[txn.date[:7]] += txn.amount

    return [MonthPoint(month, totals[month]) for month in sorted(totals)]
