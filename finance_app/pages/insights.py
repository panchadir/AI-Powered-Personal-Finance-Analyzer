"""Insights page — insight cards, dismiss lifecycle (Story 7.3 / FR-8.2, FR-8.4, FR-8.5).

Ported from the WDS prototype ``01.6-ai-insights-recommendations.html``: same class names,
already compiled into ``assets/wds.css`` (no new CSS). Two deliberate divergences from the
prototype (see the story's Dev Notes): dismiss is a hard removal, not the prototype's
fade-toggle; the footer uses the PRD/epics exact copy, not the prototype's placeholder text.
No severity-tier color/badge treatment exists in the prototype's CSS — ordering only (AC #3).
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.insights_state import EMPTY_COPY, FOOTER_NOTE, InsightsState


def _insight_card(card: rx.Var) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.span("💡", class_name="insight-icon", aria_hidden="true"),
            rx.el.h2(card.pattern_name, class_name="insight-name"),
            class_name="insight-card-head",
        ),
        rx.el.p(card.observation, class_name="insight-observation"),
        rx.el.p(card.explanation, class_name="insight-explanation"),
        rx.el.p(card.effect, class_name="insight-explanation"),
        rx.el.p(card.advice, class_name="insight-explanation"),
        rx.el.div(
            rx.el.button(
                "Dismiss",
                on_click=InsightsState.dismiss(card.id),
                class_name="insight-dismiss",
                aria_label="Dismiss: " + card.pattern_name,
                type="button",
            ),
            rx.el.a(
                "Ask the Copilot about this",
                href=card.copilot_href,
                class_name="btn btn--secondary",
            ),
            class_name="insight-actions",
        ),
        class_name="insight-card",
        role="article",
        id="insight-" + card.id.to_string(),  # Story 7.4: Dashboard teaser scroll target
    )


def _empty_state() -> rx.Component:
    """FR-8.4: graceful copy, never a blank page or "No insights" placeholder tone."""
    return rx.el.p(EMPTY_COPY, class_name="insights-subline")


def _footer() -> rx.Component:
    return rx.cond(
        InsightsState.show_footer_note,
        rx.el.div(rx.el.p(FOOTER_NOTE, id="insights-footer-note"), class_name="insights-footer"),
    )


@rx.page(
    route="/insights",
    title="Insights · Finance Analyzer",
    on_load=[InsightsState.check_auth, InsightsState.load_insights],
)
def insights() -> rx.Component:
    return rx.fragment(
        side_nav("insights"),
        rx.el.main(
            rx.el.div(
                rx.el.h1("What we noticed", class_name="insights-headline"),
                rx.el.p(
                    "These are patterns in your data — not judgments. We share what we see, "
                    "you decide what to do.",
                    class_name="insights-subline",
                ),
                class_name="insights-header",
                id="insights-header",
            ),
            rx.cond(
                InsightsState.cards.length() > 0,
                rx.el.div(
                    rx.foreach(InsightsState.cards, _insight_card),
                    class_name="insights-list",
                    id="insights-list",
                ),
                rx.cond(InsightsState.loaded, _empty_state(), rx.el.div()),
            ),
            _footer(),
            class_name="has-sidenav",
        ),
    )
