"""Handler + computed-var coverage for ``finance_app/state/transactions_state.py``.

The pure query/chip/filter functions are covered by ``tests/test_transactions_state.py``; this
drives the ``rx.State`` surface: the load, the Teach-Me correction panel handlers, and the
derived vars — through the ``make_state`` harness.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from finance_app.models import MerchantRule, Transaction
from finance_app.state.transactions_state import (
    ALL_KEY,
    NEEDS_REVIEW_KEY,
    TransactionsState,
    TxnRow,
)
from tests.conftest import drive, drive_background


def _row(**overrides):
    base = dict(
        id=1, date_label="1 Jun 2026", merchant="Zomato", category="Food & Dining",
        icon="🍽️", amount_label="₹500", is_credit=False, needs_review=False, is_ai=False,
    )
    base.update(overrides)
    return TxnRow(**base)


def _seed_txn(session, user_id, **overrides):
    defaults = dict(
        user_id=user_id, date="2026-06-01", description_raw="ZOMATO",
        amount=Decimal("500"), direction="debit", category="Uncategorized",
        category_source="rule", category_confidence=0.0,
    )
    defaults.update(overrides)
    txn = Transaction(**defaults)  # type: ignore[call-arg]
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# TxnRow invariant
# ---------------------------------------------------------------------------

def test_txn_row_rejects_both_badges_set():
    with pytest.raises(ValueError):
        _row(needs_review=True, is_ai=True)


# ---------------------------------------------------------------------------
# Computed vars
# ---------------------------------------------------------------------------

class TestComputedVars:
    def test_derived_vars_reflect_rows(self, make_state):
        s = make_state(TransactionsState)
        s.rows = [
            _row(id=1, category="Food & Dining", needs_review=False),
            _row(id=2, category="Uncategorized", needs_review=True),
        ]
        assert s.has_transactions is True
        assert s.review_count == 1
        keys = [c.key for c in s.chip_items]
        assert ALL_KEY in keys and NEEDS_REVIEW_KEY in keys
        # Filtering flows through active_filter.
        s.active_filter = NEEDS_REVIEW_KEY
        assert [r.id for r in s.visible_rows] == [2]

    def test_category_options_marks_selection(self, make_state):
        s = make_state(TransactionsState)
        s.selected_category = "Groceries"
        selected = [o for o in s.category_options if o.is_selected]
        assert len(selected) == 1 and selected[0].category == "Groceries"

    def test_has_transactions_false_when_empty(self, make_state):
        s = make_state(TransactionsState)
        assert s.has_transactions is False


# ---------------------------------------------------------------------------
# Simple panel handlers
# ---------------------------------------------------------------------------

class TestPanelHandlers:
    def test_set_filter(self, make_state):
        s = make_state(TransactionsState)
        s.set_filter("Food & Dining")
        assert s.active_filter == "Food & Dining"

    def test_toggle_reapply(self, make_state):
        s = make_state(TransactionsState)
        assert s.reapply is True
        s.toggle_reapply()
        assert s.reapply is False

    def test_toggle_row_opens_and_preselects_category(self, make_state):
        s = make_state(TransactionsState)
        s.rows = [_row(id=1, category="Food & Dining")]
        s.toggle_row(1)
        assert s.open_row_id == 1 and s.selected_category == "Food & Dining" and s.reapply is True

    def test_toggle_row_uncategorized_starts_unpicked(self, make_state):
        s = make_state(TransactionsState)
        s.rows = [_row(id=1, category="Uncategorized", needs_review=True)]
        s.toggle_row(1)
        assert s.open_row_id == 1 and s.selected_category == ""

    def test_toggle_row_again_closes(self, make_state):
        s = make_state(TransactionsState)
        s.rows = [_row(id=1, category="Food & Dining")]
        s.toggle_row(1)
        s.toggle_row(1)
        assert s.open_row_id is None and s.selected_category == ""

    def test_select_category_accepts_valid_rejects_invalid(self, make_state):
        s = make_state(TransactionsState)
        s.select_category("Groceries")
        assert s.selected_category == "Groceries"
        s.select_category("Not A Real Category")
        assert s.selected_category == "Groceries"  # unchanged


# ---------------------------------------------------------------------------
# load_transactions (async)
# ---------------------------------------------------------------------------

class TestLoadTransactions:
    def test_unauthenticated_loads_empty(self, make_state):
        s = make_state(TransactionsState, auth_token="nope")
        drive(s.load_transactions())
        assert s.loaded is True and s.rows == []

    def test_authenticated_loads_rows(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        _seed_txn(db_session, uid, description_raw="SWIGGY", category="Food & Dining", category_confidence=1.0)
        s = make_state(TransactionsState, auth_token=token)
        drive(s.load_transactions())
        assert s.loaded is True and len(s.rows) == 1
        assert s.rows[0].merchant == "SWIGGY"


# ---------------------------------------------------------------------------
# save_correction (Teach Me)
# ---------------------------------------------------------------------------

class TestSaveCorrection:
    def test_guard_no_category_is_noop(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(TransactionsState, auth_token=token)
        s.open_row_id = 1
        s.selected_category = ""
        assert s.save_correction() is None

    def test_guard_row_not_in_view_closes_panel(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(TransactionsState, auth_token=token)
        s.rows = []
        s.open_row_id = 42
        s.selected_category = "Groceries"
        s.save_correction()
        assert s.open_row_id is None and s.selected_category == ""

    def test_reapply_on_writes_rule_and_confirms(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        txn = _seed_txn(db_session, uid, description_raw="SWIGGY")
        s = make_state(TransactionsState, auth_token=token)
        drive(s.load_transactions())
        s.open_row_id = txn.id
        s.selected_category = "Food & Dining"
        s.reapply = True
        result = s.save_correction()
        assert "Got it" in s.confirmation and s.open_row_id is None
        assert result is not None  # schedules the toast auto-dismiss
        from sqlmodel import select
        rules = db_session.exec(select(MerchantRule).where(MerchantRule.user_id == uid)).all()
        assert len(rules) == 1

    def test_reapply_off_updates_single_row(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        txn = _seed_txn(db_session, uid, description_raw="SWIGGY")
        s = make_state(TransactionsState, auth_token=token)
        drive(s.load_transactions())
        s.open_row_id = txn.id
        s.selected_category = "Food & Dining"
        s.reapply = False
        s.save_correction()
        assert "Got it" in s.confirmation
        db_session.expire_all()
        assert db_session.get(Transaction, txn.id).category == "Food & Dining"

    def test_reapply_off_missing_single_reports_failure(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(TransactionsState, auth_token=token)
        # A row present in the view but with no backing DB transaction → single is None.
        s.rows = [_row(id=9999, merchant="GHOST", category="Uncategorized", needs_review=True)]
        s.open_row_id = 9999
        s.selected_category = "Food & Dining"
        s.reapply = False
        s.save_correction()
        assert "Couldn't save" in s.confirmation

    def test_unauthenticated_save_is_noop(self, make_state):
        s = make_state(TransactionsState, auth_token="nope")
        s.rows = [_row(id=1, merchant="X", category="Uncategorized", needs_review=True)]
        s.open_row_id = 1
        s.selected_category = "Food & Dining"
        assert s.save_correction() is None


class TestDismissConfirmationBackground:
    def test_auto_dismiss_clears_toast(self, make_state, monkeypatch):
        import finance_app.state.transactions_state as tmod

        async def _instant(*_a, **_k):
            return None

        monkeypatch.setattr(tmod.asyncio, "sleep", _instant)  # skip the 4-second wait
        s = make_state(TransactionsState)
        s.confirmation = "Got it — I'll call Zomato 'Food & Dining' from now on."
        drive_background(s, TransactionsState.dismiss_confirmation_after_delay)
        assert s.confirmation == ""
