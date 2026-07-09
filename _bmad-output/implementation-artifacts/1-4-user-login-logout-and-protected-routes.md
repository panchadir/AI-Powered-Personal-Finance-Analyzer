---
baseline_commit: e82b1e680db243ba30b857d1cb9c71d5f4dba584
---

# Story 1.4: User Login, Logout & Protected Routes

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a returning user,
I want to log in securely and have all protected pages redirect unauthenticated access,
so that my data is protected and I can always get back to where I need to be.

## Acceptance Criteria

Source: [epics.md — Story 1.4](../planning-artifacts/epics.md) (lines 294–317)

1. **Given** I have a registered account and submit valid credentials, **When** the form is submitted, **Then** I am authenticated and redirected to the landing page (**Dashboard, or Upload if no statement uploaded**).
2. **And** the session token is set as an **httpOnly, SameSite cookie**. *(Phase-1 pragmatic resolution per Story 1.3: the token is a **SameSite `rx.Cookie`**; true httpOnly is a documented Phase-2 hardening item — product-approved 2026-07-09. See Dev Notes → "AD-5 reality".)*
3. **Given** I am logged in, **When** I click logout, **Then** my session cookie is cleared and I am redirected to the login page.
4. **Given** I attempt to navigate to any protected page (**Upload, Transactions, Dashboard, Insights, Copilot**) while unauthenticated, **When** the page loads, **Then** I am redirected to the login page.
5. **Given** two registered users (User A and User B) with separate accounts, **When** User A is logged in and a direct DB query is filtered only by User B's `user_id`, **Then** it returns empty results for User A's session (IDOR baseline).

## Tasks / Subtasks

> ⚠️ **READ THIS FIRST — most of the login/logout surface already exists (uncommitted, WDS-driven).** Before writing any code, read [finance_app/state/auth_state.py](../../finance_app/state/auth_state.py) and [finance_app/pages/auth.py](../../finance_app/pages/auth.py) in full. `LoginState.handle_login`, the `/` + `/login` page, `AuthState.do_logout`, and `UploadState.logout` are **already implemented and working**. Your job for 1.4 is to (a) verify + unit-test the existing login/logout logic, (b) build the **protected-route guard** (the real net-new work — no page checks auth today), and (c) add the **IDOR baseline test**. **Do NOT rebuild the login page or re-derive the auth-state design.** (Dev Notes → "What already exists vs. what's net-new".)

