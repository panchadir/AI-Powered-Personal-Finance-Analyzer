"""Upload entry point: pick the right parser for a file and parse its bytes (Story 2.4).

The Reflex upload handler receives a filename + raw bytes; the actual parsing is business
logic and must live in ``services/`` (not the ``rx.State`` handler) per AD-2/AD-3. This
module is that seam: it dispatches to :class:`CSVParser` or :class:`PDFParser` by extension,
materializes the bytes to a temp file (both parsers take a ``Path``), parses, and cleans up.

Everything it can go wrong with surfaces as a typed :class:`IngestionError` (unknown
extension -> :class:`UnsupportedFormatError`; parse failures bubble up from the parsers,
including :class:`ScannedPDFError`), so the UI layer has exactly one exception family to
catch and translate to plain-language copy (AD-12). Framework-agnostic and unit-testable
without Reflex.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from services.ingestion.csv_parser import CSVParser
from services.ingestion.errors import IngestionError, UnsupportedFormatError
from services.ingestion.pdf_parser import PDFParser
from services.ingestion.protocol import StatementParser
from services.ingestion.schema import Transaction

__all__ = ["parse_statement", "parser_for", "extension_of"]

log = logging.getLogger(__name__)

_PARSERS: dict[str, type[StatementParser]] = {"csv": CSVParser, "pdf": PDFParser}


def extension_of(filename: str) -> str:
    """Lowercase extension without the dot (``"HDFC.CSV"`` -> ``"csv"``)."""
    parts = (filename or "").lower().rsplit(".", 1)
    return parts[1] if len(parts) > 1 else ""


def parser_for(filename: str) -> StatementParser:
    """Return the parser for ``filename``'s extension, or raise a typed refusal."""
    ext = extension_of(filename)
    parser_cls = _PARSERS.get(ext)
    if parser_cls is None:
        raise UnsupportedFormatError(
            f"I can only read PDF or CSV statements — not a .{ext or '?'} file. "
            "Try your bank's PDF or CSV export."
        )
    return parser_cls()


def parse_statement(filename: str, data: bytes) -> list[Transaction]:
    """Parse uploaded bytes into canonical transactions, dispatching by file type.

    Writes ``data`` to a temp file (closed before the parser opens it, so Windows file
    locking is a non-issue) and always deletes it. Any parse failure raises a typed
    :class:`~services.ingestion.errors.IngestionError` for the caller to translate.
    """
    parser = parser_for(filename)  # raises UnsupportedFormatError for unknown extensions
    suffix = "." + extension_of(filename)
    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        try:
            return parser.parse(tmp_path)
        except IngestionError:
            raise  # a typed refusal is already user-safe — pass it straight through
        except Exception as exc:  # noqa: BLE001
            # Guarantee the dispatcher's contract: only IngestionError ever escapes, so the
            # UI's single catch site holds (AD-12). Realistic triggers: a non-UTF-8 CSV
            # (UnicodeDecodeError), malformed CSV (csv.Error), or an unexpected parser bug.
            # Logged with context so a genuine bug is visible, never silently swallowed.
            log.exception("Unexpected failure parsing %s", filename)
            raise IngestionError(
                "We couldn't read this statement — it may be in an unexpected format or "
                "character encoding. Try your bank's standard PDF or CSV export.",
                code="PARSE_FAILED",
            ) from exc
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass