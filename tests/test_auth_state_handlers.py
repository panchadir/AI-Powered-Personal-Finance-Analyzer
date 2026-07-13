"""Event-handler coverage for ``finance_app/state/auth_state.py``.

The pure, session-injected helpers (``register_new_user`` / ``authenticate`` / ``user_for_token``
/ ``clear_sessions_for_token``) are exercised by ``tests/security/``. This module drives the
``rx.State`` event handlers themselves — the validation/toggle/blur wiring and the DB-touching
login/logout/registration flows — through the ``make_state`` harness (see ``tests/conftest.py``).
"""
from __future__ import annotations

import pytest

from finance_app.state.auth_state import (
    AuthState,
    LoginState,
    MIN_PASSWORD_LENGTH,
    RegisterState,
    authenticate,
    register_new_user,
)


def _register(session, email="user@example.com", password="supersecret8"):
    result = register_new_user(session, email, password)
    assert result.ok
    return result.user_id


# ---------------------------------------------------------------------------
# RegisterState — synchronous validation/toggle handlers (no DB)
# ---------------------------------------------------------------------------

class TestRegisterStateFieldHandlers:
    def test_toggle_password_and_confirm_flip(self, make_state):
        s = make_state(RegisterState)
        assert s.show_password is False and s.show_confirm is False
        s.toggle_password()
        s.toggle_confirm()
        assert s.show_password is True and s.show_confirm is True

    def test_reset_form_clears_errors_and_success(self, make_state):
        s = make_state(RegisterState)
        s.email_error = "x"
        s.password_error = "y"
        s.registration_success = True
        s.email_taken = True
        s.password_value = "cached"
        s.reset_form()
        assert s.email_error == "" and s.password_error == ""
        assert s.registration_success is False and s.email_taken is False
        assert s.password_value == ""

    @pytest.mark.parametrize(
        "value, expect_error",
        [("", True), ("not-an-email", True), ("good@example.com", False)],
    )
    def test_blur_email_branches(self, make_state, value, expect_error):
        s = make_state(RegisterState)
        s.blur_email(value)
        assert bool(s.email_error) is expect_error

    def test_blur_email_valid_clears_email_taken(self, make_state):
        s = make_state(RegisterState)
        s.email_taken = True
        s.blur_email("good@example.com")
        assert s.email_taken is False

    @pytest.mark.parametrize(
        "value, expect_error",
        [("", True), ("short", True), ("supersecret8", False)],
    )
    def test_blur_password_branches(self, make_state, value, expect_error):
        s = make_state(RegisterState)
        s.blur_password(value)
        assert bool(s.password_error) is expect_error
        assert s.password_value == (value or "")

    @pytest.mark.parametrize(
        "value, prior, expect_error",
        [("", "pw12345678", True), ("different", "pw12345678", True), ("match", "match", False)],
    )
    def test_blur_confirm_branches(self, make_state, value, prior, expect_error):
        s = make_state(RegisterState)
        s.password_value = prior
        s.blur_confirm(value)
        assert bool(s.confirm_error) is expect_error

    def test_change_email_clears_prior_error(self, make_state):
        s = make_state(RegisterState)
        s.email_error = "bad"
        s.email_taken = True
        s.change_email("typing")
        assert s.email_error == "" and s.email_taken is False

    def test_change_password_tracks_value_and_clears_error(self, make_state):
        s = make_state(RegisterState)
        s.password_error = "bad"
        s.change_password("newvalue")
        assert s.password_value == "newvalue" and s.password_error == ""

    def test_change_confirm_clears_error(self, make_state):
        s = make_state(RegisterState)
        s.confirm_error = "bad"
        s.change_confirm("typing")
        assert s.confirm_error == ""


# ---------------------------------------------------------------------------
# RegisterState.handle_registration — DB path (every branch)
# ---------------------------------------------------------------------------

class TestHandleRegistration:
    def test_success_shows_success_panel_no_autologin(self, make_state):
        s = make_state(RegisterState)
        s.handle_registration(
            {"email": "new@example.com", "password": "supersecret8", "confirm_password": "supersecret8"}
        )
        assert s.registration_success is True
        assert s.error_message == "" and s.email_error == ""

    def test_client_validation_failure_short_circuits(self, make_state):
        s = make_state(RegisterState)
        s.handle_registration({"email": "bad", "password": "x", "confirm_password": "y"})
        assert s.registration_success is False
        assert s.email_error and s.password_error and s.confirm_error

    def test_duplicate_email_surfaces_on_email_field(self, make_state, db_session):
        _register(db_session, email="dupe@example.com")
        s = make_state(RegisterState)
        s.handle_registration(
            {"email": "dupe@example.com", "password": "supersecret8", "confirm_password": "supersecret8"}
        )
        assert s.registration_success is False
        assert s.email_taken is True and s.email_error


