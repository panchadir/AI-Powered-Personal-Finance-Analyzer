"""Copilot chat page — Stories 6.1–6.4 (FR-7.1, FR-7.5, FR-7.7–FR-7.10, NFR-8).

Mirrors WDS prototype ``01.7-copilot-chat.html``:
  * ``.copilot-page.has-sidenav`` layout, sticky ``.topnav``
  * ``.copilot-thread`` role="log" + aria-live="polite" (NFR-8)
  * Welcome card with quick-prompt chips (FR-7.7) — hidden after first message
  * ``.msg--user`` / ``.msg--bot`` bubbles for completed turns
  * In-flight streaming bubble: thinking-dots → token stream → blinking cursor
  * ``"Based on: …"`` trace chips below each data-citing bot bubble (FR-7.5)
  * Dismissable ``.context-chip`` "Talking about: {pattern}" when navigating
    from an Insight card via ``?insight=<id>&pre=<text>`` (FR-7.8)
  * Topnav back link dynamically points to Insights when context is active,
    Dashboard otherwise (FR-7.8 prototype pattern)
  * ``aria-disabled`` (not ``disabled``) on the send button while streaming (FR-7.10)
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.auth_state import AuthState
from finance_app.state.copilot_state import QUICK_PROMPTS, CopilotMessage, CopilotState


# ---------------------------------------------------------------------------
# Trace chips (FR-7.5)
# ---------------------------------------------------------------------------

def _trace_chip(source: str) -> rx.Component:
    return rx.el.a(source, href="/transactions", class_name="trace-chip")


def _trace_row(sources: list) -> rx.Component:
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

def _user_bubble(msg: CopilotMessage) -> rx.Component:
    return rx.el.div(
        rx.el.span(msg.content, class_name="msg-text"),
        class_name="msg msg--user",
    )


def _bot_bubble(msg: CopilotMessage) -> rx.Component:
    return rx.el.div(
        rx.el.span(msg.content, class_name="msg-text"),
        _trace_row(msg.trace_sources),
        class_name="msg msg--bot",
    )


def _message_bubble(msg: CopilotMessage) -> rx.Component:
    return rx.cond(
        msg.role == "user",
        _user_bubble(msg),
        _bot_bubble(msg),
    )


def _streaming_bubble() -> rx.Component:
    """In-flight assistant bubble — thinking-dots until first token, then streaming text."""
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
                    rx.el.span(CopilotState.streaming_content, class_name="msg-text"),
                    rx.el.span(class_name="cursor"),
                ),
            ),
            _trace_row(CopilotState.current_trace_sources),
            class_name="msg msg--bot",
        ),
        rx.fragment(),
    )


# ---------------------------------------------------------------------------
# Context chip — Insights handoff (FR-7.8)
# ---------------------------------------------------------------------------

def _context_chip() -> rx.Component:
    """Dismissable 'Talking about: {pattern}' chip shown when arriving from Insights.

    Visible only when ``context_pattern_name`` is non-empty. The dismiss button
    calls ``dismiss_context`` which also clears the pre-filled input.
    """
    return rx.cond(
        CopilotState.context_pattern_name != "",
        rx.el.div(
            rx.el.span(
                "Talking about: ",
                rx.el.strong(CopilotState.context_pattern_name),
            ),
            rx.el.button(
                "✕",
                on_click=CopilotState.dismiss_context,
                aria_label="Clear context",
                type="button",
            ),
            id="copilot-thread-context-chip",
            class_name="context-chip",
        ),
        rx.fragment(),
    )


# ---------------------------------------------------------------------------
# Welcome card (FR-7.7)
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
    """Hidden once the user sends their first message.

    Quick-prompt chips are also hidden when no transactions have been uploaded
    yet (Story 8.2 AC-4) — the prompts assume real data exists.
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
            rx.cond(
                CopilotState.has_transactions,
                rx.el.div(
                    *[_quick_chip(p) for p in QUICK_PROMPTS],
                    class_name="chip-suggest",
                    id="copilot-thread-welcome-chips",
                ),
                rx.fragment(),
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
    """Scrollable chat thread — role=log + aria-live=polite (NFR-8)."""
    return rx.el.div(
        # Context chip sits above the welcome card / messages (prototype position).
        _context_chip(),
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
    """Back link points to Insights when context active, Dashboard otherwise (FR-7.8)."""
    return rx.el.div(
        rx.cond(
            CopilotState.context_pattern_name != "",
            rx.el.a("← Insights", href="/insights", class_name="back-link",
                    id="copilot-topnav-back"),
            rx.el.a("← Dashboard", href="/dashboard", class_name="back-link",
                    id="copilot-topnav-back"),
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
    """Copilot chat page — Stories 6.1–6.4."""
    return rx.fragment(
        side_nav("copilot"),
        rx.el.div(
            _topnav(),
            _thread(),
            _input_bar(),
            class_name="copilot-page has-sidenav",
        ),
    )
