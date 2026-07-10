"""Single source of truth for the category taxonomy (AD-7).

Story 3.1 note: the Tier-1 rules engine (``services/categorize/rules.py``) already existed
(landed on this branch ahead of this story, ~90 merchant rules) with its own category
taxonomy — broader and more India-specific than the WDS prototype's 9-label set. Rather than
replace working, already-comprehensive rule coverage, this file canonicalizes the taxonomy
``rules.py`` actually uses, so it becomes the single declared source AD-7 requires (imported
by Story 3.2's Tier-2 LLM ``Literal`` enum and by the transactions page) instead of being
implicit string literals scattered across ``RULES``. ``tests/categorize/test_rules.py``
asserts every category ``RULES`` emits is a member of ``CATEGORIES`` below, so the two can
never silently drift apart.
"""
from __future__ import annotations

from typing import Literal

#: Every category a Tier-1 rule (or, from Story 3.2, the Tier-2 LLM) may assign. Order
#: mirrors ``services/categorize/rules.py``'s section order for readability.
CATEGORIES: tuple[str, ...] = (
    "Food & Dining",
    "Groceries",
    "Shopping",
    "Entertainment",
    "Travel & Transport",
    "Health & Medical",
    "Utilities",
    "Mobile & Recharge",
    "Insurance",
    "Loan & EMI",
    "Credit Card Payment",
    "Education",
    "Investments",
    "Salary",
    "Transfer In",
    "Bank Transfer",
    "UPI Transfer",
    "ATM & Cash",
    "Taxes",
)

#: Static type alias mirroring ``CATEGORIES`` for Story 3.2's structured-output enum.
Category = Literal[
    "Food & Dining",
    "Groceries",
    "Shopping",
    "Entertainment",
    "Travel & Transport",
    "Health & Medical",
    "Utilities",
    "Mobile & Recharge",
    "Insurance",
    "Loan & EMI",
    "Credit Card Payment",
    "Education",
    "Investments",
    "Salary",
    "Transfer In",
    "Bank Transfer",
    "UPI Transfer",
    "ATM & Cash",
    "Taxes",
]

#: The sentinel ``rules.py`` assigns when no rule matches — not a real category a rule or
#: the LLM deliberately chooses, so it is deliberately excluded from ``CATEGORIES``/``Category``.
UNCATEGORIZED = "Uncategorized"
