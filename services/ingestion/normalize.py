"""Field normalization + the canonical dedup key (Story 2.2 seam, used by 2.3 & 2.5).

The dedup key is decided **once, here** so CSV and PDF parsers — and the persistence-time
dedup in Story 2.5 — can never disagree on what "the same transaction" means:

    (user_id, date, amount, description_raw, balance_after)

normalized before comparison (project-context Seams):

* **date** → ISO ``'YYYY-MM-DD'`` (banks emit ``01/06/2026``, ``01-Jun-2026``, ``01 Jun 26``…);
* **description_raw** → trimmed and internal whitespace collapsed to single spaces;
* **amount** → ``abs()`` (sign is carried by ``direction``, not by the amount magnitude).

Keeping these here — not inside a specific parser — is what lets a re-upload of the same
statement, or an overlapping wider-range export, dedupe cleanly regardless of source format.
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from services.ingestion.errors import IngestionError
from services.ingestion.schema import Transaction

__all__ = ["normalize_date", "normalize_description", "dedup_key", "deduplicate"]

# Date formats seen across Indian bank CSV/PDF exports, tried in order.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",  # already ISO
    "%d/%m/%Y",  # 01/06/2026
    "%d-%m-%Y",  # 01-06-2026
    "%d/%m/%y",  # 01/06/26
    "%d-%m-%y",  # 01-06-26
    "%d-%b-%Y",  # 01-Jun-2026
    "%d %b %Y",  # 01 Jun 2026
    "%d/%b/%Y",  # 01/Jun/2026
    "%d-%b-%y",  # 01-Jun-26
    "%d %b %y",  # 01 Jun 26
)

_WHITESPACE = re.compile(r"\s+")


def normalize_date(raw: str) -> str:
    """Parse a bank date string into ISO ``'YYYY-MM-DD'``.

    Raises :class:`IngestionError` on an unparseable date rather than guessing — a
    silently-wrong date would corrupt both the dedup key and the STS income timeline.
    """
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise IngestionError(
        f"Couldn't read a date from {raw!r}. This statement's date format isn't one I "
        "recognise yet — try your bank's CSV export.",
        code="UNPARSEABLE_DATE",
    )


def normalize_description(raw: str) -> str:
    """Trim ends and collapse internal runs of whitespace to single spaces."""
    return _WHITESPACE.sub(" ", raw).strip()


def dedup_key(txn: Transaction) -> tuple[int | None, str, Decimal, str, Decimal | None]:
    """The canonical identity of a transaction for de-duplication.

    Components are normalized on the way in: ISO date (already normalized by the parser),
    collapsed description, and ``abs(amount)``. ``user_id`` participates so one user's rows
    never collide with another's (AD-4); it may be ``None`` pre-persistence.
    """
    return (
        txn.user_id,
        txn.date,
        abs(txn.amount),
        normalize_description(txn.description_raw),
        txn.balance_after,
    )


def deduplicate(txns: list[Transaction]) -> list[Transaction]:
    """Return ``txns`` with exact-duplicate rows removed, preserving first-seen order.

    This is the pure in-memory guarantee (a re-parse of the same file collapses to the
    original rows). Persistence-time dedup against already-stored rows is Story 2.5.
    """
    seen: set[tuple[int | None, str, Decimal, str, Decimal | None]] = set()
    unique: list[Transaction] = []
    for txn in txns:
        key = dedup_key(txn)
        if key in seen:
            continue
        seen.add(key)
        unique.append(txn)
    return unique