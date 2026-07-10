"""The 13-scenario Safe-to-Spend gate (Story 4.3 → S4.2) — the MVP go/no-go.

Table-driven over the LOCKED contract (`4-1-engine-contract.md` §5), one parametrized case
per scenario, asserting every evidence-pack field the contract pins for that row. This is
the non-negotiable quality gate: **green, with zero LLM calls (AD-1)**, before the dashboard
is wired. The zero-LLM guarantee is enforced by the autouse `_forbid_anthropic` fixture in
`tests/engine/conftest.py`.

Boundary with Story 4.4: this suite asserts **CS-2** (prediction confidence, per scenario)
and **CS-4** (no contradiction, via STS/`safety_ok`). **CS-1** (0–100 Confidence Score
ordering) and **CS-3** (`score_events` binding) need `confidence_score.py` + the writeback
and are asserted in Story 4.4.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from services.engine.safe_to_spend import (
    CommitmentInput,
    EngineInput,
    EvidencePack,
    compute_safe_to_spend,
)

D = Decimal


def _known(name: str, amount: str, due: date, criticality: str = "critical") -> CommitmentInput:
    return CommitmentInput(name=name, amount=D(amount), due_date=due, criticality=criticality)


@dataclass(frozen=True)
class Case:
    """One locked scenario: inputs + the contract §5 expected outputs."""

    name: str
    ei: EngineInput
    reserved_total: str
    spendable_pool: str
    days_to_income: int | None
    safe_to_spend_today: str
    safety_ok: bool
    prediction_confidence: str | None = None  # asserted only where contract §5 pins it (S1–S7)


# --- The 13 locked scenarios (contract §5 / safe-to-spend-scenarios.md) -------------------
# Dates are chosen so `days_to_income` equals the contract's `days` column exactly.

CASES: tuple[Case, ...] = (
    # 1 — Healthy mid-cycle. Rent due on income day (income amount unknown → reserved);
    #     EMI due after income → not this cycle.
    Case(
        "s1_healthy_mid_cycle",
        EngineInput(
            available_balance=D("42000"),
            as_of=date(2026, 6, 11),
            commitments=(
                _known("Rent", "15000", date(2026, 7, 1)),
                _known("EMI", "8500", date(2026, 7, 5)),
            ),
            next_income_date=date(2026, 7, 1),
            income_confidence="High",
        ),
        reserved_total="15000", spendable_pool="25000", days_to_income=20,
        safe_to_spend_today="1250", safety_ok=True, prediction_confidence="High",
    ),
    # 2 — Critical inside 7-day window.
    Case(
        "s2_critical_inside_7d",
        EngineInput(
            available_balance=D("22000"),
            as_of=date(2026, 6, 25),
            commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
            next_income_date=date(2026, 7, 1),
            income_confidence="High",
        ),
        reserved_total="15000", spendable_pool="5000", days_to_income=6,
        safe_to_spend_today="830", safety_ok=True, prediction_confidence="High",
    ),
    # 3 — Low balance, day before payday. Today layer is the locked assertion (₹150);
    #     after-income asserted structurally (contract §8 open item).
    Case(
        "s3_day_before_payday",
        EngineInput(
            available_balance=D("2150"),
            as_of=date(2026, 6, 30),
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
            income_confidence="High",
        ),
        reserved_total="0", spendable_pool="150", days_to_income=1,
        safe_to_spend_today="150", safety_ok=True, prediction_confidence="High",
    ),
    # 4 — Variable bill reserved at TOP of range (₹3,000, not ₹2,250 midpoint).
    Case(
        "s4_variable_top_of_range",
        EngineInput(
            available_balance=D("28000"),
            as_of=date(2026, 6, 18),
            commitments=(
                _known("Rent", "15000", date(2026, 7, 1)),
                CommitmentInput(
                    "Electricity", D("3000"), amount_min=D("1500"),
                    due_date=date(2026, 6, 22), criticality="important", is_predicted=True,
                ),
            ),
            next_income_date=date(2026, 7, 2),
        ),
        reserved_total="18000", spendable_pool="8000", days_to_income=14,
        safe_to_spend_today="570", safety_ok=True, prediction_confidence="Medium",
    ),
    # 5 — Predicted, uncertain, OUTSIDE window → surfaced, not reserved.
    Case(
        "s5_predicted_outside_window",
        EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 15),
            commitments=(
                _known("Rent", "15000", date(2026, 7, 1)),
                CommitmentInput(
                    "EMI", D("5000"), due_date=date(2026, 6, 27),
                    criticality="critical", is_predicted=True,
                ),
            ),
            next_income_date=date(2026, 7, 2),
        ),
        reserved_total="15000", spendable_pool="13000", days_to_income=17,
        safe_to_spend_today="760", safety_ok=True, prediction_confidence="Medium",
    ),
    # 6 — Collision: three commitments all before payday, all fenced.
    Case(
        "s6_collision",
        EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 26),
            commitments=(
                _known("Rent", "15000", date(2026, 7, 1)),
                _known("EMI", "8500", date(2026, 6, 30)),
                _known("Broadband", "800", date(2026, 6, 29), criticality="important"),
            ),
            next_income_date=date(2026, 7, 1),
            income_confidence="High",
        ),
        reserved_total="24300", spendable_pool="3700", days_to_income=5,
        safe_to_spend_today="740", safety_ok=True, prediction_confidence="High",
    ),
    # 7 — Cold start: compute now, Low prediction confidence (no fake neutral-50).
    Case(
        "s7_cold_start_low_confidence",
        EngineInput(
            available_balance=D("25000"),
            as_of=date(2026, 6, 21),
            commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
            next_income_date=date(2026, 7, 1),
            low_data=True,
        ),
        reserved_total="15000", spendable_pool="8000", days_to_income=10,
        safe_to_spend_today="800", safety_ok=True, prediction_confidence="Low",
    ),
    # 8 — Due-date TODAY (off-by-one guard): a commitment due today is reserved, not ignored.
    Case(
        "s8_due_today",
        EngineInput(
            available_balance=D("40000"),
            as_of=date(2026, 6, 4),
            commitments=(_known("EMI", "8500", date(2026, 6, 4)),),
            next_income_date=date(2026, 7, 1),
        ),
        reserved_total="8500", spendable_pool="29500", days_to_income=27,
        safe_to_spend_today="1090", safety_ok=True,
    ),
    # 9 — Payday tomorrow + same-day commitment, income Medium → reserve from balance (÷1 guard).
    Case(
        "s9_payday_tomorrow_uncertain_income",
        EngineInput(
            available_balance=D("18000"),
            as_of=date(2026, 6, 30),
            commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
            income_confidence="Medium",
        ),
        reserved_total="15000", spendable_pool="1000", days_to_income=1,
        safe_to_spend_today="1000", safety_ok=True,
    ),
    # 10 — Shortfall: floored to ₹0, safety_ok False, honest shortfall surfaced.
    Case(
        "s10_shortfall",
        EngineInput(
            available_balance=D("16000"),
            as_of=date(2026, 6, 20),
            commitments=(
                _known("Rent", "15000", date(2026, 6, 28)),
                _known("EMI", "8500", date(2026, 6, 29)),
            ),
            next_income_date=date(2026, 7, 1),
        ),
        reserved_total="23500", spendable_pool="-9500", days_to_income=11,
        safe_to_spend_today="0", safety_ok=False,
    ),
    # 11 — Over-conservatism guard (FR-5.8): no commitments, positive balance → non-zero STS.
    Case(
        "s11_over_conservatism_guard",
        EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 11),
            next_income_date=date(2026, 7, 1),
        ),
        reserved_total="0", spendable_pool="28000", days_to_income=20,
        safe_to_spend_today="1400", safety_ok=True,
    ),
    # 12 — Salary not detected (FR-4.8): after-income null + flag, no crash. days_to_income None.
    Case(
        "s12_salary_not_detected",
        EngineInput(available_balance=D("20000"), as_of=date(2026, 6, 15), next_income_date=None),
        reserved_total="0", spendable_pool="18000", days_to_income=None,
        safe_to_spend_today="18000", safety_ok=True,
    ),
    # 13 — Payday is today (÷0 guard): days=0 never divides; reserved-only fallback.
    Case(
        "s13_payday_today",
        EngineInput(
            available_balance=D("20000"),
            as_of=date(2026, 7, 1),
            commitments=(_known("Rent", "15000", date(2026, 7, 11)),),
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
            income_confidence="High",
        ),
        reserved_total="0", spendable_pool="18000", days_to_income=0,
        safe_to_spend_today="18000", safety_ok=True,
    ),
)

_IDS = [c.name for c in CASES]


@pytest.fixture(params=CASES, ids=_IDS)
def scenario(request: pytest.FixtureRequest) -> tuple[Case, EvidencePack]:
    case: Case = request.param
    return case, compute_safe_to_spend(case.ei)


# --------------------------------------------------------------------- evidence-pack fields


def test_reserved_total(scenario: tuple[Case, EvidencePack]) -> None:
    case, pack = scenario
    assert pack.reserved_total == D(case.reserved_total)


def test_spendable_pool(scenario: tuple[Case, EvidencePack]) -> None:
    case, pack = scenario
    assert pack.spendable_pool == D(case.spendable_pool)


def test_days_to_income(scenario: tuple[Case, EvidencePack]) -> None:
    case, pack = scenario
    assert pack.days_to_income == case.days_to_income


def test_safe_to_spend_today(scenario: tuple[Case, EvidencePack]) -> None:
    case, pack = scenario
    assert pack.safe_to_spend_today == D(case.safe_to_spend_today)


def test_safety_ok(scenario: tuple[Case, EvidencePack]) -> None:
    case, pack = scenario
    assert pack.safety_ok is case.safety_ok


def test_prediction_confidence_where_locked(scenario: tuple[Case, EvidencePack]) -> None:
    case, pack = scenario
    if case.prediction_confidence is None:
        pytest.skip("prediction_confidence not pinned by contract §5 for this scenario")
    assert pack.prediction_confidence == case.prediction_confidence  # CS-2


# ------------------------------------------------------------------------ global invariants


def test_sts_non_negative_and_ends_in_zero(scenario: tuple[Case, EvidencePack]) -> None:
    _case, pack = scenario
    assert pack.safe_to_spend_today >= 0  # AD-8 floor
    assert pack.safe_to_spend_today % 10 == 0  # AD-8 round-DOWN-to-₹10


# ------------------------------------------------------------- targeted boundary assertions


def test_safety_ok_truth_table() -> None:
    """Contract §5: True for 1–9, 11, 12, 13; False for 10 only."""
    by_name = {c.name: compute_safe_to_spend(c.ei) for c in CASES}
    assert by_name["s10_shortfall"].safety_ok is False
    for name, pack in by_name.items():
        if name != "s10_shortfall":
            assert pack.safety_ok is True, f"{name} must be safety_ok=True"


def test_scenario_10_shortfall_driver_names_gap() -> None:
    """The driver names bills-minus-balance, not the pool gap.

    S10: ₹16,000 balance, ₹23,500 of bills, ₹2,000 buffer → ``spendable_pool == -9,500``. The
    bills exceed the balance by **₹7,500**; the extra ₹2,000 is the buffer. Saying "₹9,500"
    would make the sentence false — the buffer is a separate concern (``buffer_intact``), and
    ``-spendable_pool`` is the *action* target ("free up ₹9,500 to also restore your buffer"),
    which lives on the Confidence Score's `suggested_action`, not on this claim.
    """
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s10_shortfall"))
    assert any("exceed your balance by ₹7,500" in d for d in pack.drivers)  # formatINR (AD-13)
    assert not any("₹9,500" in d for d in pack.drivers)


def test_scenario_12_no_income_flag_and_null_after_layer() -> None:
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s12_salary_not_detected"))
    assert pack.safe_to_spend_after_income is None
    assert "no_income_detected" in pack.data_quality_flags


def test_scenario_13_payday_today_no_zero_division() -> None:
    # Reaching here without raising proves the ÷0 guard; assert the fallback figure too.
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s13_payday_today"))
    assert pack.days_to_income == 0
    assert pack.safe_to_spend_today == D("18000")


def test_scenario_3_today_and_after_income_both_exact() -> None:
    """Contract §8 CLOSED: both layers are now exact.

    Today is ₹150. After-income spreads the **income only** (₹55,000 / 30 = ₹1,833.33, floored
    to ₹1,830); the ₹2,150 balance is not added back, because today's layer is already spending
    it. The pool is positive, so no shortfall carries forward.

    (§8 previously left this structural because the old model added the balance in, making the
    figure a function of two layers at once. It is a single, derivable number now.)
    """
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s3_day_before_payday"))
    assert pack.safe_to_spend_today == D("150")
    assert pack.safe_to_spend_after_income == D("1830")
    assert pack.safe_to_spend_after_income % 10 == 0


def test_after_income_spreads_income_only_not_the_rolled_over_balance() -> None:
    """The double-count regression: the balance must not appear in both layers."""
    ei = EngineInput(
        available_balance=D("25040"),
        as_of=date(2026, 6, 30),
        next_income_date=date(2026, 7, 30),
        next_income_amount=D("85000"),
        income_confidence="High",
    )
    pack = compute_safe_to_spend(ei)
    # income only: 85,000 / 30 = 2,833.33 -> ₹2,830.
    # old model:  (25,040 + 85,000 − 2,000) / 30 = 3,601.33 -> ₹3,600  (balance counted twice)
    assert pack.safe_to_spend_after_income == D("2830")


def test_a_shortfall_carries_forward_into_the_after_income_layer() -> None:
    """A shortfall must not vanish at the payday boundary.

    The card previously read "you're short today" beside a cheerful after-payday figure,
    because the gap was never subtracted from the next cycle. The gap has to be made good out
    of the incoming salary, so it is.
    """
    ei = EngineInput(
        available_balance=D("25040"),
        as_of=date(2026, 6, 30),
        commitments=(
            _known("HDFC EMI", "8500", date(2026, 7, 15)),
            _known("Rent", "20000", date(2026, 6, 30)),
        ),
        next_income_date=date(2026, 7, 30),
        next_income_amount=D("85000"),
        income_confidence="High",
    )
    pack = compute_safe_to_spend(ei)
    assert pack.safe_to_spend_today == D("0")
    assert pack.safety_ok is False
    assert pack.spendable_pool == D("-5460")
    # (85,000 − 5,460 carried shortfall) / 30 = 2,651.33 -> ₹2,650. Strictly less than the
    # ₹2,830 the same balance/income yields with no shortfall.
    assert pack.safe_to_spend_after_income == D("2650")
    assert pack.safe_to_spend_after_income < D("2830")


def test_a_surplus_does_not_carry_forward() -> None:
    """Only shortfalls cross the boundary; today's unspent surplus was already offered today."""
    base = dict(
        available_balance=D("25040"),
        as_of=date(2026, 6, 30),
        next_income_date=date(2026, 7, 30),
        next_income_amount=D("85000"),
        income_confidence="High",
    )
    lean = compute_safe_to_spend(EngineInput(**base))
    rich = compute_safe_to_spend(EngineInput(**{**base, "available_balance": D("90000")}))
    # A much larger balance raises *today*, and leaves the after-income layer untouched.
    assert rich.safe_to_spend_today > lean.safe_to_spend_today
    assert rich.safe_to_spend_after_income == lean.safe_to_spend_after_income == D("2830")


