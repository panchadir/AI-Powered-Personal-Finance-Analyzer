"""Insights page.

Story 8.2: welcoming empty state for first-time users (AC-3).
Real insight cards (detector output, dismiss lifecycle) land in Epic 7 Story 7.3.
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.insights_state import InsightsState


def _empty_state() -> rx.Component:
    """No data yet — direct the user to upload (Story 8.2 AC-3).

    Copy is exact from epics.md; changing it fails acceptance.
    """
    return rx.el.section(
        rx.el.p(
            "Insights will appear once I've analysed your statement.",
            class_name="hero-label",
        ),
        rx.el.a(
            "Upload your statement",
            href="/upload",
            class_name="btn btn--primary",
        ),
        class_name="hero-card",
    )


def _placeholder() -> rx.Component:
    """Stub content shown when data exists but Epic 7 UI is not yet built."""
    return rx.vstack(
        rx.heading("Insights", size="7"),
        rx.text(
            "Insight cards coming soon — your patterns are being analysed.",
            color_scheme="gray",
        ),
        spacing="3",
        align="center",
        min_height="50vh",
        justify="center",
    )


@rx.page(
    route="/insights",
    title="Insights · Finance Analyzer",
    on_load=[InsightsState.check_auth, InsightsState.load_page],
)
def insights() -> rx.Component:
    return rx.fragment(
        side_nav("insights"),
        rx.el.main(
            rx.cond(
                InsightsState.has_data,
                _placeholder(),
                rx.cond(InsightsState.loaded, _empty_state(), rx.el.div()),
            ),
            class_name="has-sidenav",
        ),
    )
