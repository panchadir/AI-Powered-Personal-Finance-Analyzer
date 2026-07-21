"""PDF statement parser chain for text-based bank PDFs (Story 2.3, FR-2.2 / FR-2.4).

Implements the :class:`~services.ingestion.protocol.StatementParser` contract for PDFs as a
**fallback chain of extractors**, each an adapter over one extraction strategy:

    positional-text  ->  statementsparser  ->  pdfplumber-tables  ->  camelot

They are tried in order; the next is attempted only if the previous yields **no rows**
(the AC's "next tried only if previous yields no rows").

* :class:`PositionalColumnExtractor` is the **primary, bank-agnostic** path. It reads word
  coordinates (``page.extract_words``), locates the column headers (Date / Withdrawal|Debit /
  Deposit|Credit / Balance) by keyword, and assigns every value to a column by its *x*
  position. This is what makes "any bank, any layout" work: most Indian e-statements (ICICI,
  HDFC, SBI, Axis, Kotak, …) lay transactions out as *text in positional columns with no
  ruled table lines*, which grid/table extractors cannot see. Crucially, debit-vs-credit is
  decided by **which column** a number sits in — never by guessing from balance movement,
  which is unreliable (batch-posted NACH/mandate rows routinely have balance deltas that do
  not equal the row's own amount).
* :class:`StatementsparserExtractor` (bank-aware library) and the :class:`PdfplumberExtractor`
  / :class:`CamelotExtractor` table paths remain as fallbacks for ruled-table PDFs; their rows
  are mapped through the *same* Indian-bank column profiles the CSV parser uses (``map_table``),
  so there is one mapping, not three.

If every extractor comes back empty we distinguish two honest failures (AD-12):

* **no text layer at all** -> the PDF is a scanned image; raise :class:`ScannedPDFError`
  with the approved copy. Never a crash, never a wrong row count, never a generic toast.
* **text present but no transactions found** -> a text PDF we couldn't structure; a typed
  ``NO_TRANSACTIONS_FOUND`` refusal.

Extractors are injected (default = the real six) so the chain logic and the refusal paths
are unit-testable without a real PDF; the external libraries are imported lazily inside each
adapter's ``extract`` so importing this module stays cheap and side-effect free.
"""
from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from services.ingestion.csv_parser import map_table
from services.ingestion.errors import IngestionError, ScannedPDFError
from services.ingestion.normalize import normalize_date, normalize_description
from services.ingestion.schema import Transaction
from services.utils.enums import Direction

__all__ = [
    "PDFParser",
    "Extractor",
    "PositionalColumnExtractor",
    "StatementsparserExtractor",
    "ICICITextExtractor",
    "HDFCTableExtractor",
    "PdfplumberExtractor",
    "CamelotExtractor",
    "SCANNED_MESSAGE",
]

log = logging.getLogger(__name__)

