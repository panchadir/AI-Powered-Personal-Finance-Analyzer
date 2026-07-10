"""CSV statement parser for Indian bank exports (Story 2.2, FR-2.1).

Implements the :class:`~services.ingestion.protocol.StatementParser` contract for CSV
files. Different banks label the same columns differently and split (or share) the
debit/credit columns; a small registry of :class:`BankCSVProfile` records maps each known
header shape onto the canonical :class:`~services.ingestion.schema.Transaction`. Adding a
bank is adding one profile — no branching in the parse loop.

Two profiles ship in this story (FR-2.1 requires ≥2): **HDFC** (``Withdrawal Amt.`` /
``Deposit Amt.``) and **SBI** (``Debit`` / ``Credit``). Detection is by header signature,
case- and whitespace-insensitive, so trailing blank columns or minor spacing don't break it.

Every amount is parsed as :class:`~decimal.Decimal` after stripping Indian-grouped commas
and currency symbols — never ``float`` (AD-8). Dates are normalized to ISO and descriptions
whitespace-collapsed via :mod:`services.ingestion.normalize`, so the dedup key is stable
across a re-upload.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from services.ingestion.errors import IngestionError, UnsupportedFormatError
from services.ingestion.normalize import normalize_date
from services.ingestion.schema import Transaction
from services.utils.enums import Direction

__all__ = ["CSVParser", "BankCSVProfile", "PROFILES"]

# Encodings tried in order when reading a CSV. utf-8-sig first (BOM-aware, the common case);
# many Indian bank exports are Windows cp1252; latin-1 is the guaranteed final fallback — it
# maps every byte so it never raises, so an unusual encoding yields an approximate character
# rather than an untyped UnicodeDecodeError crash (AD-12).
_CSV_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def _read_csv_text(file_path: Path) -> str:
    """Read a CSV file as text, tolerating non-UTF-8 bank exports (cp1252 / latin-1)."""
    for enc in _CSV_ENCODINGS:
        try:
            return file_path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return file_path.read_text(encoding="latin-1", errors="replace")  # defensive; unreachable


@dataclass(frozen=True)
class BankCSVProfile:
    """Maps one bank's CSV columns onto the canonical schema.

    ``debit_col``/``credit_col`` are the split-amount columns; a row has a value in exactly
    one of them. Column names are matched normalized (stripped, lowercased).
    """

    name: str
    date_col: str
    description_col: str
    debit_col: str
    credit_col: str
    balance_col: str | None = None

    def required_columns(self) -> set[str]:
        cols = {self.date_col, self.description_col, self.debit_col, self.credit_col}
        if self.balance_col:
            cols.add(self.balance_col)
        return {_norm_header(c) for c in cols}


def _norm_header(name: str) -> str:
    # Collapse newlines and excess whitespace — pdfplumber splits multi-line header
    # cells with \n (e.g. "Transaction\nDate", "Withdrawal\nAmount (INR)").
    import re as _re
    return _re.sub(r"\s+", " ", name).strip().lower()


#: Known bank profiles, tried in registration order (FR-2.1: ≥2 Indian shapes).
PROFILES: tuple[BankCSVProfile, ...] = (
    BankCSVProfile(
        name="HDFC",
        date_col="Date",
        description_col="Narration",
        debit_col="Withdrawal Amt.",
        credit_col="Deposit Amt.",
        balance_col="Closing Balance",
    ),
    BankCSVProfile(
        name="SBI",
        date_col="Txn Date",
        description_col="Description",
        debit_col="Debit",
        credit_col="Credit",
        balance_col="Balance",
    ),
    BankCSVProfile(
        name="ICICI",
        date_col="Transaction Date",
        description_col="Transaction Remarks",
        debit_col="Withdrawal Amount (INR)",
        credit_col="Deposit Amount (INR)",
        balance_col="Balance (INR)",
    ),
)


def _clean_amount(raw: str) -> Decimal | None:
    """Parse a possibly grouped/symboled amount string to Decimal; blank → None."""
    text = raw.strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    if not text or text in {"-", "--"}:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise IngestionError(
            f"Couldn't read an amount from {raw!r}.", code="UNPARSEABLE_AMOUNT"
        )
    return value


def _is_valid_date(raw: str) -> bool:
    """True if ``raw`` parses as a statement date — the non-raising twin of normalize_date."""
    try:
        normalize_date(raw)
        return True
    except IngestionError:
        return False


#: Keyword sets for generic (unnamed-bank) column detection. Matched as substrings against
#: normalized header names. Order inside each tuple is a preference hint (earlier = stronger).
_GENERIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "date": ("transaction date", "txn date", "value date", "posting date", "date"),
    "description": (
        "narration", "transaction remarks", "remarks", "particulars",
        "description", "details",
    ),
    "debit": ("withdrawal", "debit", "dr amount", "paid out"),
    "credit": ("deposit", "credit", "cr amount", "paid in"),
    "balance": ("balance",),
}


def _find_column(header: set[str], keywords: tuple[str, ...], *, exclude: tuple[str, ...] = ()) -> str | None:
    """First header (by keyword preference, then shortest) containing a keyword, else None."""
    for kw in keywords:
        matches = [
            h for h in header if kw in h and not any(x in h for x in exclude)
        ]
        if matches:
            return min(matches, key=len)  # shortest = least-decorated header wins ties
    return None


def _generic_profile_or_none(header: set[str]) -> BankCSVProfile | None:
    """Build a profile for an unknown bank by matching column *roles* by keyword.

    This is what lets an arbitrary bank's split debit/credit statement parse without a
    hand-written profile: as long as the header names carry the usual words (date /
    narration|remarks / withdrawal|debit / deposit|credit / balance), the columns are found
    by meaning rather than exact string. Description keywords are excluded from the date match
    so "Transaction Remarks" is never mistaken for "Transaction Date".
    """
    date_col = _find_column(header, _GENERIC_KEYWORDS["date"], exclude=_GENERIC_KEYWORDS["description"])
    desc_col = _find_column(header, _GENERIC_KEYWORDS["description"])
    debit_col = _find_column(header, _GENERIC_KEYWORDS["debit"])
    credit_col = _find_column(header, _GENERIC_KEYWORDS["credit"])
    balance_col = _find_column(header, _GENERIC_KEYWORDS["balance"])
    if date_col and desc_col and debit_col and credit_col:
        return BankCSVProfile(
            name="Generic",
            date_col=date_col,
            description_col=desc_col,
            debit_col=debit_col,
            credit_col=credit_col,
            balance_col=balance_col,
        )
    return None


def _match_profile_or_none(header: set[str]) -> BankCSVProfile | None:
    """First named bank profile whose columns are all present; else a keyword-derived generic
    profile; else None (non-raising)."""
    for profile in PROFILES:
        if profile.required_columns() <= header:
            return profile
    return _generic_profile_or_none(header)


class CSVParser:
    """Parses a CSV bank statement into canonical transactions (StatementParser protocol)."""

    def parse(self, file_path: Path) -> list[Transaction]:
        reader = csv.DictReader(io.StringIO(_read_csv_text(Path(file_path))))
        if reader.fieldnames is None:
            raise IngestionError(
                "This CSV file has no header row I could read.", code="EMPTY_CSV"
            )
        header = {_norm_header(c) for c in reader.fieldnames if c is not None}
        profile = self._match_profile(header)
        # Build a lookup from normalized header -> original field name.
        field_by_norm = {
            _norm_header(c): c for c in reader.fieldnames if c is not None
        }
        transactions: list[Transaction] = []
        for row in reader:
            if not _has_content(row):
                continue
            txn = self._row_to_txn(row, profile, field_by_norm)
            if txn is not None:  # None = a structural row (footer/summary), skipped
                transactions.append(txn)
        return transactions

    @staticmethod
    def _match_profile(header: set[str]) -> BankCSVProfile:
        profile = _match_profile_or_none(header)
        if profile is None:
            raise UnsupportedFormatError(
                "I don't recognise this statement's columns yet. Supported CSV formats: "
                + ", ".join(p.name for p in PROFILES)
                + ". Try your bank's standard CSV export."
            )
        return profile

    @staticmethod
    def _row_to_txn(
        row: dict[str, str],
        profile: BankCSVProfile,
        field_by_norm: dict[str, str],
    ) -> Transaction | None:
        """Normalize one row, or return ``None`` if it is a structural (non-transaction) row.

        Returns ``None`` only for rows that carry neither a debit/credit amount nor a valid
        date — footer/summary rows like ``Opening Balance`` / ``Statement Total`` that a bank
        appends after the transactions. Skipping these drops no transaction, so AD-12's
        "never show fewer rows than were parsed" caveat is not triggered. A row that has a
        date OR an amount but can't be fully parsed still raises — that could be real data,
        and silently dropping it is exactly what AD-12 forbids.
        """
        def col(name: str) -> str:
            return row.get(field_by_norm[_norm_header(name)], "") or ""

        debit = _clean_amount(col(profile.debit_col))
        credit = _clean_amount(col(profile.credit_col))
        # In a split debit/credit layout a zero means "not this side" — many banks pad
        # the non-applicable column with 0.00 instead of leaving it blank. Collapse it to
        # absent so a padded row isn't misread as having both a debit and a credit. (Only
        # here — `balance_after` keeps 0.00 verbatim, since a ₹0 balance is legitimate.)
        if debit == 0:
            debit = None
        if credit == 0:
            credit = None
        if debit is not None and credit is not None:
            raise IngestionError(
                f"Row has both a debit and a credit amount, which I can't interpret: "
                f"{row!r}",
                code="AMBIGUOUS_DIRECTION",
            )
        if debit is not None:
            direction, amount = Direction.debit, abs(debit)
        elif credit is not None:
            direction, amount = Direction.credit, abs(credit)
        else:
            # No debit and no credit. If there's no valid date either, this is a structural
            # footer/summary row — skip it (not a transaction). If it DOES carry a valid
            # transaction date, it's a malformed transaction row — refuse honestly (AD-12)
            # rather than silently dropping a row that may represent real money movement.
            if not _is_valid_date(col(profile.date_col)):
                return None
            raise IngestionError(
                f"Row has a date but no debit or credit amount: {row!r}",
                code="MISSING_AMOUNT",
            )

        balance = _clean_amount(col(profile.balance_col)) if profile.balance_col else None

        return Transaction(
            date=normalize_date(col(profile.date_col)),
            description_raw=col(profile.description_col).strip(),
            amount=amount,
            direction=direction,
            balance_after=balance,
        )


def map_table(header_cells: list[str], data_rows: list[list[str]]) -> list[Transaction]:
    """Map an extracted table (a header row + data rows) to canonical transactions.

    Shared with the Story 2.3 PDF-table extractors (pdfplumber / camelot): they hand their
    extracted tables here so the *same* Indian-bank column mapping, direction resolution,
    and F1/F2 row handling used for CSVs are reused verbatim — no second, drifting copy.

    Returns ``[]`` when the header matches no known bank profile, so the PDF parser chain
    simply falls through to the next extractor. (This is the deliberate difference from the
    CSV entrypoint, which *raises* ``UnsupportedFormatError`` for an unrecognized CSV — a
    lone CSV of unknown shape is a user error to surface; one unrecognized table among a
    PDF's many is just noise to skip.)
    """
    names = [c for c in header_cells if c]
    profile = _match_profile_or_none({_norm_header(c) for c in names})
    if profile is None:
        return []
    field_by_norm = {_norm_header(c): c for c in names}
    transactions: list[Transaction] = []
    for cells in data_rows:
        # Key the row by the FULL header positions, not the filtered `names` — an empty
        # header cell (common in extracted PDF tables) must not shift the column-to-value
        # alignment. Empty/None header keys are simply never looked up (profile columns are
        # non-empty), so they are harmless.
        row = {
            header_cells[i]: (cells[i] if i < len(cells) and cells[i] is not None else "")
            for i in range(len(header_cells))
        }
        txn = CSVParser._row_to_txn(row, profile, field_by_norm)
        if txn is not None:  # None = a structural row (footer/summary), skipped
            transactions.append(txn)
    return transactions


def _has_content(row: dict[str, str]) -> bool:
    """Skip blank trailing rows (common in exported CSVs)."""
    return any((v or "").strip() for v in row.values())