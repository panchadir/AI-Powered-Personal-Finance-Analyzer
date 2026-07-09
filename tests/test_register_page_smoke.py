"""Story 1.3 · AC #4, #5, #6, #7 — registration page smoke test.

UI coverage is necessarily light (redirect/cookie behavior is app-verified). This asserts
the page builds without error and that the load-bearing microcopy/contract is present:
the trust signal, the show/hide toggle state, and link-consent (no pre-ticked checkbox).
"""
from __future__ import annotations

import reflex as rx

from finance_app.pages.register import TRUST_HEADLINE, register
from finance_app.state.auth_state import RegisterState


def test_trust_signal_contains_required_substring() -> None:
    # AC #4: "No guessing. No shame." must appear in the trust signal above the form.
    assert "No guessing. No shame." in TRUST_HEADLINE


def test_register_page_builds() -> None:
    component = register()
    assert isinstance(component, rx.Component)  # renders without raising (catches API errors)


def test_password_toggle_defaults_hidden() -> None:
    # AC #5: show/hide toggle exists and starts hidden.
    assert RegisterState.__fields__["show_password"].default is False


def test_no_preticked_consent_checkbox() -> None:
    # AC #7 (DPDP Rule 4): link-consent design has no consent checkbox at all,
    # so there is no boolean consent var that could default to True/checked.
    consent_like = [
        name for name in RegisterState.__fields__
        if "consent" in name.lower() or "agree" in name.lower() or "terms" in name.lower()
    ]
    assert consent_like == [], f"unexpected consent var(s) that could be pre-ticked: {consent_like}"
