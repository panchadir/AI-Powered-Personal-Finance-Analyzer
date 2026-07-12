"""Insights page state (Story 7.3) — loads narrated insights, owns the dismiss lifecycle.

Orchestration only (AD-2 / NFR-6): every sentence/figure arrives already computed from
Story 7.1's detectors + Story 7.2's narrator via ``insights_bridge``. No arithmetic here.
"""
from __future__ import annotations

import asyncio
import dataclasses
import logging
from urllib.parse import quote

import reflex as rx

from finance_app.state.auth_state import LOGIN_ROUTE, AuthState, user_for_token
from finance_app.state.insights_bridge import dismiss_insight, refresh_insights
from services.engine.insights import MIN_DATA_MONTHS_FOOTNOTE

log = logging.getLogger(__name__)

#: FR-8.5's exact required string — the WDS prototype's own footer copy is placeholder text,
#: not this string (see Story 7.3 Dev Notes).
FOOTER_NOTE = "More data sharpens these patterns."

#: Empty-state copy (FR-8.4) — never a blank page or "No insights available".
EMPTY_COPY = "Insights will appear once I've analysed your statement."


@dataclasses.dataclass
class InsightCardView:
    """One active insight, pre-formatted for the page. Mirrors a real ``Insight`` row —
    no card is ever rendered that isn't backed by one (mirrors ``ScoreEventView``'s contract
    in ``dashboard_state.py``)."""

    id: int = 0
    pattern_name: str = ""
    observation: str = ""
    explanation: str = ""
    effect: str = ""
    advice: str = ""
    severity: str = "important"
    copilot_href: str = ""  # precomputed here — a foreach render fn can't call quote()


class InsightsState(AuthState):
    """Loads the active insight feed and exposes it as display-ready cards."""

    loaded: bool = False
    cards: list[InsightCardView] = []
    show_footer_note: bool = False
    highlight_id: int = 0  # Story 7.4: ?highlight=<id> deep-link from the Dashboard teaser

    @rx.event
    async def load_insights(self):
        """Page ``on_load``: run/persist detection, then load the ordered active feed.

        Async so ``refresh_insights`` — which can make several sequential LLM calls, one
        per new/materially-changed pattern — runs off the event loop via
        ``asyncio.to_thread``, mirroring ``dashboard_state.load_dashboard``'s identical
        reason for doing the same around its own narration call: a blocking network call
        must never stall the whole Reflex server for every other connected user.
        """
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)

            data = await asyncio.to_thread(refresh_insights, session, user.id)
            self.cards = [self._to_card(row) for row in data.active]
            self.show_footer_note = data.data_months < MIN_DATA_MONTHS_FOOTNOTE
            self.loaded = True

        # Story 7.4: scroll to the Dashboard teaser's linked insight, if any (mirrors
        # copilot_state.load_history's identical ?insight= parsing). A stale/no-longer-active
        # id (dismissed or materially-changed since the teaser was rendered) is a silent
        # no-op in the browser via `?.` -- never a crash, never checked here.
        raw_highlight = self.router.page.params.get("highlight", "")
        try:
            self.highlight_id = int(raw_highlight) if raw_highlight else 0
        except (ValueError, TypeError):
            self.highlight_id = 0

        if self.highlight_id:
            return rx.call_script(
                f"document.getElementById('insight-{self.highlight_id}')"
                "?.scrollIntoView({behavior: 'smooth', block: 'center'})"
            )

    @rx.event
    def dismiss(self, insight_id: int):
        """Optimistic UI update first (AC #5), then persist the dismissal."""
        self.cards = [card for card in self.cards if card.id != insight_id]
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)
            dismiss_insight(session, user.id, insight_id)

    @staticmethod
    def _to_card(row) -> InsightCardView:
        return InsightCardView(
            id=row.id,
            pattern_name=row.pattern_name,
            observation=row.observation,
            explanation=row.explanation,
            effect=row.effect,
            advice=row.action_suggestion,
            severity=row.severity,
            # Story 6.4's receiving side already parses `insight`/`pre` — this story only
            # needs to produce the link (Story 7.3 Dev Notes "Ask Copilot contract").
            copilot_href=f"/copilot?insight={row.id}&pre={quote(row.action_suggestion)}",
        )
