"""Insights page. Real UI lands in Epic 7 Story 7.3."""

import reflex as rx

from finance_app.components.placeholder import coming_soon
from finance_app.state.auth_state import AuthState


@rx.page(route="/insights", title="Insights · Finance Analyzer", on_load=AuthState.check_auth)
def insights() -> rx.Component:
    return coming_soon("Insights")
