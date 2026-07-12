"""Story 8.2 — Onboarding Empty States: structural tests.

These tests verify:
  AC-1  Dashboard empty state: correct copy + step-indicator hint.
  AC-2  Transactions empty state: correct copy + upload link.
  AC-3  Insights empty state: correct copy + upload link.
  AC-4  Copilot: quick prompts absent when has_transactions=False;
        no-data reply returned without LLM call.

All tests are structural (state-logic, source inspection, constant checks) and run
without a running Reflex app or a database, following the pattern established in
``test_register_page_smoke.py``.
"""
from __future__ import annotations

import inspect

import reflex as rx

# ---------------------------------------------------------------------------
# AC-1 — Dashboard empty state
# ---------------------------------------------------------------------------

from finance_app.pages.dashboard import _empty_state as _dash_empty
from finance_app.state.dashboard_state import EMPTY_HERO_COPY


def test_dashboard_empty_state_builds() -> None:
    component = _dash_empty()
    assert isinstance(component, rx.Component)


def test_dashboard_empty_state_copy() -> None:
    """The approved UX-DR12 copy must be present in the EMPTY_HERO_COPY constant."""
    assert "Upload a statement" in EMPTY_HERO_COPY
    assert "safe to spend" in EMPTY_HERO_COPY


def test_dashboard_empty_state_step_hint_in_source() -> None:
    """Step 1 of 3 hint is present in the _empty_state source (Story 8.2 AC-1).

    We check the function source rather than walking the component tree, because
    Reflex components hold ``Var`` objects that wrap the text rather than the
    literal string, so string-searching the tree is not reliable.
    """
    source = inspect.getsource(_dash_empty)
    assert "Step 1 of 3" in source, (
        "Dashboard empty state must contain 'Step 1 of 3' (Story 8.2 AC-1)"
    )


# ---------------------------------------------------------------------------
# AC-2 — Transactions empty state
# ---------------------------------------------------------------------------

from finance_app.pages.transactions import _empty_state as _txn_empty, transactions


def test_transactions_empty_state_builds() -> None:
    component = _txn_empty()
    assert isinstance(component, rx.Component)


def test_transactions_empty_state_copy() -> None:
    source = inspect.getsource(_txn_empty)
    assert "Your transactions will appear here after you upload a statement." in source, (
        "Exact AC-2 copy must be present"
    )


def test_transactions_empty_state_has_upload_link() -> None:
    source = inspect.getsource(_txn_empty)
    assert '"/upload"' in source or "'/upload'" in source, (
        "Transactions empty state must link to /upload"
    )


def test_transactions_page_builds() -> None:
    component = transactions()
    assert isinstance(component, rx.Component)


# ---------------------------------------------------------------------------
# AC-3 — Insights empty state
# ---------------------------------------------------------------------------

from finance_app.pages.insights import _empty_state as _insights_empty, insights


def test_insights_empty_state_builds() -> None:
    component = _insights_empty()
    assert isinstance(component, rx.Component)


def test_insights_empty_state_copy() -> None:
    source = inspect.getsource(_insights_empty)
    assert "Insights will appear once I've analysed your statement." in source, (
        "Exact AC-3 copy must be present"
    )


def test_insights_empty_state_has_upload_link() -> None:
    source = inspect.getsource(_insights_empty)
    assert '"/upload"' in source or "'/upload'" in source, (
        "Insights empty state must link to /upload"
    )


def test_insights_page_builds() -> None:
    component = insights()
    assert isinstance(component, rx.Component)


# ---------------------------------------------------------------------------
# AC-4 — Copilot empty state
# ---------------------------------------------------------------------------

from finance_app.state.copilot_state import CopilotState, QUICK_PROMPTS
from finance_app.pages.copilot import _welcome_card


def test_copilot_has_transactions_defaults_false() -> None:
    """has_transactions starts False — new user sees no quick prompts."""
    assert CopilotState.__fields__["has_transactions"].default is False


def test_copilot_quick_prompts_list_nonempty() -> None:
    """QUICK_PROMPTS must have entries (they're only hidden, not deleted)."""
    assert len(QUICK_PROMPTS) > 0


def test_copilot_welcome_card_builds() -> None:
    """The welcome card (subset of the full page) must render without error."""
    component = _welcome_card()
    assert isinstance(component, rx.Component)


def test_copilot_no_data_reply_copy() -> None:
    """The no-data reply copy must match the AC-4 exact wording."""
    # Reflex decorates event handlers — get the underlying function source.
    fn = CopilotState.send_message.fn
    source = inspect.getsource(fn)
    assert "I don't have your transactions yet" in source, (
        "send_message must return the exact AC-4 no-data copy"
    )
    assert "Upload a statement" in source, (
        "no-data reply must mention uploading a statement"
    )


def test_copilot_no_data_skips_llm() -> None:
    """When has_transactions is False, astream_events must NOT be called.

    The no-data branch returns before the streaming code runs.
    """
    fn = CopilotState.send_message.fn
    source = inspect.getsource(fn)
    # The no-data guard and early return must appear before the astream_events call.
    no_data_pos = source.find("I don't have your transactions yet")
    astream_pos = source.find("astream_events")
    assert no_data_pos != -1, "no-data reply text must be in send_message"
    assert astream_pos != -1, "astream_events call must be in send_message"
    assert no_data_pos < astream_pos, (
        "no-data guard must appear before astream_events in send_message"
    )


def test_copilot_welcome_card_hides_chips_without_data_in_source() -> None:
    """_welcome_card source must gate quick chips on has_transactions (Story 8.2 AC-4)."""
    source = inspect.getsource(_welcome_card)
    assert "has_transactions" in source, (
        "_welcome_card must reference has_transactions to gate quick prompts"
    )


# ---------------------------------------------------------------------------
# State-level structural checks
# ---------------------------------------------------------------------------

from finance_app.state.transactions_state import TransactionsState
from finance_app.state.insights_state import InsightsState


def test_transactions_state_has_has_data_field() -> None:
    assert "has_data" in TransactionsState.__fields__
    assert TransactionsState.__fields__["has_data"].default is False


def test_transactions_state_has_loaded_field() -> None:
    assert "loaded" in TransactionsState.__fields__
    assert TransactionsState.__fields__["loaded"].default is False


def test_insights_state_has_has_data_field() -> None:
    assert "has_data" in InsightsState.__fields__
    assert InsightsState.__fields__["has_data"].default is False


def test_insights_state_has_loaded_field() -> None:
    assert "loaded" in InsightsState.__fields__
    assert InsightsState.__fields__["loaded"].default is False
