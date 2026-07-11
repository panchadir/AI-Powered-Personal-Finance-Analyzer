"""Unit suite for the recurring-commitment detector (Story 5.6 / FR-9.1).

Covers the three AC scenarios — EMI-like pattern detected, irregular amounts not detected,
dismissed pattern not re-surfaced — plus the cadence and credit guards. Lives under
``tests/engine/`` so it inherits that package's autouse ``_forbid_anthropic`` fixture: any
Anthropic client construction raises, proving the detector makes zero LLM calls (AD-1).
"""
from __future__ import annotations

from decimal import Decimal

from services.engine import CommitmentCandidate, detect_recurring_commitments
from services.ingestion.schema import Transaction
from services.utils.enums import Criticality, Direction


def _txn(
    date: str,
    amount: str,
    *,
    merchant: str = "HDFC EMI",
    direction: Direction = Direction.debit,
) -> Transaction:
    return Transaction(
        date=date,
        description_raw=merchant,
        amount=Decimal(amount),
        direction=direction,
        merchant_normalized=merchant,
    )


# --------------------------------------------------------------------------------------
# EMI-like pattern detected
# --------------------------------------------------------------------------------------
def test_emi_like_pattern_is_detected() -> None:
    txns = [
        _txn("2026-04-05", "8500"),
        _txn("2026-05-05", "8500"),
        _txn("2026-06-05", "8500"),
    ]
    candidates = detect_recurring_commitments(txns)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.merchant == "HDFC EMI"
    assert candidate.amount == Decimal("8500")
    assert candidate.due_day == 5
    assert candidate.occurrences == 3
    assert candidate.criticality == Criticality.important.value  # default (FR-9.2)
    assert candidate.signature == "hdfc emi@5"


def test_amount_within_ten_percent_still_detected_and_reserves_median() -> None:
    # Slight variation (±10%) is still one commitment; the median is the amount to protect.
    txns = [
        _txn("2026-04-10", "2000", merchant="Airtel"),
        _txn("2026-05-10", "2100", merchant="Airtel"),
        _txn("2026-06-10", "1950", merchant="Airtel"),
    ]
    candidates = detect_recurring_commitments(txns)

    assert len(candidates) == 1
    assert candidates[0].amount == Decimal("2000")  # lower-median of 1950/2000/2100
    assert candidates[0].due_day == 10


def test_modal_due_day_absorbs_a_one_day_posting_drift() -> None:
    txns = [
        _txn("2026-04-05", "5000", merchant="Rent"),
        _txn("2026-05-05", "5000", merchant="Rent"),
        _txn("2026-06-06", "5000", merchant="Rent"),  # posted a day late once
    ]
    candidates = detect_recurring_commitments(txns)

    assert len(candidates) == 1
    assert candidates[0].due_day == 5  # the mode, not the outlier


# --------------------------------------------------------------------------------------
# Irregular amounts / cadence NOT detected
# --------------------------------------------------------------------------------------
def test_irregular_amounts_not_detected() -> None:
    # Same merchant, monthly cadence, but amounts swing far beyond ±10% → variable spend.
    txns = [
        _txn("2026-04-12", "1200", merchant="Swiggy"),
        _txn("2026-05-12", "3800", merchant="Swiggy"),
        _txn("2026-06-12", "600", merchant="Swiggy"),
    ]
    assert detect_recurring_commitments(txns) == []


def test_non_monthly_cadence_not_detected() -> None:
    # Near-constant amount but the gaps are weekly, not monthly.
    txns = [
        _txn("2026-06-01", "500", merchant="Gym drop-in"),
        _txn("2026-06-08", "500", merchant="Gym drop-in"),
        _txn("2026-06-15", "500", merchant="Gym drop-in"),
    ]
    assert detect_recurring_commitments(txns) == []


def test_single_occurrence_not_detected() -> None:
    assert detect_recurring_commitments([_txn("2026-06-05", "8500")]) == []


def test_credits_are_ignored() -> None:
    # A recurring salary credit must never be proposed as a commitment to ring-fence.
    txns = [
        _txn("2026-04-01", "50000", merchant="ACME SALARY", direction=Direction.credit),
        _txn("2026-05-01", "50000", merchant="ACME SALARY", direction=Direction.credit),
        _txn("2026-06-01", "50000", merchant="ACME SALARY", direction=Direction.credit),
    ]
    assert detect_recurring_commitments(txns) == []


# --------------------------------------------------------------------------------------
# Dismissed pattern not re-surfaced
# --------------------------------------------------------------------------------------
def test_dismissed_pattern_not_resurfaced() -> None:
    txns = [
        _txn("2026-04-05", "8500"),
        _txn("2026-05-05", "8500"),
        _txn("2026-06-05", "8500"),
    ]
    # The user already decided on this signature (confirmed or dismissed).
    candidates = detect_recurring_commitments(txns, exclude_signatures={"hdfc emi@5"})
    assert candidates == []


def test_only_the_excluded_signature_is_suppressed() -> None:
    txns = [
        _txn("2026-04-05", "8500", merchant="HDFC EMI"),
        _txn("2026-05-05", "8500", merchant="HDFC EMI"),
        _txn("2026-06-05", "8500", merchant="HDFC EMI"),
        _txn("2026-04-15", "499", merchant="Netflix"),
        _txn("2026-05-15", "499", merchant="Netflix"),
    ]
    candidates = detect_recurring_commitments(txns, exclude_signatures={"hdfc emi@5"})

    assert [c.merchant for c in candidates] == ["Netflix"]
    assert isinstance(candidates[0], CommitmentCandidate)
