"""Registration page (Story 1.3, route ``/register``).

Rendered to match the **approved WDS prototype** ``01.1-register.html`` verbatim: the same
DOM structure and the same ``wds.css`` class names (auth card, app header with the ₹ logo,
trust signal, per-field inline validation, password show/hide toggles, a confirm-password
field, in-page Terms/Privacy modals, a link-consent legal footnote, and — on success — the
"Registration successful → Return to Login" panel, with **no auto-login**).

Only functionality and validation are layered on top of the prototype's markup; the layout,
copy, spacing and visual hierarchy come straight from the prototype (the UI baseline).
"""

import reflex as rx
import reflex_local_auth

from finance_app.state.auth_state import RegisterState

# Microcopy (from prototype 01.1-register.html). AC #4 requires the exact substring
# "No guessing. No shame." in the trust signal, above the form fields.
TRUST_HEADLINE = "Your honest financial picture. No guessing. No shame."
TRUST_SUBLINE = "We only tell you what we actually know. When we're uncertain, we say so."

_TERMS_BODY = (
    "Placeholder Terms of Service for the prototype. In production this opens the full Terms "
    "of Service. We frame everything as information, never financial advice."
)
_PRIVACY_BODY = (
    "Placeholder privacy notice (DPDP-compliant). We collect only what is needed to compute "
    "your Safe-to-Spend, we never sell your data, and consent is never pre-ticked."
)


def _app_header() -> rx.Component:
    """Prototype Section 1: the ₹ logo mark + app name, centered above the card body."""
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
    toggle: rx.Component | None = None,
    extra: rx.Component | None = None,
    on_blur=None,
    on_change=None,
) -> rx.Component:
    """One ``.field`` (label + input-wrap + inline error), matching the prototype markup."""
    attrs: dict = {}
    if autocomplete:
        attrs["autoComplete"] = autocomplete
    input_props: dict = dict(
        id=f"register-{name}",
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
        rx.el.label(label, html_for=f"register-{name}"),
        rx.el.div(
            rx.el.input(**input_props),
            toggle if toggle is not None else rx.fragment(),
            class_name="input-wrap",
        ),
        rx.el.span(error, class_name="error", role="alert"),
        extra if extra is not None else rx.fragment(),
        class_name="field",
    )


def _pw_toggle(is_shown: rx.Var, on_click) -> rx.Component:
    """The 'Show'/'Hide' button pinned inside the password input (prototype .pw-toggle)."""
    return rx.el.button(
        rx.cond(is_shown, "Hide", "Show"),
        type="button",  # never submits — just toggles visibility
        on_click=on_click,
        aria_label=rx.cond(is_shown, "Hide password", "Show password"),
        class_name="pw-toggle",
    )


def _legal_modal(label: str, body: str) -> rx.Component:
    """A legal link that opens an in-page modal (AC #6) — never a new tab."""
    return rx.dialog.root(
        rx.dialog.trigger(rx.el.a(label, class_name="link", cursor="pointer")),
        rx.dialog.content(
            rx.dialog.title(label),
            rx.dialog.description(body),
            rx.dialog.close(rx.button("Got it", margin_top="1em")),
        ),
    )


def _register_form() -> rx.Component:
    return rx.form(
        _field(
            "Email address", "email", "you@example.com", RegisterState.email_error,
            input_type="email", autocomplete="email",
            on_blur=RegisterState.blur_email,
            on_change=RegisterState.change_email,
            # On a duplicate email, offer an inline "Log in instead?" link (AC #8).
            extra=rx.cond(
                RegisterState.email_taken,
                rx.el.a(
                    "Log in instead?",
                    href=reflex_local_auth.routes.LOGIN_ROUTE,
                    class_name="link",
                    font_size="var(--text-sm)",
                ),
            ),
        ),
        _field(
            "Password", "password", "8+ characters", RegisterState.password_error,
            input_type=rx.cond(RegisterState.show_password, "text", "password"),
            autocomplete="new-password",
            on_blur=RegisterState.blur_password,
            on_change=RegisterState.change_password,
            toggle=_pw_toggle(RegisterState.show_password, RegisterState.toggle_password),
        ),
        _field(
            "Confirm password", "confirm_password", "Repeat your password",
            RegisterState.confirm_error,
            input_type=rx.cond(RegisterState.show_confirm, "text", "password"),
            autocomplete="new-password",
            on_blur=RegisterState.blur_confirm,
            on_change=RegisterState.change_confirm,
            toggle=_pw_toggle(RegisterState.show_confirm, RegisterState.toggle_confirm),
        ),
        rx.el.button(
            rx.el.span("Create my account", class_name="btn-label"),
            type="submit",
            class_name="btn btn--primary",
        ),
        on_submit=RegisterState.handle_registration,
        class_name="register-form",
    )
    # NOTE: rx.form (not rx.el.form) so on_submit receives the serialized field dict.


def _form_view() -> rx.Component:
    """Everything shown before a successful submit (trust signal → form → links → legal)."""
    return rx.fragment(
        rx.el.section(
            rx.el.h2(TRUST_HEADLINE, class_name="trust-headline"),
            rx.el.p(TRUST_SUBLINE, class_name="trust-subline"),
            class_name="register-trust",
        ),
        # Form-level (network/server) error banner — the prototype's toast, inline here.
        rx.cond(
            RegisterState.error_message != "",
            rx.el.div(RegisterState.error_message, class_name="upload-error", role="alert"),
        ),
        _register_form(),
        rx.el.div(
            rx.el.span("Already have an account? ", class_name="text-muted"),
            rx.el.a("Log in", href=reflex_local_auth.routes.LOGIN_ROUTE, class_name="link"),
            class_name="register-existing-user",
        ),
        rx.el.p(
            rx.el.span(
                "By creating an account you agree to our ",
                _legal_modal("Terms of Service", _TERMS_BODY),
                " and ",
                _legal_modal("Privacy Policy", _PRIVACY_BODY),
                ". We never sell your data.",
                class_name="text-muted",
            ),
            class_name="register-legal",
        ),
    )


def _success_view() -> rx.Component:
    """Prototype success state: no auto-login — the user returns to Login to sign in."""
    return rx.el.section(
        rx.el.div("✓", class_name="success-check", aria_hidden="true"),
        rx.el.h2("Registration successful!", class_name="register-success-headline"),
        rx.el.p(
            "Your account has been created. For your security, please log in to continue.",
            class_name="text-muted register-success-sub",
        ),
        rx.el.a(
            "Return to Login",
            href=reflex_local_auth.routes.LOGIN_ROUTE,
            class_name="btn btn--primary",
            text_decoration="none",
        ),
        class_name="register-success",
        role="status",
    )


@rx.page(
    route=reflex_local_auth.routes.REGISTER_ROUTE,
    title="Create your account · AI Financial Copilot",
    on_load=RegisterState.reset_form,
)
def register() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            _app_header(),
            rx.cond(RegisterState.registration_success, _success_view(), _form_view()),
            class_name="auth-card",
        ),
        class_name="page page--auth",
    )
