"""Transactions page state (Story 3.1), rebuilt against WDS prototype ``01.4-transactions-table.html``.

Loads the signed-in user's transactions (AD-4: explicit ``user_id`` filter), formats them
through ``formatINR``/``formatDate`` (AD-13), and derives the filter-chip bar and the
"needs review" badge/banner state the prototype's JS computes client-side.

Story 3.3 ("Teach Me"): rows are interactive again (Story 3.1's review had deliberately made
them a non-interactive ``div`` — "until Story 3.3 gives them real behavior"). Clicking a row
opens a correction panel (category picker + "re-apply" toggle); saving writes a
``merchant_rules`` row and, if re-apply is on, updates every matching transaction now — see
``services/categorize/teach_me.py`` for the session-injected DB writes this delegates to.

Code-review follow-up (2026-07-10, Story 3.1/3.2 reviews): the chip/filter derivation
(``needs_review_count``, ``distinct_categories``, ``build_chip_items``, ``filter_rows``) is
pulled out into plain, session-free pure functions so it's unit-testable without a running
Reflex app. Row-building is defensive: a malformed DB row (bad date/amount) is skipped with a
logged warning instead of raising and failing the whole page load.
"""
from __future__ import annotations

import asyncio
import logging

import reflex as rx
from pydantic import BaseModel, model_validator
from sqlmodel import select

from finance_app.models import MerchantRule, Transaction as TxnModel
from finance_app.state.auth_state import AuthState
from services.categorize.schema import CATEGORIES, UNCATEGORIZED
from services.categorize.teach_me import reapply_correction, write_merchant_rule
from services.utils.enums import CategorySource, Direction
from services.utils.format import formatDate, formatINR

log = logging.getLogger(__name__)

#: Rows with confidence below this are shown with the amber "?" needs-review badge. A
#: `rule`-sourced match is confidence 1.0; the rules engine's unrecognized-credit fallback is
#: 0.5; an unmatched row is 0.0 — those are the only two ways a *non*-`llm`-sourced row is
#: flagged "needs review" (Story 3.4: an `llm`-sourced row is never gated by this threshold
#: at all — see `TxnRow.is_ai`/``_to_row``, which check `category_source` first).
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
    """One pre-formatted transaction row for display (AD-13: no raw numbers/dates in the UI).

    ``needs_review``/``is_ai`` drive the 3-state badge (Story 3.4): ``is_ai`` wins
    unconditionally (a blue "AI" badge for any ``category_source='llm'`` row, regardless of
    the LLM's own self-reported confidence); otherwise ``needs_review`` (confidence below
    threshold) shows the amber "?" badge; otherwise no badge.

    Code-review follow-up (2026-07-10): the two are mutually exclusive by construction in
    ``_to_row`` (``needs_review = (not is_ai) and ...``), but nothing on this plain
    ``BaseModel`` enforced that invariant against a future construction site building a row
    directly. A model validator now rejects ``needs_review=True, is_ai=True`` together —
    fail loudly at construction rather than silently rendering the wrong badge (the page's
    ``rx.cond`` checks ``needs_review`` first, so a row with both set would show "?" and
    silently swallow the AI signal).
    """

    id: int
    date_label: str
    merchant: str
    category: str
    icon: str
    amount_label: str
    is_credit: bool
    needs_review: bool
    is_ai: bool

    @model_validator(mode="after")
    def _needs_review_and_is_ai_are_mutually_exclusive(self) -> "TxnRow":
        if self.needs_review and self.is_ai:
            raise ValueError(
                "TxnRow cannot have both needs_review and is_ai set — the 3-state badge "
                "(review/AI/none) is defined by exactly one of these being true at a time."
            )
        return self


class ChipItem(BaseModel):
    """One filter chip: a stable ``key`` (for comparison/click) and its display ``label``."""

    key: str
    label: str


class CategoryOption(BaseModel):
    """One category choice in the Teach Me picker; ``is_selected`` avoids a Reflex Var
    comparison inside the component (mirrors ``ChipItem``'s ``is-active`` pattern)."""

    category: str
    is_selected: bool


def _icon_for(category: str) -> str:
    if category == UNCATEGORIZED:
        return _UNCATEGORIZED_ICON
    return _CATEGORY_ICON.get(category, _DEFAULT_ICON)


