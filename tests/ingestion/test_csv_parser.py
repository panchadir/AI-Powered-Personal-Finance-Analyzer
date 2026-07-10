"""Story 2.2 acceptance: CSV parser for Indian bank formats (FR-2.1).

Golden-file tests, one fixture per supported bank shape (HDFC, SBI), asserting:

* dates ISO-normalized, amounts ``Decimal`` (never float), direction the ``Direction`` enum;
* Indian-grouped amounts (``85,000.00``) and split debit/credit columns handled;
* the canonical dedup key is stable, so a re-upload of the same file yields zero new rows;
* an unrecognised column layout is refused with a typed :class:`UnsupportedFormatError`
  rather than producing garbled rows (AD-12).
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from services.ingestion import (
    CSVParser,
    IngestionError,
    StatementParser,
    Transaction,
    UnsupportedFormatError,
    dedup_key,
    deduplicate,
    normalize_description,
)
from services.utils.enums import Direction

FIXTURES = Path(__file__).parent / "fixtures"


def test_csv_parser_satisfies_protocol() -> None:
    parser: StatementParser = CSVParser()
    assert isinstance(parser, StatementParser)


def test_hdfc_golden_file() -> None:
    rows = CSVParser().parse(FIXTURES / "hdfc_sample.csv")
    assert len(rows) == 4
    # Every row is canonical: Decimal money, Direction enum, ISO date.
    assert all(isinstance(t, Transaction) for t in rows)
    assert all(isinstance(t.amount, Decimal) for t in rows)
    assert all(isinstance(t.direction, Direction) for t in rows)
    assert all(len(t.date) == 10 and t.date[4] == "-" for t in rows)

    swiggy, rent, salary, atm = rows
    assert (swiggy.date, swiggy.amount, swiggy.direction) == (
        "2026-06-01",
        Decimal("450.00"),
        Direction.debit,
    )
    assert swiggy.balance_after == Decimal("18000.00")
    # Indian-grouped amount parsed correctly.
    assert rent.amount == Decimal("15000.00") and rent.direction is Direction.debit
    # Credit row → Direction.credit, positive amount.
    assert salary.amount == Decimal("85000.00") and salary.direction is Direction.credit
    assert salary.balance_after == Decimal("88000.00")
    assert atm.date == "2026-07-02" and atm.amount == Decimal("2000.00")


def test_sbi_golden_file() -> None:
    rows = CSVParser().parse(FIXTURES / "sbi_sample.csv")
    assert len(rows) == 3
    zomato, emi, salary = rows
    # SBI uses '01-Jun-2026' dates — normalized to ISO.
    assert zomato.date == "2026-06-01"
    assert zomato.amount == Decimal("320.50") and zomato.direction is Direction.debit
    assert emi.amount == Decimal("8500.00") and emi.direction is Direction.debit
    assert salary.date == "2026-06-30"
    assert salary.amount == Decimal("75000.00") and salary.direction is Direction.credit
    assert salary.balance_after == Decimal("78500.00")


def test_no_float_anywhere_in_parsed_output() -> None:
    """AD-8: money fields must be Decimal, never float — the schema guard enforces it."""
    for name in ("hdfc_sample.csv", "sbi_sample.csv"):
        for txn in CSVParser().parse(FIXTURES / name):
            assert isinstance(txn.amount, Decimal)
            assert txn.balance_after is None or isinstance(txn.balance_after, Decimal)


def test_reupload_same_file_produces_zero_duplicates() -> None:
    """Re-uploading the exact same file dedupes back to the original row count (FR-2.1)."""
    rows = CSVParser().parse(FIXTURES / "hdfc_sample.csv")
    reuploaded = rows + CSVParser().parse(FIXTURES / "hdfc_sample.csv")
    assert len(reuploaded) == 2 * len(rows)
    assert len(deduplicate(reuploaded)) == len(rows)


def test_dedup_key_collapses_whitespace_variants() -> None:
    """Description whitespace differences don't create distinct dedup identities."""
    base = CSVParser().parse(FIXTURES / "hdfc_sample.csv")[3]  # 'ATM WITHDRAWAL   HDFC'
    assert normalize_description(base.description_raw) == "ATM WITHDRAWAL HDFC"
    spaced = base.with_fields(description_raw="ATM   WITHDRAWAL     HDFC")
    assert dedup_key(base) == dedup_key(spaced)


