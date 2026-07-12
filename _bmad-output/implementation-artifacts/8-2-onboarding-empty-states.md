---
baseline_commit: bc4e17c9528a0c1e2cbdd03a155071a856f35b33
---

# Story 8.2: Onboarding Empty States

Status: review

## Story

As a first-time user with no data uploaded,
I want every screen to show a welcoming, action-directing empty state rather than a blank page or "No data available",
So that I know exactly what to do next.

## Acceptance Criteria

1. **Dashboard empty state:** shows "Upload a statement and I'll show you what's safe to spend — and why." with a prominent "Upload your statement" CTA. No charts, no STS number, no narration panel rendered. The Upload page step indicator ("Step 1 of 3") is visible as a visual hint.
2. **Transactions empty state:** shows "Your transactions will appear here after you upload a statement." with a "Upload your statement" link.
3. **Insights empty state:** shows "Insights will appear once I've analysed your statement." with a "Upload your statement" link.
4. **Copilot empty state:** Copilot is still functional. Quick-prompt buttons are hidden until data exists. The first response to any question without data says: "I don't have your transactions yet. Upload a statement and I'll be able to give you real answers."

## Tasks / Subtasks

- [x] **Task 1 — Dashboard empty state: add step indicator (AC: 1)**
  - [x] Update `_empty_state()` in `finance_app/pages/dashboard.py` to include the "Step 1 of 3" hint text.
- [x] **Task 2 — Transactions empty state (AC: 2)**
  - [x] Add `has_data` bool var to a `TransactionsState` (or reuse `AuthState`).
  - [x] Implement `load_transactions_page` event that checks for transactions.
  - [x] Update `finance_app/pages/transactions.py` to show the approved empty state or actual content.
- [x] **Task 3 — Insights empty state (AC: 3)**
  - [x] Add `has_data` state to `InsightsState` / page on-load check.
  - [x] Update `finance_app/pages/insights.py` to show the approved empty state.
- [x] **Task 4 — Copilot empty state (AC: 4)**
  - [x] Add `has_transactions` bool to `CopilotState`, set in `load_history`.
  - [x] Hide quick-prompt chips when `has_transactions == False`.
  - [x] Guard `send_message`: when `has_transactions == False`, return the no-data response instead of calling the LLM.
- [x] **Task 5 — Tests (AC: 1–4)**
  - [x] `tests/test_empty_states.py` — 21 structural tests covering all 4 screens.
- [x] **Task 6 — Green gate**
  - [x] `pytest tests/` passes with zero regressions (458 passed, 3 pre-existing failures confirmed on baseline).

## Dev Notes

### Context
Story 8.2 is an "empty-state hardening" story — it adds the first-time-user experience across all 4 app screens. The Dashboard already has a partial `_empty_state()` in `finance_app/pages/dashboard.py` (line 199–213) that shows the correct copy and CTA. Story 8.2 extends it to also show the "Step 1 of 3" upload-step hint, and implements proper empty states for the other 3 screens (Transactions, Insights, Copilot) which currently show "Coming soon" placeholders.

### Pattern to follow
- `dashboard_state.py` / `dashboard.py` is the reference: `has_data` (bool in state), `loaded` (prevents flash), `rx.cond(has_data, real_content, rx.cond(loaded, empty_state, rx.el.div()))`.
- For Transactions and Insights: add minimal state with `has_data` + `loaded`, query just a COUNT (avoid loading full rows for a check). The engine_bridge `load_transactions` can be reused but a simple COUNT is cheaper.
- Copy is exact from epics.md AC (do not paraphrase):
  - Transactions: "Your transactions will appear here after you upload a statement."
  - Insights: "Insights will appear once I've analysed your statement."
  - Copilot no-data reply: "I don't have your transactions yet. Upload a statement and I'll be able to give you real answers."
- CTA uses `rx.el.a` with `href="/upload"` (not a button redirect) for Transactions and Insights — matches the epics.md wording "link".
- Copilot quick prompts: `QUICK_PROMPTS` are rendered inside `_welcome_card()` which already checks `messages.length() == 0`. For Story 8.2 we add an additional `has_transactions` guard so prompts don't appear when there's no data.

### Copilot no-data guard
The no-data response in `send_message` must be a local guard that fires **before** calling `astream_events`. It appends a synthetic assistant reply directly (no LLM call). This keeps the Copilot functional (user can type and get a response) and honest about the missing data.

