"""Coverage for ``finance_app/state/commitments_state.py`` — pure validators plus the full
add / edit / delete / suggestion handler surface, driven through the ``make_state`` harness.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from finance_app.models import Commitment, Transaction
from finance_app.state.commitments_state import (
    CommitmentsState,
    as_text,
    _due_phrase,
    validate_commitment,
)
from finance_app.state.engine_bridge import detect_commitment_candidates


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

class TestPureHelpers:
    @pytest.mark.parametrize(
        "day, expected_fragment",
        [(31, "end of each month"), (1, "1st"), (2, "2nd"), (3, "3rd"), (5, "5th"), (22, "22nd")],
    )
    def test_due_phrase(self, day, expected_fragment):
        assert expected_fragment in _due_phrase(day)

    @pytest.mark.parametrize(
        "value, expected",
        [(None, ""), (15.0, "15"), (15.5, "15.5"), (" hi ", "hi"), (20, "20")],
    )
    def test_as_text(self, value, expected):
        assert as_text(value) == expected

    def test_validate_ok(self):
        errors, name, amount, due = validate_commitment("Rent", "15000", "5")
        assert errors == {} and name == "Rent" and amount == Decimal("15000") and due == 5

    def test_validate_missing_name(self):
        errors, *_ = validate_commitment("", "100", "5")
        assert "name" in errors

    def test_validate_long_name(self):
        errors, *_ = validate_commitment("x" * 51, "100", "5")
        assert "name" in errors

    @pytest.mark.parametrize("amount", ["0", "-5", "abc", ""])
    def test_validate_bad_amount(self, amount):
        errors, *_ = validate_commitment("Rent", amount, "5")
        assert "amount" in errors

    @pytest.mark.parametrize("due", ["0", "32", "15.5", "abc"])
    def test_validate_bad_due_day(self, due):
        errors, *_ = validate_commitment("Rent", "100", due)
        assert "due_day" in errors


# ---------------------------------------------------------------------------
# Modal / form handlers (no DB or trivial DB)
# ---------------------------------------------------------------------------

class TestModalHandlers:
    def test_open_add_resets_form(self, make_state):
        s = make_state(CommitmentsState)
        s.form_name = "stale"
        s.open_add()
        assert s.modal_open is True and s.editing_id == -1 and s.form_name == ""

    def test_close_modal(self, make_state):
        s = make_state(CommitmentsState)
        s.modal_open = True
        s.editing_id = 5
        s.close_modal()
        assert s.modal_open is False and s.editing_id == -1

    def test_setters_clear_errors(self, make_state):
        s = make_state(CommitmentsState)
        s.name_error = s.amount_error = s.due_day_error = "x"
        s.set_form_name("Rent")
        s.set_form_amount(15000.0)
        s.set_form_due_day(5.0)
        s.set_criticality("critical")
        assert s.form_name == "Rent" and s.form_amount == "15000" and s.form_due_day == "5"
        assert s.form_criticality == "critical"
        assert not (s.name_error or s.amount_error or s.due_day_error)

    def test_dismiss_toast(self, make_state):
        s = make_state(CommitmentsState)
        s.toast = "hi"
        s.dismiss_toast()
        assert s.toast == ""

    def test_close_delete(self, make_state):
        s = make_state(CommitmentsState)
        s.delete_open = True
        s.delete_id = 3
        s.close_delete()
        assert s.delete_open is False and s.delete_id == -1


# ---------------------------------------------------------------------------
# Page load + impact bar
# ---------------------------------------------------------------------------

class TestLoadPage:
    def test_no_user_redirects(self, make_state):
        s = make_state(CommitmentsState, auth_token="nope")
        assert s.load_commitments_page() is not None

    def test_load_populates_list_and_bar(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        db_session.add(Commitment(user_id=uid, name="Rent", amount=Decimal("15000"),
                                  due_day=5, criticality="critical"))  # type: ignore[call-arg]
        db_session.commit()
        s = make_state(CommitmentsState, auth_token=token)
        s.load_commitments_page()
        assert s.empty is False and len(s.commitments) == 1
        assert s.commitments[0].name == "Rent" and s.commitments[0].icon == "🔴"
        assert s.protecting_total.startswith("₹") and s.safe_to_spend.startswith("₹")


# ---------------------------------------------------------------------------
# Save (add + edit) and its IDOR / validation branches
# ---------------------------------------------------------------------------

class TestSaveCommitment:
    def test_validation_failure_short_circuits(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CommitmentsState, auth_token=token)
        s.form_name, s.form_amount, s.form_due_day = "", "0", "99"
        s.save_commitment()
        assert s.name_error and s.amount_error and s.due_day_error
        assert s.modal_open is False or s.saving is False

    def test_add_creates_commitment(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        s = make_state(CommitmentsState, auth_token=token)
        s.editing_id = -1
        s.form_name, s.form_amount, s.form_due_day = "Gym", "1200", "3"
        s.form_criticality = "flexible"
        s.save_commitment()
        assert "Protected" in s.toast and s.modal_open is False
        from sqlmodel import select
        rows = db_session.exec(select(Commitment).where(Commitment.user_id == uid)).all()
        assert len(rows) == 1 and rows[0].name == "Gym"

    def test_edit_updates_commitment(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        c = Commitment(user_id=uid, name="Rent", amount=Decimal("15000"), due_day=5, criticality="critical")  # type: ignore[call-arg]
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        s = make_state(CommitmentsState, auth_token=token)
        s.editing_id = c.id
        s.form_name, s.form_amount, s.form_due_day = "Rent (new)", "16000", "6"
        s.form_criticality = "critical"
        s.save_commitment()
        assert "Updated" in s.toast

    def test_edit_missing_row_toasts_gone(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CommitmentsState, auth_token=token)
        s.editing_id = 9999  # not owned / nonexistent
        s.form_name, s.form_amount, s.form_due_day = "Ghost", "100", "5"
        s.save_commitment()
        assert "no longer there" in s.toast

    def test_open_edit_loads_row(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        c = Commitment(user_id=uid, name="Rent", amount=Decimal("15000"), due_day=5, criticality="critical")  # type: ignore[call-arg]
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        s = make_state(CommitmentsState, auth_token=token)
        s.open_edit(c.id)
        assert s.modal_open is True and s.form_name == "Rent" and s.editing_id == c.id

    def test_open_edit_foreign_id_is_noop(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CommitmentsState, auth_token=token)
        assert s.open_edit(4242) is None
        assert s.modal_open is False


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestDelete:
    def _commit(self, db_session, uid):
        c = Commitment(user_id=uid, name="Rent", amount=Decimal("15000"), due_day=5, criticality="critical")  # type: ignore[call-arg]
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        return c

    def test_open_delete_sets_prompt(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        c = self._commit(db_session, uid)
        s = make_state(CommitmentsState, auth_token=token)
        s.open_delete(c.id)
        assert s.delete_open is True and "Rent" in s.delete_prompt and s.delete_id == c.id

    def test_confirm_delete_removes_row(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        c = self._commit(db_session, uid)
        s = make_state(CommitmentsState, auth_token=token)
        s.delete_id = c.id
        s.confirm_delete()
        assert "Removed" in s.toast and s.delete_open is False
        from sqlmodel import select
        assert db_session.exec(select(Commitment).where(Commitment.id == c.id)).first() is None

    def test_confirm_delete_no_selection_is_noop(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CommitmentsState, auth_token=token)
        s.delete_id = -1
        assert s.confirm_delete() is None

    def test_confirm_delete_foreign_row_clears_state(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CommitmentsState, auth_token=token)
        s.delete_id = 5150  # not owned
        s.confirm_delete()
        assert s.delete_open is False and s.delete_id == -1


# ---------------------------------------------------------------------------
# Auto-detected suggestions (Story 5.6)
# ---------------------------------------------------------------------------

def _seed_recurring(db_session, uid):
    """Two identical monthly Netflix debits → a detectable recurring candidate."""
    for date in ("2026-05-05", "2026-06-05"):
        db_session.add(Transaction(  # type: ignore[call-arg]
            user_id=uid, date=date, description_raw="NETFLIX",
            merchant_normalized="Netflix", amount=Decimal("500"),
            direction="debit", category="Entertainment",
        ))
    db_session.commit()


class TestSuggestions:
    def test_dismiss_suggestion_records_and_refreshes(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        _seed_recurring(db_session, uid)
        s = make_state(CommitmentsState, auth_token=token)
        s.dismiss_suggestion("any-signature")
        from sqlmodel import select
        from finance_app.models import CommitmentSuggestion
        rows = db_session.exec(select(CommitmentSuggestion).where(CommitmentSuggestion.user_id == uid)).all()
        assert rows and rows[0].status == "dismissed"

    def test_confirm_unknown_signature_just_refreshes(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        _seed_recurring(db_session, uid)
        s = make_state(CommitmentsState, auth_token=token)
        assert s.confirm_suggestion("does-not-match") is None

    def test_confirm_real_candidate_creates_commitment(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        _seed_recurring(db_session, uid)
        candidates = detect_commitment_candidates(db_session, uid)
        assert candidates, "expected a recurring candidate from the seeded charges"
        signature = candidates[0].signature
        s = make_state(CommitmentsState, auth_token=token)
        s.confirm_suggestion(signature)
        assert "Protected" in s.toast
        from sqlmodel import select
        commitments = db_session.exec(select(Commitment).where(Commitment.user_id == uid)).all()
        assert len(commitments) == 1


class TestSuggestionAuthGuards:
    @pytest.mark.parametrize("call", ["confirm", "dismiss"])
    def test_no_user_redirects(self, make_state, call):
        s = make_state(CommitmentsState, auth_token="nope")
        handler = s.confirm_suggestion if call == "confirm" else s.dismiss_suggestion
        assert handler("sig") is not None


class TestExpiredSessionGuards:
    """Every DB handler must redirect (never silently mutate) when the session is gone."""

    def test_open_edit_no_user_redirects(self, make_state):
        s = make_state(CommitmentsState, auth_token="nope")
        assert s.open_edit(1) is not None

    def test_save_no_user_redirects(self, make_state):
        s = make_state(CommitmentsState, auth_token="nope")
        s.form_name, s.form_amount, s.form_due_day = "Rent", "15000", "5"
        assert s.save_commitment() is not None

    def test_open_delete_no_user_redirects(self, make_state):
        s = make_state(CommitmentsState, auth_token="nope")
        assert s.open_delete(1) is not None

    def test_open_delete_foreign_id_is_noop(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CommitmentsState, auth_token=token)
        assert s.open_delete(7777) is None
        assert s.delete_open is False

    def test_confirm_delete_no_user_redirects(self, make_state):
        s = make_state(CommitmentsState, auth_token="nope")
        s.delete_id = 1
        assert s.confirm_delete() is not None
