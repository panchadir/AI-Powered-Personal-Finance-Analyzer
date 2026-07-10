"""Copilot chat page — Story 6.1 (FR-7.1, FR-7.7, FR-7.9, FR-7.10, NFR-8).

Mirrors the WDS prototype ``01.7-copilot-chat.html`` exactly:
  * ``.copilot-page.has-sidenav`` layout with sticky ``.topnav``
  * ``.copilot-thread`` (``role="log"``, ``aria-live="polite"``) — the live region
    announces completed sentences, not every token (NFR-8 / FR-7.10).
  * Welcome card with headline, body copy, and quick-prompt chips (FR-7.7).
    Hidden once the first message is sent.
  * ``.msg--user`` / ``.msg--bot`` bubbles for completed turns.
  * A ``.msg--bot`` streaming bubble that shows the in-flight ``streaming_content``
    token-by-token via a reactive var (FR-7.1).
  * ``.copilot-input-bar`` with a textarea + send button. The send button uses
    ``aria-disabled`` (not ``disabled``) so it remains keyboard-focusable while
    streaming (FR-7.10).

Trace chips (FR-7.5) and context-chip handoff from Insights (FR-7.8) are
Story 6.3 / Story 6.4 concerns; the skeleton CSS classes are in place.
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.auth_state import AuthState
from finance_app.state.copilot_state import QUICK_PROMPTS, CopilotState


# ---------------------------------------------------------------------------
# Sub-components
# ---------------------------------------------------------------------------

def _user_bubble(msg: dict) -> rx.Component:
    """A user message bubble."""
    return rx.el.div(
        rx.el.span(msg["content"], class_name="msg-text"),
        class_name="msg msg--user",
    )


def _bot_bubble(msg: dict) -> rx.Component:
    """A completed assistant message bubble."""
    return rx.el.div(
        rx.el.span(msg["content"], class_name="msg-text"),
        class_name="msg msg--bot",
    )


def _streaming_bubble() -> rx.Component:
    """The in-flight assistant bubble — visible only while streaming."""
    return rx.cond(
        CopilotState.streaming,
        rx.el.div(
            rx.cond(
                CopilotState.streaming_content == "",
                # Thinking dots shown before the first token arrives.
                rx.el.span(
                    rx.el.span(), rx.el.span(), rx.el.span(),
                    class_name="typing-dots",
                ),
                # Token-by-token text once tokens start arriving.
                rx.fragment(
                    rx.el.span(
                        CopilotState.streaming_content,
                        class_name="msg-text",
                    ),
                    rx.el.span(class_name="cursor"),
                ),
            ),
            class_name="msg msg--bot",
        ),
        rx.fragment(),
    )


def _message_bubble(msg: dict) -> rx.Component:
    """Route a completed message to the correct bubble style."""
    return rx.cond(
        msg["role"] == "user",
        _user_bubble(msg),
        _bot_bubble(msg),
    )


def _quick_chip(prompt: str) -> rx.Component:
    return rx.el.button(
        prompt,
        on_click=CopilotState.send_quick_prompt(prompt),
        class_name="chip",
        type="button",
        disabled=CopilotState.streaming,
    )


def _welcome_card() -> rx.Component:
    """First-visit welcome card with headline, body, and suggestion chips.

    Hidden once the user has sent their first message (messages list is non-empty).
    """
    return rx.cond(
        CopilotState.messages.length() == 0,
        rx.el.div(
            rx.el.h2(
                "Ask me anything about your finances",
                id="copilot-thread-welcome-headline",
            ),
            rx.el.p(
                "I only use your actual data — I'll never make up numbers or give "
                "you generic advice. If I'm not sure, I'll say so.",
                id="copilot-thread-welcome-body",
            ),
            rx.el.div(
                *[_quick_chip(p) for p in QUICK_PROMPTS],
                class_name="chip-suggest",
                id="copilot-thread-welcome-chips",
            ),
            class_name="welcome-card",
            id="copilot-thread-welcome",
        ),
        rx.fragment(),
    )


def _thread() -> rx.Component:
    """The scrollable chat thread — role=log + aria-live=polite (NFR-8 / FR-7.10)."""
    return rx.el.div(
        _welcome_card(),
        rx.foreach(CopilotState.messages, _message_bubble),
        _streaming_bubble(),
        id="copilot-thread",
        class_name="copilot-thread",
        role="log",
        aria_live="polite",
    )


def _input_bar() -> rx.Component:
    """Sticky bottom input bar with auto-sizing textarea and send button.

    Send button uses ``aria-disabled`` (not ``disabled``) so it stays in the
    tab order while streaming (FR-7.10).
    """
    send_disabled = CopilotState.streaming | (CopilotState.input_value.strip() == "")

    return rx.el.div(
        rx.el.textarea(
            id="copilot-input-bar-field",
            placeholder="Ask anything about your finances…",
            aria_label="Message to AI Copilot",
            rows="1",
            value=CopilotState.input_value,
            on_change=CopilotState.set_input,
            # Enter (without Shift) submits via handle_key_down; Shift+Enter inserts newline.
            on_key_down=CopilotState.handle_key_down,
            disabled=CopilotState.streaming,
            auto_complete="off",
        ),
        rx.el.button(
            "➤",
            id="copilot-input-bar-send",
            class_name="send-btn",
            aria_label="Send message",
            aria_disabled=rx.cond(send_disabled, "true", "false"),
            on_click=CopilotState.send_message,
            type="button",
            # ``disabled`` only when streaming so Enter-key still works from textarea;
            # the aria-disabled above communicates the not-yet-active state accessibly.
            disabled=CopilotState.streaming,
        ),
        id="copilot-input-bar",
        class_name="copilot-input-bar",
    )


def _topnav() -> rx.Component:
    return rx.el.div(
        rx.el.a(
            "← Dashboard",
            href="/dashboard",
            class_name="back-link",
            id="copilot-topnav-back",
        ),
        rx.el.span("AI Copilot", class_name="topnav-title", id="copilot-topnav-title"),
        id="copilot-topnav",
        class_name="topnav",
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

@rx.page(
    route="/copilot",
    title="AI Copilot · Finance Analyzer",
    on_load=[AuthState.check_auth, CopilotState.load_history],
)
def copilot() -> rx.Component:
    """Copilot chat page — Story 6.1."""
    return rx.fragment(
        side_nav("copilot"),
        rx.el.div(
            _topnav(),
            _thread(),
            _input_bar(),
            class_name="copilot-page has-sidenav",
        ),
    )
