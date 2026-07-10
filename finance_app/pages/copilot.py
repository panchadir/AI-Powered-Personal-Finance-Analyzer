"""Copilot chat page. Real UI lands in Epic 6."""

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.auth_state import AuthState


@rx.page(route="/copilot", title="Copilot · Finance Analyzer", on_load=AuthState.check_auth)
def copilot() -> rx.Component:
    return rx.fragment(
        side_nav("copilot"),
        rx.el.main(
            rx.vstack(
                rx.heading("Copilot Chat", size="7"),
                rx.text("Coming soon", color_scheme="gray"),
                spacing="3",
                align="center",
                min_height="85vh",
                justify="center",
            ),
            class_name="has-sidenav",
        ),
    )
