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
#: Post-authentication landing page (Statement Upload). The WDS prototype routes both a
#: fresh login and the existing-user path here (README: Login → Upload).
HOME_ROUTE = "/upload"
#: Back-compat alias. Registration itself no longer auto-logs-in (the WDS prototype shows a
#: "Registration successful → Return to Login" screen instead — product decision 2026-07-09),
#: so this is now only the post-*login* destination.
POST_REGISTER_ROUTE = HOME_ROUTE
#: Login route (reused from reflex-local-auth so links stay consistent app-wide).
LOGIN_ROUTE = "/login"
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


def authenticate(session: Session, email: str | None, password: str | None) -> LocalUser | None:
    """Return the ``LocalUser`` for valid credentials, else ``None``.

    Framework-agnostic and session-injected so it is unit-testable without a Reflex app.
    Email is normalized (trimmed + lowercased) to match registration's storage. The caller
    surfaces a **uniform** error whether the email is unknown or the password is wrong — this
    helper never distinguishes the two (no user enumeration).
    """
    email = (email or "").strip().lower()
    if not email or not password:
        return None
    user = session.exec(select(LocalUser).where(LocalUser.username == email)).one_or_none()
    if user is None or not user.enabled or not user.verify(password):
        return None
    return user


def user_for_token(session: Session, token: str | None) -> LocalUser | None:
    """Return the ``LocalUser`` bound to a valid, non-expired session ``token``, else ``None``.

    The single source of truth for "is this cookie token a live session?" — reused by
    ``AuthState.authenticated_user`` (UI reactivity), ``AuthState.check_auth`` (route guard),
    and the IDOR baseline test. Session-injected so the decision is unit-testable.
    """
    if not token:
        return None
    row = session.exec(
        select(LocalUser, LocalAuthSession).where(
            LocalAuthSession.session_id == token,
            LocalAuthSession.expiration >= datetime.datetime.now(datetime.timezone.utc),
            LocalUser.id == LocalAuthSession.user_id,
        )
    ).first()
    return row[0] if row else None


