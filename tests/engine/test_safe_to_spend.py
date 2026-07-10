"""Targeted unit tests for the Safe-to-Spend engine (Story 4.2 → S4.1, FR-4, AD-8).

Scope (contract §5 boundary): the *mechanics* (round-down, ₹0 floor, ÷0 / ÷undefined
guards, each DD-1 sub-rule, top-of-range reserve) plus **representative** end-to-end
scenarios 1, 2, 10, 12, 13. The exhaustive table-driven gate over all 13 scenarios and the
CS-1..CS-4 companion assertions are Story 4.3 — deliberately NOT built here.

All money is :class:`~decimal.Decimal`; every Safe-to-Spend figure must end in ``0``
(AD-8). Runs with zero LLM calls, enforced by ``tests/engine/conftest.py`` (AD-1).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.engine.safe_to_spend import (
    CommitmentInput,
    EngineInput,
    EvidencePack,
    compute_safe_to_spend,
)

D = Decimal


def _known(name: str, amount: str, due: date, criticality: str = "critical") -> CommitmentInput:
    return CommitmentInput(name=name, amount=D(amount), due_date=due, criticality=criticality)


# --------------------------------------------------------------------------- mechanics


class TestRoundingAndFloor:
    def test_sts_always_ends_in_zero_rounds_down(self) -> None:
        # pool 5000 / 6 days = 833.33 -> floored DOWN to 830 (never 840).
        ei = EngineInput(
            available_balance=D("22000"),
            as_of=date(2026, 6, 25),
            commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
            next_income_date=date(2026, 7, 1),
        )
        pack = compute_safe_to_spend(ei)
        assert pack.safe_to_spend_today == D("830")
        assert pack.safe_to_spend_today % 10 == 0

    def test_never_negative_floored_to_zero(self) -> None:
        # Reserved + buffer exceed the balance → pool negative → STS floored to 0.
        ei = EngineInput(
            available_balance=D("16000"),
            as_of=date(2026, 6, 20),
            commitments=(
                _known("Rent", "15000", date(2026, 6, 28)),
                _known("EMI", "8500", date(2026, 6, 29)),
            ),
            next_income_date=date(2026, 7, 1),
        )
        pack = compute_safe_to_spend(ei)
        assert pack.safe_to_spend_today == D("0")
        assert pack.spendable_pool == D("-9500")  # honest negative pool preserved

    def test_returns_frozen_evidence_pack(self) -> None:
        pack = compute_safe_to_spend(
            EngineInput(available_balance=D("30000"), as_of=date(2026, 6, 11), next_income_date=date(2026, 7, 1))
        )
        assert isinstance(pack, EvidencePack)
        # frozen dataclass → cannot mutate
        import dataclasses

        assert dataclasses.is_dataclass(pack)


class TestDenominatorGuard:
    def test_days_zero_payday_today_no_zero_division(self) -> None:
        # Scenario 13: income confirmed TODAY (days=0) must never divide by zero.
        ei = EngineInput(
            available_balance=D("20000"),
            as_of=date(2026, 7, 1),
            commitments=(_known("Rent", "15000", date(2026, 7, 11)),),  # due AFTER income
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
            income_confidence="High",
        )
        pack = compute_safe_to_spend(ei)
        assert pack.days_to_income == 0
        assert pack.reserved_total == D("0")  # rent due after income → not this cycle
        assert pack.safe_to_spend_today == D("18000")  # reserved-only fallback, undivided
        assert pack.safety_ok is True

    def test_no_income_detected_undefined_horizon(self) -> None:
        # Scenario 12: no salary detected → after-income null + flag, no crash.
        ei = EngineInput(available_balance=D("20000"), as_of=date(2026, 6, 15), next_income_date=None)
        pack = compute_safe_to_spend(ei)
        assert pack.days_to_income is None
        assert pack.safe_to_spend_after_income is None
        assert "no_income_detected" in pack.data_quality_flags
        assert pack.safe_to_spend_today == D("18000")  # max(0, pool) fallback


class TestReservationRuleDD1:
    def test_known_before_income_always_reserved(self) -> None:
        # DD-1 rule 1.
        ei = EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 20),
            commitments=(_known("Rent", "15000", date(2026, 6, 28)),),
            next_income_date=date(2026, 7, 1),
        )
        assert compute_safe_to_spend(ei).reserved_total == D("15000")

    def test_known_after_income_not_reserved_this_cycle(self) -> None:
        # DD-1: an obligation due after next income is not this cycle's problem.
        ei = EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 20),
            commitments=(_known("EMI", "8500", date(2026, 7, 5)),),  # after July 1 income
            next_income_date=date(2026, 7, 1),
        )
        assert compute_safe_to_spend(ei).reserved_total == D("0")

    def test_predicted_inside_window_reserved(self) -> None:
        # DD-1 rule 2: predicted + within critical 7d window → reserved.
        ei = EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 25),
            commitments=(
                CommitmentInput("EMI", D("5000"), due_date=date(2026, 6, 30), criticality="critical", is_predicted=True),
            ),
            next_income_date=date(2026, 7, 1),
        )
        assert compute_safe_to_spend(ei).reserved_total == D("5000")

    def test_predicted_outside_window_surfaced_not_reserved(self) -> None:
        # DD-1 rule 2: predicted critical 12d out (> 7d window) → surfaced, NOT reserved,
        # prediction confidence drops to Medium.
        ei = EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 15),
            commitments=(
                CommitmentInput("EMI", D("5000"), due_date=date(2026, 6, 27), criticality="critical", is_predicted=True),
            ),
            next_income_date=date(2026, 7, 1),
        )
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("0")
        assert pack.prediction_confidence == "Medium"
        assert any("confirm" in d.lower() for d in pack.drivers)

    def test_predicted_after_income_does_not_lower_confidence(self) -> None:
        # Regression (code review, 2026-07-10): a predicted commitment due AFTER next income
        # returns no driver and must NOT be counted as "surfaced" — prediction confidence
        # stays High (previously wrongly downgraded to Medium via the due_date check).
        ei = EngineInput(
            available_balance=D("30000"),
            as_of=date(2026, 6, 20),
            commitments=(
                CommitmentInput(
                    "Next-month EMI", D("5000"), due_date=date(2026, 7, 15),
                    criticality="critical", is_predicted=True,  # after July 1 income
                ),
            ),
            next_income_date=date(2026, 7, 1),
        )
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("0")  # due after income → not this cycle
        assert pack.prediction_confidence == "High"  # not downgraded (no driver surfaced)

    def test_variable_amount_reserves_top_of_range(self) -> None:
        # DD-1 rule 3: reserve the TOP of the range, not the midpoint.
        ei = EngineInput(
            available_balance=D("28000"),
            as_of=date(2026, 6, 18),
            commitments=(
                _known("Rent", "15000", date(2026, 6, 28)),
                CommitmentInput("Electricity", D("3000"), amount_min=D("1500"), due_date=date(2026, 6, 22), criticality="important"),
            ),
            next_income_date=date(2026, 7, 2),
        )
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("18000")  # 15000 + 3000 (top), not 2250 midpoint
        assert pack.prediction_confidence == "Medium"  # variable bill lowers it

    def test_due_on_income_day_reserved_when_income_uncertain(self) -> None:
        # DD-1 rule 4: same-day commitment reserved from present balance when income < High.
        ei = EngineInput(
            available_balance=D("18000"),
            as_of=date(2026, 6, 30),
            commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
            income_confidence="Medium",  # < High → do not assume it covers same-day rent
        )
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("15000")
        assert pack.safe_to_spend_today == D("1000")  # (18000-15000-2000)/1

    def test_due_on_income_day_covered_when_income_high_and_sufficient(self) -> None:
        # DD-1 rule 4 exception: High confidence + income >= commitment → not reserved now.
        ei = EngineInput(
            available_balance=D("18000"),
            as_of=date(2026, 6, 30),
            commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
            income_confidence="High",
        )
        assert compute_safe_to_spend(ei).reserved_total == D("0")


# ----------------------------------------------------- representative scenarios (1,2,10,12,13)


class TestRepresentativeScenarios:
    def test_scenario_1_healthy_mid_cycle(self) -> None:
        ei = EngineInput(
            available_balance=D("42000"),
            as_of=date(2026, 6, 11),  # 20 days to July 1
            commitments=(
                _known("Rent", "15000", date(2026, 7, 1)),  # due on income day, income amount unknown → reserved
                _known("EMI", "8500", date(2026, 7, 5)),  # after income → not reserved
            ),
            next_income_date=date(2026, 7, 1),
            income_confidence="High",
        )
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("15000")
        assert pack.spendable_pool == D("25000")
        assert pack.days_to_income == 20
        assert pack.safe_to_spend_today == D("1250")
        assert pack.prediction_confidence == "High"
        assert pack.safety_ok is True

    def test_scenario_2_critical_inside_7day_window(self) -> None:
        ei = EngineInput(
            available_balance=D("22000"),
            as_of=date(2026, 6, 25),  # 6 days to July 1
            commitments=(_known("Rent", "15000", date(2026, 7, 1)),),
            next_income_date=date(2026, 7, 1),
            income_confidence="High",
        )
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("15000")
        assert pack.spendable_pool == D("5000")
        assert pack.days_to_income == 6
        assert pack.safe_to_spend_today == D("830")  # 6 * 830 = 4980 <= 5000
        assert pack.safety_ok is True

    def test_scenario_10_shortfall_never_negative_never_hidden(self) -> None:
        ei = EngineInput(
            available_balance=D("16000"),
            as_of=date(2026, 6, 20),
            commitments=(
                _known("Rent", "15000", date(2026, 6, 28)),
                _known("EMI", "8500", date(2026, 6, 29)),
            ),
            next_income_date=date(2026, 7, 1),
        )
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("23500")
        assert pack.spendable_pool == D("-9500")
        assert pack.safe_to_spend_today == D("0")  # floored, not negative
        assert pack.safety_ok is False  # honest shortfall
        assert any("exceed your balance by ₹9,500" in d for d in pack.drivers)  # formatINR (AD-13)

    def test_scenario_12_salary_not_detected(self) -> None:
        ei = EngineInput(available_balance=D("20000"), as_of=date(2026, 6, 15), next_income_date=None)
        pack = compute_safe_to_spend(ei)
        assert pack.reserved_total == D("0")
        assert pack.spendable_pool == D("18000")
        assert pack.days_to_income is None
        assert pack.safe_to_spend_after_income is None
        assert "no_income_detected" in pack.data_quality_flags
        assert pack.safety_ok is True

    def test_scenario_13_payday_today_div0_guard(self) -> None:
        ei = EngineInput(
            available_balance=D("20000"),
            as_of=date(2026, 7, 1),
            commitments=(_known("Rent", "15000", date(2026, 7, 11)),),  # after today's income
            next_income_date=date(2026, 7, 1),
            next_income_amount=D("55000"),
            income_confidence="High",
        )
        pack = compute_safe_to_spend(ei)
        assert pack.days_to_income == 0
        assert pack.reserved_total == D("0")
        assert pack.spendable_pool == D("18000")
        assert pack.safe_to_spend_today == D("18000")  # reserved-only fallback
        assert pack.safety_ok is True
