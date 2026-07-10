"""Copilot streaming service — Story 6.1 + Story 6.2 (FR-7.1–FR-7.4).

Public API:
  ``astream_reply(messages, user_id, session)``
    Async generator that yields text token strings.  Internally runs the
    Anthropic agentic tool-use loop:
      1. Call the model with the 5 read-only tool schemas.
      2. If the model requests a tool, run it via ``services.narrate.tools.run_tool``
         (which queries the DB with an explicit ``user_id`` filter — IDOR guard).
      3. Feed the tool result back and continue until the model emits a final
         text response, which is streamed token-by-token.

Story 6.2 AC checklist:
  * Only the 5 read-only tools defined in ``tools.TOOL_SCHEMAS`` appear in the
    tool list — no write-capable function (FR-7.2).
  * Every tool call uses the caller-supplied ``user_id`` — no cross-user leak (FR-7.2).
  * System prompt contains the 4 hardcoded honesty rules (FR-7.3).
  * Model constant from ``config.COPILOT_MODEL``, never hardcoded (FR-7.2 AC).
  * System prompt marked ``cache_control: ephemeral`` (NFR-4).
  * ``/copilot/chat`` auth uses the httpOnly cookie, NOT URL/query-param token
    (enforced in the Reflex state handler, not here — AD-5 × AD-11 seam note).

Architecture (AD-1 / NFR-3):
  * No ``reflex`` / ``finance_app.*`` imports at the module level.
  * DB access is done exclusively through the injected ``session`` parameter.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import anthropic
from sqlmodel import Session

from services.narrate.config import COPILOT_MODEL
from services.narrate.tools import TOOL_SCHEMAS, run_tool

# ---------------------------------------------------------------------------
# System prompt — static, cache_control: ephemeral (NFR-4)
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

# Maximum tokens for a single assistant turn.
_MAX_TOKENS = 1024

# Safety cap on tool-use rounds to prevent runaway loops.
_MAX_TOOL_ROUNDS = 5


# ---------------------------------------------------------------------------
# Public streaming entry point
# ---------------------------------------------------------------------------

async def astream_reply(
    messages: list[dict[str, str]],
    *,
    user_id: int,
    session: Session,
    api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    """Async-stream Copilot reply tokens, running the tool-use loop as needed.

    Args:
        messages:  Full conversation history including the new user turn.
        user_id:   Authenticated user's id — passed to every tool call (IDOR guard).
        session:   Open SQLModel session for tool DB queries.
        api_key:   Anthropic API key; falls back to ``ANTHROPIC_API_KEY`` env var.

    Yields:
        Text delta strings as they arrive from the final streaming response.

    The tool-use loop (non-streaming):
        The model may request one or more tool calls before producing its final
        text response.  Each round executes the requested tools, appends the
        results to the conversation, and calls the model again — up to
        ``_MAX_TOOL_ROUNDS`` rounds.  The final response is then streamed.
    """
    client = anthropic.AsyncAnthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
    )

    # Mutable copy — we append tool_use / tool_result turns during the loop.
    conversation: list[dict[str, Any]] = list(messages)  # type: ignore[assignment]

    for _round in range(_MAX_TOOL_ROUNDS):
        # Non-streaming call to check for tool requests first.
        response = await client.messages.create(
            model=COPILOT_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM,
            tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
            messages=conversation,  # type: ignore[arg-type]
        )

        # Collect any text blocks from this response (may be empty when tool_use).
        text_blocks = [b.text for b in response.content if b.type == "text"]
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" or not tool_use_blocks:
            # Final response — stream it for real.
            # Re-issue as a streaming call so the UI gets token-by-token output.
            async with client.messages.stream(
                model=COPILOT_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM,
                tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
                messages=conversation,  # type: ignore[arg-type]
            ) as stream:
                async for text in stream.text_stream:
                    yield text
            return

        # Tool use round — execute each requested tool and append results.
        # Append the assistant's tool_use turn first (required by Anthropic API).
        conversation.append({"role": "assistant", "content": response.content})  # type: ignore[arg-type]

        tool_results: list[dict[str, Any]] = []
        for block in tool_use_blocks:
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
                    "content": _serialise(result),
                }
            )

        conversation.append({"role": "user", "content": tool_results})

    # Exhausted tool rounds — ask the model to answer with what it has.
    conversation.append(
        {
            "role": "user",
            "content": "Please give your best honest answer based on the data retrieved.",
        }
    )
    async with client.messages.stream(
        model=COPILOT_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM,
        messages=conversation,  # type: ignore[arg-type]
    ) as stream:
        async for text in stream.text_stream:
            yield text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise(obj: Any) -> str:
    """Convert a tool result dict to a compact JSON string for the tool_result block."""
    import json
    return json.dumps(obj, ensure_ascii=False, default=str)