SCANNED_MESSAGE = (
    "I can't read this one — it's a scanned image, not text. Try your bank's CSV export."
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _clean_dec(s: str) -> Decimal:
    return Decimal(s.replace(",", "").strip())


@runtime_checkable
class Extractor(Protocol):
    name: str

    def extract(self, file_path: Path) -> list[Transaction]:
        ...


# ---------------------------------------------------------------------------
# ICICI text extractor
# ICICI PDFs have grid lines only on the header row; all transaction data is
# in free-form plain text.  Pattern per transaction:
#   <merchant short name>          <- line before
#   <sno>  DD.MM.YYYY  amt1  [amt2]  balance
#   <full UPI narration lines>     <- lines after
# ---------------------------------------------------------------------------

_ICICI_TXN_RE = re.compile(
    r"^(\d+)\s+"
    r"(\d{2}\.\d{2}\.\d{4})\s+"
    r"([\d,]+\.\d{2})\s+"
    r"(?:([\d,]+\.\d{2})\s+)?"
    r"([\d,]+\.\d{2})\s*$"
)

_ICICI_FOOTER_MARKERS = (
    "Never share", "www.icici", "Dial your", "Please call",
    "Sincerely", "Legends", "RCHG", "This is a system",
)


class ICICITextExtractor:
    """Parses ICICI Bank PDFs via plain-text extraction."""

    name = "icici_text"

    def extract(self, file_path: Path) -> list[Transaction]:
        import pdfplumber

        with pdfplumber.open(str(file_path)) as pdf:
            first_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            if "ICICI" not in first_text.upper():
                return []
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        return self._parse_text(full_text)

    def _parse_text(self, text: str) -> list[Transaction]:
        lines = text.splitlines()
        transactions: list[Transaction] = []
        prev_balance: Decimal | None = None
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            m = _ICICI_TXN_RE.match(line)
            if not m:
                i += 1
                continue

            date_raw = m.group(2)
            a1 = _clean_dec(m.group(3))
            a2 = _clean_dec(m.group(4)) if m.group(4) else None
            balance = _clean_dec(m.group(5))

            # Merchant short name is the line immediately before the number line
            narration_parts = []
            if i > 0:
                prev = lines[i - 1].strip()
                if prev and not _ICICI_TXN_RE.match(prev) and not re.match(r"^\d{2}\.\d{2}\.\d{4}", prev):
                    narration_parts.append(prev)

            # Full UPI narration follows the number line
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or _ICICI_TXN_RE.match(nxt):
                    break
                if any(kw in nxt for kw in _ICICI_FOOTER_MARKERS):
                    break
                narration_parts.append(nxt)
                j += 1

            narration = " ".join(narration_parts).strip()

            if prev_balance is not None:
                direction = Direction.credit if balance > prev_balance else Direction.debit
            else:
                direction = Direction.debit

            if a2 is not None and prev_balance is not None:
                amount = abs(balance - prev_balance)
            else:
                amount = a1

            try:
                iso_date = normalize_date(date_raw)
            except IngestionError:
                i += 1
                continue

            transactions.append(Transaction(
                date=iso_date,
                description_raw=narration,
                amount=abs(amount),
                direction=direction,
                balance_after=balance,
            ))
            prev_balance = balance
            i = j

        return transactions


# ---------------------------------------------------------------------------
# HDFC table extractor
# HDFC PDFs have a proper table with headers:
#   Txn Date | Narration | Withdrawals | Deposits | Closing Balance
# BUT pdfplumber merges all rows into a single row — each cell contains
# newline-separated values for all transactions.  We split on newlines.
# ---------------------------------------------------------------------------

_HDFC_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")

_HDFC_REQUIRED_HEADERS = {"txn date", "narration", "withdrawals", "deposits", "closing balance"}


class HDFCTableExtractor:
    """Parses HDFC Bank PDFs by splitting the merged-row table pdfplumber extracts."""

    name = "hdfc_table"

    def extract(self, file_path: Path) -> list[Transaction]:
        import pdfplumber

        with pdfplumber.open(str(file_path)) as pdf:
            first_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            if "HDFC" not in first_text.upper():
                return []

            transactions: list[Transaction] = []
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    txns = self._parse_table(table)
                    transactions.extend(txns)

        return transactions

    def _parse_table(self, table: list[list[str | None]]) -> list[Transaction]:
        if not table:
            return []

        # Find header row
        header_idx = None
        col = {}
        for idx, row in enumerate(table):
            cells = [re.sub(r"\s+", " ", (c or "")).strip().lower() for c in row]
            if _HDFC_REQUIRED_HEADERS <= set(cells):
                header_idx = idx
                col = {cells[i]: i for i in range(len(cells))}
                break

        if header_idx is None:
            return []

        transactions: list[Transaction] = []
        for row in table[header_idx + 1:]:
            if not row:
                continue

            # HDFC merges all transactions into one cell per column, newline-separated.
            # Date/withdrawal/deposit/balance cells are 1:1 per transaction (one line each).
            # Narration spans multiple lines per transaction — split by detecting the
            # "Value Dt DD/MM/YYYY Ref <ref>" boundary line that ends every HDFC narration.
            dates_raw   = [l.strip() for l in (row[col["txn date"]] or "").splitlines()]
            narr_lines  = [l.strip() for l in (row[col["narration"]] or "").splitlines()]
            withdrawals = [l.strip() for l in (row[col["withdrawals"]] or "").splitlines()]
            deposits    = [l.strip() for l in (row[col["deposits"]] or "").splitlines()]
            balances    = [l.strip() for l in (row[col["closing balance"]] or "").splitlines()]

            date_vals = [d for d in dates_raw if _HDFC_DATE_RE.match(d)]
            if not date_vals:
                continue

            n = len(date_vals)

            # Split narration lines into n groups.
            # Each HDFC narration ends with a line matching "Value Dt DD/MM/YYYY Ref <ref>"
            # followed by the ref number on the next line. We use that as the group boundary.
            narr_groups = self._split_narrations(narr_lines, n)

            for k in range(n):
                narration = narr_groups[k] if k < len(narr_groups) else ""
                w_str = withdrawals[k] if k < len(withdrawals) else "0.00"
                d_str = deposits[k]    if k < len(deposits)    else "0.00"
                b_str = balances[k]    if k < len(balances)    else ""

                try:
                    withdrawal = _clean_dec(w_str) if w_str else Decimal("0")
                except Exception:
                    withdrawal = Decimal("0")
                try:
                    deposit = _clean_dec(d_str) if d_str else Decimal("0")
                except Exception:
                    deposit = Decimal("0")
                try:
                    balance = _clean_dec(b_str) if b_str else None
                except Exception:
                    balance = None

                if withdrawal == 0 and deposit == 0:
                    continue

                direction = Direction.credit if deposit > 0 else Direction.debit
                amount    = deposit if deposit > 0 else withdrawal

                try:
                    iso_date = normalize_date(date_vals[k])
                except IngestionError:
                    continue

                transactions.append(Transaction(
                    date=iso_date,
                    description_raw=narration,
                    amount=abs(amount),
                    direction=direction,
                    balance_after=balance,
                ))

        return transactions

    # "Value Dt DD/MM/YYYY Ref" — may or may not have the ref number on the same line
    _HDFC_VALUE_DT = re.compile(r"Value\s+Dt\s+\d{2}/\d{2}/\d{4}\s+Ref", re.I)
    # Inline ref: "Value Dt … Ref <digits>" all on one line
    _HDFC_VALUE_DT_INLINE = re.compile(r"Value\s+Dt\s+\d{2}/\d{2}/\d{4}\s+Ref\s+\d+", re.I)

    def _split_narrations(self, lines: list[str], n: int) -> list[str]:
        """Split flat narration lines into exactly n groups.

        HDFC narrations always end with a "Value Dt DD/MM/YYYY Ref" marker.
        Two forms:
          A) "... Value Dt 01/05/2026 Ref 189499104532"  — ref on same line → close here
          B) "... Value Dt 01/05/2026 Ref"               — ref on next line → close after next
        """
        if n == 1:
            return [" ".join(l for l in lines if l)]

        groups: list[list[str]] = []
        current: list[str] = []
        pending_ref = False  # waiting to consume the standalone ref line

        for line in lines:
            current.append(line)

            if pending_ref:
                # This line is the standalone ref number — close the group
                pending_ref = False
                if len(groups) < n - 1:
                    groups.append(current)
                    current = []
                if len(groups) == n - 1:
                    break
            elif self._HDFC_VALUE_DT_INLINE.search(line):
                # Ref is on this line — close immediately
                if len(groups) < n - 1:
                    groups.append(current)
                    current = []
                if len(groups) == n - 1:
                    break
            elif self._HDFC_VALUE_DT.search(line):
                # Ref is on the next line
                pending_ref = True

        groups.append(current)

        while len(groups) < n:
            groups.append([])

        return [" ".join(l for l in g if l).strip() for g in groups[:n]]


# ---------------------------------------------------------------------------
# Generic pdfplumber extractor (table-based, reuses CSV column profiles)
# ---------------------------------------------------------------------------

class PdfplumberExtractor:
    """Generic table extractor — wraps pdfplumber; rows mapped via map_table."""

    name = "pdfplumber"

    def extract(self, file_path: Path) -> list[Transaction]:
        import pdfplumber

        transactions: list[Transaction] = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if len(table) >= 2:
                        transactions.extend(map_table(table[0], table[1:]))
        return transactions


# ---------------------------------------------------------------------------
# Camelot extractor (last resort)
# ---------------------------------------------------------------------------

class CamelotExtractor:
    """Last-resort table extractor — wraps camelot; rows mapped via map_table."""

    name = "camelot"

    def extract(self, file_path: Path) -> list[Transaction]:
        import camelot

        transactions: list[Transaction] = []
        for table in camelot.read_pdf(str(file_path), pages="all"):
            rows = table.df.values.tolist()
            if len(rows) >= 2:
                transactions.extend(map_table(rows[0], rows[1:]))
        return transactions


# ---------------------------------------------------------------------------
# Primary statementparser extractor
# ---------------------------------------------------------------------------

# ─────────────────────────────────────────────────────────────────────────────
# Positional (coordinate-based) extractor — the general, bank-agnostic path.
# ─────────────────────────────────────────────────────────────────────────────

#: A money token: Indian-grouped decimal with 1–2 decimal places, optional trailing/leading
#: sign or "Dr"/"Cr" markers stripped before matching. e.g. "1,850.00", "355.72", "65.00".
#: A date such as "02.06.2026" deliberately does NOT match (it has two dots / four trailing
#: digits), so dates are never mistaken for amounts.
_MONEY_RE = re.compile(r"^\d[\d,]*\.\d{1,2}$")

#: Header keyword -> canonical column role. Matched case-insensitively as a substring of a
#: single header word. These words appear only in the header band of real statements (data
#: cells hold dates, amounts and UPI strings, none of which contain "withdrawal"/"balance"/…),
#: so keyword hits reliably locate the columns without a fragile fixed layout.
_HEADER_ROLE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("date", ("date",)),
    ("debit", ("withdrawal", "debit")),
    ("credit", ("deposit", "credit")),
    ("balance", ("balance",)),
)

