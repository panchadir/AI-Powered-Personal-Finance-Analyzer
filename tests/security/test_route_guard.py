"""Story 1.4 · AC #4 — protected-route guard decision.

The guard (``AuthState.check_auth``) redirects to ``/login`` whenever the cookie token has
no valid, non-expired session. Its pure decision lives in ``user_for_token``; that is what
we unit-test here. The ``rx.redirect`` wiring on each page's ``on_load`` is verified at
``reflex run`` (Task 5) — ``rx.State`` on_load handlers are not reliably testable outside a
running app.
"""
from __future__ import annotations

import datetime

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers localuser/localauthsession tables
from finance_app.state.auth_state import user_for_token
from reflex_local_auth.auth_session import LocalAuthSession
from reflex_local_auth.user import LocalUser


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _seed_user(session, email: str = "priya@example.com") -> LocalUser:
    user = LocalUser(  # type: ignore[call-arg]
        username=email, password_hash=LocalUser.hash_password("supersecret8"), enabled=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _bind_session(session, user_id: int, token: str, *, expires_in: datetime.timedelta) -> None:
    session.add(
        LocalAuthSession(  # type: ignore[call-arg]
            user_id=user_id,
            session_id=token,
            expiration=datetime.datetime.now(datetime.timezone.utc) + expires_in,
        )
    )
    session.commit()


class TestRouteGuardDecision:
    def test_valid_token_resolves_user_guard_allows(self, session) -> None:
        user = _seed_user(session)
        _bind_session(session, user.id, "tok-valid", expires_in=datetime.timedelta(days=7))
        found = user_for_token(session, "tok-valid")
        assert found is not None
        assert found.id == user.id  # guard would allow the page to load

    def test_unknown_token_returns_none_guard_redirects(self, session) -> None:
        _seed_user(session)
        assert user_for_token(session, "tok-does-not-exist") is None

    def test_empty_token_returns_none_guard_redirects(self, session) -> None:
        _seed_user(session)
        assert user_for_token(session, "") is None
        assert user_for_token(session, None) is None

    def test_expired_token_returns_none_guard_redirects(self, session) -> None:
        user = _seed_user(session)
        _bind_session(session, user.id, "tok-expired", expires_in=datetime.timedelta(days=-1))
        assert user_for_token(session, "tok-expired") is None