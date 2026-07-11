---
baseline_commit: eecddd7b272053cb1a0045862003b28ffe2c15a3
---

# Story 1.5: Auth Confirmation UX, Validation Behavior & Nav Scaffold

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user registering or logging in,
I want inline validation feedback, an accessible registration-success confirmation, and a persistent navigation skeleton,
so that I can complete auth confidently and the nav is in place for all subsequent screens.

## Acceptance Criteria

Source: [epics.md — Story 1.5](../planning-artifacts/epics.md) (lines 319–339)

1. **Given** I am on the registration or login form, **When** I leave any field (blur event), **Then** validation fires immediately — on-submit-only validation is not acceptable. **And** error messages clear as I start typing (on input).
2. **Given** registration succeeds, **When** the success confirmation panel appears (replacing the form), **Then** the panel is `role="status"` with `aria-live="assertive"` on the `"Registration successful!"` headline. **And** it offers a `"Return to Login"` action and creates no session — no auto-login, no auto-redirect (product decision 2026-07-09).
3. **Given** any of the 4 app screens renders (Transactions, Dashboard, Insights, Copilot), **When** the page loads, **Then** a persistent left sidebar navigation (~200px) is visible with links to all 4 screens — even as a skeleton with placeholder routes for screens not yet built.

## Backfill note (why this story file appears after the fact)

