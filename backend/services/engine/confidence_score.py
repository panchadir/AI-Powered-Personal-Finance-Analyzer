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

# Score bands (contract §6 / FR-5). Three strictly-ordered states, worst first:
#   not safety_ok            → [0, 20]   bills cannot be paid
#   safety_ok, buffer dented → [20, 39]  bills covered, emergency buffer being eaten
#   safety_ok, buffer intact → [40, 95]  fully covered
# The middle band exists so a ₹0 Safe-to-Spend can never present as "On track" (the ≥40 label).
_SHORTFALL_CEILING = Decimal("20")  # not safety_ok → [0, 20]
_BUFFER_FLOOR = Decimal("20")  # buffer dented → [20, 39]
_BUFFER_CEILING = Decimal("39")  # strictly below _COVERED_FLOOR — never reads "On track"
_COVERED_FLOOR = Decimal("40")  # safety_ok + buffer intact → [40, 95]
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

    Uses ``net = spendable_pool + reserved_total`` (= balance − buffer).
    """
    if not evidence.safety_ok:
        # Shortfall: lowest band; a deeper gap scores lower.
        gap = -evidence.spendable_pool  # positive (incl. the dented buffer)
        denom = evidence.reserved_total if evidence.reserved_total > _ZERO else _ONE
        severity = _clamp(gap / denom, _ZERO, _ONE)
        return max(0, _round_to_int(_SHORTFALL_CEILING * (_ONE - severity)))

    if not evidence.buffer_intact:
        # Bills are payable, but the emergency buffer is being eaten. Strictly below the covered
        # floor: this is precisely the state where Safe-to-Spend is ₹0 while `safety_ok` is
        # True, and calling that "On track" would be the CS-4 contradiction in a friendlier hat.
        # A deeper dent scores lower; a fully-consumed buffer bottoms out at _BUFFER_FLOOR.
        dent = -evidence.spendable_pool  # in (0, buffer] while safety_ok holds
        denom = evidence.buffer if evidence.buffer > _ZERO else _ONE
        severity = _clamp(dent / denom, _ZERO, _ONE)
        span = _BUFFER_CEILING - _BUFFER_FLOOR
        return _round_to_int(_BUFFER_CEILING - span * severity)

    net = evidence.spendable_pool + evidence.reserved_total  # balance − buffer
    headroom = _ZERO if net <= _ZERO else _clamp(evidence.spendable_pool / net, _ZERO, _ONE)
    score = _COVERED_FLOOR + _COVERED_SPAN * headroom
    return _round_to_int(_clamp(score, _ZERO, Decimal("100")))


def _explain(evidence: EvidencePack) -> tuple[str, str]:
    """Plain-language (explanation, suggested_action), traceable to real figures (FR-5.6)."""
    if not evidence.safety_ok:
        # `-spendable_pool` is the amount needed to cover the bills *and* restore the buffer,
        # which is the right target for the action. It is NOT "how much the bills exceed your
        # balance" — that claim belongs to the engine's driver, which names the smaller
        # bills-minus-balance figure. Keep the two distinct.
        to_free = formatINR(-evidence.spendable_pool)
        return (
            f"Your committed bills before payday exceed what's available by {to_free}, "
            "so your preparedness is low right now.",
            f"Free up {to_free} before payday — move a bill's date or add funds — "
            "and I'll lift this.",
        )
    if not evidence.buffer_intact:
        dent = formatINR(-evidence.spendable_pool)
        return (
            f"Your committed bills are covered, but paying them dips {dent} into your "
            f"{formatINR(evidence.buffer)} emergency buffer.",
            f"Setting aside {dent} before payday would leave your buffer whole.",
        )
    if "no_income_detected" in evidence.data_quality_flags:
        return (
            "Your committed bills are covered from your current balance, but I couldn't "
            "detect your next salary yet.",
            "Add your expected salary so I can sharpen this and show your after-payday picture.",
        )
    if "income_amount_unknown" in evidence.data_quality_flags:
        return (
            "Your committed bills are covered, and I can see when your next income lands — "
            "but not how much it will be.",
            "Add your expected salary amount so I can show your after-payday picture.",
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
