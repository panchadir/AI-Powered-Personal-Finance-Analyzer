"""Login page — the application landing screen (route ``/`` and ``/login``).

Rendered to match the approved **WDS prototype** ``01.2-login.html`` verbatim: the ₹ app
header, a "Welcome back." trust signal, email + password (with a show/hide toggle), a
right-aligned "Forgot password?" reset modal, a form-level error banner, a "Register User"
link, and the demo-account hint. Only the auth functionality is layered on top of the
prototype's markup + ``wds.css`` classes; the layout and copy come from the prototype.
"""

import reflex as rx
import reflex_local_auth

from finance_app.state.auth_state import LoginState

TRUST_HEADLINE = "Welcome back."
TRUST_SUBLINE = "Log in to see your honest financial picture."


def _app_header() -> rx.Component:
    return rx.el.header(
        rx.el.div("₹", class_name="logo-mark", aria_hidden="true"),
        rx.el.h1("AI Financial Copilot", class_name="app-name"),
        class_name="register-header",
    )


def _field(
    label: str,
    name: str,
    placeholder: str,
    error: rx.Var,
    *,
    input_type: str = "text",
    autocomplete: str | None = None,
    id_prefix: str = "login",
    toggle: rx.Component | None = None,
    on_blur=None,
    on_change=None,
) -> rx.Component:
    attrs: dict = {}
    if autocomplete:
        attrs["autoComplete"] = autocomplete
    input_props: dict = dict(
        id=f"{id_prefix}-{name}",
        name=name,
        type=input_type,
        placeholder=placeholder,
        custom_attrs=attrs,
        class_name=rx.cond(error != "", "has-error", ""),
    )
    if on_blur is not None:
        input_props["on_blur"] = on_blur
    if on_change is not None:
        input_props["on_change"] = on_change
    return rx.el.div(
        rx.el.label(label, html_for=f"{id_prefix}-{name}"),
        rx.el.div(
            rx.el.input(**input_props),
            toggle if toggle is not None else rx.fragment(),
            class_name="input-wrap",
        ),
        rx.el.span(error, class_name="error", role="alert"),
        class_name="field",
    )


def _pw_toggle() -> rx.Component:
    return rx.el.button(
        rx.cond(
            LoginState.show_password,
            # Eye-off icon — password visible, click to hide
            rx.html(
                '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"'
                ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
                ' stroke-linejoin="round" aria-hidden="true">'
                '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>'
                '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>'
                '<line x1="1" y1="1" x2="23" y2="23"/>'
                "</svg>"
            ),
            # Eye icon — password hidden, click to show
            rx.html(
                '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"'
                ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
                ' stroke-linejoin="round" aria-hidden="true">'
                '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>'
                '<circle cx="12" cy="12" r="3"/>'
                "</svg>"
            ),
        ),
        type="button",
        on_click=LoginState.toggle_password,
        aria_label=rx.cond(LoginState.show_password, "Hide password", "Show password"),
        class_name="pw-toggle",
    )


def _forgot_modal() -> rx.Component:
    """In-page password reset (prototype's forgot-password dialog)."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.el.a("Forgot password?", class_name="link", cursor="pointer",
                    on_click=LoginState.open_forgot),
        ),
        rx.dialog.content(
            rx.el.h3("Reset your password", margin="0 0 var(--space-xs)"),
            rx.el.p(
                "In production we'd email you a secure reset link. For this demo, set a new "
                "password directly.",
                class_name="text-muted", font_size="var(--text-sm)",
                margin="0 0 var(--space-md)",
            ),
            rx.form(
                _field("Account email", "email", "you@example.com",
                       LoginState.forgot_email_error, input_type="email",
                       autocomplete="email", id_prefix="forgot",
                       on_blur=LoginState.blur_forgot_email,
                       on_change=LoginState.change_forgot_email),
                _field("New password", "new_password", "8+ characters",
                       LoginState.forgot_password_error, input_type="password",
                       autocomplete="new-password", id_prefix="forgot",
                       on_blur=LoginState.blur_forgot_password,
                       on_change=LoginState.change_forgot_password),
                _field("Confirm new password", "confirm_password", "Repeat new password",
                       LoginState.forgot_confirm_error, input_type="password",
                       autocomplete="new-password", id_prefix="forgot",
                       on_blur=LoginState.blur_forgot_confirm,
                       on_change=LoginState.change_forgot_confirm),
                rx.el.div(
                    rx.dialog.close(
                        rx.el.button("Cancel", type="button", class_name="btn btn--secondary",
                                     flex="1"),
                    ),
                    rx.el.button("Update password", type="submit",
                                 class_name="btn btn--primary", flex="1"),
                    display="flex", gap="var(--space-sm)", margin_top="var(--space-lg)",
                ),
                on_submit=LoginState.handle_forgot,
                class_name="register-form",
            ),
            max_width="26rem",
        ),
        open=LoginState.forgot_open,
        on_open_change=LoginState.set_forgot_open,
    )


def _login_form() -> rx.Component:
    return rx.form(
        _field(
            "Email address", "email", "you@example.com", LoginState.email_error,
            input_type="email", autocomplete="email",
            on_blur=LoginState.blur_email,
            on_change=LoginState.change_email,
        ),
        _field(
            "Password", "password", "Your password", LoginState.password_error,
            input_type=rx.cond(LoginState.show_password, "text", "password"),
            autocomplete="current-password", toggle=_pw_toggle(),
            on_blur=LoginState.blur_password,
            on_change=LoginState.change_password,
        ),
        rx.el.div(_forgot_modal(), class_name="login-row"),
        rx.el.button(
            rx.el.span("Log in", class_name="btn-label"),
            type="submit", class_name="btn btn--primary",
        ),
        on_submit=LoginState.handle_login,
        class_name="register-form",
    )


def _login_body() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            _app_header(),
            rx.el.section(
                rx.el.h2(TRUST_HEADLINE, class_name="trust-headline"),
                rx.el.p(TRUST_SUBLINE, class_name="trust-subline"),
                class_name="register-trust",
            ),
            # Success notice after a password reset (green), then any form-level error (red).
            rx.cond(
                LoginState.reset_notice != "",
                rx.el.div(
                    LoginState.reset_notice, role="status",
                    background="var(--success-tint)", color="var(--success)",
                    border="1px solid var(--success)", border_radius="var(--radius-sm)",
                    padding="var(--space-sm) var(--space-md)", margin_bottom="var(--space-md)",
                    font_size="var(--text-sm)",
                ),
            ),
            rx.cond(
                LoginState.form_error != "",
                rx.el.div(LoginState.form_error, class_name="upload-error", role="alert",
                          margin_bottom="var(--space-md)"),
            ),
            _login_form(),
            rx.el.div(
                rx.el.span("New here? ", class_name="text-muted"),
                rx.el.a("Register User", href=reflex_local_auth.routes.REGISTER_ROUTE,
                        class_name="link"),
                class_name="register-existing-user",
            ),
            class_name="auth-card",
        ),
        class_name="page page--auth",
    )


@rx.page(route="/", title="Log in · AI Financial Copilot", on_load=LoginState.reset_form)
@rx.page(route=reflex_local_auth.routes.LOGIN_ROUTE, title="Log in · AI Financial Copilot",
         on_load=LoginState.reset_form)
def auth() -> rx.Component:
    return _login_body()
