"""Day-1 validation of the flagged statementsparser assumption (Story 1.1 AC #4).

The architecture spine flags statementsparser as an ASSUMPTION: "covers HDFC demo
format — verify Day 1 hour 1". This test locks that verification in as a repeatable
guard so a future dependency bump that drops HDFC support fails loudly here rather
than surfacing as a silent parse failure in Epic 2.

GOTCHA (documented for Epic 2): the PyPI package is `statementsparser` but the
import name is `statementparser` (no trailing "s").

SCOPE: this asserts the library *ships and registers* an HDFC parser. A live parse
of the actual Priya demo HDFC PDF is owed in Epic 2 Story 2.3 (golden-file test),
once data/demo-data.json and the demo statement fixture exist.
"""
from __future__ import annotations

import importlib


def test_statementparser_importable() -> None:
    """PyPI `statementsparser` imports as `statementparser`."""
    sp = importlib.import_module("statementparser")
    assert hasattr(sp, "parse"), "expected a top-level parse() entrypoint"


def test_hdfc_parser_is_registered() -> None:
    """The flagged assumption: HDFC format is supported."""
    from statementparser.parsers.registry import list_parsers

    banks = {b.upper() for b in list_parsers()}
    assert "HDFC" in banks, (
        f"statementsparser no longer registers an HDFC parser (found {sorted(banks)}). "
        "The Day-1 flagged assumption has REGRESSED — Epic 2 ingestion must fall back "
        "to the pdfplumber -> camelot chain for HDFC (AD-6)."
    )


def test_hdfc_parser_class_available() -> None:
    """A concrete HDFCParser class exists to adapt into the canonical schema (AD-6)."""
    hdfc = importlib.import_module("statementparser.parsers.hdfc")
    assert hasattr(hdfc, "HDFCParser")
