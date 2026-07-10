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
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s10_shortfall"))
    assert any("exceed your balance by ₹9,500" in d for d in pack.drivers)  # formatINR (AD-13)


def test_scenario_12_no_income_flag_and_null_after_layer() -> None:
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s12_salary_not_detected"))
    assert pack.safe_to_spend_after_income is None
    assert "no_income_detected" in pack.data_quality_flags


def test_scenario_13_payday_today_no_zero_division() -> None:
    # Reaching here without raising proves the ÷0 guard; assert the fallback figure too.
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s13_payday_today"))
    assert pack.days_to_income == 0
    assert pack.safe_to_spend_today == D("18000")


def test_scenario_3_today_exact_after_income_structural() -> None:
    """Contract §8: today layer is locked (₹150); after-income asserted structurally
    (engine returns ₹1,830 from the stated inputs, not the file's flagged-approximate ~990)."""
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s3_day_before_payday"))
    assert pack.safe_to_spend_today == D("150")
    assert pack.safe_to_spend_after_income is not None
    assert pack.safe_to_spend_after_income > 0
    assert pack.safe_to_spend_after_income % 10 == 0


def test_cs4_no_contradiction_shortfall() -> None:
    """CS-4: S10 tells one story — STS ₹0 AND safety_ok False (never 'well-prepared' at ₹0)."""
    pack = compute_safe_to_spend(next(c.ei for c in CASES if c.name == "s10_shortfall"))
    assert pack.safe_to_spend_today == D("0")
    assert pack.safety_ok is False
    # CS-1 (0–100 score ordering) and CS-3 (score_events binding) are asserted in Story 4.4.
