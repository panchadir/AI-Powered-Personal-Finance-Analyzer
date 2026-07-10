"""Story 2.4 seam: parse_statement dispatches uploaded bytes to the right parser.

The Reflex upload handler hands this framework-agnostic function a filename + bytes; it must
route CSV vs PDF, parse to canonical transactions, and refuse unknown types with a typed
error (AD-12). Only the CSV path is exercised end-to-end here (real parser, no external PDF
libs needed); PDF dispatch is asserted at the routing level.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from services.ingestion import (
    CSVParser,
    IngestionError,
    PDFParser,
    Transaction,
    UnsupportedFormatError,
    extension_of,
    parse_statement,
    parser_for,
)
from services.utils.enums import Direction

FIXTURES = Path(__file__).parent / "fixtures"


def test_extension_of() -> None:
    assert extension_of("HDFC-Statement.CSV") == "csv"
    assert extension_of("june.pdf") == "pdf"
    assert extension_of("noext") == ""


def test_parser_for_routes_by_extension() -> None:
    assert isinstance(parser_for("x.csv"), CSVParser)
    assert isinstance(parser_for("x.pdf"), PDFParser)


def test_parser_for_unknown_extension_is_refused() -> None:
    with pytest.raises(UnsupportedFormatError):
        parser_for("statement.xlsx")


def test_parse_statement_csv_end_to_end() -> None:
    data = (FIXTURES / "hdfc_sample.csv").read_bytes()
    rows = parse_statement("hdfc_sample.csv", data)
    assert len(rows) == 4
    assert all(isinstance(t, Transaction) for t in rows)
    assert all(isinstance(t.amount, Decimal) for t in rows)  # AD-8
    assert rows[0].direction is Direction.debit and rows[0].amount == Decimal("450.00")


def test_parse_statement_unknown_type_raises_before_touching_data() -> None:
    with pytest.raises(UnsupportedFormatError):
        parse_statement("statement.docx", b"whatever")


def test_parse_statement_wraps_unexpected_error_as_typed(monkeypatch) -> None:
    """Any non-IngestionError from a parser is wrapped as a typed IngestionError, so the
    UI's single catch site holds and the beforeunload guard clears (AD-12). (Realistic
    triggers: csv.Error on malformed CSV, OSError, or a parser bug — encoding is handled
    separately by CSVParser's cp1252/latin-1 fallback.)
    """
    import services.ingestion.dispatch as dispatch

    def _boom(self, path):
        raise ValueError("kaboom inside a parser")

    monkeypatch.setattr(dispatch.CSVParser, "parse", _boom)
    with pytest.raises(IngestionError) as exc:
        parse_statement("bank.csv", b"anything")
    assert exc.value.code == "PARSE_FAILED"


def test_parse_statement_cleans_up_temp_file(tmp_path, monkeypatch) -> None:
    """The temp file the dispatcher writes is always removed, even on parse failure."""
    import services.ingestion.dispatch as dispatch

    created: list[Path] = []
    real_mkstemp = dispatch.tempfile.mkstemp

    def _tracking_mkstemp(*a, **k):
        fd, name = real_mkstemp(*a, **k)
        created.append(Path(name))
        return fd, name

    monkeypatch.setattr(dispatch.tempfile, "mkstemp", _tracking_mkstemp)
    # A CSV with an unknown column layout makes CSVParser raise mid-parse.
    with pytest.raises(UnsupportedFormatError):
        parse_statement("weird.csv", b"Foo,Bar,Baz\n1,2,3\n")
    assert created and not created[0].exists()  # cleaned up despite the raise