"""Story 3.2 code-review follow-up — ``summarize_categorization``'s honest three-way split.

Extracted from ``finance_app/state/upload_state.py`` (an ``rx.State`` handler, app-verify-only
per this codebase's established precedent) so the counting rule itself is unit-testable.
Two reviewers independently misread the inline version as a bug; these tests pin down the
actual, intentional contract.
"""
from __future__ import annotations

from decimal import Decimal

from services.categorize.summary import summarize_categorization
from services.ingestion.schema import Transaction
from services.utils.enums import Direction


def _txn(**kwargs) -> Transaction:
    defaults = dict(
        date="2026-06-01", description_raw="Merchant", amount=Decimal("100.00"),
        direction=Direction.debit,
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def test_confident_rule_match_counts_as_rules() -> None:
    txns = [_txn(category="Food & Dining", category_source="rule", category_confidence=1.0)]
    assert summarize_categorization(txns) == (1, 0, 0)


def test_llm_match_counts_as_ai() -> None:
    txns = [_txn(category="Shopping", category_source="llm", category_confidence=0.8)]
    assert summarize_categorization(txns) == (0, 1, 0)


def test_uncategorized_row_counts_as_need_review() -> None:
    txns = [_txn(category="Uncategorized", category_source=None, category_confidence=None)]
    assert summarize_categorization(txns) == (0, 0, 1)


def test_low_confidence_rule_fallback_counts_as_need_review_not_rules() -> None:
    """The rules engine's unrecognized-credit fallback (category='Transfer In',
    confidence=0.5) is a real categorization, but confidence < 1.0 means the
    transactions table shows its amber badge (Story 3.1's NEEDS_REVIEW_THRESHOLD) — the
    upload summary must agree, so it counts toward need_review, not rules."""
    txns = [_txn(
        direction=Direction.credit, category="Transfer In",
        category_source="rule", category_confidence=0.5,
    )]
    assert summarize_categorization(txns) == (0, 0, 1)


def test_mixed_batch_totals_correctly() -> None:
    txns = [
        _txn(category="Food & Dining", category_source="rule", category_confidence=1.0),
        _txn(category="Transport", category_source="rule", category_confidence=1.0),
        _txn(category="Shopping", category_source="llm", category_confidence=0.8),
        _txn(category="Uncategorized", category_source=None, category_confidence=None),
    ]
    assert summarize_categorization(txns) == (2, 1, 1)


def test_empty_list_returns_all_zero() -> None:
    assert summarize_categorization([]) == (0, 0, 0)


def test_counts_always_sum_to_total() -> None:
    txns = [
        _txn(category="Food & Dining", category_source="rule", category_confidence=1.0),
        _txn(category="Shopping", category_source="llm", category_confidence=0.9),
        _txn(category="Transfer In", category_source="rule", category_confidence=0.5),
        _txn(category="Uncategorized", category_source=None, category_confidence=None),
    ]
    summary = summarize_categorization(txns)
    assert sum(summary) == len(txns)