def test_known_income_date_without_an_amount_yields_no_after_layer() -> None:
    """We know *when* the salary lands, not *how much*. ₹0/day would be a confidently wrong number.

    Under the old model this case still produced a figure — derived entirely from the rolled-over
    balance. An "after your salary" number that never touched a salary violates NFR-1.
    """
    ei = EngineInput(
        available_balance=D("42000"),
        as_of=date(2026, 6, 11),
        commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
        next_income_date=date(2026, 7, 1),  # no next_income_amount
        income_confidence="High",
    )
    pack = compute_safe_to_spend(ei)
    assert pack.safe_to_spend_after_income is None
    assert "income_amount_unknown" in pack.data_quality_flags
    assert "no_income_detected" not in pack.data_quality_flags  # a salary *was* detected
    assert pack.safe_to_spend_today > 0  # today's layer is unaffected


class TestBufferHealthIsSeparateFromCommitmentSafety:
    """`safety_ok` answers "can the bills be paid?"; `buffer_intact` answers "is the buffer whole?"."""

    def _bills_covered_buffer_dented(self) -> EngineInput:
        # ₹16,000 balance, ₹15,000 of bills, ₹2,000 buffer -> bills payable, buffer down ₹1,000.
        return EngineInput(
            available_balance=D("16000"),
            as_of=date(2026, 6, 20),
            commitments=(_known("Rent", "15000", date(2026, 6, 28)),),
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
        )

    def test_bills_covered_but_buffer_dented_keeps_safety_ok_true(self) -> None:
        pack = compute_safe_to_spend(self._bills_covered_buffer_dented())
        assert pack.safety_ok is True  # no obligation is missed
        assert pack.buffer_intact is False  # but the buffer is being eaten
        assert pack.safe_to_spend_today == D("0")

    def test_the_driver_does_not_claim_the_bills_exceed_the_balance(self) -> None:
        # They don't: ₹15,000 of bills against a ₹16,000 balance.
        pack = compute_safe_to_spend(self._bills_covered_buffer_dented())
        assert not any("exceed your balance" in d for d in pack.drivers)
        assert any("emergency buffer" in d for d in pack.drivers)

    def test_a_zero_safe_to_spend_never_reads_as_on_track(self) -> None:
        """CS-4, at the boundary the old model missed.

        Previously this scored exactly 40 -> the "On track" label, beside a ₹0 Safe-to-Spend.
        The buffer band puts it strictly below the covered floor.
        """
        from services.engine.confidence_score import compute_confidence_score

        pack = compute_safe_to_spend(self._bills_covered_buffer_dented())
        score = compute_confidence_score(pack).score
        assert pack.safe_to_spend_today == D("0")
        assert score < 40  # below the "On track" floor
        assert score >= 20  # but above the cannot-pay-your-bills band

    def test_a_deeper_dent_scores_lower_than_a_shallow_one(self) -> None:
        from services.engine.confidence_score import compute_confidence_score

        shallow = compute_safe_to_spend(self._bills_covered_buffer_dented())  # dent ₹1,000
        deep = compute_safe_to_spend(
            EngineInput(
                available_balance=D("15100"),  # dent ₹1,900 of the ₹2,000 buffer
                as_of=date(2026, 6, 20),
                commitments=(_known("Rent", "15000", date(2026, 6, 28)),),
                next_income_date=date(2026, 7, 1),
                next_income_amount=D("55000"),
            )
        )
        assert deep.safety_ok is True and deep.buffer_intact is False
        assert compute_confidence_score(deep).score < compute_confidence_score(shallow).score

    def test_a_true_shortfall_still_scores_below_every_buffer_dent(self) -> None:
        """The three bands stay strictly ordered: shortfall < buffer-dented < covered."""
        from services.engine.confidence_score import compute_confidence_score

        shortfall = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s10_shortfall"))
        dented = compute_safe_to_spend(self._bills_covered_buffer_dented())
        healthy = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s11_over_conservatism_guard"))

        assert compute_confidence_score(shortfall).score <= 20
        assert 20 <= compute_confidence_score(dented).score < 40
        assert compute_confidence_score(healthy).score >= 40

    def test_a_healthy_cycle_reports_the_buffer_intact(self) -> None:
        pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s11_over_conservatism_guard"))
        assert pack.safety_ok is True
        assert pack.buffer_intact is True
        assert not any("emergency buffer" in d for d in pack.drivers)


def test_cs4_no_contradiction_shortfall() -> None:
    """CS-4: S10 tells one story — STS ₹0 AND safety_ok False (never 'well-prepared' at ₹0)."""
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s10_shortfall"))
    assert pack.safe_to_spend_today == D("0")
    assert pack.safety_ok is False
    # CS-1 (0–100 score ordering) and CS-3 (score_events binding) are asserted in Story 4.4.
