"""Story 1.4 · AC #1 — login credential-check core logic.

Tests the injectable, framework-agnostic ``authenticate`` helper against a temp SQLite
session (same harness as Story 1.3's ``test_registration``). The thin ``rx.State``
``handle_login`` handler that wires this to ``rx.session()`` / ``_login`` / ``rx.redirect``
is verified by running the app (Task 5), per the story's testing note.
"""
from __future__ import annotations

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers localuser/localauthsession tables
from finance_app.state.auth_state import authenticate
from reflex_local_auth.user import LocalUser


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _make_user(session, email: str, password: str, *, enabled: bool = True) -> LocalUser:
    user = LocalUser(  # type: ignore[call-arg]
        username=email, password_hash=LocalUser.hash_password(password), enabled=enabled
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestAuthenticate:
    def test_valid_credentials_return_user(self, session) -> None:
        created = _make_user(session, "priya@example.com", "supersecret8")
        found = authenticate(session, "priya@example.com", "supersecret8")
        assert found is not None
        assert found.id == created.id

    def test_wrong_password_returns_none(self, session) -> None:
        _make_user(session, "priya@example.com", "supersecret8")
        assert authenticate(session, "priya@example.com", "wrongpassword") is None

    def test_unknown_email_returns_none(self, session) -> None:
        _make_user(session, "priya@example.com", "supersecret8")
        assert authenticate(session, "nobody@example.com", "supersecret8") is None

    def test_mixed_case_email_still_authenticates(self, session) -> None:
        # Registration stores email lowercased; login must normalize before lookup
        # (forward-requirement from Story 1.3's review — deferred-work.md).
        _make_user(session, "priya@example.com", "supersecret8")
        found = authenticate(session, "  Priya@Example.COM ", "supersecret8")
        assert found is not None
        assert found.username == "priya@example.com"

    def test_disabled_user_returns_none(self, session) -> None:
        _make_user(session, "priya@example.com", "supersecret8", enabled=False)
        assert authenticate(session, "priya@example.com", "supersecret8") is None

    def test_empty_credentials_return_none(self, session) -> None:
        _make_user(session, "priya@example.com", "supersecret8")
        assert authenticate(session, "", "") is None
        assert authenticate(session, "priya@example.com", "") is None

    def test_none_email_returns_none(self, session) -> None:
        _make_user(session, "priya@example.com", "supersecret8")
        assert authenticate(session, None, "supersecret8") is None

    def test_whitespace_only_email_returns_none(self, session) -> None:
        _make_user(session, "priya@example.com", "supersecret8")
        assert authenticate(session, "   ", "supersecret8") is None
