"""Transactions page. Real UI lands in Epic 3 Stories 3.1/3.4."""

import reflex as rx

from finance_app.components.placeholder import coming_soon


@rx.page(route="/transactions", title="Transactions · Finance Analyzer")
def transactions() -> rx.Component:
    return coming_soon("Transactions")
