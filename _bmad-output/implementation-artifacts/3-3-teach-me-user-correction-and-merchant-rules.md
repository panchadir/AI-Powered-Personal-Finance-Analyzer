---
baseline_commit: e646b0750eaafa9211a823915a88f31919623b75
---

# Story 3.3: "Teach Me" — User Correction & Merchant Rules

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user who sees a miscategorized transaction,
I want to correct it and have that correction apply to all matching merchants now and in future uploads,
so that the app gets smarter with my specific spending patterns.

## Acceptance Criteria

Source: [epics.md — Story 3.3](../planning-artifacts/epics.md) (lines 491–506)

1. **Given** I click a transaction's category badge to correct it, **When** I select the correct category and confirm, **Then** a `merchant_rules` row is written: `(user_id, pattern, category, source='user')`.
2. **And** a `"Re-apply to all matching merchants"` toggle is shown, defaulting ON.
3. **And** when the toggle is ON, all transactions matching the merchant pattern in the current statement are updated to `category_source='user'`.
4. **And** the confirmation reads `"Got it — I'll call [Merchant] '[Category]' from now on."` — not `"Category updated successfully."`
5. **And** on the next upload, the merchant rule is applied automatically via the Tier-1 rules engine (user rules checked before system rules).
6. **And** `pytest tests/categorize/test_teach_me.py` passes: correction persists, re-apply updates matching rows, future upload picks up the rule.

## Tasks / Subtasks

