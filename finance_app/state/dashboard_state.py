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
import datetime
import logging
import math

import plotly.graph_objects as go
import reflex as rx

from finance_app.state.auth_state import LOGIN_ROUTE, AuthState, user_for_token
from finance_app.state.engine_bridge import (
    compute_dashboard,
    confidence_label,
    confidence_variant,
    format_day,
    format_money,
    humanize_since,
    load_commitments,
    load_transactions,
    recent_score_events,
    sync_confidence_score,
)
# NOTE: the dashboard deliberately reads no insight data. The Story 7.4 teaser card was
# removed on 2026-07-12 (product decision) — the briefing card's "See my insights" button is
# the dashboard's only route into Insights. `insights_bridge.top_active_insight` remains for
# FR-8.6's briefing sentence, which does not go through this state.
from services.analytics import CategorySlice, MonthPoint, monthly_spend, spending_by_category
from services.engine import resolve_due_date
from services.narrate import BriefingContext, generate_briefing
from services.utils.format import formatINR

log = logging.getLogger(__name__)

#: Empty-state copy (UX-DR12). Not "No data available".
EMPTY_HERO_COPY = "Upload a statement and I'll show you what's safe to spend — and why."

#: Shown when the engine can't explain the figure from real data (Story 5.1 fallback).
WHY_FALLBACK = "We don't have enough data yet to fully explain this."

#: Minimum time the skeleton loader stays on screen. A hair under a second: long enough that
#: the loading state registers as intentional rather than a flicker, short enough that it never
#: feels like a stall on a fast load. Shared by the dashboard, transactions and insights loads.
_LOADER_MIN_SECONDS = 0.8


@dataclasses.dataclass
class ScoreEventView:
    """One row of the Confidence Score drill-in panel. Mirrors a real ``score_events`` row."""

    delta: str = ""  # "+4" / "-3" — signed, already formatted
    explanation: str = ""
    when: str = ""  # "2 hours ago"


@dataclasses.dataclass
class TimelineView:
    """One row of the upcoming-commitments timeline (Story 5.4 AC)."""

    due: str = ""  # formatDate'd next occurrence, e.g. "05 Aug 2026"
    name: str = ""
    amount: str = ""  # formatINR'd
    tier: str = ""  # criticality label: "Critical" / "Important" / "Flexible"


#: A calm, evidence-not-headline palette for the donut (UX-DR1: charts support, never shout).
_CHART_COLORS = (
    "#4f46e5", "#0ea5e9", "#14b8a6", "#f59e0b",
    "#ec4899", "#8b5cf6", "#10b981", "#64748b",
)
_INK = "#334155"

#: WDS warm accent — the ``--accent`` gold in ``assets/wds.css``. The monthly-pace bars use it
#: (not the ``--primary`` teal) so they stay on-brand while reading as distinct from the teal
#: buttons/chips/nav — a chart in the same colour as every button loses its visual separation.
_PACE_BAR_COLOR = "#e0a63c"

#: Fraction of each x-slot left empty between bars — a high gap renders slim, calm bars rather
#: than chunky blocks (UX-DR1: the chart supports the hero figure, it doesn't shout).
_PACE_BAR_GAP = 0.6


def _nice_ceiling(value: float) -> float:
    """Round ``value`` up to a clean 1/2/2.5/5/10 × power-of-ten, for readable y-axis ticks."""
    if value <= 0:
        return 0.0
    magnitude = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 2.5, 5, 10):
        if value <= step * magnitude:
            return step * magnitude
    return 10 * magnitude


def _empty_figure() -> go.Figure:
    """A blank figure used as the state default and when there is nothing to plot."""
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=8, b=8),
    )
    return fig


def _category_figure(slices: list[CategorySlice]) -> go.Figure:
    """Donut of debit spend by category. Every rupee shown is ``formatINR``'d (NFR-7).

    Slice labels carry the category name only; the exact amount rides in the hover via
    ``formatINR`` — a raw ``125000.0`` on a label would fail acceptance (Story 5.4 AC).
    """
    fig = go.Figure(
        go.Pie(
            labels=[s.category for s in slices],
            values=[float(s.total) for s in slices],
            text=[formatINR(s.total) for s in slices],
            hole=0.58,
            sort=False,  # keep the analytics' largest-first order → stable colour mapping
            marker=dict(colors=list(_CHART_COLORS)),
            textinfo="label",
            hovertemplate="%{label}<br>%{text} · %{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, x=0.5, xanchor="center"),
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=_INK, size=12),
        height=320,
    )
    return fig


