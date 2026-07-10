"""Confidence Score engine (Story 4.4 → epic S4.3/S4.4, FR-5).

A **0–100 preparedness score** derived deterministically from the Safe-to-Spend evidence
pack. **LLM-free (AD-1).** Because it reads the same computed figures the Safe-to-Spend
engine produced, the score can never contradict Safe-to-Spend (CS-4).

Two guarantees baked into the type system:

* **Preparedness-only (FR-5.1 / CS-1):** the signature accepts *only* an
  :class:`~services.engine.safe_to_spend.EvidencePack` — there is no app-usage/engagement
  input, so engagement *cannot* move the score.
* **Event binding (FR-5.3 / AD-9 / CS-3):** every :class:`ScoreResult` carries a non-empty
  ``trigger_event``, ``explanation`` and ``suggested_action`` plus a ``delta`` — an
  *unexplained* score change is structurally impossible.

**Prediction Confidence is separate (FR-5.2):** the ``prediction_confidence`` string is
passed through from the evidence pack and is **never** blended into the 0–100 score
(preparedness) — the two are shown side by side.

**Score-events writeback is deferred (product decision 2026-07-10).** ``services/`` may not
import ``finance_app``'s ``ScoreEvent`` ``rx.Model`` (AD-2). The atomic ``score_events`` row
insert is therefore performed by the **caller** — the Epic 5 dashboard ``rx.State`` handler —
using this result's fields, in one transaction, with the UI score read back from the latest
row (AD-9). This module makes that write *possible and honest* by always emitting the four
bound fields; it does not perform the write.

Scope note: FR-5.1 also names spending-pace and savings-trend, which need transaction
history not present in the evidence pack. The MVP score uses commitment coverage, buffer
health, and spendable headroom; the historical factors are a documented future refinement.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from services.engine.safe_to_spend import EvidencePack
from services.utils.format import formatINR

# Score bands (contract §6 / FR-5). Shortfall sits strictly below every covered state.
_SHORTFALL_CEILING = Decimal("20")  # not safety_ok → [0, 20]
_COVERED_FLOOR = Decimal("40")  # safety_ok → [40, 95]
_COVERED_SPAN = Decimal("55")

_ZERO = Decimal("0")
_ONE = Decimal("1")


@dataclass(frozen=True)
class ScoreResult:
    """The Confidence Score plus its bound event fields (FR-5.3 / AD-9).

    ``trigger_event``, ``explanation`` and ``suggested_action`` mirror the
    ``finance_app.models.ScoreEvent`` column names exactly so the deferred writeback is a
    field-for-field copy — no re-mapping, no mis-spelling (``trigger_event`` not
    ``triggering_event``; ``suggested_action`` not ``action``).
    """

    score: int  # 0..100 preparedness
    delta: int  # score − (previous_score or 0)
    trigger_event: str
    explanation: str
    suggested_action: str
    prediction_confidence: str  # pass-through from the evidence pack — NOT the score


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


def _round_to_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def _preparedness_score(evidence: EvidencePack) -> int:
    """0–100 preparedness from the evidence pack (never engagement). Monotonic + clamped.

    Uses ``net = spendable_pool + reserved_total`` (= balance − buffer); the evidence pack
    carries no raw balance/buffer and none is needed.
    """
    if not evidence.safety_ok:
        # Shortfall: lowest band; a deeper gap scores lower.
        gap = -evidence.spendable_pool  # positive (incl. the dented buffer)
        denom = evidence.reserved_total if evidence.reserved_total > _ZERO else _ONE
        severity = _clamp(gap / denom, _ZERO, _ONE)
        return max(0, _round_to_int(_SHORTFALL_CEILING * (_ONE - severity)))

    net = evidence.spendable_pool + evidence.reserved_total  # balance − buffer
    headroom = _ZERO if net <= _ZERO else _clamp(evidence.spendable_pool / net, _ZERO, _ONE)
    score = _COVERED_FLOOR + _COVERED_SPAN * headroom
    return _round_to_int(_clamp(score, _ZERO, Decimal("100")))


def _explain(evidence: EvidencePack) -> tuple[str, str]:
    """Plain-language (explanation, suggested_action), traceable to real figures (FR-5.6)."""
    if not evidence.safety_ok:
        gap = formatINR(-evidence.spendable_pool)
        return (
            f"Your committed bills before payday exceed what's available by {gap}, "
            "so your preparedness is low right now.",
            f"Free up {gap} before payday — move a bill's date or add funds — "
            "and I'll lift this.",
        )
    if "no_income_detected" in evidence.data_quality_flags:
        return (
            "Your committed bills are covered from your current balance, but I couldn't "
            "detect your next salary yet.",
            "Add your expected salary so I can sharpen this and show your after-payday picture.",
        )
    return (
        f"Your committed bills are covered and you have {formatINR(evidence.spendable_pool)} of "
        "breathing room this cycle.",
        "Keep your emergency buffer intact — you're on track.",
    )


def compute_confidence_score(
    evidence: EvidencePack,
    *,
    previous_score: int | None = None,
    trigger_event: str = "recalculation",
) -> ScoreResult:
    """Compute the preparedness Confidence Score for one user (FR-5). Deterministic, LLM-free.

    ``previous_score`` (the last persisted score, or ``None`` on first calculation) drives
    ``delta``; ``trigger_event`` names what caused this change (e.g. ``"statement_upload"``,
    ``"commitment_added"``). Cold start computes immediately — there is no fake neutral-50
    default (FR-5.4); the low-data signal surfaces via ``prediction_confidence`` instead.
    """
    score = _preparedness_score(evidence)
    baseline = previous_score if previous_score is not None else 0
    explanation, suggested_action = _explain(evidence)
    return ScoreResult(
        score=score,
        delta=score - baseline,
        trigger_event=trigger_event,
        explanation=explanation,
        suggested_action=suggested_action,
        prediction_confidence=evidence.prediction_confidence,
    )
