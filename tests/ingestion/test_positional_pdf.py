"""Regression: the coordinate-based PDF extractor separates columns by x position.

Generates a positional bank-statement PDF (text laid out in columns with no ruled lines,
wrapped narration, right-aligned amounts) with ``fitz`` and asserts the extractor recovers
every transaction with the correct debit/credit direction, amount and balance.

The point the test protects: **direction comes from which column an amount sits in, not from
balance movement.** The dataset includes a batch whose running balance does NOT move by the
row's own amount (real ICICI NACH/mandate batches behave this way); a balance-delta approach
would mislabel those rows, the x-position approach must not. It also covers a short single-line
narration sharing the amount row, and a date embedded inside a narration (must not start a new
transaction).

Skipped where ``fitz`` (pymupdf, a statementsparser dependency) isn't installed.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

fitz = pytest.importorskip("fitz")

from services.ingestion.pdf_parser import PositionalColumnExtractor
from services.utils.enums import Direction

# (sno, date, [narration blocks], 'D'|'C', amount, balance)
_ROWS = [
    (1, "02.06.2026", ["MR RAVI KU", "UPI/MR RAVI KU/q950008199@ybl/UPI/YES BANK L/615363"], "D", "65.00", "21364.25"),
    (2, "06.06.2026", ["YELLANKI R", "UPI/YELLANKI R/7898014838@ybl/Maintenanc/HDFC BANK"], "C", "1,200.00", "22564.25"),
    # balance-scrambled batch: deltas != amounts; direction is fixed only by column.
    (3, "10.06.2026", ["NACH trxn", "ACH/ETMONEY/ICIC7010504220003906/ETMONEY XXX1"], "D", "2,000.00", "16000.00"),
    (4, "10.06.2026", ["NACH trxn", "ACH/ETMONEY/ICIC7010504220003906/ETMONEY XXX2"], "C", "4,000.00", "18000.00"),
    (5, "10.06.2026", ["NACH trxn", "ACH/ETMONEY/ICIC7010504220003906/ETMONEY XXX3"], "D", "2,500.00", "10000.00"),
    (6, "19.06.2026", ["Self BIL/INFT/FFN2708723/CC BillPay-3007/Self"], "D", "14,739.88", "5360.39"),
    (7, "30.06.2026", ["Credit trxn", "006001550566:Int.Pd:30-03-2026 to 29-06-2026"], "C", "265.00", "5625.39"),
]

_X_SNO, _X_DATE, _X_REMARK = 38, 70, 210
_R_WITHDRAWAL, _R_DEPOSIT, _R_BALANCE = 415, 482, 548
_FS = 8


def _build_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    def txt(x, y, s):
        page.insert_text((x, y), s, fontsize=_FS, fontname="helv")

    def rtxt(right, y, s):
        w = fitz.get_text_length(s, fontname="helv", fontsize=_FS)
        page.insert_text((right - w, y), s, fontsize=_FS)

    def wrap(s, max_x=345):
        limit = max_x - _X_REMARK
        lines, cur = [], ""
        for word in s.split():
            trial = (cur + " " + word).strip()
            if fitz.get_text_length(trial, fontname="helv", fontsize=_FS) > limit and cur:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    page.insert_text((240, 30), "ICICI Bank", fontsize=12, fontname="helv")
    hy = 62
    txt(_X_SNO, hy, "S No.")
    txt(_X_DATE, hy, "Transaction"); txt(_X_DATE, hy + 10, "Date")
    txt(_X_REMARK, hy + 5, "Transaction Remarks")
    txt(345, hy, "Withdrawal"); txt(345, hy + 10, "Amount (INR)")
    txt(415, hy, "Deposit"); txt(415, hy + 10, "Amount (INR)")
    txt(505, hy, "Balance"); txt(505, hy + 10, "(INR)")

    y = 95
    for sno, date, blocks, col, amount, balance in _ROWS:
        wrapped = [ln for block in blocks for ln in wrap(block)]
        txt(_X_SNO, y, str(sno))
        txt(_X_DATE, y, date)
        txt(_X_REMARK, y, wrapped[0])
        rtxt(_R_WITHDRAWAL if col == "D" else _R_DEPOSIT, y, amount)
        rtxt(_R_BALANCE, y, balance)
        for k, extra in enumerate(wrapped[1:], start=1):
            txt(_X_REMARK, y + 10 * k, extra)
        y += 12 + 10 * len(wrapped)

    txt(40, y + 10, "Never share your OTP, CVV or passwords with anyone.")
    txt(40, y + 22, "www.icici.bank.in    Dial your Bank 1800-1080")
    doc.save(path)
    doc.close()


def test_positional_extractor_separates_columns_by_x(tmp_path) -> None:
    pdf = tmp_path / "statement.pdf"
    _build_pdf(str(pdf))

    rows = PositionalColumnExtractor().extract(pdf)

    assert len(rows) == len(_ROWS)
    for (sno, _date, _blocks, col, amount, balance), r in zip(_ROWS, rows):
        expected_dir = Direction.debit if col == "D" else Direction.credit
        assert r.direction is expected_dir, f"row {sno}: wrong direction"
        assert r.amount == Decimal(amount.replace(",", "")), f"row {sno}: wrong amount"
        assert r.balance_after == Decimal(balance), f"row {sno}: wrong balance"
        assert isinstance(r.amount, Decimal)  # AD-8: never float


def test_positional_extractor_direction_ignores_balance_movement(tmp_path) -> None:
    """The scrambled batch (rows 3–5) proves direction is column-driven, not delta-driven."""
    pdf = tmp_path / "statement.pdf"
    _build_pdf(str(pdf))
    rows = PositionalColumnExtractor().extract(pdf)
    # All three share date 2026-06-10; their balances move up and down independently of
    # amount, yet the middle one is the only credit — exactly as placed by column.
    directions = [r.direction for r in rows if r.description_raw.startswith("NACH")]
    assert directions == [Direction.debit, Direction.credit, Direction.debit]