def test_zero_padded_unused_column_parses() -> None:
    """A bank that pads the non-applicable split column with 0.00 (not blank) still parses.

    Regression for the code-review F1 finding: `0.00` in the unused debit/credit column
    must be read as "not this side", not as a competing amount that trips the
    both-present AMBIGUOUS_DIRECTION guard and aborts the whole file.
    """
    rows = CSVParser().parse(FIXTURES / "hdfc_zero_padded.csv")
    assert len(rows) == 2
    swiggy, salary = rows
    assert swiggy.direction is Direction.debit and swiggy.amount == Decimal("450.00")
    assert salary.direction is Direction.credit and salary.amount == Decimal("85000.00")
    # A ₹0 balance would still be preserved (the fix is scoped to direction, not balance).
    assert salary.balance_after == Decimal("88000.00")


def test_unsupported_layout_is_refused() -> None:
    """An unknown column shape raises a typed error, not garbled rows (AD-12)."""
    bad = FIXTURES / "unknown_bank.csv"
    bad.write_text("Foo,Bar,Baz\n1,2,3\n", encoding="utf-8")
    try:
        with pytest.raises(UnsupportedFormatError):
            CSVParser().parse(bad)
    finally:
        bad.unlink()


def test_non_utf8_cp1252_csv_parses(tmp_path) -> None:
    """A cp1252-encoded bank CSV (non-UTF-8) parses instead of crashing.

    Some Indian banks export Windows-1252, not UTF-8; the encoding fallback reads it rather
    than raising UnicodeDecodeError. Uses a curly apostrophe (0x92 in cp1252) that is invalid
    UTF-8, so a utf-8-only reader would fail on this exact file.
    """
    text = (
        "Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
        "01/06/2026,CAFÉ COFFEE DAY’S,R1,01/06/2026,450.00,,18000.00\n"
    )
    p = tmp_path / "cp1252.csv"
    p.write_bytes(text.encode("cp1252"))
    rows = CSVParser().parse(p)
    assert len(rows) == 1
    assert rows[0].amount == Decimal("450.00") and rows[0].direction is Direction.debit


def test_footer_summary_rows_are_skipped_not_failed() -> None:
    """Trailing Opening/Closing Balance rows (no date, no amount) are skipped, not fatal.

    Resolves the deferred F2 finding. Such rows are structural, not transactions, so
    skipping them drops no transaction — the visible count stays accurate and AD-12's
    'never show fewer rows than parsed' caveat is not triggered.
    """
    rows = CSVParser().parse(FIXTURES / "sbi_with_footer.csv")
    assert len(rows) == 2  # the 2 real transactions; 2 footer rows skipped
    assert rows[0].direction is Direction.debit and rows[0].amount == Decimal("320.50")
    assert rows[1].direction is Direction.credit and rows[1].amount == Decimal("75000.00")


def _write_tmp(tmp_path, name: str, text: str) -> "Path":
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_valid_date_but_no_amount_still_refused(tmp_path) -> None:
    """A row that has a real date but no debit/credit is NOT silently dropped (AD-12)."""
    header = "Txn Date,Value Date,Description,Ref No./Cheque No.,Debit,Credit,Balance\n"
    csv_text = header + "01-Jun-2026,01-Jun-2026,MYSTERY ROW,R1,,,12000.00\n"
    with pytest.raises(IngestionError) as exc:
        CSVParser().parse(_write_tmp(tmp_path, "no_amount.csv", csv_text))
    assert exc.value.code == "MISSING_AMOUNT"


def test_amount_but_no_valid_date_still_refused(tmp_path) -> None:
    """A row with an amount but an unparseable date is refused, never skipped (AD-12)."""
    header = "Txn Date,Value Date,Description,Ref No./Cheque No.,Debit,Credit,Balance\n"
    csv_text = header + "not-a-date,,SPEND,R1,450.00,,12000.00\n"
    with pytest.raises(IngestionError) as exc:
        CSVParser().parse(_write_tmp(tmp_path, "no_date.csv", csv_text))
    assert exc.value.code == "UNPARSEABLE_DATE"