"""Recurring-debit detector (Story 5.6 / FR-9.1).

Finds debits that repeat at a roughly-monthly cadence with a near-constant amount, and
surfaces each as a :class:`CommitmentCandidate` for the user to **confirm**. It never creates
a commitment on its own — FR-9.1 is *proactively surface for user confirmation*, and NFR-1's
conservative-by-default rule means we would rather miss a real EMI (the user can still add it
by hand) than ring-fence money against a pattern the user never acknowledged.

Pure, deterministic, framework-agnostic (AD-2): nothing here imports ``reflex`` or
``finance_app``. All money is :class:`~decimal.Decimal` (AD-8). ``detect_recurring_commitments``
is a pure function of its inputs, so "a dismissed pattern is not re-surfaced" is testable
without a database — the caller passes the signatures the user already decided on.

Shares the shape-matching intuition of the Epic 7 ``ZombieSubscriptionDetector`` (near-equal
amount + ~monthly gaps), but answers a different question: that detector *narrates a pattern*;
this one *proposes a commitment to ring-fence*, so it also resolves a ``due_day`` and a
representative amount the engine can reserve against.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from services.ingestion.schema import Transaction
from services.utils.enums import Criticality, Direction

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")

#: Amounts within ±this percent of the group's median count as "the same charge" (FR-9.1).
AMOUNT_TOLERANCE_PCT = Decimal("10")

#: A gap between consecutive charges is "roughly monthly" inside this inclusive day range —
#: wide enough to absorb weekends, short months, and a bank posting a day late.
MONTHLY_MIN_GAP_DAYS = 25
MONTHLY_MAX_GAP_DAYS = 35

#: Two charges are the minimum needed to establish a cadence at all; one charge is a purchase,
#: not a commitment.
MIN_OCCURRENCES = 2


@dataclass(frozen=True)
class CommitmentCandidate:
    """A recurring charge proposed for ring-fencing — structured facts only, no prose.

    ``signature`` is the stable identity the caller stores when the user confirms or dismisses,
    so the same pattern is not proposed twice. ``amount`` is the representative (median) charge
    the confirmed commitment will reserve; ``due_day`` is the day-of-month the charge lands on.
    """

    signature: str
    merchant: str
    amount: Decimal
    due_day: int  # 1–31
    occurrences: int
    criticality: str = Criticality.important.value  # new commitments default to Important (FR-9.2)


def _is_debit(txn: Transaction) -> bool:
    value = txn.direction.value if isinstance(txn.direction, Direction) else txn.direction
    return value == Direction.debit.value


def _merchant_key(txn: Transaction) -> str:
    """The grouping/identity key: normalized merchant name, else the raw description.

    Lower-cased and whitespace-trimmed so casing drift doesn't split one merchant into two
    groups. This inherits the known limitation flagged in Story 3.3's review — bank
    descriptions carrying per-transaction reference numbers won't group — so detection is
    reliable for statements that populate ``merchant_normalized`` (the demo path) and degrades
    honestly (no false grouping) otherwise.
    """
    raw = txn.merchant_normalized or txn.description_raw or ""
    return " ".join(raw.split()).lower()


def _median(amounts: list[Decimal]) -> Decimal:
    """Lower-median of a non-empty list (matches the zombie-subscription detector's choice)."""
    return sorted(amounts)[len(amounts) // 2]


def _modal_due_day(charges: list[Transaction]) -> int:
    """The most common day-of-month among the charges; ties break to the earliest day.

    A recurring bill can post on the 5th one month and the 6th the next; the mode is the
    stable "due day" a user would recognise, and the earliest-day tie-break keeps the
    signature deterministic.
    """
    days = [date.fromisoformat(c.date).day for c in charges]
    counts = Counter(days)
    top = max(counts.values())
    return min(day for day, count in counts.items() if count == top)


def detect_recurring_commitments(
    transactions: Iterable[Transaction],
    *,
    exclude_signatures: Iterable[str] = (),
) -> list[CommitmentCandidate]:
    """Propose recurring debits as commitment candidates the user can confirm.

    A group of same-merchant debits becomes a candidate only when it clears every guard:
    at least :data:`MIN_OCCURRENCES` charges, every amount within :data:`AMOUNT_TOLERANCE_PCT`
    of the median, and every consecutive gap roughly monthly. Any group whose signature is in
    ``exclude_signatures`` (already confirmed or dismissed by the user) is skipped, so a
    dismissed pattern is never re-surfaced.

    Returns candidates ordered by due day (then merchant) for a stable, calm UI. Empty list
    when nothing qualifies — never ``None``.
    """
    excluded = set(exclude_signatures)

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        if _is_debit(txn):
            by_merchant[_merchant_key(txn)].append(txn)

    candidates: list[CommitmentCandidate] = []
    for key, charges in by_merchant.items():
        if len(charges) < MIN_OCCURRENCES:
            continue

        charges = sorted(charges, key=lambda t: t.date)
        amounts = [c.amount for c in charges]
        median = _median(amounts)
        if median <= _ZERO:
            continue

        tolerance = median * AMOUNT_TOLERANCE_PCT / _HUNDRED
        if any(abs(amount - median) > tolerance for amount in amounts):
            continue  # amounts not near-constant → a variable spend, not a fixed commitment

        gaps = [
            (date.fromisoformat(charges[i + 1].date) - date.fromisoformat(charges[i].date)).days
            for i in range(len(charges) - 1)
        ]
        if not all(MONTHLY_MIN_GAP_DAYS <= gap <= MONTHLY_MAX_GAP_DAYS for gap in gaps):
            continue  # cadence isn't ~monthly

        due_day = _modal_due_day(charges)
        signature = f"{key}@{due_day}"
        if signature in excluded:
            continue

        merchant = charges[0].merchant_normalized or charges[0].description_raw or "this merchant"
        candidates.append(
            CommitmentCandidate(
                signature=signature,
                merchant=merchant,
                amount=median,
                due_day=due_day,
                occurrences=len(charges),
            )
        )

    return sorted(candidates, key=lambda c: (c.due_day, c.merchant.lower()))
