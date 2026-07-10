"""PDF statement parser chain for text-based bank PDFs (Story 2.3, FR-2.2 / FR-2.4).

Implements the :class:`~services.ingestion.protocol.StatementParser` contract for PDFs as a
**fallback chain of extractors**, each an adapter over one external tool:

    statementsparser  ->  pdfplumber  ->  camelot

They are tried in order; the next is attempted only if the previous yields **no rows**
(the AC's "next tried only if previous yields no rows"). ``statementparser`` is the primary
because it is bank-aware (it knows the HDFC/SBI/ICICI/Axis layouts and returns structured
transactions); pdfplumber and camelot are generic table extractors whose rows are mapped
through the *same* Indian-bank column profiles the CSV parser uses (``map_table``), so there
is one mapping, not three.

If every extractor comes back empty we distinguish two honest failures (AD-12):

* **no text layer at all** -> the PDF is a scanned image; raise :class:`ScannedPDFError`
  with the approved copy. Never a crash, never a wrong row count, never a generic toast.
* **text present but no transactions found** -> a text PDF we couldn't structure; a typed
  ``NO_TRANSACTIONS_FOUND`` refusal.

Extractors are injected (default = the real three) so the chain logic and the refusal paths
are unit-testable without a real PDF; the external libraries are imported lazily inside each
adapter's ``extract`` so importing this module stays cheap and side-effect free.

**Deferred (needs an asset that isn't in the repo yet):** the golden-file test that parses a
real text-based HDFC demo PDF to exactly 24 rows matching ``data/demo-data.json``. Tracked in
``deferred-work.md`` — the three adapters' end-to-end fidelity against a real HDFC layout is
verified there once the fixture exists.
"""
from __future__ import annotations

import logging
import re
from decimal import Decimal
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from services.ingestion.csv_parser import map_table
from services.ingestion.errors import IngestionError, ScannedPDFError
from services.ingestion.normalize import normalize_date
from services.ingestion.schema import Transaction
from services.utils.enums import Direction

__all__ = [
    "PDFParser",
    "Extractor",
    "StatementsparserExtractor",
    "PdfplumberExtractor",
    "CamelotExtractor",
    "ICICITextExtractor",
    "SCANNED_MESSAGE",
]

# ICICI transaction line: S.No  DD.MM.YYYY  [withdrawal]  [deposit]  balance
# e.g. "1 02.06.2026 65.00 21364.25" or "7 06.06.2026 1200.00 21289.25"
_ICICI_TXN_RE = re.compile(
    r"^(\d+)\s+"                          # S No.
    r"(\d{2}\.\d{2}\.\d{4})\s+"          # Transaction Date  DD.MM.YYYY
    r"([\d,]+\.\d{2})\s+"                # amount1 (withdrawal or deposit)
    r"(?:([\d,]+\.\d{2})\s+)?"           # amount2 optional (deposit when both present)
    r"([\d,]+\.\d{2})\s*$"              # closing balance
)


