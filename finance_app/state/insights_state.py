"""Insights page state (Story 7.3) — loads narrated insights, owns the dismiss lifecycle.

Orchestration only (AD-2 / NFR-6): every sentence/figure arrives already computed from
Story 7.1's detectors + Story 7.2's narrator via ``insights_bridge``. No arithmetic here —
including in the evidence block: each point is *formatted* (``formatINR``/``formatDate``),
never recomputed, from the exact figures the detector cited.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from decimal import Decimal
from urllib.parse import quote

import reflex as rx

from finance_app.state.auth_state import LOGIN_ROUTE, AuthState, user_for_token
from finance_app.state.engine_bridge import format_money
from finance_app.state.insights_bridge import dismiss_insight, refresh_insights
from services.engine.insights import (
    MIN_DATA_MONTHS_FOOTNOTE,
    MIN_TRANSACTIONS_FOR_INSIGHTS,
)
from services.utils.format import formatDate

log = logging.getLogger(__name__)

#: FR-8.5's exact required string — the WDS prototype's own footer copy is placeholder text,
#: not this string (see Story 7.3 Dev Notes).
FOOTER_NOTE = "More data sharpens these patterns."

#: Empty-state copy (FR-8.4) — never a blank page or "No insights available".
#: Two distinct arms, because they mean opposite things to the user: one says *you're done*,
#: the other says *I'm not ready yet*. Collapsing them into one string (the bug this replaces)
#: tells a brand-new user their empty feed is an achievement.
EMPTY_COPY = "You've read everything I noticed. I'll surface new patterns as they appear."
INSUFFICIENT_DATA_COPY = (
    "I'm still getting to know your spending. Patterns need about a month of "
    "transactions before I can name them honestly — upload another statement and "
    "I'll start pointing things out."
)

#: FR-8.2's evidence block reads "5 Jul 2026 · Swiggy · ₹450" — the separator is a middle dot
#: because the three parts are peers, not a sentence.
_EVIDENCE_SEP = " · "

#: Severity tier → the badge label shown on the card (Story 7.3 AC #3 orders by tier; until
#: now nothing on the page *said* which tier a card was in).
SEVERITY_LABELS: dict[str, str] = {
    "critical": "Needs attention",
    "important": "Worth a look",
    "flexible": "Just noticing",
}

#: Pattern → card icon. The WDS prototype's card markup always supported a per-insight icon
#: (``ins.icon || '💡'``); we only ever sent it the fallback, so every card wore the same
#: lightbulb and the feed read as one undifferentiated wall. An unknown pattern (a detector
#: added without an entry here) still gets the prototype's own default rather than a blank.
DEFAULT_ICON = "💡"
PATTERN_ICONS: dict[str, str] = {
    # warnings
    "Post-payday spike": "💸",
    "Death by small purchases": "🧾",
    "Zombie subscriptions": "🧟",
    "Weekend vs weekday pace": "📅",
    "Upcoming commitment collision": "⚠️",
    # wins
    "Subscription ended": "🚫",
    "Commitments covered": "🛡️",
    "Spending pace improved": "📉",
}

#: The two bands. Wins are not "less urgent warnings" — they are a different kind of thing,
#: and the whole point of the market-research finding is that they must not be buried among
#: the warnings to be noticed.
WINS_HEADING = "What's going well"
WATCH_HEADING = "Worth your attention"


@dataclasses.dataclass
class InsightCardView:
    """One insight, pre-formatted for the page. Mirrors a real ``Insight`` row —
    no card is ever rendered that isn't backed by one (mirrors ``ScoreEventView``'s contract
    in ``dashboard_state.py``)."""

    id: int = 0
    pattern_name: str = ""
    observation: str = ""
    evidence: list[str] = dataclasses.field(default_factory=list)
    explanation: str = ""
    effect: str = ""
    advice: str = ""
    severity: str = "important"
    severity_label: str = ""
    tone: str = "watch"  # 'watch' | 'win' — which band this card belongs to
    icon: str = DEFAULT_ICON
    copilot_href: str = ""  # precomputed here — a foreach render fn can't call quote()


class InsightsState(AuthState):
    """Loads the active insight feed and exposes it as display-ready cards."""

    loaded: bool = False
    cards: list[InsightCardView] = []  # the "watch" band
    win_cards: list[InsightCardView] = []  # the "win" band
    dismissed_cards: list[InsightCardView] = []  # FR-8.4: the collapsed section
    show_dismissed: bool = False
    show_footer_note: bool = False
    insufficient_data: bool = False
    highlight_id: int = 0  # Story 7.4: ?highlight=<id> deep-link from the Dashboard teaser

    @rx.var
    def dismissed_count(self) -> int:
        return len(self.dismissed_cards)

    @rx.var
    def watch_count(self) -> int:
        return len(self.cards)

    @rx.var
    def win_count(self) -> int:
        return len(self.win_cards)

    @rx.var
    def needs_attention_count(self) -> int:
        """How many watch cards are in the top severity tier — the summary chip's whole point
        is to answer "is any of this actually urgent?" before the user reads a single card."""
        return len([c for c in self.cards if c.severity == "critical"])

    @rx.var
    def has_anything(self) -> bool:
        """True when *either* band has content. The empty state must not fire just because
        the watch band is empty — a user with only wins has the best possible feed, and
        telling them "nothing to see" would be precisely backwards."""
        return len(self.cards) > 0 or len(self.win_cards) > 0

    @rx.event
    def toggle_dismissed(self):
        self.show_dismissed = not self.show_dismissed

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
            self.win_cards = [self._to_card(row) for row in data.wins]
            self.dismissed_cards = [self._to_card(row) for row in data.dismissed]
            self.show_footer_note = data.data_months < MIN_DATA_MONTHS_FOOTNOTE
            # FR-8.4: only "insufficient data" when there is genuinely too little to look at.
            # A user with plenty of transactions and an empty feed has simply read them all.
            self.insufficient_data = data.txn_count < MIN_TRANSACTIONS_FOR_INSIGHTS
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
        """Optimistic UI update first (AC #5), then persist the dismissal.

        FR-8.4: the card *moves* to the collapsed dismissed section — it is not destroyed.
        Prepended, because ``_load_dismissed`` returns most-recently-dismissed first and this
        card was just dismissed; that keeps the optimistic order identical to the order the
        next page load will produce from the DB.

        Searches **both** bands: a win is dismissible like anything else (the DB knows nothing
        about bands — ``dismiss_insight`` just flips ``status``), so an optimistic update that
        only swept ``cards`` would leave a dismissed win stranded on screen until reload.
        """
        moved = [
            card
            for card in (*self.cards, *self.win_cards)
            if card.id == insight_id
        ]
        self.cards = [card for card in self.cards if card.id != insight_id]
        self.win_cards = [card for card in self.win_cards if card.id != insight_id]
        self.dismissed_cards = moved + self.dismissed_cards

        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)
            dismiss_insight(session, user.id, insight_id)

    @staticmethod
    def _parse_evidence(raw: str) -> list[str]:
        """FR-8.2's evidence pack → display lines like ``"5 Jul 2026 · Swiggy · ₹450"``.

        Deliberately total: a row whose ``evidence`` column is empty, malformed JSON, the
        wrong shape, or carries an unparseable date/amount yields *fewer* lines (or none) —
        never an exception. The evidence block is a supporting detail; a bad one must degrade
        to a card without it, not blank the whole Insights page. Every ``format*`` helper here
        raises ``ValueError`` on junk, which is exactly why each point is guarded individually.
        """
        if not raw:
            return []
        try:
            points = json.loads(raw)
        except (ValueError, TypeError):
            log.warning("insight evidence is not valid JSON; rendering card without it")
            return []
        if not isinstance(points, list):
            log.warning("insight evidence is not a JSON list; rendering card without it")
            return []

        lines: list[str] = []
        for point in points:
            if not isinstance(point, dict):
                continue
            try:
                parts = [
                    formatDate(point["date"]),
                    str(point["merchant"]).strip(),
                    format_money(Decimal(str(point["amount"]))),
                ]
            except (KeyError, ValueError, TypeError, ArithmeticError):  # incl. InvalidOperation
                log.warning("skipping malformed insight evidence point: %r", point)
                continue
            lines.append(_EVIDENCE_SEP.join(part for part in parts if part))
        return lines

    @classmethod
    def _to_card(cls, row) -> InsightCardView:
        return InsightCardView(
            id=row.id,
            pattern_name=row.pattern_name,
            observation=row.observation,
            evidence=cls._parse_evidence(row.evidence),
            explanation=row.explanation,
            effect=row.effect,
            advice=row.action_suggestion,
            severity=row.severity,
            severity_label=SEVERITY_LABELS.get(row.severity, SEVERITY_LABELS["important"]),
            tone=row.tone,
            icon=PATTERN_ICONS.get(row.pattern_name, DEFAULT_ICON),
            # Story 6.4's receiving side already parses `insight`/`pre` — this story only
            # needs to produce the link (Story 7.3 Dev Notes "Ask Copilot contract").
            copilot_href=f"/copilot?insight={row.id}&pre={quote(row.action_suggestion)}",
        )
