"""Skeleton loading placeholders — the financial-dashboard "shimmer" loading state.

Shown before a page's data arrives so the UI never flashes blank (UX requirement:
"the UI never appears blank while data is loading") and never shows an empty-state
"no data" message while data is in fact still loading.

Every placeholder is built from the same ``:root`` tokens and the shared
``@keyframes insight-shimmer`` animation that the Insights skeleton already uses, so
the whole app's loading state reads as one system rather than a bag of ad-hoc
spinners. No generic spinner is used — each placeholder mirrors the *shape* of the
real content it stands in for (hero card, cards, charts, list rows).

Accessibility: each skeleton root carries ``role="status"``/``aria-busy`` with a
human label so a screen reader announces "Loading …" once; the individual shimmer
bars are ``aria-hidden`` so they are not read as empty boxes.
"""
from __future__ import annotations

import reflex as rx


def _bar(class_name: str, width: str | None = None) -> rx.Component:
    """One shimmer bar. ``width`` overrides the class default when given."""
    return rx.el.div(
        class_name=class_name,
        style={"width": width} if width else None,
        aria_hidden="true",
    )


# ---------------------------------------------------------------------------
# Safe-to-Spend hero (Dashboard)
# ---------------------------------------------------------------------------

def sts_skeleton() -> rx.Component:
    """Safe-to-Spend hero placeholder — mirrors ``.hero-card``'s two-column shape."""
    return rx.el.section(
        rx.el.div(
            _bar("skeleton skeleton-line", "35%"),
            _bar("skeleton skeleton-amount"),
            _bar("skeleton skeleton-line skeleton-line--sm", "55%"),
            class_name="hero-primary",
        ),
        rx.el.hr(class_name="hero-sep"),
        rx.el.div(
            _bar("skeleton skeleton-line", "45%"),
            _bar("skeleton skeleton-chip"),
            _bar("skeleton skeleton-line skeleton-line--sm", "40%"),
            class_name="hero-secondary",
        ),
        class_name="hero-card skeleton-hero",
        aria_hidden="true",
    )


# ---------------------------------------------------------------------------
# Generic card + chart placeholders (Dashboard grid)
# ---------------------------------------------------------------------------

_LINE_WIDTHS = ["100%", "92%", "70%", "85%", "60%"]


def card_skeleton(lines: int = 3, with_button: bool = False) -> rx.Component:
    """A ``.dash-card`` placeholder: a title bar, a few text lines, optional button."""
    body: list[rx.Component] = [_bar("skeleton skeleton-title")]
    body += [
        _bar("skeleton skeleton-line", _LINE_WIDTHS[i % len(_LINE_WIDTHS)])
        for i in range(lines)
    ]
    if with_button:
        body.append(_bar("skeleton skeleton-btn"))
    return rx.el.section(*body, class_name="dash-card skeleton-card", aria_hidden="true")


def chart_skeleton() -> rx.Component:
    """A ``.dash-card`` placeholder shaped like one of the dashboard charts."""
    return rx.el.section(
        _bar("skeleton skeleton-title"),
        _bar("skeleton skeleton-chart"),
        class_name="dash-section dash-card skeleton-card",
        aria_hidden="true",
    )


def dashboard_skeleton() -> rx.Component:
    """Whole-dashboard loading state: hero + briefing/commitments row + charts row."""
    return rx.el.div(
        sts_skeleton(),
        rx.el.div(
            card_skeleton(3, with_button=True),
            card_skeleton(4),
            class_name="dash-grid",
        ),
        rx.el.div(
            chart_skeleton(),
            chart_skeleton(),
            class_name="dash-grid",
        ),
        class_name="dash-skeleton",
        role="status",
        aria_busy="true",
        aria_label="Loading your dashboard",
    )


# ---------------------------------------------------------------------------
# Transactions list
# ---------------------------------------------------------------------------

def _txn_row_skeleton() -> rx.Component:
    return rx.el.li(
        rx.el.div(
            class_name="skeleton skeleton-circle",
            style={"width": "36px", "height": "36px"},
            aria_hidden="true",
        ),
        rx.el.div(
            _bar("skeleton skeleton-line", "45%"),
            _bar("skeleton skeleton-line skeleton-line--sm", "28%"),
            class_name="txn-skeleton-meta",
        ),
        _bar("skeleton skeleton-line", "64px"),
        class_name="txn-row txn-row--skeleton",
    )


def txn_skeleton(rows: int = 6) -> rx.Component:
    """Transactions loading state: a filter-chip row + placeholder list rows."""
    return rx.el.div(
        rx.el.div(
            *[_bar("skeleton skeleton-chip") for _ in range(4)],
            class_name="chip-group chip--wrap",
            aria_hidden="true",
        ),
        rx.el.ul(
            *[_txn_row_skeleton() for _ in range(rows)],
            class_name="txn-list",
            aria_hidden="true",
        ),
        class_name="txn-skeleton",
        role="status",
        aria_busy="true",
        aria_label="Loading your transactions",
    )