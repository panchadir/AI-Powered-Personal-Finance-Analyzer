"""The bridge between the DB, the insight detectors, and the insight narrator (Story 7.3).

Mirrors ``engine_bridge.py``'s established pattern: plain, session-injected functions, not an
``rx.State`` class, so the whole DB -> detect -> narrate -> persist round trip is unit-testable
without booting Reflex. Neither ``services/engine/insights/`` nor ``services/narrate/`` may
import ``finance_app`` or each other (AD-1 / AD-2) -- this module is the one place all three
meet, exactly as Story 7.1 and 7.2's own Dev Notes each assign to "Story 7.3's caller."

No arithmetic here. Every sentence/figure comes from Story 7.1's detectors or Story 7.2's
narrator; this module only maps types, decides the resurface/dedup state transition (a
comparison, not a financial computation), and persists.
"""
from __future__ import annotations

import datetime
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from sqlmodel import Session, select

from finance_app.models import Insight
from finance_app.state.engine_bridge import load_commitments, load_transactions
from services.engine import resolve_due_date
from services.engine.insights import (
    MATERIAL_CHANGE_THRESHOLD_PCT,
    CommitmentRecord,
    InsightCandidate,
    InsightContext,
    TxnRecord,
    data_months,
    run_all_detectors,
)
from services.narrate.insight_narrator import (
    InsightNarration,
    InsightNarrationInput,
    NarrationEvidencePoint,
    generate_insight_narration,
)

__all__ = [
    "InsightsData",
    "load_insight_context",
    "refresh_insights",
    "dismiss_insight",
    "top_active_insight",
]

#: The single ``metrics`` key compared for the >=15% resurface rule, per pattern (Story 7.3
#: Dev Notes "Headline metric per pattern"). A pattern name with no entry here (a future,
#: not-yet-known detector) is always treated as materially new -- see `_headline_metric`.
_HEADLINE_METRIC_KEY: dict[str, str] = {
    "Post-payday spike": "spike_pct",
    "Death by small purchases": "total",
    "Zombie subscriptions": "monthly_amount",
    "Weekend vs weekday pace": "ratio",
    "Upcoming commitment collision": "projected_shortfall",
}

_SEVERITY_ORDER: dict[str, int] = {"critical": 0, "important": 1, "flexible": 2}


def _utcnow() -> datetime.datetime:
    """Naive UTC -- matches the storage convention pinned in ``finance_app/models.py``."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class InsightsData:
    """Everything the Insights page needs, computed once per page load."""

    active: list[Insight]
    data_months: int


def load_insight_context(
    session: Session, user_id: int, *, as_of: datetime.date | None = None
) -> InsightContext:
    """Map this user's DB rows into Story 7.1's plain detector input (AD-4 scoped).

    Reuses ``engine_bridge.load_transactions``/``load_commitments`` for the actual DB fetch
    (same tables Epic 5 already reads) rather than re-querying — only the further mapping
    into Story 7.1's ``TxnRecord``/``CommitmentRecord`` shapes (different from Epic 4's
    engine-input types of the same name) is new here.
    """
    as_of = as_of or datetime.date.today()

    transactions = tuple(
        TxnRecord(
            date=t.date,
            amount=t.amount,
            direction=t.direction.value,
            description_raw=t.description_raw,
            merchant_normalized=t.merchant_normalized,
            category=t.category,
            balance_after=t.balance_after,
        )
        for t in load_transactions(session, user_id)
    )

    commitments = tuple(
        CommitmentRecord(
            name=c.name,
            amount=Decimal(c.amount),
            due_date=resolve_due_date(c.due_day, as_of),
            criticality=c.criticality,
        )
        for c in load_commitments(session, user_id)
    )

    return InsightContext(
        transactions=transactions, commitments=commitments, as_of=as_of, income_dates=()
    )


def _dedup_key(candidate: InsightCandidate) -> str:
    """Identity key for resurface/dedup lookups (not displayed).

    Equals ``pattern_name`` except for Zombie-subscription candidates: that detector can emit
    more than one candidate per run (one per recurring merchant), all sharing the identical
    ``pattern_name`` -- a bare-name key would conflate two unrelated subscriptions.
    """
    if candidate.pattern_name == "Zombie subscriptions":
        merchant = candidate.metrics.get("merchant", "")
        return f"{candidate.pattern_name}::{merchant}"
    return candidate.pattern_name


def _headline_metric(pattern_name: str, metrics: Mapping[str, object]) -> Decimal | None:
    key = _HEADLINE_METRIC_KEY.get(pattern_name)
    if key is None:
        return None  # unrecognized pattern -- _materially_changed treats None as "changed"
    value = metrics.get(key)
    return value if isinstance(value, Decimal) else None


def _materially_changed(new: Decimal | None, old: Decimal | None) -> bool:
    """>=15% move, with the zero/unknown guards this story's AC calls for."""
    if new is None or old is None:
        return True
    if old == 0:
        return new != 0
    return abs(new - old) / abs(old) * 100 >= MATERIAL_CHANGE_THRESHOLD_PCT


