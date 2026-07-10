"""Safe-to-Spend engine (Story 4.2 → epic S4.1, FR-4).

Deterministic, framework-agnostic Python. **The LLM never computes a number here
(AD-1).** All money arithmetic is :class:`~decimal.Decimal`, never ``float`` (AD-8 /
Agent-Misread Guard) — ``float`` is display-only and belongs to ``services/utils/format``,
not this layer.

Implements the LOCKED contract in
``_bmad-output/implementation-artifacts/4-1-engine-contract.md``:

* **Formula (§1, AD-8/FR-4.1):**
  ``safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days)``
  floored to ₹0, rounded **down** to the nearest ₹10 (never up).
* **Denominator guard (§1a, Seam):** ``days`` may be ``0`` (payday today) or ``None`` (no
  confirmed income). Guard *before* dividing → reserved-only fallback ``max(0, pool)``;
  never ``ZeroDivisionError`` / ``inf`` / ``nan``.
* **Reservation Rule DD-1 (§2, FR-4.2):** known-before-income always reserved; predicted
  reserved only inside its criticality window (critical 7d / important 5d / flexible 3d);
  variable-amount reserved at top-of-range; due-on-income-day reserved unless income is
  High-confidence and covers it.
* **Two-layer output (FR-4.5):** ``safe_to_spend_today`` and ``safe_to_spend_after_income``
  are separate; the after-income layer is ``None`` only when no income is detected.

Scope: this module returns the FR-4.12 evidence pack. The full 0–100 Confidence Score and
``score_events`` writeback are Story 4.4 (``confidence_score.py``); this module derives only
the ``prediction_confidence`` string the evidence pack carries.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from services.utils.format import formatDate, formatINR

# Criticality proximity windows in days (FR-4.3 / contract §2a).
# Enum values are exactly critical|important|flexible (services/utils/enums.py); the
# scenario file's prose "medium"/"low" map to important/flexible (contract §2a).
_WINDOW_DAYS: dict[str, int] = {"critical": 7, "important": 5, "flexible": 3}

# After-income layer spreads over an assumed next cycle length until the following income
# is known (contract §8 open item; refined when next-next income date is available).
_FOLLOWING_CYCLE_DAYS = 30

_ZERO = Decimal("0")


@dataclass(frozen=True)
class CommitmentInput:
    """A single obligation fed to the engine (contract §3).

    ``amount`` is the amount to reserve; for a variable-amount bill it is the **top** of
    the range (conservative under uncertainty, DD-1 rule 3) and ``amount_min`` carries the
    low end for surfacing. ``is_predicted`` marks a detected-from-history commitment whose
    date/amount are estimates (DD-1 rule 2).
    """

    name: str
    amount: Decimal
    amount_min: Decimal | None = None
    due_date: date | None = None
    criticality: str = "important"  # 'critical' | 'important' | 'flexible'
    is_predicted: bool = False


@dataclass(frozen=True)
class EngineInput:
    """Everything the Safe-to-Spend computation needs (contract §3). No DB/Reflex types."""

    available_balance: Decimal
    as_of: date
    buffer: Decimal = Decimal("2000")  # DD-2 default; per-user configurable
    commitments: tuple[CommitmentInput, ...] = ()
    next_income_date: date | None = None
    next_income_amount: Decimal | None = None
    income_confidence: str = "High"  # 'Low' | 'Medium' | 'High'
    low_data: bool = False  # cold-start / thin-history signal → prediction_confidence 'Low' (FR-5.4)


@dataclass(frozen=True)
class EvidencePack:
    """The FR-4.12 struct the engine returns; Story 4.3 asserts every field by name.

    ``safety_ok`` and ``buffer_intact`` are **two different questions**, deliberately not merged:

    * ``safety_ok`` — can every ring-fenced commitment actually be paid? This is the NFR-1
      promise ("no displayed number may cause a missed committed obligation").
    * ``buffer_intact`` — is the emergency buffer still whole? A balance can cover every bill
      while eating into the buffer. That is *not* a missed obligation, so ``safety_ok`` stays
      ``True``; but it is not "well prepared" either, so the Confidence Score bands it below a
      fully-covered cycle.

    Collapsing the two would make the shortfall driver ("your bills exceed your balance") lie in
    the buffer-dented case, where the bills are in fact covered.
    """

    reserved_total: Decimal
    spendable_pool: Decimal
    days_to_income: int | None
    safe_to_spend_today: Decimal
    safe_to_spend_after_income: Decimal | None
    prediction_confidence: str  # 'Low' | 'Medium' | 'High'
    drivers: tuple[str, ...] = field(default_factory=tuple)
    data_quality_flags: tuple[str, ...] = field(default_factory=tuple)
    safety_ok: bool = True
    buffer_intact: bool = True
    buffer: Decimal = Decimal("2000")  # echoed from the input so consumers can size the dent


def _floor_to_nearest_ten(amount: Decimal) -> Decimal:
    """Round **down** to the nearest ₹10 (AD-8). Never rounds up.

    Operates on :class:`~decimal.Decimal` so a drifted ``float`` can never push the result
    into the wrong ₹10 bucket. Callers pass a non-negative value (post ``max(0, …)``).
    """
    return Decimal(math.floor(amount / 10) * 10)


def _reserve_for_commitment(
    commitment: CommitmentInput,
    *,
    as_of: date,
    next_income_date: date | None,
    income_confidence: str,
    income_amount: Decimal | None,
) -> tuple[Decimal, str | None]:
    """Apply DD-1 to one commitment → ``(amount_to_reserve, driver_message)``.

    ``amount_to_reserve`` is ``0`` when the commitment is not ring-fenced this cycle. A
    ``driver_message`` is returned whenever the commitment is reserved *or* surfaced (a
    predicted one outside its window still gets a "confirm and I'll protect it" driver).
    """
    if commitment.due_date is None:
        return _ZERO, None

    # Due strictly after the next confirmed income → not this cycle (DD-1; e.g. next
    # month's EMI). With no confirmed income we cannot place it "after", so fall through.
    if next_income_date is not None and commitment.due_date > next_income_date:
        return _ZERO, None

    reserve = commitment.amount  # top-of-range already for variable bills (DD-1 rule 3)

    if not commitment.is_predicted:
        # Known commitment (confirmed amount + date), due on-or-before income.
        if next_income_date is not None and commitment.due_date == next_income_date:
            # DD-1 rule 4: due ON the income day.
            covered_by_income = (
                income_confidence == "High"
                and income_amount is not None
                and income_amount >= commitment.amount
            )
            if covered_by_income:
                return _ZERO, (
                    f"{commitment.name} due on payday — covered by your incoming salary"
                )
            return reserve, (
                f"{commitment.name} reserved (due on payday, held against your balance)"
            )
        # DD-1 rule 1: strictly before income → always fully reserved.
        return reserve, f"{commitment.name} reserved (due before payday)"

    # Predicted/uncertain commitment (DD-1 rule 2): reserve only inside its window.
    window = _WINDOW_DAYS.get(commitment.criticality, _WINDOW_DAYS["important"])
    days_until_due = (commitment.due_date - as_of).days
    if 0 <= days_until_due <= window:
        return reserve, f"{commitment.name} predicted within {window} days — reserved"
    # Outside the window: surface it (lowers prediction confidence) but do NOT subtract.
    return _ZERO, (
        f"{commitment.name} looks likely around {formatDate(commitment.due_date.isoformat())} — "
        "confirm it and I'll protect it"
    )


def _after_income_layer(
    engine_input: EngineInput, *, spendable_pool: Decimal
) -> Decimal | None:
    """The "after confirmed income" per-day figure (FR-4.5), or ``None`` when it is unknowable.

    Never merged with today's layer. **Spreads the income only — not the current balance.**

    The previous model spread ``available_balance + income − next-cycle-reserved − buffer`` over
    the cycle, but today's layer is *already* spending that same ``available_balance`` down over
    ``days_to_income``. Counting it in both layers inflated the after-payday figure and, worse,
    let it stay cheerful while today's layer was in shortfall — the card could read "you are
    ₹5,460 short today" directly above "₹3,600/day after payday". Spreading only the income is
    the conservative reading (FR-4.6): what is left of the balance on payday is whatever the
    user did not spend, and we must not promise it back to them.

    A shortfall *does* cross the boundary. If ``spendable_pool`` is negative the gap (commitments
    plus the dented buffer) has to be made good out of the incoming salary, so it is subtracted
    here. A surplus does not cross: it was already offered as today's spend.

    Returns ``None`` in two honest cases, distinguished by ``data_quality_flags``:

    * no income date at all (``no_income_detected``, scenario 12);
    * an income date but no income *amount* (``income_amount_unknown``) — we know *when* the
      salary lands, not *how much*. There is nothing to spread, and a ₹0/day figure would be a
      confidently wrong number. (Under the old model this case silently produced a figure
      derived entirely from the rolled-over balance — an "after your salary" number that never
      touched a salary.)
    """
    if engine_input.next_income_date is None or engine_input.next_income_amount is None:
        return None

    income = engine_input.next_income_amount
    reserved_next_cycle = sum(
        (
            c.amount
            for c in engine_input.commitments
            if c.due_date is not None
            and c.due_date > engine_input.next_income_date
            and not c.is_predicted
        ),
        start=_ZERO,
    )
    # min(0, pool): a shortfall carries forward; a surplus does not.
    carried_shortfall = min(_ZERO, spendable_pool)
    post_pool = income - reserved_next_cycle + carried_shortfall
    return _floor_to_nearest_ten(max(_ZERO, post_pool / _FOLLOWING_CYCLE_DAYS))


def _prediction_confidence(engine_input: EngineInput, *, surfaced_predictions: bool) -> str:
    """Data-completeness signal for the evidence pack (FR-5.2).

    Signals: an explicit ``low_data`` cold-start marker → Low (FR-5.4); otherwise a
    variable-amount bill or a surfaced (out-of-window) prediction → Medium. The fuller
    preparedness model and the 0–100 Confidence Score live in Story 4.4.
    """
    if engine_input.low_data:
        return "Low"
    has_variable = any(c.amount_min is not None for c in engine_input.commitments)
    if has_variable or surfaced_predictions:
        return "Medium"
    return "High"


def compute_safe_to_spend(engine_input: EngineInput) -> EvidencePack:
    """Compute the two-layer Safe-to-Spend evidence pack (FR-4.12) for one user.

    Deterministic and LLM-free (AD-1). See module docstring / contract §1–§4 for the rules.
    """
    buffer = engine_input.buffer
    drivers: list[str] = []
    reserved_total = _ZERO
    surfaced_predictions = False

    for commitment in engine_input.commitments:
        amount, driver = _reserve_for_commitment(
            commitment,
            as_of=engine_input.as_of,
            next_income_date=engine_input.next_income_date,
            income_confidence=engine_input.income_confidence,
            income_amount=engine_input.next_income_amount,
        )
        reserved_total += amount
        if driver is not None:
            drivers.append(driver)
        # A prediction lowers confidence only when it was *surfaced* (a driver was emitted for
        # an unreserved predicted commitment) — NOT merely because it is due after next income
        # (that path returns no driver and is simply next cycle's concern).
        if commitment.is_predicted and amount == _ZERO and driver is not None:
            surfaced_predictions = True

    spendable_pool = engine_input.available_balance - reserved_total - buffer

    # days_to_income: None (no confirmed income) or an int (0 == payday today).
    days_to_income: int | None
    if engine_input.next_income_date is None:
        days_to_income = None
    else:
        days_to_income = (engine_input.next_income_date - engine_input.as_of).days

    # Formula + denominator guard (contract §1 / §1a). max(0, …) floor is non-negotiable.
    positive_pool = max(_ZERO, spendable_pool)
    if days_to_income is None or days_to_income <= 0:
        # Reserved-only fallback: never divide by 0 or an undefined horizon.
        safe_to_spend_today = _floor_to_nearest_ten(positive_pool)
    else:
        safe_to_spend_today = _floor_to_nearest_ten(positive_pool / days_to_income)

    data_quality_flags: list[str] = []
    if engine_input.next_income_date is None:
        data_quality_flags.append("no_income_detected")
    elif engine_input.next_income_amount is None:
        # We know when the salary lands but not how much. The after-income layer is None rather
        # than a fabricated ₹0/day (see `_after_income_layer`).
        data_quality_flags.append("income_amount_unknown")

    # safety_ok: can the balance actually honour every ring-fenced commitment? The buffer is a
    # *separate* question (below) — folding it in here would make the shortfall copy lie.
    safety_ok = engine_input.available_balance >= reserved_total
    buffer_intact = spendable_pool >= _ZERO

    if not safety_ok:
        # Honest shortfall (FR-4.9 / UX-DR11). The gap named here is bills-minus-balance — the
        # amount actually missing to pay them. Reporting `-spendable_pool` would overstate it by
        # the buffer and make the sentence false: with a ₹16,000 balance and ₹23,500 of bills,
        # the bills exceed the balance by ₹7,500, not ₹9,500.
        bills_gap = reserved_total - engine_input.available_balance
        drivers.append(
            f"Committed bills before payday exceed your balance by {formatINR(bills_gap)} — "
            "here's what to do"
        )
    elif not buffer_intact:
        # Bills are covered; the emergency buffer is not whole. Not a missed obligation, so
        # `safety_ok` stays True — but it is not "well prepared" either (see confidence_score).
        dent = -spendable_pool
        drivers.append(
            f"Your bills are covered, but you'd dip {formatINR(dent)} into your "
            f"{formatINR(buffer)} emergency buffer"
        )

    return EvidencePack(
        reserved_total=reserved_total,
        spendable_pool=spendable_pool,
        days_to_income=days_to_income,
        safe_to_spend_today=safe_to_spend_today,
        safe_to_spend_after_income=_after_income_layer(
            engine_input, spendable_pool=spendable_pool
        ),
        prediction_confidence=_prediction_confidence(
            engine_input, surfaced_predictions=surfaced_predictions
        ),
        drivers=tuple(drivers),
        data_quality_flags=tuple(data_quality_flags),
        safety_ok=safety_ok,
        buffer_intact=buffer_intact,
        buffer=buffer,
    )
