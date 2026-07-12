---
baseline_commit: bae7b040cf5b7bfaeebe2de9c123f5af73596f0d
---

# Story 8.2: Onboarding Empty States

Status: done

## Story

As a first-time user with no data uploaded,
I want every screen to show a welcoming, action-directing empty state rather than a blank page or "No data available",
So that I know exactly what to do next.

## Story Context

**Epic 8 — Hardening & Demo-Readiness, story 2 of 5.** Story 8.1 (edge-case honest refusals) is done. This story polishes the first-run experience across all four main pages.

**Gap analysis against current code (as of Story 8.2 start):**

1. **AC1 — Dashboard**: `_empty_state()` in `pages/dashboard.py` already shows the approved hero copy and "Upload your statement" CTA button (`DashboardState.go_upload`). The AC requires a "Step 1 of 3" visual hint to be visible — this indicator currently only appears on the Upload page's `.flow-topbar`. Need to add it to the dashboard empty state so users know where they are in the flow.

2. **AC2 — Transactions**: `_empty_state()` in `pages/transactions.py` exists but has the wrong copy ("Upload a statement and your transactions will show up here.") and is plain text with no link. AC requires: "Your transactions will appear here after you upload a statement." plus a clickable "Upload your statement" link.

3. **AC3 — Insights**: `EMPTY_COPY = "Insights will appear once I've analysed your statement."` in `insights_state.py` matches AC exactly. But `_empty_state()` in `pages/insights.py` renders `rx.el.p(EMPTY_COPY)` with no link. AC requires a "Upload your statement" link.

4. **AC4 — Copilot — two gaps**:
   - **Quick prompts always visible**: `_welcome_card()` shows chips when `CopilotState.messages.length() == 0`, regardless of whether the user has transactions. AC requires quick prompts hidden until data exists.
   - **No-data first response**: `send_message` calls `astream_events` unconditionally. AC requires: when the user has no transactions and sends their first message, the first response is the approved copy: "I don't have your transactions yet. Upload a statement and I'll be able to give you real answers." (no LLM call; synthetic response only).

**What this story does NOT deliver:**
- ❌ Copilot remains fully functional for registered users — the no-data gate only applies to users with zero transactions
- ❌ No new pages, no layout changes, no new services
- ❌ Story 8.3–8.5 content

## Acceptance Criteria

**AC1 — Dashboard empty state:**
- Given I have registered and no statement has been uploaded
- When I land on the Dashboard
- Then the hero area shows: "Upload a statement and I'll show you what's safe to spend — and why." (already correct)
- And a prominent "Upload your statement" CTA button is visible (already correct)
- And a "Step 1 of 3" visual hint is visible — so I know the upload is the first step

**AC2 — Transactions empty state:**
- Given I navigate to the Transactions page with no data
- When the page renders
- Then the page shows: "Your transactions will appear here after you upload a statement."
- And a "Upload your statement" link is present and navigates to `/upload`

**AC3 — Insights empty state:**
- Given I navigate to the Insights page with no data
- When the page renders
- Then the page shows: "Insights will appear once I've analysed your statement." (already correct)
- And a "Upload your statement" link is present and navigates to `/upload`

**AC4 — Copilot empty state:**
- Given I navigate to the Copilot page with no data (zero transactions)
- When I view the page
- Then the quick-prompt chips are hidden (not shown until data exists)
- And when I send any message, the first response is: "I don't have your transactions yet. Upload a statement and I'll be able to give you real answers."
- And no LLM call is made for the no-data response
- And the Copilot is otherwise functional — the input bar, welcome headline, and send button work normally

## Tasks / Subtasks

- [x] **Task 1 — Dashboard: add "Step 1 of 3" hint to empty state (AC1)**
  - [x] In `finance_app/pages/dashboard.py::_empty_state()`, add `rx.el.span("Step 1 of 3", class_name="step-indicator")` above (or below) the hero copy — matches the WDS prototype's `.step-indicator` class already in `assets/wds.css`
  - [x] Write `tests/ui/test_empty_states.py::test_dashboard_empty_state_has_step_indicator` — verify the `step-indicator` span is present in the empty-state component output

- [x] **Task 2 — Transactions: fix copy and add upload link (AC2)**
  - [x] Update `_empty_state()` copy in `finance_app/pages/transactions.py` to the AC2-approved string
  - [x] Add `rx.el.a("Upload your statement", href="/upload", class_name="link")` to the empty state
  - [x] Write `tests/ui/test_empty_states.py::test_transactions_empty_state_copy` and `test_transactions_empty_state_has_upload_link`

- [x] **Task 3 — Insights: add upload link (AC3)**
  - [x] In `finance_app/pages/insights.py::_empty_state()`, add `rx.el.a("Upload your statement", href="/upload", class_name="link")` after the existing `rx.el.p(EMPTY_COPY)`
  - [x] Write `tests/ui/test_empty_states.py::test_insights_empty_state_has_upload_link`

- [x] **Task 4 — Copilot: gate quick prompts on has_transactions (AC4a)**
  - [x] Add `has_transactions: bool = False` state var to `CopilotState`
  - [x] In `CopilotState.load_history()`, set `self.has_transactions` by querying the transaction count for the user (one `count(*)` query on `Transaction` table with `user_id` filter — AD-4)
  - [x] In `finance_app/pages/copilot.py::_welcome_card()`, wrap the chips div with `rx.cond(CopilotState.has_transactions, chips_div, rx.fragment())`
  - [x] Write `tests/ui/test_empty_states.py::test_copilot_quick_prompts_hidden_when_no_data`

