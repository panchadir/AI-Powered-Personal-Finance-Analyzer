"""Statement ingestion: StatementParser protocol, CSV/PDF parsers, normalizer, dedup.

Public API is exposed here; internal helpers are prefixed ``_``. Parsers normalize
to the canonical ``Transaction`` schema before returning (AD-6).

Landed so far (Epic 2):

* Story 2.1 — the canonical :class:`Transaction` schema and the :class:`StatementParser`
  protocol (the ingestion contract).
* Story 2.2 — the :class:`CSVParser` for Indian bank formats (HDFC, SBI), the shared
  :mod:`~services.ingestion.normalize` helpers + canonical dedup key, and the typed
  :class:`IngestionError` hierarchy (AD-12).
* Story 2.3 — the :class:`PDFParser` chain (statementsparser -> pdfplumber -> camelot) with
  an honest :class:`ScannedPDFError` refusal for image PDFs; table extractors reuse the
  CSV column mapping via ``map_table``. Persistence/dedup follow in 2.5.
"""
from services.ingestion.csv_parser import BankCSVProfile, CSVParser, map_table
from services.ingestion.dispatch import extension_of, parse_statement, parser_for
from services.ingestion.errors import (
    IngestionError,
    ScannedPDFError,
    UnsupportedFormatError,
)
from services.ingestion.normalize import (
    dedup_key,
    deduplicate,
    normalize_date,
    normalize_description,
)
from services.ingestion.pdf_parser import (
    SCANNED_MESSAGE,
    CamelotExtractor,
    Extractor,
    PDFParser,
    PdfplumberExtractor,
    StatementsparserExtractor,
)
from services.ingestion.persist import (
    PersistResult,
    filter_new_transactions,
    persist_transactions,
)
from services.ingestion.protocol import StatementParser
from services.ingestion.schema import Transaction

__all__ = [
    "StatementParser",
    "Transaction",
    "CSVParser",
    "BankCSVProfile",
    "map_table",
    "parse_statement",
    "parser_for",
    "extension_of",
    "persist_transactions",
    "filter_new_transactions",
    "PersistResult",
    "PDFParser",
    "Extractor",
    "StatementsparserExtractor",
    "PdfplumberExtractor",
    "CamelotExtractor",
    "SCANNED_MESSAGE",
    "IngestionError",
    "UnsupportedFormatError",
    "ScannedPDFError",
    "normalize_date",
    "normalize_description",
    "dedup_key",
    "deduplicate",
]