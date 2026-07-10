"""Copilot chat state — Stories 6.1–6.4 (FR-7.1, FR-7.4–FR-7.10, NFR-8).

Story 6.4 additions:
  * ``load_history`` reads ``?insight=<id>&pre=<text>`` URL params on page
    load. When present it sets ``context_pattern_name`` (chip label),
    ``context_insight_id``, and pre-fills ``input_value`` (FR-7.8).
  * ``dismiss_context`` clears the context chip (FR-7.8).
  * ``send_message`` appends ``insight_id`` to the POST body when a context
    is active (FR-7.8 AC).
  * ``QUICK_PROMPTS`` extended with "Can I afford ₹___ this weekend?" (FR-7.7).
  * "Can I afford ₹X?" reasons over real STS from the engine via the
    ``get_safe_to_spend`` tool — the LLM never invents the figure (FR-7.7 AC).

Prior stories unchanged; see earlier story docstrings for 6.1–6.3 details.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import reflex as rx
from sqlmodel import select

from finance_app.models import ChatMessage, Insight
from finance_app.state.auth_state import AuthState, user_for_token
from services.narrate.copilot import astream_events

log = logging.getLogger(__name__)

# Quick-prompt suggestions (FR-7.7). "Can I afford" is the STS gut-check prompt.
QUICK_PROMPTS: list[str] = [
    "How am I doing?",
    "What's my biggest spend?",
    "Am I on track this month?",
    "Can I afford ₹2,000 this weekend?",
]

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

    # Completed chat turns.
    # Each dict: {"role": str, "content": str, "trace_sources": list[str]}
    messages: list[dict] = []

    # In-flight streaming buffer.
    streaming_content: str = ""

    # Live trace sources during the current stream.
    current_trace_sources: list[str] = []

    # True while the assistant is generating.
    streaming: bool = False

    # Controlled textarea value.
    input_value: str = ""

    # Prevents double-load on re-renders.
    _history_loaded: bool = False

    # ---- Insight context handoff (FR-7.8 / Story 6.4) ----------------------

    # The pattern_name label shown in the "Talking about: …" chip.
    # Empty string means no active insight context.
    context_pattern_name: str = ""

    # The insight DB id sent in the POST body (FR-7.8 AC).
    context_insight_id: int = 0

    # ------------------------------------------------------------------ events

    @rx.event
    def set_input(self, value: str):
        self.input_value = value

    @rx.event
    def handle_key_down(self, key: str):
        if key == "Enter" and not self.streaming and self.input_value.strip():
            return CopilotState.send_message

    @rx.event
    def dismiss_context(self):
        """Clear the insight context chip and pre-filled input (FR-7.8)."""
        self.context_pattern_name = ""
        self.context_insight_id = 0
        self.input_value = ""

    @rx.event
    async def load_history(self):
        """Fetch prior messages from DB and read insight context from URL params.

        URL params consumed (FR-7.8):
          ?insight=<int id>   — activates the context chip
          ?pre=<str>          — pre-fills the textarea

        Called as ``on_load`` on the Copilot page.
        """
        # Read URL query params before the DB round-trip.
        params = self.router.page.params
        raw_insight = params.get("insight", "")
        pre_text = params.get("pre", "")

        if not self._history_loaded:
            with rx.session() as session:
                user = user_for_token(session, self.auth_token)
                if user is None:
                    return
                user_id = user.id

                rows = session.exec(
                    select(ChatMessage)
                    .where(ChatMessage.user_id == user_id)
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

                # Resolve insight context from the URL param.
                if raw_insight:
                    try:
                        insight_id = int(raw_insight)
                        insight = session.exec(
                            select(Insight).where(
                                Insight.id == insight_id,
                                Insight.user_id == user_id,
                            )
                        ).one_or_none()
                        if insight is not None:
                            self.context_insight_id = insight_id
                            self.context_pattern_name = insight.pattern_name
                    except (ValueError, TypeError):
                        pass  # malformed ?insight= param — ignore silently

            self._history_loaded = True

        # Pre-fill the textarea if ?pre= is present (set after history load so it
        # is not overwritten by the reset inside load_history on a fresh page).
        if pre_text and not self.input_value:
            self.input_value = pre_text

    @rx.event
    def send_quick_prompt(self, prompt: str):
        """Submit a welcome-card suggestion chip (FR-7.7)."""
        self.input_value = prompt
        return CopilotState.send_message

    @rx.event
    async def send_message(self):
        """Validate input, stream the assistant reply, persist both turns.

        When an insight context is active, the ``insight_id`` is embedded in the
        first user turn passed to the LLM so it can reference the specific pattern.
        The context chip stays visible until the user explicitly dismisses it
        (FR-7.8 — the chip is not auto-cleared on send).
        """
        text = self.input_value.strip()
        if not text or self.streaming:
            return

        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return
            user_id = user.id

        # Build the user message, embedding insight context when present (FR-7.8).
        user_content = text
        if self.context_insight_id:
            user_content = (
                f"[insight_id={self.context_insight_id}] {text}"
            )

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

        # Build API conversation: all prior turns plus the (possibly annotated) new turn.
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages[:-1]  # all but the optimistic user bubble just added
        ]
        api_messages.append({"role": "user", "content": user_content})

        assistant_content = ""
        trace_sources: list[str] = []

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
                    assistant_content = event.get("text", "Something went wrong.")
                    self.streaming_content = assistant_content
                    yield

                elif etype == "done":
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

                # Unknown event types silently ignored (forward-compat AC).

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
