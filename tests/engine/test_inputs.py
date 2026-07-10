"""Tests for the persisted-rows -> EngineInput bridge (Epic 5, services/engine/inputs.py).

The engine itself is covered by the 13-scenario suite. What is asserted here is the
*derivation*: the ``due_day=31`` calendar clamp (FR-9.3), salary detection and its honest
absence (FR-4.8), the closing-balance rule, and the low-data flag (FR-5.4).

Like the rest of ``tests/engine/``, this module runs with zero LLM calls — ``conftest.py``'s
raising fixture makes an accidental one fail loudly.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from services.engine.inputs import (
    CommitmentRecord,
    build_engine_input,
    derive_statement_facts,
    detect_next_income,
    due_day_label,
    resolve_due_date,
    to_commitment_inputs,
)
from services.ingestion.schema import Transaction
from services.utils.enums import Direction


def txn(
    date_iso: str,
    description: str,
    amount: str,
    direction: Direction = Direction.debit,
    balance: str | None = None,
    row_id: int | None = None,
) -> Transaction:
    return Transaction(
        date=date_iso,
        description_raw=description,
        amount=Decimal(amount),
        direction=direction,
        balance_after=Decimal(balance) if balance is not None else None,
        id=row_id,
    )


# --------------------------------------------------------------------------------------
# resolve_due_date — the FR-9.3 "end of month" clamp
# --------------------------------------------------------------------------------------


class TestResolveDueDate:
    def test_due_day_31_clamps_to_last_day_of_a_30_day_month(self):
        # June has 30 days: "end of month" must not roll into July.
        assert resolve_due_date(31, date(2026, 6, 1)) == date(2026, 6, 30)

    def test_due_day_31_clamps_to_28_in_a_non_leap_february(self):
        assert resolve_due_date(31, date(2026, 2, 1)) == date(2026, 2, 28)

    def test_due_day_31_clamps_to_29_in_a_leap_february(self):
        assert resolve_due_date(31, date(2024, 2, 1)) == date(2024, 2, 29)

    def test_due_day_30_also_clamps_in_february(self):
        # The clamp is general, not a special case for 31.
        assert resolve_due_date(30, date(2026, 2, 1)) == date(2026, 2, 28)

    def test_due_day_on_as_of_is_this_cycle_not_next(self):
        # Due *today* is still due this cycle — it must stay reservable.
        assert resolve_due_date(15, date(2026, 6, 15)) == date(2026, 6, 15)

    def test_past_due_day_rolls_to_next_month(self):
        assert resolve_due_date(5, date(2026, 6, 15)) == date(2026, 7, 5)

    def test_past_due_day_in_december_rolls_into_january(self):
        assert resolve_due_date(5, date(2026, 12, 15)) == date(2027, 1, 5)

    def test_past_due_day_31_rolls_and_clamps(self):
        # From 30 Nov (30-day month, so this cycle's "31st" == the 30th, already past)
        # -> next cycle is December, which really has a 31st.
        assert resolve_due_date(31, date(2026, 12, 1)) == date(2026, 12, 31)

    @pytest.mark.parametrize("bad", [0, 32, -1, True, 1.5, "15", None])
    def test_invalid_due_day_raises_rather_than_guessing(self, bad):
        # A bad day must never become a date that silently under-reserves a commitment.
        with pytest.raises(ValueError):
            resolve_due_date(bad, date(2026, 6, 1))


class TestDueDayLabel:
    def test_31_renders_as_end_of_month(self):
        assert due_day_label(31) == "end of month"

    @pytest.mark.parametrize(
        "day,expected",
        [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (21, "21st"), (22, "22nd")],
    )
    def test_ordinal_suffixes(self, day, expected):
        assert due_day_label(day).startswith(expected)


# --------------------------------------------------------------------------------------
# derive_statement_facts — closing balance + freshness date
# --------------------------------------------------------------------------------------


class TestDeriveStatementFacts:
    def test_balance_is_from_the_chronologically_last_row(self):
        facts = derive_statement_facts([
            txn("2026-06-01", "UPI-SWIGGY", "450", balance="18000"),
            txn("2026-06-30", "SALARY ACME", "85000", Direction.credit, balance="88000"),
            txn("2026-06-03", "NEFT-RENT", "15000", balance="3000"),
        ])
        assert facts.available_balance == Decimal("88000")
        assert facts.statement_end_date == date(2026, 6, 30)
        assert facts.transaction_count == 3

    def test_same_day_rows_break_the_tie_on_insertion_order(self):
        facts = derive_statement_facts([
            txn("2026-06-30", "SECOND", "100", balance="900", row_id=2),
            txn("2026-06-30", "FIRST", "100", balance="1000", row_id=1),
        ])
        assert facts.available_balance == Decimal("900")

    def test_missing_balance_column_yields_zero_not_an_inferred_number(self):
        # Summing amounts would fabricate a balance. NFR-1: never a confidently wrong number.
        facts = derive_statement_facts([txn("2026-06-01", "UPI-SWIGGY", "450")])
        assert facts.available_balance == Decimal("0")

    def test_falls_back_to_the_last_row_that_actually_carries_a_balance(self):
        facts = derive_statement_facts([
            txn("2026-06-01", "HAS BALANCE", "450", balance="18000"),
            txn("2026-06-02", "NO BALANCE", "450"),
        ])
        assert facts.available_balance == Decimal("18000")

    def test_empty_statement_has_no_data(self):
        facts = derive_statement_facts([])
        assert facts.statement_end_date is None
        assert facts.has_data is False
        assert facts.available_balance == Decimal("0")


# --------------------------------------------------------------------------------------
# detect_next_income — FR-4.8, and its honest absence
# --------------------------------------------------------------------------------------


class TestDetectNextIncome:
    def test_single_salary_credit_projects_one_month_on_at_medium_confidence(self):
        signal = detect_next_income(
            [txn("2026-06-30", "SALARY ACME CORP", "85000", Direction.credit)],
            as_of=date(2026, 6, 30),
        )
        assert signal.next_income_date == date(2026, 7, 30)
        assert signal.next_income_amount == Decimal("85000")
        # One credit is not a cadence — must not claim High (DD-1 rule 4 depends on this).
        assert signal.confidence == "Medium"

    def test_two_monthly_salaries_give_high_confidence(self):
        signal = detect_next_income(
            [
                txn("2026-05-30", "SALARY ACME CORP", "85000", Direction.credit),
                txn("2026-06-30", "SALARY ACME CORP", "85000", Direction.credit),
            ],
            as_of=date(2026, 6, 30),
        )
        assert signal.confidence == "High"
        assert signal.next_income_date == date(2026, 7, 30)

    def test_two_credits_far_apart_are_not_a_monthly_cadence(self):
        signal = detect_next_income(
            [
                txn("2026-01-30", "SALARY ACME CORP", "85000", Direction.credit),
                txn("2026-06-30", "SALARY ACME CORP", "85000", Direction.credit),
            ],
            as_of=date(2026, 6, 30),
        )
        assert signal.confidence == "Medium"

    def test_no_salary_returns_an_explicit_absence_not_a_guess(self):
        # FR-4.8: the dashboard prompts "add one manually" — never a zero, never an error.
        signal = detect_next_income(
            [txn("2026-06-01", "UPI-SWIGGY", "450", balance="18000")],
            as_of=date(2026, 6, 1),
        )
        assert signal.next_income_date is None
        assert signal.next_income_amount is None

    def test_a_debit_mentioning_salary_is_not_income(self):
        signal = detect_next_income(
            [txn("2026-06-01", "SALARY ADVANCE REPAYMENT", "5000", Direction.debit)],
            as_of=date(2026, 6, 1),
        )
        assert signal.next_income_date is None

    def test_a_tiny_credit_mentioning_salary_is_not_income(self):
        # A ₹1 verification credit must not become a payday.
        signal = detect_next_income(
            [txn("2026-06-01", "SALARY TEST CREDIT", "1", Direction.credit)],
            as_of=date(2026, 6, 1),
        )
        assert signal.next_income_date is None

    def test_projection_skips_past_the_as_of_date(self):
        # Statement ends well after the last salary — the "next" payday must still be future.
        signal = detect_next_income(
            [txn("2026-03-31", "SALARY ACME CORP", "85000", Direction.credit)],
            as_of=date(2026, 6, 15),
        )
        assert signal.next_income_date is not None
        assert signal.next_income_date > date(2026, 6, 15)

    def test_a_31st_payday_clamps_in_a_30_day_month(self):
        signal = detect_next_income(
            [txn("2026-05-31", "SALARY ACME CORP", "85000", Direction.credit)],
            as_of=date(2026, 5, 31),
        )
        assert signal.next_income_date == date(2026, 6, 30)


# --------------------------------------------------------------------------------------
# to_commitment_inputs / build_engine_input
# --------------------------------------------------------------------------------------


class TestToCommitmentInputs:
    def test_due_day_becomes_a_concrete_date_and_fields_carry_through(self):
        inputs = to_commitment_inputs(
            [CommitmentRecord("HDFC EMI", Decimal("8500"), due_day=15, criticality="critical")],
            as_of=date(2026, 6, 1),
        )
        assert len(inputs) == 1
        assert inputs[0].name == "HDFC EMI"
        assert inputs[0].amount == Decimal("8500")
        assert inputs[0].due_date == date(2026, 6, 15)
        assert inputs[0].criticality == "critical"
        assert inputs[0].is_predicted is False

    def test_variable_bill_carries_its_low_end_for_surfacing(self):
        inputs = to_commitment_inputs(
            [
                CommitmentRecord(
                    "Electricity", Decimal("3000"), due_day=10, amount_min=Decimal("1800")
                )
            ],
            as_of=date(2026, 6, 1),
        )
        # The engine reserves `amount` (top of range); amount_min is only for display.
        assert inputs[0].amount == Decimal("3000")
        assert inputs[0].amount_min == Decimal("1800")


class TestBuildEngineInput:
    def test_as_of_is_the_statement_end_date_not_today(self):
        # Safe-to-Spend is only ever as fresh as the statement behind it (FR-4.7).
        engine_input = build_engine_input(
            [txn("2026-06-30", "SALARY ACME", "85000", Direction.credit, balance="88000")],
            [],
            today=date(2030, 1, 1),
        )
        assert engine_input.as_of == date(2026, 6, 30)

    def test_empty_statement_falls_back_to_today_and_flags_low_data(self):
        engine_input = build_engine_input([], [], today=date(2026, 7, 10))
        assert engine_input.as_of == date(2026, 7, 10)
        assert engine_input.low_data is True
        assert engine_input.available_balance == Decimal("0")

    def test_thin_statement_flags_low_data(self):
        engine_input = build_engine_input(
            [txn("2026-06-01", "UPI-SWIGGY", "450", balance="18000")], []
        )
        assert engine_input.low_data is True

    def test_a_full_statement_does_not_flag_low_data(self):
        rows = [
            txn(f"2026-06-{day:02d}", "UPI-SWIGGY", "450", balance="18000")
            for day in range(1, 13)
        ]
        assert build_engine_input(rows, []).low_data is False

    def test_end_to_end_produces_an_input_the_engine_accepts(self):
        from services.engine.safe_to_spend import compute_safe_to_spend

        rows = [
            txn("2026-06-01", "UPI-SWIGGY", "450", balance="30000"),
            txn("2026-06-30", "SALARY ACME CORP", "85000", Direction.credit, balance="25040"),
        ]
        engine_input = build_engine_input(
            rows,
            [CommitmentRecord("HDFC EMI", Decimal("8500"), due_day=15, criticality="critical")],
            buffer=Decimal("2000"),
        )
        evidence = compute_safe_to_spend(engine_input)

        # as_of is the statement end date (30 Jun). The salary landed that same day, so the
        # next one is projected to 30 Jul -> a 30-day horizon. The EMI's due_day=15 resolves
        # to 15 Jul, which is before payday, so it is fully reserved (DD-1 rule 1).
        # (25040 balance - 8500 reserved - 2000 buffer) / 30 days = 484.67, floored to ₹480.
        assert evidence.reserved_total == Decimal("8500")
        assert evidence.days_to_income == 30
        assert evidence.safe_to_spend_today == Decimal("480")
        assert evidence.safe_to_spend_today % 10 == 0  # never a ₹484 figure (FR-4.1)
        assert evidence.safety_ok is True

    def test_no_salary_flows_through_to_the_engines_reserved_only_fallback(self):
        # Scenario 12: no income detected -> after-income layer is None, flag is raised,
        # and Safe-to-Spend is still a real number (never a crash, never a divide-by-zero).
        from services.engine.safe_to_spend import compute_safe_to_spend

        engine_input = build_engine_input(
            [txn("2026-06-01", "UPI-SWIGGY", "450", balance="20000")], [], buffer=Decimal("2000")
        )
        evidence = compute_safe_to_spend(engine_input)

        assert evidence.days_to_income is None
        assert evidence.safe_to_spend_after_income is None
        assert "no_income_detected" in evidence.data_quality_flags
        assert evidence.safe_to_spend_today == Decimal("18000")
