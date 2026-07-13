"""UI-layer data provider for the Copilot read-only tools (Story 6.2 wiring).

Implements the ``services.narrate.tools.CopilotData`` contract against the real database and
the deterministic engines. This is the UI side of the injected-provider seam: the service
layer defines *what* the read-only tools are; this binds them to ``finance_app.models`` and
``services/engine`` — the allowed UI → Service → Data direction (AD-2), so ``services/`` itself
never imports the app layer.

Honesty guarantees baked in here:

* Every read is scoped to the ``user_id`` bound at construction — the LLM cannot choose whose
  data it sees (IDOR guard, AD-4).
* Money is returned as ``formatINR`` strings so the model copies an already-correct figure
  rather than formatting a raw number itself (FR-7.3 rule 1).
* The raw 0–100 Confidence Score never leaves the server — only its label (FR-5.5 / UX-DR2).
* When a figure genuinely does not exist yet (no statement uploaded), the provider returns
  ``{"available": False, "reason": …}`` so the model says so plainly (FR-7.6).

These methods replace the Epic-4/Epic-5 *stubs* the tools shipped with: now that the engine
and commitments exist, ``get_safe_to_spend`` / ``get_confidence_score`` /
``get_upcoming_commitments`` return real data through the same ``engine_bridge`` the Dashboard
uses, so the Copilot and the Dashboard can never disagree.
"""
from __future__ import annotations

import datetime
from contextlib import contextmanager
from typing import Any, Iterator

import reflex as rx
from sqlmodel import Session, select

from finance_app.models import Insight, Transaction, UploadedFile
from finance_app.state.engine_bridge import (
    compute_dashboard,
    confidence_label,
    detect_commitment_candidates,
    format_day,
    format_money,
    humanize_since,
    latest_score_event,
    load_commitments,
    load_transactions,
    recent_score_events,
)
from services.analytics import monthly_spend, spending_by_category
from services.engine import detect_next_income, due_day_label, resolve_due_date
from services.utils.enums import Criticality

_DEFAULT_TXN_LIMIT = 20
_MAX_TXN_LIMIT = 50

_DEFAULT_HISTORY_LIMIT = 5
_MAX_HISTORY_LIMIT = 20

#: Insight severity → sort weight, most urgent first. Mirrors the Insights page ordering so the
#: Copilot surfaces the same thing the user would see there.
_SEVERITY_ORDER: dict[str, int] = {
    Criticality.critical.value: 0,
    Criticality.important.value: 1,
    Criticality.flexible.value: 2,
}


def _format_month(iso_month: str) -> str:
    """``'2026-06'`` → ``'Jun 2026'``. Falls back to the raw key if it isn't ``YYYY-MM``."""
    try:
        return datetime.datetime.strptime(iso_month, "%Y-%m").strftime("%b %Y")
    except ValueError:
        return iso_month


def _change_direction(delta: int) -> str:
    """Human word for a score delta's sign — the raw number never leaves the server (FR-5.5)."""
    if delta > 0:
        return "improved"
    if delta < 0:
        return "dropped"
    return "unchanged"


