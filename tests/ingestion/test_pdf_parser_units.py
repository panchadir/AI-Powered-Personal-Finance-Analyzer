"""Library-free unit coverage for ``services/ingestion/pdf_parser.py``.

The heavy extractors lazy-import pdfplumber/camelot/statementparser *inside* their ``extract()``
methods, but the actual parsing logic operates on plain Python structures — text lines, table
cells, and pdfplumber-shaped word dicts. This drives that logic directly (no real PDF, no
external libraries), plus the ``PDFParser`` chain/refusal paths via injected fake extractors.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.ingestion.errors import IngestionError, ScannedPDFError
from services.ingestion.pdf_parser import (
    CamelotExtractor,
    HDFCTableExtractor,
    ICICITextExtractor,
    PDFParser,
    PdfplumberExtractor,
    PositionalColumnExtractor,
    StatementsparserExtractor,
    _clean_dec,
    _is_txn_date,
    _money,
)
from services.utils.enums import Direction


def _w(text, x0, x1, top):
    return {"text": text, "x0": x0, "x1": x1, "top": top}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class TestSharedHelpers:
    def test_clean_dec_strips_commas(self):
        assert _clean_dec(" 1,234.50 ") == Decimal("1234.50")

    @pytest.mark.parametrize("text, expected", [
        ("450.00", Decimal("450.00")),
        ("1,200.50", Decimal("1200.50")),
        ("355.72 Dr", Decimal("355.72")),
        ("900.00 Cr", Decimal("900.00")),
        ("02.06.2026", None),  # a date is not money
        ("hello", None),
    ])
    def test_money(self, text, expected):
        assert _money(text) == expected

    def test_is_txn_date(self):
        assert _is_txn_date("02.06.2026") is True
        assert _is_txn_date("not a date") is False


# ---------------------------------------------------------------------------
# PositionalColumnExtractor — static geometry helpers
# ---------------------------------------------------------------------------

class TestPositionalHelpers:
    def test_cluster_empty(self):
        assert PositionalColumnExtractor._cluster([], gap=18.0) == []

    def test_cluster_merges_within_gap(self):
        assert PositionalColumnExtractor._cluster([100, 105, 400], gap=18.0) == [102.5, 400]

    def test_nearest(self):
        assert PositionalColumnExtractor._nearest(283, [280, 470]) == 280
        assert PositionalColumnExtractor._nearest(5, []) == 5

    def test_label_clusters_empty(self):
        assert PositionalColumnExtractor._label_clusters([], {}) == {}

    def test_label_clusters_two_amounts_orientation(self):
        centers = {"debit": 240, "credit": 330}
        roles = PositionalColumnExtractor._label_clusters([280, 360, 470], centers)
        assert roles == {470: "balance", 280: "debit", 360: "credit"}

    def test_label_clusters_extra_amounts_use_nearest(self):
        centers = {"debit": 100, "credit": 300}
        roles = PositionalColumnExtractor._label_clusters([100, 200, 260, 500], centers)
        assert roles[500] == "balance"
        assert roles[260] in {"debit", "credit"}  # the 3rd+ amount resolves by nearest header

    def test_label_clusters_single_amount_only_debit_header(self):
        roles = PositionalColumnExtractor._label_clusters([280, 470], {"debit": 240})
        assert roles == {470: "balance", 280: "debit"}

    def test_label_clusters_single_amount_only_credit_header(self):
        roles = PositionalColumnExtractor._label_clusters([280, 470], {"credit": 330})
        assert roles == {470: "balance", 280: "credit"}

    def test_header_centers_locates_all_roles(self):
        words = [
            _w("Date", 60, 80, 10), _w("Withdrawal", 200, 280, 10),
            _w("Deposit", 300, 360, 10), _w("Balance", 420, 480, 10),
        ]
        centers = PositionalColumnExtractor._header_centers(words)
        assert set(centers) == {"date", "debit", "credit", "balance"}

    def test_header_centers_none_when_no_headers(self):
        assert PositionalColumnExtractor._header_centers([_w("hello", 0, 10, 0)]) is None

    def test_header_centers_ties_pick_leftmost(self):
        # "Transaction Date" (left) beats "Value Date" (right) for the date role.
        words = [_w("Date", 60, 80, 10), _w("Date", 500, 520, 10)]
        centers = PositionalColumnExtractor._header_centers(words)
        assert centers["date"] == 70

    def test_group_lines_groups_by_top(self):
        words = [_w("b", 100, 110, 10), _w("a", 50, 60, 10.5), _w("c", 50, 60, 40)]
        lines = PositionalColumnExtractor._group_lines(words)
        assert [[w["text"] for w in line] for line in lines] == [["a", "b"], ["c"]]

    def test_amounts_credit_only_fallback(self):
        # Only a credit-column amount present (no debit) → credit direction.
        line = [_w("1,200.00", 300, 360, 10), _w("5,000.00", 420, 470, 10)]
        clusters = [360, 470]
        role_of = {360: "credit", 470: "balance"}
        amount, direction, balance = PositionalColumnExtractor()._amounts(line, clusters, role_of)
        assert amount == Decimal("1200.00") and direction == Direction.credit
        assert balance == Decimal("5000.00")

    def test_description_tokens_drops_sno_and_numeric_columns(self):
        date_word = _w("02.06.2026", 60, 100, 10)
        line = [
            _w("7", 30, 38, 10),          # S.No — left of date, dropped
            date_word,                     # the date word itself, dropped
            _w("SWIGGY", 150, 190, 10),   # kept
            _w("450.00", 240, 280, 10),   # money, dropped
        ]
        out = PositionalColumnExtractor._description_tokens(line, date_word, date_cx=80, numeric_left=240)
        assert [w["text"] for w in out] == ["SWIGGY"]

    def test_description_tokens_skips_nonmoney_in_numeric_columns(self):
        # A non-money token sitting at/after the numeric-column boundary is dropped, not folded
        # into the narration.
        line = [_w("SWIGGY", 150, 190, 10), _w("STRAY", 250, 290, 10)]
        out = PositionalColumnExtractor._description_tokens(line, None, date_cx=80, numeric_left=240)
        assert [w["text"] for w in out] == ["SWIGGY"]


# ---------------------------------------------------------------------------
# PositionalColumnExtractor._parse_page — the row assembler
# ---------------------------------------------------------------------------

def _header_words():
    return [
        _w("Date", 60, 80, 10), _w("Withdrawal", 200, 280, 10),
        _w("Deposit", 300, 360, 10), _w("Balance", 420, 480, 10),
    ]


class TestParsePage:
    def test_no_headers_returns_empty(self):
        txns, centers = PositionalColumnExtractor()._parse_page([_w("hi", 0, 10, 0)], None)
        assert txns == [] and centers is None

    def test_headers_but_no_money_returns_empty(self):
        txns, centers = PositionalColumnExtractor()._parse_page(_header_words(), None)
        assert txns == []
        assert centers and "date" in centers

    def test_parses_debit_and_credit_rows(self):
        words = _header_words() + [
            # debit row
            _w("02.06.2026", 60, 100, 30), _w("SWIGGY", 150, 190, 30),
            _w("450.00", 240, 280, 30), _w("1,000.00", 420, 470, 30),
            # credit row
            _w("05.06.2026", 60, 100, 50), _w("SALARY", 150, 190, 50),
            _w("5,000.00", 300, 360, 50), _w("6,000.00", 420, 470, 50),
        ]
        txns, _ = PositionalColumnExtractor()._parse_page(words, None)
        assert len(txns) == 2
        assert txns[0].direction == Direction.debit and txns[0].amount == Decimal("450.00")
        assert txns[1].direction == Direction.credit and txns[1].amount == Decimal("5000.00")

    def test_continuation_line_backfills_missing_amount(self):
        # The date row carries no money; the amount lands on the next visual line.
        words = _header_words() + [
            _w("02.06.2026", 60, 100, 30), _w("UPI", 150, 190, 30),
            _w("MERCHANT", 150, 210, 45), _w("450.00", 240, 280, 45),
            _w("1,000.00", 420, 470, 45),
        ]
        txns, _ = PositionalColumnExtractor()._parse_page(words, None)
        assert len(txns) == 1 and txns[0].amount == Decimal("450.00")
        assert "MERCHANT" in txns[0].description_raw

    def test_footer_marker_ends_transaction_block(self):
        words = _header_words() + [
            _w("02.06.2026", 60, 100, 30), _w("SWIGGY", 150, 190, 30),
            _w("450.00", 240, 280, 30), _w("1,000.00", 420, 470, 30),
            _w("This", 60, 90, 50), _w("is", 95, 110, 50), _w("a", 115, 120, 50),
            _w("system", 125, 170, 50),  # "this is a system" footer marker
        ]
        txns, _ = PositionalColumnExtractor()._parse_page(words, None)
        assert len(txns) == 1  # footer text not folded into a phantom row


# ---------------------------------------------------------------------------
# ICICITextExtractor._parse_text
# ---------------------------------------------------------------------------

class TestICICIParseText:
    def test_parses_debit_and_credit_and_skips_footer_and_bad_date(self):
        text = "\n".join([
            "MR RAVI",
            "1  02.06.2026  65.00  21364.25",
            "UPI/MR RAVI/q950008199@ybl/YES BANK",
            "This is a system generated statement",   # footer — stops narration
            "YELLANKI R",
            "2  06.06.2026  1,200.00  22564.25",       # a2 absent → amount = a1
            "3  99.99.9999  10.00  100.00",            # bad date → skipped
        ])
        txns = ICICITextExtractor()._parse_text(text)
        assert len(txns) == 2
        assert txns[0].direction == Direction.debit and txns[0].amount == Decimal("65.00")
        # second row's balance rose above the first → credit
        assert txns[1].direction == Direction.credit

    def test_middle_amount_uses_balance_delta(self):
        text = "\n".join([
            "OPEN",
            "1  02.06.2026  100.00  1000.00",
            "2  03.06.2026  50.00  200.00  1200.00",  # a2 present + prev balance → delta = 200
        ])
        txns = ICICITextExtractor()._parse_text(text)
        assert txns[1].amount == Decimal("200.00") and txns[1].direction == Direction.credit


# ---------------------------------------------------------------------------
# HDFCTableExtractor
# ---------------------------------------------------------------------------

class TestHDFCTable:
    _HEADER = ["Txn Date", "Narration", "Withdrawals", "Deposits", "Closing Balance"]

    def test_parses_merged_rows(self):
        table = [
            self._HEADER,
            [
                "01/05/2026\n02/05/2026",
                "UPI SWIGGY Value Dt 01/05/2026 Ref 189499104532\n"
                "NEFT SALARY Value Dt 02/05/2026 Ref 555",
                "450.00\n",
                "\n85000.00",
                "9550.00\n94550.00",
            ],
        ]
        txns = HDFCTableExtractor()._parse_table(table)
        assert len(txns) == 2
        assert txns[0].direction == Direction.debit and txns[0].amount == Decimal("450.00")
        assert txns[1].direction == Direction.credit and txns[1].amount == Decimal("85000.00")

    def test_no_header_row_returns_empty(self):
        assert HDFCTableExtractor()._parse_table([["a", "b"], ["1", "2"]]) == []

    def test_empty_table_returns_empty(self):
        assert HDFCTableExtractor()._parse_table([]) == []

    def test_split_narrations_single_group(self):
        out = HDFCTableExtractor()._split_narrations(["one", "two"], n=1)
        assert out == ["one two"]

    def test_split_narrations_inline_ref_boundary(self):
        # First transaction's narration is closed at its inline "Value Dt … Ref <n>" marker.
        lines = [
            "UPI A Value Dt 01/05/2026 Ref 111",
            "UPI B Value Dt 02/05/2026 Ref 222",
        ]
        out = HDFCTableExtractor()._split_narrations(lines, n=2)
        assert len(out) == 2 and "UPI A" in out[0]

    def test_split_narrations_ref_on_next_line(self):
        # The "Value Dt … Ref" marker with the ref number on the *following* line closes the
        # group only after that standalone ref line is consumed (the pending-ref branch).
        lines = [
            "UPI A Value Dt 01/05/2026 Ref",
            "111",
            "UPI B Value Dt 02/05/2026 Ref",
            "222",
        ]
        out = HDFCTableExtractor()._split_narrations(lines, n=2)
        assert len(out) == 2 and "UPI A" in out[0] and "111" in out[0]

    def test_split_narrations_pads_when_short(self):
        out = HDFCTableExtractor()._split_narrations(["only one narration"], n=3)
        assert len(out) == 3 and out[1] == "" and out[2] == ""


# ---------------------------------------------------------------------------
# StatementsparserExtractor._to_canonical
# ---------------------------------------------------------------------------

class TestStatementsparserCanonical:
    def test_maps_debit(self):
        txn = SimpleNamespace(
            type=SimpleNamespace(value="DEBIT"),
            date=SimpleNamespace(isoformat=lambda: "2026-06-01"),
            narration="SWIGGY", description=None,
            amount=Decimal("-450.00"), closing_balance=Decimal("1000"),
        )
        out = StatementsparserExtractor._to_canonical(txn)
        assert out.direction == Direction.debit and out.amount == Decimal("450.00")
        assert out.date == "2026-06-01" and out.description_raw == "SWIGGY"

    def test_maps_credit_using_description_fallback(self):
        txn = SimpleNamespace(
            type="CREDIT",
            date=SimpleNamespace(isoformat=lambda: "2026-06-02"),
            narration=None, description="SALARY",
            amount=Decimal("85000"), closing_balance=None,
        )
        out = StatementsparserExtractor._to_canonical(txn)
        assert out.direction == Direction.credit and out.description_raw == "SALARY"


# ---------------------------------------------------------------------------
# PDFParser — chain orchestration + refusal paths
# ---------------------------------------------------------------------------

class _FakeExtractor:
    def __init__(self, name, rows=None, boom=False):
        self.name = name
        self._rows = rows or []
        self._boom = boom

    def extract(self, file_path):
        if self._boom:
            raise RuntimeError("extractor exploded")
        return self._rows


def _txn():
    from services.ingestion.schema import Transaction

    return Transaction(date="2026-06-01", description_raw="X", amount=Decimal("1"),
                       direction=Direction.debit, balance_after=None)


# ---------------------------------------------------------------------------
# HDFC _parse_table edge branches (empty rows, junk cells, missing dates)
# ---------------------------------------------------------------------------

class TestHDFCTableEdges:
    _HEADER = ["Txn Date", "Narration", "Withdrawals", "Deposits", "Closing Balance"]

    def test_skips_empty_and_dateless_and_zero_rows(self):
        table = [
            self._HEADER,
            None,                                                   # empty row → skipped
            ["no dates here", "junk", "1.00", "", "5.00"],          # no valid date → skipped
            ["01/05/2026", "N Value Dt 01/05/2026 Ref 1", "bad", "worse", "notnum"],  # junk decimals → 0/None
            ["02/05/2026", "N Value Dt 02/05/2026 Ref 2", "", "", "9.00"],            # both zero → skipped
        ]
        txns = HDFCTableExtractor()._parse_table(table)
        # The junk-decimal row parses to withdrawal=0/deposit=0 → also skipped; net zero rows.
        assert txns == []

    def test_skips_row_whose_date_matches_shape_but_is_invalid(self):
        # "99/99/9999" passes the DD/MM/YYYY *shape* regex but normalize_date rejects it.
        table = [
            self._HEADER,
            ["99/99/9999", "N Value Dt 99/99/9999 Ref 1", "450.00", "", "9550.00"],
        ]
        assert HDFCTableExtractor()._parse_table(table) == []


# ---------------------------------------------------------------------------
# .extract() methods — driven with fake lazily-imported libraries
# ---------------------------------------------------------------------------

class _FakePage:
    def __init__(self, text="", tables=None, words=None):
        self._text, self._tables, self._words = text, tables or [], words or []

    def extract_text(self):
        return self._text

    def extract_tables(self):
        return self._tables

    def extract_words(self, **_kwargs):
        return self._words


class _FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install_pdfplumber(monkeypatch, pages):
    import sys

    fake = SimpleNamespace(open=lambda _path: _FakePdf(pages))
    monkeypatch.setitem(sys.modules, "pdfplumber", fake)


class TestExtractMethods:
    def test_icici_extract_delegates_when_icici(self, monkeypatch):
        text = "ICICI Bank\n1  02.06.2026  65.00  1000.00\nUPI/X"
        _install_pdfplumber(monkeypatch, [_FakePage(text=text)])
        txns = ICICITextExtractor().extract(Path("x.pdf"))
        assert len(txns) == 1

    def test_icici_extract_returns_empty_for_other_bank(self, monkeypatch):
        _install_pdfplumber(monkeypatch, [_FakePage(text="SomeOtherBank statement")])
        assert ICICITextExtractor().extract(Path("x.pdf")) == []

    def test_hdfc_extract_delegates_when_hdfc(self, monkeypatch):
        table = [
            ["Txn Date", "Narration", "Withdrawals", "Deposits", "Closing Balance"],
            ["01/05/2026", "UPI SWIGGY Value Dt 01/05/2026 Ref 1", "450.00", "", "9550.00"],
        ]
        _install_pdfplumber(monkeypatch, [_FakePage(text="HDFC BANK", tables=[table])])
        txns = HDFCTableExtractor().extract(Path("x.pdf"))
        assert len(txns) == 1 and txns[0].amount == Decimal("450.00")

    def test_hdfc_extract_returns_empty_for_other_bank(self, monkeypatch):
        _install_pdfplumber(monkeypatch, [_FakePage(text="ICICI only")])
        assert HDFCTableExtractor().extract(Path("x.pdf")) == []

    def test_pdfplumber_extract_maps_tables(self, monkeypatch):
        table = [
            ["Date", "Narration", "Withdrawal", "Deposit", "Balance"],
            ["01/05/2026", "SWIGGY", "450.00", "", "9550.00"],
        ]
        _install_pdfplumber(monkeypatch, [_FakePage(tables=[table])])
        result = PdfplumberExtractor().extract(Path("x.pdf"))
        assert isinstance(result, list)

    def test_positional_extract_runs_over_words_and_skips_empty_pages(self, monkeypatch):
        words = _header_words() + [
            _w("02.06.2026", 60, 100, 30), _w("SWIGGY", 150, 190, 30),
            _w("450.00", 240, 280, 30), _w("1,000.00", 420, 470, 30),
        ]
        _install_pdfplumber(monkeypatch, [_FakePage(words=[]), _FakePage(words=words)])
        txns = PositionalColumnExtractor().extract(Path("x.pdf"))
        assert len(txns) == 1

    def test_pdf_has_text_layer(self, monkeypatch):
        from services.ingestion.pdf_parser import _pdf_has_text_layer

        _install_pdfplumber(monkeypatch, [_FakePage(text="  "), _FakePage(text="real text")])
        assert _pdf_has_text_layer(Path("x.pdf")) is True
        _install_pdfplumber(monkeypatch, [_FakePage(text="   ")])
        assert _pdf_has_text_layer(Path("x.pdf")) is False

    def test_camelot_extract_maps_tables(self, monkeypatch):
        import sys

        rows = [
            ["Date", "Narration", "Withdrawal", "Deposit", "Balance"],
            ["01/05/2026", "SWIGGY", "450.00", "", "9550.00"],
        ]
        table = SimpleNamespace(df=SimpleNamespace(values=SimpleNamespace(tolist=lambda: rows)))
        fake_camelot = SimpleNamespace(read_pdf=lambda _p, pages=None: [table])
        monkeypatch.setitem(sys.modules, "camelot", fake_camelot)
        result = CamelotExtractor().extract(Path("x.pdf"))
        assert isinstance(result, list)

    def test_statementsparser_extract_maps_transactions(self, monkeypatch):
        import sys

        txn = SimpleNamespace(
            type=SimpleNamespace(value="DEBIT"),
            date=SimpleNamespace(isoformat=lambda: "2026-06-01"),
            narration="SWIGGY", description=None,
            amount=Decimal("450"), closing_balance=Decimal("1000"),
        )
        statement = SimpleNamespace(transactions=[txn])
        fake_sp = SimpleNamespace(parse=lambda _p, categorize=True, verify_balance=True: statement)
        fake_base = SimpleNamespace(DATE_FORMATS={"ICICI": []})
        fake_parsers = SimpleNamespace(base=fake_base)
        monkeypatch.setitem(sys.modules, "statementparser", fake_sp)
        monkeypatch.setitem(sys.modules, "statementparser.parsers", fake_parsers)
        monkeypatch.setitem(sys.modules, "statementparser.parsers.base", fake_base)
        result = StatementsparserExtractor().extract(Path("x.pdf"))
        assert len(result) == 1 and result[0].amount == Decimal("450")

    def test_statementsparser_extract_tolerates_missing_date_formats_module(self, monkeypatch):
        # The DATE_FORMATS patch is best-effort: if the library's internals aren't importable
        # the extractor must still parse (the try/except around the patch).
        import sys

        txn = SimpleNamespace(
            type=SimpleNamespace(value="CREDIT"),
            date=SimpleNamespace(isoformat=lambda: "2026-06-02"),
            narration="SALARY", description=None,
            amount=Decimal("85000"), closing_balance=None,
        )
        statement = SimpleNamespace(transactions=[txn])
        fake_sp = SimpleNamespace(parse=lambda _p, categorize=True, verify_balance=True: statement)
        monkeypatch.setitem(sys.modules, "statementparser", fake_sp)
        # Deliberately do NOT register statementparser.parsers.base → the inner import raises.
        monkeypatch.delitem(sys.modules, "statementparser.parsers.base", raising=False)
        monkeypatch.delitem(sys.modules, "statementparser.parsers", raising=False)
        result = StatementsparserExtractor().extract(Path("x.pdf"))
        assert len(result) == 1 and result[0].direction == Direction.credit


class TestPDFParserChain:
    def test_returns_first_nonempty_and_skips_failing(self, tmp_path):
        rows = [_txn()]
        parser = PDFParser(
            extractors=[
                _FakeExtractor("boom", boom=True),   # logged + skipped
                _FakeExtractor("empty", rows=[]),    # empty → try next
                _FakeExtractor("hit", rows=rows),    # returns
            ],
            text_probe=lambda p: True,
        )
        assert parser.parse(tmp_path / "x.pdf") == rows

    def test_all_empty_with_text_layer_raises_no_transactions(self, tmp_path):
        parser = PDFParser(extractors=[_FakeExtractor("empty", rows=[])], text_probe=lambda p: True)
        with pytest.raises(IngestionError) as exc:
            parser.parse(tmp_path / "x.pdf")
        assert exc.value.code == "NO_TRANSACTIONS_FOUND"

    def test_all_empty_without_text_layer_raises_scanned(self, tmp_path):
        parser = PDFParser(extractors=[_FakeExtractor("empty", rows=[])], text_probe=lambda p: False)
        with pytest.raises(ScannedPDFError):
            parser.parse(tmp_path / "x.pdf")

    def test_default_extractor_chain_is_the_documented_six(self):
        parser = PDFParser()
        names = [e.name for e in parser._extractors]
        assert names == [
            "positional_text", "statementsparser", "icici_text",
            "hdfc_table", "pdfplumber", "camelot",
        ]