def _to_row(txn: TxnModel) -> TxnRow:
    confidence = txn.category_confidence if txn.category_confidence is not None else 0.0
    category = txn.category or UNCATEGORIZED
    # is_ai wins unconditionally (AC #2 — no confidence carve-out for an LLM-sourced row) —
    # but only for a row that actually got a real category out of it. The documented Tier-2
    # write path (services/categorize/llm_categorizer.py) can never leave a row
    # llm-sourced-yet-Uncategorized, but category_source/category_confidence are plain
    # nullable columns with no DB constraint tying them together; a legacy/corrupted row
    # could exist in that state, and it must still surface as "needs review", not silently
    # show a confident-looking "AI" badge (code-review follow-up, 2026-07-10).
    is_ai = txn.category_source == CategorySource.llm.value and category != UNCATEGORIZED
    # Otherwise fall back to the pre-existing confidence-threshold check, which is what
    # actually catches a fully-unmatched Uncategorized row (confidence 0.0) and the rules
    # engine's 0.5-confidence "Transfer In" credit fallback (both source='rule').
    needs_review = (not is_ai) and confidence < NEEDS_REVIEW_THRESHOLD
    is_credit = txn.direction == Direction.credit.value
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
        is_ai=is_ai,
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

    # Teach Me correction panel (Story 3.3).
    open_row_id: int | None = None
    selected_category: str = ""
    reapply: bool = True  # AC #2: defaults ON
    confirmation: str = ""

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

    @rx.event
    def toggle_row(self, row_id: int):
        """Open this row's Teach Me panel, or close it if already open (mirrors the WDS
        prototype's toggleRow — opening one row closes any other)."""
        self.confirmation = ""
        if self.open_row_id == row_id:
            self.open_row_id = None
            self.selected_category = ""
            return
        self.open_row_id = row_id
        # AC #2: the re-apply toggle defaults ON for every panel — the WDS prototype rebuilds
        # the checkbox as `checked` from scratch on each open, so it must reset here too, not
        # just once at state-init (a prior correction turning it off must not leak into the
        # next row's panel).
        self.reapply = True
        row = next((r for r in self.rows if r.id == row_id), None)
        # Pre-select the row's current category, same as the prototype's `current` logic —
        # an UNCATEGORIZED row starts with nothing picked.
        self.selected_category = "" if row is None or row.category == UNCATEGORIZED else row.category

    @rx.event
    def select_category(self, category: str):
        # The taxonomy is the single source of truth (AD-7) — a client can call this handler
        # directly over the websocket, so it must not accept a value the chip UI would never
        # have offered.
        if category not in CATEGORIES:
            return
        self.selected_category = category

    @rx.event
    def toggle_reapply(self):
        self.reapply = not self.reapply

    @rx.event
    def save_correction(self):
        """AC #1-#4: write a merchant_rules row, optionally re-apply it to every matching
        transaction, and show the exact confirmation copy the AC specifies."""
        if (
            not self.selected_category
            or self.selected_category not in CATEGORIES
            or self.open_row_id is None
        ):
            return
        row = next((r for r in self.rows if r.id == self.open_row_id), None)
        if row is None:
            # The row this panel was opened for is no longer in view (e.g. a reload changed
            # the list) — nothing left to correct. Close the panel instead of leaving it
            # stuck open with no control left that can reset it.
            self.open_row_id = None
            self.selected_category = ""
            return
        user = self.authenticated_user
        if user.id is None or user.id < 0:
            return

        updated = True
        with rx.session() as session:
            write_merchant_rule(session, MerchantRule, user.id, row.merchant, self.selected_category)
            if self.reapply:
                reapply_correction(session, TxnModel, user.id, row.merchant, self.selected_category)
            else:
                # Re-apply is off: correct only the one transaction the user actually opened,
                # not every matching row (AD-4: still scoped to this user's own row).
                single = session.get(TxnModel, row.id)
                updated = single is not None and single.user_id == user.id
                if updated:
                    single.category = self.selected_category
                    single.category_source = CategorySource.user.value
                    single.category_confidence = 1.0
                    session.add(single)
                    session.commit()
            self.rows = load_user_transaction_rows(session, TxnModel, user.id)

        self.confirmation = (
            f"Got it — I'll call {row.merchant} '{self.selected_category}' from now on."
            if updated
            else "Couldn't save that correction — please try again."
        )
        self.open_row_id = None
        self.selected_category = ""
        return TransactionsState.dismiss_confirmation_after_delay

    @rx.event(background=True)
    async def dismiss_confirmation_after_delay(self):
        """Auto-dismisses the confirmation toast a few seconds after it appears, so it
        doesn't linger indefinitely until the next row is opened or corrected."""
        await asyncio.sleep(4)
        async with self:
            if self.confirmation:
                self.confirmation = ""

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

    @rx.var
    def category_options(self) -> list[CategoryOption]:
        return [
            CategoryOption(category=c, is_selected=c == self.selected_category)
            for c in CATEGORIES
        ]
