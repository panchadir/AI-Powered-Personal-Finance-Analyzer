---
baseline_commit: bae7b040cf5b7bfaeebe2de9c123f5af73596f0d
---

# Story 8.1: Edge-Case Honest Refusals

Status: done

## Story

As the system handling unexpected or degenerate inputs,
I want every failure mode to surface an honest, plain-language message — never a raw exception, never a silently wrong result,
so that the app's honesty promise holds under adversarial conditions.

## Story Context

**Epic 8 — Hardening & Demo-Readiness, story 1 of 5.** All prior epics (1–7) are done. This story firms up the ingestion edge cases plus two runtime degradation paths: the no-income STS guard and the Tier-2 LLM categorization fallback caveat.

**What this story delivers:**

1. **`EMPTY_STATEMENT` error code + honest copy** — when a PDF or CSV parses to zero transactions, raise a typed `IngestionError(code="EMPTY_STATEMENT")` with the approved copy from Story 8.1's AC. The current `validate_statement()` already refuses a zero-byte file; this closes the gap for a non-empty file that yields zero transactions (e.g. a valid PDF of account terms, not a statement).

2. **`NO_TEXT_LAYER` already exists** — `ScannedPDFError(code="NO_TEXT_LAYER")` is already defined in `services/ingestion/errors.py` and raised by `PDFParser`. The upload handler already catches `IngestionError` and surfaces `exc.message`. AC #2 is already satisfied. The test verifying it is Story 8.1's contribution (the existing `tests/ingestion/test_pdf_parser.py` covers `ScannedPDFError` being raised; we add a test asserting the approved UI copy).

3. **STS no-income guard already passes scenario 12** — `pytest tests/engine/test_safe_to_spend.py` scenario 12 (salary-not-detected) already passes per Story 4.3. The AC requires `pytest tests/engine/test_sts.py scenario 12` — the actual file is `tests/engine/test_safe_to_spend.py` and the 13 scenarios are already there. No new engine code needed; this AC just needs a test verifying the approved Dashboard copy displayed when `safe_to_spend_after_income` is None.

4. **Tier-2 failure caveat** — when the LLM categorizer fails, the upload state already logs and continues with Tier-1-only results. AC #4 requires: `category_source` stays `rule` for affected rows (already true), and the UI shows a dismissable caveat banner: `"AI categorisation was unavailable — some categories may need your review."` This requires adding an `ai_caveat: bool` var to `UploadState` and rendering it in `pages/upload.py`.

5. **`pytest tests/ingestion/` covering all four scenarios** — the AC says `pytest tests/ingestion/` covers empty statement, scanned PDF, scenario 12, and Tier-2 fallback. Tests in `tests/ingestion/` naturally cover scenarios 1–2; scenario 12 is in `tests/engine/` (already passing); the Tier-2 caveat is tested in a new `tests/ingestion/test_edge_cases.py` for the handler-level behavior.

**What this story does NOT deliver:**
- ❌ Story 8.2–8.5 content (empty states, IDOR test, README, demo dry-run)
- ❌ New ingestion error codes beyond `EMPTY_STATEMENT`
- ❌ Changes to the engine STS formula — scenario 12 already passes

## Acceptance Criteria

**AC1 — Empty statement (zero transactions):**
- Given a user uploads an empty PDF (zero bytes or zero parsed transactions)
- When ingestion processes it
- Then the typed `IngestionError` is raised with code `EMPTY_STATEMENT`
- And the UI shows: `"This file didn't contain any transactions I could read. Try your bank's CSV export or a different date range."` (approved UX copy)
- And no partial or empty transaction table is persisted

**AC2 — Scanned PDF (no text layer):**
- Given a user uploads a scanned-image PDF (no text layer)
- When pdfplumber returns zero text
- Then the typed `IngestionError` is raised with code `NO_TEXT_LAYER`
- And the UI shows: `"I can't read this one — it's a scanned image, not text. Try your bank's CSV export."` (approved UX copy from ux-spec-mvp.md)
- **Already implemented** — `ScannedPDFError` exists; this story verifies the message and adds a direct test.

**AC3 — No confirmed future income (STS guard):**
- Given no confirmed future income row exists
- When the STS engine runs
- Then STS does not divide by zero — falls back to reserved-only safe state
- And the Dashboard hero card shows: `"Upload your payday date so I can calculate your daily safe-to-spend."`
- And `pytest tests/engine/test_safe_to_spend.py` scenario 12 (salary-not-detected) passes
- **Engine already passes** — only UI copy verification needed.

