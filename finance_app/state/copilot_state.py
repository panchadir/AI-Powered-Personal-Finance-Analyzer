"""Copilot chat state — Stories 6.1–6.3 (FR-7.1, FR-7.4, FR-7.5, FR-7.9, NFR-8).

Drives the streaming chat UI:
  * ``send_message`` streams typed events from ``astream_events``:
      - ``token``  → append to ``streaming_content``, yield to browser
      - ``trace``  → store in ``current_trace_sources`` for the bubble
      - ``error``  → set ``streaming_content`` to the error message
      - ``done``   → finalise: move content + trace into ``messages``, clear buffer
      - unknown    → ignored gracefully (FR-7.3 forward-compat AC)
  * ``load_history`` on_load: fetches prior messages from DB (FR-7.9).
  * ``set_input`` / ``handle_key_down`` drive the controlled textarea.

Each completed ``messages`` entry carries a ``trace_sources`` list so the
page can render ``"Based on: …"`` trace chips below assistant bubbles (FR-7.5).

Architecture (AD-2): only this file imports ``reflex``; ``services.narrate`` is
framework-agnostic. No financial arithmetic here (AD-1 / NFR-3).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import reflex as rx
from sqlmodel import select

from finance_app.models import ChatMessage
from finance_app.state.auth_state import AuthState, user_for_token
from services.narrate.copilot import astream_events

log = logging.getLogger(__name__)

# Quick-prompt suggestions shown on the welcome card (FR-7.7).
QUICK_PROMPTS: list[str] = [
    "How am I doing?",
    "What's my biggest spend?",
    "Am I on track this month?",
]

# Human-readable labels for the tool names shown in trace chips (FR-7.5).
_TOOL_LABELS: dict[str, str] = {
    "get_safe_to_spend":        "Safe-to-Spend",
    "get_confidence_score":     "Confidence Score",
    "query_transactions":       "Your transactions",
    "get_spending_by_category": "Spending by category",
    "get_upcoming_commitments": "Upcoming commitments",
}


def _label(tool_name: str) -> str:
    return _TOOL_LABELS.get(tool_name, tool_name)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CopilotState(AuthState):
    """State for the Copilot chat page."""

    # Completed chat turns rendered in the thread.
    # Each dict: {"role": str, "content": str, "trace_sources": list[str]}
    messages: list[dict] = []

    # In-flight token buffer (token-by-token streaming).
    streaming_content: str = ""

    # Trace sources collected during the current stream (emitted as one trace event).
    # Stored here so the streaming bubble can show them before the turn finalises.
    current_trace_sources: list[str] = []

    # True while the assistant is generating — drives aria-disabled on send button.
    streaming: bool = False

    # Controlled textarea value.
    input_value: str = ""

    # Prevents double-load when the page component mounts twice.
    _history_loaded: bool = False

    # ------------------------------------------------------------------ events

    @rx.event
    def set_input(self, value: str):
        self.input_value = value

    @rx.event
    def handle_key_down(self, key: str):
        """Submit on Enter; Shift+Enter inserts a newline (handled client-side)."""
        if key == "Enter" and not self.streaming and self.input_value.strip():
            return CopilotState.send_message

    @rx.event
    async def load_history(self):
        """Fetch prior chat messages from DB on page load (FR-7.9)."""
        if self._history_loaded:
            return
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return
            rows = session.exec(
                select(ChatMessage)
                .where(ChatMessage.user_id == user.id)
                .order_by(ChatMessage.timestamp)
            ).all()
            self.messages = [
                {
                    "role": r.role,
                    "content": r.content,
                    "trace_sources": (
                        json.loads(r.trace_sources) if r.trace_sources else []
                    ),
                }
                for r in rows
            ]
        self._history_loaded = True

    @rx.event
    def send_quick_prompt(self, prompt: str):
        """Submit one of the welcome-card suggestion chips (FR-7.7)."""
        self.input_value = prompt
        return CopilotState.send_message

    @rx.event
    async def send_message(self):
        """Stream the assistant reply via typed SSE events and persist both turns.

        Event handling (FR-7.4 / Story 6.3 AC):
          token   → append text to streaming_content, yield
          trace   → store human-readable source labels in current_trace_sources, yield
          error   → overwrite streaming_content with the error message, yield
          done    → finalise the turn (move to messages, clear buffer, persist to DB)
          unknown → ignored (forward-compatibility AC)
        """
        text = self.input_value.strip()
        if not text or self.streaming:
            return

        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return
            user_id = user.id

        # Append user bubble, clear input, enter streaming mode.
        self.messages = self.messages + [
            {"role": "user", "content": text, "trace_sources": []}
        ]
        self.input_value = ""
        self.streaming = True
        self.streaming_content = ""
        self.current_trace_sources = []
        yield

        # Persist user turn (best-effort).
        try:
            with rx.session() as session:
                session.add(
                    ChatMessage(  # type: ignore[call-arg]
                        user_id=user_id,
                        role="user",
                        content=text,
                    )
                )
                session.commit()
        except Exception:
            log.exception("Failed to persist user message for user_id=%d", user_id)

        api_messages = [
            {"role": m["role"], "content": m["content"]} for m in self.messages
        ]

        assistant_content = ""
        trace_sources: list[str] = []
        error_occurred = False

        with rx.session() as tool_session:
            async for event in astream_events(
                api_messages,
                user_id=user_id,
                session=tool_session,
            ):
                etype = event.get("type")

                if etype == "token":
                    assistant_content += event.get("text", "")
                    self.streaming_content = assistant_content
                    yield

                elif etype == "trace":
                    raw_sources: list[str] = event.get("sources", [])
                    trace_sources = [_label(s) for s in raw_sources]
                    self.current_trace_sources = trace_sources
                    yield

                elif etype == "error":
                    # Honest error frame — overwrite whatever content was streamed.
                    assistant_content = event.get("text", "Something went wrong.")
                    self.streaming_content = assistant_content
                    error_occurred = True
                    yield

                elif etype == "done":
                    # Finalise: move completed turn into messages list, clear buffer.
                    self.messages = self.messages + [
                        {
                            "role": "assistant",
                            "content": assistant_content,
                            "trace_sources": trace_sources,
                        }
                    ]
                    self.streaming_content = ""
                    self.current_trace_sources = []
                    self.streaming = False
                    yield

                # Unknown event types are silently ignored (forward-compat AC).

        # Persist assistant turn (best-effort; skip empty content on error with no text).
        if assistant_content:
            try:
                with rx.session() as session:
                    session.add(
                        ChatMessage(  # type: ignore[call-arg]
                            user_id=user_id,
                            role="assistant",
                            content=assistant_content,
                            trace_sources=(
                                json.dumps(trace_sources) if trace_sources else None
                            ),
                        )
                    )
                    session.commit()
            except Exception:
                log.exception(
                    "Failed to persist assistant message for user_id=%d", user_id
                )
