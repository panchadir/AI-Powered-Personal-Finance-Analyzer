"""Story 1.3 · AC #3 — the AD-5 tripwire.

reflex-local-auth stores the session token in ``rx.LocalStorage`` by default, which AD-5 /
FR-1.1 forbid. ``AuthState`` owns a standalone SameSite ``rx.Cookie`` token instead (Phase-1
pragmatic resolution; true httpOnly is a Phase-2 item — see deferred-work.md).

We assert on the **field default** (the ``ClientStorageBase`` instance Reflex actually
compiles into ``clientStorage``), not the class-attribute Var wrapper — the wrapper's type
is an unreliable surface (it silently passed even when the compiled token was still
localStorage; caught at ``reflex run``). We also structurally forbid inheriting
``LocalAuthState``, which would re-introduce the localStorage token regardless of overrides.
"""
from __future__ import annotations

import reflex_local_auth
from reflex.istate.storage import Cookie, LocalStorage

from finance_app.state.auth_state import AuthState


def _auth_token_backing():
    return AuthState.get_fields()["auth_token"].default


def test_auth_token_backed_by_cookie_not_localstorage() -> None:
    backing = _auth_token_backing()
    assert isinstance(backing, Cookie), (
        f"AD-5: auth token must compile to a cookie, got {type(backing).__name__}."
    )
    assert not isinstance(backing, LocalStorage)


def test_auth_token_cookie_is_samesite() -> None:
    # AD-5 requires a SameSite cookie.
    assert _auth_token_backing().same_site == "strict"


def test_auth_state_does_not_inherit_localauthstate() -> None:
    # Structural guard: subclassing reflex-local-auth's LocalAuthState smuggles in its
    # rx.LocalStorage auth_token, which Reflex compiles regardless of a subclass override
    # (verified at reflex run — the compiled clientStorage kept the token in local_storage).
    assert not issubclass(AuthState, reflex_local_auth.LocalAuthState), (
        "AuthState must NOT inherit LocalAuthState — that re-introduces the localStorage token (AD-5)."
    )
