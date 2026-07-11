"""Regression guard: raw confidence is never shown in the UI (Story 3.4, AC #4).

Two checks, both structural rather than behavioral, so a future change can't silently
reintroduce a raw confidence number/percentage without a test noticing:

1. ``TxnRow`` (the transactions page's only display model) has no confidence-carrying
   field at all — ``category_confidence`` is consumed by ``_to_row`` purely to derive the
   ``needs_review``/``is_ai`` badge booleans and never forwarded onto the row itself, so the
   page has no field to accidentally render even if someone tried.
2. The transactions page module's source never references ``category_confidence`` — a
   defense-in-depth text scan in case a future change bypasses ``TxnRow`` entirely (e.g. a
   new component reading straight off the DB model).

Mirrors the AST/text-based structural-guard style already used by
``tests/test_service_boundary.py``.
"""
from __future__ import annotations

from pathlib import Path

from finance_app.state.transactions_state import TxnRow

PAGE_FILE = Path(__file__).resolve().parent.parent / "finance_app" / "pages" / "transactions.py"


def test_txn_row_has_no_confidence_field() -> None:
    field_names = TxnRow.model_fields.keys()
    confidence_fields = [f for f in field_names if "confidence" in f.lower()]
    assert not confidence_fields, (
        "TxnRow must never carry a raw confidence field (AC #4) — found: "
        + ", ".join(confidence_fields)
    )


def test_transactions_page_never_references_raw_confidence() -> None:
    source = PAGE_FILE.read_text(encoding="utf-8")
    assert "category_confidence" not in source, (
        "finance_app/pages/transactions.py must never reference category_confidence "
        "directly (AC #4: raw confidence percentages are never shown anywhere in the UI)."
    )
