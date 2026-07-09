"""Registration page (Story 1.3, route ``/register``).

Custom UI over reflex-local-auth: trust signal, email + password with a show/hide toggle,
in-page Terms/Privacy modals (never a new tab), link-consent (no pre-ticked checkbox —
DPDP Rule 4), and an inline "Log in instead?" link when the email is already registered.
On submit the account is created, the user is auto-logged-in, and redirected to /upload.
"""

import reflex as rx
import reflex_local_auth

from finance_app.state.auth_state import RegisterState

# Microcopy (from prototype 01.1-register.html). AC #4 requires the exact substring
# "No guessing. No shame." in the trust signal, above the form fields.
TRUST_HEADLINE = "Your honest financial picture. No guessing. No shame."
TRUST_SUBLINE = "We only tell you what we actually know. When we're uncertain, we say so."

_TERMS_BODY = (
    "Placeholder Terms of Service for the MVP. We frame everything as information, never "
    "financial advice."
)
_PRIVACY_BODY = (
    "Placeholder Privacy notice (DPDP-conscious). We collect only what is needed to compute "
    "your Safe-to-Spend, we never sell your data, and consent is never pre-ticked."
)


def _legal_modal(label: str, body: str) -> rx.Component:
    """A link that opens an in-page modal (AC #6) — not a new tab."""
    return rx.dialog.root(
        rx.dialog.trigger(rx.link(label, cursor="pointer", color_scheme="blue")),
        rx.dialog.content(
            rx.dialog.title(label),
            rx.dialog.description(body),
            rx.dialog.close(rx.button("Got it", margin_top="1em")),
        ),
    )


def _error_callout() -> rx.Component:
    """Amber error; when the email is already registered, include an inline 'Log in instead?' link (AC #8)."""
    return rx.cond(
        RegisterState.error_message != "",
        rx.callout(
            rx.hstack(
                rx.text(RegisterState.error_message),
                rx.cond(
                    RegisterState.email_taken,
                    rx.link(
                        "Log in instead?",
                        href=reflex_local_auth.routes.LOGIN_ROUTE,
                        weight="bold",
                    ),
                ),
                spacing="2",
                align="center",
            ),
            color_scheme="amber",
            role="alert",
            width="100%",
        ),
    )


def _password_field() -> rx.Component:
    """Password input with a show/hide toggle (AC #5)."""
    return rx.hstack(
        rx.input(
            name="password",
            type=rx.cond(RegisterState.show_password, "text", "password"),
            placeholder="8+ characters",
            custom_attrs={"autoComplete": "new-password"},
            required=True,
            width="100%",
        ),
        rx.button(
            rx.cond(RegisterState.show_password, "Hide", "Show"),
            type="button",  # not a submit — just toggles visibility
            on_click=RegisterState.toggle_password,
            aria_label=rx.cond(RegisterState.show_password, "Hide password", "Show password"),
            variant="soft",
        ),
        width="100%",
        spacing="2",
    )


def _consent_line() -> rx.Component:
    """Link-consent (no checkbox → nothing pre-ticked, AC #7); legal links open modals (AC #6)."""
    return rx.text(
        "By creating an account you agree to our ",
        _legal_modal("Terms of Service", _TERMS_BODY),
        " and ",
        _legal_modal("Privacy Policy", _PRIVACY_BODY),
        ".",
        size="1",
        color_scheme="gray",
    )


def register_form() -> rx.Component:
    return rx.form(
        rx.vstack(
            rx.text("Email address", weight="medium"),
            rx.input(
                name="email",
                type="email",
                placeholder="you@example.com",
                custom_attrs={"autoComplete": "email"},
                required=True,
                width="100%",
            ),
            rx.text("Password", weight="medium"),
            _password_field(),
            rx.button("Create my account", type="submit", width="100%", margin_top="0.5em"),
            _consent_line(),
            spacing="3",
            width="100%",
        ),
        on_submit=RegisterState.handle_registration,
        width="100%",
    )


@rx.page(route=reflex_local_auth.routes.REGISTER_ROUTE, title="Create your account · Finance Analyzer")
def register() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                # Trust signal ABOVE the form (AC #4).
                rx.heading(TRUST_HEADLINE, size="6"),
                rx.text(TRUST_SUBLINE, color_scheme="gray"),
                _error_callout(),
                register_form(),
                rx.hstack(
                    rx.text("Already have an account?", color_scheme="gray"),
                    rx.link("Log in", href=reflex_local_auth.routes.LOGIN_ROUTE),
                    spacing="2",
                ),
                spacing="4",
                width="100%",
            ),
            width="28em",
            max_width="90vw",
        ),
        min_height="100vh",
        padding="2em",
    )
