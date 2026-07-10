"""Copilot chat page — Stories 6.1–6.3 (FR-7.1, FR-7.5, FR-7.7, FR-7.9, FR-7.10, NFR-8).

Mirrors WDS prototype ``01.7-copilot-chat.html``:
  * ``.copilot-page.has-sidenav`` layout, sticky ``.topnav``
  * ``.copilot-thread`` role="log" + aria-live="polite" (NFR-8)
  * Welcome card with quick-prompt chips (FR-7.7) — hidden after first message
  * ``.msg--user`` / ``.msg--bot`` bubbles for completed turns
  * In-flight streaming bubble: thinking-dots → token stream → blinking cursor
  * ``"Based on: …"`` trace chips below each data-citing bot bubble (FR-7.5)
    - Chips on completed turns navigate to /transactions (transparency)
    - Chips on the live streaming bubble appear as soon as the trace event fires
  * ``aria-disabled`` (not ``disabled``) on the send button while streaming (FR-7.10)
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.auth_state import AuthState
from finance_app.state.copilot_state import QUICK_PROMPTS, CopilotState


# ---------------------------------------------------------------------------
# Trace chips
# ---------------------------------------------------------------------------

def _trace_chip(source: str) -> rx.Component:
    """A single 'Based on: …' trace chip that navigates to /transactions."""
    return rx.el.a(
        source,
        href="/transactions",
        class_name="trace-chip",
    )


def _trace_row(sources: list) -> rx.Component:
    """Render the 'Based on: …' row when sources is non-empty."""
    return rx.cond(
        sources.length() > 0,
        rx.el.div(
            rx.el.span("Based on:", class_name="trace-label"),
            rx.foreach(sources, _trace_chip),
            class_name="trace-row",
        ),
        rx.fragment(),
    )


# ---------------------------------------------------------------------------
# Message bubbles
# ---------------------------------------------------------------------------

def _user_bubble(msg: dict) -> rx.Component:
    return rx.el.div(
        rx.el.span(msg["content"], class_name="msg-text"),
        class_name="msg msg--user",
    )


def _bot_bubble(msg: dict) -> rx.Component:
    """Completed assistant bubble with optional trace chips (FR-7.5)."""
    return rx.el.div(
        rx.el.span(msg["content"], class_name="msg-text"),
        _trace_row(msg["trace_sources"]),
        class_name="msg msg--bot",
    )


def _message_bubble(msg: dict) -> rx.Component:
    return rx.cond(
        msg["role"] == "user",
        _user_bubble(msg),
        _bot_bubble(msg),
    )


def _streaming_bubble() -> rx.Component:
    """In-flight assistant bubble — visible only while streaming.

    Shows:
      - Thinking dots before the first token arrives
      - Token-by-token text + blinking cursor while tokens arrive
      - Live trace chips as soon as the trace event fires (before done)
    """
    return rx.cond(
        CopilotState.streaming,
        rx.el.div(
            rx.cond(
                CopilotState.streaming_content == "",
                rx.el.span(
                    rx.el.span(), rx.el.span(), rx.el.span(),
                    class_name="typing-dots",
                ),
                rx.fragment(
                    rx.el.span(
                        CopilotState.streaming_content,
                        class_name="msg-text",
                    ),
                    rx.el.span(class_name="cursor"),
                ),
            ),
            # Live trace chips appear as soon as the trace event fires.
            _trace_row(CopilotState.current_trace_sources),
            class_name="msg msg--bot",
        ),
        rx.fragment(),
    )


# ---------------------------------------------------------------------------
# Welcome card
# ---------------------------------------------------------------------------

def _quick_chip(prompt: str) -> rx.Component:
    return rx.el.button(
        prompt,
        on_click=CopilotState.send_quick_prompt(prompt),
        class_name="chip",
        type="button",
        disabled=CopilotState.streaming,
    )


def _welcome_card() -> rx.Component:
    """Hidden once the user sends their first message."""
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


# ---------------------------------------------------------------------------
# Thread + input bar + topnav
# ---------------------------------------------------------------------------

def _thread() -> rx.Component:
    """Scrollable chat thread — role=log + aria-live=polite (NFR-8 / FR-7.10)."""
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
    """Sticky bottom bar. Send button uses aria-disabled, not disabled (FR-7.10)."""
    send_disabled = CopilotState.streaming | (CopilotState.input_value.strip() == "")
    return rx.el.div(
        rx.el.textarea(
            id="copilot-input-bar-field",
            placeholder="Ask anything about your finances…",
            aria_label="Message to AI Copilot",
            rows="1",
            value=CopilotState.input_value,
            on_change=CopilotState.set_input,
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
            disabled=CopilotState.streaming,
        ),
        id="copilot-input-bar",
        class_name="copilot-input-bar",
    )


def _topnav() -> rx.Component:
    return rx.el.div(
        rx.el.a("← Dashboard", href="/dashboard", class_name="back-link",
                id="copilot-topnav-back"),
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
    """Copilot chat page — Stories 6.1–6.3."""
    return rx.fragment(
        side_nav("copilot"),
        rx.el.div(
            _topnav(),
            _thread(),
            _input_bar(),
            class_name="copilot-page has-sidenav",
        ),
    )
