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
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from services.ingestion.csv_parser import map_table
from services.ingestion.errors import IngestionError, ScannedPDFError
from services.ingestion.schema import Transaction
from services.utils.enums import Direction

__all__ = [
    "PDFParser",
    "Extractor",
    "StatementsparserExtractor",
    "PdfplumberExtractor",
    "CamelotExtractor",
    "SCANNED_MESSAGE",
]

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
            else [StatementsparserExtractor(), PdfplumberExtractor(), CamelotExtractor()]
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