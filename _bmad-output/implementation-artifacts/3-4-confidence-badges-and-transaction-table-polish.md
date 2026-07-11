---
baseline_commit: e646b0750eaafa9211a823915a88f31919623b75
---

# Story 3.4: Confidence Badges & Transaction Table Polish

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reviewing my transactions,
I want to clearly see which transactions were categorized by rules, by AI, or need my review — without being shown raw confidence percentages,
so that I understand the quality of categorization at a glance.

## Acceptance Criteria

Source: [epics.md — Story 3.4](../planning-artifacts/epics.md) (lines 508–524)

1. **Given** the transactions table renders, **When** a row's confidence is below the needs-review threshold, **Then** it shows an amber `"?"` badge.
2. **And** a row with `category_source='llm'` shows a blue `"AI"` badge — unconditionally, regardless of the LLM's own self-reported confidence value (see Dev Notes' resolved badge-priority rule).
3. **And** a row with `category_source='rule'` or `category_source='user'` (at full confidence) shows no badge.
4. **And** raw confidence percentages are never shown anywhere in the UI.
5. **And** the transaction list uses virtual scroll — standard DOM list is not acceptable for 100–300 rows. **Documented override (user decision, 2026-07-10): NOT implemented this story** — see Dev Notes' "Virtual scroll — deviated from epics.md by user decision" section. Deferred as a future improvement, tracked in `deferred-work.md`.
6. **And** virtual scroll renders without layout thrash at 300 rows on a standard developer machine. **Same override as AC #5 — not implemented this story.**
7. **And** the `"Needs review"` count in the filter chip matches the actual count of amber-badged (`"?"`) transactions — a self-consistency invariant, not a new count to compute separately.

## Tasks / Subtasks

