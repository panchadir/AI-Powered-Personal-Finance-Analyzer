"""Dashboard page (hero card, briefing, charts). Real UI lands in Epic 5."""

import reflex as rx

from finance_app.components.placeholder import coming_soon
from finance_app.state.auth_state import AuthState


@rx.page(route="/dashboard", title="Dashboard · Finance Analyzer", on_load=AuthState.check_auth)
def dashboard() -> rx.Component:
    return coming_soon("Dashboard")
