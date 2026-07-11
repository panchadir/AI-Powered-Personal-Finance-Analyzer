"""Story 2.5 acceptance: deduplicated persistence.

Covers the AC scenarios against the real ``finance_app.models.Transaction`` on a throwaway
SQLite engine (AD-14 — sqlmodel data access, no Reflex app): exact re-upload -> zero new,
overlapping upload -> only the new rows, wider date range -> only the genuinely new rows.
Plus the pure dedup logic, per-user isolation (AD-4), and the normalize-before-compare rule.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers all app tables
from finance_app.models import Transaction as TxnModel
from services.ingestion import (
    Transaction,
    filter_new_transactions,
    persist_transactions,
)
from services.ingestion.normalize import dedup_key
from services.utils.enums import Direction


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'dedup.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _t(date: str, desc: str, amount: str, direction: Direction = Direction.debit,
       balance: str | None = None) -> Transaction:
    return Transaction(
        date=date, description_raw=desc, amount=Decimal(amount), direction=direction,
        balance_after=Decimal(balance) if balance is not None else None,
    )


def _count(session, user_id: int) -> int:
    return len(session.exec(
        sqlmodel.select(TxnModel).where(TxnModel.user_id == user_id)
    ).all())


# --- AC scenarios (real DB round-trip) ---------------------------------------

def test_exact_reupload_creates_zero_new_rows(session) -> None:
    txns = [_t("2026-06-01", "SWIGGY", "450.00", balance="18000.00"),
            _t("2026-06-02", "RENT", "15000.00", balance="3000.00")]
    first = persist_transactions(session, TxnModel, 1, None, txns)
    assert (first.inserted, first.skipped) == (2, 0)

    second = persist_transactions(session, TxnModel, 1, None, txns)  # same file again
    assert (second.inserted, second.skipped) == (0, 2)
    assert _count(session, 1) == 2  # no duplicates


def test_overlapping_upload_inserts_only_new(session) -> None:
    batch_a = [_t("2026-06-01", "SWIGGY", "450.00"),
               _t("2026-06-02", "RENT", "15000.00")]
    batch_b = [_t("2026-06-02", "RENT", "15000.00"),                    # overlaps A
               _t("2026-06-03", "SALARY", "85000.00", Direction.credit)]  # new
    persist_transactions(session, TxnModel, 1, None, batch_a)
    result = persist_transactions(session, TxnModel, 1, None, batch_b)
    assert (result.inserted, result.skipped) == (1, 1)
    assert _count(session, 1) == 3


def test_wider_date_range_upload_inserts_only_the_new_rows(session) -> None:
    june = [_t("2026-06-01", "SWIGGY", "450.00"),
            _t("2026-06-30", "SALARY", "85000.00", Direction.credit)]
    may_and_june = [_t("2026-05-15", "AMAZON", "1200.00")] + june  # wider range re-includes June
    persist_transactions(session, TxnModel, 1, None, june)
    result = persist_transactions(session, TxnModel, 1, None, may_and_june)
    assert (result.inserted, result.skipped) == (1, 2)  # only May is new
    assert _count(session, 1) == 3


def test_dedup_is_per_user_no_cross_user_collision(session) -> None:
    """AD-4: the same transaction for two users persists for both — keys include user_id."""
    txns = [_t("2026-06-01", "SWIGGY", "450.00")]
    persist_transactions(session, TxnModel, 1, None, txns)
    persist_transactions(session, TxnModel, 2, None, txns)
    assert _count(session, 1) == 1 and _count(session, 2) == 1


def test_intra_batch_duplicate_collapses(session) -> None:
    """A statement listing the same row twice inserts it once."""
    txns = [_t("2026-06-01", "SWIGGY", "450.00"), _t("2026-06-01", "SWIGGY", "450.00")]
    result = persist_transactions(session, TxnModel, 1, None, txns)
    assert (result.inserted, result.skipped) == (1, 1)
    assert _count(session, 1) == 1


# --- pure logic ---------------------------------------------------------------

def test_filter_new_transactions_against_existing_keys() -> None:
    existing = {dedup_key(_t("2026-06-01", "SWIGGY", "450.00").with_fields(user_id=1))}
    candidates = [
        _t("2026-06-01", "SWIGGY", "450.00").with_fields(user_id=1),   # dup of existing
        _t("2026-06-02", "RENT", "15000.00").with_fields(user_id=1),   # new
    ]
    new = filter_new_transactions(candidates, existing)
    assert [t.date for t in new] == ["2026-06-02"]


def test_dedup_key_normalizes_description_whitespace() -> None:
    """Normalize-before-compare: whitespace-variant descriptions dedup to the same row."""
    existing = {dedup_key(_t("2026-06-01", "ATM WITHDRAWAL", "450.00").with_fields(user_id=1))}
    spaced = _t("2026-06-01", "ATM   WITHDRAWAL", "450.00").with_fields(user_id=1)
    assert filter_new_transactions([spaced], existing) == []


def test_reasoning_field_round_trips_through_persist(session) -> None:
    """Story 3.2: Tier-2's reasoning must survive the parse -> persist -> DB round-trip,
    same as category/category_source/category_confidence already do."""
    txn = _t("2026-06-01", "XYZCORP PAYMENT", "100.00").with_fields(
        category="Shopping", category_source="llm", category_confidence=0.82,
        reasoning="Generic merchant settlement, likely retail.",
    )
    persist_transactions(session, TxnModel, 1, None, [txn])

    row = session.exec(
        sqlmodel.select(TxnModel).where(TxnModel.user_id == 1)
    ).one()
    assert row.reasoning == "Generic merchant settlement, likely retail."


def test_rule_matched_row_has_no_reasoning(session) -> None:
    """A Tier-1-only row (no LLM involvement) leaves reasoning unset."""
    txn = _t("2026-06-01", "Zomato", "100.00").with_fields(
        category="Food & Dining", category_source="rule", category_confidence=1.0,
    )
    persist_transactions(session, TxnModel, 1, None, [txn])

    row = session.exec(
        sqlmodel.select(TxnModel).where(TxnModel.user_id == 1)
    ).one()
    assert row.reasoning is None