def _serialize_evidence(evidence: tuple) -> str:
    """JSON blob for audit/future use -- this story's page only renders the narrated prose,
    not a re-read evidence list (see Dev Notes "evidence column serialization")."""
    return json.dumps(
        [{"date": e.date, "merchant": e.merchant, "amount": str(e.amount)} for e in evidence]
    )


def _to_narration_input(candidate: InsightCandidate) -> InsightNarrationInput:
    """The exact 1:1 mapping Story 7.2's own Dev Notes assign to "Story 7.3's caller."""
    return InsightNarrationInput(
        pattern_name=candidate.pattern_name,
        severity=candidate.severity,
        evidence=tuple(
            NarrationEvidencePoint(date=e.date, merchant=e.merchant, amount=e.amount)
            for e in candidate.evidence
        ),
        metrics=candidate.metrics,
        data_months=candidate.data_months,
    )


def _apply_narration(
    row: Insight,
    candidate: InsightCandidate,
    narration: InsightNarration,
    metric_value: Decimal | None,
) -> None:
    row.observation = narration.observation
    row.evidence = _serialize_evidence(candidate.evidence)
    row.explanation = narration.explanation
    row.effect = narration.effect
    row.action_suggestion = narration.advice
    row.severity = candidate.severity
    row.metric_value = metric_value
    row.created_at = _utcnow()  # bumped so an in-place update still sorts newest-first


def _load_active(session: Session, user_id: int) -> list[Insight]:
    """Newest-first within severity tier (AC #3): fetch newest-first by ``created_at``
    (``id`` as the tiebreak for same-timestamp rows, mirroring
    ``engine_bridge.recent_score_events``'s identical convention), then a *stable* sort by
    severity preserves that recency order within each tier. ``created_at`` — not ``id`` —
    is the sort key because ``_apply_narration`` bumps ``created_at`` (not ``id``, which
    never changes) when an active row is updated in place, so a materially-changed insight
    correctly moves back to the top of its tier."""
    rows = list(
        session.exec(
            select(Insight)
            .where(Insight.user_id == user_id, Insight.status == "active")
            .order_by(Insight.created_at.desc(), Insight.id.desc())
        ).all()
    )
    return sorted(rows, key=lambda r: _SEVERITY_ORDER.get(r.severity, 1))


