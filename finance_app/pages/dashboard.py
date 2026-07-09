"""Dashboard page (hero card, briefing, charts). Real UI lands in Epic 5."""

import reflex as rx

from finance_app.components.placeholder import coming_soon


@rx.page(route="/dashboard", title="Dashboard · Finance Analyzer")
def dashboard() -> rx.Component:
    return coming_soon("Dashboard")
