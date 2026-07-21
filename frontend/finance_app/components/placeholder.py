"""Shared placeholder component for the Story 1.1 blank multi-page skeleton.

Each route renders this until its real UI lands in a later epic. Kept in one place
(DRY) so the six skeleton pages stay identical and trivially replaceable.
"""

import reflex as rx


def coming_soon(page_name: str) -> rx.Component:
    """A minimal, centered placeholder for a not-yet-built page."""
    return rx.center(
        rx.vstack(
            rx.heading(page_name, size="7"),
            rx.text("Coming soon", color_scheme="gray"),
            spacing="3",
            align="center",
        ),
        min_height="85vh",
    )
