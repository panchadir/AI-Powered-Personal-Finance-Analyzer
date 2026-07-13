"""Dashboard page — hero card, confidence chip, drill-in, briefing (Stories 5.1, 5.2, 5.3).

Ported from the WDS prototype ``01.5-dashboard.html``: same DOM shape, same class names, so
``assets/wds.css`` styles it without a new stylesheet. Charts (Story 5.4) sit below the fold
and land once Epic 3 fills in transaction categories.

Layout contract (UX-DR1 / FR-6.1): the Safe-to-Spend card and Confidence chip are the first
elements in the tree, above the fold, before anything else. Nothing may be inserted above the
hero card.
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.dashboard_state import DashboardState


def _stale_banner() -> rx.Component:
    """Amber re-upload prompt when the statement is >30 days old (FR-5.7 / UX-DR15).

    Amber, not error-red: stale data is a nudge, not a failure.
    """
    return rx.cond(
        DashboardState.is_stale,
        rx.el.div(
            rx.el.span(class_name="dot", aria_hidden="true"),
            rx.el.span(
                "This statement is more than 30 days old. Upload a newer one and I'll "
                "sharpen these figures."
            ),
            class_name="banner",
            role="status",
        ),
    )


def _confidence_chip() -> rx.Component:
    """Label-only chip + its drill-in panel (Story 5.2 / FR-5.5 / UX-DR2).

    The raw 0–100 score is not in state, so it cannot be rendered here even by mistake.
    """
    return rx.el.div(
        rx.el.span("Confidence", class_name="hero-conf-label"),
        rx.el.button(
            DashboardState.confidence_label,
            on_click=DashboardState.toggle_drillin,
            class_name="conf-chip conf-chip--" + DashboardState.confidence_variant,
            aria_label="Confidence: "
            + DashboardState.confidence_label
            + " — tap to see what changed it",
            aria_expanded=DashboardState.drillin_open.to_string(),
            type="button",
        ),
        rx.cond(
            DashboardState.drillin_open,
            rx.el.div(
                rx.el.p(
                    DashboardState.prediction_confidence
                    + " — "
                    + DashboardState.prediction_reason,
                    class_name="conf-drillin-summary",
                ),
                rx.el.ul(
                    rx.foreach(DashboardState.score_events, _score_event_row),
                    class_name="conf-drillin-events",
                ),
                class_name="conf-drillin",
                role="dialog",
                aria_label="Confidence Score history",
            ),
        ),
        class_name="hero-conf",
    )


def _score_event_row(event) -> rx.Component:
    """One real ``score_events`` row. No row is rendered that isn't backed by one."""
    return rx.el.li(
        rx.el.span(event.delta, class_name="conf-drillin-delta"),
        rx.el.span(
            rx.el.span(event.explanation, class_name="conf-drillin-explanation"),
            rx.el.span(event.when, class_name="conf-drillin-when"),
            class_name="conf-drillin-body",
        ),
        class_name="conf-drillin-event",
    )


def _hero_card() -> rx.Component:
    """Safe-to-Spend, freshness caveat, second layer, confidence chip, "Why?" (Story 5.1)."""
    return rx.el.section(
        rx.el.div(
            rx.el.p("Safe to spend today", class_name="hero-label"),
            rx.el.p(
                DashboardState.safe_to_spend_today,
                class_name="hero-amount",
                aria_label="Safe to spend today: " + DashboardState.safe_to_spend_today,
            ),
            # FR-4.7 / UX-DR4: the caveat lives on the card, not in a footer or tooltip.
            rx.el.p(DashboardState.freshness_caveat, class_name="hero-freshness"),
            # Two distinct honest states, never conflated (UX-DR11). A shortfall means the bills
            # cannot be paid; a dented buffer means they can, but the emergency cushion is being
            # spent. Saying the first when only the second is true would be a false alarm.
            rx.cond(
                DashboardState.shortfall,
                rx.el.p(
                    "Your committed bills before payday come to more than your balance. "
                    "Here's what I'd protect first.",
                    class_name="hero-freshness",
                    role="status",
                ),
            ),
            rx.cond(
                DashboardState.buffer_dented,
                rx.el.p(
                    "Your bills are covered, but paying them dips into your emergency buffer.",
                    class_name="hero-freshness",
                    role="status",
                ),
            ),
            class_name="hero-primary",
        ),
        rx.el.hr(class_name="hero-sep"),
        rx.el.div(
            # The second STS layer is its own row — never merged with today's figure (FR-4.5).
            rx.el.div(
                rx.el.span(DashboardState.after_income_label, class_name="hero-after-label"),
                rx.cond(
                    DashboardState.has_income,
                    rx.el.span(
                        DashboardState.after_income_amount, class_name="hero-after-amount"
                    ),
                ),
                class_name="hero-after",
            ),
            _confidence_chip(),
            rx.el.div(
                rx.el.button(
                    "Show me why",  # UX-DR17: not "View details"
                    on_click=DashboardState.toggle_why,
                    class_name="hero-why-trigger",
                    aria_expanded=DashboardState.why_open.to_string(),
                    aria_controls="dashboard-hero-why-content",
                    type="button",
                ),
                rx.cond(
                    DashboardState.why_open,
                    rx.el.p(
                        DashboardState.why_text,
                        id="dashboard-hero-why-content",
                        class_name="hero-why-content",
                    ),
                ),
                class_name="hero-why",
            ),
            class_name="hero-secondary",
        ),
        class_name="hero-card",
    )