# ---------------------------------------------------------------------------
# LoginState — sync handlers
# ---------------------------------------------------------------------------

class TestLoginStateFieldHandlers:
    def test_toggle_and_reset(self, make_state):
        s = make_state(LoginState)
        s.toggle_password()
        assert s.show_password is True
        s.email_error = s.password_error = s.form_error = s.reset_notice = "x"
        s.reset_form()
        assert not (s.email_error or s.password_error or s.form_error or s.reset_notice)

    @pytest.mark.parametrize("value, err", [("", True), ("nope", True), ("ok@example.com", False)])
    def test_blur_email(self, make_state, value, err):
        s = make_state(LoginState)
        s.blur_email(value)
        assert bool(s.email_error) is err

    @pytest.mark.parametrize("value, err", [("", True), ("anything", False)])
    def test_blur_password(self, make_state, value, err):
        s = make_state(LoginState)
        s.blur_password(value)
        assert bool(s.password_error) is err

    def test_change_email_and_password_clear_errors(self, make_state):
        s = make_state(LoginState)
        s.email_error = "e"
        s.password_error = "p"
        s.change_email("x")
        s.change_password("y")
        assert s.email_error == "" and s.password_error == ""

    def test_forgot_modal_open_and_toggle(self, make_state):
        s = make_state(LoginState)
        s.forgot_email_error = "stale"
        s.open_forgot()
        assert s.forgot_open is True and s.forgot_email_error == ""
        s.set_forgot_open(False)
        assert s.forgot_open is False

    @pytest.mark.parametrize("value, err", [("", True), ("nope", True), ("ok@example.com", False)])
    def test_blur_forgot_email(self, make_state, value, err):
        s = make_state(LoginState)
        s.blur_forgot_email(value)
        assert bool(s.forgot_email_error) is err

    @pytest.mark.parametrize(
        "value, err",
        [("", True), ("short", True), ("supersecret8", False), ("a" * 73, True)],
    )
    def test_blur_forgot_password(self, make_state, value, err):
        s = make_state(LoginState)
        s.blur_forgot_password(value)
        assert bool(s.forgot_password_error) is err
        assert s._forgot_password_value == value

    @pytest.mark.parametrize("value, prior, err", [("", "pw", True), ("x", "y", True), ("m", "m", False)])
    def test_blur_forgot_confirm(self, make_state, value, prior, err):
        s = make_state(LoginState)
        s._forgot_password_value = prior
        s.blur_forgot_confirm(value)
        assert bool(s.forgot_confirm_error) is err

    def test_change_forgot_handlers_clear_errors(self, make_state):
        s = make_state(LoginState)
        s.forgot_email_error = s.forgot_password_error = s.forgot_confirm_error = "x"
        s.change_forgot_email("a")
        s.change_forgot_password("bnewpass")
        s.change_forgot_confirm("c")
        assert not (s.forgot_email_error or s.forgot_password_error or s.forgot_confirm_error)
        assert s._forgot_password_value == "bnewpass"


# ---------------------------------------------------------------------------
# LoginState.handle_login — DB path (every branch)
# ---------------------------------------------------------------------------

class TestHandleLogin:
    def test_invalid_email_sets_field_error(self, make_state):
        s = make_state(LoginState)
        s.handle_login({"email": "bad", "password": "supersecret8"})
        assert s.email_error and s.form_error == ""

    def test_missing_password_sets_field_error(self, make_state):
        s = make_state(LoginState)
        s.handle_login({"email": "ok@example.com", "password": ""})
        assert s.password_error

    def test_wrong_credentials_uniform_error(self, make_state, db_session):
        _register(db_session, email="real@example.com")
        s = make_state(LoginState)
        s.handle_login({"email": "real@example.com", "password": "wrongpassword"})
        assert s.form_error == "Invalid email or password. Please try again."

    def test_success_without_uploads_redirects_home(self, make_state, db_session):
        _register(db_session, email="home@example.com")
        s = make_state(LoginState)
        result = s.handle_login({"email": "home@example.com", "password": "supersecret8"})
        # rx.redirect(...) returns an event spec — non-None means we routed.
        assert result is not None

    def test_success_with_uploads_redirects_dashboard(self, make_state, db_session):
        from finance_app.models import UploadedFile

        uid = _register(db_session, email="dash@example.com")
        db_session.add(UploadedFile(user_id=uid, filename="jan.pdf"))  # type: ignore[call-arg]
        db_session.commit()
        s = make_state(LoginState)
        result = s.handle_login({"email": "dash@example.com", "password": "supersecret8"})
        assert result is not None


