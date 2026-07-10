"""LLM model routing constants (single source of truth).

Model IDs live here, never hardcoded at call sites:
  - Tier-2 categorization: ``claude-haiku-4-5``
  - Narration + Copilot:   ``claude-opus-4-8`` (cost lever: ``claude-sonnet-5``)
"""

#: Tier-2 transaction categorization (cheap, fast structured output).
CATEGORIZE_MODEL = "claude-haiku-4-5-20251001"

#: Briefing narration and Copilot chat (high quality, cached system prompt).
COPILOT_MODEL = "claude-opus-4-8"

#: Cost lever — swap COPILOT_MODEL for this string to reduce spend.
COPILOT_MODEL_COST_LEVER = "claude-sonnet-5"
