"""Epic 2 end-to-end integration: the exact seam the upload handler runs.

Each Epic-2 unit is tested in isolation (parser protocol, CSV/PDF parse, dispatch, dedup);
this chains them the way ``upload_state._run_parse`` does — raw uploaded bytes ->
``parse_statement`` -> ``persist_transactions`` -> deduped rows in the DB — so a regression at
any boundary between parse and persist is caught. Runs on a throwaway SQLite engine (AD-14),
no Reflex app and no PDF asset needed.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers all app tables
from finance_app.models import Transaction as TxnModel
from services.ingestion import parse_statement, persist_transactions
from services.utils.enums import Direction

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'pipeline.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _rows(session, user_id: int):
    return session.exec(
        sqlmodel.select(TxnModel).where(TxnModel.user_id == user_id)
    ).all()


def test_upload_pipeline_parse_then_persist_then_reupload_dedups(session) -> None:
    data = (FIXTURES / "hdfc_sample.csv").read_bytes()

    # First upload: parse the bytes, then persist for the signed-in user.
    parsed = parse_statement("hdfc_sample.csv", data)
    first = persist_transactions(session, TxnModel, 1, None, parsed)
    assert (first.inserted, first.skipped) == (4, 0)

    # Persisted rows are scoped to the user and carry the parsed values (direction stored
    # as the enum's string value).
    rows = _rows(session, 1)
    assert len(rows) == 4
    assert {r.direction for r in rows} == {Direction.debit.value, Direction.credit.value}
    assert all(r.user_id == 1 for r in rows)

    # Re-uploading the identical file (a real user habit) adds zero rows — the whole
    # parse->persist->dedup path holds end to end.
    reparsed = parse_statement("hdfc_sample.csv", data)
    second = persist_transactions(session, TxnModel, 1, None, reparsed)
    assert (second.inserted, second.skipped) == (0, 4)
    assert len(_rows(session, 1)) == 4


def test_upload_pipeline_is_user_scoped(session) -> None:
    """Two users uploading the same statement each get their own rows (AD-4)."""
    data = (FIXTURES / "sbi_sample.csv").read_bytes()
    persist_transactions(session, TxnModel, 1, None, parse_statement("s.csv", data))
    persist_transactions(session, TxnModel, 2, None, parse_statement("s.csv", data))
    assert len(_rows(session, 1)) == 3
    assert len(_rows(session, 2)) == 3