This story was never run through `create-story` → `dev-story`. Its scope (blur validation, the nav scaffold) was built organically alongside Stories 1.3/1.4/the Epic-2 prep work in commit `ed482c5` ("epic1 completed") — a common pattern on this project (Epic 2's 5 stories similarly have no story files). `sprint-status.yaml` still showed `1-5: backlog`, which was stale: **AC #1 and AC #3 were already fully implemented**; only AC #2's `aria-live="assertive"` requirement had a real gap. This file was created retroactively (2026-07-10, during Epic 3 kickoff) to close that gap, verify the rest against the actual code, and give Story 1.5 an honest paper trail before marking it `done`.

## Tasks / Subtasks

- [x] **Task 1 — Blur-triggered validation + clear-on-input** (AC: #1) — **pre-existing, verified**
  - [x] `RegisterState` (`finance_app/state/auth_state.py`): `blur_email`/`blur_password`/`blur_confirm` set inline errors on blur; `change_email`/`change_password`/`change_confirm` clear them on input. Wired via `_field()`'s `on_blur=`/`on_change=` props in `finance_app/pages/register.py`.
  - [x] `LoginState`: same pattern — `blur_email`/`blur_password` + `change_email`/`change_password`, plus the forgot-password modal's own `blur_forgot_*`/`change_forgot_*` pairs. Wired in `finance_app/pages/auth.py`.
  - [x] Errors render with `role="alert"` (`_field()`'s error span in both pages) — confirmed present, not part of the literal AC but reinforces accessibility.

- [x] **Task 2 — Registration-success confirmation accessibility** (AC: #2)
  - [x] `_success_view()` (`finance_app/pages/register.py`) already had `role="status"` on the container, the `"Registration successful!"` headline, the "Your account has been created..." subtext, and a `"Return to Login"` link to `reflex_local_auth.routes.LOGIN_ROUTE` — no session/redirect (confirmed: `RegisterState.handle_registration` only sets `self.registration_success = True`, never calls `_login` or `rx.redirect`).
  - [x] **Gap found and fixed (2026-07-10):** the headline `<h2>` had no `aria-live` attribute — only the outer container had `role="status"`, which is necessary but not sufficient per the AC's literal wording ("`aria-live="assertive"` on the ... headline"). Added `aria_live="assertive"` directly to the `rx.el.h2("Registration successful!", ...)` call.
  - [x] Added `test_success_headline_has_aria_live_assertive` to `tests/test_register_page_smoke.py` — renders `_success_view()` and asserts `'"aria-live":"assertive"'` appears in the output, so this can't silently regress.

- [x] **Task 3 — Persistent left nav scaffold** (AC: #3) — **pre-existing, verified**
  - [x] `finance_app/components/nav.py` (`side_nav(active)`) renders the 4-tab sidebar (Dashboard/Transactions/Insights/Copilot Chat) + logout, mirroring the WDS prototype's `nav.js`/`renderSideNav` exactly (`.side-nav`, `.side-nav__tab`, `.is-active`, `aria-current="page"`).
  - [x] Wired into all 4 app pages: `finance_app/pages/{dashboard,transactions,insights,copilot}.py` each call `side_nav("<page>")` and are guarded by `on_load=AuthState.check_auth` (Story 1.4). Confirmed via direct read of all 4 files — no change needed.

- [x] **Task 4 — Regression check**
  - [x] Full `pytest` suite: **136 passed** (135 after Story 1.4's patches + 1 new aria-live test), zero regressions from the `aria_live` prop addition.
  - [x] Not re-verified live in-browser (no browser driver in this environment — same documented limitation as Stories 1.3/1.4); the component-render assertion (Task 2) is the closest available proof short of a live screen-reader pass, which folds into Epic 8's E2E per the existing precedent.

## Dev Notes

### What this story actually changed vs. what it found already done
Unlike Stories 1.1–1.4 (built forward from an empty page), this story's job was **audit + one targeted fix**, not net-new construction. Read this table before assuming anything here needs building:

| AC | State found | Action taken |
| --- | --- | --- |
| #1 (blur validation) | Fully implemented on both register and login forms, including the forgot-password modal | None — verified only |
| #2 (success a11y) | `role="status"` present; `aria-live="assertive"` **missing** on the headline | Added `aria_live="assertive"` to the `h2`; added a regression test |
| #3 (nav scaffold) | Fully implemented, wired to all 4 app pages | None — verified only |

### Why the gap survived this long
`role="status"` on the *container* already gives most screen readers a live-region announcement when the form is replaced by the success panel, so the missing `aria-live` on the *headline specifically* is a real but easy-to-miss gap — the panel "worked" in the sense of being announced, just not exactly per the AC's literal, more explicit contract (headline-level `aria-live="assertive"` guarantees immediate/interruptive announcement of that exact text, independent of how the container's `role="status"` polite-queue behavior resolves). Both attributes now coexist; that's intentional, not redundant to remove.

### Project-context rules that applied here
- **WDS baseline (project-context.md "UI/UX Baseline"):** the nav scaffold (Task 3) already follows this — same class names as the prototype's `nav.js`, no new layout invented. No action needed, just confirms the rule was already honored.
- **NFR-8 accessibility baseline:** `aria-live="assertive"` on the registration-success headline is explicitly named in NFR-8 — this story's Task 2 fix is what makes that NFR literally true, not just role="status"-adjacent.

### References
- [Source: epics.md#Story-1.5-Auth-Confirmation-UX] (lines 319–339) — acceptance criteria origin
- [Source: ARCHITECTURE-SPINE.md] — NFR-8 accessibility baseline (aria-live, aria-disabled, role="log")
- [Source: finance_app/pages/register.py] — `_success_view`, blur/change handlers wiring
- [Source: finance_app/pages/auth.py] — login + forgot-password blur/change handlers
- [Source: finance_app/state/auth_state.py] — `RegisterState`/`LoginState` blur/change event handlers
- [Source: finance_app/components/nav.py] — `side_nav`, mirrors prototype `nav.js`
- [Source: finance_app/pages/dashboard.py, transactions.py, insights.py, copilot.py] — nav wiring confirmation
- [Source: 1-4 story](./1-4-user-login-logout-and-protected-routes.md) — sibling Epic-1 story, same session's patch-and-close pattern

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (audit + targeted fix, 2026-07-10)

### Debug Log References

- Rendered `_success_view()` directly (`str(component.render())`) to confirm the `aria-live` prop compiles to `"aria-live":"assertive"` in the component tree before writing the assertion test.

### Completion Notes List

- AC #1 and AC #3 required no code changes — verified against the live codebase, not assumed from the (stale) `backlog` sprint-status entry.
- AC #2's `aria-live="assertive"` gap was real; fixed with a one-line prop addition plus a regression test.
- Full suite: 136 passed, no regressions.
- This story was completed in the same session as Story 1.4's review-patch cleanup, prompted by a request to verify whether 1.4/1.5 were actually done before continuing Epic 3 work.

### File List

**Modified**
- `finance_app/pages/register.py` — added `aria_live="assertive"` to the registration-success headline
- `tests/test_register_page_smoke.py` — added `test_success_headline_has_aria_live_assertive`

### Change Log

| Date | Change |
| --- | --- |
| 2026-07-10 | Backfilled story file after auditing the codebase against AC #1–#3. Found AC #1 and #3 already fully implemented (undocumented, from earlier ad-hoc work); found and fixed a real AC #2 gap (`aria-live="assertive"` missing on the registration-success headline). Added a regression test. Full suite 136 passed. Status → done. |
