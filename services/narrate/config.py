"""LLM model routing constants (single source of truth).

Model IDs live here, never hardcoded at call sites:
  - Tier-2 categorization: ``claude-haiku-4-5``
  - Narration + Copilot:   ``claude-opus-4-8`` (cost lever: ``claude-sonnet-5``)

NFR-4 (cost): total Claude spend for the build + demo cycle is budgeted under $15. Two levers
are wired here rather than at the call sites:

* ``NARRATION_MODEL`` can be flipped to ``COST_LEVER_MODEL`` in one place.
* System prompts are sent with ``cache_control: {"type": "ephemeral"}`` (see
  ``services/narrate/briefing.py``), which bills the cached portion at ~10% on a read.

**AD-1 boundary:** nothing in ``services/narrate/`` computes a number. This package turns an
evidence pack that the deterministic engine already produced into prose. It must not import
``services/engine/`` — the pack arrives as an argument.
"""
from __future__ import annotations

#: Tier-2 transaction categorization (Epic 3). Cheap, high-volume, structured output.
TIER2_CATEGORIZATION_MODEL = "claude-haiku-4-5-20251001"

#: Morning briefing (Epic 5) and Copilot (Epic 6). Tone quality matters most here.
NARRATION_MODEL = "claude-opus-4-8"

#: Drop-in replacement for ``NARRATION_MODEL`` if the API budget tightens (NFR-4).
COST_LEVER_MODEL = "claude-sonnet-5"

#: Briefing narration and Copilot chat (high quality, cached system prompt).
COPILOT_MODEL = "claude-opus-4-8"

#: Cost lever — swap COPILOT_MODEL for this string to reduce spend.
COPILOT_MODEL_COST_LEVER = "claude-sonnet-5"

#: A briefing is 2–4 sentences (FR-6.2). Cap generation so a runaway response cannot burn
#: budget or overflow the panel.
BRIEFING_MAX_TOKENS = 400

#: Deterministic narration — the same evidence pack should yield the same briefing.
NARRATION_TEMPERATURE = 0.0

#: Environment variable holding the API key. Absent -> narration degrades to a deterministic
#: fallback rather than crashing the dashboard (NFR-1: degrade visibly, never silently wrong).
API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

#: An insight narration is exactly 4 short sentences (Story 7.2) — well under
#: BRIEFING_MAX_TOKENS.
INSIGHT_NARRATION_MAX_TOKENS = 200

#: Case-insensitive substrings that mark a generated insight as touching a regulated
#: investment topic (FR-8.3 / Story 7.2 AC #3). "invest" also catches investment/investing;
#: "mutual fund" also catches mutual funds. A bare "return" was deliberately dropped — it
#: false-positived on ordinary banking vocabulary ("returned payment") and merchant names
#: (e.g. a real "Amazon Returns" refund); the multi-word phrases below are unambiguous.
SEBI_TRIGGER_KEYWORDS: tuple[str, ...] = (
    "invest",
    "equity",
    "mutual fund",
    "rate of return",
    "return on investment",
)

#: Exact disclaimer appended once (never duplicated) when SEBI_TRIGGER_KEYWORDS match.
SEBI_DISCLAIMER = "This is not investment advice."