def _briefing_card() -> rx.Component:
    """The narrated briefing (Story 5.3). A snapshot; the hero above it is live (FR-4.11).

    Its "See my insights" button is the dashboard's *only* route into the Insights page, and
    the only insight-related surface on the dashboard at all (product decision, 2026-07-12):
    the Story 7.4 teaser card was removed because two cards pointing at Insights read as two
    destinations. Do not reintroduce an insight card here.
    """
    return rx.el.section(
        rx.cond(
            DashboardState.briefing_loading,
            rx.el.p("Writing your briefing…", class_name="briefing-text"),
            rx.el.p(DashboardState.briefing, class_name="briefing-text"),
        ),
        rx.el.button(
            "See my insights →",
            on_click=rx.redirect("/insights"),
            class_name="btn btn--primary",
            type="button",
        ),
        class_name="briefing-card dash-card",
    )


def _timeline_row(item) -> rx.Component:
    """One upcoming commitment: next due date, name, amount, criticality tier (Story 5.4 AC)."""
    return rx.el.li(
        rx.el.span(item.due, class_name="tl-date"),
        rx.el.span(
            item.name,
            rx.el.span(item.tier, class_name="tl-tag"),
            class_name="tl-name",
        ),
        rx.el.span(item.amount, class_name="tl-amt"),
    )


def _commitments_card() -> rx.Component:
    """Upcoming-commitments timeline + "+ Add a commitment" (Story 5.4 / FR-6.5).

    "+ Add a commitment" routes to the dedicated page (FR-6.5), not an inline modal.
    """
    return rx.el.section(
        rx.el.h2("Upcoming commitments"),
        rx.cond(
            DashboardState.timeline,
            rx.el.ul(
                rx.foreach(DashboardState.timeline, _timeline_row),
                class_name="timeline",
            ),
            rx.el.p(
                "Your protected bills and EMIs, and what they leave you.",
                class_name="txn-cta-text",
            ),
        ),
        rx.el.button(
            "+ Add a commitment",
            on_click=DashboardState.go_commitments,
            class_name="btn btn--primary add-commitment",
            type="button",
        ),
        class_name="dash-section dash-card",
    )


def _charts_section() -> rx.Component:
    """Below-the-fold supporting charts (Story 5.4 / UX-DR1): spending donut + monthly pace.

    Rendered *after* the hero and briefing, never above the fold — these are evidence, not the
    headline. Hidden entirely when the statement has no debits to plot.
    """
    return rx.cond(
        DashboardState.has_charts,
        rx.el.div(
            rx.el.section(
                rx.el.h2("Where your money went"),
                rx.plotly(data=DashboardState.category_fig, class_name="dash-chart"),
                class_name="dash-section dash-card",
            ),
            rx.el.section(
                rx.el.h2("Your monthly pace"),
                rx.plotly(data=DashboardState.pace_fig, class_name="dash-chart"),
                class_name="dash-section dash-card",
            ),
            class_name="dash-grid",
        ),
    )


def _empty_state() -> rx.Component:
    """First-time user: welcoming and action-directing, never "No data available" (UX-DR12)."""
    return rx.el.section(
        rx.el.p(
            "Upload a statement and I'll show you what's safe to spend — and why.",
            class_name="hero-label",
        ),
        rx.el.button(
            "Upload your statement",
            on_click=DashboardState.go_upload,
            class_name="btn btn--primary",
            type="button",
        ),
        class_name="hero-card",
    )


@rx.page(
    route="/dashboard",
    title="Dashboard · Finance Analyzer",
    on_load=[DashboardState.check_auth, DashboardState.load_dashboard],
)
def dashboard() -> rx.Component:
    return rx.fragment(
        side_nav("dashboard"),
        rx.el.main(
            rx.cond(
                DashboardState.has_data,
                rx.fragment(
                    _stale_banner(),
                    _hero_card(),
                    rx.el.div(
                        _briefing_card(),
                        _commitments_card(),
                        class_name="dash-grid",
                    ),
                    _charts_section(),
                ),
                rx.cond(DashboardState.loaded, _empty_state(), rx.el.div()),
            ),
            class_name="dash dash--sidenav has-sidenav",
        ),
    )
