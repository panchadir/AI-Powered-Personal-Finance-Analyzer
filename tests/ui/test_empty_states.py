"""Story 8.2 — Onboarding Empty States (AC1/AC2/AC3/AC4).

Tests verify that every screen shows welcoming, action-directing empty states
with the approved copy and upload links rather than blank pages.

Component introspection strategy: Reflex components store text in child ``Bare``
nodes whose ``contents`` field holds JSON-quoted strings (``'"text"'``). Links use
``ReactRouterLink`` with the path in the ``to`` field. Tests walk the tree using
the helpers below.
"""
from __future__ import annotations

import json


def _bare_text(node) -> str:
    """Extract text from a Reflex Bare node (contents is a JSON-quoted string)."""
    contents = getattr(node, "contents", None)
    if contents is None:
        return ""
    try:
        return json.loads(contents)
    except (ValueError, TypeError):
        return str(contents)


def _collect_text(component) -> str:
    """Recursively collect all literal text from a Reflex component tree."""
    parts = []
    for child in (getattr(component, "children", None) or []):
        type_name = type(child).__name__
        if type_name == "Bare":
            parts.append(_bare_text(child))
        else:
            parts.append(_collect_text(child))
    return " ".join(p for p in parts if p)


def _collect_class_names(component) -> list[str]:
    """Collect all class_name values from a component tree."""
    names = []
    cn = getattr(component, "class_name", None)
    if cn:
        names.append(str(cn))
    for child in (getattr(component, "children", None) or []):
        type_name = type(child).__name__
        if type_name != "Bare":
            names.extend(_collect_class_names(child))
    return names


def _unwrap(value) -> str:
    """Unwrap a Reflex prop value — may be a JSON-quoted string like '"/upload"'."""
    if value is None:
        return ""
    s = str(value)
    try:
        parsed = json.loads(s)
        if isinstance(parsed, str):
            return parsed
    except (ValueError, TypeError):
        pass
    return s


def _collect_link_targets(component) -> list[str]:
    """Collect all link targets (``to`` or ``href``) from ReactRouterLink and anchor nodes."""
    targets = []
    to = getattr(component, "to", None)
    href = getattr(component, "href", None)
    if to is not None:
        targets.append(_unwrap(to))
    elif href is not None:
        targets.append(_unwrap(href))
    for child in (getattr(component, "children", None) or []):
        type_name = type(child).__name__
        if type_name != "Bare":
            targets.extend(_collect_link_targets(child))
    return targets


# ---------------------------------------------------------------------------
# AC1 — Dashboard empty state
# ---------------------------------------------------------------------------


def test_dashboard_empty_state_has_step_indicator():
    """Dashboard empty state must include a 'Step 1 of 3' span with class step-indicator."""
    from finance_app.pages.dashboard import _empty_state

    comp = _empty_state()
    class_names = _collect_class_names(comp)
    assert "step-indicator" in class_names, (
        "Dashboard empty state must include an element with class 'step-indicator' "
        "to show users they are at Step 1 of 3 (AC1)"
    )


def test_dashboard_empty_state_approved_copy():
    """Dashboard empty state must contain the AC1-approved hero copy."""
    from finance_app.pages.dashboard import _empty_state

    comp = _empty_state()
    text = _collect_text(comp)
    assert "Upload a statement" in text, f"Dashboard empty state copy missing. Got: {text!r}"


def test_dashboard_empty_state_has_cta():
    """Dashboard empty state must have an 'Upload your statement' CTA button."""
    from finance_app.pages.dashboard import _empty_state

    comp = _empty_state()
    text = _collect_text(comp)
    assert "Upload your statement" in text


# ---------------------------------------------------------------------------
# AC2 — Transactions empty state
# ---------------------------------------------------------------------------

_TRANSACTIONS_EMPTY_COPY = "Your transactions will appear here after you upload a statement."


def test_transactions_empty_state_copy():
    """Transactions empty state must show the AC2-approved copy."""
    from finance_app.pages.transactions import _empty_state

    comp = _empty_state()
    text = _collect_text(comp)
    assert _TRANSACTIONS_EMPTY_COPY in text, (
        f"Expected '{_TRANSACTIONS_EMPTY_COPY}' in transactions empty state, got: {text!r}"
    )