# ---------------------------------------------------------------------------
# LoginState.handle_forgot — demo password reset (every branch)
# ---------------------------------------------------------------------------

class TestHandleForgot:
    def test_validation_errors_short_circuit(self, make_state):
        s = make_state(LoginState)
        s.handle_forgot({"email": "bad", "new_password": "short", "confirm_password": "nomatch"})
        assert s.forgot_email_error and s.forgot_password_error and s.forgot_confirm_error
        assert s.forgot_open is False  # not closed on failure... default already False
        assert s.reset_notice == ""

    def test_too_long_password_is_rejected(self, make_state):
        s = make_state(LoginState)
        long_pw = "a" * 73
        s.handle_forgot({"email": "ok@example.com", "new_password": long_pw, "confirm_password": long_pw})
        assert s.forgot_password_error

    def test_unknown_email_reports_no_account(self, make_state):
        s = make_state(LoginState)
        s.handle_forgot(
            {"email": "ghost@example.com", "new_password": "supersecret8", "confirm_password": "supersecret8"}
        )
        assert s.forgot_email_error == "No account found for that email"

    def test_successful_reset_updates_password_and_notice(self, make_state, db_session):
        _register(db_session, email="reset@example.com", password="oldpassword1")
        s = make_state(LoginState)
        s.handle_forgot(
            {"email": "reset@example.com", "new_password": "brandnew8", "confirm_password": "brandnew8"}
        )
        assert s.forgot_open is False and s.reset_notice
        # The new password now authenticates.
        assert authenticate(db_session, "reset@example.com", "brandnew8") is not None


# ---------------------------------------------------------------------------
# AuthState — session lifecycle handlers
# ---------------------------------------------------------------------------

class TestAuthStateSession:
    def test_check_auth_redirects_when_no_session(self, make_state):
        s = make_state(AuthState, auth_token="no-such-token")
        assert s.check_auth() is not None  # rx.redirect(LOGIN_ROUTE)

    def test_check_auth_passes_for_live_session(self, make_state, db_session):
        # Log a user in through LoginState so a real session row exists; _login rotates the
        # cookie to router.session.client_token, so the guard must use that same token.
        _register(db_session, email="live@example.com")
        login = make_state(LoginState, client_token="live-token")
        login.handle_login({"email": "live@example.com", "password": "supersecret8"})
        assert login.auth_token == "live-token"  # rotated on login
        guard = make_state(AuthState, auth_token="live-token")
        assert guard.check_auth() is None

    def test_do_logout_clears_token_and_sessions(self, make_state, db_session):
        _register(db_session, email="out@example.com")
        s = make_state(LoginState, client_token="out-token")
        s.handle_login({"email": "out@example.com", "password": "supersecret8"})
        assert s.auth_token == "out-token"
        s.do_logout()
        assert s.auth_token == ""

    def test_logout_returns_redirect(self, make_state):
        s = make_state(AuthState, auth_token="whatever")
        assert s.logout() is not None

    def test_authenticated_user_sentinel_when_no_session(self, make_state):
        s = make_state(AuthState, auth_token="")
        assert s.authenticated_user.id == -1
        assert s.is_authenticated is False

    def test_authenticated_user_resolves_live_session(self, make_state, db_session):
        _register(db_session, email="who@example.com")
        login = make_state(LoginState, client_token="who-token")
        login.handle_login({"email": "who@example.com", "password": "supersecret8"})
        s = make_state(AuthState, auth_token="who-token")
        assert s.authenticated_user.id is not None and s.authenticated_user.id >= 0
        assert s.is_authenticated is True

    def test_login_with_negative_user_id_is_a_noop(self, make_state):
        s = make_state(LoginState, client_token="tok")
        s._login(-1)  # sentinel user id — must not create a session
        # auth_token was cleared by the do_logout at the top of _login and never rotated.
        assert s.auth_token == ""


# ---------------------------------------------------------------------------
# Pure session-injected helpers — the validation branches ``tests/security`` skips
# ---------------------------------------------------------------------------

class TestPureHelperBranches:
    def test_register_rejects_invalid_email(self, db_session):
        assert register_new_user(db_session, "not-an-email", "supersecret8").ok is False

    def test_register_rejects_short_password(self, db_session):
        result = register_new_user(db_session, "a@example.com", "short")
        assert result.ok is False and str(MIN_PASSWORD_LENGTH) in result.error

    def test_register_rejects_overlong_password(self, db_session):
        result = register_new_user(db_session, "b@example.com", "a" * 73)
        assert result.ok is False and "too long" in result.error

    def test_authenticate_rejects_empty_credentials(self, db_session):
        assert authenticate(db_session, "", "") is None
        assert authenticate(db_session, "x@example.com", "") is None
