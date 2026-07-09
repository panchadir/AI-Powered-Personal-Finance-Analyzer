"""Upload page (Step 1 of 3). Real UI lands in Epic 2 Story 2.4."""

import reflex as rx

from finance_app.components.placeholder import coming_soon


@rx.page(route="/upload", title="Upload · Finance Analyzer")
def upload() -> rx.Component:
    return coming_soon("Upload")