def refresh_insights(
    session: Session, user_id: int, *, as_of: datetime.date | None = None
) -> InsightsData:
    """Run the detectors, apply the resurface/dedup state machine, and return the active feed.

    See the story's Dev Notes "Corrected resurface algorithm" for why this is a 2-branch state
    machine and not the naive "dismissed row missing -> always insert" reading of the AC prose
    (that reading would duplicate every steady, already-active pattern on every page load).
    """
    ctx = load_insight_context(session, user_id, as_of=as_of)
    candidates = run_all_detectors(ctx)

    for candidate in candidates:
        key = _dedup_key(candidate)
        metric_value = _headline_metric(candidate.pattern_name, candidate.metrics)

        active_row = session.exec(
            select(Insight).where(
                Insight.user_id == user_id,
                Insight.dedup_key == key,
                Insight.status == "active",
            )
        ).first()
        if active_row is not None:
            # `_materially_changed` treats *any* None as "changed" -- correct for the
            # never-seen-before / dismissed-resurface paths below (an unmapped pattern
            # should never be silently suppressed there), but wrong here: an unmapped
            # pattern's metric_value is None both times, and without this guard an
            # already-active row would be needlessly re-narrated (an LLM call) on every
            # single page load forever instead of being left alone like every other
            # unchanged pattern.
            both_unknown = metric_value is None and active_row.metric_value is None
            if not both_unknown and _materially_changed(metric_value, active_row.metric_value):
                narration = generate_insight_narration(_to_narration_input(candidate))
                _apply_narration(active_row, candidate, narration, metric_value)
                session.add(active_row)
                session.commit()
            continue  # unchanged: leave the existing active row alone, never duplicate it

        dismissed_row = session.exec(
            select(Insight)
            .where(
                Insight.user_id == user_id,
                Insight.dedup_key == key,
                Insight.status == "dismissed",
            )
            .order_by(Insight.dismissed_at.desc())
        ).first()
        if dismissed_row is not None:
            # Same both-None guard as the active-row branch above: an unmapped pattern's
            # metric_value is None on both sides, and without this a dismissed insight for
            # it would never actually stay dismissed -- every refresh would read "changed"
            # and immediately create a brand-new active row, silently overriding the user's
            # dismiss action.
            both_unknown = metric_value is None and dismissed_row.metric_value is None
            if both_unknown or not _materially_changed(metric_value, dismissed_row.metric_value):
                continue  # stays correctly suppressed

        # Either never seen before, or a dismissed pattern that has now materially changed --
        # either way, a brand-new row (never un-dismiss the old one).
        narration = generate_insight_narration(_to_narration_input(candidate))
        new_row = Insight(  # type: ignore[call-arg]
            user_id=user_id,
            pattern_name=candidate.pattern_name,
            observation=narration.observation,
            evidence=_serialize_evidence(candidate.evidence),
            explanation=narration.explanation,
            effect=narration.effect,
            action_suggestion=narration.advice,
            status="active",
            severity=candidate.severity,
            metric_value=metric_value,
            dedup_key=key,
        )
        session.add(new_row)
        session.commit()

    return InsightsData(
        active=_load_active(session, user_id), data_months=data_months(ctx.transactions)
    )


def top_active_insight(session: Session, user_id: int) -> Insight | None:
    """The single highest-priority active insight (Story 7.4's Dashboard teaser).

    Read-only: delegates entirely to `_load_active`'s existing severity-tier/newest-first
    ordering, and deliberately never runs the detectors or calls the narrator (that only
    happens once, on the Insights page's own load via `refresh_insights` -- see Story 7.4's
    Dev Notes "Why this is read-only"). A user who has never opened the Insights page simply
    has no rows yet, so this correctly returns `None`, same as "ran and found nothing."
    """
    rows = _load_active(session, user_id)
    return rows[0] if rows else None


def dismiss_insight(session: Session, user_id: int, insight_id: int) -> None:
    """Mark an insight dismissed (AC #5). A no-op -- not a crash -- for a foreign or
    nonexistent ``insight_id`` (AD-4 IDOR guard: nothing to leak, nothing to raise)."""
    row = session.exec(
        select(Insight).where(Insight.id == insight_id, Insight.user_id == user_id)
    ).first()
    if row is None:
        return
    row.status = "dismissed"
    row.dismissed_at = _utcnow()
    session.add(row)
    session.commit()