**AC4 — Tier-2 LLM categorisation failure:**
- Given a user has uploaded a valid statement but the LLM categorisation Tier-2 call fails
- When categorisation falls back to rules-only
- Then the `category_source` for affected rows is `rule` (not `llm`)
- And the UI shows a dismissable caveat: `"AI categorisation was unavailable — some categories may need your review."`
- And no uncategorised rows are silently left with a null category

**AC5 — pytest tests/ingestion/ covers all four scenarios above**

## Tasks / Subtasks

- [x] **Task 1 — `EMPTY_STATEMENT` error in dispatch (AC1)**
  - [x] Add `EmptyStatementError(IngestionError)` with `code = "EMPTY_STATEMENT"` to `services/ingestion/errors.py`; update `__all__`
  - [x] In `services/ingestion/dispatch.py::parse_statement`, after calling `parser.parse(tmp_path)`, if the result is an empty list raise `EmptyStatementError("This file didn't contain any transactions I could read. Try your bank's CSV export or a different date range.")`
  - [x] Export `EmptyStatementError` from `services/ingestion/__init__.py`
  - [x] Write `tests/ingestion/test_edge_cases.py::test_empty_csv_raises_empty_statement_error` — a CSV with header-only (no data rows) → `EmptyStatementError` raised from `parse_statement`
  - [x] Write `test_empty_statement_error_code` — asserts `code == "EMPTY_STATEMENT"` and message contains "Try your bank's CSV export"

- [x] **Task 2 — Verify `NO_TEXT_LAYER` copy (AC2)**
  - [x] In `tests/ingestion/test_edge_cases.py`, added `test_scanned_pdf_error_code_and_message`, `test_scanned_pdf_error_is_ingestion_error`, `test_pdf_parser_raises_scanned_pdf_error_for_image_pdf` — all verify `NO_TEXT_LAYER` code and approved UX copy
  - [x] `ScannedPDFError` uses `SCANNED_MESSAGE` from `pdf_parser.py` (already correct approved copy)

- [x] **Task 3 — STS no-income dashboard copy (AC3)**
  - [x] Verified `pytest tests/engine/test_safe_to_spend.py -k "scenario_12"` passes (engine already implemented)
  - [x] Added `test_no_income_detected_flag_in_engine_evidence_pack` to `test_edge_cases.py`
  - [x] Updated `dashboard_state.py` `after_income_label` for `no_income_detected` branch to Story 8.1 AC3 approved copy: `"Upload your payday date so I can calculate your daily safe-to-spend."`

- [x] **Task 4 — Tier-2 caveat UI (AC4)**
  - [x] Added `ai_caveat: bool = False` to `UploadState`
  - [x] Set `self.ai_caveat = True` in Tier-2 except block in `_run_parse`
  - [x] Added `ai_caveat` to `reset_page()` reset
  - [x] Added `dismiss_ai_caveat` event handler to `UploadState`
  - [x] Added `_ai_caveat_banner()` component to `pages/upload.py` — dismissable amber banner using `.needs-review-banner` WDS class
  - [x] Added `test_tier2_failure_sets_ai_caveat_flag`, `test_ai_caveat_resets_on_reset_page`, `test_ai_caveat_flag_exists_on_upload_state` to `test_edge_cases.py`

- [x] **Task 5 — Full test run and story completion (AC5)**
  - [x] `pytest tests/ingestion/test_edge_cases.py` — 12 passed
  - [x] `pytest tests/ingestion/ tests/engine/ tests/categorize/ tests/narrate/ tests/security/ tests/utils/ tests/analytics/` — 509 passed, 6 skipped, zero regressions (baseline was 497)
  - [x] `pytest tests/test_service_boundary.py` — 4 passed
  - [x] File list complete

## Dev Notes

**Key files to read before starting:**
- `services/ingestion/errors.py` — add `EmptyStatementError` here
- `services/ingestion/dispatch.py` — add the post-parse empty-list check here
- `services/ingestion/__init__.py` — add export
- `finance_app/state/upload_state.py` — add `ai_caveat` var and set it in Tier-2 except block
- `finance_app/pages/upload.py` — add caveat banner render
- `tests/ingestion/test_edge_cases.py` — new test file