def clear_sessions_for_token(session: Session, token: str | None) -> int:
    """Delete every ``LocalAuthSession`` bound to ``token``; return how many were removed.

    The DB side of logout (AC #3). Session-injected so the effect is unit-testable.
    """
    if not token:
        return 0
    rows = session.exec(
        select(LocalAuthSession).where(LocalAuthSession.session_id == token)
    ).all()
    for row in rows:
        session.delete(row)
    session.commit()
    return len(rows)


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
            user = user_for_token(session, self.auth_token)
            if user is not None:
                return user
        return LocalUser(id=-1)  # type: ignore[call-arg]

    @rx.var(cache=True, interval=AUTH_REFRESH_DELTA, initial_value=False)
    def is_authenticated(self) -> bool:
        """Whether a valid, non-expired session exists for the cookie token."""
        return self.authenticated_user.id is not None and self.authenticated_user.id >= 0

    @rx.event
    def check_auth(self):
        """Route guard (AD-4/AC #4): redirect to login when the cookie token has no live session.

        Wire as an ``on_load`` on every protected page. Reads the session **fresh** (not the
        cached ``is_authenticated`` var, which is interval-refreshed and can be stale on first
        load). Returns ``None`` when authenticated so the page renders normally.
        """
        with rx.session() as session:
            if user_for_token(session, self.auth_token) is None:
                return rx.redirect(LOGIN_ROUTE)

    @rx.event
    def do_logout(self):
        """Delete any LocalAuthSession rows bound to the current cookie token."""
        with rx.session() as session:
            clear_sessions_for_token(session, self.auth_token)
        # Re-assign to force Reflex to re-emit the (now session-less) cookie to the browser.
        self.auth_token = self.auth_token

    @rx.event
    def logout(self):
        """Clear the session and redirect to login."""
        self.do_logout()
        return rx.redirect(LOGIN_ROUTE)

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
    """Registration form state, mirroring the WDS prototype (01.1-register.html).

    Flow matches the approved prototype: client-side per-field validation → server-side
    create → **no auto-login** → a "Registration successful → Return to Login" success
    screen (product decision 2026-07-09; supersedes the earlier FR-1.2 auto-login).
    """

    # Per-field inline errors (prototype shows each empty/invalid field its own message).
    email_error: str = ""
    password_error: str = ""
    confirm_error: str = ""
    # Form-level error for network/unexpected failures (prototype toast).
    error_message: str = ""
    email_taken: bool = False  # True when the submitted email is already registered (AC #8)
    show_password: bool = False  # drives the show/hide password toggle (AC #5)
    show_confirm: bool = False  # show/hide for the confirm-password field
    registration_success: bool = False  # swaps the form for the success panel (no auto-login)
    password_value: str = ""  # tracked so blur_confirm can cross-check for a match

    @rx.event
    def toggle_password(self):
        """Flip password field visibility (AC #5)."""
        self.show_password = not self.show_password

    @rx.event
    def toggle_confirm(self):
        """Flip confirm-password field visibility."""
        self.show_confirm = not self.show_confirm

    @rx.event
    def reset_form(self):
        """Clear inline errors and the success panel (used when the page mounts)."""
        self.email_error = self.password_error = self.confirm_error = self.error_message = ""
        self.email_taken = False
        self.registration_success = False
        self.password_value = ""

    # ---- Blur-triggered per-field validation ----

    @rx.event
    def blur_email(self, value: str):
        email = (value or "").strip()
        if not email:
            self.email_error = "Please enter your email address"
        elif not is_valid_email(email):
            self.email_error = "That doesn't look like a valid email"
        else:
            self.email_error = ""
            self.email_taken = False

    @rx.event
    def blur_password(self, value: str):
        password = value or ""
        self.password_value = password
        if not password:
            self.password_error = "Please create a password"
        elif len(password) < MIN_PASSWORD_LENGTH:
            self.password_error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        else:
            self.password_error = ""

    @rx.event
    def blur_confirm(self, value: str):
        if not value:
            self.confirm_error = "Please confirm your password"
        elif value != self.password_value:
            self.confirm_error = "Passwords don't match"
        else:
            self.confirm_error = ""

    # ---- Clear-on-input handlers ----

    @rx.event
    def change_email(self, value: str):  # noqa: ARG002
        if self.email_error or self.email_taken:
            self.email_error = ""
            self.email_taken = False

    @rx.event
    def change_password(self, value: str):
        self.password_value = value
        if self.password_error:
            self.password_error = ""

    @rx.event
    def change_confirm(self, value: str):  # noqa: ARG002
        if self.confirm_error:
            self.confirm_error = ""

    def _validate(self, email: str, password: str, confirm: str) -> bool:
        """Client-side validation matching the prototype; sets every field's message."""
        self.email_error = self.password_error = self.confirm_error = ""
        email = (email or "").strip()
        if not email:
            self.email_error = "Please enter your email address"
        elif not is_valid_email(email):
            self.email_error = "That doesn't look like a valid email"
        if not password:
            self.password_error = "Please create a password"
        elif len(password) < MIN_PASSWORD_LENGTH:
            self.password_error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        if not confirm:
            self.confirm_error = "Please confirm your password"
        elif confirm != password:
            self.confirm_error = "Passwords don't match"
        return not (self.email_error or self.password_error or self.confirm_error)

    @rx.event
    def handle_registration(self, form_data: dict[str, Any]):
        """Validate → create account → show the success screen (no auto-login, no redirect)."""
        self.error_message = ""
        self.email_taken = False
        email = form_data.get("email") or ""
        password = form_data.get("password") or ""
        confirm = form_data.get("confirm_password") or ""
        if not self._validate(email, password, confirm):
            return
        with rx.session() as session:
            result = register_new_user(session, email, password)
        if not result.ok:
            # Duplicate email surfaces on the email field (with an inline "Log in instead?"
            # link, AC #8); anything else is a form-level message.
            if result.email_taken:
                self.email_error = result.error
                self.email_taken = True
            else:
                self.error_message = result.error
            return
        # Success: DO NOT create a session or redirect. Show "Return to Login" (prototype).
        self.registration_success = True