- [x] **Task 1 — Extend `categorize_rules` to check user-taught rules first** (AC: #5)
  - [x] `services/categorize/rules.py`'s `categorize_rules(transactions)` currently has no notion of per-user rules — it's a pure function over the fixed `RULES` table only. Add an optional parameter: `categorize_rules(transactions: Sequence[Transaction], user_rules: Sequence[tuple[str, str]] = ()) -> list[Transaction]`. `user_rules` is a sequence of `(pattern, category)` pairs, matched **before** the built-in `RULES` table (same case-insensitive substring mechanism as `_match`), so a user's correction always wins over the default heuristic for that merchant. A user-rule match sets `category_confidence=1.0` (the user is now the authority — no "needs review"/"AI" badge should show for a user-taught row).
  - [x] Do **not** change `RULES`, `_match`'s existing behavior for the no-user-rules case, or any existing caller that doesn't pass `user_rules` (default `()` keeps `categorize_rules([...])` calls from Stories 3.1/3.2 working unchanged — verify `tests/categorize/test_rules.py` still passes untouched).
  - [x] `pattern`/`category` are plain strings, not DB rows — `categorize_rules` stays framework-agnostic (AD-2/AD-14); the caller (Task 3) is responsible for loading a user's `merchant_rules` from the DB and reducing them to this `(pattern, category)` shape.

- [x] **Task 2 — Merchant-rule persistence (new `services/categorize/teach_me.py`)** (AC: #1, #2, #3)
  - [x] New module, session-injected like `services/ingestion/persist.py` (AD-2: DB session + model passed in, nothing constructed inside `services/`). Three functions:
    - `load_user_merchant_rules(session, user_id: int) -> list[tuple[str, str]]` — all of a user's `MerchantRule` rows as `(pattern, category)` pairs, for Task 1's `categorize_rules(..., user_rules=...)` argument. **`user_id`-scoped (AD-4)** — a query with no `user_id` filter would leak one user's taught rules into another's categorization (this project's own Agent-Misread Guard calls out `merchant_rules` by name: "looks global but is per-user; leaking it cross-user is an IDOR").
    - `write_merchant_rule(session, txn_model_merchant_rule: type, user_id: int, pattern: str, category: str) -> None` — **upsert**, not blind insert: if a `MerchantRule` for this exact `(user_id, pattern)` already exists, update its `category` (and `created_at`); otherwise insert a new row with `source='user'`. (Not explicitly required by the AC's literal wording, but correcting the same merchant twice must not leave two rows for the same pattern — `categorize_rules`'s first-match-wins mechanism would then depend on undefined DB query order, which is exactly the class of bug this project's honesty philosophy exists to prevent.)
    - `reapply_correction(session, txn_model: type, user_id: int, pattern: str, category: str) -> int` — updates every one of this user's `Transaction` rows whose `description_raw` case-insensitively contains `pattern` (same substring semantics as Tier-1 matching, so "what will match on the next upload" and "what gets updated right now" use one consistent rule) to `category`/`category_source='user'`/`category_confidence=1.0`. Returns the count updated (for the confirmation copy/toast, if you choose to show a count — not required by the AC, optional). **`user_id`-scoped (AD-4)** — same reasoning as above, applies to `transactions` too.
  - [x] `MerchantRule` already exists in `finance_app/models.py` (Story 1.2) with exactly the AC's shape (`user_id`, `pattern`, `category`, `source` defaulting to `CategorySource.user.value`, `created_at`) — no migration needed for this story.

- [x] **Task 3 — Wire user rules into the upload pipeline** (AC: #5)
  - [x] `finance_app/state/upload_state.py`'s step 3 currently calls `categorize_rules(transactions)` with no user-rule argument. Before that call, load the signed-in user's rules via Task 2's `load_user_merchant_rules` (same `rx.session()` + `user_for_token(session, self.auth_token)` pattern already used later in `_run_parse` for persistence — reuse it, don't open a second session) and pass them: `categorize_rules(transactions, user_rules=user_rules)`.
  - [x] This must happen **before** `asyncio.to_thread(categorize_rules, ...)` — loading rules is a cheap DB read, doesn't need `to_thread`; only the (already-thread-dispatched) categorization call does.

- [x] **Task 4 — Transactions page: interactive rows + Teach Me correction panel** (AC: #1, #2, #3, #4)
  - [x] `finance_app/state/transactions_state.py` gains: `open_row_id: int | None` (which row's panel is expanded, `None` = all collapsed), `selected_category: str` (the chip currently picked in the open panel), `reapply: bool` (toggle state, **default `True`** per AC #2). Event handlers: `toggle_row(row_id: int)` (open/close, mirrors the WDS prototype's `toggleRow` — opening a new row closes any other), `select_category(category: str)`, `toggle_reapply()`, and `save_correction()` (calls Task 2's `write_merchant_rule` + `reapply_correction` inside `rx.session()`, user-scoped via `self.authenticated_user`, then reloads `self.rows` via `load_user_transaction_rows` so the UI reflects the change immediately — no full page reload).
  - [x] `finance_app/pages/transactions.py`'s `_row()` currently renders `rx.el.div` (deliberately non-interactive — Story 3.1's code review changed it *from* a dead focusable button *to* a plain div specifically because it had no `on_click` yet, with an explicit note to make it real "until Story 3.3 gives it real behavior"). **This is that story** — restore it to a real, keyboard-accessible control: `on_click=TransactionsState.toggle_row(row.id)`, `aria_expanded=` reflecting `open_row_id == row.id` (mirrors the prototype's `row.setAttribute('aria-expanded', ...)`).
  - [x] When a row is open, render the Teach Me panel beneath it using the WDS prototype's exact classes (`01.4-transactions-table.html`'s `buildTeachMe`): `.teach-me` container, `.teach-me-label` (`"What's this actually for?"`), a `.chip-group.chip--wrap` of category chips (one per `services.categorize.schema.CATEGORIES` entry, `.chip.is-active` on the selected one — reuse the existing `_chip`-style pattern from the filter chips, this is a second, separate chip picker, not the same component/state), a `.toggle-row` with a `.switch` (`<input type="checkbox">` + `.track`) for "Re-apply to all '[Merchant]' transactions?", and a `.btn.btn--secondary` "Got it — save this" button that calls `save_correction()`.
  - [x] **The whole row is clickable, not just the badge** (epics.md AC #1 literally says "click a transaction's category badge," but the WDS prototype — the UI source of truth per `project-context.md` — makes the *entire row* open the panel via one click listener, badge included, and has a larger, easier touch target). Aligning to the prototype here, consistent with the documented precedent from Stories 1.3/1.4/3.1 of resolving an epics-vs-WDS wording gap by following the prototype. Record this in Completion Notes; don't build a badge-only click zone.
  - [x] Confirmation copy is **exactly** `"Got it — I'll call {Merchant} '{Category}' from now on."` (AC #4) — `{Merchant}` is `row.merchant` (== `description_raw`, per Story 3.1 — no merchant-name normalization/extraction exists yet, out of scope here; using the full `description_raw` as both the display name and the stored `pattern` is the smallest-scope choice that satisfies the AC literally). Show it as a toast/inline confirmation (the prototype uses a bottom toast, `#txn-toast` / `.toast`) — reuse that class if convenient, or an inline message; either satisfies the AC, but the **exact copy string** does not.
  - [x] Category-picker chips must come from `services/categorize/schema.py`'s `CATEGORIES` (the single source of truth, Story 3.1) — do not hand-type the category list again.

- [x] **Task 5 — Tests** (AC: #6)
  - [x] New `tests/categorize/__init__.py` already exists; add `tests/categorize/test_teach_me.py`. Cover, against a temp SQLite session (mirror the harness in `tests/ingestion/test_dedup.py`/`tests/security/test_idor_baseline.py`):
    - `write_merchant_rule` inserts a new row with `source='user'`; calling it again for the **same** `(user_id, pattern)` updates the existing row's category rather than inserting a second one (upsert).
    - `write_merchant_rule` is `user_id`-scoped: two users writing a rule for the same `pattern` text produce two independent rows, never collide or overwrite each other's.
    - `reapply_correction` updates every matching transaction for that user to the new category/`category_source='user'`/`category_confidence=1.0`, and returns the correct count; a transaction belonging to a **different** user with the same description text is untouched (AD-4/IDOR).
    - `load_user_merchant_rules` returns only the calling user's rules, as `(pattern, category)` tuples.
    - **End-to-end "future upload picks up the rule"**: build a `Transaction` list containing a merchant Tier-1's `RULES` table would categorize one way (e.g. "Zomato" → normally "Food & Dining"), call `categorize_rules(transactions, user_rules=[("zomato", "Personal Project")])`, and assert the **user rule wins** — this is the direct proof of AC #5, and of Task 1's "before the built-in RULES table" ordering guarantee.
    - A user rule for a merchant with **no** Tier-1 match at all (e.g. a previously-`UNCATEGORIZED` description) also gets picked up correctly.
  - [x] Run the full suite — no regressions, especially `tests/categorize/test_rules.py` (Task 1 must be additive-only) and `tests/test_transactions_state.py`/`tests/categorize/test_summary.py` (Task 4 changes `TransactionsState`'s shape but must not change `load_user_transaction_rows`/`summarize_categorization`'s existing contracts).

### Review Findings

- [x] [Review][Defer] Taught rule pattern is the full raw description, not a normalized merchant name [services/categorize/teach_me.py, finance_app/state/transactions_state.py] — deferred, already a documented Dev Notes scope decision; user re-confirmed 2026-07-10 to leave as-is rather than add merchant-name normalization now. All three review layers independently flagged that unique reference numbers in real bank description text will likely make "apply to all"/future-upload matching rarely fire in practice. Flag for a future merchant-normalization story.
- [x] [Review][Patch] `select_category`/`save_correction` accepted an arbitrary client-supplied category with no validation against `CATEGORIES`, risking an off-taxonomy value reaching `merchant_rules.category`/`transactions.category` (AD-7) [finance_app/state/transactions_state.py:220]
- [x] [Review][Patch] `reapply` toggle never reset to ON when a new row's panel opened, so once turned off it stayed off for every subsequent row that session — violates AC #2's "defaulting ON" [finance_app/state/transactions_state.py:204]
- [x] [Review][Patch] A blank/whitespace merchant description would be "contained in" every transaction's text, so a correction on such a row (with re-apply on) could silently recategorize a user's entire transaction history [services/categorize/teach_me.py, services/categorize/rules.py]
- [x] [Review][Patch] `write_merchant_rule`'s upsert lookup was case-sensitive while `_match`/`reapply_correction` are both case-insensitive, so a case-variant of an already-taught pattern inserted a duplicate row instead of updating it [services/categorize/teach_me.py:68]
- [x] [Review][Patch] `write_merchant_rule` didn't refresh `created_at` on update, despite the story's own Task 2 spec explicitly requiring it [services/categorize/teach_me.py:74]
- [x] [Review][Patch] No deterministic ordering when multiple stored rules could match the same description — `load_user_merchant_rules` had no `ORDER BY`, so precedence between two matching rules was undefined DB order rather than "most recently taught wins" [services/categorize/teach_me.py:35]
- [x] [Review][Patch] `save_correction` left the Teach Me panel stuck open with no way to close it if its row disappeared from `self.rows` (e.g. after a reload) [finance_app/state/transactions_state.py:233]
- [x] [Review][Patch] The re-apply-off branch always showed the "Got it..." success toast even when the single-transaction update silently didn't happen (row missing or wrong user) [finance_app/state/transactions_state.py:244]
- [x] [Review][Patch] "Got it — save this" button had no disabled state before a category was picked, so a click before selecting silently no-op'd [finance_app/pages/transactions.py]
- [x] [Review][Patch] Row toggle button had no `aria-controls` linking it to the Teach Me panel it expands, breaking the assistive-tech association [finance_app/pages/transactions.py]
- [x] [Review][Patch] Confirmation toast never auto-dismissed, lingering indefinitely until the next row was opened or corrected [finance_app/state/transactions_state.py]
- [x] [Review][Defer] No DB-level unique constraint on `(user_id, pattern)` in `MerchantRule` [finance_app/models.py] — deferred, pre-existing (table shape from Story 1.2), needs a migration. The application-level upsert (now case-insensitive) covers sequential corrections, but a true concurrent double-submit (double-click, two tabs) could still race past the check-then-write and insert two rows. Fold into a future hardening pass (Epic 8).

Dismissed as noise: `rx.State` event-handler wiring (`toggle_row`/`select_category`/`save_correction`) has no direct unit tests — consistent with this project's established, repeatedly-reaffirmed "app-verified only" convention for `rx.State` handlers (no browser driver in this environment), not a new gap. `reapply_correction` loading all of a user's transactions into memory on every save — already an explicitly accepted tradeoff in the module's own docstring at this project's single-user local scale.

## Dev Notes

### What already exists vs. what's net-new (READ FIRST)
| Area | Already implemented | Net-new for THIS story |
| --- | --- | --- |
| `merchant_rules` DB table | `finance_app/models.py` `MerchantRule` (Story 1.2) — exact shape the AC needs | Nothing — no migration required |
| Category taxonomy for the picker | `services/categorize/schema.py` `CATEGORIES` (Story 3.1) | Nothing — import and reuse |
| Tier-1 rules engine | `services/categorize/rules.py` `categorize_rules`/`RULES` (Story 3.1, extended in 3.2's review) | Extend with an optional `user_rules` param (Task 1) — additive, existing callers unaffected |
| Transactions page + state | `finance_app/pages/transactions.py`, `finance_app/state/transactions_state.py` (Story 3.1, hardened in its code review) — rows deliberately **non-interactive** (`rx.el.div`, no `on_click`) with an explicit "until Story 3.3" note | Make rows interactive again; add the Teach Me panel + its state (Task 4) |
| Upload pipeline (Tier-1 + Tier-2 wiring) | `finance_app/state/upload_state.py` (Stories 3.1/3.2) — calls `categorize_rules(transactions)` with no user-rule awareness | Load + pass the user's rules before calling it (Task 3) |
| Session-injected, `user_id`-scoped persistence pattern to mirror | `services/ingestion/persist.py` (Story 2.5), `finance_app/state/auth_state.py`'s `user_for_token` (Story 1.4) | `services/categorize/teach_me.py` (Task 2), same shape |

### The "current statement" scope question — resolved
AC #3 says re-apply updates "all transactions matching the merchant pattern **in the current statement**." The transactions page (Story 3.1) shows a user's entire transaction history in one unified view — there is no per-statement/per-upload grouping UI anywhere in the app today, and building one is not this story's scope. **Resolution:** "re-apply" updates all of the user's matching transactions across their full history (i.e., everything `reapply_correction` can see for that `user_id`), not scoped to a single upload. This is both the simplest reading consistent with the app's actual structure and matches the WDS prototype's own re-apply logic (`o.merchant === t.merchant` over the *entire* loaded `txns` array, not a per-file subset). Record this as a documented scope decision, same precedent as prior epics-vs-implementation reconciliations (Stories 1.3/1.4).

### `pattern` = the full `description_raw` text, not an extracted merchant name
No merchant-name normalization exists in this codebase (`merchant_normalized` is declared in the schema but never populated by any parser — a known, previously-documented gap from Story 3.1). Rather than build merchant-name extraction as a side quest, this story uses the transaction's full `description_raw` (== `TxnRow.merchant`, what's already shown on screen) as both the confirmation copy's `{Merchant}` text and the stored `pattern`/re-apply match target. This is a real, intentional scope boundary — a future story could add merchant normalization and this story's `pattern` storage would need no schema change to benefit from it later (still just a string column).

### Project-context rules that bind this story
- **AD-4 / user_id scoping — explicitly named for `merchant_rules`:** project-context.md's own Agent-Misread Guards section calls this out by name: *"`user_id` scoping has no 'reference data' exemption... `merchant_rules` (user-taught)... looks global but is per-user; leaking it cross-user is an IDOR."* Every function in Task 2 takes `user_id` and filters by it — no exceptions.
- **AD-2 boundary:** `services/categorize/teach_me.py` takes a DB session + model classes as parameters (mirrors `persist.py`); it does not import `reflex` or open its own session. `tests/test_service_boundary.py` will catch a `reflex` import automatically — no wiring needed.
- **WDS baseline:** the Teach Me panel's markup/classes must match `01.4-transactions-table.html`'s `buildTeachMe` — reuse `assets/wds.css` classes, don't invent new ones (project-context "UI Consistency Rule").
- **Enums are exact:** `category_source` values are `rule|llm|user` (`services/utils/enums.py` `CategorySource`) — a user correction is `CategorySource.user.value`, not a new string.

### Previous story intelligence (Stories 3.1/3.2)
- **`Transaction.with_fields(**changes)`** is the established idiom for a modified copy of the frozen ingestion dataclass — not directly relevant here (Task 2 operates on the persisted `finance_app.models.Transaction` rows, not the ingestion dataclass), but `categorize_rules`'s internals (Task 1) still use it.
- **Extract pure functions, test them** — the pattern this project has now applied twice after code review (`transactions_state.py`'s chip/filter functions in 3.1's review, `summarize_categorization` in 3.2's review). Task 2's three functions are written pure/session-injected *from the start* this time, not discovered as a gap afterward — apply the lesson proactively.
- **`_row()`'s div-not-button state is a deliberate, documented placeholder**, not an oversight to work around — read the comment at the top of `finance_app/pages/transactions.py` before touching it; it says exactly what this story needs to do.
- **Honest testing split** (every story since 1.4): the pure DB-writing functions (Task 2) and the extended `categorize_rules` (Task 1) are fully unit-testable and must be. The `rx.State` panel-open/close/save wiring (Task 4) is app-verified (`reflex compile` + the full suite), consistent with this project's established, repeatedly-reaffirmed limitation (no browser driver in this environment).

### References
- [Source: epics.md#Story-3.3-Teach-Me] (lines 491–506) — acceptance criteria origin
- [Source: ARCHITECTURE-SPINE.md#AD-4] — user_id isolation, explicitly extended to `merchant_rules` in project-context's Agent-Misread Guards
- [Source: ARCHITECTURE-SPINE.md#AD-2/AD-14] — services/ framework-agnosticism, session-injection pattern
- [Source: project-context.md] — "merchant_rules ... is per-user; leaking it cross-user is an IDOR" (Agent-Misread Guards), WDS UI Consistency Rule
- [Source: services/categorize/rules.py] — `categorize_rules`/`RULES`/`_match`, extended by Task 1
- [Source: services/categorize/schema.py] — `CATEGORIES`, the picker's source of truth
- [Source: finance_app/models.py] — `MerchantRule` (already has the AC's exact shape)
- [Source: finance_app/state/transactions_state.py] — `TransactionsState`, `load_user_transaction_rows`, extended by Task 4
- [Source: finance_app/pages/transactions.py] — `_row()`'s current div-not-button placeholder and its "until Story 3.3" comment
- [Source: finance_app/state/upload_state.py] — `_run_parse` step 3, where Task 3's user-rule loading is inserted
- [Source: services/ingestion/persist.py] — the session-injected persistence pattern Task 2 mirrors
- [Source: prototypes/01-priyas-first-honest-morning-Prototype/01.4-transactions-table.html] — `buildTeachMe`, `toggleRow`, `saveCorrection` — the exact interaction/markup this story reproduces in Reflex
- [Source: 3-1 story](./3-1-tier-1-rules-engine-and-transactions-table.md), [3-2 story](./3-2-tier-2-llm-categorizer-claude-haiku.md) — extract-pure-function precedent, session-injection pattern, epics-vs-WDS reconciliation precedent

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (`bmad-dev-story`, 2026-07-10)

### Debug Log References

- Fresh full repo re-scan before drafting/implementing (lesson from Stories 3.1/3.2) — confirmed no pre-existing Teach Me code and no new commits since Story 3.2's review landed.
- Verified empirically (not from memory) that a zero-argument `rx.State` event handler bound to a checkbox `on_change` compiles cleanly in this Reflex version (`reflex==0.9.6.post1`) before writing the toggle switch — Reflex drops the event payload when the handler signature doesn't accept it, no arity error.
- `reflex compile` — Success, 32/31, confirming the nested `rx.foreach` (category chips inside the Teach Me panel, itself inside the outer transaction-row `rx.foreach`) and the `rx.cond`-gated panel visibility all wire correctly.

### Completion Notes List

- **Task 1** — `categorize_rules(transactions, user_rules=())` — additive-only change; `_match` checks `user_rules` (case-insensitive substring, same mechanism as the built-in table) before `RULES`. Verified `tests/categorize/test_rules.py` passes unchanged (29 tests, zero modifications to that file).
- **Task 2** — New `services/categorize/teach_me.py`: `load_user_merchant_rules`, `write_merchant_rule` (upsert on `(user_id, pattern)` — a second correction updates the existing rule rather than creating a conflicting duplicate), `reapply_correction` (Python-side substring filter, not SQL `LIKE`/`ILIKE`, so its matching semantics are provably identical to `categorize_rules`'s — no wildcard-escaping edge cases to get wrong). All three explicitly `user_id`-scoped (AD-4) per project-context's own naming of `merchant_rules` as an IDOR risk.
- **Task 3** — `upload_state.py`'s step 3 now loads the signed-in user's `merchant_rules` (a cheap DB read, not dispatched to a thread — only the categorization call itself is) and passes them into `categorize_rules(transactions, user_rules)`.
- **Task 4** — `TransactionsState` gained `open_row_id`/`selected_category`/`reapply` (default `True`)/`confirmation` plus `toggle_row`/`select_category`/`toggle_reapply`/`save_correction` event handlers and a `category_options` computed var (from `services/categorize/schema.py`'s `CATEGORIES` — not hand-typed). `save_correction` always writes the merchant rule; when `reapply` is off it corrects only the single opened transaction (not a blind no-op) rather than silently doing nothing. `finance_app/pages/transactions.py`'s `_row()` — deliberately left as a non-interactive `div` by Story 3.1's code review specifically for this story to complete — is now a real `<button>` again with `on_click`/`aria-expanded`; the Teach Me panel (`.teach-me`/`.teach-me-label`/`.toggle-row`/`.switch`, matching the WDS prototype's `buildTeachMe`) renders as a sibling of the row button (not nested inside it — a button can't validly contain another button/checkbox). **Documented alignment decision:** the whole row is clickable (matching the WDS prototype's actual click handler), not just the badge (epics.md's literal AC #1 wording) — same resolution pattern as prior epics-vs-WDS gaps.
- **Task 5** — `tests/categorize/test_teach_me.py` (12 tests) covers all of Task 2's functions against a real temp-SQLite round-trip (insert, upsert, per-user isolation, re-apply scoping, re-apply overriding already-confident rows, zero-match count) plus the direct AC #5 proof: `categorize_rules(txns, user_rules=[...])` returns the user's category instead of the built-in rule's, and also correctly categorizes a merchant Tier-1 never recognized at all. A dedicated test (`test_no_user_rules_behaves_exactly_as_before`) locks in that Task 1 is additive-only.
- **Honest testing split** (established since Story 1.4, reapplied in 3.1/3.2): Task 2's pure/session-injected DB functions and Task 1's extended `categorize_rules` are fully unit-tested (12 + inherited 29 = 41 relevant tests). Task 4's `rx.State` panel-open/close/save wiring is app-verified only (`reflex compile` Success, 32/31) — this project's environment has no browser driver, a limitation documented consistently since Story 1.3; a manual browser pass (open a row, pick a category, toggle re-apply, save, confirm the exact copy string and the row list refreshing) is recommended before demo.
- **Full regression suite: 233 passed** (221 baseline + 12 new in `test_teach_me.py`), zero regressions. `reflex compile` — Success, 32/31.

### Code Review (2026-07-10)

Three parallel review layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor) ran against the full Task 1–4 diff. 1 decision-needed item (user resolved: leave the full-description pattern scope as documented, defer merchant normalization to a future story), 11 patch findings (all applied — see `### Review Findings` above for the full list: taxonomy validation on `select_category`/`save_correction`, `reapply` reset-to-ON on panel open, a blank-pattern guard against mass-recategorization in `teach_me.py`/`rules.py`, a case-insensitive upsert lookup, `created_at` refresh on rule update, deterministic most-recent-first rule ordering, stuck-panel recovery when a row disappears, an accurate success/failure toast on the re-apply-off path, a disabled Save button before a category is picked, `aria-controls` on the row toggle, and toast auto-dismiss), 2 deferred (no DB-level unique constraint on `(user_id, pattern)`; the full-description pattern scope), 2 dismissed as noise (established `rx.State` app-verified-only testing convention; the already-accepted in-memory `reapply_correction` scan).

6 new tests added in `tests/categorize/test_teach_me.py` (12 → 18) covering the blank-pattern guard on both the write and re-apply paths, the case-insensitive upsert, the `created_at` refresh, deterministic rule ordering, and a blank user-rule pattern being ignored by `_match`. Full suite: **239 passed**, zero regressions. `reflex compile` — Success, 32/31 (verifies the new `disabled=`/`aria_controls`/background-dismiss wiring compiles cleanly).

### File List

**New**
- `services/categorize/teach_me.py` — `load_user_merchant_rules`, `write_merchant_rule`, `reapply_correction`
- `tests/categorize/test_teach_me.py` — 12 tests, +6 from the review pass (18 total)

**Modified**
- `services/categorize/rules.py` — `categorize_rules`/`_match` gained the optional `user_rules` parameter (additive); review pass added a blank-pattern skip guard
- `finance_app/state/upload_state.py` — loads + passes the user's merchant rules before Tier-1 categorization
- `finance_app/state/transactions_state.py` — Teach Me panel state (`open_row_id`, `selected_category`, `reapply`, `confirmation`) + handlers + `category_options` computed var + `CategoryOption` model; review pass added category validation, reapply-reset-on-open, stuck-panel recovery, accurate success/failure toast copy, and a `dismiss_confirmation_after_delay` background event
- `finance_app/pages/transactions.py` — rows restored to interactive `<button>`s; new Teach Me panel rendering; review pass added `disabled=`/`aria_controls`/panel `id`

### Change Log

| Date | Change |
| --- | --- |
| 2026-07-10 | Story drafted (`bmad-create-story`), with a fresh full-repo re-scan first (now a standing habit after Stories 3.1/3.2) confirming no pre-existing Teach Me code. Resolved two scope questions upfront rather than leaving them for the dev pass: "current statement" scope (no per-statement grouping UI exists — re-apply covers the user's full history) and `pattern` = full `description_raw` text (no merchant-name normalization exists yet). Status → ready-for-dev. |
| 2026-07-10 | `bmad-dev-story` run, all 5 tasks completed in order, no surprises (the fresh-rescan habit held). Extended `categorize_rules` additively; built `services/categorize/teach_me.py`'s 3 session-injected, user-scoped functions; wired user rules into the upload pipeline; restored the transactions page rows to interactive and added the full Teach Me correction panel matching the WDS prototype. 12 new tests, all passing; full suite 233 passed; `reflex compile` Success. Status → review. |
| 2026-07-10 | `bmad-code-review` run (3 parallel layers). 1 decision-needed (resolved: defer merchant-pattern normalization), 11 patches applied, 2 deferred, 2 dismissed as noise. Full suite 239 passed; `reflex compile` Success. Status → done. |
