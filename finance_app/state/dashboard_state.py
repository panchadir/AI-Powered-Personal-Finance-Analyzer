"""Dashboard state (Stories 5.1, 5.2, 5.3) — hero card, confidence chip, drill-in, briefing.

Orchestration only (AD-2 / NFR-6): every figure arrives already computed from
``services/engine/`` via ``engine_bridge``, and every sentence arrives from
``services/narrate/``. There is no arithmetic in this file.

The state vars are **display strings**, not engine types. Reflex serializes state to the
browser, and a ``Decimal`` or an ``EvidencePack`` has no business crossing that boundary — nor
does the raw 0–100 Confidence Score, which must never reach the client at all (FR-5.5 /
UX-DR2). Formatting happens once, here, through ``formatINR`` / ``formatDate`` (NFR-7), so no
component is ever tempted to f-string a rupee.

Briefing vs hero card: the briefing is a **snapshot** narrated at page load, while the hero
figures are **live** and re-render when a commitment changes (FR-4.11). That divergence is
intentional, not a bug.
"""
from __future__ import annotations

import asyncio
import dataclasses
import logging

import reflex as rx

from finance_app.state.auth_state import LOGIN_ROUTE, AuthState, user_for_token
from finance_app.state.engine_bridge import (
    compute_dashboard,
    confidence_label,
    confidence_variant,
    format_day,
    format_money,
    humanize_since,
    recent_score_events,
    sync_confidence_score,
)
from services.narrate import BriefingContext, generate_briefing

log = logging.getLogger(__name__)

#: Empty-state copy (UX-DR12). Not "No data available".
EMPTY_HERO_COPY = "Upload a statement and I'll show you what's safe to spend — and why."

#: Shown when the engine can't explain the figure from real data (Story 5.1 fallback).
WHY_FALLBACK = "We don't have enough data yet to fully explain this."


@dataclasses.dataclass
class ScoreEventView:
    """One row of the Confidence Score drill-in panel. Mirrors a real ``score_events`` row."""

    delta: str = ""  # "+4" / "-3" — signed, already formatted
    explanation: str = ""
    when: str = ""  # "2 hours ago"


