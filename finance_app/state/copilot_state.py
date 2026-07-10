"""Copilot chat state — Story 6.1 (FR-7.1, FR-7.9, NFR-8).

Drives the streaming chat UI:
  * ``send_message`` appends the user turn, streams assistant tokens via
    ``services.narrate.copilot.astream_reply``, persists both turns to
    ``chat_messages`` (server-side, scoped to ``user_id`` — never localStorage).
  * ``load_history`` is the ``on_load`` handler: fetches prior messages from DB
    so the thread is populated when the user returns to the page.
  * ``set_input`` drives the controlled textarea.

Streaming approach: ``astream_reply`` is an async generator. The event handler
loops over it, appending each token to ``streaming_content`` and yielding to
push the update over Reflex's WebSocket. Once streaming ends, the complete
response is appended to ``messages`` and ``streaming_content`` is cleared.

Accessibility (NFR-8 / FR-7.10):
  * ``role="log"`` + ``aria-live="polite"`` are set on the thread element in the
    page component (not here — state owns data, component owns markup).
  * ``streaming`` drives ``aria-disabled`` on the send button so it stays
    keyboard-focusable while a response is in flight (FR-7.10).

Architecture (AD-2): only this file imports ``reflex``; ``services.narrate`` is
framework-agnostic. No financial arithmetic lives here (AD-1 / NFR-3).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import reflex as rx
from sqlmodel import select

from finance_app.models import ChatMessage
from finance_app.state.auth_state import AuthState, user_for_token
from services.narrate.copilot import astream_reply

log = logging.getLogger(__name__)

# Quick-prompt suggestions shown on the welcome card (FR-7.7).
QUICK_PROMPTS: list[str] = [
    "How am I doing?",
    "What's my biggest spend?",
    "Am I on track this month?",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CopilotState(AuthState):
    """State for the Copilot chat page."""

    # Completed chat turns rendered in the thread.
    # Each dict: {"role": "user"|"assistant", "content": "..."}
    messages: list[dict] = []

    # Token buffer for the in-flight assistant response (appended token-by-token).
    streaming_content: str = ""

    # True while the assistant is generating — drives aria-disabled on the send btn.
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
        """Submit on Enter (without Shift); Shift+Enter is a newline (handled client-side)."""
        if key == "Enter" and not self.streaming and self.input_value.strip():
            return CopilotState.send_message

    @rx.event
    async def load_history(self):
        """Fetch prior chat messages from DB on page load (FR-7.9).

        Called as ``on_load`` on the Copilot page. Loads only once per session
        to avoid re-fetching when state updates trigger re-renders.
        """
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
            self.messages = [{"role": r.role, "content": r.content} for r in rows]
        self._history_loaded = True

    @rx.event
    def send_quick_prompt(self, prompt: str):
        """Submit one of the welcome-card suggestion chips (FR-7.7)."""
        self.input_value = prompt
        return CopilotState.send_message

    @rx.event
    async def send_message(self):
        """Validate input, stream the assistant reply, persist both turns to DB.

        Flow:
          1. Guard: empty input or already streaming → no-op.
          2. Resolve user_id from the session cookie (IDOR guard — all DB ops use this id).
          3. Optimistically append user bubble + clear input → yield (immediate UI update).
          4. Persist user turn to DB.
          5. Stream tokens from the LLM, appending each to ``streaming_content`` → yield.
          6. On finish (or error): move completed text into ``messages``, clear buffer.
          7. Persist assistant turn to DB.
        """
        text = self.input_value.strip()
        if not text or self.streaming:
            return

        # Resolve user_id before any DB writes (all writes use this id — IDOR guard).
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return
            user_id = user.id

        # Step 3: append user bubble, clear input, enter streaming mode.
        self.messages = self.messages + [{"role": "user", "content": text}]
        self.input_value = ""
        self.streaming = True
        self.streaming_content = ""
        yield

        # Step 4: persist user turn (best-effort; a failure doesn't abort the response).
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
            log.exception("Failed to persist user chat message for user_id=%d", user_id)

        # Build the full conversation history for the API (all prior turns + new user turn).
        api_messages = [{"role": m["role"], "content": m["content"]} for m in self.messages]

        # Step 5: stream tokens from the async LLM generator.
        # user_id and session are passed so tool calls are IDOR-safe (Story 6.2).
        assistant_content = ""
        try:
            with rx.session() as tool_session:
                async for token in astream_reply(
                    api_messages,
                    user_id=user_id,
                    session=tool_session,
                ):
                    assistant_content += token
                    self.streaming_content = assistant_content
                    yield
        except Exception:
            log.exception("Copilot stream error for user_id=%d", user_id)
            assistant_content = (
                "I ran into a problem and couldn't finish that response. "
                "Please try again in a moment."
            )
            self.streaming_content = assistant_content
            yield

        # Step 6: finalise — move completed response into messages list, clear buffer.
        self.messages = self.messages + [
            {"role": "assistant", "content": assistant_content}
        ]
        self.streaming_content = ""
        self.streaming = False
        yield

        # Step 7: persist assistant turn (best-effort).
        try:
            with rx.session() as session:
                session.add(
                    ChatMessage(  # type: ignore[call-arg]
                        user_id=user_id,
                        role="assistant",
                        content=assistant_content,
                    )
                )
                session.commit()
        except Exception:
            log.exception(
                "Failed to persist assistant chat message for user_id=%d", user_id
            )
