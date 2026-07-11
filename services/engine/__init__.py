"""Deterministic financial engine: safe_to_spend, confidence_score, commitments.

No LLM touches these numbers (AD-1). All arithmetic uses ``Decimal`` (or integer
paise), never ``float``. ``pytest services/engine/`` is the non-negotiable MVP quality
gate and must run with zero LLM calls. Populated in Epic 4.
"""
from services.engine.commitment_detector import (
    CommitmentCandidate,
    detect_recurring_commitments,
)
from services.engine.confidence_score import ScoreResult, compute_confidence_score
from services.engine.inputs import (
    DEFAULT_BUFFER,
    CommitmentRecord,
    IncomeSignal,
    StatementFacts,
    build_engine_input,
    derive_statement_facts,
    detect_next_income,
    due_day_label,
    resolve_due_date,
    to_commitment_inputs,
)
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
    # Epic 5 — the persisted-rows -> EngineInput bridge.
    "CommitmentRecord",
    "StatementFacts",
    "IncomeSignal",
    "DEFAULT_BUFFER",
    "build_engine_input",
    "derive_statement_facts",
    "detect_next_income",
    "to_commitment_inputs",
    "resolve_due_date",
    "due_day_label",
    # Story 5.6 — recurring-commitment auto-detection.
    "CommitmentCandidate",
    "detect_recurring_commitments",
]
