"""Tier-1 deterministic rules engine (Story 3.1, FR-3.1).

40+ India-relevant merchant/keyword rules applied via case-insensitive substring
matching on description_raw.  Returns category, category_source='rule',
category_confidence=1.0 for every matched transaction.

Rules are checked in order; first match wins.  Unmatched transactions get
category='Uncategorized', source='rule', confidence=0.0 so downstream code
(and the UI filter chip) can identify them as "needs review".

No LLM, no network call — runs in-process at parse time.

Story 3.3 ("Teach Me"): ``categorize_rules`` accepts an optional ``user_rules`` sequence of
``(pattern, category)`` pairs, checked *before* the built-in ``RULES`` table below — a user's
correction always wins over the default heuristic for that merchant. ``categorize_rules``
itself stays a pure, framework-agnostic function (AD-2/AD-14): loading a user's taught rules
from the DB is the caller's job (``services/categorize/teach_me.py::load_user_merchant_rules``,
called from ``finance_app/state/upload_state.py``, the composition root).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from services.ingestion.schema import Transaction
from services.utils.enums import CategorySource, Direction

__all__ = ["categorize_rules", "RULES"]


@dataclass(frozen=True)
class Rule:
    keywords: tuple[str, ...]  # any keyword match → category
    category: str


# ---------------------------------------------------------------------------
# Rule registry — India-relevant merchants/keywords, ordered by specificity.
# ---------------------------------------------------------------------------
RULES: tuple[Rule, ...] = (
    # --- Food & Dining ---
    Rule(("swiggy",), "Food & Dining"),
    Rule(("zomato",), "Food & Dining"),
    Rule(("dominos", "domino's"), "Food & Dining"),
    Rule(("pizza hut",), "Food & Dining"),
    Rule(("mcdonald", "mcdonalds"), "Food & Dining"),
    Rule(("kfc",), "Food & Dining"),
    Rule(("burger king",), "Food & Dining"),
    Rule(("cafe coffee", "ccd",), "Food & Dining"),
    Rule(("starbucks",), "Food & Dining"),
    Rule(("restaurant", "hotel", "dhaba", "biryani", "canteen", "eatery", "mess"), "Food & Dining"),

    # --- Groceries & Supermarket ---
    Rule(("bigbasket", "big basket"), "Groceries"),
    Rule(("blinkit", "grofers"), "Groceries"),
    Rule(("jiomart", "jio mart"), "Groceries"),
    Rule(("dmart", "d-mart"), "Groceries"),
    Rule(("reliance fresh", "reliance smart", "reliance retail"), "Groceries"),
    Rule(("more supermarket", "more megastore"), "Groceries"),
    Rule(("nature's basket", "natures basket"), "Groceries"),
    Rule(("supermarket", "grocery", "provision", "kirana"), "Groceries"),

    # --- Shopping & E-Commerce ---
    Rule(("amazon",), "Shopping"),
    Rule(("flipkart",), "Shopping"),
    Rule(("myntra",), "Shopping"),
    Rule(("ajio",), "Shopping"),
    Rule(("snapdeal",), "Shopping"),
    Rule(("meesho",), "Shopping"),
    Rule(("nykaa",), "Shopping"),
    Rule(("tatacliq", "tata cliq"), "Shopping"),
    Rule(("shopsy",), "Shopping"),
    Rule(("reliance digital",), "Shopping"),

    # --- Entertainment & Subscriptions ---
    Rule(("netflix",), "Entertainment"),
    Rule(("hotstar", "disney+", "jiohotstar"), "Entertainment"),
    Rule(("amazon prime", "primevideo", "prime video"), "Entertainment"),
    Rule(("spotify",), "Entertainment"),
    Rule(("youtube premium",), "Entertainment"),
    Rule(("sonyliv", "sony liv"), "Entertainment"),
    Rule(("zee5",), "Entertainment"),
    Rule(("voot",), "Entertainment"),
    Rule(("bookmyshow", "book my show"), "Entertainment"),
    Rule(("pvr", "inox cinema"), "Entertainment"),
    Rule(("multiplex", "cinema", "theatre"), "Entertainment"),

    # --- Travel & Transport ---
    Rule(("ola",), "Travel & Transport"),
    Rule(("uber",), "Travel & Transport"),
    Rule(("rapido",), "Travel & Transport"),
    Rule(("irctc",), "Travel & Transport"),
    Rule(("makemytrip", "make my trip"), "Travel & Transport"),
    Rule(("goibibo",), "Travel & Transport"),
    Rule(("yatra",), "Travel & Transport"),
    Rule(("redbus", "red bus"), "Travel & Transport"),
    Rule(("indigo", "air india", "spicejet", "vistara", "akasa"), "Travel & Transport"),
    Rule(("metro card", "metro rail", "nmmc", "bmtc", "best bus"), "Travel & Transport"),
    Rule(("fastag", "fast tag"), "Travel & Transport"),
    Rule(("petrol", "diesel", "fuel", "hp petro", "bharat petro", "indian oil"), "Travel & Transport"),

    # --- Health & Medical ---
    Rule(("apollo pharmacy", "apollo pharma"), "Health & Medical"),
    Rule(("medplus",), "Health & Medical"),
    Rule(("netmeds",), "Health & Medical"),
    Rule(("1mg", "tata 1mg"), "Health & Medical"),
    Rule(("pharmeasy",), "Health & Medical"),
    Rule(("hospital", "clinic", "diagnostic", "pathology", "pharmacy", "medical"), "Health & Medical"),
    Rule(("dr.", "doctor",), "Health & Medical"),

    # --- Utilities & Bills ---
    Rule(("electricity", "bescom", "msedcl", "tsspdcl", "apspdcl", "epdcl", "eastern power", "tata power"), "Utilities"),
    Rule(("water board", "water supply", "bwssb", "bmc water"), "Utilities"),
    Rule(("gas bill", "indane", "bharat gas", "hp gas", "mahanagar gas", "igl"), "Utilities"),
    Rule(("broadband", "internet", "wifi", "jio fiber", "airtel fiber", "act fibernet"), "Utilities"),
    Rule(("bbps",), "Utilities"),

    # --- Mobile & Recharge ---
    Rule(("jio recharge", "airtel recharge", "vi recharge", "bsnl recharge"), "Mobile & Recharge"),
    Rule(("mobile recharge", "prepaid recharge", "phone recharge"), "Mobile & Recharge"),
    Rule(("google pay recharge", "gpay recharge", "paytm recharge"), "Mobile & Recharge"),

    # --- Insurance ---
    Rule(("lic of india", "lic premium", "life insurance"), "Insurance"),
    Rule(("hdfc life", "icici prulife", "sbi life", "bajaj allianz life"), "Insurance"),
    Rule(("star health", "niva bupa", "care health", "health insurance"), "Insurance"),
    Rule(("vehicle insurance", "bike insurance", "car insurance", "motor insurance"), "Insurance"),
    Rule(("insurance premium", "policy premium"), "Insurance"),

    # --- Loan & EMI ---
    Rule(("emi", "loan emi", "home loan", "car loan", "personal loan"), "Loan & EMI"),
    Rule(("nach", "ach d-", "nach d-", "nach trxn"), "Loan & EMI"),
    Rule(("lnpy", "linked loan"), "Loan & EMI"),
    Rule(("etmoney",), "Loan & EMI"),

    # --- Credit Card Payment ---
    Rule(("cc bill", "credit card bill", "ccbill", "mycards cc", "cc billpay"), "Credit Card Payment"),
    Rule(("pavc", "pay visa card"), "Credit Card Payment"),

    # --- Education ---
    Rule(("school fee", "college fee", "tuition fee", "edtech", "byjus", "byju's", "unacademy", "vedantu", "coursera"), "Education"),
    Rule(("educati", "education", "university", "institute"), "Education"),

    # --- Investments & Savings ---
    Rule(("mutual fund", "sip", "demat", "zerodha", "groww", "kuvera", "coin by zerodha"), "Investments"),
    Rule(("nps", "national pension", "ppf", "public provident"), "Investments"),
    Rule(("eba", "icici direct", "hdfc securities", "motilal oswal", "angel broking"), "Investments"),
    Rule(("sgb", "sovereign gold bond"), "Investments"),

    # --- Salary & Income ---
    Rule(("salary", "sal credit", "payroll", "wages"), "Salary"),
    Rule(("neft cr", "imps cr", "rtgs cr"), "Transfer In"),

    # --- Transfers ---
    Rule(("imps", "neft", "rtgs", "inft"), "Bank Transfer"),
    Rule(("upi", "gpay", "phonepe", "paytm", "bhim"), "UPI Transfer"),

    # --- ATM & Cash ---
    Rule(("atm withdrawal", "cash withdrawal", "atm-", "atm wd"), "ATM & Cash"),

    # --- Taxes ---
    Rule(("income tax", "tds", "gst", "dtax", "direct tax", "tax payment"), "Taxes"),
)

_NEEDS_REVIEW = "Uncategorized"


def _match(description: str, user_rules: Sequence[tuple[str, str]] = ()) -> tuple[str, float]:
    """Return (category, confidence) for a description string.

    ``user_rules`` (Story 3.3, "Teach Me") is checked first — a user's own correction always
    wins over the built-in ``RULES`` table for that merchant. A user-rule match is full
    confidence, same as a built-in match: the user is now the authority.
    """
    text = description.lower()
    for pattern, category in user_rules:
        needle = pattern.strip().lower()
        # Defensive: a blank/whitespace pattern would otherwise be "contained in" every
        # description and match everything (belt-and-suspenders — the write path in
        # teach_me.py already refuses to store one).
        if not needle:
            continue
        if needle in text:
            return category, 1.0
    for rule in RULES:
        if any(kw in text for kw in rule.keywords):
            return rule.category, 1.0
    return _NEEDS_REVIEW, 0.0


def categorize_rules(
    transactions: Sequence[Transaction], user_rules: Sequence[tuple[str, str]] = ()
) -> list[Transaction]:
    """Apply Tier-1 rules to every transaction; return new Transaction objects with
    category/category_source/category_confidence filled.

    ``user_rules`` is an optional sequence of ``(pattern, category)`` pairs — a user's
    "Teach Me" corrections (Story 3.3), checked before the built-in ``RULES`` table. Pure and
    framework-agnostic (AD-2/AD-14): loading a user's rules from the DB is the caller's job.

    Credits (salary/transfer-in) are handled by the rules above; unrecognized
    credits default to 'Income / Transfer In' rather than 'Uncategorized' so
    the dashboard income detection has something to work with.
    """
    result: list[Transaction] = []
    for txn in transactions:
        category, confidence = _match(txn.description_raw, user_rules)

        # Unrecognized credits default to Transfer In rather than Uncategorized
        if category == _NEEDS_REVIEW and txn.direction == Direction.credit:
            category = "Transfer In"
            confidence = 0.5

        result.append(txn.with_fields(
            category=category,
            category_source=CategorySource.rule.value,
            category_confidence=confidence,
        ))
    return result
