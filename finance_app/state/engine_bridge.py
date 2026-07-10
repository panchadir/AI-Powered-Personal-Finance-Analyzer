"""The single bridge between the DB and the deterministic engine (Epic 5).

``services/`` may not import ``finance_app`` (AD-2), so *something* in the UI layer has to
turn ``rx.Model`` rows into the framework-agnostic values the engine consumes, and turn engine
results back into rows. That is this module, and only this module. Both ``DashboardState`` and
``CommitmentsState`` call it, so the Safe-to-Spend the Dashboard shows and the one the
Commitments page shows are computed by the same code path and can never disagree.

Deliberately **not** an ``rx.State``: it is plain, session-injected functions, so the whole
DB→engine→DB round trip is unit-testable without a Reflex app.

Two rules this module exists to enforce:

* **No arithmetic here.** Every figure comes from ``services/engine/``. This module maps types
  and persists results; it never adds, subtracts, or rounds a rupee (AD-1 / NFR-3).
* **A score never moves without an explanation.** :func:`sync_confidence_score` is the *only*
  way the score is written, and it writes the score and its ``score_events`` row in one
  transaction (FR-5.3 / AD-9). Epic 4's ``compute_confidence_score`` deliberately left this
  writeback to its caller; this is that caller.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlmodel import Session, select

from finance_app.models import Commitment, ScoreEvent, Transaction as TxnModel
from services.engine import (
    CommitmentRecord,
    EvidencePack,
    ScoreResult,
    build_engine_input,
    compute_confidence_score,
    compute_safe_to_spend,
)
from services.ingestion.schema import Transaction
from services.utils.enums import Direction
from services.utils.format import formatDate, formatINR

__all__ = [
    "DashboardData",
    "CONFIDENCE_BANDS",
    "STALE_AFTER_DAYS",
    "confidence_label",
    "confidence_variant",
    "humanize_since",
    "load_transactions",
    "load_commitments",
    "to_commitment_records",
    "compute_dashboard",
    "sync_confidence_score",
    "latest_score_event",
    "recent_score_events",
    "format_money",
    "format_day",
]

#: A statement older than this earns the amber "re-upload" banner (FR-5.7 / UX-DR15).
STALE_AFTER_DAYS = 30

#: Score → (label, chip variant). Label only ever reaches the UI; the raw 0–100 score is never
#: rendered anywhere (FR-5.5 / UX-DR2). Bands are inclusive lower bounds, checked high→low.
#: Tied to Epic 4's bands: a shortfall scores ≤20 and a covered balance scores ≥40, so a ₹0
#: Safe-to-Spend can never coexist with "Well prepared" (CS-4).
CONFIDENCE_BANDS: tuple[tuple[int, str, str], ...] = (
    (70, "Well prepared", "green"),
    (40, "On track", "amber"),
    (0, "Watch this", "red-amber"),
)


def confidence_label(score: int) -> str:
    """The chip's text. Never the number (FR-5.5)."""
    for floor, label, _variant in CONFIDENCE_BANDS:
        if score >= floor:
            return label
    return CONFIDENCE_BANDS[-1][1]


def confidence_variant(score: int) -> str:
    """The chip's CSS modifier: ``green`` | ``amber`` | ``red-amber``."""
    for floor, _label, variant in CONFIDENCE_BANDS:
        if score >= floor:
            return variant
    return CONFIDENCE_BANDS[-1][2]


def _as_utc(moment: datetime.datetime) -> datetime.datetime:
    """Lift a stored timestamp to tz-aware UTC for comparison against ``now()``.

    Stored timestamps are naive UTC by convention (``models._utcnow``). This is the one place
    that convention is turned back into an aware value, because comparing a naive and an aware
    datetime raises ``TypeError`` — and a drill-in panel that crashes is worse than one that is
    an hour off. Already-aware values pass through, so rows written before the convention was
    enforced still render.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=datetime.timezone.utc)
    return moment


def humanize_since(moment: datetime.datetime, *, now: datetime.datetime | None = None) -> str:
    """``"2 hours ago"`` / ``"1 day ago"`` for the score drill-in panel (Story 5.2)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    seconds = max(0, int((_as_utc(now) - _as_utc(moment)).total_seconds()))
    if seconds < 60:
        return "just now"
    for unit_seconds, name in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= unit_seconds:
            count = seconds // unit_seconds
            return f"{count} {name}{'s' if count != 1 else ''} ago"
    return "just now"


@dataclass(frozen=True)
class DashboardData:
    """Everything the hero card needs, computed once per page load.

    ``next_income_date`` is carried alongside the evidence pack because the pack exposes only
    ``days_to_income``. The briefing has to *name* the payday ("After your salary on 30 Jul"),
    and re-deriving that date in the UI would be arithmetic outside the engine.
    """

    evidence: EvidencePack
    score: ScoreResult
    statement_end_date: datetime.date | None
    transaction_count: int
    next_income_date: datetime.date | None = None

    @property
    def has_data(self) -> bool:
        """False for a freshly registered user — the Dashboard shows its empty state."""
        return self.transaction_count > 0

    @property
    def is_stale(self) -> bool:
        """True when the statement is more than 30 days old (FR-5.7)."""
        if self.statement_end_date is None:
            return False
        age = (datetime.date.today() - self.statement_end_date).days
        return age > STALE_AFTER_DAYS


