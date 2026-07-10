"""Story 3.1 · AC #1, #2, #9 — Tier-1 rules engine (``services/categorize/rules.py``).

**Adapted scope (documented decision, 2026-07-10):** ``services/categorize/rules.py``
already existed on this branch before Story 3.1 was drafted — a ~90-rule engine with its
own India-specific category taxonomy (Salary, Loan & EMI, Travel & Transport, Groceries,
UPI Transfer, Bank Transfer, ...), landed ahead of this story rather than the WDS
prototype's narrower 9-category set the story was originally written against. Per an
explicit product decision (AskUserQuestion, 2026-07-10): **keep the existing engine**
rather than replace it, and adapt this story's tests to its actual behavior instead of
the story's original 18-rule-matched/3-AI/3-needs-review split.

Running the existing engine against the 24-row demo fixture (``data/demo-data.json``)
originally rule-matched **22** rows (not 18) — it already recognized ``BigBasket``,
``Amazon``, ``Myntra``, and the ``UPI-``/``NEFT-``/``PhonePe`` reference-number rows that an
earlier draft of this story assumed would be reserved for Tier-2 AI / permanent
needs-review. Only ``Tata Power`` and ``Reliance Digital`` fell through as unmatched.

**Code-review follow-up (2026-07-10, user decision):** a review flagged that gap as a likely
oversight — the engine already had an extensive Utilities section covering regional
electricity boards, so a bare "Tata Power" rule was a natural, low-risk addition; the user
chose to close it rather than defer it. Two rules were added: ``"tata power"`` → Utilities
(alongside the existing regional-discom keywords) and ``"reliance digital"`` → Shopping
(it's an electronics retailer, not a utility, despite the "Reliance" name overlap with the
existing Reliance Fresh/Smart/Retail *grocery* rules — kept as a distinct, more-specific
keyword so it doesn't collide with those). The demo fixture now rule-matches **24/24**.
This still supersedes the "18 by rules · 3 by AI · 3 need your help" figure quoted in
Epic 2 Story 2.4's AC — Story 3.2 (Tier-2) will have nothing left to categorize on this
fixture, which is a fine outcome (Tier-2 exists for statements Tier-1 can't fully cover).
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest

from services.categorize.rules import RULES, categorize_rules
from services.categorize.schema import CATEGORIES, Category, UNCATEGORIZED
from services.ingestion.schema import Transaction
from services.utils.enums import CategorySource, Direction

DEMO_FIXTURE = Path(__file__).resolve().parent.parent.parent / "data" / "demo-data.json"

# A representative sample of expected category assignments (not exhaustive) — guards against
# a rule-table refactor silently reshuffling categories while the matched *count* stays put.
_EXPECTED_CATEGORY = {
    "ACME Corp Salary": "Salary",
    "Zomato": "Food & Dining",
    "Swiggy": "Food & Dining",
    "HDFC EMI": "Loan & EMI",
    "Car Loan EMI": "Loan & EMI",
    "Personal Loan EMI": "Loan & EMI",
    "Netflix": "Entertainment",
    "PVR Cinemas": "Entertainment",
    "Uber": "Travel & Transport",
    "BEST Bus Pass": "Travel & Transport",
    "BigBasket": "Groceries",
    "Amazon": "Shopping",
    "Myntra": "Shopping",
    "UPI-8847213": "UPI Transfer",
    "PhonePe-Merchant": "UPI Transfer",
    "NEFT-REF-99120": "Bank Transfer",
    "Jio Recharge": "Mobile & Recharge",
    "Spotify": "Entertainment",
    "Starbucks": "Food & Dining",
    "Tata Power": "Utilities",
    "Reliance Digital": "Shopping",
}


@pytest.fixture(scope="module")
def demo_transactions() -> list[Transaction]:
    rows = json.loads(DEMO_FIXTURE.read_text(encoding="utf-8"))
    assert len(rows) == 24
    return [
        Transaction(
            date=r["date"],
            description_raw=r["description_raw"],
            amount=Decimal(r["amount"]),
            direction=Direction(r["direction"]),
        )
        for r in rows
    ]


@pytest.fixture(scope="module")
def categorized(demo_transactions) -> list[Transaction]:
    return categorize_rules(demo_transactions)


class TestRuleTable:
    def test_at_least_40_rules(self) -> None:
        """AC #1's literal '>=40 rules', enforced against the rule table directly — not just
        as a side effect of how many demo-fixture merchants happen to match."""
        assert len(RULES) >= 40

    def test_every_rule_category_is_declared_in_the_taxonomy(self) -> None:
        """AD-7 single-source-of-truth guard: rules.py and schema.py can never silently drift."""
        rule_categories = {rule.category for rule in RULES}
        undeclared = rule_categories - set(CATEGORIES)
        assert not undeclared, f"rules.py uses categories not declared in schema.CATEGORIES: {undeclared}"

    def test_category_literal_matches_categories_tuple(self) -> None:
        """AD-7 guard (code-review follow-up): CATEGORIES (tuple, runtime) and Category
        (Literal, static typing) are two hand-written copies of the same 19 strings — this
        catches a one-sided edit to either without needing a risky Literal[*tuple] unpacking
        trick in schema.py itself."""
        assert get_args(Category) == CATEGORIES


class TestCategorizeRulesOnDemoFixture:
    def test_returns_24_rows(self, categorized) -> None:
        assert len(categorized) == 24

    def test_all_24_rows_are_rule_matched(self, categorized) -> None:
        """AC #9 (adapted): with the "tata power"/"reliance digital" rules added (code-review
        follow-up, 2026-07-10), the engine now matches all 24/24 demo rows — see module
        docstring for the documented reason this changed from the original 22/24."""
        matched = [t for t in categorized if t.category != UNCATEGORIZED]
        assert len(matched) == 24
        for t in matched:
            assert t.category_confidence == 1.0

    def test_no_rows_are_uncategorized(self, categorized) -> None:
        unmatched = {t.description_raw for t in categorized if t.category == UNCATEGORIZED}
        assert unmatched == set()

    def test_every_row_has_category_source_rule(self, categorized) -> None:
        """This engine tags category_source='rule' on every row — matched or not; "needs
        review" is expressed via category/confidence, not a null category_source."""
        for t in categorized:
            assert t.category_source == CategorySource.rule.value

    @pytest.mark.parametrize("merchant,expected_category", list(_EXPECTED_CATEGORY.items()))
    def test_specific_category_assignments(self, categorized, merchant, expected_category) -> None:
        matches = [t for t in categorized if t.description_raw == merchant]
        assert matches, f"no demo row found for {merchant!r}"
        assert matches[0].category == expected_category

    def test_amount_and_direction_unchanged_by_categorization(self, demo_transactions, categorized) -> None:
        """categorize_rules must only add category fields — never touch the parsed data."""
        for original, result in zip(demo_transactions, categorized):
            assert result.amount == original.amount
            assert result.direction == original.direction
            assert result.date == original.date