class DbCopilotData:
    """Read-only, user-scoped Copilot data backed by the DB and the engines (Story 6.2)."""

    def __init__(self, session: Session, user_id: int) -> None:
        self._session = session
        self._user_id = user_id

    # -- Safe-to-Spend (Epic 4, formerly a stub) ---------------------------------------
    def get_safe_to_spend(self) -> dict[str, Any]:
        data = compute_dashboard(self._session, self._user_id)
        if not data.has_data:
            return {
                "available": False,
                "reason": (
                    "No statement has been uploaded yet, so there is no Safe-to-Spend "
                    "figure. Tell the user to upload a bank statement first."
                ),
            }
        ev = data.evidence
        result: dict[str, Any] = {
            "available": True,
            "safe_to_spend_today": format_money(ev.safe_to_spend_today),
            "reserved_total": format_money(ev.reserved_total),
            "days_until_income": ev.days_to_income,
            "prediction_confidence": ev.prediction_confidence,
            "all_commitments_covered": ev.safety_ok,
            "statement_up_to": format_day(data.statement_end_date),
        }
        if ev.safe_to_spend_after_income is not None and data.next_income_date:
            result["safe_to_spend_after_income_per_day"] = format_money(
                ev.safe_to_spend_after_income
            )
            result["next_income_date"] = format_day(data.next_income_date)
        return result

    # -- Confidence Score (Epic 4, formerly a stub) ------------------------------------
    def get_confidence_score(self) -> dict[str, Any]:
        # Prefer the persisted latest event (what the Dashboard shows); fall back to a
        # read-only computation if the user hasn't opened the Dashboard yet. The raw integer
        # is deliberately never included — only the label (FR-5.5).
        event = latest_score_event(self._session, self._user_id)
        if event is not None:
            return {
                "available": True,
                "label": confidence_label(event.score),
                "explanation": event.explanation,
                "suggested_action": event.suggested_action,
            }

        data = compute_dashboard(self._session, self._user_id)
        if not data.has_data:
            return {
                "available": False,
                "reason": (
                    "No statement has been uploaded yet, so there is no Confidence Score. "
                    "Tell the user to upload a statement first."
                ),
            }
        return {
            "available": True,
            "label": confidence_label(data.score.score),
            "explanation": data.score.explanation,
            "prediction_confidence": data.evidence.prediction_confidence,
        }

    # -- Transactions ------------------------------------------------------------------
    def query_transactions(
        self, *, category: str | None, direction: str | None, limit: int | None
    ) -> dict[str, Any]:
        capped = min(int(limit) if limit is not None else _DEFAULT_TXN_LIMIT, _MAX_TXN_LIMIT)
        stmt = select(Transaction).where(Transaction.user_id == self._user_id)
        if category:
            stmt = stmt.where(Transaction.category == category)
        if direction:
            stmt = stmt.where(Transaction.direction == direction)
        stmt = stmt.order_by(Transaction.date.desc()).limit(capped)  # type: ignore[union-attr]

        rows = self._session.exec(stmt).all()
        return {
            "count": len(rows),
            "transactions": [
                {
                    "date": r.date,
                    "merchant": r.merchant_normalized or r.description_raw,
                    "amount": format_money(r.amount),
                    "direction": r.direction,
                    "category": r.category or "Uncategorised",
                }
                for r in rows
            ],
        }

    # -- Spending by category ----------------------------------------------------------
    def get_spending_by_category(self) -> dict[str, Any]:
        slices = spending_by_category(load_transactions(self._session, self._user_id))
        if not slices:
            return {
                "available": False,
                "reason": "No categorised spending yet — the statement has no debits to group.",
            }
        return {
            "by_category": [
                {"category": s.category, "total": format_money(s.total)} for s in slices
            ]
        }

    # -- Upcoming commitments (Epic 5, formerly a stub) --------------------------------
    def get_upcoming_commitments(self) -> dict[str, Any]:
        rows = load_commitments(self._session, self._user_id)
        if not rows:
            return {
                "commitments": [],
                "note": "The user has not declared any commitments yet.",
            }
        today = datetime.date.today()
        ordered = sorted(
            ((resolve_due_date(r.due_day, today), r) for r in rows), key=lambda pair: pair[0]
        )
        return {
            "commitments": [
                {
                    "name": r.name,
                    "amount": format_money(r.amount),
                    "due": format_day(due_date),
                    "criticality": r.criticality,
                }
                for due_date, r in ordered
            ]
        }

    # -- Spending trend over time ------------------------------------------------------
    def get_spending_trend(self, *, category: str | None) -> dict[str, Any]:
        """Total debit spend per calendar month, oldest first (reuses the Dashboard's
        ``monthly_spend`` so the Copilot's trend and the pace chart can never disagree).

        Optionally scoped to a single category. Money is pre-formatted so the model copies a
        correct figure rather than doing arithmetic (FR-7.3 rule 1).
        """
        txns = load_transactions(self._session, self._user_id)
        if category:
            txns = [t for t in txns if t.category == category]
        points = monthly_spend(txns)
        if not points:
            reason = (
                f"No spending recorded for category '{category}' yet."
                if category
                else "No spending recorded yet — upload a statement first."
            )
            return {"available": False, "reason": reason}
        result: dict[str, Any] = {
            "by_month": [
                {"month": _format_month(p.month), "total": format_money(p.total)}
                for p in points
            ]
        }
        if category:
            result["category"] = category
        return result

    # -- Behavioral insights (Epic 7) --------------------------------------------------
    def get_insights(self) -> dict[str, Any]:
        """The active insights already surfaced on the Insights page (Epic 7), most urgent
        first. Read-only — the Copilot never invents insights, it only relays detected ones."""
        rows = self._session.exec(
            select(Insight).where(
                Insight.user_id == self._user_id, Insight.status == "active"
            )
        ).all()
        if not rows:
            return {
                "insights": [],
                "note": "No active insights right now — nothing notable was detected.",
            }
        ordered = sorted(
            rows, key=lambda i: (_SEVERITY_ORDER.get(i.severity, 99), -(i.id or 0))
        )
        return {
            "insights": [
                {
                    "observation": i.observation,
                    "evidence": i.evidence,
                    "explanation": i.explanation,
                    "effect": i.effect,
                    "suggested_action": i.action_suggestion,
                    "severity": i.severity,
                }
                for i in ordered
            ]
        }

    # -- Confidence-Score history (labels only, FR-5.5) --------------------------------
    def get_score_history(self, *, limit: int | None) -> dict[str, Any]:
        """Recent Confidence-Score changes, newest first — label + direction + explanation.

        The raw 0–100 score and the numeric delta never leave the server (FR-5.5); only the
        band *label* and a human word for the change direction are exposed.
        """
        capped = min(
            int(limit) if limit is not None else _DEFAULT_HISTORY_LIMIT, _MAX_HISTORY_LIMIT
        )
        events = recent_score_events(self._session, self._user_id, limit=capped)
        if not events:
            return {
                "available": False,
                "reason": (
                    "No Confidence-Score history yet — it appears after the first statement "
                    "is uploaded."
                ),
            }
        return {
            "history": [
                {
                    "when": humanize_since(e.timestamp),
                    "label": confidence_label(e.score),
                    "change": _change_direction(e.delta),
                    "explanation": e.explanation,
                    "suggested_action": e.suggested_action,
                }
                for e in events
            ]
        }

    # -- Detected (unconfirmed) recurring charges (Story 5.6) --------------------------
    def get_detected_subscriptions(self) -> dict[str, Any]:
        """Recurring charges the detector proposed that the user hasn't confirmed or dismissed
        yet — the "forgotten subscription" surface. Reuses the same deterministic detector the
        Commitments page uses, so the two can never disagree, and it already excludes anything
        the user has already decided on (FR-9.1)."""
        candidates = detect_commitment_candidates(self._session, self._user_id)
        if not candidates:
            return {
                "detected_subscriptions": [],
                "note": (
                    "No new recurring charges detected — either there aren't enough repeats "
                    "yet, or the user has already reviewed the ones found."
                ),
            }
        return {
            "detected_subscriptions": [
                {
                    "merchant": c.merchant,
                    "amount": format_money(c.amount),
                    "due": due_day_label(c.due_day),
                    "times_seen": c.occurrences,
                }
                for c in candidates
            ],
            "note": "These are suggestions to review, not confirmed commitments.",
        }

    # -- Income detection (Epic 4) -----------------------------------------------------
    def get_income_summary(self) -> dict[str, Any]:
        """The next detected salary/income — date, amount, and detection confidence.

        Delegates to the engine's ``detect_next_income`` (the same signal Safe-to-Spend uses),
        so the Copilot never invents an income figure. When no salary-shaped credit exists it
        says so plainly rather than guessing (FR-4.8 honest-refusal path)."""
        txns = load_transactions(self._session, self._user_id)
        if not txns:
            return {
                "available": False,
                "reason": "No statement uploaded yet, so no income has been detected.",
            }
        signal = detect_next_income(txns, as_of=datetime.date.today())
        if signal.next_income_date is None:
            return {
                "available": False,
                "reason": (
                    "No salary-shaped income was detected in the transactions. The user may "
                    "need to add their income manually."
                ),
            }
        return {
            "available": True,
            "next_income_date": format_day(signal.next_income_date),
            "expected_amount": format_money(signal.next_income_amount),
            "detection_confidence": signal.confidence,
        }

    # -- Data coverage / freshness (FR-5.7) --------------------------------------------
    def get_data_coverage(self) -> dict[str, Any]:
        """How much data exists for the user and whether it is stale — lets the Copilot qualify
        its answers honestly ("I only have one month of data…") with specifics rather than a
        vague hedge."""
        data = compute_dashboard(self._session, self._user_id)
        if not data.has_data:
            return {
                "available": False,
                "reason": "No statement has been uploaded yet, so there is no data to analyse.",
            }
        txns = load_transactions(self._session, self._user_id)
        statement_count = len(
            self._session.exec(
                select(UploadedFile).where(UploadedFile.user_id == self._user_id)
            ).all()
        )
        dates = [t.date for t in txns]
        result: dict[str, Any] = {
            "available": True,
            "statements_uploaded": statement_count,
            "transaction_count": data.transaction_count,
            "earliest_transaction": format_day(datetime.date.fromisoformat(min(dates))),
            "latest_transaction": format_day(datetime.date.fromisoformat(max(dates))),
            "statement_up_to": format_day(data.statement_end_date),
            "is_stale": data.is_stale,
        }
        if data.is_stale:
            result["note"] = (
                "This data is more than 30 days old — figures may no longer reflect reality. "
                "Encourage the user to upload a fresh statement."
            )
        return result


@contextmanager
def open_copilot_data(user_id: int) -> Iterator[DbCopilotData]:
    """A short-lived, user-scoped :class:`DbCopilotData` over a fresh session.

    Passed to ``astream_events`` as its ``data_factory``; the streaming loop opens one of these
    per tool call so no DB connection is held open while tokens stream.
    """
    with rx.session() as session:
        yield DbCopilotData(session, user_id)