def _month_label(month: str) -> str:
    """``'2026-06'`` → ``'Jun 2026'`` for the x-axis (display only, not a rupee)."""
    return datetime.datetime.strptime(month, "%Y-%m").strftime("%b %Y")


def _pace_figure(points: list[MonthPoint]) -> go.Figure:
    """Monthly spend as a bar trend. Y-axis tick *values* are ``formatINR``'d (Story 5.4 AC).

    Plotly's default axis would print ``125000``; the AC requires Indian grouping, so the tick
    labels are explicit ``formatINR`` strings and the exact bar total rides in the hover.
    """
    fig = go.Figure(
        go.Bar(
            x=[_month_label(p.month) for p in points],
            y=[float(p.total) for p in points],
            customdata=[formatINR(p.total) for p in points],
            marker_color=_PACE_BAR_COLOR,
            hovertemplate="%{x}<br>%{customdata}<extra></extra>",
        )
    )

    top = _nice_ceiling(max((float(p.total) for p in points), default=0.0))
    tickvals = [top * i / 4 for i in range(5)] if top > 0 else []
    fig.update_layout(
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=_INK, size=12),
        showlegend=False,
        height=320,
        bargap=_PACE_BAR_GAP,  # slimmer bars — the chart supports, never shouts (UX-DR1)
        yaxis=dict(
            tickvals=tickvals,
            ticktext=[formatINR(v) for v in tickvals],
            gridcolor="rgba(100,116,139,0.15)",
        ),
        xaxis=dict(showgrid=False),
    )
    return fig


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

    # --- Insight teaser (Story 7.4) ---

    # --- Charts & timeline (Story 5.4) — below the fold, supporting evidence (UX-DR1) ---
    has_charts: bool = False
    category_fig: go.Figure = _empty_figure()
    pace_fig: go.Figure = _empty_figure()
    timeline: list[TimelineView] = []

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
        # Show the skeleton only on the *first* load of the session. On a revisit the state
        # still holds the previous data, so forcing the skeleton here would flash the page
        # data → loader → data. When nothing is loaded yet the skeleton is already on screen
        # (loaded defaults False); hold it a beat so it reads as a deliberate loading moment
        # rather than a flicker on a fast local DB. A revisit just refreshes the data in place.
        if not self.loaded:
            yield
            await asyncio.sleep(_LOADER_MIN_SECONDS)

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
            # Below-the-fold supporting evidence (Story 5.4). Built from the same rows the
            # engine ran on, so the charts can never disagree with the hero figure.
            self._apply_charts(load_transactions(session, user.id))
            self._apply_timeline(
                load_commitments(session, user.id), as_of=data.statement_end_date
            )
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
        self.has_charts = False
        self.category_fig = _empty_figure()
        self.pace_fig = _empty_figure()
        self.timeline = []

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
                # Story 8.1 AC3: approved copy for the no-income-detected state.
                self.after_income_label = (
                    "Upload your payday date so I can calculate your daily safe-to-spend."
                )

        # Label only. The `score` int stays on the server (FR-5.5 / UX-DR2).
        self.confidence_label = confidence_label(score)
        self.confidence_variant = confidence_variant(score)
        self.prediction_confidence = evidence.prediction_confidence
        self.prediction_reason = _PREDICTION_REASONS.get(
            evidence.prediction_confidence, _PREDICTION_REASONS["Low"]
        )

        # "Why?" traces to real engine drivers; the fallback is honest about not knowing.
        self.why_text = " ".join(evidence.drivers) if evidence.drivers else WHY_FALLBACK

    def _apply_charts(self, transactions) -> None:
        """Build the donut and pace figures from real debits (Story 5.4).

        Aggregation is done in ``services/analytics`` (Decimal, unit-tested); this only turns
        those numbers into figures and formats them. ``has_charts`` gates the whole below-fold
        section so a statement with no debits shows nothing rather than an empty axis.
        """
        slices = spending_by_category(transactions)
        points = monthly_spend(transactions)
        self.has_charts = bool(slices)
        self.category_fig = _category_figure(slices) if slices else _empty_figure()
        self.pace_fig = _pace_figure(points) if points else _empty_figure()

    def _apply_timeline(self, commitments, *, as_of) -> None:
        """Upcoming commitments, soonest first, with each one's next due date (Story 5.4 AC)."""
        anchor = as_of or datetime.date.today()
        rows = [
            (resolve_due_date(c.due_day, anchor), c)
            for c in commitments
        ]
        rows.sort(key=lambda pair: pair[0])
        self.timeline = [
            TimelineView(
                due=format_day(due_date),
                name=c.name,
                amount=format_money(c.amount),
                tier=c.criticality.capitalize(),
            )
            for due_date, c in rows
        ]

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
