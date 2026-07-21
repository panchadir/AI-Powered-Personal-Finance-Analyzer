"""Pure summary-count logic for the upload flow's honest three-way split (Story 3.2 code-review
follow-up).

Extracted from ``finance_app/state/upload_state.py`` so the counting rule is unit-testable
without a running Reflex app — the same "extract pure function, test it" pattern Story 3.1's
review applied to the transactions page's chip/filter logic. Two reviewers independently read
the inline version as a bug before this extraction; the docstring below is the answer to "why
does a categorized row ever count as needs_review".
"""
from __future__ import annotations

from typing import NamedTuple, Sequence

from services.ingestion.schema import Transaction

#: A rule match at this confidence gets no badge on the transactions table
#: (``TransactionsState.NEEDS_REVIEW_THRESHOLD``, Story 3.1) — anything below it, including
#: the rules engine's own unrecognized-credit "Transfer In" fallback (confidence 0.5), is a
#: real categorization but still shown as needing review. The upload summary must agree with
#: that table, so this constant mirrors it rather than treating every non-UNCATEGORIZED row
#: as "by rules".
FULL_CONFIDENCE = 1.0


class CategorizationSummary(NamedTuple):
    rules: int
    ai: int
    need_review: int


def summarize_categorization(transactions: Sequence[Transaction]) -> CategorizationSummary:
    """Split a fully-categorized (Tier-1 + Tier-2) transaction list into the upload page's
    three honest counts.

    ``rules`` = confident (``category_confidence == 1.0``) Tier-1 matches. ``ai`` = Tier-2
    LLM matches (``category_source == 'llm'``). Everything else — genuinely
    ``UNCATEGORIZED`` rows *and* low-confidence rule fallbacks like "Transfer In" — counts as
    ``need_review``, consistent with the transactions table's badge threshold.
    """
    rules = sum(
        1 for t in transactions
        if t.category_source == "rule" and t.category_confidence == FULL_CONFIDENCE
    )
    ai = sum(1 for t in transactions if t.category_source == "llm")
    total = len(transactions)
    return CategorizationSummary(rules=rules, ai=ai, need_review=total - rules - ai)
