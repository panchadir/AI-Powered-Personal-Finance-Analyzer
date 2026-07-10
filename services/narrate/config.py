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
CATEGORIZATION_MODEL = "claude-haiku-4-5"

#: Morning briefing (Epic 5) and Copilot (Epic 6). Tone quality matters most here.
NARRATION_MODEL = "claude-opus-4-8"

#: Drop-in replacement for ``NARRATION_MODEL`` if the API budget tightens (NFR-4).
COST_LEVER_MODEL = "claude-sonnet-5"

#: A briefing is 2–4 sentences (FR-6.2). Cap generation so a runaway response cannot burn
#: budget or overflow the panel.
BRIEFING_MAX_TOKENS = 400

#: Deterministic narration — the same evidence pack should yield the same briefing.
NARRATION_TEMPERATURE = 0.0

#: Environment variable holding the API key. Absent -> narration degrades to a deterministic
#: fallback rather than crashing the dashboard (NFR-1: degrade visibly, never silently wrong).
API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
