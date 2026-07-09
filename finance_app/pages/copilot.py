"""Copilot chat page. Real UI lands in Epic 6."""

import reflex as rx

from finance_app.components.placeholder import coming_soon


@rx.page(route="/copilot", title="Copilot · Finance Analyzer")
def copilot() -> rx.Component:
    return coming_soon("Copilot")
