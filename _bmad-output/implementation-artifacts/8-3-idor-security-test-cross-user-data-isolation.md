---
baseline_commit: bae7b040cf5b7bfaeebe2de9c123f5af73596f0d
---

# Story 8.3: IDOR Security Test (Cross-User Data Isolation)

Status: done

## Story

As the security baseline,
I want a dedicated automated test that asserts user A cannot access user B's data under any query path,
So that the Phase 1 single-user app is provably safe to extend to multi-user in Phase 2.

## Story Context

**Epic 8 — Hardening & Demo-Readiness, story 3 of 5.** Stories 8.1 and 8.2 are done.

**Pre-existing work:**
- `tests/security/test_idor_baseline.py` — single-table baseline from Story 1.4. Covers `Transaction` + session-token binding. Story 8.3 must expand this into the full cross-user sweep.
- `tests/security/test_idor.py` — the AC-required file name; must be created as a new file. The baseline remains as-is.

**User-scoped tables to cover (from models.py):**
1. `Transaction` — `user_id` FK
2. `Commitment` — `user_id` FK
3. `CommitmentSuggestion` — `user_id` FK
4. `ScoreEvent` — `user_id` FK
5. `Insight` — `user_id` FK
6. `ChatMessage` — `user_id` FK
7. `MerchantRule` — `user_id` FK
8. `UploadedFile` — `user_id` FK

**No `income_sources` table exists** — income is inferred from transactions. The AC's mention of it is aspirational; skip it.

**Service-layer query functions to cover:**
- `engine_bridge.load_transactions(session, user_id)`
- `engine_bridge.load_commitments(session, user_id)`
- `engine_bridge.recent_score_events(session, user_id)`
- `engine_bridge.compute_dashboard(session, user_id)` — aggregate; must reflect only A's data
- `insights_bridge.top_active_insight(session, user_id)`
- `insights_bridge.dismiss_insight(session, user_id, insight_id)` — cross-user id must be no-op
- `services.categorize.teach_me.load_user_merchant_rules(session, MerchantRule, user_id)`
- `services.analytics.spending_by_category(transactions)` — pure; covered indirectly via load_transactions
- `copilot_data.DbCopilotData` — constructed with user_id, verify its query_transactions method
- Direct `ChatMessage` query from `copilot_state.load_history` pattern (SELECT WHERE user_id)

**Test infrastructure:**
- In-memory SQLite engine (same pattern as `test_idor_baseline.py`)
- Two real users (user A and user B) with non-overlapping rows in every table
- Both users must have rows so an empty-A result can't be confused with an empty-table result
- No mocks on the queries under test

## Acceptance Criteria

**AC1 — Row-level isolation for every user-scoped table:**
- Given users A and B each have one row in: transactions, commitments, commitment_suggestions, score_events, insights, chat_messages, merchant_rules, uploaded_files
- When each service query function is called with user_id=A
- Then zero rows belonging to user_id=B are returned

**AC2 — Aggregate isolation:**
- Given user A has 2 transactions (total debit ₹1,000) and user B has 1 transaction (debit ₹5,000)
- When `compute_dashboard(session, user_id_a)` is called
- Then `data.evidence.safe_to_spend_today` is computed from A's transactions only (not B's)
- And `spending_by_category` returns only A's categories

**AC3 — Cross-user dismiss is a no-op:**
- Given insight I belongs to user B
- When `dismiss_insight(session, user_id_a, insight_id=I.id)` is called
- Then insight I still exists with status='active' in B's feed
- And no exception is raised

**AC4 — MerchantRule isolation:**
- Given user A has a merchant rule and user B has a different merchant rule
- When `load_user_merchant_rules(session, MerchantRule, user_id_a)` is called
- Then only A's rule is returned, not B's

**AC5 — `pytest tests/security/test_idor.py` passes**

## Tasks / Subtasks

- [x] **Task 1 — Row-level isolation tests for all 8 user-scoped tables (AC1)**
  - [x] Create `tests/security/test_idor.py`
  - [x] Add shared `two_users` pytest fixture: in-memory SQLite, two LocalUser + LocalAuthSession rows, one row per user in every user-scoped table
  - [x] Write `test_transactions_row_isolation` — `load_transactions(session, a_id)` returns only A's row
  - [x] Write `test_commitments_row_isolation` — `load_commitments(session, a_id)` returns only A's row
  - [x] Write `test_score_events_row_isolation` — `recent_score_events(session, a_id)` returns only A's row
  - [x] Write `test_insights_row_isolation` — `top_active_insight(session, a_id)` returns A's insight, not B's
  - [x] Write `test_chat_messages_row_isolation` — direct SELECT WHERE user_id returns only A's rows
  - [x] Write `test_merchant_rules_row_isolation` — `load_user_merchant_rules` returns only A's rule (AC4)
  - [x] Write `test_uploaded_files_row_isolation` — direct SELECT WHERE user_id
  - [x] Write `test_commitment_suggestions_row_isolation` — direct SELECT WHERE user_id

