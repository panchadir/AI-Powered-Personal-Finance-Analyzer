---
baseline_commit: eecddd7b272053cb1a0045862003b28ffe2c15a3
---

# Story 3.1: Tier-1 Rules Engine & Transactions Table

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user who just uploaded a statement,
I want to see all my transactions instantly categorized by recognizable merchant/keyword rules with a clean table view,
so that the bulk of my data is ready to review without waiting for AI.

## Acceptance Criteria

Source: [epics.md — Story 3.1](../planning-artifacts/epics.md) (lines 453–471)

1. **Given** a parsed statement has been ingested, **When** the Tier-1 rules engine runs, **Then** ≥40 India-relevant merchant/keyword rules are applied (e.g. Swiggy→Food & Dining, Netflix→Subscriptions, EMI/HDFC→EMIs — see Dev Notes "Category taxonomy" for the exact WDS-aligned labels).
2. **And** matched transactions have `category_source='rule'` and `category_confidence=1.0`.
3. **And** the upload progress bar step 3 (`"Categorising by Rules"`) fires with a real row count when this step completes — completing the skeleton wired in Epic 2 Story 2.4.
4. **And** the transactions page renders a table with all transactions: date, merchant, amount, direction, category, badge.
5. **And** credit/income rows have a visually distinct green treatment (UX-DR14).
6. **And** filter chips are dynamically generated from actual parsed categories; a `"Needs review"` chip is always present when uncategorized count > 0.
7. **And** `"Needs review"` banner uses amber tone, not error red.
8. **And** the `"See my Dashboard"` CTA is always visible and enabled (sticky) — user is never blocked in the review loop.
9. **And** `pytest tests/categorize/test_rules.py` passes asserting the demo fixture's 18 rule-matched transactions.

## Tasks / Subtasks

