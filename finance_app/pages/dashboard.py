"""Dashboard page (hero card, briefing, charts). Real UI lands in Epic 5."""

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.auth_state import AuthState


@rx.page(route="/dashboard", title="Dashboard · Finance Analyzer", on_load=AuthState.check_auth)
def dashboard() -> rx.Component:
    return rx.fragment(
        side_nav("dashboard"),
        rx.el.main(
            rx.vstack(
                rx.heading("Dashboard", size="7"),
                rx.text("Coming soon", color_scheme="gray"),
                spacing="3",
                align="center",
                min_height="85vh",
                justify="center",
            ),
            class_name="has-sidenav",
        ),
    )
