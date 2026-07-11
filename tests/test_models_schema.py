"""Story 1.2 · AC #1, #2, #3, #7 — database schema contract.

Builds the schema on a throwaway SQLite file via a plain SQLAlchemy engine (no Reflex app
started — AD-14) and asserts: all 8 tables exist, every user-scoped table has an integer
``id`` PK + ``user_id`` FK, the canonical transaction columns (AD-6) and ``score_events``
columns (AD-9, incl. the ``trigger_event`` spelling) are present, money columns are not
floats, and ``commitments.criticality`` defaults to ``important``.

``users`` is satisfied by reflex-local-auth's ``localuser`` table (see models.py) — the
library owns user identity; we do not hand-roll a second users table.
"""
from __future__ import annotations

from decimal import Decimal

import sqlmodel
from sqlalchemy import inspect as sa_inspect

import finance_app.models as models  # noqa: F401  — importing registers all tables + localuser
from services.utils.enums import CategorySource, Criticality, Direction

USER_SCOPED_TABLES = [
    "uploaded_files",
    "transactions",
    "merchant_rules",
    "commitments",
    "score_events",
    "insights",
    "chat_messages",
]
# 8th table = the reflex-local-auth user identity table (the "users" table).
USERS_TABLE = "localuser"


def _make_inspector(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'schema.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    return sa_inspect(engine)


def test_all_eight_tables_created(tmp_path) -> None:
    insp = _make_inspector(tmp_path)
    tables = set(insp.get_table_names())
    expected = set(USER_SCOPED_TABLES) | {USERS_TABLE}
    missing = expected - tables
    assert not missing, f"missing tables: {sorted(missing)} (present: {sorted(tables)})"


def test_user_scoped_tables_have_int_pk_and_user_id_fk(tmp_path) -> None:
    insp = _make_inspector(tmp_path)
    for table in USER_SCOPED_TABLES:
        cols = {c["name"]: c for c in insp.get_columns(table)}
        assert "id" in cols, f"{table} missing id PK"
        pk = insp.get_pk_constraint(table)["constrained_columns"]
        assert pk == ["id"], f"{table} PK is {pk}, expected ['id']"
        assert "user_id" in cols, f"{table} missing user_id column"
        fk_targets = {
            fk["referred_table"] for fk in insp.get_foreign_keys(table)
            if "user_id" in fk["constrained_columns"]
        }
        assert USERS_TABLE in fk_targets, f"{table}.user_id does not FK to {USERS_TABLE} (got {fk_targets})"


def test_transactions_has_canonical_ad6_columns(tmp_path) -> None:
    insp = _make_inspector(tmp_path)
    cols = {c["name"] for c in insp.get_columns("transactions")}
    canonical = {
        "id", "user_id", "source_file_id", "date", "description_raw",
        "merchant_normalized", "amount", "direction", "balance_after",
        "category", "category_source", "category_confidence", "reasoning", "created_at",
    }
    assert canonical <= cols, f"transactions missing canonical columns: {canonical - cols}"


def test_score_events_uses_trigger_event_spelling(tmp_path) -> None:
    insp = _make_inspector(tmp_path)
    cols = {c["name"] for c in insp.get_columns("score_events")}
    assert "trigger_event" in cols, "score_events must have trigger_event (AD-9/CS-3)"
    assert "triggering_event" not in cols, "column must be trigger_event, not triggering_event"
    assert {"score", "delta", "explanation", "suggested_action", "timestamp"} <= cols


def test_money_columns_are_not_float(tmp_path) -> None:
    insp = _make_inspector(tmp_path)
    money = {"transactions": ["amount", "balance_after"], "commitments": ["amount"]}
    for table, columns in money.items():
        typed = {c["name"]: str(c["type"]).upper() for c in insp.get_columns(table)}
        for col in columns:
            assert "FLOAT" not in typed[col] and "REAL" not in typed[col], (
                f"{table}.{col} is {typed[col]} — money must be Decimal/NUMERIC, not float (AD-8)"
            )
            assert "NUMERIC" in typed[col] or "DECIMAL" in typed[col], (
                f"{table}.{col} is {typed[col]} — expected NUMERIC/DECIMAL"
            )


def test_criticality_defaults_to_important() -> None:
    c = models.Commitment(user_id=1, name="Rent", amount=Decimal("18000"), due_day=5)
    assert c.criticality == "important"


def test_enums_have_exact_values() -> None:
    assert {d.value for d in Direction} == {"credit", "debit"}
    assert {c.value for c in CategorySource} == {"rule", "llm", "user"}
    assert {c.value for c in Criticality} == {"critical", "important", "flexible"}