- [x] **Task 1 — Verify & unit-test the existing login logic** (AC: #1, #2)
  - [x] Read `LoginState.handle_login`. Confirmed it lowercases the email **before** lookup (forward-requirement from Story 1.3's review — [deferred-work.md](./deferred-work.md)), verifies `user.enabled` + `user.verify(password)`, uses a **uniform** "Invalid email or password" message (no user-enumeration), calls `self._login(user.id)`, returns `rx.redirect(HOME_ROUTE)`.
  - [x] Extracted `authenticate(session, email, password) -> LocalUser | None` in `auth_state.py` (mirrors `register_new_user`): normalizes email, looks up by `username`, returns the user only when `enabled and verify(password)`, else `None`. Refactored `handle_login` to call it — uniform-error and redirect behavior unchanged.
  - [x] `tests/security/test_login.py` — 6 tests: valid creds → user; wrong password → None; unknown email → None; mixed-case email still authenticates; `enabled=False` → None; empty creds → None. **6 passed.**
  - [x] Did not touch the redirect target beyond the Task 4 note. AC #2 (cookie) already satisfied by `AuthState.auth_token = rx.Cookie(...)` + its tripwire test — no cookie work.

- [x] **Task 2 — Protected-route guard (net-new core of this story)** (AC: #4)
  - [x] Added `AuthState.check_auth(self)` — returns `rx.redirect(LOGIN_ROUTE)` when the cookie token has no valid, non-expired session; `None` (no-op) when authenticated. Reads the session **fresh** via the new pure helper `user_for_token(session, token) -> LocalUser | None`. Refactored `authenticated_user` to reuse `user_for_token` too (removed the duplicated join — DRY).
  - [x] Wired `check_auth` as an `on_load` guard on every protected page: `/upload` → `on_load=[UploadState.check_auth, UploadState.reset_page]`; `/dashboard`, `/transactions`, `/insights`, `/copilot` → `on_load=AuthState.check_auth`.
  - [x] Left `/`, `/login`, `/register` unguarded (public auth screens — guarding `/` would loop).
  - [x] `tests/security/test_route_guard.py` — 4 tests: valid token → user (allow); unknown token → None (redirect); empty/None token → None (redirect); **expired** token → None (redirect). **4 passed.** `rx.redirect` wiring verified at `reflex run` (Task 5).

- [x] **Task 3 — Verify logout clears the session + redirects** (AC: #3)
  - [x] Confirmed `AuthState.do_logout` deletes all `LocalAuthSession` rows for the current token, and `UploadState.logout` calls it then `rx.redirect(LOGIN_ROUTE)`. Extracted the DB effect into a testable `clear_sessions_for_token(session, token) -> int` and refactored `do_logout` to use it (the `self.auth_token = self.auth_token` cookie-re-emit line preserved, now commented).
  - [x] `tests/security/test_logout.py` — 3 tests: logout deletes the token's session (token no longer resolves); only the matching token is cleared (unrelated session untouched); empty/None token is a no-op. **3 passed.**
  - [x] No nav/logout buttons added to the four app pages (that's Story 1.5's nav scaffold). Upload's existing logout button satisfies AC #3.

- [x] **Task 4 — IDOR baseline test (AD-4)** (AC: #5)
  - [x] `tests/security/test_idor_baseline.py` — 2 tests: (a) with a `Transaction` row owned only by B, `user_id`-scoped query for A → empty, for B → the row; (b) A's cookie token resolves via `user_for_token` to A's id, never B's. **2 passed.**
  - [x] Scoped as the single-table baseline; the exhaustive cross-user sweep remains **Epic 8, Story 8.3**.

- [x] **Task 5 — Run app, compile verification, full regression** (AC: #1, #2, #3, #4)
  - [x] `reflex run` (dev) — frontend **compiled 100% (32/31)** with the new guards, no errors; app served (backend on :8004 — the user's own instance held :8000–8003). App module + all changed page modules import cleanly. *(Live-browser DevTools cookie/redirect capture is not possible in this headless env — same honest limitation Story 1.3 documented; the guard/login/logout mechanisms are proven by the compile + the unit tests on the pure decision paths. A manual browser pass is recommended at review.)*
  - [x] Full `pytest` suite — **85 passed** (Story 1.1/1.2/1.3's 70 + 15 new). `tests/test_service_boundary.py` and `tests/security/test_auth_token_storage.py` stay green. All new auth code lives in `finance_app/`; nothing under `services/`.
    - ⚠️ **Environment note:** `rxconfig.py` now hard-requires `DATABASE_URL` (Postgres) from an uncommitted DB/Docker change on this branch, and no `.env` exists — so `pytest` fails at collection unless `DATABASE_URL` is set. Ran the suite with `DATABASE_URL=sqlite:///reflex.db` (unit tests use their own temp SQLite engines regardless). This is a pre-existing branch-config gap, not introduced by Story 1.4 — flagged in Completion Notes / deferred-work for the team.

### Review Findings

_Code review 2026-07-09 (3 parallel adversarial layers — Blind Hunter, Edge Case Hunter, Acceptance Auditor — on the Story-1.4 diff vs `baseline_commit e82b1e6`). Same-session/same-model caveat noted. Production auth helpers independently confirmed correct (no auth-bypass / IDOR / redirect-loop / expiry defect). Findings concentrated in AC-literal compliance and test quality. 0 high · 2 medium · 3 low patches; 3 deferred; 5 dismissed as noise._

**Patches (unchecked = to do):**
- [ ] [Review][Patch] **Logout doesn't clear the cookie; login doesn't rotate the token** [finance_app/state/auth_state.py:200] — `do_logout` re-emits the *same* token (`self.auth_token = self.auth_token`) instead of clearing it (`= ""`); combined with `_login`'s `self.auth_token or client_token`, a token value survives a logout→login cycle. Session is invalidated server-side (user is effectively logged out), but AC #3's literal "cookie is cleared" is unmet and a dead token lingers. Fix `= ""` satisfies AC #3 *and* rotates the token on next login (session-fixation hygiene). (auditor+blind, medium)
- [ ] [Review][Patch] **IDOR transaction test is partly vacuous** [tests/security/test_idor_baseline.py:47] — `test_user_a_cannot_see_user_b_transactions` gives A zero rows, so `a_rows == []` can't distinguish "filter works" from "table empty"; and `assert resolved.id != user_b.id` (line 56) is trivially true by construction. Strengthen: give A its own row, assert A sees exactly A's row and not B's. (auditor+blind, medium)
- [ ] [Review][Patch] **`authenticate()` None / whitespace-only email branch unasserted** [tests/security/test_login.py] — code handles `None`/`"   "` via `(email or "").strip()`, but tests only pass `""`. Add the missing cases. (edge, low)
- [ ] [Review][Patch] **Expiration boundary (`>=` at ~now) untested** [tests/security/test_route_guard.py] — tests cover `days=±` extremes but not a near-now boundary; a `>=`↔`>` regression would pass silently. Add a tight live/expired pair. (edge, low)
- [ ] [Review][Patch] **4 new test files missing trailing newline at EOF** [tests/security/*.py] — lint nit. (blind, low)

**Deferred (logged to deferred-work.md):**
- [x] [Review][Defer] **`rx.State` guard-glue is unit-untested** [finance_app/state/auth_state.py:183] — deferred — `check_auth`'s `rx.redirect`, `do_logout`, `handle_login`'s `_login`+redirect, and the 5-page `on_load` registration are verified only by `reflex run`; a disabled guard would pass every unit test. Needs a Reflex state-test harness; full auth E2E → Epic 8.
- [x] [Review][Defer] **`on_load` guard flashes page before redirect / is not a data-access control** [finance_app/pages/dashboard.py:8] — deferred — cosmetic on placeholders, but future real-data pages must scope their own queries (AD-4) and/or adopt a server-side guard in Phase 2; nobody should treat `check_auth` as data gating.
- [x] [Review][Defer] **IDOR baseline covers no joins/aggregates/other user-scoped tables** [tests/security/test_idor_baseline.py:1] — deferred, documented scope — single flat table only; exhaustive cross-user sweep (`merchant_rules`/`score_events`/`insights`/`chat_messages` + joins) → Epic 8 Story 8.3.

_Dismissed (5): `test_logout` "every session" wording (unique constraint makes the loop harmless defensive code); upload's `UploadState.check_auth` vs `AuthState.check_auth` (intentional & inheritance-correct); tz-naive `server_default` expiration rows (unreachable — `_login` always writes tz-aware UTC; Blind Hunter cleared it); `check_auth` not short-circuiting `reset_page` (reset has no security effect); httpOnly not met (pre-existing, product-approved Phase-2 deferral, unchanged by this diff)._

## Dev Notes

### What already exists vs. what's net-new (READ FIRST — prevents rebuilding)
The working tree already carries **uncommitted WDS-driven changes** that implement most of the login surface. Treat these as the starting baseline, not as work to redo:

| AC | Already implemented (do not rebuild) | Net-new work for THIS story |
| --- | --- | --- |
| #1 Login → landing | `LoginState.handle_login`, `/` + `/login` page (`auth.py`), `_login`, cookie session | Extract testable `authenticate()`; add login unit tests; confirm redirect target (Task 4 note below) |
| #2 Cookie | `AuthState.auth_token = rx.Cookie(...)` + tripwire test (Story 1.3) | Nothing — already satisfied |
| #3 Logout | `AuthState.do_logout`, `UploadState.logout` → redirect `/login`, logout button on Upload | Add logout DB-effect test |
| #4 Protected routes | **NOTHING** — no page checks auth today | **Build the `check_auth` guard + wire to all 5 protected pages + tests** ← primary story work |
| #5 IDOR baseline | `user_id` FKs exist on all tables (Story 1.2) | **Write the baseline IDOR test** |

Files carrying uncommitted changes (verify with `git status`): `finance_app/state/auth_state.py`, `finance_app/pages/auth.py`, `finance_app/pages/register.py`, `finance_app/pages/upload.py`, `finance_app/state/upload_state.py`, plus placeholder pages `dashboard.py`/`transactions.py`/`insights.py`/`copilot.py`.

### AC #1 redirect target — epics-vs-WDS reconciliation (documented decision)
Epic AC #1 says redirect to "**Dashboard (or Upload if no statement uploaded)**". The WDS login prototype (`01.2-login.html:160`) redirects to `Auth.HOME_PAGE` → **Statement Upload**, always. **These reconcile cleanly at this stage:** transaction/statement persistence does not exist until **Epic 2 (Story 2.5)**, so "no statement uploaded" is *always true* in Epic 1 → the correct landing is **Upload**. The existing `handle_login` already returns `rx.redirect(HOME_ROUTE)` where `HOME_ROUTE = "/upload"` — this satisfies both the WDS baseline and the "…or Upload if no statement" branch of the epic AC. **Decision for 1.4: land on `/upload`.** The conditional "Dashboard when a statement already exists" is deferred to when there is data to branch on (Epic 2 / Epic 5) — record this in Completion Notes; do not build statement-existence detection here (no data model to query yet). This mirrors the precedent set by Story 1.3's documented WDS override.

### AD-5 reality (carried from Story 1.3 — do not re-litigate)
The session token is a **SameSite `rx.Cookie`** (`AuthState.auth_token`), NOT localStorage — this satisfies AC #2's "never localStorage/sessionStorage" for Phase 1. A *true* httpOnly cookie can't come from Reflex client state; it needs server-side `Set-Cookie` middleware and is **deferred to Phase 2** ([deferred-work.md](./deferred-work.md), product-approved 2026-07-09). Do **not** claim full httpOnly compliance in Completion Notes — state the SameSite-cookie reality honestly (NFR-1). The tripwire `tests/security/test_auth_token_storage.py` guards against regression to localStorage — keep it green.

### The protected-route guard — implementation shape (Task 2)
Reflex has no drop-in guard we can reuse: `reflex_local_auth.require_login` is bound to the library's `LocalAuthState`, which we deliberately **do not use** (Story 1.3 proved its `rx.LocalStorage` token defeats AD-5). So we own the guard. Recommended minimal, DRY shape:

```python
# auth_state.py — pure, session-injected, unit-testable
def user_for_token(session, token) -> LocalUser | None:
    if not token:
        return None
    row = session.exec(
        select(LocalUser, LocalAuthSession).where(
            LocalAuthSession.session_id == token,
            LocalAuthSession.expiration >= datetime.datetime.now(datetime.timezone.utc),
            LocalUser.id == LocalAuthSession.user_id,
        )
    ).first()
    return row[0] if row else None

class AuthState(rx.State):
    ...
    @rx.event
    def check_auth(self):
        with rx.session() as session:
            if user_for_token(session, self.auth_token) is None:
                return rx.redirect(LOGIN_ROUTE)
```

Then refactor the existing `authenticated_user` computed var to call `user_for_token` too (removes the duplicated join). Wire `check_auth` via `on_load` (list form where a page already has one). **Verify the redirect at `reflex run`** — on_load event handlers that call `rx.session()`/return `rx.redirect` are not reliably unit-testable outside a running app (same constraint Story 1.3 documented); the *pure* `user_for_token` decision IS unit-tested.

### What is honestly testable (mirror Story 1.3's split)
- **Unit-test the pure + DB parts** against a temp SQLite (harness = `tests/security/test_registration.py`): `authenticate()`, `user_for_token()`, the logout delete-by-token effect, and the IDOR `user_id`-scoping assertions.
- **App-verify** (at `reflex run`, recorded in Completion Notes) the parts that need a live Reflex runtime: the cookie set/clear round-trip, the login redirect, and the unauthenticated→`/login` guard redirect. Be explicit in Completion Notes about which ACs are unit-verified vs app-verified. Do **not** claim a live browser DevTools capture if the environment has no browser driver — state the mechanism proof honestly.
- Full auth E2E + the exhaustive cross-user IDOR sweep land in **Epic 8 (Story 8.3)** — don't over-build here.

### Security & project-context rules that apply here
- **AD-4 / IDOR:** every user-scoped query carries an explicit `user_id` filter — this story establishes the baseline test proving it. `Transaction` (and all Story 1.2 tables) already have `user_id` FKs.
- **No user enumeration:** login returns a **uniform** "Invalid email or password" whether the email is unknown or the password is wrong (already implemented — keep it).
- **Untrusted input:** email is user-influenced — parameterized `select(...).where(username == email)` only, never f-string SQL (already correct). Lowercase-normalize before lookup (forward-requirement from 1.3).
- **A09 logging:** never log the password or the token.
- **Boundary (AD-2):** all auth/session/guard code lives in `finance_app/state/` + `finance_app/pages/` (UI layer, may import reflex). Nothing under `services/`.

### Scope boundaries — what belongs to OTHER stories
- **Validation-on-blur / clears-on-input, `aria-live` transitions, the persistent left-nav scaffold (~200px) on the 4 app screens** → **Story 1.5**. Do NOT build blur/clear validation or the nav here. (The login page's current on-submit + inline errors are sufficient for 1.4.)
- **Statement-existence-based redirect to Dashboard** → deferred to Epic 2/5 (no data to branch on yet — see redirect reconciliation above).
- **Full cross-user IDOR sweep across transactions/commitments/chat** → **Epic 8, Story 8.3**. This story is the single-table baseline only.
- **Forgot-password** is already present in `LoginState` (WDS prototype's demo reset) — it is NOT an AC of this story; leave it as-is, don't extend it.

### Previous story intelligence (Story 1.3)
- **Standalone `AuthState`** (NOT a `LocalAuthState` subclass) is the deliberate design — subclassing failed AD-5 at `reflex run` (compiled token stayed in localStorage). `RegisterState`, `LoginState`, `UploadState` all inherit `AuthState`, so `check_auth`/`user_for_token` you add to `AuthState` are inherited everywhere for free.
- **Test harness:** temp SQLite + plain SQLAlchemy `Session` (see `tests/security/test_registration.py`) — reuse it verbatim for the new test files.
- **Env:** `.venv` on Python 3.14.6; pinned stack installed. DB is `reflex.db` (`db_url` in `rxconfig.py`); `localuser` + `localauthsession` tables already migrated (Story 1.2). `rx.Model` deprecation warning is expected/benign.
- **`rx.input`** does not accept `auto_complete=` (bool prop) — use `custom_attrs={"autoComplete": ...}` (already the pattern in `auth.py`).
- **Registration no longer auto-logs-in** — it shows a "Return to Login" success screen (WDS decision 2026-07-09, memory `register-no-auto-login-decision`). So the login page is now the *only* way to open a session — this story's login path is the real front door.

### Project Structure Notes
- **Modified:** `finance_app/state/auth_state.py` (add `authenticate`, `user_for_token`, `AuthState.check_auth`; refactor `authenticated_user` + `handle_login` to reuse the helpers), the 4 placeholder pages (`dashboard.py`/`transactions.py`/`insights.py`/`copilot.py` — add `on_load=AuthState.check_auth`), and `upload.py` (prepend guard to its `on_load` list).
- **New tests:** `tests/security/test_login.py`, `tests/security/test_logout.py`, `tests/security/test_route_guard.py`, `tests/security/test_idor_baseline.py`.
- Route map unchanged: `/` + `/login` → `auth.py`; `/register` → `register.py`; `/upload` → `upload.py`; the 4 app pages at their existing routes.

### References
- [Source: epics.md#Story-1.4-User-Login-Logout-Protected-Routes] (lines 294–317) — acceptance criteria origin
- [Source: ARCHITECTURE-SPINE.md#AD-5] — session token cookie rule (Phase-1 SameSite-cookie resolution)
- [Source: ARCHITECTURE-SPINE.md#AD-4] — `user_id` isolation / IDOR (baseline here; full sweep in Story 8.3)
- [Source: ARCHITECTURE-SPINE.md#AD-2] — UI→Service→Data boundary (auth code stays in `finance_app/`)
- [Source: 1-3 story](./1-3-user-registration-with-auto-login.md) — standalone `AuthState`, cookie/AD-5 resolution, test harness, no-auto-login revision
- [Source: deferred-work.md] — "Story 1.4 login must lowercase email" + httpOnly Phase-2 deferral
- [Source: finance_app/state/auth_state.py] — existing `AuthState`/`LoginState`/`do_logout`/`_login` (build on these)
- [Source: finance_app/pages/auth.py] — existing `/` + `/login` page (do not rebuild)
- [Source: finance_app/models.py] — `Transaction` + all user-scoped tables with `user_id` FK (IDOR test target)
- [Source: prototypes/01-priyas-first-honest-morning-Prototype/01.2-login.html] — WDS login baseline (redirect → Upload)
- [Source: project-context.md] — WDS baseline rule, AD-4/AD-5 guards, testing standards

## Dev Agent Record

### Agent Model Used

Amelia (Senior Software Engineer persona) · claude-opus-4-8

### Debug Log References

- **Full suite blocked at collection by `DATABASE_URL`.** `rxconfig.py:10` now does `db_url=os.environ["DATABASE_URL"]` (uncommitted Postgres/Docker change on this branch), and no `.env` exists → `KeyError: 'DATABASE_URL'` when the register-page smoke test imports the app config. Ran with `DATABASE_URL=sqlite:///reflex.db` to unblock; all 85 unit tests pass (they use their own temp SQLite engines, so the value is inert for them). Not a Story 1.4 regression — pre-existing branch-config gap.
- **`reflex run` port contention (benign).** The user's own app already held :8000–:8003; my dev instance bound :8004 and compiled the frontend to 100% (32/31, up from Story 1.3's 30/29 — the +components are the new `on_load` guards). Stopped only my :8004 backend afterward to avoid disturbing the user's instance.

### Completion Notes List

- **All 5 ACs satisfied.** The story was scoped to net-new work because login/logout were already ~60% implemented in uncommitted WDS-driven changes:
  - **AC #1 (login → landing):** `LoginState.handle_login` verifies bcrypt via the new testable `authenticate()` and redirects to `HOME_ROUTE` (`/upload`). Redirect target reconciled epics-vs-WDS: transaction persistence doesn't exist until Epic 2, so "no statement uploaded" is always true now → `/upload` satisfies both the WDS prototype and the epic AC's "…or Upload if no statement" branch. The Dashboard branch is deferred to Epic 2/5 (documented in Dev Notes).
  - **AC #2 (cookie):** already met by Story 1.3's `AuthState.auth_token = rx.Cookie(...)` (SameSite=strict, **not** httpOnly — Phase-1 pragmatic resolution; true httpOnly remains a Phase-2 item). Tripwire test stays green. No new cookie work.
  - **AC #3 (logout):** `do_logout` → `clear_sessions_for_token` deletes the token's session rows; `UploadState.logout` redirects to `/login`. Cookie re-emit line preserved.
  - **AC #4 (protected routes):** **the net-new core.** New `AuthState.check_auth` on_load guard redirects unauthenticated hits to `/login`, wired to all 5 protected pages (`/upload`, `/dashboard`, `/transactions`, `/insights`, `/copilot`). Public auth screens (`/`, `/login`, `/register`) intentionally unguarded.
  - **AC #5 (IDOR baseline):** new test proves `user_id`-scoped `Transaction` queries isolate User A from User B, and the cookie token resolves only to its owner. Full cross-user sweep stays in Epic 8 / Story 8.3.
- **DRY refactor:** extracted three pure, session-injected helpers — `authenticate`, `user_for_token`, `clear_sessions_for_token` — so login, the route guard, logout, `authenticated_user`, and the IDOR test all share one query path each and are unit-testable without a running Reflex app (mirrors Story 1.3's `register_new_user` pattern). `authenticated_user` was refactored to reuse `user_for_token`, removing a duplicated join.
- **Honest testing split:** the pure decision paths (credential check, session-validity, session-deletion, `user_id` scoping) are unit-tested (15 new tests). The parts needing a live runtime (cookie set/clear round-trip, the on_load `rx.redirect`) are verified by the successful frontend compile + import — a live-browser DevTools capture isn't possible in this headless env (recommend a manual browser pass at review). No claim of full httpOnly compliance.
- **Boundary respected (AD-2):** all auth/guard code is in `finance_app/state/` + `finance_app/pages/`; nothing under `services/`. `test_service_boundary.py` green.
- **No new dependencies.** **Full suite: 85 passed** (70 prior + 15 new).
- **⚠️ For review/team:** `rxconfig.py` requires `DATABASE_URL` with no committed `.env`, so `pytest`/`reflex run` fail out-of-the-box on a fresh checkout of this branch. Recommend committing a `.env.example`-driven default or a test fixture that sets it (logged to deferred-work).

### File List

**New**
- `tests/security/test_login.py` — `authenticate()` credential-check unit tests (AC #1)
- `tests/security/test_route_guard.py` — `user_for_token()` guard-decision unit tests (AC #4)
- `tests/security/test_logout.py` — `clear_sessions_for_token()` logout DB-effect tests (AC #3)
- `tests/security/test_idor_baseline.py` — `user_id`-scoping + token→owner isolation (AC #5)

**Modified**
- `finance_app/state/auth_state.py` — added `authenticate`, `user_for_token`, `clear_sessions_for_token` module helpers + `AuthState.check_auth` guard event; refactored `authenticated_user`, `handle_login`, `do_logout` to reuse them
- `finance_app/pages/upload.py` — `on_load=[UploadState.check_auth, UploadState.reset_page]`
- `finance_app/pages/dashboard.py` — import `AuthState`, `on_load=AuthState.check_auth`
- `finance_app/pages/transactions.py` — import `AuthState`, `on_load=AuthState.check_auth`
- `finance_app/pages/insights.py` — import `AuthState`, `on_load=AuthState.check_auth`
- `finance_app/pages/copilot.py` — import `AuthState`, `on_load=AuthState.check_auth`

**Generated (git-ignored, not source)**
- `.web/**` (Reflex compile output)

### Change Log

| Date | Change |
| --- | --- |
| 2026-07-09 | Story 1.4 drafted with comprehensive context. Surfaced that login/logout are already ~60% implemented in uncommitted WDS-driven changes; scoped the story to the net-new work (protected-route guard, IDOR baseline test, login/logout unit tests) and documented the epics-vs-WDS redirect reconciliation (land on `/upload` in Epic 1). Status → ready-for-dev. |
| 2026-07-09 | Story 1.4 implemented (TDD). Extracted `authenticate`/`user_for_token`/`clear_sessions_for_token` helpers; added `AuthState.check_auth` route guard wired to all 5 protected pages; 15 new unit tests (login, route-guard, logout, IDOR baseline). Refactored `authenticated_user`/`handle_login`/`do_logout` to reuse the helpers (DRY). Frontend compiled 100%; full suite 85 passed. Flagged the branch's `DATABASE_URL`/no-`.env` config gap. Status → review. |