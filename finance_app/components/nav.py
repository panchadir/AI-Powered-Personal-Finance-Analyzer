"""Persistent left sidebar navigation.

Mirrors the prototype's ``nav.js``/``renderSideNav`` exactly:
- 4 tabs: Dashboard, Transactions, Insights, Copilot Chat
- Active tab gets ``.is-active`` + ``aria-current="page"``
- Log out pinned at the bottom via ``.side-nav__logout``
- Commitments is intentionally absent (FR-6.4 / nav.js comment: reached via Dashboard)

Usage in a page::

    from finance_app.components.nav import side_nav
    ...
    rx.el.div(
        side_nav("dashboard"),
        rx.el.main(..., class_name="has-sidenav"),
    )

``active`` must be one of: ``"dashboard"`` | ``"transactions"`` | ``"insights"`` | ``"copilot"``.
"""
from __future__ import annotations

import reflex as rx

from finance_app.state.auth_state import AuthState

_TABS = [
    ("dashboard",    "Dashboard",    "📊", "/dashboard"),
    ("transactions", "Transactions", "📄", "/transactions"),
    ("insights",     "Insights",     "💡", "/insights"),
    ("copilot",      "Copilot Chat", "💬", "/copilot"),
]


def _tab(key: str, label: str, icon: str, href: str, active: str) -> rx.Component:
    is_active = key == active
    return rx.el.a(
        rx.el.span(icon, class_name="ico", aria_hidden="true"),
        rx.el.span(label, class_name="label"),
        href=href,
        class_name="side-nav__tab" + (" is-active" if is_active else ""),
        aria_current="page" if is_active else None,
    )


def side_nav(active: str) -> rx.Component:
    """Render the fixed left sidebar with the 4 primary nav tabs + logout.

    ``active``: the tab key for the current page (sets ``.is-active`` + ``aria-current``).
    """
    tabs = [_tab(key, label, icon, href, active) for key, label, icon, href in _TABS]
    logout_btn = rx.el.button(
        rx.el.span("⏻", class_name="ico", aria_hidden="true"),
        rx.el.span("Log out", class_name="label"),
        on_click=AuthState.logout,
        class_name="side-nav__tab side-nav__logout",
        type="button",
    )
    return rx.el.nav(
        *tabs,
        logout_btn,
        class_name="side-nav",
        aria_label="Primary",
    )
