"""Story 1.3 · AC #1, #8 — registration core logic.

Tests the injectable, framework-agnostic parts of registration against a temp SQLite
session (the same harness Story 1.2 used). The thin ``rx.State`` handler that wires these
to ``rx.session()`` / ``_login`` / ``rx.redirect`` is verified by running the app (Task 4),
per the story's testing note.
"""
from __future__ import annotations

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers localuser/localauthsession tables
from finance_app.state.auth_state import is_valid_email, register_new_user
from reflex_local_auth.user import LocalUser


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


class TestEmailValidation:
    @pytest.mark.parametrize("good", ["priya@example.com", "a.b+c@sub.domain.co.in"])
    def test_valid(self, good) -> None:
        assert is_valid_email(good) is True

    @pytest.mark.parametrize("bad", ["", None, "notanemail", "no@tld", "a@b@c.com", "spaces in@x.com"])
    def test_invalid(self, bad) -> None:
        assert is_valid_email(bad) is False


class TestRegisterNewUser:
    def test_valid_registration_creates_bcrypt_user(self, session) -> None:
        result = register_new_user(session, "priya@example.com", "supersecret8")
        assert result.ok is True
        assert result.user_id is not None
        user = session.get(LocalUser, result.user_id)
        assert user is not None
        assert user.username == "priya@example.com"
        assert user.enabled is True
        # bcrypt: hash is not the plaintext, and verify() round-trips
        assert user.password_hash != b"supersecret8"
        assert b"supersecret8" not in user.password_hash
        assert user.verify("supersecret8") is True
        assert user.verify("wrongpassword") is False

    def test_email_is_normalized(self, session) -> None:
        result = register_new_user(session, "  Priya@Example.COM ", "supersecret8")
        assert result.ok is True
        assert session.get(LocalUser, result.user_id).username == "priya@example.com"

    def test_duplicate_email_sets_email_taken_and_adds_no_user(self, session) -> None:
        first = register_new_user(session, "dupe@example.com", "supersecret8")
        assert first.ok is True
        second = register_new_user(session, "dupe@example.com", "anotherpass8")
        assert second.ok is False
        assert second.email_taken is True  # drives the "Log in instead?" link (AC #8)
        count = len(session.exec(sqlmodel.select(LocalUser).where(LocalUser.username == "dupe@example.com")).all())
        assert count == 1

    def test_invalid_email_rejected_no_user(self, session) -> None:
        result = register_new_user(session, "notanemail", "supersecret8")
        assert result.ok is False
        assert result.email_taken is False
        assert result.error
        assert session.exec(sqlmodel.select(LocalUser)).first() is None

    def test_short_password_rejected_no_user(self, session) -> None:
        result = register_new_user(session, "priya@example.com", "short")
        assert result.ok is False
        assert session.exec(sqlmodel.select(LocalUser)).first() is None

    def test_overlong_password_rejected_gracefully_no_crash(self, session) -> None:
        # bcrypt raises ValueError >72 bytes; register_new_user must return a friendly
        # error instead of crashing (and create no user).
        result = register_new_user(session, "priya@example.com", "A" * 73)
        assert result.ok is False
        assert "too long" in result.error.lower()
        assert session.exec(sqlmodel.select(LocalUser)).first() is None

    def test_password_at_72_byte_boundary_is_accepted(self, session) -> None:
        result = register_new_user(session, "priya@example.com", "A" * 72)
        assert result.ok is True
        assert session.get(LocalUser, result.user_id) is not None
