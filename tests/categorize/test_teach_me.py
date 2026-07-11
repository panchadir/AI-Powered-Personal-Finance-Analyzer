"""Story 3.3 · AC #1, #2, #3, #5, #6 — "Teach Me" user correction & merchant rules.

Covers ``services/categorize/teach_me.py`` (session-injected DB writes, real SQLite
round-trip) and ``services/categorize/rules.py::categorize_rules``'s ``user_rules``
parameter (pure, no DB) — the end-to-end proof that a taught rule wins on a future upload.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers all app tables
from finance_app.models import MerchantRule, Transaction as TxnModel
from reflex_local_auth.user import LocalUser
from services.categorize.rules import categorize_rules
from services.categorize.schema import UNCATEGORIZED
from services.categorize.teach_me import (
    load_user_merchant_rules,
    reapply_correction,
    write_merchant_rule,
)
from services.ingestion.schema import Transaction
from services.utils.enums import Direction


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'teach_me.db'}")
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


def _add_txn(session, user_id: int, **kwargs) -> TxnModel:
    defaults = dict(
        date="2026-06-01", description_raw="Merchant", amount=Decimal("100.00"),
        direction="debit", category="Uncategorized", category_source="rule",
        category_confidence=0.0,
    )
    defaults.update(kwargs)
    row = TxnModel(user_id=user_id, **defaults)  # type: ignore[call-arg]
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


class TestWriteMerchantRule:
    def test_inserts_a_new_rule(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        write_merchant_rule(session, MerchantRule, user.id, "swiggy", "Personal Project")

        rows = session.exec(
            sqlmodel.select(MerchantRule).where(MerchantRule.user_id == user.id)
        ).all()
        assert len(rows) == 1
        assert rows[0].pattern == "swiggy"
        assert rows[0].category == "Personal Project"
        assert rows[0].source == "user"

    def test_second_correction_for_same_pattern_updates_not_duplicates(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        write_merchant_rule(session, MerchantRule, user.id, "swiggy", "Food & Dining")
        write_merchant_rule(session, MerchantRule, user.id, "swiggy", "Personal Project")

        rows = session.exec(
            sqlmodel.select(MerchantRule).where(MerchantRule.user_id == user.id)
        ).all()
        assert len(rows) == 1  # upsert, not a second conflicting row
        assert rows[0].category == "Personal Project"

    def test_same_pattern_different_users_do_not_collide(self, session) -> None:
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        write_merchant_rule(session, MerchantRule, user_a.id, "swiggy", "Food & Dining")
        write_merchant_rule(session, MerchantRule, user_b.id, "swiggy", "Personal Project")

        rows_a = session.exec(
            sqlmodel.select(MerchantRule).where(MerchantRule.user_id == user_a.id)
        ).all()
        rows_b = session.exec(
            sqlmodel.select(MerchantRule).where(MerchantRule.user_id == user_b.id)
        ).all()
        assert len(rows_a) == 1 and rows_a[0].category == "Food & Dining"
        assert len(rows_b) == 1 and rows_b[0].category == "Personal Project"

    def test_case_variant_of_an_existing_pattern_updates_not_duplicates(self, session) -> None:
        # Code-review follow-up: matching everywhere else is case-insensitive, so the upsert
        # lookup must be too, or "Swiggy" vs "swiggy" would pile up as separate rows.
        user = _make_user(session, "priya@example.com")
        write_merchant_rule(session, MerchantRule, user.id, "swiggy", "Food & Dining")
        write_merchant_rule(session, MerchantRule, user.id, "SWIGGY", "Personal Project")

        rows = session.exec(
            sqlmodel.select(MerchantRule).where(MerchantRule.user_id == user.id)
        ).all()
        assert len(rows) == 1
        assert rows[0].category == "Personal Project"

    def test_updating_an_existing_rule_refreshes_created_at(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        write_merchant_rule(session, MerchantRule, user.id, "swiggy", "Food & Dining")
        row = session.exec(
            sqlmodel.select(MerchantRule).where(MerchantRule.user_id == user.id)
        ).one()
        original_created_at = row.created_at

        write_merchant_rule(session, MerchantRule, user.id, "swiggy", "Personal Project")

        session.refresh(row)
        assert row.created_at >= original_created_at

    def test_blank_pattern_is_not_written(self, session) -> None:
        # Code-review follow-up: an empty/whitespace pattern would match every transaction
        # via _match's/reapply_correction's substring check — refuse to store one at all.
        user = _make_user(session, "priya@example.com")
        write_merchant_rule(session, MerchantRule, user.id, "   ", "Personal Project")

        rows = session.exec(
            sqlmodel.select(MerchantRule).where(MerchantRule.user_id == user.id)
        ).all()
        assert rows == []


class TestLoadUserMerchantRules:
    def test_returns_only_this_users_rules(self, session) -> None:
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        write_merchant_rule(session, MerchantRule, user_a.id, "swiggy", "Personal Project")
        write_merchant_rule(session, MerchantRule, user_b.id, "amazon", "Office Supplies")

        assert load_user_merchant_rules(session, MerchantRule, user_a.id) == [
            ("swiggy", "Personal Project")
        ]

    def test_no_rules_returns_empty_list(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        assert load_user_merchant_rules(session, MerchantRule, user.id) == []

    def test_most_recently_taught_rule_comes_first(self, session) -> None:
        # Code-review follow-up: no deterministic order previously existed, so which of two
        # matching rules "won" in categorize_rules/_match was arbitrary DB order.
        user = _make_user(session, "priya@example.com")
        write_merchant_rule(session, MerchantRule, user.id, "swiggy", "Food & Dining")
        write_merchant_rule(session, MerchantRule, user.id, "swiggy instamart", "Groceries")

        rules = load_user_merchant_rules(session, MerchantRule, user.id)
        assert rules[0] == ("swiggy instamart", "Groceries")


class TestReapplyCorrection:
    def test_updates_all_matching_rows_for_the_user(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, description_raw="Swiggy")
        _add_txn(session, user.id, description_raw="Swiggy Instamart")
        _add_txn(session, user.id, description_raw="Zomato")

        count = reapply_correction(session, TxnModel, user.id, "swiggy", "Personal Project")

        assert count == 2
        rows = session.exec(
            sqlmodel.select(TxnModel).where(TxnModel.user_id == user.id)
        ).all()
        swiggy_rows = [r for r in rows if "swiggy" in r.description_raw.lower()]
        assert all(r.category == "Personal Project" for r in swiggy_rows)
        assert all(r.category_source == "user" for r in swiggy_rows)
        assert all(r.category_confidence == 1.0 for r in swiggy_rows)
        zomato_row = next(r for r in rows if r.description_raw == "Zomato")
        assert zomato_row.category == "Uncategorized"  # untouched

    def test_overrides_even_already_confident_rows(self, session) -> None:
        """AC #3 has no source/confidence carve-out: re-apply updates a matching row even
        if Tier-1/Tier-2 already confidently categorized it."""
        user = _make_user(session, "priya@example.com")
        _add_txn(
            session, user.id, description_raw="Swiggy", category="Food & Dining",
            category_source="rule", category_confidence=1.0,
        )

        count = reapply_correction(session, TxnModel, user.id, "swiggy", "Personal Project")

        assert count == 1
        row = session.exec(sqlmodel.select(TxnModel).where(TxnModel.user_id == user.id)).one()
        assert row.category == "Personal Project"

    def test_scoped_to_user_id_never_touches_another_users_rows(self, session) -> None:
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        _add_txn(session, user_a.id, description_raw="Swiggy")
        b_row = _add_txn(session, user_b.id, description_raw="Swiggy")

        reapply_correction(session, TxnModel, user_a.id, "swiggy", "Personal Project")

        session.refresh(b_row)
        assert b_row.category == "Uncategorized"  # user B's row untouched

    def test_no_matches_returns_zero(self, session) -> None:
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, description_raw="Zomato")
        count = reapply_correction(session, TxnModel, user.id, "swiggy", "Personal Project")
        assert count == 0

    def test_blank_pattern_matches_nothing(self, session) -> None:
        # Code-review follow-up: an empty/whitespace pattern must never be treated as
        # "contained in" every description — that would recategorize a user's entire history.
        user = _make_user(session, "priya@example.com")
        _add_txn(session, user.id, description_raw="Zomato")
        _add_txn(session, user.id, description_raw="Swiggy")

        count = reapply_correction(session, TxnModel, user.id, "   ", "Personal Project")

        assert count == 0
        rows = session.exec(
            sqlmodel.select(TxnModel).where(TxnModel.user_id == user.id)
        ).all()
        assert all(r.category == "Uncategorized" for r in rows)


class TestCategorizeRulesWithUserRules:
    """AC #5: on a future upload, the taught rule is applied via categorize_rules — checked
    before the built-in RULES table."""

    def _txn(self, description: str) -> Transaction:
        return Transaction(
            date="2026-06-01", description_raw=description, amount=Decimal("100.00"),
            direction=Direction.debit,
        )

    def test_user_rule_overrides_the_built_in_rule_for_the_same_merchant(self) -> None:
        # Without a user rule, "Zomato" normally matches the built-in Food & Dining rule.
        baseline = categorize_rules([self._txn("Zomato")])
        assert baseline[0].category == "Food & Dining"

        # With a user correction, the user's category wins instead.
        taught = categorize_rules(
            [self._txn("Zomato")], user_rules=[("zomato", "Personal Project")]
        )
        assert taught[0].category == "Personal Project"
        assert taught[0].category_confidence == 1.0

    def test_user_rule_catches_a_merchant_tier1_never_recognized(self) -> None:
        baseline = categorize_rules([self._txn("XYZCORP PAYMENT REF 88213")])
        assert baseline[0].category == UNCATEGORIZED

        taught = categorize_rules(
            [self._txn("XYZCORP PAYMENT REF 88213")],
            user_rules=[("xyzcorp", "Personal Project")],
        )
        assert taught[0].category == "Personal Project"

    def test_no_user_rules_behaves_exactly_as_before(self) -> None:
        """Task 1 must be additive-only — existing callers passing no user_rules are unaffected."""
        result = categorize_rules([self._txn("Zomato")])
        assert result[0].category == "Food & Dining"
        assert result[0].category_confidence == 1.0

    def test_blank_user_rule_pattern_is_ignored(self) -> None:
        # Code-review follow-up: a stray blank pattern must never act as a match-everything
        # rule — it should behave as if it weren't in the list at all.
        result = categorize_rules(
            [self._txn("Zomato")], user_rules=[("   ", "Personal Project")]
        )
        assert result[0].category == "Food & Dining"  # falls through to the built-in rule
