"""Typed ingestion errors — honest refusal instead of silent wrong data (AD-12).

Any parsing failure (unsupported layout, scanned image, empty/corrupt file, partial
extraction) raises a subclass of :class:`IngestionError` carrying a plain-language,
user-facing ``message`` and a stable ``code``. The ``rx.State`` upload handler catches
these and surfaces the message directly — it never re-raises a bare ``Exception`` to the
UI, and never shows a transaction table with fewer rows than were actually parsed without
an explicit caveat.

Story 2.2 introduces the base plus the CSV-format cases. The PDF chain (Story 2.3) and the
edge-case hardening pass (Story 8.1) add ``NO_TEXT_LAYER`` / ``EMPTY_STATEMENT`` and the
rest of the code vocabulary against this same base — one hierarchy, one catch site.
"""
from __future__ import annotations

__all__ = ["IngestionError", "UnsupportedFormatError", "ScannedPDFError", "EmptyStatementError"]


class IngestionError(Exception):
    """Base class for every ingestion failure surfaced to the user (AD-12).

    ``message`` is safe to show verbatim; ``code`` is a stable machine token the UI and
    tests can branch on without string-matching the copy.
    """

    #: Default stable code; subclasses override.
    code: str = "INGESTION_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class UnsupportedFormatError(IngestionError):
    """The file's column layout matches no known bank profile."""

    code = "UNSUPPORTED_CSV_FORMAT"


class ScannedPDFError(IngestionError):
    """A scanned/image PDF with no text layer — cannot be read, only honestly refused.

    Carries the approved user-facing copy (FR-2.4 / ux-spec) by default. Story 8.1's
    edge-case pass reuses this same ``NO_TEXT_LAYER`` code.
    """

    code = "NO_TEXT_LAYER"


class EmptyStatementError(IngestionError):
    """A file that parsed successfully but yielded zero transactions (AD-12, Story 8.1).

    Raised by the dispatch layer after a parse returns an empty list — so the UI shows
    an honest refusal rather than an empty transaction table.
    """

    code = "EMPTY_STATEMENT"