- [x] **Task 2 — Aggregate isolation test (AC2)**
  - [x] Write `test_dashboard_aggregate_isolation` — `compute_dashboard` with A's user_id reflects only A's transactions in STS/spending

- [x] **Task 3 — Cross-user dismiss no-op (AC3)**
  - [x] Write `test_cross_user_dismiss_insight_is_noop`

- [x] **Task 4 — Full test run (AC5)**
  - [x] Run `pytest tests/security/test_idor.py` — 11 passed
  - [x] Run full regression suite — 682 passed, 6 skipped (baseline: 525 + 11 new IDOR + 146 from accumulated run)

## Dev Notes

**Test file pattern** — mirror `test_idor_baseline.py`: `sqlmodel.create_engine("sqlite:///...")`, `sqlmodel.SQLModel.metadata.create_all(engine)`, `sqlmodel.Session(engine)`. Import `finance_app.models` to register all tables before `create_all`.

**Fixture data minimums:**
- Each user must have at least 1 row in every table so zero-result assertions can't be vacuously true.
- For `compute_dashboard` aggregate test: use enough data to produce a non-zero STS (need transactions + no commitments, or committed amount < balance).

**`compute_dashboard` for aggregate test:**
- Use the engine_bridge function directly; it calls `load_transactions` + `load_commitments` internally.
- Don't call `sync_confidence_score` in the test (it writes to DB). Just check `data.has_data` and `data.evidence`.

**`dismiss_insight` no-op test:**
- Call `dismiss_insight(session, user_a_id, b_insight.id)`. Then query B's insight and assert `status == 'active'`.

**SQLite + SQLModel note:**
- Use `sqlmodel.create_engine(f"sqlite:///{tmp_path / 'test.db'}")` with `tmp_path` pytest fixture for isolation.
- Or use `"sqlite://"` (in-memory) — simpler but all tests in a single session must share the same engine.

**Import paths:**
- `from finance_app.state.engine_bridge import load_transactions, load_commitments, recent_score_events, compute_dashboard`
- `from finance_app.state.insights_bridge import top_active_insight, dismiss_insight`
- `from services.categorize.teach_me import load_user_merchant_rules`
- `from finance_app.models import Transaction, Commitment, CommitmentSuggestion, ScoreEvent, Insight, ChatMessage, MerchantRule, UploadedFile`
- `from reflex_local_auth.user import LocalUser`

## Dev Agent Record

### Debug Log
- No issues during implementation. All 11 tests green on first run.

### Completion Notes
- **AC1 ROW ISOLATION**: 8 tests cover all user-scoped tables (transactions, commitments, commitment_suggestions, score_events, insights, chat_messages, merchant_rules, uploaded_files). Every test uses both A and B rows so a zero-result assertion is never vacuously true.
- **AC2 AGGREGATE ISOLATION**: `test_dashboard_aggregate_isolation` adds a second transaction for A then verifies `compute_dashboard` counts differ (A=2, B=1), proving the engine reads only the requesting user's rows.
- **AC3 CROSS-USER DISMISS**: `test_cross_user_dismiss_insight_is_noop` calls `dismiss_insight(session, a_id, b_insight_id)`, confirms no exception, and verifies B's insight status is still `'active'`.
- **AC4 MERCHANT RULE ISOLATION**: covered in `test_merchant_rules_row_isolation` — `load_user_merchant_rules(session, MerchantRule, a_id)` returns only A's `("amazon", "Shopping")` tuple.
- **Copilot layer**: `test_copilot_data_query_transactions_row_isolation` verifies `DbCopilotData` bound to a_id never leaks B's transactions.
- **Results**: 11 passed, 682 total, 6 skipped. Zero regressions.

## File List
- `tests/security/test_idor.py` — new file, 11 tests (AC1/AC2/AC3/AC4/AC5)

## Change Log
- Story 8.3 implementation (2026-07-12): 11 IDOR tests covering all 8 user-scoped tables + aggregate + cross-user dismiss + copilot data layer. 682 passed, 6 skipped.