- [x] **Task 5 — Copilot: no-data response on first message (AC4b)**
  - [x] In `CopilotState.send_message()`, before building the API call, check `self.has_transactions`. If False, emit a synthetic assistant response with the AC4-approved copy, persist it (both user turn and bot turn to DB), and return early — no LLM call
  - [x] The synthetic response text: `"I don't have your transactions yet. Upload a statement and I'll be able to give you real answers."`
  - [x] Write `tests/ui/test_empty_states.py::test_copilot_no_data_response_copy` — verify the correct copy constant exists
  - [x] Write `tests/ui/test_empty_states.py::test_copilot_has_transactions_var_exists` — structural check

- [x] **Task 6 — Full test run (AC1–AC4)**
  - [x] Run `pytest tests/ui/test_empty_states.py` — 10 passed
  - [x] Run full regression suite — 523 passed, 6 skipped (baseline 513 + 10 new)

## Dev Notes

**Key files to read before starting:**
- `finance_app/pages/dashboard.py` — `_empty_state()` at line ~267
- `finance_app/pages/transactions.py` — `_empty_state()` at line ~129
- `finance_app/pages/insights.py` — `_empty_state()` at line ~49
- `finance_app/state/insights_state.py` — `EMPTY_COPY` constant at line ~26
- `finance_app/pages/copilot.py` — `_welcome_card()` at line ~140
- `finance_app/state/copilot_state.py` — `send_message` event handler; imports

**Architecture constraints:**
- AD-2: Nothing in `services/` touched — all changes are in `pages/` and `state/`
- AD-4: The `has_transactions` DB query in `load_history` must include an explicit `user_id` filter
- The synthetic no-data Copilot response should be persisted to DB (both user + bot turns) so it appears in chat history on re-load. Use the same persist pattern as the real `send_message`.

**CSS class notes:**
- `.step-indicator` is already defined in `assets/wds.css` (line 207) — same class as upload page
- `.link` for plain anchor links — check `assets/wds.css` for the exact class; use what's already there
- The empty state components live inside the existing page layout (no new layout scaffolding)

**Copilot `has_transactions` query:**
```python
from sqlmodel import select, func
from finance_app.models import Transaction as TxnModel

count = session.exec(
    select(func.count()).select_from(TxnModel).where(TxnModel.user_id == user_id)
).one()
self.has_transactions = count > 0
```

**Test file location:** `tests/ui/test_empty_states.py` — new file. Tests use component introspection (checking `rx.Component` return values for expected child text/attributes) rather than a browser. Pattern established in existing component unit tests if any; if none exist, test by instantiating the component and checking its `children` / `props` structure, or test the constant strings and state var presence directly (as Story 8.1 tests did for `ai_caveat`).

## Dev Agent Record

### Debug Log
- `_collect_hrefs` initially looked at `component.props["href"]` — Reflex's `rx.el.a` creates `ReactRouterLink` which stores the path in the `to` field, not `href`. Fixed helper to check `to` first.
- `to` field returns JSON-quoted string (`'"/upload"'`) — added `_unwrap()` JSON parser in test helpers to normalize to plain string.
- Dashboard `_collect_text` initially missed text — Reflex children are `Bare` nodes with `contents` holding JSON-quoted strings, not plain Python strings. Fixed `_collect_text` to call `_bare_text()`.

### Completion Notes
- **AC1 DASHBOARD**: Added `rx.el.span("Step 1 of 3", class_name="step-indicator")` to `dashboard.py::_empty_state()`. Existing hero copy and CTA were already correct.
- **AC2 TRANSACTIONS**: Updated copy to "Your transactions will appear here after you upload a statement." and added `rx.el.a("Upload your statement", href="/upload", class_name="link")`.
- **AC3 INSIGHTS**: Added `rx.el.a("Upload your statement", href="/upload", class_name="link")` to `insights.py::_empty_state()`. Existing copy was already correct.
- **AC4a COPILOT QUICK PROMPTS**: Added `has_transactions: bool = False` to `CopilotState`. Set by `count(*)` query in `load_history()` (AD-4 compliant). Quick-prompt chips div wrapped in `rx.cond(CopilotState.has_transactions, ...)` in `_welcome_card()`.
- **AC4b COPILOT NO-DATA**: Added `COPILOT_NO_DATA_RESPONSE` constant. `send_message()` returns a synthetic persisted response when `has_transactions` is False — no LLM call made.
- **Tests**: 10 new tests in `tests/ui/test_empty_states.py`. Used Reflex component introspection pattern with `Bare`-node text extraction and `ReactRouterLink.to` field for link checks.
- **Results**: 523 passed, 6 skipped. Zero regressions.

## File List
- `finance_app/pages/dashboard.py` — added `rx.el.span("Step 1 of 3", class_name="step-indicator")` to `_empty_state()`
- `finance_app/pages/transactions.py` — updated `_empty_state()` copy + added upload link
- `finance_app/pages/insights.py` — added upload link to `_empty_state()`
- `finance_app/state/copilot_state.py` — added `COPILOT_NO_DATA_RESPONSE` constant; `has_transactions` state var; transaction count query in `load_history()`; no-data early-return in `send_message()`; updated imports (`func`, `TxnModel`)
- `finance_app/pages/copilot.py` — gated quick-prompt chips on `CopilotState.has_transactions`
- `tests/ui/__init__.py` — new file (package)
- `tests/ui/test_empty_states.py` — new file, 10 tests covering AC1/AC2/AC3/AC4

## Change Log
- Story 8.2 implementation (2026-07-12): Dashboard step-indicator; Transactions copy + upload link; Insights upload link; Copilot has_transactions var + quick-prompt gate + no-data synthetic response. 523 passed, 6 skipped.