#: Substrings that mark the non-transaction footer/legend region of a statement. A line
#: containing any of these ends description accumulation so footer text never leaks into a row.
_FOOTER_MARKERS: tuple[str, ...] = (
    "never share", "www.", "dial your", "please call", "sincerely", "sincerly",
    "legends for transactions", "this is a system", "statement of transactions",
    "opening balance", "closing balance", "page ",
)


def _money(text: str) -> Decimal | None:
    """Parse a positional cell into a Decimal amount, or ``None`` if it is not a money token."""
    t = text.strip().replace(",", "")
    # Some banks suffix Dr/Cr or a trailing minus to amounts; strip for the numeric test.
    t = re.sub(r"(?i)\s*(dr|cr)$", "", t).rstrip("-").strip()
    if not re.match(r"^\d+\.\d{1,2}$", t):
        return None
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def _is_txn_date(text: str) -> bool:
    """True if ``text`` is a statement transaction date (non-raising twin of normalize_date)."""
    try:
        normalize_date(text)
        return True
    except IngestionError:
        return False


class PositionalColumnExtractor:
    """Bank-agnostic PDF extractor that separates columns by *x* coordinate.

    Reads word boxes from each page, finds the Date / Withdrawal / Deposit / Balance columns
    from their header keywords, and assigns every value to a column by position. A transaction
    is a row whose Date column holds a valid date; the following continuation lines (wrapped
    narration) are folded into that transaction's description. Debit vs credit is decided by
    which numeric column the amount occupies — the only signal that stays correct when balances
    are batch-posted out of order.
    """

    name = "positional_text"

    def extract(self, file_path: Path) -> list[Transaction]:
        import pdfplumber  # lazy: heavy import only when actually parsing a PDF

        transactions: list[Transaction] = []
        centers: dict[str, float] | None = None
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
                if not words:
                    continue
                page_txns, centers = self._parse_page(words, centers)
                transactions.extend(page_txns)
        return transactions

    # ── page parsing ──────────────────────────────────────────────────────────

    def _parse_page(
        self, words: list[dict], carry_centers: dict[str, float] | None
    ) -> tuple[list[Transaction], dict[str, float] | None]:
        """Parse one page's words into transactions, reusing header columns across pages."""
        centers = self._header_centers(words) or carry_centers
        # A usable statement table needs a date column, a balance column, and at least one
        # amount column. Anything less isn't a transaction grid — skip the page (fall through).
        if not centers or "date" not in centers or "balance" not in centers or not (
            "debit" in centers or "credit" in centers
        ):
            return [], centers

        money_words = [w for w in words if _MONEY_RE.match(w["text"])]
        if not money_words:
            return [], centers
        clusters = self._cluster([w["x1"] for w in money_words], gap=18.0)
        role_of = self._label_clusters(clusters, centers)
        numeric_left = min(w["x0"] for w in money_words)
        date_cx = centers["date"]

        lines = self._group_lines(words)
        transactions: list[Transaction] = []
        pending: dict | None = None

        def flush() -> None:
            if pending and pending.get("amount") is not None:
                transactions.append(
                    Transaction(
                        date=pending["date"],
                        description_raw=normalize_description(" ".join(pending["desc"])),
                        amount=abs(pending["amount"]),
                        direction=pending["direction"],
                        balance_after=pending.get("balance"),
                    )
                )

        for line in lines:
            text = " ".join(w["text"] for w in line)
            date_word = self._date_word(line, date_cx, numeric_left)

            if date_word is not None:
                # A new transaction row starts here — emit the previous one first.
                flush()
                amount, direction, balance = self._amounts(line, clusters, role_of)
                pending = {
                    "date": normalize_date(date_word["text"]),
                    "desc": [
                        w["text"]
                        for w in self._description_tokens(line, date_word, date_cx, numeric_left)
                    ],
                    "amount": amount,
                    "direction": direction,
                    "balance": balance,
                }
                continue

            if pending is None:
                continue
            if any(m in text.lower() for m in _FOOTER_MARKERS):
                # Footer/legend reached — the current transaction block is over.
                flush()
                pending = None
                continue

            # Continuation line: fold wrapped narration in; back-fill amounts if the header
            # row carried none (some layouts drop the number onto the next visual line).
            if pending.get("amount") is None:
                amount, direction, balance = self._amounts(line, clusters, role_of)
                if amount is not None:
                    pending["amount"], pending["direction"] = amount, direction
                    pending["balance"] = balance
            pending["desc"].extend(
                w["text"] for w in self._description_tokens(line, None, date_cx, numeric_left)
            )

        flush()
        return transactions, centers

    # ── column geometry ─────────────────────────────────────────────────────────

    @staticmethod
    def _group_lines(words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
        """Group words into visual lines by their ``top`` coordinate, each sorted left→right."""
        ordered = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
        lines: list[list[dict]] = []
        current: list[dict] = []
        anchor: float | None = None
        for w in ordered:
            if anchor is None or abs(w["top"] - anchor) <= y_tol:
                current.append(w)
                anchor = w["top"] if anchor is None else anchor
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current, anchor = [w], w["top"]
        if current:
            lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    @staticmethod
    def _header_centers(words: list[dict]) -> dict[str, float] | None:
        """Map each column role to its header x-center, from the topmost matching header word.

        Ties (a role whose keyword appears more than once, e.g. "Transaction Date" and
        "Value Date") resolve to the leftmost — the transaction date sits before value date.
        """
        centers: dict[str, float] = {}
        for role, keywords in _HEADER_ROLE_KEYWORDS:
            best: tuple[float, float] | None = None  # (top, x0) of the chosen word
            best_cx = 0.0
            for w in words:
                low = w["text"].lower()
                if any(k in low for k in keywords):
                    cx = (w["x0"] + w["x1"]) / 2
                    key = (round(w["top"], 1), w["x0"])
                    if best is None or key < best:
                        best, best_cx = key, cx
            if best is not None:
                centers[role] = best_cx
        return centers or None

    @staticmethod
    def _cluster(values: list[float], gap: float) -> list[float]:
        """1-D cluster of right-edge x's into column centers (values within ``gap`` merge)."""
        if not values:
            return []
        ordered = sorted(values)
        groups: list[list[float]] = [[ordered[0]]]
        for v in ordered[1:]:
            if v - groups[-1][-1] <= gap:
                groups[-1].append(v)
            else:
                groups.append([v])
        return [sum(g) / len(g) for g in groups]

    @staticmethod
    def _label_clusters(clusters: list[float], centers: dict[str, float]) -> dict[float, str]:
        """Label each numeric column (by its center x) as debit / credit / balance.

        The rightmost column is the running balance. Remaining columns are amounts: with two
        of them, orientation comes from the header (whichever of Withdrawal/Deposit is further
        left owns the left column) — an ordering signal that stays correct regardless of how
        right-aligned numbers drift. With one, it is assigned to the nearer of the two headers.
        """
        roles: dict[float, str] = {}
        if not clusters:
            return roles
        ordered = sorted(clusters)
        roles[ordered[-1]] = "balance"
        amounts = ordered[:-1]
        debit_cx, credit_cx = centers.get("debit"), centers.get("credit")

        def nearer(x: float) -> str:
            if debit_cx is not None and credit_cx is not None:
                return "debit" if abs(x - debit_cx) <= abs(x - credit_cx) else "credit"
            return "debit" if debit_cx is not None else "credit"

        if len(amounts) >= 2 and debit_cx is not None and credit_cx is not None:
            left_role = "debit" if debit_cx <= credit_cx else "credit"
            right_role = "credit" if left_role == "debit" else "debit"
            roles[amounts[0]] = left_role
            roles[amounts[1]] = right_role
            for extra in amounts[2:]:
                roles[extra] = nearer(extra)
        else:
            for x in amounts:
                roles[x] = nearer(x)
        return roles

    # ── per-row extraction ──────────────────────────────────────────────────────

    @staticmethod
    def _date_word(
        line: list[dict], date_cx: float, numeric_left: float
    ) -> dict | None:
        """Return the transaction-date word on this line, if any.

        Restricted to the date column (near ``date_cx`` and left of the numeric columns) so a
        date embedded in a narration cell — e.g. "Int.Pd:30-03-2026 to 29-06-2026" — is never
        mistaken for a new transaction's date.
        """
        for w in line:
            cx = (w["x0"] + w["x1"]) / 2
            if cx < numeric_left and abs(cx - date_cx) <= 45 and _is_txn_date(w["text"]):
                return w
        return None

    def _amounts(
        self, line: list[dict], clusters: list[float], role_of: dict[float, str]
    ) -> tuple[Decimal | None, Direction, Decimal | None]:
        """Resolve (amount, direction, balance) from the money tokens on a line by column."""
        amount: Decimal | None = None
        direction = Direction.debit
        balance: Decimal | None = None
        debit_amt: Decimal | None = None
        credit_amt: Decimal | None = None
        for w in line:
            value = _money(w["text"])
            if value is None:
                continue
            role = role_of.get(self._nearest(w["x1"], clusters))
            if role == "balance":
                balance = value
            elif role == "credit":
                credit_amt = value
            elif role == "debit":
                debit_amt = value
        # A row has a value in exactly one of the two amount columns. If a layout ever fills
        # both, prefer the non-zero one; a genuine both-non-zero row is not representable and
        # falls back to debit (logged upstream via the chain if it produces nothing useful).
        if credit_amt is not None and (debit_amt is None or debit_amt == 0):
            amount, direction = credit_amt, Direction.credit
        elif debit_amt is not None:
            amount, direction = debit_amt, Direction.debit
        elif credit_amt is not None:
            amount, direction = credit_amt, Direction.credit
        return amount, direction, balance

    @staticmethod
    def _nearest(x: float, clusters: list[float]) -> float:
        return min(clusters, key=lambda c: abs(c - x)) if clusters else x

    @staticmethod
    def _description_tokens(
        line: list[dict], date_word: dict | None, date_cx: float, numeric_left: float
    ) -> list[dict]:
        """Narration words on a line: right of the S.No/date, left of the numeric columns."""
        out: list[dict] = []
        for w in line:
            if w is date_word or _money(w["text"]) is not None:
                continue
            cx = (w["x0"] + w["x1"]) / 2
            if cx >= numeric_left:
                continue  # a numeric-column token that wasn't money (rare) — skip
            # Drop the leftmost S.No integer column (left of the date column).
            if cx < date_cx - 10 and w["text"].isdigit():
                continue
            out.append(w)
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Library / table fallbacks.
# ─────────────────────────────────────────────────────────────────────────────


class StatementsparserExtractor:
    """Bank-aware fallback extractor — wraps the ``statementparser`` library."""

    name = "statementsparser"

    def extract(self, file_path: Path) -> list[Transaction]:
        import statementparser

        # categorize/verify_balance off: we run our own Tier-1/2 categorization (Epic 3) and
        # don't want the library's balance check to raise on a benign mismatch.
        try:
            from statementparser.parsers.base import DATE_FORMATS
            if "%d.%m.%Y" not in DATE_FORMATS.get("ICICI", []):
                DATE_FORMATS.setdefault("ICICI", []).insert(0, "%d.%m.%Y")
                DATE_FORMATS.setdefault("ICICI", []).insert(1, "%d.%m.%y")
        except Exception:
            pass

        statement = statementparser.parse(
            str(file_path), categorize=False, verify_balance=False
        )
        return [self._to_canonical(t) for t in statement.transactions]

    @staticmethod
    def _to_canonical(t: object) -> Transaction:
        direction = (
            Direction.debit if getattr(t.type, "value", t.type) == "DEBIT" else Direction.credit
        )
        return Transaction(
            date=t.date.isoformat(),
            description_raw=(t.narration or t.description or "").strip(),
            amount=abs(t.amount),
            direction=direction,
            balance_after=t.closing_balance,
        )


# ---------------------------------------------------------------------------
# Text layer probe
# ---------------------------------------------------------------------------

def _pdf_has_text_layer(file_path: Path) -> bool:
    import pdfplumber
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            if (page.extract_text() or "").strip():
                return True
    return False


# ---------------------------------------------------------------------------
# PDFParser — runs the chain
# ---------------------------------------------------------------------------

class PDFParser:
    """Runs the extractor chain and produces canonical transactions."""

    def __init__(
        self,
        extractors: list[Extractor] | None = None,
        text_probe: Callable[[Path], bool] | None = None,
    ) -> None:
        # Collaborators injected (project-context DI rule) so the chain + refusal paths are
        # testable without a real PDF or the heavy libraries. The positional extractor leads:
        # it handles the common text-in-columns layout across banks; the library and table
        # extractors back it up for ruled-table PDFs it can't find headers in.
        self._extractors: list[Extractor] = (
            list(extractors)
            if extractors is not None
            else [
                PositionalColumnExtractor(),
                StatementsparserExtractor(),
                ICICITextExtractor(),
                HDFCTableExtractor(),
                PdfplumberExtractor(),
                CamelotExtractor(),
            ]
        )
        self._has_text_layer = text_probe if text_probe is not None else _pdf_has_text_layer

    def parse(self, file_path: Path) -> list[Transaction]:
        path = Path(file_path)
        for extractor in self._extractors:
            try:
                rows = extractor.extract(path)
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "PDF extractor %r failed on %s: %s",
                    getattr(extractor, "name", extractor),
                    path,
                    exc,
                )
                continue
            if rows:
                log.info("PDF extractor %r parsed %d rows from %s", extractor.name, len(rows), path.name)
                return rows

        if not self._has_text_layer(path):
            raise ScannedPDFError(SCANNED_MESSAGE)
        raise IngestionError(
            "I couldn't find any transactions in this PDF. If it's a bank statement, "
            "try your bank's CSV export instead.",
            code="NO_TRANSACTIONS_FOUND",
        )
