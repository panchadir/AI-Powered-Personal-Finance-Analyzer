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

from finance_app.models import Transaction
from finance_app.state.engine_bridge import (
    compute_dashboard,
    confidence_label,
    format_day,
    format_money,
    latest_score_event,
    load_commitments,
    load_transactions,
)
from services.analytics import spending_by_category
from services.engine import resolve_due_date

_DEFAULT_TXN_LIMIT = 20
_MAX_TXN_LIMIT = 50


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


@contextmanager
def open_copilot_data(user_id: int) -> Iterator[DbCopilotData]:
    """A short-lived, user-scoped :class:`DbCopilotData` over a fresh session.

    Passed to ``astream_events`` as its ``data_factory``; the streaming loop opens one of these
    per tool call so no DB connection is held open while tokens stream.
    """
    with rx.session() as session:
        yield DbCopilotData(session, user_id)
