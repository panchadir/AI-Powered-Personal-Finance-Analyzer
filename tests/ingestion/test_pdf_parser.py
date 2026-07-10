"""Story 2.3 acceptance: PDF parser chain + honest scanned-image refusal.

Covers everything the AC specifies that does NOT need a real HDFC PDF:

* the chain tries extractors in order and stops at the first that yields rows;
* a failing extractor is logged and the chain falls through (never a hard crash);
* an image PDF (no text layer) is refused with the exact approved copy via `ScannedPDFError`;
* a text PDF that yields nothing is refused with a typed `NO_TRANSACTIONS_FOUND`;
* the `statementsparser` adapter maps the library's Transaction to the canonical schema;
* the pdfplumber/camelot table path reuses the CSV column mapping (`map_table`), including
  the F1 (0.00 padding) and F2 (footer-row skip) handling.

The one deferred AC — a real text-based HDFC PDF parsing to exactly 24 rows — is tracked in
`deferred-work.md`; it needs a fixture that isn't in the repo yet.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.ingestion import (
    IngestionError,
    PDFParser,
    ScannedPDFError,
    SCANNED_MESSAGE,
    StatementParser,
    StatementsparserExtractor,
    Transaction,
    map_table,
)
from services.utils.enums import Direction

HDFC_HEADER = [
    "Date", "Narration", "Chq./Ref.No.", "Value Dt",
    "Withdrawal Amt.", "Deposit Amt.", "Closing Balance",
]
DUMMY = Path("statement.pdf")


class _FakeExtractor:
    """A stand-in chain link recording whether it was called."""

    def __init__(self, name: str, rows=None, raises: Exception | None = None) -> None:
        self.name = name
        self._rows = rows or []
        self._raises = raises
        self.called = False

    def extract(self, file_path: Path) -> list[Transaction]:
        self.called = True
        if self._raises is not None:
            raise self._raises
        return self._rows


def _txn(**kw) -> Transaction:
    base = dict(date="2026-06-01", description_raw="X", amount=Decimal("10.00"),
                direction=Direction.debit)
    base.update(kw)
    return Transaction(**base)


# --- protocol + chain ordering ------------------------------------------------

def test_pdf_parser_satisfies_protocol() -> None:
    parser: StatementParser = PDFParser()
    assert isinstance(parser, StatementParser)


def test_chain_returns_first_extractor_with_rows_and_stops() -> None:
    first = _FakeExtractor("a", rows=[])                 # empty -> fall through
    second = _FakeExtractor("b", rows=[_txn()])          # yields rows -> win
    third = _FakeExtractor("c", rows=[_txn(), _txn()])   # must NOT be reached
    out = PDFParser(extractors=[first, second, third], text_probe=lambda p: True).parse(DUMMY)
    assert len(out) == 1
    assert first.called and second.called and not third.called


def test_failing_extractor_is_skipped_not_fatal() -> None:
    boom = _FakeExtractor("boom", raises=RuntimeError("camelot blew up"))
    ok = _FakeExtractor("ok", rows=[_txn()])
    out = PDFParser(extractors=[boom, ok], text_probe=lambda p: True).parse(DUMMY)
    assert len(out) == 1 and ok.called


# --- honest refusals ----------------------------------------------------------

def test_scanned_image_pdf_is_refused_with_exact_copy() -> None:
    """No rows + no text layer → ScannedPDFError with the approved microcopy (FR-2.4)."""
    parser = PDFParser(extractors=[_FakeExtractor("a", rows=[])], text_probe=lambda p: False)
    with pytest.raises(ScannedPDFError) as exc:
        parser.parse(DUMMY)
    assert str(exc.value) == SCANNED_MESSAGE
    assert exc.value.code == "NO_TEXT_LAYER"
    assert "scanned image" in SCANNED_MESSAGE  # guards against silent copy drift


def test_text_pdf_with_no_transactions_is_refused_distinctly() -> None:
    """No rows but text IS present → a different typed refusal, not the scanned message."""
    parser = PDFParser(extractors=[_FakeExtractor("a", rows=[])], text_probe=lambda p: True)
    with pytest.raises(IngestionError) as exc:
        parser.parse(DUMMY)
    assert exc.value.code == "NO_TRANSACTIONS_FOUND"
    assert not isinstance(exc.value, ScannedPDFError)


# --- statementsparser adapter mapping ----------------------------------------

def test_statementsparser_extractor_maps_to_canonical(monkeypatch) -> None:
    lib_txns = [
        SimpleNamespace(
            date=date(2026, 6, 1), narration="UPI-SWIGGY", description="",
            amount=Decimal("450.00"), type=SimpleNamespace(value="DEBIT"),
            closing_balance=Decimal("18000.00"),
        ),
        SimpleNamespace(
            date=date(2026, 6, 30), narration="SALARY", description="",
            amount=Decimal("85000.00"), type=SimpleNamespace(value="CREDIT"),
            closing_balance=Decimal("103000.00"),
        ),
    ]
    import statementparser
    monkeypatch.setattr(
        statementparser, "parse",
        lambda *a, **k: SimpleNamespace(transactions=lib_txns),
    )
    rows = StatementsparserExtractor().extract(DUMMY)
    assert [(r.date, r.direction, r.amount) for r in rows] == [
        ("2026-06-01", Direction.debit, Decimal("450.00")),
        ("2026-06-30", Direction.credit, Decimal("85000.00")),
    ]
    assert rows[0].balance_after == Decimal("18000.00")
    assert all(isinstance(r.amount, Decimal) for r in rows)  # AD-8


def test_pdfplumber_extractor_wires_tables_into_map_table(monkeypatch) -> None:
    """The pdfplumber adapter feeds each extracted table through the shared map_table."""
    table = [HDFC_HEADER,
             ["01/06/2026", "UPI-SWIGGY", "R1", "01/06/2026", "450.00", "", "18000.00"]]

    class _Page:
        def extract_tables(self):
            return [table]

    class _PDF:
        pages = [_Page()]
        def __enter__(self): return self
        def __exit__(self, *a): return False

    # inject a fake `pdfplumber` module so the adapter's lazy `import pdfplumber` resolves to it
    import sys
    monkeypatch.setitem(sys.modules, "pdfplumber", SimpleNamespace(open=lambda p: _PDF()))

    from services.ingestion.pdf_parser import PdfplumberExtractor
    rows = PdfplumberExtractor().extract(DUMMY)
    assert len(rows) == 1
    assert rows[0].direction is Direction.debit and rows[0].amount == Decimal("450.00")


# --- shared map_table (used by pdfplumber/camelot) ---------------------------

def test_map_table_maps_hdfc_table_reusing_csv_logic() -> None:
    data = [
        ["01/06/2026", "UPI-SWIGGY", "R1", "01/06/2026", "450.00", "0.00", "18000.00"],
        ["30/06/2026", "SALARY", "R2", "30/06/2026", "0.00", "85,000.00", "88,000.00"],
        ["Opening Balance", "", "", "", "", "", "12000.00"],  # footer → skipped (F2)
    ]
    rows = map_table(HDFC_HEADER, data)
    assert len(rows) == 2  # footer skipped
    # 0.00 padding handled (F1): debit row and credit row resolve correctly
    assert rows[0].direction is Direction.debit and rows[0].amount == Decimal("450.00")
    assert rows[1].direction is Direction.credit and rows[1].amount == Decimal("85000.00")


def test_map_table_unknown_header_returns_empty() -> None:
    """An unrecognized table yields [] so the PDF chain falls through (no raise)."""
    assert map_table(["Foo", "Bar", "Baz"], [["1", "2", "3"]]) == []


def test_map_table_tolerates_empty_header_cell_without_misaligning() -> None:
    """An empty header cell (common in extracted PDF tables) must not shift columns.

    Regression: previously the empty cell was filtered from the header while data rows kept
    full positions, so every column after the gap read the wrong value (silent wrong data).
    """
    header = ["Date", "", "Narration", "Chq./Ref.No.", "Value Dt",
              "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"]
    data = [["01/06/2026", "xref", "UPI-SWIGGY", "R1", "01/06/2026",
             "450.00", "", "18000.00"]]
    rows = map_table(header, data)
    assert len(rows) == 1
    r = rows[0]
    assert r.date == "2026-06-01"
    assert r.description_raw == "UPI-SWIGGY"
    assert r.amount == Decimal("450.00") and r.direction is Direction.debit
    assert r.balance_after == Decimal("18000.00")