"""Story 3.1 — TransactionsState's pure query/formatting/filter core.

``load_user_transaction_rows`` is session-injected (mirrors ``user_for_token``'s pattern in
``auth_state.py``) so the AD-4 user_id scoping and the row-formatting logic are unit-testable
without a running Reflex app. ``needs_review_count``/``distinct_categories``/
``build_chip_items``/``filter_rows`` are plain pure functions over a list of ``TxnRow`` — no
session needed at all — pulled out of the ``rx.State`` class (code-review follow-up,
2026-07-10) specifically so AC #6's chip/filter behavior has real test coverage instead of
only being implicitly exercised by ``reflex compile``. The ``rx.State`` event handler wiring
itself (``load_transactions``, filter clicks) is app-verified, same honest split documented
since Story 1.4/2.4.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers all app tables
from finance_app.models import Transaction
from finance_app.state.transactions_state import (
    ALL_KEY,
    NEEDS_REVIEW_KEY,
    ChipItem,
    TxnRow,
    build_chip_items,
    distinct_categories,
    filter_rows,
    load_user_transaction_rows,
    needs_review_count,
)
from reflex_local_auth.user import LocalUser


def _row(**kwargs) -> TxnRow:
    defaults = dict(
        id=1, date_label="1 Jun 2026", merchant="Zomato", category="Food & Dining",
        icon="🍽️", amount_label="₹500", is_credit=False, needs_review=False,
    )
    defaults.update(kwargs)
    return TxnRow(**defaults)


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'txns.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _make_user(session, email: str) -> LocalUser:
    user = LocalUser(  # type: ignore[call-arg]
        username=email, password_hash=LocalUser.hash_password("supersecret8"), enabled=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _add_txn(session, user_id: int, **kwargs) -> None:
    defaults = dict(
        date="2026-06-01",
        description_raw="Zomato",
        amount=Decimal("500.00"),
        direction="debit",
        category="Food & Dining",
        category_source="rule",
        category_confidence=1.0,
    )
    defaults.update(kwargs)
    session.add(Transaction(user_id=user_id, **defaults))  # type: ignore[call-arg]
    session.commit()


class TestLoadUserTransactionRows:
    def test_scoped_to_user_id(self, session) -> None:
        # AD-4: a user never sees another user's rows.
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        _add_txn(session, user_a.id, description_raw="Swiggy")
        _add_txn(session, user_b.id, description_raw="Netflix")

        rows_a = load_user_transaction_rows(session, Transaction, user_a.id)
        assert len(rows_a) == 1
        assert rows_a[0].merchant == "Swiggy"

    def test_rule_matched_row_has_no_review_flag(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, category="Food & Dining", category_confidence=1.0)

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].needs_review is False
        assert rows[0].category == "Food & Dining"

    def test_unmatched_row_is_flagged_needs_review(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(
            session, user.id, description_raw="Tata Power",
            category="Uncategorized", category_confidence=0.0,
        )

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].needs_review is True
        assert rows[0].category == "Uncategorized"

    def test_null_category_confidence_is_treated_as_needs_review(self, session) -> None:
        # Defensive: a row that somehow never ran through categorization at all.
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, category=None, category_source=None, category_confidence=None)

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].needs_review is True
        assert rows[0].category == "Uncategorized"

    def test_credit_row_amount_label_has_plus_prefix_and_is_credit_flag(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(
            session, user.id, description_raw="ACME Corp Salary", amount=Decimal("65000.00"),
            direction="credit", category="Salary", category_confidence=1.0,
        )

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].is_credit is True
        assert rows[0].amount_label.startswith("+")
        assert "65,000" in rows[0].amount_label

    def test_debit_row_amount_label_has_no_plus_prefix(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, direction="debit")

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].is_credit is False
        assert not rows[0].amount_label.startswith("+")

    def test_rows_ordered_by_date(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, date="2026-06-20", description_raw="Later")
        _add_txn(session, user.id, date="2026-06-01", description_raw="Earlier")

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert [r.merchant for r in rows] == ["Earlier", "Later"]

    def test_no_transactions_returns_empty_list(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        assert load_user_transaction_rows(session, Transaction, user.id) == []

    def test_confidence_0_5_transfer_in_row_is_flagged_needs_review(self, session) -> None:
        # The engine's unrecognized-credit fallback (category='Transfer In', confidence=0.5,
        # per services/categorize/rules.py) is one of exactly two ways a row becomes
        # needs_review — the other (confidence=0.0) was already covered above.
        user = _make_user(session, "priya@example.com")
        _add_txn(
            session, user.id, description_raw="NEFT CR unknown sender", direction="credit",
            category="Transfer In", category_confidence=0.5,
        )

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].needs_review is True
        assert rows[0].category == "Transfer In"

    def test_malformed_row_is_skipped_not_fatal(self, session) -> None:
        # AD-12: one corrupted row must not fail the whole page load. An invalid date string
        # makes formatDate raise ValueError inside _to_row — load_user_transaction_rows must
        # catch it and skip just that row, per the code-review follow-up.
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, date="not-a-date", description_raw="Corrupted")
        _add_txn(session, user.id, date="2026-06-05", description_raw="Good Row")

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert [r.merchant for r in rows] == ["Good Row"]

    def test_same_day_rows_ordered_by_id_as_tiebreaker(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, date="2026-06-05", description_raw="First")
        _add_txn(session, user.id, date="2026-06-05", description_raw="Second")
        _add_txn(session, user.id, date="2026-06-05", description_raw="Third")

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert [r.merchant for r in rows] == ["First", "Second", "Third"]

    def test_row_icon_matches_category(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, category="Loan & EMI", category_confidence=1.0)

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].icon == "🏦"

    def test_uncategorized_row_gets_the_uncategorized_icon(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, category="Uncategorized", category_confidence=0.0)

        rows = load_user_transaction_rows(session, Transaction, user.id)
        assert rows[0].icon == "❓"


class TestNeedsReviewCount:
    def test_counts_only_needs_review_rows(self) -> None:
        rows = [_row(needs_review=False), _row(needs_review=True), _row(needs_review=True)]
        assert needs_review_count(rows) == 2

    def test_zero_when_no_rows(self) -> None:
        assert needs_review_count([]) == 0


class TestDistinctCategories:
    def test_dedupes_and_preserves_first_seen_order(self) -> None:
        rows = [
            _row(category="Food & Dining"),
            _row(category="Transport"),
            _row(category="Food & Dining"),
        ]
        assert distinct_categories(rows) == ["Food & Dining", "Transport"]

    def test_excludes_needs_review_rows(self) -> None:
        rows = [_row(category="Food & Dining", needs_review=True)]
        assert distinct_categories(rows) == []


class TestBuildChipItems:
    def test_all_chip_always_first(self) -> None:
        chips = build_chip_items([])
        assert chips[0] == ChipItem(key=ALL_KEY, label="All")

    def test_needs_review_chip_absent_when_count_is_zero(self) -> None:
        rows = [_row(needs_review=False)]
        keys = [c.key for c in build_chip_items(rows)]
        assert NEEDS_REVIEW_KEY not in keys

    def test_needs_review_chip_present_with_count_in_label(self) -> None:
        rows = [_row(needs_review=True), _row(needs_review=True)]
        chips = build_chip_items(rows)
        review_chip = next(c for c in chips if c.key == NEEDS_REVIEW_KEY)
        assert review_chip.label == "Needs review (2)"

    def test_one_chip_per_distinct_confident_category(self) -> None:
        rows = [_row(category="Food & Dining"), _row(category="Transport")]
        keys = {c.key for c in build_chip_items(rows)}
        assert keys == {ALL_KEY, "Food & Dining", "Transport"}


class TestFilterRows:
    def test_all_key_returns_everything(self) -> None:
        rows = [_row(id=1), _row(id=2, needs_review=True)]
        assert filter_rows(rows, ALL_KEY) == rows

    def test_needs_review_key_returns_only_flagged_rows(self) -> None:
        rows = [_row(id=1, needs_review=False), _row(id=2, needs_review=True)]
        result = filter_rows(rows, NEEDS_REVIEW_KEY)
        assert [r.id for r in result] == [2]

    def test_category_key_returns_only_matching_confident_rows(self) -> None:
        rows = [
            _row(id=1, category="Food & Dining", needs_review=False),
            _row(id=2, category="Transport", needs_review=False),
            _row(id=3, category="Food & Dining", needs_review=True),
        ]
        result = filter_rows(rows, "Food & Dining")
        assert [r.id for r in result] == [1]