- [x] **Task 1 — Add the AI-categorized signal to `TxnRow`/`_to_row`, and fix the needs-review formula's Tier-2 blind spot** (AC: #1, #2, #7)
  - [x] `finance_app/state/transactions_state.py`'s `TxnRow` gains `is_ai: bool`.
  - [x] In `_to_row`, compute `is_ai = txn.category_source == CategorySource.llm.value` (`CategorySource` is already imported in this file — added during Story 3.3's review pass).
  - [x] **Fix the needs-review formula**: today it is `needs_review = confidence < NEEDS_REVIEW_THRESHOLD` (`NEEDS_REVIEW_THRESHOLD = 1.0`). This was correct in Story 3.1 (only `rule`-sourced rows existed on this page: confidence is always exactly `1.0`, `0.5`, or `0.0`), but is now wrong for `llm`-sourced rows: Tier-2's self-reported `category_confidence` (`services/categorize/llm_categorizer.py`) is essentially never exactly `1.0`, so **every** AI-categorized row would incorrectly show the amber "needs review" badge instead of the blue "AI" badge. Change the formula to `needs_review = (not is_ai) and confidence < NEEDS_REVIEW_THRESHOLD`. Do **not** change `NEEDS_REVIEW_THRESHOLD` itself (still `1.0`) — this exclusion is the fix, not a new threshold value.
  - [x] Do not touch `_icon_for`/the row icon — that keys off `category`, not badge state; unrelated to this task.

- [x] **Task 2 — Render the third badge state in the transactions page** (AC: #1, #2, #3)
  - [x] `finance_app/pages/transactions.py`'s `_row()` currently renders a 2-way `rx.cond(row.needs_review, review_badge, none_badge)`. Nest a second `rx.cond` inside the `else` branch for the new `is_ai` state.
  - [x] No new CSS: `.txn-badge--ai` already exists in `assets/wds.css` (`background: #e6ecf5; color: #3f5c8c; font-size: 9px;`) — it is the prototype's own class (`prototypes/01-priyas-first-honest-morning-Prototype/01.4-transactions-table.html`'s `badgeFor()`), just never wired up in the Reflex build until now. Reused the exact class name and `"AI-categorised"` aria-label copy from that prototype function. `reflex compile` — Success, 32/31.

- [x] **Task 3 — Virtual scroll: documented non-implementation (user decision, 2026-07-10)** (AC: #5, #6)
  - [x] No virtualization library, custom Reflex component wrapper, or windowing logic added. The list stays the plain `rx.el.ul` + `rx.foreach(TransactionsState.visible_rows, _row)` rendering exactly as Story 3.1 built it.
  - [x] Rationale recorded in `finance_app/pages/transactions.py`'s module docstring (Story 3.4 note) and here in Dev Notes.
  - [x] `deferred-work.md` entry (`## Deferred from: story-3.4 planning — virtual scroll (2026-07-10)`) added at story-creation time — verified present.

- [x] **Task 4 — Structural guard: raw confidence is never rendered** (AC: #4)
  - [x] New `tests/test_transactions_page_structure.py`: (a) `TxnRow` has no confidence-carrying field at all — `category_confidence` is consumed by `_to_row` purely to derive `needs_review`/`is_ai` and never forwarded onto the row; (b) a defense-in-depth text scan confirms `finance_app/pages/transactions.py`'s source never references `category_confidence` directly. Mirrors `tests/test_service_boundary.py`'s structural-guard style.

- [x] **Task 5 — Tests** (AC: #1, #2, #3, #4, #7)
  - [x] Extended `tests/test_transactions_state.py` with all 9 planned cases (llm low-confidence, llm full-confidence, rule 0.5-confidence regression, rule/user full-confidence no-badge, AI rows included in `distinct_categories`/`build_chip_items`/`filter_rows`, AC #7 self-consistency ×2).
  - [x] Added Task 4's structural guard tests (`tests/test_transactions_page_structure.py`).
  - [x] Full suite: **249 passed** (239 baseline + 10 new), zero regressions. `test_confidence_0_5_transfer_in_row_is_flagged_needs_review` and all of `tests/categorize/test_teach_me.py` pass unmodified. `reflex compile` — Success, 32/31.

### Review Findings

- [x] [Review][Patch] `TxnRow` had no guard against `needs_review=True` and `is_ai=True` being set simultaneously — mutually exclusive only by `_to_row`'s own construction, not enforced on the model itself [finance_app/state/transactions_state.py]
- [x] [Review][Patch] `is_ai` could be true for a corrupted/legacy row that is `category_source='llm'` yet `category='Uncategorized'` — no current write path produces this, but nothing prevented it from silently showing a confident "AI" badge instead of "needs review" [finance_app/state/transactions_state.py's `_to_row`]
- [x] [Review][Patch] Stale `NEEDS_REVIEW_THRESHOLD` docstring still read "until Tier-2 (Story 3.2) exists" — future tense, misleading now that this story is entirely about correctly handling Tier-2 rows [finance_app/state/transactions_state.py:37-40]
- [x] [Review][Patch] `deferred-work.md`'s Story 3.1 entry about this exact threshold was never closed out despite being resolved by this story [deferred-work.md]
- [x] [Review][Patch] Missing test coverage for `category_source=None` (a real, nullable DB column state) and for the llm-sourced-yet-Uncategorized edge case [tests/test_transactions_state.py]
- [x] [Review][Patch] `is_credit`/`is_ai` used two different idioms (raw string vs. enum) for structurally identical comparisons in the same function [finance_app/state/transactions_state.py's `_to_row`]
- [x] [Review][Patch] A test comment overclaimed Tier-2 confidence is "essentially never exactly 1.0" as if guaranteed, when it's a legal, reachable value — softened the wording [tests/test_transactions_state.py]
- [x] [Review][Defer] The "full confidence = 1.0" threshold/constant is duplicated across 4 locations (`transactions_state.py`, `summary.py`, `save_correction`, `teach_me.py::reapply_correction`) with no shared source of truth — pre-existing across Stories 3.1-3.3, not introduced by this story
- [x] [Review][Defer] `category_source` values outside the 3-enum members (or `None`) are silently folded into "not AI" with no anomaly logging — no current write path produces this
- [x] [Review][Defer] `category_confidence > 1.0` on a non-`llm` row silently produces "no badge" instead of surfacing corruption — no current write path produces this

Dismissed as noise: `is_ai`'s naming (it means `category_source == 'llm'` specifically, not "AI" generally) — already precisely documented on `TxnRow`, renaming is disproportionate churn for today's single-tier reality. The `aria-label="AI-categorised"` British spelling — intentional, verbatim match to the WDS prototype's own copy (the UI source of truth). The structural guard test's single-file scope — the inherent, accepted scope of a lightweight regression guard, same as `test_service_boundary.py`. No test for the rendered `rx.cond` priority order — an already-established, repeatedly-reaffirmed project limitation (no browser driver in this environment), not new to this story.

## Dev Notes

### What already exists vs. what's net-new (READ FIRST)
| Area | Already implemented | Net-new for THIS story |
| --- | --- | --- |
| Two-state badge (`needs_review`/none) | `finance_app/state/transactions_state.py` `TxnRow.needs_review`, `_to_row` (Story 3.1); rendering in `finance_app/pages/transactions.py`'s `_row()` (Story 3.1, made interactive in 3.3) | Add a third state (`is_ai`) and fix `needs_review`'s formula so it no longer misfires on `llm`-sourced rows |
| `CategorySource` enum (`rule`/`llm`/`user`) | `services/utils/enums.py` (Story 1.2); already imported in `transactions_state.py` (added during Story 3.3's review) | Nothing — import and reuse |
| `.txn-badge--ai` CSS class | `assets/wds.css` (prototype's own class, present since the prototype was authored) | Nothing — wire the existing class into the Reflex render, don't invent a new one |
| Tier-2 LLM categorization (`category_source='llm'`, real self-reported `category_confidence`) | `services/categorize/llm_categorizer.py` (Story 3.2) | Nothing — this story only changes how the transactions page *displays* rows that already carry `category_source='llm'` |
| Chip/filter pure functions (`needs_review_count`, `distinct_categories`, `build_chip_items`, `filter_rows`) | `finance_app/state/transactions_state.py` (Story 3.1, extracted+tested in its review) | No signature changes — they already operate on `TxnRow.needs_review`; correctness now depends on Task 1's formula fix, not a rewrite of these functions themselves |

### The badge-priority rule — resolved (READ BEFORE COOING TASK 1/2)
epics.md's AC literally reads: *"category_source='needs_review' (confidence below threshold) → amber badge; category_source='llm' → blue badge; category_source='rule' or 'user' → no badge."* Taken completely literally this is inconsistent: `category_source` in this codebase only ever holds `rule`/`llm`/`user` (`services/utils/enums.py`'s `CategorySource`) — there is no `'needs_review'` source value, and a row can be `rule`-sourced yet still need review (the existing 0.5-confidence "unrecognized credit → Transfer In" fallback in `services/categorize/rules.py`, which is `source='rule'`, not `source='needs_review'`).

**Resolution** (this is the actual decision tree to implement, priority-ordered):
1. `category_source == 'llm'` → blue `"AI"` badge. **Unconditional** — no further confidence gating. Tier-2 already made its best attempt within the AD-7 constrained taxonomy; the AI badge itself *is* the "this was an educated guess, not a rule match" signal AC #4 wants ("understand the quality... without raw percentages"). Gating it by the LLM's own self-reported confidence would need a second, undocumented threshold and isn't what the AC's literal wording asks for.
2. Else, `category_confidence < NEEDS_REVIEW_THRESHOLD` (still `1.0`, unchanged) → amber `"?"` badge. This is what actually catches both a fully-unmatched `Uncategorized` row (confidence `0.0`) and the rules engine's `0.5`-confidence "Transfer In" credit fallback — both pre-existing, already-tested Story 3.1 behaviors that must be preserved exactly.
3. Else (`rule`/`user` at full confidence) → no badge.

This is a straightforward `is_ai` short-circuit ahead of the existing confidence check — see Task 1's exact formula.

### Virtual scroll — deviated from epics.md by user decision (READ BEFORE TASK 3)
Two independent project artifacts already question this AC before this story was even drafted:
- The WDS prototype (`01.4-transactions-table.html`) renders the full transaction list with `listEl.innerHTML = ''` + a plain `.forEach` append — **no virtualization of any kind**, at any row count.
- The project's own UX-scenario notes for this exact screen (`_bmad-output/C-UX-Scenarios/01-priyas-first-honest-morning/01.4-transactions-table/01.4-transactions-table.md`, "Technical Notes" section) say: *"Virtual scroll — retained as specced; originally justified by budget Android device performance. On a desktop-only MVP, a standard DOM list of 100–300 rows will likely render fine without virtualization — this is a simplification opportunity, but not applied here since epics.md's story ACs may still reference virtual scroll. Flagged for review, not removed."*

Per project-context.md's own Story Implementation Process rule #6 ("If a story conflicts with the epic definition or with the WDS prototype, raise the conflict before implementing — do not silently resolve it"), this was raised with the user at story-creation time rather than silently resolved either way. **User decision (2026-07-10): skip virtual scroll for this story** — implement the badge/polish work (AC #1-#4, #7) only; do not add a virtualization dependency or custom component. **This is explicitly a deferred future improvement, not an abandoned requirement** — logged in `deferred-work.md` to revisit once all epics are built, per the user's own framing ("we need this as improvement" at that later point). Reflex has no built-in virtualized list; satisfying AC #5/#6 literally would require wrapping an external React library (e.g. `react-window`) as a custom Reflex component — new architectural ground for this codebase, correctly out of scope for this pass.

### Project-context rules that bind this story
- **AD-7 (category taxonomy hard-constraint):** unaffected by this story — badges are a pure display concern layered on top of the already-constrained `category`/`category_source` values; no new category values are introduced.
- **AD-13 (currency/date formatting):** unaffected — no new currency/date rendering in this story.
- **"Raw confidence percentages never shown" (AC #4, sharpened by project-context's Agent-Misread Guards spirit):** `category_confidence` must never appear as a formatted number/percentage in any page template — Task 4's structural guard test enforces this goes forward, not just today.
- **Performance Rules ("not as speculative gold-plating on a single-user local MVP"):** directly informs the virtual-scroll decision above — this AD is why deferring, not building, an unneeded virtualization layer is the architecturally correct call for this MVP phase, not just an expedient shortcut.
- **Honest testing split** (every story since 1.4): `TxnRow`/`_to_row`/the pure chip-filter functions are fully unit-testable and must be (Task 5). The `rx.State`/component rendering wiring (Task 2's nested `rx.cond`) is app-verified only (`reflex compile` + the full suite) — this project's established, repeatedly-reaffirmed limitation (no browser driver in this environment).

### Previous story intelligence (Story 3.3)
- **`CategorySource` is already imported** in `finance_app/state/transactions_state.py` (added during Story 3.3's code-review pass for `save_correction`'s single-row-update branch) — Task 1 needs no new import for it, only for the `is_ai` comparison itself.
- **Story 3.3's `save_correction` always writes `category_confidence=1.0`/`category_source='user'`** (both the re-apply-all and single-row paths) — a corrected row must always land as `is_ai=False`, `needs_review=False` (no badge) after this story's changes; Task 5 includes a regression test for this specific interaction between the two stories.
- **Extract pure functions, test them** — the pattern this project has now applied on every story since 3.1 (`transactions_state.py`'s chip/filter functions, `summarize_categorization`, `teach_me.py`'s three functions). This story's `is_ai` field and the fixed `needs_review` formula continue that pattern — both live in `_to_row`, already a pure/session-injected function, not inline in an `rx.State` handler.
- **`reflex compile` is the standing verification step** for any new `rx.cond`/component wiring in this codebase — run it after Task 2, same as every prior UI-touching story.

### References
- [Source: epics.md#Story-3.4-Confidence-Badges] (lines 508–524) — acceptance criteria origin
- [Source: prototypes/01-priyas-first-honest-morning-Prototype/01.4-transactions-table.html] — `badgeFor()` (the exact 3-state badge logic and CSS classes this story reproduces), full-list rendering with no virtualization
- [Source: prototypes/01-priyas-first-honest-morning-Prototype/shared/styles.css] — `.txn-badge`, `.txn-badge--review`, `.txn-badge--ai`, `.txn-badge--none` (already present, unused by `.txn-badge--ai` until this story)
- [Source: _bmad-output/C-UX-Scenarios/01-priyas-first-honest-morning/01.4-transactions-table/01.4-transactions-table.md] — "Technical Notes" section, the pre-existing virtual-scroll doubt this story's Task 3 resolves
- [Source: services/utils/enums.py] — `CategorySource` (`rule`/`llm`/`user`)
- [Source: services/categorize/llm_categorizer.py] — Tier-2's real, LLM-self-reported `category_confidence` range (why the old `needs_review` formula misfires on `llm` rows)
- [Source: finance_app/state/transactions_state.py] — `TxnRow`, `_to_row`, `NEEDS_REVIEW_THRESHOLD`, the pure chip/filter functions this story extends
- [Source: finance_app/pages/transactions.py] — `_row()`'s current 2-way badge `rx.cond`, extended to 3-way by Task 2
- [Source: project-context.md] — Story Implementation Process rule #6 (raise epics-vs-WDS conflicts, don't silently resolve), Performance Rules ("not speculative gold-plating")
- [Source: 3-1 story](./3-1-tier-1-rules-engine-and-transactions-table.md), [3-3 story](./3-3-teach-me-user-correction-and-merchant-rules.md) — extract-pure-function precedent, `CategorySource` import provenance, the `save_correction` interaction Task 5 regression-tests

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (`bmad-create-story`, 2026-07-10)

### Debug Log References

- Confirmed via RED-phase test run (`AttributeError: 'TxnRow' object has no attribute 'is_ai'`) that the new tests genuinely exercised the not-yet-implemented field before writing the fix.
- `reflex compile` — Success, 32/31, confirming the nested `rx.cond` (badge) still compiles correctly with a third branch.

### Completion Notes List

- **Task 1** — `TxnRow` gained `is_ai: bool`; `_to_row` now computes `is_ai = txn.category_source == CategorySource.llm.value` and the fixed formula `needs_review = (not is_ai) and confidence < NEEDS_REVIEW_THRESHOLD`. This closes the actual bug the story exists to fix: Tier-2's self-reported confidence is essentially never exactly `1.0`, so every AI-categorized row would otherwise have shown the amber "needs review" badge instead of the blue "AI" badge. `NEEDS_REVIEW_THRESHOLD` itself is unchanged (still `1.0`) — the `is_ai` short-circuit is the whole fix.
- **Task 2** — `finance_app/pages/transactions.py`'s `_row()` badge `rx.cond` extended from 2-way to 3-way (`needs_review` → amber "?"; else `is_ai` → blue "AI"; else → none). Reused the WDS prototype's exact `.txn-badge--ai` class and `"AI-categorised"` aria-label — no new CSS needed, the class already existed in `assets/wds.css` unused.
- **Task 3** — Virtual scroll (AC #5/#6) intentionally **not implemented**, per the user's explicit decision at story-creation time: the WDS prototype (UI source of truth) renders a full plain list at any row count, and the project's own UX-scenario notes for this screen had already flagged virtual scroll as likely unnecessary on a desktop-only MVP. Documented in the page's module docstring and tracked in `deferred-work.md` as a genuine future improvement (not a dropped requirement), to revisit once all epics are built.
- **Task 4** — New `tests/test_transactions_page_structure.py` structurally guarantees AC #4 two ways: `TxnRow` carries no confidence-named field at all (so the page has nothing to accidentally render even if someone tried), plus a defense-in-depth text scan confirming the page module's source never references `category_confidence` directly.
- **Task 5** — 10 new/updated tests across `tests/test_transactions_state.py` (llm-sourced rows at both low and full self-reported confidence are unconditionally `is_ai=True`/`needs_review=False`; the pre-existing `rule`-sourced 0.5-confidence "Transfer In" fallback still correctly flags `needs_review=True`, `is_ai=False` — proving Task 1's exclusion logic didn't weaken it; `rule`/`user`-sourced full-confidence rows show no badge; AI-categorized rows are correctly included in the category chip/filter functions; two direct AC #7 self-consistency tests) plus 2 new structural-guard tests. Full suite: **249 passed** (239 baseline + 10 new), zero regressions. `reflex compile` — Success, 32/31.
- **Honest testing split** (every story since 1.4): `TxnRow`/`_to_row`'s new `is_ai` logic and the chip/filter functions are fully unit-tested (pure/session-injected). The `rx.State`/component rendering wiring (Task 2's nested `rx.cond`) is app-verified only (`reflex compile` Success) — this project's established, repeatedly-reaffirmed limitation (no browser driver in this environment); a manual browser pass (upload a statement with a mix of rule/AI/needs-review rows, confirm all three badge states render correctly) is recommended before demo.

### Code Review (2026-07-10)

Three parallel review layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor) ran against the isolated Story 3.4 diff. 0 decision-needed, 7 patch findings (all applied — a `TxnRow` mutual-exclusivity validator, the llm-sourced-yet-Uncategorized edge-case guard, a stale docstring fix, a `deferred-work.md` ledger cleanup, 2 new tests, an idiom-consistency fix, and a wording tightening), 3 deferred (the duplicated `1.0` confidence constant across 4 files, and two corrupted-data observability gaps — neither reachable via any current write path), 4 dismissed as noise. Full suite: **251 passed** (249 + 2 new), zero regressions. `reflex compile` — Success, 32/31.

### File List

**New**
- `tests/test_transactions_page_structure.py` — 2 tests (AC #4 structural guard)

**Modified**
- `finance_app/state/transactions_state.py` — `TxnRow.is_ai` field + mutual-exclusivity validator (review pass); `_to_row`'s `is_ai`/fixed `needs_review` computation, hardened against the llm-sourced-yet-Uncategorized edge case (review pass); `is_credit` aligned to the `Direction` enum (review pass); stale threshold docstring fixed (review pass)
- `finance_app/pages/transactions.py` — 3-way badge `rx.cond`; module docstring updated (badge classes, virtual-scroll decision)
- `tests/test_transactions_state.py` — 12 new/updated tests total (10 from dev pass, +2 from review pass: `category_source=None`, llm-sourced-yet-Uncategorized); `_row()` test helper default updated for the new required field
- `_bmad-output/implementation-artifacts/deferred-work.md` — virtual-scroll future-improvement entry (story-creation time) + Story 3.1's threshold entry closed out + 3 new review-pass deferrals

### Change Log

| Date | Change |
| --- | --- |
| 2026-07-10 | Story drafted (`bmad-create-story`). Resolved the badge-priority ambiguity in epics.md's AC wording (traced against the real `CategorySource` enum and the rules engine's existing 0.5-confidence fallback) and raised the virtual-scroll epics-vs-WDS conflict with the user before drafting rather than silently resolving it — user decision: skip virtual scroll, track as a future improvement. Status → ready-for-dev. |
| 2026-07-10 | `bmad-dev-story` run, all 5 tasks completed in order following red-green-refactor (RED confirmed via a real `AttributeError` before the fix). Fixed the latent `needs_review` formula bug (Tier-2 confidence was never being compared correctly), wired the 3-way badge, documented the virtual-scroll deviation, added a structural guard against ever rendering raw confidence, and added 10 new tests. Full suite 249 passed; `reflex compile` Success. Status → review. |
| 2026-07-10 | `bmad-code-review` run (3 parallel layers). 7 patches applied (a model-level invariant guard, a corrupted-data edge-case fix, doc/ledger cleanup, 2 new tests, an idiom fix, a wording fix), 3 deferred, 4 dismissed as noise. Full suite 251 passed; `reflex compile` Success. Status → done. Epic 3 (Transaction Categorization & Teach Me) is now fully complete. |
