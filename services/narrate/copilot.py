"""Copilot streaming service — Stories 6.1–6.3 (FR-7.1–FR-7.5).

Public API:
  ``astream_events(messages, user_id, session)``
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
  Non-streaming rounds until stop_reason == end_turn, then a final streaming
  pass that emits token events.  Tool names are collected as trace sources and
  emitted as a single ``trace`` event before ``done``.

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
import os
from collections.abc import AsyncGenerator
from typing import Any

import anthropic
from sqlmodel import Session

from services.narrate.config import COPILOT_MODEL
from services.narrate.tools import TOOL_SCHEMAS, run_tool

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
    session: Session,
    api_key: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Async-stream typed event dicts for the Copilot response.

    Yields ``token``, ``trace``, ``error`` (on failure), and ``done`` events.
    ``done`` is guaranteed from a ``finally`` block — the caller never hangs.

    Args:
        messages:  Full conversation history including the new user turn.
        user_id:   Authenticated user's id — injected into every tool call.
        session:   Open SQLModel session for tool DB queries.
        api_key:   Anthropic API key; falls back to ``ANTHROPIC_API_KEY`` env var.
    """
    client = anthropic.AsyncAnthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
    )

    conversation: list[dict[str, Any]] = list(messages)  # type: ignore[assignment]
    tools_called: list[str] = []  # accumulates tool names for the trace event

    try:
        # ---- Tool-use rounds (non-streaming) --------------------------------
        for _round in range(_MAX_TOOL_ROUNDS):
            response = await client.messages.create(
                model=COPILOT_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM,
                tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
                messages=conversation,  # type: ignore[arg-type]
            )

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason == "end_turn" or not tool_use_blocks:
                # No more tool calls needed — stream the final response.
                break

            # Execute each requested tool, collect results.
            conversation.append(
                {"role": "assistant", "content": response.content}  # type: ignore[arg-type]
            )
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                tools_called.append(block.name)
                result = run_tool(
                    block.name,
                    block.input,  # type: ignore[arg-type]
                    user_id=user_id,
                    session=session,
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
            # Exhausted tool rounds — instruct model to answer with what it has.
            conversation.append(
                {
                    "role": "user",
                    "content": "Please give your best honest answer based on the data retrieved.",
                }
            )

        # ---- Final streaming response ----------------------------------------
        async with client.messages.stream(
            model=COPILOT_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM,
            tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
            messages=conversation,  # type: ignore[arg-type]
        ) as stream:
            async for text in stream.text_stream:
                yield _token_event(text)

        # Emit trace event after streaming completes (FR-7.5).
        if tools_called:
            yield _trace_event(tools_called)

    except Exception as exc:
        # Emit an honest error frame before done so the UI can show it (Story 6.3 AC).
        yield _error_event(
            "I ran into a problem and couldn't finish that response. "
            "Please try again in a moment."
        )

    finally:
        # ``done`` is ALWAYS emitted — even on error, even mid-token (FR-7.3 / Story 6.3 AC).
        yield _done_event()