def load_transactions(session: Session, user_id: int) -> list[Transaction]:
    """Read this user's transactions as canonical engine values.

    The ``user_id`` filter is not optional — it is the IDOR boundary (AD-4). Every read in this
    module carries it explicitly rather than relying on a caller to remember.
    """
    rows = session.exec(
        select(TxnModel).where(TxnModel.user_id == user_id).order_by(TxnModel.date)
    ).all()
    return [
        Transaction(
            date=row.date,
            description_raw=row.description_raw,
            amount=Decimal(row.amount),
            direction=Direction(row.direction),
            balance_after=Decimal(row.balance_after) if row.balance_after is not None else None,
            merchant_normalized=row.merchant_normalized,
            category=row.category,
            category_source=row.category_source,
            category_confidence=row.category_confidence,
            user_id=row.user_id,
            source_file_id=row.source_file_id,
            id=row.id,
        )
        for row in rows
    ]


def load_commitments(session: Session, user_id: int) -> list[Commitment]:
    """This user's commitments, soonest due-day first (AD-4 scoped)."""
    return list(
        session.exec(
            select(Commitment)
            .where(Commitment.user_id == user_id)
            .order_by(Commitment.due_day)
        ).all()
    )


def to_commitment_records(rows: list[Commitment]) -> list[CommitmentRecord]:
    """Map persisted rows to the engine's framework-agnostic input type."""
    return [
        CommitmentRecord(
            name=row.name,
            amount=Decimal(row.amount),
            due_day=row.due_day,
            criticality=row.criticality,
        )
        for row in rows
    ]


def compute_dashboard(session: Session, user_id: int) -> DashboardData:
    """Run the engine over this user's real data. Deterministic, LLM-free (AD-1).

    Read-only: computes the score but does not persist it — see :func:`sync_confidence_score`,
    which is the only writer.
    """
    transactions = load_transactions(session, user_id)
    commitments = to_commitment_records(load_commitments(session, user_id))

    engine_input = build_engine_input(transactions, commitments)
    evidence = compute_safe_to_spend(engine_input)

    previous = latest_score_event(session, user_id)
    score = compute_confidence_score(
        evidence, previous_score=previous.score if previous else None
    )
    return DashboardData(
        evidence=evidence,
        score=score,
        statement_end_date=engine_input.as_of if transactions else None,
        transaction_count=len(transactions),
        next_income_date=engine_input.next_income_date,
    )


def latest_score_event(session: Session, user_id: int) -> ScoreEvent | None:
    """The row the UI's score is read from. ``None`` before the first computation (AD-9)."""
    return session.exec(
        select(ScoreEvent)
        .where(ScoreEvent.user_id == user_id)
        .order_by(ScoreEvent.timestamp.desc(), ScoreEvent.id.desc())
    ).first()


def recent_score_events(session: Session, user_id: int, limit: int = 10) -> list[ScoreEvent]:
    """Newest-first history for the drill-in panel (Story 5.2). Every row is a real event."""
    return list(
        session.exec(
            select(ScoreEvent)
            .where(ScoreEvent.user_id == user_id)
            .order_by(ScoreEvent.timestamp.desc(), ScoreEvent.id.desc())
            .limit(limit)
        ).all()
    )


def sync_confidence_score(
    session: Session,
    user_id: int,
    evidence: EvidencePack,
    *,
    trigger_event: str,
) -> ScoreEvent:
    """Recompute the score and persist it **with** its explanation, atomically (FR-5.3 / AD-9).

    This is the only code path that writes a score. There is no "set the score" function to
    call without an event, so an unexplained score change is not merely discouraged — it is
    unreachable. Returns the row the UI should render (the new one, or the unchanged latest).

    A recomputation that produces no delta writes no row: the score didn't change, so there is
    nothing to explain. The first computation for a user always writes (cold start, FR-5.4) —
    the score is real from the first upload, never a fake neutral 50.
    """
    previous = latest_score_event(session, user_id)
    result = compute_confidence_score(
        evidence,
        previous_score=previous.score if previous else None,
        trigger_event=trigger_event,
    )
    if previous is not None and result.delta == 0:
        return previous

    event = ScoreEvent(  # type: ignore[call-arg]
        user_id=user_id,
        score=result.score,
        delta=result.delta,
        trigger_event=result.trigger_event,
        explanation=result.explanation,
        suggested_action=result.suggested_action,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def format_money(amount: Decimal | None) -> str:
    """``formatINR`` with an honest empty state — never renders ``None`` as ``₹0`` (NFR-7)."""
    return formatINR(amount) if amount is not None else "—"


def format_day(value: datetime.date | None) -> str:
    """``formatDate`` over a ``date``. Empty string when unknown, so callers can hide the row."""
    return formatDate(value.isoformat()) if value is not None else ""
