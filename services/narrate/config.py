"""LLM model routing constants (single source of truth).

Model IDs live here, never hardcoded at call sites (project-context "LLM model IDs are
constants" rule). Narration/Copilot constants land in Epic 5/6; Tier-2 categorization is
populated now (Story 3.2).
"""
from __future__ import annotations

#: Tier-2 transaction categorizer (services/categorize/llm_categorizer.py, Story 3.2).
TIER2_CATEGORIZATION_MODEL = "claude-haiku-4-5"
