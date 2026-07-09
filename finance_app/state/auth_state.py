"""Authentication state for the Finance Analyzer (Story 1.3).

``AuthState`` is a **standalone** ``rx.State`` that keeps the session token in a SameSite
``rx.Cookie`` — satisfying AD-5 / FR-1.1 ("never localStorage/sessionStorage").

Why not just subclass ``reflex_local_auth.LocalAuthState``? Because its ``auth_token`` is an
``rx.LocalStorage`` var, and that parent state is registered independently — subclassing and
overriding the var does NOT stop Reflex from compiling the parent's localStorage token
(verified at ``reflex run``: the compiled ``clientStorage`` still put ``_auth_token`` in
``local_storage``). So we reuse only the library's **data models** (``LocalUser`` /
``LocalAuthSession``) and its **bcrypt** helpers, and own the session mechanism here (the
logic below is adapted from ``reflex_local_auth/local_auth.py``, ~40 lines).

AD-5 note (Phase-1 pragmatic resolution, product-approved 2026-07-09): a real *httpOnly*
cookie can't come from Reflex client state, so Phase 1 uses a SameSite cookie (not httpOnly).
True httpOnly via server-side ``Set-Cookie`` middleware is a Phase-2 item (deferred-work.md).
``secure=False`` is for local http; Phase-2/https flips it to ``True``.

This module lives in the UI layer (``finance_app/state/``), so importing ``reflex`` here is
fine — auth/session logic must never live under ``services/`` (AD-2).
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any

import reflex as rx
from reflex_local_auth.auth_session import LocalAuthSession
from reflex_local_auth.user import LocalUser
from sqlmodel import Session, select

#: How long an auth session lives (matches reflex-local-auth's default).
AUTH_SESSION_EXPIRATION_DELTA = datetime.timedelta(days=7)
#: Auth computed-var refresh cadence (matches reflex-local-auth's default).
AUTH_REFRESH_DELTA = datetime.timedelta(minutes=10)
#: Route the user lands on immediately after auto-login (FR-1.2).
POST_REGISTER_ROUTE = "/upload"
#: Minimum password length (matches the prototype's "8+ characters" hint).
MIN_PASSWORD_LENGTH = 8
#: Maximum password length in UTF-8 bytes. bcrypt rejects secrets longer than 72 bytes
#: (raises ValueError), so we validate the boundary and return a friendly error instead
#: of letting hash_password crash.
MAX_PASSWORD_BYTES = 72

# RFC-lite email check. Deliberately a small regex — we do NOT pull in
# email-validator / pydantic[email] (a new dependency); this is sufficient for MVP.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str | None) -> bool:
    """True if ``email`` looks like a valid address (single @, a dot in the domain, no spaces)."""
    return bool(email and _EMAIL_RE.match(email))


@dataclass
class RegistrationResult:
    """Outcome of a registration attempt — decouples the DB/validation logic from rx.State."""

    ok: bool
    user_id: int | None = None
    error: str = ""
    email_taken: bool = False


def register_new_user(session: Session, email: str | None, password: str | None) -> RegistrationResult:
    """Validate and create a user (email stored in the ``username`` column, bcrypt-hashed).

    Framework-agnostic and session-injected so it is unit-testable without a Reflex app.
    Does NOT touch the session token / auto-login — that is the caller's job.
    """
    email = (email or "").strip().lower()
    password = password or ""
    if not is_valid_email(email):
        return RegistrationResult(ok=False, error="Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        return RegistrationResult(
            ok=False, error=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        # bcrypt raises ValueError above 72 bytes — guard before hashing (never crash).
        return RegistrationResult(
            ok=False, error=f"Password is too long (max {MAX_PASSWORD_BYTES} characters)."
        )
    existing = session.exec(select(LocalUser).where(LocalUser.username == email)).one_or_none()
    if existing is not None:
        return RegistrationResult(
            ok=False, error="That email is already registered.", email_taken=True
        )
    user = LocalUser(username=email, password_hash=LocalUser.hash_password(password), enabled=True)  # type: ignore[call-arg]
    session.add(user)
    session.commit()
    session.refresh(user)
    return RegistrationResult(ok=True, user_id=user.id)


class AuthState(rx.State):
    """Cookie-backed session state (AD-5). Standalone — NOT a reflex-local-auth subclass."""

    # The session token lives in a SameSite cookie (AD-5), never localStorage.
    auth_token: str = rx.Cookie(
        name="_auth_token",
        same_site="strict",
        path="/",
        secure=False,  # localhost http; Phase-2/https -> True
    )

    @rx.var(cache=True, interval=AUTH_REFRESH_DELTA, initial_value=LocalUser(id=-1))  # type: ignore[call-arg]
    def authenticated_user(self) -> LocalUser:
        """The signed-in user, or a sentinel ``LocalUser(id=-1)`` when not authenticated."""
        with rx.session() as session:
            result = session.exec(
                select(LocalUser, LocalAuthSession).where(
                    LocalAuthSession.session_id == self.auth_token,
                    LocalAuthSession.expiration >= datetime.datetime.now(datetime.timezone.utc),
                    LocalUser.id == LocalAuthSession.user_id,
                )
            ).first()
            if result:
                user, _ = result
                return user
        return LocalUser(id=-1)  # type: ignore[call-arg]

    @rx.var(cache=True, interval=AUTH_REFRESH_DELTA, initial_value=False)
    def is_authenticated(self) -> bool:
        """Whether a valid, non-expired session exists for the cookie token."""
        return self.authenticated_user.id is not None and self.authenticated_user.id >= 0

    @rx.event
    def do_logout(self):
        """Delete any LocalAuthSession rows bound to the current cookie token."""
        with rx.session() as session:
            for auth_session in session.exec(
                select(LocalAuthSession).where(LocalAuthSession.session_id == self.auth_token)
            ).all():
                session.delete(auth_session)
            session.commit()
        self.auth_token = self.auth_token

    def _login(self, user_id: int, expiration_delta: datetime.timedelta = AUTH_SESSION_EXPIRATION_DELTA) -> None:
        """Create a LocalAuthSession for ``user_id``, keyed on the cookie token."""
        self.do_logout()
        if user_id < 0:
            return
        self.auth_token = self.auth_token or self.router.session.client_token
        with rx.session() as session:
            session.add(
                LocalAuthSession(  # type: ignore[call-arg]
                    user_id=user_id,
                    session_id=self.auth_token,
                    expiration=datetime.datetime.now(datetime.timezone.utc) + expiration_delta,
                )
            )
            session.commit()


class RegisterState(AuthState):
    """Handles the registration form: create account, auto-login, redirect to Upload."""

    error_message: str = ""
    email_taken: bool = False  # True when the submitted email is already registered (AC #8)
    show_password: bool = False  # drives the show/hide password toggle (AC #5)
    show_confirm: bool = False  # show/hide for the confirm-password field

    @rx.event
    def toggle_password(self):
        """Flip password field visibility (AC #5)."""
        self.show_password = not self.show_password

    @rx.event
    def toggle_confirm(self):
        """Flip confirm-password field visibility."""
        self.show_confirm = not self.show_confirm

    @rx.event
    def handle_registration(self, form_data: dict[str, Any]):
        """Register + auto-login + redirect to /upload (FR-1.2). Replaces the stock
        reflex-local-auth flow, which does not auto-login and redirects to /login."""
        self.error_message = ""
        self.email_taken = False
        password = form_data.get("password") or ""
        with rx.session() as session:
            result = register_new_user(session, form_data.get("email"), password)
        if not result.ok:
            self.error_message = result.error
            self.email_taken = result.email_taken
            return
        # Auto-login: write a LocalAuthSession keyed on our cookie token.
        self._login(result.user_id)
        return rx.redirect(POST_REGISTER_ROUTE)
