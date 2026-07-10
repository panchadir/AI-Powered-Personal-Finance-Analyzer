"""Story 1.4 · AC #5 — IDOR baseline (AD-4 user_id scoping).

Proves the core isolation invariant on one representative user-scoped table (``transactions``)
plus the cookie-token → ``user_id`` binding: User A's session never resolves to User B, and a
``user_id``-filtered query returns only its owner's rows. The exhaustive cross-user sweep across
transactions / commitments / chat is Epic 8, Story 8.3 — this is the single-table baseline.
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers all app tables
from finance_app.models import Transaction
from finance_app.state.auth_state import user_for_token
from reflex_local_auth.auth_session import LocalAuthSession
from reflex_local_auth.user import LocalUser


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
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


class TestIdorBaseline:
    def test_user_a_cannot_see_user_b_transactions(self, session) -> None:
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        # Both A and B have a row, so an empty A result can't be confused with an empty table.
        session.add(
            Transaction(  # type: ignore[call-arg]
                user_id=user_a.id,
                date="2026-06-29",
                description_raw="ZOMATO",
                amount=Decimal("640.00"),
                direction="debit",
            )
        )
        session.add(
            Transaction(  # type: ignore[call-arg]
                user_id=user_b.id,
                date="2026-06-30",
                description_raw="SWIGGY",
                amount=Decimal("250.00"),
                direction="debit",
            )
        )
        session.commit()

        a_rows = session.exec(select_txn(user_a.id)).all()
        b_rows = session.exec(select_txn(user_b.id)).all()
        # A sees exactly its own row and nothing of B's (proves the filter works, not that
        # the table is empty).
        assert len(a_rows) == 1
        assert a_rows[0].user_id == user_a.id
        assert a_rows[0].description_raw == "ZOMATO"
        assert len(b_rows) == 1
        assert b_rows[0].user_id == user_b.id
        assert b_rows[0].description_raw == "SWIGGY"

    def test_session_token_resolves_only_to_its_owner(self, session) -> None:
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        session.add(
            LocalAuthSession(  # type: ignore[call-arg]
                user_id=user_a.id,
                session_id="tok-a",
                expiration=datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=7),
            )
        )
        session.commit()

        resolved = user_for_token(session, "tok-a")
        assert resolved is not None
        assert resolved.id == user_a.id
        assert resolved.id != user_b.id  # A's cookie token never resolves to B


def select_txn(user_id: int):
    """The user_id-scoped query every service read must mirror (AD-4)."""
    return sqlmodel.select(Transaction).where(Transaction.user_id == user_id)