def _clean_dec(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


class ICICITextExtractor:
    """Parses ICICI Bank PDFs by reading plain text — needed because ICICI puts transaction
    data in free-form text rows, not in table cells that pdfplumber/camelot can grid-extract.

    Each transaction spans several lines:
      <merchant short name>
      <sno>  <DD.MM.YYYY>  [withdrawal]  [deposit]  <balance>
      <full UPI/narration line(s)>
    Direction is determined by comparing consecutive balances: balance goes up → credit.
    """

    name = "icici_text"

    def extract(self, file_path: Path) -> list[Transaction]:
        import pdfplumber

        full_text = []
        with pdfplumber.open(str(file_path)) as pdf:
            # Check if this is an ICICI statement before spending time parsing
            first_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            if "ICICI" not in first_text.upper():
                return []
            for page in pdf.pages:
                t = page.extract_text() or ""
                full_text.append(t)

        return self._parse_text("\n".join(full_text))

    def _parse_text(self, text: str) -> list[Transaction]:
        lines = text.splitlines()
        transactions: list[Transaction] = []
        prev_balance: Decimal | None = None

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = _ICICI_TXN_RE.match(line)
            if m:
                date_raw = m.group(2)
                a1 = _clean_dec(m.group(3))
                a2 = _clean_dec(m.group(4)) if m.group(4) else None
                balance = _clean_dec(m.group(5))

                # Collect narration: look back one line for merchant short name,
                # then forward for UPI detail lines until next txn or blank section
                narration_parts = []
                if i > 0:
                    prev = lines[i - 1].strip()
                    # Only include if it looks like a merchant name (not a date/number line)
                    if prev and not _ICICI_TXN_RE.match(prev) and not re.match(r"^\d{2}\.\d{2}\.\d{4}", prev):
                        narration_parts.append(prev)

                j = i + 1
                while j < len(lines):
                    nxt = lines[j].strip()
                    if not nxt or _ICICI_TXN_RE.match(nxt):
                        break
                    # Stop at footer markers
                    if any(kw in nxt for kw in ("Never share", "www.icici", "Dial your", "Please call", "Sincerely", "Legends", "RCHG", "This is a system")):
                        break
                    narration_parts.append(nxt)
                    j += 1

                narration = " ".join(narration_parts).strip()

                # Determine direction from balance movement
                if prev_balance is not None:
                    direction = Direction.credit if balance > prev_balance else Direction.debit
                else:
                    # First transaction: if two amounts present, figure out which is which;
                    # otherwise default to debit (most common first entry)
                    direction = Direction.debit

                # Amount: if two amounts given, pick the non-zero one matching direction
                if a2 is not None:
                    # Both withdrawal and deposit columns have values — use balance delta
                    if prev_balance is not None:
                        delta = abs(balance - prev_balance)
                        amount = delta if delta > 0 else a1
                    else:
                        amount = a1
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
                continue
            i += 1

        return transactions

log = logging.getLogger(__name__)

#: Approved user-facing copy for a scanned/image PDF (FR-2.4 / ux-spec-mvp.md). Exact — the
#: em dash and wording are part of the microcopy contract; changing it fails acceptance.
SCANNED_MESSAGE = (
    "I can't read this one — it's a scanned image, not text. Try your bank's CSV export."
)


@runtime_checkable
class Extractor(Protocol):
    """One link in the PDF parser chain: an adapter over a single extraction tool."""

    name: str

    def extract(self, file_path: Path) -> list[Transaction]:
        """Return canonical transactions, or ``[]`` if this tool found none."""
        ...


class StatementsparserExtractor:
    """Primary, bank-aware extractor — wraps the ``statementparser`` library."""

    name = "statementsparser"

    def extract(self, file_path: Path) -> list[Transaction]:
        import statementparser  # lazy: heavy import only when actually parsing a PDF

        # Patch ICICI date formats to include DD.MM.YYYY (e.g. 02.06.2026) which the
        # library omits but ICICI PDFs use.
        try:
            from statementparser.parsers.base import DATE_FORMATS
            if "%d.%m.%Y" not in DATE_FORMATS.get("ICICI", []):
                DATE_FORMATS.setdefault("ICICI", []).insert(0, "%d.%m.%Y")
                DATE_FORMATS.setdefault("ICICI", []).insert(1, "%d.%m.%y")
        except Exception:
            pass

        # categorize/verify_balance off: we run our own Tier-1/2 categorization (Epic 3) and
        # don't want the library's balance check to raise on a benign mismatch.
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
            date=t.date.isoformat(),  # datetime.date -> ISO 'YYYY-MM-DD'
            description_raw=(t.narration or t.description or "").strip(),
            amount=abs(t.amount),
            direction=direction,
            balance_after=t.closing_balance,
        )


class PdfplumberExtractor:
    """Generic table extractor — wraps ``pdfplumber``; rows mapped via ``map_table``."""

    name = "pdfplumber"

    def extract(self, file_path: Path) -> list[Transaction]:
        import pdfplumber  # lazy

        transactions: list[Transaction] = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if len(table) >= 2:  # header + at least one data row
                        transactions.extend(map_table(table[0], table[1:]))
        return transactions


class CamelotExtractor:
    """Last-resort table extractor — wraps ``camelot``; rows mapped via ``map_table``."""

    name = "camelot"

    def extract(self, file_path: Path) -> list[Transaction]:
        import camelot  # lazy

        transactions: list[Transaction] = []
        for table in camelot.read_pdf(str(file_path), pages="all"):
            rows = table.df.values.tolist()
            if len(rows) >= 2:
                transactions.extend(map_table(rows[0], rows[1:]))
        return transactions


def _pdf_has_text_layer(file_path: Path) -> bool:
    """True if any page yields extractable text — the scanned-vs-text discriminator."""
    import pdfplumber  # lazy

    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            if (page.extract_text() or "").strip():
                return True
    return False


class PDFParser:
    """Runs the extractor chain and produces canonical transactions (StatementParser)."""

    def __init__(
        self,
        extractors: list[Extractor] | None = None,
        text_probe: Callable[[Path], bool] | None = None,
    ) -> None:
        # Collaborators injected (project-context DI rule) so the chain + refusal paths are
        # testable without a real PDF or the heavy libraries.
        self._extractors: list[Extractor] = (
            list(extractors)
            if extractors is not None
            else [StatementsparserExtractor(), ICICITextExtractor(), PdfplumberExtractor(), CamelotExtractor()]
        )
        self._has_text_layer = text_probe if text_probe is not None else _pdf_has_text_layer

    def parse(self, file_path: Path) -> list[Transaction]:
        path = Path(file_path)
        for extractor in self._extractors:
            try:
                rows = extractor.extract(path)
            except Exception as exc:  # noqa: BLE001
                # A tool failing on a PDF it doesn't understand is expected — fall through to
                # the next link. Logged with context, never silently swallowed (AD-12); the
                # honest final refusal below is what reaches the user if all links fail.
                log.warning(
                    "PDF extractor %r failed on %s: %s",
                    getattr(extractor, "name", extractor),
                    path,
                    exc,
                )
                continue
            if rows:
                return rows

        # Every extractor came back empty — decide which honest refusal to raise.
        if not self._has_text_layer(path):
            raise ScannedPDFError(SCANNED_MESSAGE)
        raise IngestionError(
            "I couldn't find any transactions in this PDF. If it's a bank statement, "
            "try your bank's CSV export instead.",
            code="NO_TRANSACTIONS_FOUND",
        )