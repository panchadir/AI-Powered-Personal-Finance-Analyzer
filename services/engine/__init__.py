"""Deterministic financial engine: safe_to_spend, confidence_score, commitments.

No LLM touches these numbers (AD-1). All arithmetic uses ``Decimal`` (or integer
paise), never ``float``. ``pytest services/engine/`` is the non-negotiable MVP quality
gate and must run with zero LLM calls. Populated in Epic 4.
"""
