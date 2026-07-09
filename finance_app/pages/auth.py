"""Auth page (register / login). Real UI lands in Epic 1 Stories 1.3-1.5."""

import reflex as rx

from finance_app.components.placeholder import coming_soon


@rx.page(route="/", title="Sign in · Finance Analyzer")
def auth() -> rx.Component:
    return coming_soon("Sign in")
