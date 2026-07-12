"""Insights page state (Story 8.2 — onboarding empty state).

Thin state that checks for transactions. Story 7.3 will extend this with the
full insight lifecycle (dismissed/active rows, detector triggers).

AD-4: every DB query carries an explicit ``user_id`` filter.
"""
from __future__ import annotations

import reflex as rx
from sqlmodel import func, select

from finance_app.models import Transaction
from finance_app.state.auth_state import LOGIN_ROUTE, AuthState, user_for_token


class InsightsState(AuthState):
    """Minimal state for the Insights page empty-state (Story 8.2)."""

    loaded: bool = False
    has_data: bool = False

    @rx.event
    async def load_page(self):
        """Check for the presence of any transactions for this user (AD-4)."""
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                yield rx.redirect(LOGIN_ROUTE)
                return

            count = session.exec(
                select(func.count()).select_from(Transaction).where(
                    Transaction.user_id == user.id
                )
            ).one()
            self.has_data = count > 0
            self.loaded = True