**Architecture constraints (project-context.md):**
- AD-12: typed `IngestionError` family only — `EmptyStatementError` must extend `IngestionError`
- No business logic in the `rx.State` handler — the empty-list check belongs in `services/ingestion/dispatch.py`, not the upload handler
- The upload handler already has the right `except IngestionError` catch at the identify step — `EmptyStatementError` bubbles up through it automatically
- AC4 Tier-2 caveat: the state var `ai_caveat` is set in the handler (correct — UI state lives in `rx.State`); the test can't test `rx.State` directly (Reflex test harness gap per deferred work); test the flag-setting logic via a helper or unit-test the service layer directly

**No-income copy location:**
Check `finance_app/state/dashboard_state.py` and `finance_app/pages/dashboard.py` for where `safe_to_spend_after_income is None` is handled — the copy should already be there from Story 5.1 (`"We couldn't detect a salary — add one manually?"`). AC3's exact required copy is `"Upload your payday date so I can calculate your daily safe-to-spend."` — reconcile if there's a mismatch (the epics.md copy differs from what Story 5.1 may have implemented; use the Story 8.1 AC copy as the authoritative version since this is the hardening pass).

**ScannedPDFError default message:**
The class currently does NOT have a default message — callers in `pdf_parser.py` pass the string. Check if the default should be added. For this story, just verify the test against the actual message emitted by `PDFParser`; don't change `pdf_parser.py`'s call site.

## Dev Agent Record

### Debug Log
- `test_pdf_parser_raises_scanned_pdf_error_for_image_pdf` initially returned a `pd.DataFrame` from the fake extractor — wrong type; `Extractor.extract()` returns `list[Transaction]`, not a DataFrame. Fixed to return `[]`.
- Story 8.1 AC3 copy (`"Upload your payday date..."`) differs from Story 5.1's original copy (`"We couldn't detect a salary — add one manually?"`). Updated the `no_income_detected` branch in `dashboard_state.py` to the Story 8.1 AC3 authoritative version.

### Completion Notes
- **AC1 EMPTY_STATEMENT**: `EmptyStatementError` added to `services/ingestion/errors.py`; post-parse empty-list check added to `dispatch.py::parse_statement`; exported from `__init__.py`. 4 tests cover it.
- **AC2 NO_TEXT_LAYER**: `ScannedPDFError` / `SCANNED_MESSAGE` already existed and were already raised by `PDFParser`. Added 3 tests verifying the code, copy, and behavior.
- **AC3 STS no-income guard**: Engine scenario 12 already passes. Added `test_no_income_detected_flag_in_engine_evidence_pack` cross-reference test. Updated `dashboard_state.py` `after_income_label` to Story 8.1 AC3 approved copy.
- **AC4 Tier-2 caveat**: Added `ai_caveat: bool = False` to `UploadState`, set in Tier-2 except block, reset in `reset_page()`. Added `dismiss_ai_caveat` handler. Added `_ai_caveat_banner()` to `pages/upload.py` using WDS `.needs-review-banner` class. 3 structural/behavioral tests.
- **AC5**: 509 passed, 6 skipped (baseline 497 + 12 new). Zero regressions. Service boundary tests green.

## File List
- `services/ingestion/errors.py` — added `EmptyStatementError`, updated `__all__`
- `services/ingestion/dispatch.py` — added `EmptyStatementError` import + empty-list check post-parse
- `services/ingestion/__init__.py` — added `EmptyStatementError` export
- `finance_app/state/upload_state.py` — added `ai_caveat` var, `dismiss_ai_caveat` handler, set flag in Tier-2 except block, reset in `reset_page()`
- `finance_app/pages/upload.py` — added `_ai_caveat_banner()` component, wired into page
- `finance_app/state/dashboard_state.py` — updated no-income copy to Story 8.1 AC3 text
- `tests/ingestion/test_edge_cases.py` — new file, 12 tests covering AC1/AC2/AC3/AC4

## Change Log
- Story 8.1 implementation (2026-07-12): EmptyStatementError + EMPTY_STATEMENT code; NO_TEXT_LAYER verification tests; Tier-2 caveat UI (ai_caveat flag + dismissable banner); no-income dashboard copy updated; 509 passed.
