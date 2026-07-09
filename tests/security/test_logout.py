"""Story 1.4 · AC #3 — logout clears the session.

Tests the DB effect of logout (delete every ``LocalAuthSession`` bound to the cookie token)
via the injectable ``clear_sessions_for_token`` helper. The cookie-clear + ``rx.redirect``
to ``/login`` are app-verified at ``reflex run`` (Task 5).
"""
from __future__ import annotations

import datetime

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers localuser/localauthsession tables
from finance_app.state.auth_state import clear_sessions_for_token, user_for_token
from reflex_local_auth.auth_session import LocalAuthSession
from reflex_local_auth.user import LocalUser


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _seed_user_with_session(session, token: str) -> LocalUser:
    user = LocalUser(  # type: ignore[call-arg]
        username=f"user-{token}@example.com",  # unique per token (localuser.username is unique)
        password_hash=LocalUser.hash_password("supersecret8"),
        enabled=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(
        LocalAuthSession(  # type: ignore[call-arg]
            user_id=user.id,
            session_id=token,
            expiration=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        )
    )
    session.commit()
    return user


class TestLogout:
    def test_logout_deletes_the_session_for_the_token(self, session) -> None:
        _seed_user_with_session(session, "tok-live")
        # Session resolves before logout...
        assert user_for_token(session, "tok-live") is not None
        removed = clear_sessions_for_token(session, "tok-live")
        assert removed == 1
        # ...and no longer resolves after (cookie token is now dead → guard would redirect).
        assert user_for_token(session, "tok-live") is None

    def test_logout_only_clears_the_matching_token(self, session) -> None:
        _seed_user_with_session(session, "tok-a")
        _seed_user_with_session(session, "tok-b")
        clear_sessions_for_token(session, "tok-a")
        assert user_for_token(session, "tok-a") is None
        assert user_for_token(session, "tok-b") is not None  # unrelated session untouched

    def test_logout_with_empty_token_is_a_noop(self, session) -> None:
        _seed_user_with_session(session, "tok-live")
        assert clear_sessions_for_token(session, "") == 0
        assert clear_sessions_for_token(session, None) == 0
        assert user_for_token(session, "tok-live") is not None