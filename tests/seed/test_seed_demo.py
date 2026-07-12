"""Story 8.4 — seed_demo.py correctness and idempotency tests."""
from __future__ import annotations

import json
import sqlmodel
import pytest

import finance_app.models  # noqa: F401 — registers tables
from finance_app.models import Commitment, Transaction as TxnModel
from reflex_local_auth.user import LocalUser
from scripts.seed_demo import _DATA_FILE, _DEMO_COMMITMENTS

_EXPECTED_TXN_COUNT = len(json.loads(_DATA_FILE.read_text(encoding="utf-8")))
_EXPECTED_COMMITMENT_COUNT = len(_DEMO_COMMITMENTS)


@pytest.fixture
def engine(tmp_path):
    db_engine = sqlmodel.create_engine(
        f"sqlite:///{tmp_path / 'seed_test.db'}",
        connect_args={"check_same_thread": False},
    )
    sqlmodel.SQLModel.metadata.create_all(db_engine)
    yield db_engine


def test_seed_creates_demo_user(engine):
    from scripts.seed_demo import seed, _DEMO_EMAIL

    seed(engine=engine)

    with sqlmodel.Session(engine) as session:
        user = session.exec(
            sqlmodel.select(LocalUser).where(LocalUser.username == _DEMO_EMAIL)
        ).first()
    assert user is not None
    assert user.enabled is True


def test_seed_inserts_transactions(engine):
    from scripts.seed_demo import seed

    result = seed(engine=engine)

    assert result["transactions_inserted"] == _EXPECTED_TXN_COUNT

    with sqlmodel.Session(engine) as session:
        count = session.exec(
            sqlmodel.select(sqlmodel.func.count()).select_from(TxnModel).where(
                TxnModel.user_id == result["user_id"]
            )
        ).one()
    assert count == _EXPECTED_TXN_COUNT


def test_seed_inserts_commitments(engine):
    from scripts.seed_demo import seed

    result = seed(engine=engine)

    assert result["commitments_inserted"] == _EXPECTED_COMMITMENT_COUNT

    with sqlmodel.Session(engine) as session:
        count = session.exec(
            sqlmodel.select(sqlmodel.func.count()).select_from(Commitment).where(
                Commitment.user_id == result["user_id"]
            )
        ).one()
    assert count == _EXPECTED_COMMITMENT_COUNT


def test_seed_is_idempotent(engine):
    """Running seed twice must not double-insert rows."""
    from scripts.seed_demo import seed

    result1 = seed(engine=engine)
    result2 = seed(engine=engine)

    # Second run inserts nothing new
    assert result2["transactions_inserted"] == 0
    assert result2["commitments_inserted"] == 0
    # Same user
    assert result1["user_id"] == result2["user_id"]

    with sqlmodel.Session(engine) as session:
        txn_count = session.exec(
            sqlmodel.select(sqlmodel.func.count()).select_from(TxnModel).where(
                TxnModel.user_id == result1["user_id"]
            )
        ).one()
        commitment_count = session.exec(
            sqlmodel.select(sqlmodel.func.count()).select_from(Commitment).where(
                Commitment.user_id == result1["user_id"]
            )
        ).one()
    assert txn_count == _EXPECTED_TXN_COUNT
    assert commitment_count == _EXPECTED_COMMITMENT_COUNT


def test_seed_reset_clears_and_reseeds(engine):
    """--reset wipes existing data and re-seeds cleanly."""
    from scripts.seed_demo import seed

    # First seed
    result1 = seed(engine=engine)
    user_id = result1["user_id"]

    # Reset
    result2 = seed(reset=True, engine=engine)
    assert result2["user_id"] == user_id
    assert result2["transactions_inserted"] == _EXPECTED_TXN_COUNT
    assert result2["commitments_inserted"] == _EXPECTED_COMMITMENT_COUNT

    with sqlmodel.Session(engine) as session:
        txn_count = session.exec(
            sqlmodel.select(sqlmodel.func.count()).select_from(TxnModel).where(
                TxnModel.user_id == user_id
            )
        ).one()
    assert txn_count == _EXPECTED_TXN_COUNT


def test_seed_demo_password_hash_is_set(engine):
    """Demo user must have a non-empty bcrypt password hash."""
    from scripts.seed_demo import seed

    seed(engine=engine)

    with sqlmodel.Session(engine) as session:
        from scripts.seed_demo import _DEMO_EMAIL
        user = session.exec(
            sqlmodel.select(LocalUser).where(LocalUser.username == _DEMO_EMAIL)
        ).first()
    assert user is not None
    # reflex-local-auth 0.5.0 stores bcrypt hashes as bytes; b'$2b$' is the bcrypt prefix
    assert user.password_hash and user.password_hash[:4] == b"$2b$"