class LoginState(AuthState):
    """Login form state, mirroring the WDS prototype (01.2-login.html): validate credentials,
    open a cookie-backed session, redirect to the Upload landing page."""

    email_error: str = ""
    password_error: str = ""
    form_error: str = ""  # invalid-credentials / server error (prototype's form-level banner)
    show_password: bool = False
    reset_notice: str = ""  # success toast after a password reset (prototype)

    # Forgot-password modal (prototype's in-page reset dialog).
    forgot_open: bool = False
    forgot_email_error: str = ""
    forgot_password_error: str = ""
    forgot_confirm_error: str = ""
    _forgot_password_value: str = ""  # tracked so blur_forgot_confirm can cross-check

    @rx.event
    def toggle_password(self):
        self.show_password = not self.show_password

    @rx.event
    def reset_form(self):
        self.email_error = self.password_error = self.form_error = ""
        self.reset_notice = ""

    # ---- Blur-triggered validation + clear-on-input ----

    @rx.event
    def blur_email(self, value: str):
        email = (value or "").strip()
        if not email:
            self.email_error = "Please enter your email"
        elif not is_valid_email(email):
            self.email_error = "That doesn't look like a valid email"
        else:
            self.email_error = ""

    @rx.event
    def blur_password(self, value: str):
        if not (value or ""):
            self.password_error = "Please enter your password"
        else:
            self.password_error = ""

    @rx.event
    def change_email(self, value: str):  # noqa: ARG002
        if self.email_error:
            self.email_error = ""

    @rx.event
    def change_password(self, value: str):  # noqa: ARG002
        if self.password_error:
            self.password_error = ""

    # ---- Blur handlers for the forgot-password modal fields ----

    @rx.event
    def blur_forgot_email(self, value: str):
        email = (value or "").strip()
        if not email:
            self.forgot_email_error = "Enter your account email"
        elif not is_valid_email(email):
            self.forgot_email_error = "That doesn't look like a valid email"
        else:
            self.forgot_email_error = ""

    @rx.event
    def blur_forgot_password(self, value: str):
        password = value or ""
        if not password:
            self.forgot_password_error = f"At least {MIN_PASSWORD_LENGTH} characters"
        elif len(password) < MIN_PASSWORD_LENGTH:
            self.forgot_password_error = f"At least {MIN_PASSWORD_LENGTH} characters"
        elif len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            self.forgot_password_error = f"Password is too long (max {MAX_PASSWORD_BYTES} characters)"
        else:
            self.forgot_password_error = ""
        self._forgot_password_value = password

    @rx.event
    def blur_forgot_confirm(self, value: str):
        if not value:
            self.forgot_confirm_error = "Please confirm your new password"
        elif value != self._forgot_password_value:
            self.forgot_confirm_error = "Passwords don't match"
        else:
            self.forgot_confirm_error = ""

    @rx.event
    def change_forgot_email(self, value: str):  # noqa: ARG002
        if self.forgot_email_error:
            self.forgot_email_error = ""

    @rx.event
    def change_forgot_password(self, value: str):
        self._forgot_password_value = value
        if self.forgot_password_error:
            self.forgot_password_error = ""

    @rx.event
    def change_forgot_confirm(self, value: str):  # noqa: ARG002
        if self.forgot_confirm_error:
            self.forgot_confirm_error = ""

    @rx.event
    def open_forgot(self):
        self.forgot_email_error = self.forgot_password_error = self.forgot_confirm_error = ""
        self._forgot_password_value = ""
        self.forgot_open = True

    @rx.event
    def set_forgot_open(self, is_open: bool):
        self.forgot_open = is_open

    @rx.event
    def handle_forgot(self, form_data: dict[str, Any]):
        """Demo reset: set a new password directly (production would email a signed link)."""
        self.forgot_email_error = self.forgot_password_error = self.forgot_confirm_error = ""
        email = (form_data.get("email") or "").strip().lower()
        new_password = form_data.get("new_password") or ""
        confirm = form_data.get("confirm_password") or ""
        if not email or not is_valid_email(email):
            self.forgot_email_error = "Enter your account email"
        if len(new_password) < MIN_PASSWORD_LENGTH:
            self.forgot_password_error = f"At least {MIN_PASSWORD_LENGTH} characters"
        elif len(new_password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            self.forgot_password_error = f"Password is too long (max {MAX_PASSWORD_BYTES} characters)"
        if confirm != new_password:
            self.forgot_confirm_error = "Passwords don't match"
        if self.forgot_email_error or self.forgot_password_error or self.forgot_confirm_error:
            return
        with rx.session() as session:
            user = session.exec(select(LocalUser).where(LocalUser.username == email)).one_or_none()
            if user is None:
                self.forgot_email_error = "No account found for that email"
                return
            user.password_hash = LocalUser.hash_password(new_password)
            session.add(user)
            session.commit()
        self.forgot_open = False
        self.reset_notice = "Password updated — please log in with your new password."

    @rx.event
    def handle_login(self, form_data: dict[str, Any]):
        """Validate, verify the bcrypt hash, open a session, and go to Upload."""
        self.email_error = self.password_error = self.form_error = ""
        email = (form_data.get("email") or "").strip().lower()
        password = form_data.get("password") or ""
        if not email:
            self.email_error = "Please enter your email"
        elif not is_valid_email(email):
            self.email_error = "That doesn't look like a valid email"
        if not password:
            self.password_error = "Please enter your password"
        if self.email_error or self.password_error:
            return
        with rx.session() as session:
            user = authenticate(session, email, password)
        # Uniform message whether the email is unknown or the password is wrong (no user enumeration).
        if user is None:
            self.form_error = "Invalid email or password. Please try again."
            return
        self._login(user.id)
        return rx.redirect(HOME_ROUTE)
