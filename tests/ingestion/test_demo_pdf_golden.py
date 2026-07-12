"""Story 8.5 AC1 — Golden-file regression for the demo bank statement.

The demo PDF is an ICICI Bank statement (June 2026, 65 transactions).
This test locks the known transaction count in as a regression guard so any future
parser change or dependency bump that breaks the ICICI text-extraction path fails
loudly here rather than at demo time.

Threshold: ≥ 90% of 65 known rows = 59.  The parser currently returns all 65 — the
≥90% floor gives tolerance for minor formatting differences across library versions.
"""
from __future__ import annotations

import math
from decimal import Decimal
from pathlib import Path

import pytest

from services.ingestion import PDFParser
from services.utils.enums import Direction

_PDF = Path(__file__).parent.parent.parent / "data" / "OpTransactionHistory10-07-2026_3625 1.pdf"
_KNOWN_COUNT = 65
_MIN_COUNT = math.ceil(_KNOWN_COUNT * 0.9)  # 59


@pytest.fixture(scope="module")
def parsed_transactions():
    """Parse the demo PDF once for all golden-file assertions."""
    assert _PDF.exists(), f"Demo PDF not found at {_PDF}. Run 'git lfs pull' if on a fresh clone."
    return PDFParser().parse(_PDF)


def test_demo_pdf_parses_at_least_90_percent_of_known_count(parsed_transactions):
    """Core regression guard: parser must extract ≥90% of the 65 known transactions."""
    count = len(parsed_transactions)
    assert count >= _MIN_COUNT, (
        f"Demo PDF regression: expected ≥{_MIN_COUNT} transactions (90% of {_KNOWN_COUNT} known), "
        f"got {count}. A parser change or library bump has degraded ICICI statement parsing."
    )


def test_demo_pdf_all_rows_have_valid_date(parsed_transactions):
    """Every parsed row must have a non-empty ISO date string."""
    bad = [t for t in parsed_transactions if not t.date or len(t.date) != 10]
    assert not bad, f"{len(bad)} rows have invalid/missing date: {bad[:3]}"


def test_demo_pdf_all_rows_have_positive_amount(parsed_transactions):
    """Every parsed row must have amount > 0 (Decimal, per AD-8)."""
    bad = [t for t in parsed_transactions if not isinstance(t.amount, Decimal) or t.amount <= 0]
    assert not bad, f"{len(bad)} rows have non-positive or non-Decimal amount: {bad[:3]}"


def test_demo_pdf_all_rows_have_valid_direction(parsed_transactions):
    """Every parsed row must have direction = credit or debit (canonical enum, AD-6)."""
    valid = {Direction.credit, Direction.debit}
    bad = [t for t in parsed_transactions if t.direction not in valid]
    assert not bad, f"{len(bad)} rows have invalid direction: {bad[:3]}"


def test_demo_pdf_has_both_credits_and_debits(parsed_transactions):
    """The statement contains both salary credits and expense debits."""
    directions = {t.direction for t in parsed_transactions}
    assert Direction.credit in directions, "No credit transactions found — income row missing."
    assert Direction.debit in directions, "No debit transactions found — expense rows missing."
