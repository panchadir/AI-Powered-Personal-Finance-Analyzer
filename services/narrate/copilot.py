"""Copilot streaming service (Story 6.1 / FR-7.1–FR-7.3).

Wraps the Anthropic async streaming API and yields plain text tokens to the
caller (a Reflex async state event handler) so the UI can push each token over
the existing WebSocket.

Story 6.1 scope — chat UI + streaming + server-side history persistence:
  * ``astream_reply`` is the only public function here.
  * No read-only tool calls yet (Story 6.2).
  * No SSE contract yet (Story 6.3).

Honesty rules hard-coded in the system prompt (FR-7.3, non-configurable):
  1. Never invent or estimate financial figures.
  2. Express uncertainty explicitly when data is incomplete.
  3. Never give investment recommendations (SEBI IA boundary).
  4. Always say so honestly when data is insufficient.

Architecture note (AD-1 / NFR-3): this module MUST NOT import anything from
``services.engine`` or ``finance_app``. It receives conversation context as
plain Python values and returns token strings.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import anthropic

from services.narrate.config import COPILOT_MODEL

# The system prompt is marked cache_control so the ~800-token static portion is
# cached across turns (NFR-4 / ~90 % saving on the cached portion).
_SYSTEM: list[dict[str, Any]] = [
    {
        "type": "text",
        "text": (
            "You are an honest, calm AI Copilot for a personal finance app used by "
            "people in India. Your only job is to help the user understand their own "
            "finances using the transaction data they have already uploaded.\n\n"
            "HARD RULES (non-configurable, always enforced):\n"
            "1. NEVER invent, estimate, or extrapolate financial figures. "
            "If you do not have the data, say so plainly.\n"
            "2. Express uncertainty explicitly. Use phrases like "
            '"I only have one month of data, so I can\'t be certain…" '
            "rather than guessing.\n"
            "3. NEVER give investment recommendations of any kind "
            "(no stocks, mutual funds, gold, crypto, or asset allocation advice). "
            "This is a SEBI IA boundary — do not cross it.\n"
            "4. Keep answers short, plain-language, and non-judgmental. "
            "Use Indian Rupee (₹) formatting. No jargon.\n"
            "5. If a question is outside your data or scope, say "
            '"I don\'t have enough information to answer that confidently." — '
            "never fabricate an answer.\n\n"
            "Tone contract: honest, warm, calm, non-judgmental. "
            "Never shame the user about their spending."
        ),
        "cache_control": {"type": "ephemeral"},
    }
]


async def astream_reply(
    messages: list[dict[str, str]],
    *,
    api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    """Async-stream Copilot reply tokens for the given conversation history.

    Args:
        messages: List of ``{"role": "user"|"assistant", "content": "..."}`` dicts
                  representing the full conversation so far (caller appends the new
                  user turn before calling this function).
        api_key:  Anthropic API key. Falls back to ``ANTHROPIC_API_KEY`` env var.

    Yields:
        Individual text delta strings as they arrive from the API.

    Raises:
        anthropic.APIError: propagated to the caller for honest error handling.
    """
    client = anthropic.AsyncAnthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
    )

    async with client.messages.stream(
        model=COPILOT_MODEL,
        max_tokens=1024,
        system=_SYSTEM,
        messages=messages,  # type: ignore[arg-type]
    ) as stream:
        async for text in stream.text_stream:
            yield text
