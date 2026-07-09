"""Insights page. Real UI lands in Epic 7 Story 7.3."""

import reflex as rx

from finance_app.components.placeholder import coming_soon


@rx.page(route="/insights", title="Insights · Finance Analyzer")
def insights() -> rx.Component:
    return coming_soon("Insights")