- [x] **Task 1 — Materialize the missing demo fixture `data/demo-data.json`** (AC: #9; unblocks #1, #3)
  - [x] `data/` exists but is empty (only `.gitkeep`) — the canonical 24-transaction Priya fixture referenced by AC #9 and by Epic 2's Story 2.4 (`"18 categorized by rules · 3 by AI · 3 need your help"`) **does not exist yet**. It was deferred in Story 2.3 (see [deferred-work.md](./deferred-work.md) — "no real HDFC demo PDF fixture in the repo") because that deferral was about *PDF-parsing fidelity*, a different concern. This story only needs the **already-parsed canonical rows**, not a PDF — so build `data/demo-data.json` now as a flat JSON array of 24 objects with fields `date, description_raw, amount, direction` (`amount` unsigned string, `direction` `"credit"|"debit"` — matches `Transaction.amount`/`.direction`; no `balance_after`, no `category` — categorization is computed, never baked into the fixture). Source the exact date/merchant/amount values from the WDS prototype's `prototypes/01-priyas-first-honest-morning-Prototype/data/demo-data.json` `transactions` array (do not invent new values — the Dashboard/Insights/Copilot epics 4–7 will build on this same 24-row story and must stay internally consistent with that prototype's `safe_to_spend`/`spending_by_category`/`insights` numbers).
  - [x] Use this exact 24-row content (already converted: unsigned `amount`, canonical `direction`, prototype's signed amount → `abs()` + credit/debit):
    ```json
    [
      {"date": "2026-06-01", "description_raw": "ACME Corp Salary",  "amount": "65000.00", "direction": "credit"},
      {"date": "2026-06-02", "description_raw": "Zomato",            "amount": "640.00",   "direction": "debit"},
      {"date": "2026-06-03", "description_raw": "BEST Bus Pass",     "amount": "900.00",   "direction": "debit"},
      {"date": "2026-06-04", "description_raw": "UPI-8847213",       "amount": "1200.00",  "direction": "debit"},
      {"date": "2026-06-05", "description_raw": "Car Loan EMI",      "amount": "6500.00",  "direction": "debit"},
      {"date": "2026-06-06", "description_raw": "Netflix",           "amount": "649.00",   "direction": "debit"},
      {"date": "2026-06-07", "description_raw": "Swiggy",            "amount": "520.00",   "direction": "debit"},
      {"date": "2026-06-08", "description_raw": "BigBasket",         "amount": "2340.00",  "direction": "debit"},
      {"date": "2026-06-10", "description_raw": "Personal Loan EMI", "amount": "3000.00",  "direction": "debit"},
      {"date": "2026-06-11", "description_raw": "PVR Cinemas",       "amount": "900.00",   "direction": "debit"},
      {"date": "2026-06-12", "description_raw": "NEFT-REF-99120",    "amount": "1650.00",  "direction": "debit"},
      {"date": "2026-06-13", "description_raw": "Uber",              "amount": "410.00",   "direction": "debit"},
      {"date": "2026-06-14", "description_raw": "Amazon",            "amount": "1400.00",  "direction": "debit"},
      {"date": "2026-06-15", "description_raw": "HDFC EMI",          "amount": "8500.00",  "direction": "debit"},
      {"date": "2026-06-16", "description_raw": "Tata Power",        "amount": "1850.00",  "direction": "debit"},
      {"date": "2026-06-17", "description_raw": "Zomato",            "amount": "730.00",   "direction": "debit"},
      {"date": "2026-06-18", "description_raw": "PhonePe-Merchant",  "amount": "560.00",   "direction": "debit"},
      {"date": "2026-06-19", "description_raw": "Jio Recharge",      "amount": "399.00",   "direction": "debit"},
      {"date": "2026-06-20", "description_raw": "Spotify",           "amount": "119.00",   "direction": "debit"},
      {"date": "2026-06-21", "description_raw": "Starbucks",         "amount": "480.00",   "direction": "debit"},
      {"date": "2026-06-23", "description_raw": "Myntra",            "amount": "1200.00",  "direction": "debit"},
      {"date": "2026-06-25", "description_raw": "Reliance Digital",  "amount": "283.00",   "direction": "debit"},
      {"date": "2026-06-27", "description_raw": "Swiggy Instamart",  "amount": "690.00",   "direction": "debit"},
      {"date": "2026-06-29", "description_raw": "Uber",              "amount": "390.00",   "direction": "debit"}
    ]
    ```
  - [x] Of these 24 rows, **6 are intentionally NOT rule-matchable** — they are reserved by the prototype's own demo design for Epic 3's later tiers: `BigBasket`, `Amazon`, `Myntra` (Story 3.2's Tier-2 AI demo — must end up `category_source='llm'`), and `UPI-8847213`, `NEFT-REF-99120`, `PhonePe-Merchant` (permanently generic/reference-number descriptions — stay `needs_review` even after Tier-2, per the prototype's `"confidence": "needs_review"` tag). **Do not write a rule that matches any of these 6** — see Task 2's exclusion list.

- [x] **Task 2 — Category taxonomy: populate `services/categorize/schema.py`** (AC: #1, #2)
  - [x] The file is currently an empty placeholder ("Populated in Epic 3 (Story 3.2). Intentionally empty in Story 1.1.") — but Tier-1 rules need the same taxonomy Tier-2 will use in Story 3.2, so **populate it now**, not in 3.2, so both tiers import one source of truth (AD-7's "single source of truth" intent starts here).
  - [x] Define the 9-category taxonomy as a `Literal` (or `str, Enum` mirroring `services/utils/enums.py`'s style) with **exactly these string values** — sourced from the WDS prototype's `ALL_CATEGORIES` array (`01.4-transactions-table.html`), which is the UI source of truth per `project-context.md`'s "WDS Prototypes Are the UI Source of Truth" rule: `"Food & Dining"`, `"Transport"`, `"Bills & Utilities"`, `"Subscriptions"`, `"Shopping"`, `"Entertainment"`, `"EMIs"`, `"Income"`, `"Other"`.
  - [x] **Documented decision (epics-vs-WDS conflict, resolve by aligning to WDS — same precedent as Stories 1.3/1.4):** epics.md FR-3.1's own examples (`Swiggy→Dining`, `Netflix→Entertainment`, `EMI/HDFC→Loan Repayment`) use **different category labels** than the WDS prototype (`Food & Dining`, `Subscriptions`, `EMIs`). The WDS prototype is the shipped UI baseline the transactions page must visually match (filter chips, Teach Me chip picker, category icons all keyed off these exact 9 strings) — use the WDS labels, not the epics prose examples. Record this in Completion Notes.
  - [x] Export the taxonomy plus a `CATEGORIES: tuple[str, ...]` (or equivalent) that `services/categorize/rules.py` and the transactions page's filter-chip generator can both consume without re-declaring the list.

- [x] **Task 3 — Tier-1 rules engine** (AC: #1, #2, #9)
  - [x] New `services/categorize/rules.py`. Public API: a data-driven rule table (pattern, category) and a pure function `categorize_by_rules(transactions: Iterable[Transaction]) -> list[Transaction]` that returns each transaction unchanged if no rule matches, or `.with_fields(category=..., category_source=CategorySource.rule.value, category_confidence=1.0)` (use `Transaction.with_fields` — the frozen-dataclass update idiom, already used by `persist.py`) on a match. Match case-insensitively as a **substring** of `description_raw` (not `merchant_normalized` — no parser populates that field yet; matching `description_raw` is correct and sufficient for this story).
  - [x] Matching is **first-rule-wins** in table order — write more specific patterns (`"HDFC EMI"`, `"CAR LOAN"`) before anything that could be a substring of a broader/reserved term.
  - [x] Implement **at least these 43 rules** (≥40 AC + covers all 15 unique rule-matchable demo merchants). Do **not** add rules for `BIGBASKET`, `AMAZON`, `MYNTRA`, or any bare `UPI`/`NEFT`/`PHONEPE` catch-all — each would wrongly rule-match a transaction the demo fixture designed for Tier-2/needs-review, breaking AC #9's 18-count assertion:

    | Pattern (case-insensitive substring) | Category |
    | --- | --- |
    | SALARY | Income |
    | ZOMATO | Food & Dining |
    | SWIGGY | Food & Dining |
    | STARBUCKS | Food & Dining |
    | DOMINOS | Food & Dining |
    | MCDONALD | Food & Dining |
    | KFC | Food & Dining |
    | CAFE COFFEE DAY | Food & Dining |
    | ZEPTO | Food & Dining |
    | BLINKIT | Food & Dining |
    | UBER | Transport |
    | OLA | Transport |
    | RAPIDO | Transport |
    | BUS PASS | Transport |
    | IRCTC | Transport |
    | METRO RECHARGE | Transport |
    | FUEL STATION | Transport |
    | TATA POWER | Bills & Utilities |
    | RELIANCE DIGITAL | Bills & Utilities |
    | JIO | Bills & Utilities |
    | AIRTEL | Bills & Utilities |
    | VODAFONE | Bills & Utilities |
    | BESCOM | Bills & Utilities |
    | WATER BOARD | Bills & Utilities |
    | NETFLIX | Subscriptions |
    | SPOTIFY | Subscriptions |
    | HOTSTAR | Subscriptions |
    | SONYLIV | Subscriptions |
    | FLIPKART | Shopping |
    | AJIO | Shopping |
    | NYKAA | Shopping |
    | PVR | Entertainment |
    | INOX | Entertainment |
    | BOOKMYSHOW | Entertainment |
    | HDFC EMI | EMIs |
    | CAR LOAN | EMIs |
    | PERSONAL LOAN | EMIs |
    | HOME LOAN | EMIs |
    | LIC PREMIUM | EMIs |
    | ATM WITHDRAWAL | Other |
    | CASH WITHDRAWAL | Other |
    | BANK CHARGES | Other |
    | AMC CHARGES | Other |

  - [x] Every `category` value written by a rule must come from Task 2's `CATEGORIES` — do not hand-type a string literal that could drift from the taxonomy (import it).
  - [x] `services/categorize/__init__.py` currently only has a docstring stub — export `categorize_by_rules` (and Task 2's taxonomy) from it, mirroring `services/ingestion/__init__.py`'s public-API-in-`__init__.py` convention (project-context "Code Quality" rule).
  - [x] No new module needs registering with `tests/test_service_boundary.py` — it AST-scans all of `services/**/*.py` automatically; just don't import `reflex` or `finance_app` from `rules.py` or `schema.py`.

- [x] **Task 4 — Wire Tier-1 into the upload pipeline, replacing the Epic-2 skeleton** (AC: #3)
  - [x] `finance_app/state/upload_state.py`'s `_run_parse` currently hardcodes `self.rules = 0; self.ai = 0; self.need_review = self.total` after the parse (explicitly flagged in [deferred-work.md](./deferred-work.md) — "Upload progress steps 3 & 4 ... skeleton; the summary's rules/AI split is 0 until Epic 3" — **this is the exact gap this story closes**, half of it; step 4/AI stays 0 until Story 3.2).
  - [x] After `transactions = await asyncio.to_thread(parse_statement, name, data)` and before the persist block, call `transactions = categorize_by_rules(transactions)` (pure/sync — no `to_thread` needed, it's in-memory pattern matching, not I/O). This must happen **before** `persist_transactions`, so the rule-assigned `category`/`category_source`/`category_confidence` land in the DB in the same insert (persist.py's `_to_model` already copies those three fields — no persist.py change needed).
  - [x] Replace the skeleton counts: `self.rules = sum(1 for t in transactions if t.category_source == "rule")`; `self.need_review = self.total - self.rules`; leave `self.ai = 0` (Story 3.2's job — still accurate/honest since Tier-2 hasn't run).
  - [x] The step-3 (`"Categorising by Rules"`) `await asyncio.sleep(0.3)` placeholder in the `for key in ("rules", "ai")` loop can stay as the UI pacing beat, but it must now follow real categorization having already happened (not race it) — the count shown when step 3 completes must be the real `self.rules`, not a value computed later.
  - [x] Update the module docstring's "Categorization (the 'by rules' / 'by AI' split) is Epic 3" comment — it's now half-true; say Tier-1 is real, Tier-2 (AI) is still Story 3.2.

- [x] **Task 5 — Transactions page: real table** (AC: #4, #5, #6, #7, #8)
  - [x] `finance_app/pages/transactions.py` is currently a "Coming soon" placeholder. Rebuild it against the WDS prototype `prototypes/01-priyas-first-honest-morning-Prototype/01.4-transactions-table.html` — reuse its exact CSS class names from `shared/styles.css` (already served as `assets/wds.css` per the established reuse mechanism): `.txn-header-row`, `.pill-btn` (Dashboard CTA), `.banner` (needs-review banner, amber via existing `.banner` styling — do not use error/red classes), `.chip-group.chip--wrap` + `.chip`/`.chip.is-active` (filter chips), `.txn-list`/`.txn-row`, `.txn-icon`, `.txn-meta`/`.txn-merchant`/`.txn-cat-date`, `.txn-amount`/`.txn-amount.is-credit` (green — `#2f7d4f` — satisfies AC #5/UX-DR14), `.txn-badge`/`.txn-badge--review`/`.txn-badge--none`.
  - [x] **This story does NOT build the Teach Me correction panel** (`.teach-me` block, category picker, re-apply toggle) — that is Story 3.3's scope. Render rows as static (non-expanding) list items; clicking a badge/row does nothing yet. Do not build the AI (`.txn-badge--ai`, blue) badge state either — no transaction can be `category_source='llm'` until Story 3.2 exists; only two badge states are reachable in this story: no badge (rule-matched) and `.txn-badge--review` (unmatched → `category` is `None`/`category_source` is `None`, badge text `"?"`, `aria-label="Needs review"`). Story 3.4 formalizes the full confidence-threshold badge logic (FR-3.5) once Tier-2 exists.
  - [x] New `finance_app/state/transactions_state.py` (`TransactionsState(AuthState)`, following the one-state-per-page-domain convention). It must query `Transaction` rows scoped to `self.authenticated_user`'s `user_id` (AD-4 — no query without an explicit `user_id` filter), ordered by `date`. Filter-chip logic mirrors the prototype's JS exactly: `"All"` always first; `"Needs review (N)"` only when `N > 0`; then one chip per **distinct category actually present** in this user's rows (not the full static taxonomy — AC #6 says "dynamically generated from actual parsed categories").
  - [x] **Before writing `TransactionsState`, invoke the `reflex-docs` skill** (per `AGENTS.md` — mandatory for any Reflex state/component work) to confirm the current-version pattern for a computed/typed list of table rows in `rx.State` (e.g. an `rx.Base` row model + a `list[RowModel]` var, or the current idiomatic equivalent) and for computed vars over a DB-backed list — this story is the first to need a *structured list* of state (existing states like `UploadState` only hold scalars and `list[str]`), so don't guess the API from memory.
  - [x] The `"See my Dashboard"` CTA (`.pill-btn`) is **always enabled**, not `aria-disabled` like Upload's CTA — FR-3.9 says it must never block the user, unlike Story 2.4's parse-gated CTA. Link/navigate to `/dashboard`.

- [x] **Task 6 — Tests** (AC: #9)
  - [x] New `tests/categorize/__init__.py` + `tests/categorize/test_rules.py`.
  - [x] Load `data/demo-data.json` (Task 1), build 24 `Transaction` objects (`direction=Direction(row["direction"])`, `amount=Decimal(row["amount"])`), run `categorize_by_rules`.
  - [x] Assert exactly 18 have `category_source == "rule"` and `category_confidence == 1.0`; assert the other 6 (`BigBasket`, `Amazon`, `Myntra`, `UPI-8847213`, `NEFT-REF-99120`, `PhonePe-Merchant`) are untouched (`category is None`, `category_source is None`).
  - [x] Assert a handful of specific category assignments by merchant (e.g. `"ACME Corp Salary"` → `Income`, `"Zomato"` → `Food & Dining`, `"HDFC EMI"` → `EMIs`) so a future rule-table refactor can't silently reshuffle categories while keeping the count at 18.
  - [x] Assert `len(rules_table) >= 40` directly against the rule table (not just the demo-fixture side effect), so AC #1's literal "≥40 rules" is enforced independent of which merchants happen to appear in the demo data.
  - [x] Run the full suite (`pytest`) — no regressions. Reuse the existing SQLite-temp-engine harness pattern (`tests/security/test_registration.py`) if `TransactionsState`'s query logic needs a DB-level unit test separate from the `reflex run` app-verification.

### Review Findings

_Code review 2026-07-10 (3 parallel adversarial layers — Blind Hunter, Edge Case Hunter, Acceptance Auditor — on the Story-3.1-scoped diff: `services/categorize/schema.py`, `finance_app/pages/transactions.py`, `finance_app/state/transactions_state.py`, `data/demo-data.json`, `tests/categorize/test_rules.py`, `tests/test_transactions_state.py`). 1 decision-needed · 9 patches · 7 deferred · 4 dismissed as noise._

**Decision needed (resolved 2026-07-10):**
- [x] [Review][Decision] **`rules.py` has no rule for "Tata Power" or "Reliance Digital" despite an extensive Utilities section already covering regional discoms** [services/categorize/rules.py:104] — Blind Hunter's read: this looks like an oversight in the pre-existing engine, not a deliberate cut, and these are exactly the 2 merchants the demo fixture needs matched to reach a fully-categorized (24/0) split. **User decision: add the 2 rules.** Added `"tata power"` to the existing electricity `Rule` (Utilities) and a new `Rule(("reliance digital",), "Shopping")` (electronics retailer, not a utility — kept distinct from the existing Reliance Fresh/Smart/Retail *grocery* rules so it can't collide with them). Demo fixture now rule-matches 24/24. Updated `tests/categorize/test_rules.py` (`test_all_24_rows_are_rule_matched` replaces the old 22-count assertion; `test_no_rows_are_uncategorized` replaces the old 2-uncategorized assertion; both merchants added to `_EXPECTED_CATEGORY`) and the Story 2.4 epics.md note (22→24). Full suite 174 passed.

**Patches (applied 2026-07-10):**
- [x] [Review][Patch] **AD-7 taxonomy is duplicated, not unified** [services/categorize/schema.py:19,44] — `CATEGORIES` (tuple) and `Category` (`Literal`) are two independently hand-typed 19-string lists; the file's own docstring claims to be "the single declared source AD-7 requires," but nothing derives one from the other, and the only guard test checks `RULES` against `CATEGORIES`, never `CATEGORIES` against `Category`. (blind+edge+auditor, medium) — **Fixed:** added `test_category_literal_matches_categories_tuple` (asserts `typing.get_args(Category) == CATEGORIES`) to `tests/categorize/test_rules.py`.
- [x] [Review][Patch] **Uncaught `formatINR`/`formatDate` `ValueError` would crash the entire transactions page on one bad row** [finance_app/state/transactions_state.py:50-59] — both raise on invalid input (non-finite amount, non-ISO date); `_to_row` calls them unguarded inside `load_transactions`'s `rx.session()` block, so one malformed DB row fails the whole list load instead of degrading gracefully. Not reachable via the current ingestion path (parsers validate first), but a real robustness gap. (edge, medium) — **Fixed:** `load_user_transaction_rows` now wraps each row's `_to_row` call in `try/except ValueError`, logs it, and skips just that row (AD-12: degrade honestly, never fail the whole page for one bad row). New test `test_malformed_row_is_skipped_not_fatal`.
- [x] [Review][Patch] **No empty-state UI when a user has zero transactions** [finance_app/pages/transactions.py] — a first-time user (or anyone before Epic 2 ingestion) sees only the header + "All" chip + an empty list, no explanatory copy. (edge, medium) — **Fixed:** new `TransactionsState.has_transactions` var gates the chips/list vs. a plain "Upload a statement and your transactions will show up here" message.
- [x] [Review][Patch] **Same-day transactions have no deterministic secondary ordering** [finance_app/state/transactions_state.py:73] — `order_by(txn_model.date)` alone; multiple same-day transactions (common in real statements) have no tiebreaker, so display order isn't guaranteed stable across reloads. (edge, medium) — **Fixed:** `order_by(txn_model.date, txn_model.id)`. New test `test_same_day_rows_ordered_by_id_as_tiebreaker`.
- [x] [Review][Patch] **AC #6's chip/filter logic (`chip_items`, `visible_rows`, `needs_review_count`, `categories`) has zero automated test coverage** [finance_app/state/transactions_state.py:98,111,121] — all four are pure functions over `self.rows` (same shape as the already-tested `load_user_transaction_rows`) but were never extracted/tested the same way; the Completion Notes' claim that `reflex compile` covers this overstates what compile actually checks (it never executes this branching logic). (auditor, medium) — **Fixed:** extracted `needs_review_count`, `distinct_categories`, `build_chip_items`, `filter_rows` as module-level pure functions (the `@rx.var`s now just delegate); 19 new unit tests across `TestNeedsReviewCount`/`TestDistinctCategories`/`TestBuildChipItems`/`TestFilterRows`.
- [x] [Review][Patch] **Every transaction row is a real, focusable `<button>` with no `on_click`** [finance_app/pages/transactions.py:31-41] — copied from the prototype's Teach-Me-opening button verbatim, minus the behavior (correctly deferred to Story 3.3), leaving a keyboard-focusable, screen-reader-announced control that does nothing when activated. (blind, medium) — **Fixed:** row wrapper changed from `rx.el.button` to a plain `rx.el.div`; not focusable/interactive until Story 3.3 gives it real behavior.
- [x] [Review][Patch] **`rx.foreach` calls have no explicit `key=`** [finance_app/pages/transactions.py:90,96] — `chip_items`/`visible_rows` both change membership/order as the user clicks filter chips; without an explicit key, DOM reconciliation risks stale hover/focus state landing on the wrong row/chip. (blind, medium) — **Fixed:** `rx.foreach`'s `render_fn` returns elements with `key=item.key` (chips) / `key=row.id.to(str)` (rows) — this Reflex version takes `key` as a direct prop on the rendered element, not a `foreach` argument (verified empirically: `rx.foreach(iterable, render_fn)` has no `key=` parameter in `reflex==0.9.6.post1`).
- [x] [Review][Patch] **`.txn-icon` always renders empty — no category-keyed glyph** [finance_app/pages/transactions.py:33] — the WDS prototype renders a per-category emoji in this exact slot; the module docstring claims exact class-name parity with the prototype, but the icon column is a visible gap (the prototype's icon map is keyed to the WDS 9-category taxonomy, so this needs a new map for the ~19-category taxonomy actually in use). (blind, low) — **Fixed:** new `_CATEGORY_ICON` map (all 19 categories + `Uncategorized`) in `transactions_state.py`; `TxnRow` gained an `icon` field, computed in `_to_row`. New tests `test_row_icon_matches_category`, `test_uncategorized_row_gets_the_uncategorized_icon`.
- [x] [Review][Patch] **Empty `aria-label=""` on non-badge rows instead of `aria-hidden`** [finance_app/pages/transactions.py:53-58] — the prototype switches to `aria-hidden="true"` when there's no badge; an empty `aria-label` is worse for screen readers than properly hiding the element. (blind, low) — **Fixed:** `rx.cond` now branches the whole badge element — `aria-label="Needs review"` when shown, `aria-hidden="true"` with no label when not, matching the prototype.

Full suite re-run after all patches: **191 passed** (up from 174 — 17 new tests: 1 taxonomy-parity + 16 across malformed-row/tiebreaker/icon/chip/filter coverage); `reflex compile` → Success, 32/31.

**Deferred (logged to deferred-work.md):**
- [x] [Review][Defer] **`direction` equality uses a loose string match with no DB-level constraint** [finance_app/state/transactions_state.py:53] — deferred, pre-existing pattern from Story 1.2 (`direction` is a plain `str` column app-wide); not introduced or worsened by this diff, and the canonical `Transaction` dataclass already validates `direction` is a real `Direction` enum before persist.
- [x] [Review][Defer] **Reserved chip keys `"all"`/`"needs_review"` could collide with a future category value** [finance_app/state/transactions_state.py:33-34] — deferred, theoretical; no category in the current, curated `CATEGORIES` taxonomy matches either literal.
- [x] [Review][Defer] **Stale `active_filter` after a data change can leave no chip highlighted** [finance_app/state/transactions_state.py:94] — deferred, low-probability timing edge case; user can just click "All" again.
- [x] [Review][Defer] **`category == Uncategorized` with `confidence >= threshold` is a theoretical inconsistency** [finance_app/state/transactions_state.py:50-59] — deferred, not reachable via the current `rules.py` engine (it always pairs `Uncategorized` with `confidence 0.0`).
- [x] [Review][Defer] **Negative debit amounts would render with a bare `-` sign, no anomaly flag** [finance_app/state/transactions_state.py:56] — deferred, not reachable via the current ingestion path (parsers always store `abs(amount)` per AD-8).
- [x] [Review][Defer] **No pagination/limit on `load_user_transaction_rows`** [finance_app/state/transactions_state.py:66] — deferred per project-context's Performance Rules ("not as speculative gold-plating on a single-user local MVP"); revisit if/when transaction volume actually grows.
- [x] [Review][Defer] **`NEEDS_REVIEW_THRESHOLD = 1.0` will need revisiting once Tier-2 returns graded confidences** — deferred, already explicitly scoped to Story 3.4 in this story's own Dev Notes ("Full confidence-threshold badge logic ... → Story 3.4").

**Dismissed (4):** the new `data/demo-data.json`'s 22/2 split disagreeing with the WDS prototype's original 18/3/3 golden fixture (already documented and decided this session — see Completion Notes + the epics.md Story 2.4 fix); `data/demo-data.json` not being seeded into the running app (no AC requires demo-seeding; it's a test fixture, not a live-app feature); `TxnRow`/`ChipItem` using `pydantic.BaseModel` instead of `rx.Base` (false positive — `rx.Base` does not exist in the installed Reflex `0.9.6.post1`, verified empirically during dev-story; `pydantic.BaseModel` is the correct, working choice); the category-chip generator omitting categories present only in needs-review rows (working as designed per Task 5's Dev Notes — needs-review rows are surfaced via the "Needs review" chip, not their own category chip).

## Dev Notes

### What already exists vs. what's net-new (READ FIRST)
| Area | Already implemented | Net-new for THIS story |
| --- | --- | --- |
| Canonical schema fields for categorization (`category`, `category_source`, `category_confidence`) | `finance_app/models.py` `Transaction` table + `services/ingestion/schema.py` `Transaction` dataclass (Story 1.2/2.1) — fields exist, always `None` today | Populate them via Tier-1 rules |
| `CategorySource` enum (`rule`\|`llm`\|`user`) | `services/utils/enums.py` (Story 1.2) | Nothing — import and reuse |
| Category **taxonomy** (the 9 category names) | Nothing — `services/categorize/schema.py` is an empty placeholder | Populate it (Task 2) — this is AD-7's single source of truth, needed by both this story's rules and Story 3.2's LLM enum |
| Upload progress step 3/4 skeleton | `finance_app/state/upload_state.py` `_run_parse` (Story 2.4) — fires the UI steps but with `rules=0, ai=0` always | Wire real Tier-1 output into step 3's count (Task 4) |
| Transactions page | `finance_app/pages/transactions.py` — placeholder "Coming soon" | Full rebuild against WDS 01.4 (Task 5) |
| Demo fixture `data/demo-data.json` | **Does not exist** (`data/` is empty except `.gitkeep`) | Create it (Task 1) — blocks AC #9 otherwise |
| `persist_transactions` copying `category`/`category_source`/`category_confidence` to the DB row | Already does this (`services/ingestion/persist.py::_to_model`, Story 2.5) | Nothing — just call `categorize_by_rules` *before* persist so the fields are populated when persist runs |

### Category taxonomy (the exact 9 strings — use verbatim, do not paraphrase)
`"Food & Dining"`, `"Transport"`, `"Bills & Utilities"`, `"Subscriptions"`, `"Shopping"`, `"Entertainment"`, `"EMIs"`, `"Income"`, `"Other"`. Sourced from the WDS prototype's `ALL_CATEGORIES` (+ `Income`, which the prototype's Teach-Me picker omits on purpose — you don't recategorize a salary credit into a spend category — but the taxonomy itself needs `Income` for Tier-1 to tag salary credits). This is a **documented resolution of an epics-vs-WDS wording mismatch** — see Task 2.

### The demo fixture's designed 18/3/3 split — do not break it
The 24-row Priya fixture (`data/demo-data.json`, Task 1) is hand-designed by the WDS prototype so that **exactly 18** rows are obviously rule-matchable, **3** (`BigBasket`, `Amazon`, `Myntra`) are common-but-ambiguous merchants meant to demo Tier-2 AI in Story 3.2, and **3** (`UPI-8847213`, `NEFT-REF-99120`, `PhonePe-Merchant`) are generic reference-number descriptions meant to stay `needs_review` permanently (even AI can't confidently guess these). This exact split is asserted by Epic 2 Story 2.4's own AC ("18 categorized by rules · 3 by AI · 3 need your help") and by this story's AC #9. **Any rule pattern broad enough to catch `BIGBASKET`, `AMAZON`, `MYNTRA`, or a bare `UPI`/`NEFT`/`PHONEPE` prefix will silently break this AC in a way that still looks "reasonable"** (more rules matched = seems like an improvement, but it corrupts the fixture's cross-epic story). Task 3's rule table above is designed to avoid all six; do not add convenience/catch-all rules beyond it without re-checking against these 6 merchants.

### Scope boundaries — what belongs to OTHER stories
- **Tier-2 LLM categorization** (the 6 unmatched rows, `claude-haiku-4-5`, structured output) → **Story 3.2**. Do not call the Anthropic API in this story.
- **"Teach Me" correction UI** (tapping a badge to recategorize, the re-apply toggle, `merchant_rules` writes) → **Story 3.3**. Render transaction rows as non-interactive for now.
- **Full confidence-threshold badge logic** (blue "AI" badge, amber "?" badge with a real confidence threshold once Tier-2 exists) → **Story 3.4**. This story only has two reachable badge states (none / needs-review).
- **Virtual scroll** for 100–300 rows → **Story 3.4**. A plain rendered list is correct for this story (the demo fixture is 24 rows).

### Project-context rules that bind this story
- **AD-7 / single source of truth:** the category enum lives once in `services/categorize/schema.py`; both this story's rules and Story 3.2's LLM `Literal` import it — don't let a second copy of the category list appear anywhere (not in the rules table, not in the transactions page).
- **AD-4 / user_id scoping:** `TransactionsState`'s query must filter by the authenticated user's `id` — no bare `select(Transaction)`.
- **AD-2 boundary:** `services/categorize/` imports nothing from `finance_app` or `reflex`; `tests/test_service_boundary.py` will catch a violation automatically (no wiring needed, it globs `services/**/*.py`).
- **AD-13 / formatting:** the transactions table's amount column goes through `formatINR()` (`services/utils/format.py`), date through `formatDate()` — no f-string currency/date anywhere on this page.
- **AD-6:** `category`/`category_source`/`category_confidence` are three of the twelve canonical `Transaction` fields — Tier-1 rules populate them without inventing any new field.

### WDS UI baseline (must review before building the page)
Screenshot references in the prototype folder show the target states: `assets/transactions-default.png`, `assets/final-transactions.png`, `assets/nav-transactions.png`. The live markup/JS is `01.4-transactions-table.html` — read it in full; it defines exact chip-generation order, badge logic (`badgeFor()`), and the credit/green amount treatment (`is-credit` class) this story must reproduce in Reflex.

### Previous story intelligence (Epic 2)
- **`Transaction.with_fields(**changes)`** is the established idiom for producing a modified copy of a frozen dataclass row (used by `persist.py` to stamp `user_id`/`source_file_id`) — reuse it in `categorize_by_rules`, don't hand-roll `dataclasses.replace` again.
- **Typed exceptions / AD-12 pattern** (`IngestionError` caught in `rx.State`, translated to plain copy, never re-raised) is the house style if `categorize_by_rules` needs any error path — but it shouldn't: it's a pure, total function (every input either matches or doesn't; there's no failure case to model).
- **`user_for_token(session, token) -> LocalUser | None`** (`finance_app/state/auth_state.py`, Story 1.4) is the existing pattern for resolving the current user inside an `rx.State` handler/session block — reuse it in `TransactionsState`, same as `upload_state.py` already does.
- **Honest-testing split** (Story 1.4/2.4 precedent): unit-test the pure Tier-1 rules logic exhaustively; app-verify (via `reflex run`/frontend compile) the parts that need a live Reflex runtime (the actual table render, chip clicks). State that split honestly in Completion Notes — don't claim a browser E2E pass that wasn't run (no browser driver in this env, same limitation documented since Story 1.3).

### Project Structure Notes
- **New:** `services/categorize/rules.py`, `data/demo-data.json`, `finance_app/state/transactions_state.py`, `tests/categorize/__init__.py`, `tests/categorize/test_rules.py`.
- **Modified:** `services/categorize/schema.py` (populate taxonomy), `services/categorize/__init__.py` (export public API), `finance_app/state/upload_state.py` (`_run_parse` wiring), `finance_app/pages/transactions.py` (full rebuild).
- Route unchanged: `/transactions` (already guarded by `AuthState.check_auth` via `on_load`).

### References
- [Source: epics.md#Story-3.1-Tier-1-Rules-Engine-Transactions-Table] (lines 453–471) — acceptance criteria origin
- [Source: epics.md#Story-2.4] (lines 411, 414, 419) — the "18 by rules · 3 by AI · 3 need your help" contract this story half-completes
- [Source: ARCHITECTURE-SPINE.md#AD-7] — category enum hard-constraint, single source of truth
- [Source: ARCHITECTURE-SPINE.md#AD-6] — canonical Transaction schema fields
- [Source: ARCHITECTURE-SPINE.md#AD-4] — user_id scoping
- [Source: ARCHITECTURE-SPINE.md#AD-2/AD-14] — services/ framework-agnosticism, enforced by test_service_boundary.py
- [Source: deferred-work.md] — "Upload progress steps 3 & 4 ... skeleton ... until Epic 3" (Story 2.4); "no real HDFC demo PDF fixture" (Story 2.3, different concern than this story's fixture need)
- [Source: prototypes/01-priyas-first-honest-morning-Prototype/01.4-transactions-table.html] — WDS transactions UI baseline (markup, badge logic, chip generation)
- [Source: prototypes/01-priyas-first-honest-morning-Prototype/data/demo-data.json] — origin data for `data/demo-data.json` (Task 1); also the source for the 18/3/3 split
- [Source: services/ingestion/schema.py] — `Transaction` dataclass, `with_fields` idiom
- [Source: services/ingestion/persist.py] — confirms `category`/`category_source`/`category_confidence` already flow through persistence; confirms `amount` is stored unsigned (abs), sign carried by `direction`
- [Source: finance_app/state/upload_state.py] — `_run_parse`, the exact skeleton this story replaces
- [Source: finance_app/models.py] — `Transaction` table, `CategorySource`/`Criticality` enum usage pattern
- [Source: project-context.md] — WDS baseline rule, AD-2/AD-4/AD-7 guards, "reflex-docs before Reflex state work" (AGENTS.md)
- [Source: 1-4 story](./1-4-user-login-logout-and-protected-routes.md) — `user_for_token` pattern, honest-testing-split precedent, WDS-vs-epics documented-decision precedent

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (`bmad-dev-story`, 2026-07-10)

### Debug Log References

- **Mid-implementation discovery, before any Task 3/4 code was written:** `services/categorize/rules.py` (~90 rules) and `finance_app/state/upload_state.py`'s Tier-1 wiring (Step 3 `categorize_rules` call, persist, real `self.rules`/`self.need_review` counts) **already existed, committed, clean** — landed by two teammates' commits (`9b0954c` "Changes to parse any file that we upload", `f47af57` "PDF format changes") that were not present when this story was drafted (its Step-61 research read an empty `schema.py` and a skeleton `upload_state.py`). `git log --oneline` at dev-story start showed these two commits sitting above what was previously `HEAD`.
- Ran `categorize_rules` against the 24-row demo fixture to get ground truth before writing any test: **22/24 rows rule-matched** (not the 18 the story's AC/Task 6 assumed), because the existing engine already recognizes `BigBasket`→Groceries, `Amazon`→Shopping, `Myntra`→Shopping, and the `UPI-`/`NEFT-`/`PhonePe` reference rows as Bank/UPI Transfer — the exact 6 the story had reserved for Tier-2/needs-review. Only `Tata Power` and `Reliance Digital` are genuinely unmatched.
- Surfaced this conflict to the user via `AskUserQuestion` (3 options: keep existing engine + adapt story / replace with the WDS-aligned design / merge-and-remap) before writing any Task 2/3/6 code. **User chose: keep the existing engine, adapt the story to it.**
- `rx.Base` does not exist in the installed Reflex version (`0.9.6.post1`) — confirmed via `AttributeError` at import time, then verified empirically (no `reflex-docs` skill available in this environment) that a plain `pydantic.BaseModel` subclass works identically as a typed list-item for an `rx.State` var (`class MyState(rx.State): rows: list[Row] = []` compiles cleanly with a `pydantic.BaseModel` `Row`). Used `pydantic.BaseModel` for `TxnRow`/`ChipItem` instead.
- `reflex compile` (dry, no server) — **Success, 32/31 components**, confirming the new page/state wire correctly into the app.

### Completion Notes List

- **Scope was adapted mid-story after a real pre-existing-code discovery (documented decision, 2026-07-10, user-approved via AskUserQuestion):**
  - **Task 2** (category taxonomy): populated `services/categorize/schema.py` with the taxonomy `rules.py` **actually uses** (19 categories: Food & Dining, Groceries, Shopping, Entertainment, Travel & Transport, Health & Medical, Utilities, Mobile & Recharge, Insurance, Loan & EMI, Credit Card Payment, Education, Investments, Salary, Transfer In, Bank Transfer, UPI Transfer, ATM & Cash, Taxes) — **not** the WDS prototype's narrower 9-label set the story was originally drafted against. `rules.py` itself was left untouched (its 90 rules keep working exactly as before); a new test (`test_every_rule_category_is_declared_in_the_taxonomy`) enforces that `rules.py` can never emit a category `schema.py` doesn't declare, giving AD-7 a real single-source-of-truth guard without a risky rewrite of already-working code.
  - **Task 3** (rules engine, AC #1/#2): already existed and already satisfies both ACs (90 ≥ 40 rules; `category_source='rule'`, `category_confidence=1.0` on every match). No new file written; verified via the new test suite instead.
  - **Task 4** (wire into upload pipeline, AC #3): already existed — `upload_state.py`'s step 3 already calls `categorize_rules`, persists the categorized rows, and computes `self.rules`/`self.need_review` from real output. Verified via `reflex compile` + the existing ingestion test suite (unchanged, still green).
  - **Task 6 / AC #9** (the literal "18 rule-matched" assertion): **superseded.** With the existing engine, the demo fixture rule-matches **22/24** (not 18); only `Tata Power` and `Reliance Digital` are genuinely unmatched. `tests/categorize/test_rules.py` asserts this real behavior explicitly (`test_22_rows_are_rule_matched`, `test_exactly_the_expected_2_rows_are_uncategorized`) rather than forcing a false 18-count. This also means Epic 2 Story 2.4's own AC text ("18 categorized by rules · 3 by AI · 3 need your help") is now stale for this fixture — flagged here, not silently "fixed" to match, since Story 3.2 (Tier-2) will determine the real final split once it runs on the 2 remaining rows.
  - **Task 1** (demo fixture) and **Task 5** (transactions page) were built exactly as the story specified — no conflict there.
- **Task 5 details:** new `finance_app/state/transactions_state.py` (`TransactionsState`, `TxnRow`/`ChipItem` as `pydantic.BaseModel`, a session-injected pure `load_user_transaction_rows` helper for AD-4-scoped querying + AD-13 formatting) and a full rebuild of `finance_app/pages/transactions.py` against the WDS prototype's exact class names (`.txn-header-row`, `.pill-btn`, `.banner`, `.chip-group.chip--wrap`/`.chip`, `.txn-list`/`.txn-row`, `.txn-amount.is-credit`, `.txn-badge--review`/`.txn-badge--none`). Teach Me (Story 3.3) and the full confidence-threshold badge system (Story 3.4) are intentionally not built — rows are static, and only two badge states are reachable (no badge / needs-review) as scoped.
- **AD-4 scoping:** `load_user_transaction_rows` filters explicitly by `user_id`; unit-tested directly (`test_scoped_to_user_id`).
- **AD-13 formatting:** all currency/date display goes through `formatINR`/`formatDate` inside `_to_row` — no f-string formatting on the page.
- **Honest testing split** (Story 1.4/2.4 precedent): the pure query/formatting core (`load_user_transaction_rows`) and the rules engine (`categorize_rules`) are unit-tested against a temp SQLite session / the real demo fixture (34 new tests, all passing). The live table render, chip clicks, and badge visuals are verified by `reflex compile` (Success, 32/31) — no browser driver in this environment, same documented limitation since Story 1.3; a manual/Epic-8 browser pass is recommended.
- **Full regression suite: 172 passed** (138 baseline + 34 new), zero failures, zero regressions.

### File List

**New**
- `data/demo-data.json` — 24-row canonical Priya demo fixture (Task 1)
- `finance_app/state/transactions_state.py` — `TransactionsState`, `TxnRow`, `ChipItem`, `load_user_transaction_rows`
- `tests/categorize/__init__.py`
- `tests/categorize/test_rules.py` — Tier-1 engine tests against the demo fixture (adapted scope)
- `tests/test_transactions_state.py` — `load_user_transaction_rows` unit tests

**Modified**
- `services/categorize/schema.py` — populated with the taxonomy `rules.py` actually uses (`CATEGORIES`, `Category`, `UNCATEGORIZED`)
- `finance_app/pages/transactions.py` — full rebuild from the "Coming soon" placeholder; review pass: empty-state, icon rendering, plain-div rows (not buttons), `key=` on foreach elements, badge `aria-hidden`/`aria-label` fix
- `finance_app/state/transactions_state.py` — review pass: per-row malformed-data guard, date+id ordering tiebreaker, `chip_items`/`visible_rows`/`needs_review_count`/`categories` extracted into tested pure module-level functions, `_CATEGORY_ICON` map + `TxnRow.icon`, new `has_transactions` var
- `services/categorize/rules.py` — code-review follow-up (2026-07-10): added `"tata power"` (Utilities) and `Rule(("reliance digital",), "Shopping")`; demo fixture now rule-matches 24/24
- `_bmad-output/planning-artifacts/epics.md` — Story 2.4 AC note updated 22→24 to match
- `tests/categorize/test_rules.py` — review pass: added `test_category_literal_matches_categories_tuple`; updated the 22/2 split assertions to 24/0
- `tests/test_transactions_state.py` — review pass: added malformed-row/tiebreaker/confidence-0.5/icon tests + 4 new test classes for the extracted chip/filter pure functions (19 new tests total)

**Verified, not modified beyond the above (pre-existing on this branch, ahead of this story)**
- `services/categorize/__init__.py` — Tier-1 rules engine exports (Task 3)
- `finance_app/state/upload_state.py` — Tier-1 wiring into the upload pipeline (Task 4)

### Change Log

| Date | Change |
| --- | --- |
| 2026-07-10 | Story drafted (`bmad-create-story`), assuming no Tier-1 implementation existed yet. Status → ready-for-dev. |
| 2026-07-10 | `bmad-dev-story` run. Discovered `services/categorize/rules.py` + `upload_state.py` wiring already existed (landed by teammate commits after this story was drafted) with a different, broader category taxonomy that already rule-matches 22/24 demo-fixture rows (not the assumed 18). Raised the conflict via `AskUserQuestion`; user chose to keep the existing engine and adapt the story. Implemented: `data/demo-data.json` (Task 1), `services/categorize/schema.py` taxonomy matching the existing engine + a drift-guard test (Task 2, adapted), verified Tasks 3–4 already satisfied, built `TransactionsState` + rebuilt the transactions page (Task 5), wrote 34 new tests against real engine behavior (Task 6, adapted). Full suite 172 passed; `reflex compile` Success. Status → review. |
| 2026-07-10 | `bmad-code-review` run (Blind Hunter + Edge Case Hunter + Acceptance Auditor). 1 decision-needed (user chose to add the 2 missing `rules.py` keywords — demo fixture now 24/24 matched, not 22/24) + 9 patches, all applied: AD-7 taxonomy-parity test, per-row malformed-data guard (skip, don't crash), empty-state UI, same-day ordering tiebreaker, chip/filter logic extracted into tested pure functions, row changed from focusable button to plain div, `key=` added to foreach-rendered elements, per-category icons added, badge `aria-hidden`/`aria-label` fixed. 7 findings deferred (logged to `deferred-work.md`), 4 dismissed as noise (1 false positive: `rx.Base` doesn't exist in this Reflex version). Full suite 191 passed; `reflex compile` Success, 32/31. Status → done. |
