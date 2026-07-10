"""Transactions page state (Story 3.1), rebuilt against WDS prototype ``01.4-transactions-table.html``.

Loads the signed-in user's transactions (AD-4: explicit ``user_id`` filter), formats them
through ``formatINR``/``formatDate`` (AD-13), and derives the filter-chip bar and the
"needs review" badge/banner state the prototype's JS computes client-side.

This story does not build the Teach Me correction panel (Story 3.3) or the confidence-badge
threshold logic (Story 3.4, once Tier-2 exists) — only two badge states are reachable here:
a full-confidence rule match (no badge) and an unmatched/low-confidence row (amber "?" badge).

Code-review follow-up (2026-07-10): the chip/filter derivation (``needs_review_count``,
``distinct_categories``, ``build_chip_items``, ``filter_rows``) was pulled out into plain,
session-free pure functions — same treatment ``_to_row``/``load_user_transaction_rows``
already had — so AC #6's chip/filter behavior is unit-testable without a running Reflex app
(a review found this logic had zero test coverage; ``reflex compile`` proves the component
tree builds, but never executes this branching). Row-building is also now defensive: a
malformed DB row (bad date/amount) is skipped with a logged warning instead of raising and
failing the whole page load — not reachable via the current ingestion path (parsers validate
first), but a real robustness gap the review flagged.
"""
from __future__ import annotations

import logging

import reflex as rx
from pydantic import BaseModel
from sqlmodel import select

from finance_app.models import Transaction as TxnModel
from finance_app.state.auth_state import AuthState
from services.categorize.schema import UNCATEGORIZED
from services.utils.format import formatDate, formatINR

log = logging.getLogger(__name__)

#: Rows with confidence below this are shown with the amber "?" needs-review badge. Every
#: Tier-1 rule match is confidence 1.0; the engine's unrecognized-credit fallback is 0.5 and
#: an unmatched row is 0.0 — both count as "needs review" until Tier-2 (Story 3.2) exists.
NEEDS_REVIEW_THRESHOLD = 1.0

ALL_KEY = "all"
NEEDS_REVIEW_KEY = "needs_review"

#: Category glyphs, keyed to the taxonomy in ``services/categorize/schema.py`` (the ~90-rule
#: engine's own categories, not the WDS prototype's narrower 9 — see schema.py's docstring).
_CATEGORY_ICON: dict[str, str] = {
    "Food & Dining": "🍽️",
    "Groceries": "🛒",
    "Shopping": "🛍️",
    "Entertainment": "🎬",
    "Travel & Transport": "🚌",
    "Health & Medical": "🩺",
    "Utilities": "💡",
    "Mobile & Recharge": "📱",
    "Insurance": "🛡️",
    "Loan & EMI": "🏦",
    "Credit Card Payment": "💳",
    "Education": "🎓",
    "Investments": "📈",
    "Salary": "💰",
    "Transfer In": "↩️",
    "Bank Transfer": "🔁",
    "UPI Transfer": "🔁",
    "ATM & Cash": "🏧",
    "Taxes": "🧾",
}
_DEFAULT_ICON = "•"
_UNCATEGORIZED_ICON = "❓"


class TxnRow(BaseModel):
    """One pre-formatted transaction row for display (AD-13: no raw numbers/dates in the UI)."""

    id: int
    date_label: str
    merchant: str
    category: str
    icon: str
    amount_label: str
    is_credit: bool
    needs_review: bool


class ChipItem(BaseModel):
    """One filter chip: a stable ``key`` (for comparison/click) and its display ``label``."""

    key: str
    label: str


def _icon_for(category: str) -> str:
    if category == UNCATEGORIZED:
        return _UNCATEGORIZED_ICON
    return _CATEGORY_ICON.get(category, _DEFAULT_ICON)


def _to_row(txn: TxnModel) -> TxnRow:
    confidence = txn.category_confidence if txn.category_confidence is not None else 0.0
    needs_review = confidence < NEEDS_REVIEW_THRESHOLD
    is_credit = txn.direction == "credit"
    category = txn.category or UNCATEGORIZED
    amount = formatINR(txn.amount)
    return TxnRow(
        id=txn.id,
        date_label=formatDate(txn.date),
        merchant=txn.description_raw,
        category=category,
        icon=_icon_for(category),
        amount_label=(f"+{amount}" if is_credit else amount),
        is_credit=is_credit,
        needs_review=needs_review,
    )


def load_user_transaction_rows(session, txn_model: type, user_id: int) -> list[TxnRow]:
    """Pure/session-injected: query + build display rows for one user (AD-4 scoped).

    Session-injected so the query + formatting logic is unit-testable without a running
    Reflex app (mirrors ``user_for_token``'s pattern in ``auth_state.py``). Ordered by date,
    then id as a tiebreaker — same-day transactions (common in real statements) otherwise
    have no guaranteed stable order across reloads.

    A row that fails to format (e.g. a corrupted date/amount that ``formatDate``/``formatINR``
    reject) is skipped rather than aborting the whole load (AD-12: degrade honestly, don't
    fail the entire page for one bad row) — logged with the transaction id for follow-up.
    """
    rows = session.exec(
        select(txn_model)
        .where(txn_model.user_id == user_id)
        .order_by(txn_model.date, txn_model.id)
    ).all()
    result: list[TxnRow] = []
    for t in rows:
        try:
            result.append(_to_row(t))
        except ValueError:
            log.exception("Skipping unformattable transaction id=%s for user_id=%s", t.id, user_id)
    return result


def needs_review_count(rows: list[TxnRow]) -> int:
    return sum(1 for r in rows if r.needs_review)


def distinct_categories(rows: list[TxnRow]) -> list[str]:
    """Distinct categories actually present among confidently-matched rows, in first-seen order."""
    seen: list[str] = []
    for r in rows:
        if not r.needs_review and r.category not in seen:
            seen.append(r.category)
    return seen


def build_chip_items(rows: list[TxnRow]) -> list[ChipItem]:
    review_count = needs_review_count(rows)
    chips = [ChipItem(key=ALL_KEY, label="All")]
    if review_count > 0:
        chips.append(ChipItem(key=NEEDS_REVIEW_KEY, label=f"Needs review ({review_count})"))
    chips.extend(ChipItem(key=c, label=c) for c in distinct_categories(rows))
    return chips


def filter_rows(rows: list[TxnRow], active_filter: str) -> list[TxnRow]:
    if active_filter == ALL_KEY:
        return rows
    if active_filter == NEEDS_REVIEW_KEY:
        return [r for r in rows if r.needs_review]
    return [r for r in rows if not r.needs_review and r.category == active_filter]


class TransactionsState(AuthState):
    """Loads this user's transactions and derives the filter-chip / needs-review view state."""

    rows: list[TxnRow] = []
    active_filter: str = ALL_KEY

    @rx.event
    def load_transactions(self):
        user = self.authenticated_user
        if user.id is None or user.id < 0:
            self.rows = []
            return
        with rx.session() as session:
            self.rows = load_user_transaction_rows(session, TxnModel, user.id)

    @rx.event
    def set_filter(self, key: str):
        self.active_filter = key

    @rx.var
    def has_transactions(self) -> bool:
        return len(self.rows) > 0

    @rx.var
    def review_count(self) -> int:
        return needs_review_count(self.rows)

    @rx.var
    def chip_items(self) -> list[ChipItem]:
        return build_chip_items(self.rows)

    @rx.var
    def visible_rows(self) -> list[TxnRow]:
        return filter_rows(self.rows, self.active_filter)
