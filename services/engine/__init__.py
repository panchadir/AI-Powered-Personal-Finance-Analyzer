"""Deterministic financial engine: safe_to_spend, confidence_score, commitments.

No LLM touches these numbers (AD-1). All arithmetic uses ``Decimal`` (or integer
paise), never ``float``. ``pytest services/engine/`` is the non-negotiable MVP quality
gate and must run with zero LLM calls. Populated in Epic 4.
"""
from services.engine.confidence_score import ScoreResult, compute_confidence_score
from services.engine.safe_to_spend import (
    CommitmentInput,
    EngineInput,
    EvidencePack,
    compute_safe_to_spend,
)

__all__ = [
    "CommitmentInput",
    "EngineInput",
    "EvidencePack",
    "compute_safe_to_spend",
    "ScoreResult",
    "compute_confidence_score",
]
