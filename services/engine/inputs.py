"""Bridge from persisted rows to the Safe-to-Spend engine's ``EngineInput`` (Epic 5).

The engine (``safe_to_spend.py``) is a pure function over an ``EngineInput``. Something has
to *derive* that input from what the app actually stores: a pile of canonical transactions
and a list of commitments. That derivation is real logic — the statement's closing balance,
the statement end date, whether a salary is detectable and when the next one lands, and how a
``due_day`` integer (1–31) becomes a concrete ``date`` this cycle. It is deterministic,
LLM-free, and framework-agnostic, so it belongs here and not in an ``rx.State`` handler
(AD-1 / AD-2 / NFR-3).

**No DB or Reflex types cross this boundary.** Callers hand in canonical
``services.ingestion.schema.Transaction`` rows and lightweight ``CommitmentRecord`` values;
the ``rx.State`` handler in ``finance_app/state/`` is the only place that knows about
``rx.Model``. All money stays ``Decimal`` (AD-8).

Conservative-by-default (NFR-1): every ambiguity here resolves *against* the user's
spendable figure, never in favour of it. A salary we cannot confirm becomes
``next_income_date=None`` (reserved-only fallback), never an optimistic guess.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Sequence

from services.engine.safe_to_spend import CommitmentInput, EngineInput
from services.utils.enums import Criticality, Direction
from services.ingestion.schema import Transaction

__all__ = [
    "CommitmentRecord",
    "StatementFacts",
    "IncomeSignal",
    "DEFAULT_BUFFER",
    "LOW_DATA_TRANSACTION_COUNT",
    "resolve_due_date",
    "due_day_label",
    "derive_statement_facts",
    "detect_next_income",
    "to_commitment_inputs",
    "build_engine_input",
]

#: DD-2 default emergency buffer (FR-4.4). Per-user configurable; every engine test states it.
DEFAULT_BUFFER = Decimal("2000")

#: Below this many transactions we mark the input ``low_data`` so prediction_confidence
#: degrades to 'Low' (FR-5.4) rather than overstating certainty from a thin statement.
LOW_DATA_TRANSACTION_COUNT = 10

#: A credit whose description matches this is treated as salary/income (FR-4.8). Deliberately
#: narrow: a false *negative* costs the user an "add your payday" prompt, a false *positive*
#: would inflate Safe-to-Spend. NFR-1 says prefer the former.
_SALARY_RE = re.compile(
    r"\b(salary|payroll|sal\s*cr|neft.*salary|wages|stipend|monthly\s+pay)\b",
    re.IGNORECASE,
)

#: A salary credit must be at least this large to count — filters out a ₹1 test credit or a
#: refund that happens to carry the word "salary" in a reference string.
_MIN_SALARY_AMOUNT = Decimal("1000")

_ZERO = Decimal("0")


@dataclass(frozen=True)
class CommitmentRecord:
    """One stored commitment, in the shape the DB holds it (``due_day``, not ``due_date``).

    The persistence layer stores a *day of the month* because a commitment recurs; the engine
    needs a concrete ``date`` for *this* cycle. ``to_commitment_inputs`` performs that
    resolution so the mapping lives in exactly one place.
    """

    name: str
    amount: Decimal
    due_day: int  # 1–31
    criticality: str = Criticality.important.value
    amount_min: Decimal | None = None  # low end of a variable bill; engine reserves the top
    is_predicted: bool = False  # auto-detected, not user-confirmed (Story 5.6)


@dataclass(frozen=True)
class StatementFacts:
    """What the parsed statement tells us, independent of any commitment (FR-4.7)."""

    available_balance: Decimal
    statement_end_date: date | None  # None when there are no transactions at all
    transaction_count: int

    @property
    def has_data(self) -> bool:
        return self.statement_end_date is not None


@dataclass(frozen=True)
class IncomeSignal:
    """The next confirmed income, or an explicit absence of one (FR-4.8)."""

    next_income_date: date | None
    next_income_amount: Decimal | None
    confidence: str  # 'Low' | 'Medium' | 'High' — feeds DD-1 rule 4


def _iso_to_date(iso: str) -> date:
    return date.fromisoformat(iso)


def last_day_of_month(year: int, month: int) -> int:
    """Number of days in ``month`` — the target of the ``due_day=31`` clamp (FR-9.3)."""
    return calendar.monthrange(year, month)[1]


def resolve_due_date(due_day: int, as_of: date) -> date:
    """The next occurrence of ``due_day`` on or after ``as_of``, clamped to real calendar days.

    ``due_day=31`` means "end of month" (FR-9.3): in a 30-day month it resolves to the 30th,
    in February to the 28th/29th. The clamp applies to *any* overflowing day, so ``due_day=30``
    in February also lands on the last day rather than silently rolling into March.

    Raises:
        ValueError: if ``due_day`` is outside 1–31 — a bad day must never quietly become a
            date that under-reserves a commitment.
    """
    if not isinstance(due_day, int) or isinstance(due_day, bool) or not 1 <= due_day <= 31:
        raise ValueError(f"due_day must be an int in 1..31, got {due_day!r}")

    def _clamped(year: int, month: int) -> date:
        return date(year, month, min(due_day, last_day_of_month(year, month)))

    this_cycle = _clamped(as_of.year, as_of.month)
    if this_cycle >= as_of:
        return this_cycle
    # Already past this month — roll to next month.
    year, month = (as_of.year + 1, 1) if as_of.month == 12 else (as_of.year, as_of.month + 1)
    return _clamped(year, month)


def due_day_label(due_day: int) -> str:
    """Human label for a recurring due day: ``31`` renders as ``"end of month"`` (FR-9.3)."""
    if due_day == 31:
        return "end of month"
    suffix = {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd", 31: "st"}.get(due_day, "th")
    return f"{due_day}{suffix} of every month"


def derive_statement_facts(transactions: Sequence[Transaction]) -> StatementFacts:
    """Closing balance + statement end date from the parsed rows (FR-4.7).

    ``available_balance`` is the ``balance_after`` of the chronologically last transaction that
    carries one. When *no* row carries a balance (some CSV exports omit the column), we return
    ``Decimal('0')`` rather than summing amounts — an inferred balance is a fabricated number,
    and the engine's ``max(0, …)`` floor would turn it into a confidently wrong Safe-to-Spend.
    """
    if not transactions:
        return StatementFacts(_ZERO, None, 0)

    # Sort by (date, id) so a stable "last row of the statement" exists even when several
    # transactions share a date. `id` is DB insertion order == statement order.
    def _key(t: Transaction) -> tuple[str, int]:
        return (t.date, t.id if t.id is not None else 0)

    ordered = sorted(transactions, key=_key)
    end_date = _iso_to_date(ordered[-1].date)

    balance = _ZERO
    for txn in reversed(ordered):
        if txn.balance_after is not None:
            balance = txn.balance_after
            break

    return StatementFacts(balance, end_date, len(ordered))


def detect_next_income(
    transactions: Sequence[Transaction], *, as_of: date
) -> IncomeSignal:
    """Find the most recent salary credit and project the next one a month on (FR-4.8).

    Returns an empty signal (``next_income_date=None``) when no salary-shaped credit is found —
    the engine then takes its reserved-only fallback and the dashboard prompts "add one
    manually" rather than showing a zero or an error. This is the honest-refusal path, not a
    failure.

    Confidence is ``High`` only with two or more salary credits roughly a month apart (a real
    cadence). A single credit is ``Medium``: enough to show the after-payday layer, not enough
    for DD-1 rule 4 to let a payday-due commitment ride on the incoming salary.
    """
    salaries = [
        t
        for t in transactions
        if t.direction == Direction.credit
        and t.amount >= _MIN_SALARY_AMOUNT
        and _SALARY_RE.search(t.description_raw or "")
    ]
    if not salaries:
        return IncomeSignal(None, None, "Low")

    salaries.sort(key=lambda t: t.date)
    latest = salaries[-1]
    latest_date = _iso_to_date(latest.date)

    # Project one month forward from the last observed salary, preserving the pay day-of-month
    # and clamping to real calendar days (a 31st salary lands on the 30th in June).
    next_date = resolve_due_date(latest_date.day, latest_date + timedelta(days=1))
    while next_date <= as_of:
        next_date = resolve_due_date(latest_date.day, next_date + timedelta(days=1))

    confidence = "Medium"
    if len(salaries) >= 2:
        gap = (latest_date - _iso_to_date(salaries[-2].date)).days
        if 25 <= gap <= 35:  # a monthly cadence, allowing for weekends/short months
            confidence = "High"

    return IncomeSignal(next_date, latest.amount, confidence)


def to_commitment_inputs(
    commitments: Iterable[CommitmentRecord], *, as_of: date
) -> tuple[CommitmentInput, ...]:
    """Resolve each stored ``due_day`` to this cycle's concrete ``due_date`` for the engine."""
    return tuple(
        CommitmentInput(
            name=c.name,
            amount=c.amount,
            amount_min=c.amount_min,
            due_date=resolve_due_date(c.due_day, as_of),
            criticality=c.criticality,
            is_predicted=c.is_predicted,
        )
        for c in commitments
    )


def build_engine_input(
    transactions: Sequence[Transaction],
    commitments: Iterable[CommitmentRecord],
    *,
    buffer: Decimal = DEFAULT_BUFFER,
    today: date | None = None,
) -> EngineInput:
    """Assemble the full ``EngineInput`` for one user. Deterministic and LLM-free.

    ``as_of`` is the statement's end date when one exists — Safe-to-Spend is only ever as fresh
    as the data behind it, and the hero card says so (FR-4.7). With no transactions at all we
    fall back to ``today`` so an empty-state dashboard still computes rather than crashing;
    ``low_data`` then forces ``prediction_confidence`` to ``'Low'`` (FR-5.4).
    """
    facts = derive_statement_facts(transactions)
    as_of = facts.statement_end_date or today or date.today()
    income = detect_next_income(transactions, as_of=as_of)

    return EngineInput(
        available_balance=facts.available_balance,
        as_of=as_of,
        buffer=buffer,
        commitments=to_commitment_inputs(commitments, as_of=as_of),
        next_income_date=income.next_income_date,
        next_income_amount=income.next_income_amount,
        income_confidence=income.confidence,
        low_data=facts.transaction_count < LOW_DATA_TRANSACTION_COUNT,
    )