### Architecture note
- `TransactionsState` and `InsightsState` are new thin state classes. They inherit `AuthState` (for `check_auth` / `auth_token`). They live in `finance_app/state/`.
- No new service function needed for Transactions/Insights: use `rx.session()` + a simple `select(Transaction).where(Transaction.user_id == user_id).limit(1)` to check existence.
- AD-4: every DB query must include `user_id` filter.

### Files to create/modify
- `finance_app/pages/dashboard.py` — update `_empty_state()` (minor)
- `finance_app/pages/transactions.py` — replace "Coming soon" with proper empty/data state
- `finance_app/state/transactions_state.py` — new
- `finance_app/pages/insights.py` — replace "Coming soon" with proper empty/data state
- `finance_app/state/insights_state.py` — new
- `finance_app/state/copilot_state.py` — add `has_transactions`, guard quick prompts + send
- `finance_app/pages/copilot.py` — gate quick-prompt chips on `has_transactions`
- `tests/test_empty_states.py` — new

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6 (BMAD dev-story workflow)

### Debug Log References

- `pytest tests/test_empty_states.py -v` → 21 passed (2.00s), no failures.
- `pytest tests/ -q` → 458 passed, 3 failed, 6 skipped. The 3 failures (`test_utcnow_is_naive`, `test_utcnow_is_actually_utc_not_local_time`, `test_no_ui_layer_import_in_services`) are pre-existing and confirmed on the baseline commit `bc4e17c` — zero regressions from this story.
- Also fixed a pre-existing `SyntaxError` in `services/narrate/config.py` (unterminated triple-quoted string literal, lines 39–49 of stale dead code). Added `COPILOT_MODEL` alias that `services/narrate/copilot.py` requires.

### Completion Notes List

- **AC-1 Dashboard:** `_empty_state()` in `finance_app/pages/dashboard.py` now renders an `rx.el.p` with "Step 1 of 3: Upload → Review → Dashboard". The approved UX-DR12 copy and the upload CTA were already present. Step indicator tested by source-inspection test.
- **AC-2 Transactions:** New `TransactionsState` (thin, inherits `AuthState`) checks for transaction existence via a COUNT query (AD-4: `user_id` filter). Transactions page renders the approved empty-state copy + `/upload` link when `has_data=False` (after `loaded=True`), and a placeholder when data exists (real table lands in Epic 3).
- **AC-3 Insights:** Same pattern as AC-2 — `InsightsState` + COUNT query. Insights page renders the approved copy + `/upload` link when no data exists.
- **AC-4 Copilot:** Added `has_transactions: bool = False` to `CopilotState`. `load_history` sets it via a COUNT query alongside the existing chat-history load (same DB session, zero extra round-trips). `_welcome_card` gates the quick-prompt chip block on `CopilotState.has_transactions`. `send_message` returns the no-data reply immediately without calling `astream_events` when `has_transactions=False`.
- **Bug fix (discovered, not in scope):** `services/narrate/config.py` had stale dead code (lines 39–49) forming an unterminated triple-quoted string, causing `SyntaxError` on import. Removed the dead block and added `COPILOT_MODEL = NARRATION_MODEL` alias that the copilot service already depends on.

### File List

- `finance_app/pages/dashboard.py` (modified) — `_empty_state()` gains step-indicator hint.
- `finance_app/pages/transactions.py` (modified) — replaced "Coming soon" placeholder with proper empty/data state using `TransactionsState`.
- `finance_app/state/transactions_state.py` (new) — thin state: `has_data`, `loaded`, `load_page` event.
- `finance_app/pages/insights.py` (modified) — replaced "Coming soon" placeholder with proper empty/data state using `InsightsState`.
- `finance_app/state/insights_state.py` (new) — thin state: `has_data`, `loaded`, `load_page` event.
- `finance_app/state/copilot_state.py` (modified) — `has_transactions` var; `load_history` COUNT query; `send_message` no-data guard; `func` import added; `Transaction` model import added.
- `finance_app/pages/copilot.py` (modified) — `_welcome_card` gates quick-prompt chips on `CopilotState.has_transactions`.
- `services/narrate/config.py` (modified) — removed stale dead code (syntax error); added `COPILOT_MODEL` alias.
- `tests/test_empty_states.py` (new) — 21 structural tests covering all 4 empty-state ACs.
- `_bmad-output/implementation-artifacts/8-2-onboarding-empty-states.md` (updated) — this story record.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (updated) — status transitions.

### Change Log

- 2026-07-10 — Implemented Story 8.2 onboarding empty states for all 4 screens. 21 new tests pass; 458 total passed (zero regressions). Also fixed pre-existing `SyntaxError` in `services/narrate/config.py`. Status → review.