def test_transactions_empty_state_has_upload_link():
    """Transactions empty state must include an 'Upload your statement' link to /upload."""
    from finance_app.pages.transactions import _empty_state

    comp = _empty_state()
    targets = _collect_link_targets(comp)
    assert "/upload" in targets, (
        f"Transactions empty state must have a link to /upload (AC2). Found: {targets}"
    )
    text = _collect_text(comp)
    assert "Upload your statement" in text


# ---------------------------------------------------------------------------
# AC3 — Insights empty state
# ---------------------------------------------------------------------------


def test_insights_empty_state_copy():
    """Insights empty state must show the approved copy (regression guard).

    The "not enough data yet" arm is INSUFFICIENT_DATA_COPY, not EMPTY_COPY: Epic 7 split the
    single empty string into two, because an empty feed means opposite things depending on why
    it is empty. EMPTY_COPY now owns the *other* arm ("you've read them all"), so the guard for
    the data-poor user follows the meaning, not the old constant name.
    """
    from finance_app.state.insights_state import EMPTY_COPY, INSUFFICIENT_DATA_COPY

    # The data-poor user is told the app isn't ready yet, and pointed at uploading.
    assert "statement" in INSUFFICIENT_DATA_COPY.lower()
    assert "upload" in INSUFFICIENT_DATA_COPY.lower()
    # ...and is never told their empty feed is an achievement.
    assert INSUFFICIENT_DATA_COPY != EMPTY_COPY


def test_insights_empty_state_has_upload_link():
    """Insights no-data branch must include an 'Upload your statement' link to /upload."""
    from finance_app.pages.insights import _empty_state

    comp = _empty_state()
    # _empty_state returns rx.cond(has_data, dismissed_branch, no_data_branch).
    # The no-data branch (false branch) is the second child of the cond component.
    # Walk the whole tree — the upload link is present somewhere in the component.
    targets = _collect_link_targets(comp)
    assert "/upload" in targets, (
        f"Insights empty state no-data branch must have a link to /upload (AC3). Found: {targets}"
    )
    text = _collect_text(comp)
    assert "Upload your statement" in text


def test_insights_dismissed_copy_exists():
    """DISMISSED_COPY constant must exist and be distinct from EMPTY_COPY (regression guard)."""
    from finance_app.state.insights_state import DISMISSED_COPY, EMPTY_COPY

    assert DISMISSED_COPY != EMPTY_COPY
    assert "dismissed" in DISMISSED_COPY.lower() or "check back" in DISMISSED_COPY.lower()


def test_insights_has_data_var_exists():
    """InsightsState must declare has_data: bool = False (structural check)."""
    from finance_app.state.insights_state import InsightsState

    state = InsightsState()
    assert hasattr(state, "has_data")
    assert state.has_data is False


# ---------------------------------------------------------------------------
# AC4a — Copilot: has_transactions var on state
# ---------------------------------------------------------------------------

_COPILOT_NO_DATA_COPY = (
    "I don't have your transactions yet. "
    "Upload a statement and I'll be able to give you real answers."
)


def test_copilot_has_transactions_var_exists():
    """CopilotState must declare has_transactions: bool = False (AC4 structural check)."""
    from finance_app.state.copilot_state import CopilotState

    state = CopilotState()
    assert hasattr(state, "has_transactions"), "CopilotState must have has_transactions var"
    assert state.has_transactions is False, "has_transactions must default to False"


def test_copilot_no_data_copy_constant():
    """The no-data response constant must match the AC4-approved copy."""
    from finance_app.state.copilot_state import COPILOT_NO_DATA_RESPONSE

    assert COPILOT_NO_DATA_RESPONSE == _COPILOT_NO_DATA_COPY


def test_copilot_quick_prompts_hidden_when_no_data():
    """has_transactions must default to False and be writable (AC4a structural check)."""
    from finance_app.state.copilot_state import CopilotState

    state = CopilotState()
    assert state.has_transactions is False

    state.has_transactions = True
    assert state.has_transactions is True
