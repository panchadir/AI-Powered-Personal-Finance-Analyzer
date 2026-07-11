"""Copilot streaming service — Stories 6.1–6.3 (FR-7.1–FR-7.5).

Public API:
  ``astream_events(messages, user_id, data_factory)``
    Async generator that yields typed event dicts (SSE contract, FR-7.4):

      {"type": "token",  "text": "<string>"}
      {"type": "trace",  "sources": ["tool1", "tool2", ...]}
      {"type": "done"}
      {"type": "error",  "text": "<message>"}   — emitted before done on failure

    The ``done`` event is ALWAYS emitted from a ``finally`` block — the
    caller's EventSource / WebSocket never hangs (FR-7.3 / Story 6.3 AC).

    Unknown event types must be ignored gracefully by the caller (FR-7.3,
    forward-compatibility AC).

Tool-use loop (Story 6.2 — unchanged):
  Each round streams through ``messages.stream()``. If the model requests
  tool calls, ``text_stream`` yields nothing (tool-use and text are mutually
  exclusive in one response); the final message carries ``tool_use`` blocks.
  Tools are executed against a short-lived data provider from ``data_factory``
  (never held open during streaming). The loop continues until the model
  produces a text response — which is streamed live as token events — or
  until ``_MAX_TOOL_ROUNDS`` is exhausted, in which case a final stream call
  (without tools) forces a text answer.

Story 6.2 AC checklist (unchanged):
  * Only the 5 read-only tools in ``tools.TOOL_SCHEMAS`` — no write path.
  * Every tool call uses the caller-supplied ``user_id`` (IDOR guard).
  * 4 hardcoded honesty rules in system prompt (FR-7.3).
  * ``COPILOT_MODEL`` constant, never hardcoded.
  * System prompt ``cache_control: ephemeral`` (NFR-4).

Architecture (AD-1 / NFR-3): no ``reflex`` / ``finance_app.*`` imports.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractContextManager
from typing import Any

import anthropic

from services.narrate.config import COPILOT_MODEL
from services.narrate.tools import CopilotData, TOOL_SCHEMAS, run_tool

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — static portion marked cache_control: ephemeral (NFR-4)
# ---------------------------------------------------------------------------

_SYSTEM: list[dict[str, Any]] = [
    {
        "type": "text",
        "text": (
            "You are an honest, calm AI Copilot for a personal finance app used by "
            "people in India. Your only job is to help the user understand their own "
            "finances using the transaction data they have already uploaded.\n\n"

            "HARD RULES — non-configurable, always enforced (FR-7.3):\n"
            "1. NEVER invent, estimate, or extrapolate financial figures. "
            "Only cite values returned by the tools. If a tool returns "
            "available=false, tell the user that data is not available yet.\n"
            "2. Express uncertainty explicitly. When you have limited data, say so: "
            '"I only have one month of data, so I can\'t be certain…"\n'
            "3. NEVER give investment recommendations of any kind — no stocks, mutual "
            "funds, gold, crypto, or asset allocation advice. "
            "This is a SEBI IA boundary. If asked, say: "
            '"I\'m not able to give investment advice — please consult a SEBI-registered advisor."\n'
            "4. Always populate the trace field citing which data sources you used "
            "(e.g. which tool calls returned the figures you mention).\n\n"

            "Tone: honest, warm, calm, non-judgmental. Use Indian Rupee (₹) formatting. "
            "No jargon. Never shame the user about their spending.\n\n"

            "When data is unavailable: say so plainly and helpfully. "
            '"I don\'t have enough information to answer that" is a valid and correct response.'
        ),
        "cache_control": {"type": "ephemeral"},
    }
]

_MAX_TOKENS = 1024
_MAX_TOOL_ROUNDS = 5

# ---------------------------------------------------------------------------
# Typed event constructors (SSE contract — FR-7.4)
# ---------------------------------------------------------------------------

def _token_event(text: str) -> dict[str, Any]:
    return {"type": "token", "text": text}

def _trace_event(sources: list[str]) -> dict[str, Any]:
    return {"type": "trace", "sources": sources}

def _error_event(text: str) -> dict[str, Any]:
    return {"type": "error", "text": text}

def _done_event() -> dict[str, Any]:
    return {"type": "done"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def astream_events(
    messages: list[dict[str, str]],
    *,
    user_id: int,
    data_factory: Callable[[], AbstractContextManager[CopilotData]],
    api_key: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Async-stream typed event dicts for the Copilot response.

    Yields ``token``, ``trace``, ``error`` (on failure), and ``done`` events.
    ``done`` is guaranteed from a ``finally`` block — the caller never hangs.

    Each tool execution opens its own short-lived, user-scoped data provider via
    ``data_factory`` so no DB connection is held open during the streaming phase, and the
    tools never receive a raw session or ``user_id`` they could misuse (AD-4).

    Args:
        messages:      Full conversation history including the new user turn.
        user_id:       Authenticated user's id — used for logging (the data provider is
                       already bound to it).
        data_factory:  Zero-arg callable returning a context manager that yields a
                       user-scoped :class:`~services.narrate.tools.CopilotData`
                       (e.g. ``lambda: open_copilot_data(user_id)``).
        api_key:       Anthropic API key; falls back to ``ANTHROPIC_API_KEY`` env var.
    """
    client = anthropic.AsyncAnthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
    )

    conversation: list[dict[str, Any]] = list(messages)  # type: ignore[assignment]
    tools_called: list[str] = []

    try:
        # ---- Tool-use rounds (streaming, tool-aware) -------------------------
        # text_stream yields nothing when the model chooses tool_use, so we can
        # stream live tokens AND detect tool_use from the same stream call.
        for _round in range(_MAX_TOOL_ROUNDS):
            async with client.messages.stream(
                model=COPILOT_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM,
                tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
                messages=conversation,  # type: ignore[arg-type]
            ) as stream:
                async for text in stream.text_stream:
                    yield _token_event(text)
                final_message = await stream.get_final_message()

            tool_use_blocks = [b for b in final_message.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # Text response — tokens already yielded above. Done.
                break

            # Execute each requested tool with a short-lived session.
            conversation.append(
                {"role": "assistant", "content": list(final_message.content)}  # type: ignore[arg-type]
            )
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                tools_called.append(block.name)
                with data_factory() as data:
                    result = run_tool(
                        block.name,
                        dict(block.input),  # type: ignore[arg-type]
                        data=data,
                    )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
            conversation.append({"role": "user", "content": tool_results})
        else:
            # All _MAX_TOOL_ROUNDS were tool-use rounds. Stream a final answer
            # WITHOUT tools so the model is forced to reply in text.
            async with client.messages.stream(
                model=COPILOT_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM,
                messages=conversation,  # type: ignore[arg-type]
            ) as stream:
                async for text in stream.text_stream:
                    yield _token_event(text)

        # Emit trace event after streaming completes (FR-7.5).
        if tools_called:
            yield _trace_event(tools_called)

    except Exception:
        log.exception("Copilot streaming failed for user_id=%d", user_id)
        yield _error_event(
            "I ran into a problem and couldn't finish that response. "
            "Please try again in a moment."
        )

    finally:
        # ``done`` is ALWAYS emitted — even on error, even mid-token (FR-7.3 / Story 6.3 AC).
        yield _done_event()
