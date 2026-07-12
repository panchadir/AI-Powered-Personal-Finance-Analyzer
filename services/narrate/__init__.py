"""Narration: evidence-pack-to-language, Claude narrator, Copilot tool runner.

Receives the engine's evidence pack as input and calls the LLM only for language.
No financial number may originate here (AD-1). Populated in Epics 5-7.
"""
from services.narrate.briefing import (
    BriefingContext,
    build_fallback_briefing,
    generate_briefing,
)
from services.narrate.insight_narrator import (
    InsightNarration,
    InsightNarrationInput,
    NarrationEvidencePoint,
    build_fallback_insight_narration,
    generate_insight_narration,
)

__all__ = [
    "BriefingContext",
    "generate_briefing",
    "build_fallback_briefing",
    "InsightNarrationInput",
    "NarrationEvidencePoint",
    "InsightNarration",
    "generate_insight_narration",
    "build_fallback_insight_narration",
]