class DashboardState(AuthState):
    """Loads the engine's evidence pack and exposes it as display-ready strings."""

    # --- Hero card (Story 5.1) ---
    loaded: bool = False
    has_data: bool = False
    safe_to_spend_today: str = "₹0"
    freshness_caveat: str = ""
    after_income_label: str = ""
    after_income_amount: str = ""
    has_income: bool = False
    why_text: str = WHY_FALLBACK
    why_open: bool = False
    is_stale: bool = False
    shortfall: bool = False  # bills cannot be paid (safety_ok False)
    buffer_dented: bool = False  # bills covered, but the emergency buffer is being eaten

    # --- Confidence chip + drill-in (Stories 5.1, 5.2) ---
    # NOTE: the raw score is deliberately absent from this state. It never leaves the server.
    confidence_label: str = "Watch this"
    confidence_variant: str = "red-amber"
    prediction_confidence: str = "Low"
    prediction_reason: str = ""
    drillin_open: bool = False
    score_events: list[ScoreEventView] = []

    # --- Briefing (Story 5.3) ---
    briefing: str = ""
    briefing_loading: bool = False

    @rx.event
    def toggle_why(self):
        """The hero card's "Why ₹X?" expander (FR-5.6)."""
        self.why_open = not self.why_open

    @rx.event
    def toggle_drillin(self):
        """Tapping the chip opens the panel; tapping again collapses it (Story 5.2 AC)."""
        self.drillin_open = not self.drillin_open

    @rx.event
    def go_commitments(self):
        """"+ Add a commitment" → the dedicated Commitments page, not a modal (FR-6.5)."""
        return rx.redirect("/commitments")

    @rx.event
    def go_upload(self):
        return rx.redirect("/upload")

    @rx.event
    async def load_dashboard(self):
        """Page ``on_load``: compute the engine figures, then narrate the briefing.

        Two phases so the hero card paints immediately (NFR-9: render < 3s) rather than waiting
        on an LLM round-trip. The briefing fills in after; its panel shows a loading state
        meanwhile and degrades to deterministic prose if narration fails.
        """
        # This handler is an async *generator* (it yields to paint the hero card before the LLM
        # call), so an early exit is `yield ...; return` — a bare `return <value>` is a syntax
        # error here, not a redirect.
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                yield rx.redirect(LOGIN_ROUTE)
                return

            data = compute_dashboard(session, user.id)
            self.has_data = data.has_data
            self.loaded = True

            if not data.has_data:
                # Empty state (Story 8.2 / UX-DR12): no charts, no STS number, no narration.
                self._reset_to_empty()
                return

            # The score write is atomic with its explanation (FR-5.3) and returns the row the
            # UI reads — never a bare score column (AD-9).
            event = sync_confidence_score(
                session, user.id, data.evidence, trigger_event="dashboard_view"
            )
            self._apply_evidence(data, event.score)
            self._apply_score_events(recent_score_events(session, user.id))
            context = self._briefing_context(data)

        self.briefing_loading = True
        yield  # paint the hero card before the LLM call

        # Narration is off the event loop: it is a network call, and the hero card is already
        # on screen. A failure inside `generate_briefing` returns fallback prose, never raises.
        self.briefing = await asyncio.to_thread(generate_briefing, context)
        self.briefing_loading = False

    def _reset_to_empty(self) -> None:
        self.safe_to_spend_today = ""
        self.freshness_caveat = ""
        self.after_income_label = ""
        self.after_income_amount = ""
        self.has_income = False
        self.why_text = EMPTY_HERO_COPY
        self.is_stale = False
        self.shortfall = False
        self.buffer_dented = False
        self.score_events = []
        self.briefing = ""

    def _apply_evidence(self, data, score: int) -> None:
        """Turn the evidence pack into display strings. No arithmetic — only formatting."""
        evidence = data.evidence

        self.safe_to_spend_today = format_money(evidence.safe_to_spend_today)
        self.freshness_caveat = (
            f"Based on your statement up to {format_day(data.statement_end_date)}"
            if data.statement_end_date
            else ""
        )
        self.is_stale = data.is_stale
        self.shortfall = not evidence.safety_ok
        self.buffer_dented = evidence.safety_ok and not evidence.buffer_intact

        # FR-4.5 / UX-DR3: the two layers are separate rows and are never merged. When the
        # after-income figure is unknowable we prompt for the missing piece rather than showing
        # ₹0 (FR-4.8) — and we say *which* piece is missing, because "we couldn't detect a
        # salary" is untrue when we found the payday but not the amount.
        if evidence.safe_to_spend_after_income is not None and data.next_income_date:
            self.has_income = True
            self.after_income_label = (
                f"After your salary on {format_day(data.next_income_date)}"
            )
            self.after_income_amount = format_money(evidence.safe_to_spend_after_income)
        else:
            self.has_income = False
            self.after_income_amount = ""
            if "income_amount_unknown" in evidence.data_quality_flags:
                self.after_income_label = (
                    f"Your income lands on {format_day(data.next_income_date)}, but I don't "
                    "know how much — add the amount?"
                )
            else:
                self.after_income_label = "We couldn't detect a salary — add one manually?"

        # Label only. The `score` int stays on the server (FR-5.5 / UX-DR2).
        self.confidence_label = confidence_label(score)
        self.confidence_variant = confidence_variant(score)
        self.prediction_confidence = evidence.prediction_confidence
        self.prediction_reason = _PREDICTION_REASONS.get(
            evidence.prediction_confidence, _PREDICTION_REASONS["Low"]
        )

        # "Why?" traces to real engine drivers; the fallback is honest about not knowing.
        self.why_text = " ".join(evidence.drivers) if evidence.drivers else WHY_FALLBACK

    def _apply_score_events(self, events) -> None:
        self.score_events = [
            ScoreEventView(
                delta=f"{event.delta:+d}",
                explanation=event.explanation,
                when=humanize_since(event.timestamp),
            )
            for event in events
        ]

    def _briefing_context(self, data) -> BriefingContext:
        """Hand ``services/narrate/`` pre-formatted figures so it cannot invent one."""
        evidence = data.evidence
        return BriefingContext(
            safe_to_spend_today=format_money(evidence.safe_to_spend_today),
            statement_end_date=format_day(data.statement_end_date),
            prediction_confidence=evidence.prediction_confidence,
            reserved_total=format_money(evidence.reserved_total),
            safe_to_spend_after_income=(
                format_money(evidence.safe_to_spend_after_income)
                if evidence.safe_to_spend_after_income is not None
                else None
            ),
            next_income_date=(
                format_day(data.next_income_date) if data.next_income_date else None
            ),
            days_to_income=evidence.days_to_income,
            safety_ok=evidence.safety_ok,
            drivers=evidence.drivers,
        )


#: Distinct copy per Prediction Confidence level (FR-5.5). Measures *data completeness*, never
#: preparedness — the two are shown side by side and never conflated (FR-5.2).
_PREDICTION_REASONS: dict[str, str] = {
    "High": "we have enough history to see your patterns clearly.",
    "Medium": "some cash spends or variable bills may be missing.",
    "Low": "we only have a little data so far — confidence grows with more.",
}
