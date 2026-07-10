"""Insights page. Real UI lands in Epic 7 Story 7.3."""

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.auth_state import AuthState


@rx.page(route="/insights", title="Insights · Finance Analyzer", on_load=AuthState.check_auth)
def insights() -> rx.Component:
    return rx.fragment(
        side_nav("insights"),
        rx.el.main(
            rx.vstack(
                rx.heading("Insights", size="7"),
                rx.text("Coming soon", color_scheme="gray"),
                spacing="3",
                align="center",
                min_height="85vh",
                justify="center",
            ),
            class_name="has-sidenav",
        ),
    )
