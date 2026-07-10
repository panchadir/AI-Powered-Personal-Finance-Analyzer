"""Tests for the Commitments add/edit form rules (Story 5.5).

``validate_commitment`` is deliberately pure so the rules can be pinned without a Reflex app.
The important property is that a bad input is *refused* rather than coerced: a commitment
silently saved with the wrong amount or due-day would quietly under-reserve money the user is
counting on (NFR-1).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from finance_app.state.commitments_state import MAX_NAME_LENGTH, validate_commitment
from services.utils.enums import CRITICALITY_DEFAULT


class TestValidName:
    def test_a_valid_form_produces_no_errors_and_typed_values(self):
        errors, name, amount, due_day = validate_commitment("HDFC EMI", "8500", "15")
        assert errors == {}
        assert name == "HDFC EMI"
        assert amount == Decimal("8500")
        assert isinstance(amount, Decimal)  # AD-8: money is never float
        assert due_day == 15

    def test_name_is_trimmed(self):
        _errors, name, _amount, _due = validate_commitment("  HDFC EMI  ", "8500", "15")
        assert name == "HDFC EMI"

    def test_a_blank_name_is_refused(self):
        errors, *_ = validate_commitment("   ", "8500", "15")
        assert errors["name"] == "Please name this commitment"

    def test_an_over_long_name_is_refused(self):
        errors, *_ = validate_commitment("x" * (MAX_NAME_LENGTH + 1), "8500", "15")
        assert "name" in errors

    def test_a_name_at_the_limit_is_accepted(self):
        errors, *_ = validate_commitment("x" * MAX_NAME_LENGTH, "8500", "15")
        assert "name" not in errors


class TestAmount:
    @pytest.mark.parametrize("bad", ["0", "-100", "", "   ", "abc", "₹8500", "NaN", "Infinity"])
    def test_a_non_positive_or_unparseable_amount_is_refused(self, bad):
        errors, *_ = validate_commitment("HDFC EMI", bad, "15")
        assert errors["amount"] == "Amount must be greater than ₹0"

    def test_a_decimal_amount_is_preserved_exactly(self):
        # Decimal("8500.50") — not 8500.5 float, which cannot be represented exactly.
        _errors, _name, amount, _due = validate_commitment("Electricity", "8500.50", "15")
        assert amount == Decimal("8500.50")


class TestDueDay:
    @pytest.mark.parametrize("day", ["1", "15", "31"])
    def test_the_valid_range_is_accepted(self, day):
        errors, *_ = validate_commitment("HDFC EMI", "8500", day)
        assert "due_day" not in errors

    @pytest.mark.parametrize("bad", ["0", "32", "-1", "", "abc", "15.5"])
    def test_out_of_range_or_unparseable_days_are_refused(self, bad):
        errors, *_ = validate_commitment("HDFC EMI", "8500", bad)
        assert errors["due_day"] == "Due day must be between 1 and 31"

    def test_day_31_is_accepted_and_means_end_of_month(self):
        # FR-9.3: stored as 31, rendered as "end of month", clamped by the engine per month.
        errors, _name, _amount, due_day = validate_commitment("Rent", "20000", "31")
        assert errors == {}
        assert due_day == 31

    def test_a_fractional_day_is_refused_rather_than_truncated(self):
        # Truncating 15.5 to 15 would silently reserve on the wrong date.
        errors, *_ = validate_commitment("HDFC EMI", "8500", "15.5")
        assert "due_day" in errors


class TestNumberInputSendsFloats:
    """``<input type="number">`` can deliver its value as a float (15 arrives as ``15.0``).

    ``int("15.0")`` raises, so without normalization a valid due-day would be rejected with
    "Due day must be between 1 and 31" — a confusing error on correct input.
    """

    def test_a_whole_float_due_day_is_accepted(self):
        errors, _name, _amount, due_day = validate_commitment("HDFC EMI", "8500", 15.0)
        assert errors == {}
        assert due_day == 15

    def test_a_whole_float_amount_is_accepted_without_a_trailing_zero(self):
        errors, _name, amount, _due = validate_commitment("HDFC EMI", 8500.0, "15")
        assert errors == {}
        assert amount == Decimal("8500")

    def test_an_int_due_day_is_accepted(self):
        errors, _name, _amount, due_day = validate_commitment("HDFC EMI", "8500", 31)
        assert errors == {}
        assert due_day == 31

    def test_a_fractional_float_due_day_is_still_refused(self):
        errors, *_ = validate_commitment("HDFC EMI", "8500", 15.5)
        assert "due_day" in errors

    def test_none_values_are_refused_not_treated_as_empty_success(self):
        errors, *_ = validate_commitment(None, None, None)
        assert set(errors) == {"name", "amount", "due_day"}


class TestMultipleErrors:
    def test_every_bad_field_is_reported_at_once(self):
        errors, *_ = validate_commitment("", "-5", "99")
        assert set(errors) == {"name", "amount", "due_day"}


def test_the_default_criticality_is_important():
    """FR-4.3: a new commitment defaults to Important, not Critical."""
    assert CRITICALITY_DEFAULT.value == "important"
