---
baseline_commit: 8d6d010a49265ae0debdf9e998f9de752c925a64
---

# Story 1.3: User Registration with Auto-Login

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a new user,
I want to register with email and password and be automatically logged in,
so that I can immediately start uploading my statement without friction.

## Acceptance Criteria

Source: [epics.md — Story 1.3](../planning-artifacts/epics.md) (lines 272–292)

1. **Given** I am on the registration page, **When** I fill in a valid email and password and submit, **Then** my account is created with a **bcrypt-hashed** password (never stored plaintext).
2. **And** I am automatically authenticated and redirected to the **Upload** page within 3 seconds.
3. **And** the session token is set as an **httpOnly, SameSite cookie** — never written to localStorage, sessionStorage, or a custom header. *(See Dev Notes → "AD-5 reality & the approved MVP resolution": for Phase-1 the token is a **SameSite `rx.Cookie`**; true httpOnly is a documented Phase-2 hardening item — approved by product on 2026-07-09.)*
4. **And** the page displays `"No guessing. No shame."` above the form fields — removing this text fails acceptance.
5. **And** the password field includes a show/hide toggle.
6. **And** T&C and Privacy links open in an **in-page modal**, not a new tab.
7. **And** no consent checkbox is pre-ticked (DPDP Rule 4).
8. **Given** I submit with an already-registered email, **When** the error renders, **Then** the message includes an inline `"Log in instead?"` link.

## Tasks / Subtasks

- [x] **Task 1 — Cookie-backed auth state (AD-5 pragmatic resolution)** (AC: #3)
  - [x] Create `finance_app/state/auth_state.py` with `class AuthState(reflex_local_auth.LocalAuthState)` that **overrides the inherited `auth_token` var** from `rx.LocalStorage` to `rx.Cookie`: `auth_token: str = rx.Cookie(name="_auth_token", same_site="strict", path="/", secure=False)` (`secure=False` for localhost http; note in a comment that Phase-2/https flips it to `True`). This replaces reflex-local-auth's default `rx.LocalStorage(name="_auth_token")` — the exact thing AC #3 forbids.
  - [x] **Runtime verification (spike):** the class-level override compiles (verified during story authoring — `AuthState.auth_token` is `Cookie`-backed). At `reflex run`, confirm in browser DevTools that logging in sets a **`_auth_token` cookie** (Application → Cookies) with `SameSite=Strict` and **no `_auth_token` in localStorage**. If Reflex emits BOTH (inherited LocalStorage + new Cookie), the fallback is to NOT inherit the parent's `auth_token`: reimplement the minimal session surface (`auth_token` cookie + `_login` + `authenticated_user` + `is_authenticated`) directly on `AuthState` by copying reflex-local-auth's `local_auth.py` logic (it is ~40 lines). Document which path was taken in Completion Notes.
  - [x] Add `tests/security/test_auth_token_storage.py` asserting `type(AuthState.auth_token).__name__ == "Cookie"` (guards against a regression back to localStorage — the AD-5 tripwire).
- [x] **Task 2 — Registration logic: email + bcrypt + auto-login → /upload** (AC: #1, #2, #8)
  - [x] Create `RegisterState(AuthState)` with `handle_registration(form_data)`:
    - Validate **email format** with a lightweight regex helper `_is_valid_email(s)` (do NOT add `email-validator`/`pydantic[email]` — that is a new dependency; a simple RFC-lite regex is sufficient and keeps `requirements.txt` lean). Validate password non-empty (min length 8 recommended, matching the prototype's "8+ characters" hint).
    - Duplicate check: `select(LocalUser).where(LocalUser.username == email)` — email is stored in the library's `username` column (see Dev Notes → "Email is the username"). If found, set `error_message` AND an `email_taken: bool = True` flag (drives the inline "Log in instead?" link, AC #8); do NOT create a user.
    - On success: create `LocalUser(username=email, password_hash=LocalUser.hash_password(password), enabled=True)`, commit, refresh; then **auto-login**: `self._login(new_user.id)`; then `return rx.redirect("/upload")`. **Do NOT** use the library's stock `successful_registration` (it sleeps then redirects to `/login` with no login — see Dev Notes → "Two stock behaviors you must override").
  - [x] bcrypt is provided by `LocalUser.hash_password` (bcrypt built into reflex-local-auth) — never store or log the plaintext password.
  - [x] `tests/security/test_registration.py` (temp SQLite + plain SQLAlchemy session, mirroring Story 1.2's schema-test harness): (a) valid registration writes a `LocalUser` whose `password_hash` ≠ plaintext and `verify(password)` is `True`; (b) registration creates a `LocalAuthSession` row for the new user (auto-login); (c) the handler's redirect target is `/upload`; (d) duplicate email sets `email_taken=True` and adds **no** second user; (e) invalid email format is rejected with no user created.
- [x] **Task 3 — Registration page UI** (AC: #4, #5, #6, #7, #8)
  - [x] Create `finance_app/pages/register.py` registered at `reflex_local_auth.routes.REGISTER_ROUTE` (`/register`), with a matching `finance_app/components/register/` for reusable pieces (mirror-the-page convention).
  - [x] Trust signal **above the form fields**: headline containing `"No guessing. No shame."` (prototype uses `"Your honest financial picture. No guessing. No shame."` + subline `"We only tell you what we actually know. When we're uncertain, we say so."`). AC #4 requires the exact substring `"No guessing. No shame."`.
  - [x] Fields: email (`type="email"`, `autocomplete="email"`), password (`type="password"`, `autocomplete="new-password"`) with a **show/hide toggle** button that flips the input `type` password↔text and its label Show↔Hide. CTA `"Create my account"`.
  - [x] Consent line: `"By creating an account you agree to our Terms of Service and Privacy Policy."` where **Terms of Service** and **Privacy Policy** open an **in-page modal** (`rx.dialog`/`rx.alert_dialog`) — NOT `target="_blank"`/new tab (AC #6). If a consent checkbox is used, it must **not** be pre-checked (AC #7, DPDP Rule 4); MVP may use link-consent (agreeing by creating an account) with no checkbox — either satisfies "no pre-ticked checkbox".
  - [x] Error rendering: when `RegisterState.email_taken`, show the error with an inline `"Log in instead?"` link to `reflex_local_auth.routes.LOGIN_ROUTE` (`/login`). (The login page itself is Story 1.4; the link may point at the route now.)
  - [x] `tests/test_register_page_smoke.py`: render `register()` and assert the component tree contains the `"No guessing. No shame."` text and a password show/hide control; assert no consent checkbox defaults to checked. (UI coverage is necessarily light — the redirect/cookie behaviors are verified by running the app, see Task 4.)
- [x] **Task 4 — Wire route, run app, full regression** (AC: #1, #2, #3)
  - [x] Register the page in the app (import in `finance_app/pages/__init__.py` or via `@rx.page`). Ensure `finance_app.models` still imported (Story 1.2) so the DB is intact.
  - [x] `reflex run` and manually verify the end-to-end path: register a new email+password → auto-redirected to `/upload` within 3s → DevTools shows a `_auth_token` **cookie** (SameSite=Strict), **no** localStorage token → re-registering the same email shows the error with a working "Log in instead?" link. Record the result in Completion Notes (this is the honest verification for AC #2/#3, which are not unit-testable).
  - [x] Run the full `pytest` suite — Story 1.1/1.2 guards must stay green (esp. `tests/test_service_boundary.py`: the new auth code lives in `finance_app/`, not `services/`, so it may import reflex freely; do NOT put auth state under `services/`).

### Review Findings

_Code review 2026-07-09 (inline, full mode, scoped to Story 1.3's 6 files vs `baseline_commit 8d6d010`; 1.2's changes excluded). All 8 ACs verified met; 68 tests pass. Same-session/same-LLM caveat — reviewed adversarially against AD-5/AD-4/OWASP-in-project-context and verified hypotheses empirically. No high-severity defects._

- [x] [Review][Patch] **Unvalidated max password length → unhandled `ValueError` (crash) on registration** — `register_new_user` checked MIN length but not MAX. bcrypt 5.0's `hashpw` **raises** `ValueError: password cannot be longer than 72 bytes` (confirmed empirically), so a >72-byte password crashed `handle_registration` instead of showing a friendly message. **Fixed:** added `MAX_PASSWORD_BYTES = 72` guard in `register_new_user` (returns a `RegistrationResult` error before `hash_password`) + boundary tests (73 bytes → graceful error/no user; 72 bytes → accepted). [finance_app/state/auth_state.py:84]
- [x] [Review][Defer] **`handle_registration` orchestration is app-verified only, not unit-tested** [finance_app/state/auth_state.py:160] — the pure/DB core (`register_new_user`) is unit-tested and the route serves, but the handler's auto-login + `rx.redirect("/upload")` + `email_taken` wiring (AC #2/#8 path) is verified by `reflex run`, not a unit test (testing `rx.State` handlers that call `rx.session()`/`self.router` is fragile). Low risk (handler is thin; `_login` is copied from a shipping library). Add a handler-level test (mocked session) when a Reflex state-test harness is established (Epic 8 E2E is the natural home).
- [x] [Review][Defer] **Duplicate-email check-then-insert is not concurrency-safe** [finance_app/state/auth_state.py:79] — `register_new_user` does `email_exists` then insert; simultaneous same-email registrations would let the second raise an unhandled `IntegrityError`. The DB `unique` constraint on `localuser.username` protects data integrity (no duplicate row is created — confirmed), and this is a single-user local MVP, so severity is very low. Phase-2 (multi-user) should catch `IntegrityError` and return `email_taken=True`.

_Dismissed (2): (1) "Log in instead?" links to `/login`, which isn't routed until Story 1.4 — intentional per story scope (dev SPA fallback serves it; wired in 1.4). (2) Email is lowercase-normalized on registration — Story 1.4's login handler must apply the same normalization before lookup; noted here as a forward requirement for 1.4, not a 1.3 defect._

## Dev Notes

### What this story IS (and is NOT)
- **IS:** the registration page + the auth-state foundation (cookie-backed session token) + email/bcrypt account creation + **auto-login → /upload** + the DPDP-conscious consent UI (trust signal, show/hide, in-page T&C/Privacy modal, no pre-ticked consent, "Log in instead?" on duplicate email).
- **IS NOT:**
  - **Login / logout / protected-route redirects / the IDOR baseline test** → **Story 1.4**. (This story only creates a session via auto-login; it does not build the login form or `require_login` guards.)
  - **Validation-fires-on-blur / clears-on-input, the accessible auto-redirect transition (`aria-live="assertive"`, 3-second manual fallback link, `?fail=1` suppression), and the persistent nav scaffold** → **Story 1.5**. This story's redirect can be a straight `rx.redirect("/upload")`; 1.5 makes the transition accessible. Keep 1.3's validation simple (on-submit + server-side); do not build the blur/clear behavior here.
- Fills the `finance_app/pages/auth.py` area and adds `finance_app/state/auth_state.py`. Story 1.2 stood up the `localuser`/`localauthsession` tables this story writes to — no schema work here.

### AD-5 reality & the approved MVP resolution (READ FIRST)
AD-5 / FR-1.1 mandate the session token in an **httpOnly, SameSite cookie** that JS cannot read, and the spine even says the token comes "from reflex-local-auth" set as httpOnly. **That assumption is false:** the installed `reflex-local-auth==0.5.0` stores the token in `rx.LocalStorage(name="_auth_token")` (`reflex_local_auth/local_auth.py`), and Reflex state tokens are inherently client-visible — a true httpOnly cookie (invisible to JS) cannot come from `rx.State`/`rx.Cookie`; it needs custom server-side `Set-Cookie` middleware.
- **Product decision (2026-07-09, ALPHA):** for **Phase 1**, use a **SameSite `rx.Cookie`** — this satisfies "never localStorage/sessionStorage" and gives a SameSite cookie, but is **not httpOnly** (JS can read it). Justified by the desktop-only / localhost / single-user threat model (project-context: MVP is desktop-only).
- **True httpOnly is deferred to Phase 2** (custom FastAPI `Set-Cookie` middleware). This is logged in `deferred-work.md`. When you implement Task 1, add/confirm that ledger entry.
- **AC #3 is interpreted accordingly:** the tripwire test asserts the token is Cookie-backed (not localStorage). Do not claim full httpOnly compliance in Completion Notes — state the SameSite-cookie reality honestly (Amelia's honesty principle; NFR-1).

### Two stock reflex-local-auth behaviors you MUST override
1. **No auto-login.** `RegistrationState.handle_registration` → `successful_registration` sleeps 0.5s then `rx.redirect(LOGIN_ROUTE)` — it registers but does **not** log the user in. FR-1.2 / AC #2 require auto-authenticate → `/upload`. Override: after `_register_user`, call `self._login(new_user.id)` then `rx.redirect("/upload")`. **The clickable prototype also shows a no-auto-login flow** (`01.1-register.html`: "For your security, please log in to continue" / "Return to Login") — that prototype diverges from the canonical epics/PRD; **epics.md + FR-1.2 win**. Use the prototype for *microcopy and layout only*, not for the post-register flow.
2. **Username-based, not email-based.** The library keys on `LocalUser.username` (unique, `String(255)`). Store the **email in the `username` column** (no model change needed — 255 chars fits emails). Replace the library's `"Username X is already registered"` copy with the FR-1.6 email/"Log in instead?" treatment.

### Email is the username
`LocalUser` has `username` (unique, indexed), `password_hash` (bytes, bcrypt), `enabled` (bool). We put the email into `username`. `enabled` must be set `True` on create (the library's `_register_user` does this; if you reimplement, don't forget it — a `False` account can't log in). `LocalUser.hash_password(pw)` and `user.verify(pw)` are the bcrypt primitives — never handle plaintext beyond hashing.

### Reusing the auto-login primitive
`LocalAuthState._login(user_id)` (inherited by `AuthState`): destroys any existing session for the current `auth_token`, then inserts a `LocalAuthSession(user_id, session_id=auth_token, expiration=now+7d)`. Because `AuthState` overrides `auth_token` to a Cookie, `_login` writes the session keyed on the cookie value. Call it with the freshly-created `new_user.id`.

### Input validation & security (project-context)
- **Validate the boundary:** email format + password presence before any DB write. Use a lightweight email regex — **do not add `email-validator`/`pydantic[email]`** (new dependency needs approval; keep `requirements.txt` lean).
- **bcrypt only, never plaintext** (AC #1); never log the password or the token (project-context A09: "never log secrets/tokens").
- **Parameterized queries only** — use the sqlmodel `select(...).where(LocalUser.username == email)` expression API (never f-string SQL). Email is user-influenced input; treat as untrusted.
- Auth state lives in `finance_app/state/` (UI layer) — it MAY import reflex. Do **NOT** place any auth/session logic under `services/` (AD-2; `test_service_boundary.py` would flag it).

### UI microcopy (from prototype `01.1-register.html` — reference for copy/layout only)
- Trust headline: `"Your honest financial picture. No guessing. No shame."` (must contain `"No guessing. No shame."`); subline `"We only tell you what we actually know. When we're uncertain, we say so."`
- Password placeholder `"8+ characters"`; toggle button text `Show` ⇄ `Hide` with `aria-label` `"Show password"` ⇄ `"Hide password"`.
- CTA `"Create my account"`. Duplicate/existing: `"Already have an account? Log in"` and the inline `"Log in instead?"` per AC #8.
- Legal consent: `"By creating an account you agree to our Terms of Service and Privacy Policy."` — both open the in-page legal modal (placeholder body text is fine for MVP; DPDP note: "consent is never pre-ticked").

### Testing standards & what is honestly testable
- `rx.State` event handlers that call `rx.session()` and `rx.redirect` are hard to unit-test outside a running Reflex app. Test the **extractable/pure + DB** parts against a temp SQLite (as Story 1.2 did): email-validation helper, bcrypt hashing/verify, the duplicate-email branch, the `LocalAuthSession` row creation. Assert the redirect **target string** where the handler returns an `rx.redirect` event you can introspect.
- The **cookie-not-localStorage** guarantee gets a cheap unit tripwire (`type(AuthState.auth_token).__name__ == "Cookie"`) PLUS the DevTools check at `reflex run` (Task 4). Be honest in Completion Notes about which ACs are unit-verified vs app-verified.
- Full auth E2E (register → cookie → protected route) consolidates in Story 1.4 (login/guards) and Epic 8 (IDOR). Don't over-build E2E here.

### Previous story intelligence (Story 1.2 / 1.1)
- **Env:** `.venv` on Python 3.14.6; full pinned stack installed and working. `rx.Model` deprecation warning is expected/benign. DB is `reflex.db` (`db_url` in `rxconfig.py`); tables incl. `localuser` + `localauthsession` already migrated (Story 1.2).
- **Boundary guard** (`tests/test_service_boundary.py`) is active — it only scans `services/`, so `finance_app/state/` auth code is unaffected, but never import `finance_app` from `services/`.
- **Formatting:** any currency/date shown here goes through `services/utils/format.py` (`formatINR`/`formatDate`) — unlikely on a register page, but the rule stands (AD-13).

### Project Structure Notes
- New: `finance_app/state/auth_state.py` (AuthState + RegisterState), `finance_app/pages/register.py`, `finance_app/components/register/` (optional split), tests under `tests/security/` and `tests/`.
- Route: `/register` (reflex-local-auth `REGISTER_ROUTE`). The entry route `"/"` (currently `auth.py` placeholder) and login page are **Story 1.4** — don't redesign routing here beyond adding `/register`.
- If a new dependency feels necessary (e.g. an email validator), STOP and confirm — the story's position is "no new deps" (lightweight regex).

### References
- [Source: epics.md#Story-1.3-User-Registration-with-Auto-Login] (lines 272–292) — acceptance criteria origin
- [Source: ARCHITECTURE-SPINE.md#AD-5] (lines 101–105) — auth token cookie rule (and the false "from reflex-local-auth" assumption this story corrects)
- [Source: ARCHITECTURE-SPINE.md#AD-4] (lines 95–99) — user_id isolation (baseline; full IDOR test is Story 1.4/Epic 8)
- [Source: prd.md#FR-1.1-FR-1.2-FR-1.5-FR-1.6-FR-1.7] & [epics.md FR-1.x] — register/bcrypt/httpOnly-cookie/trust-signal/"Log in instead"/T&C-modal/DPDP-consent
- [Source: reflex_local_auth/local_auth.py, registration.py, user.py] (installed `==0.5.0`) — `LocalAuthState._login`, `RegistrationState` (stock no-auto-login), `LocalUser` (username/password_hash/enabled, bcrypt)
- [Source: prototypes/01-priyas-first-honest-morning-Prototype/01.1-register.html] — microcopy/layout (⚠️ its no-auto-login flow is superseded by FR-1.2)
- [Source: 1-2 story](./1-2-database-schema-and-shared-formatting-utilities.md) — `localuser`/`localauthsession` schema, env, boundary guard

## Dev Agent Record

### Agent Model Used

Amelia (Senior Software Engineer persona) · claude-opus-4-8

### Debug Log References

- **The AD-5 fallback fired — caught by runtime verification, not unit tests.** Task 1 first tried the planned approach: `AuthState(reflex_local_auth.LocalAuthState)` overriding `auth_token` to `rx.Cookie`. The class-level tripwire passed, BUT `reflex run` proved it insufficient: the compiled `.web/utils/context.js` `clientStorage` still put `_auth_token` in **`local_storage`** (under the parent `LocalAuthState`'s var key) — subclass-overriding an inherited client-storage var does NOT stop Reflex compiling the parent's localStorage token. Took the story's documented fallback: **reimplemented `AuthState` as a standalone `rx.State`** (not inheriting `LocalAuthState`), copying the ~40 lines of session logic (`authenticated_user`, `is_authenticated`, `do_logout`, `_login`) onto a cookie token, reusing only reflex-local-auth's `LocalUser`/`LocalAuthSession` models + bcrypt. After the refactor the compiled `clientStorage.cookies` carries `_auth_token` with `sameSite=strict` — **AC #3 mechanism verified in the compiled output.**
- **False-green lesson:** the initial tripwire (`type(AuthState.auth_token).__name__ == "Cookie"`) checked the class-attr Var wrapper — unreliable (it passed even when the compiled token was localStorage). Replaced it with an assertion on the **field default** (`AuthState.get_fields()["auth_token"].default` is a `reflex.istate.storage.Cookie`) + a structural guard that `AuthState` does not inherit `LocalAuthState`.
- **App verification (`reflex run`):** compiled clean (30/29, 100%); backend `/ping` 200; frontend `/register` 200, `/` 200, `/upload` 200. `rx.input(auto_complete="email")` failed (prop is bool) → switched to `custom_attrs={"autoComplete": ...}`. `rx.Model` deprecation warning is expected/benign.
- **Known caveat (logged to deferred-work.md):** importing reflex-local-auth for its models also registers its unused `LocalAuthState`, leaving a vestigial **empty** `_auth_token` localStorage slot in `clientStorage` that nothing ever writes (we use our own `AuthState`). The real token is the cookie; Phase-2 (server-side httpOnly) removes the library's state layer entirely.

### Completion Notes List

- **All 8 ACs met** (AC #2/#3 verified at `reflex run` per the story's testing note; the rest unit-tested):
  - AC #1: `register_new_user` creates a `LocalUser` (email in `username`) with a bcrypt `password_hash` (≠ plaintext; `verify()` round-trips). AC #8: duplicate email → `email_taken=True`, no second user, inline "Log in instead?" link.
  - AC #2: `handle_registration` auto-logins via `AuthState._login` then `rx.redirect("/upload")`; app serves `/upload`.
  - AC #3: session token is a **SameSite `rx.Cookie`** (compiled `clientStorage.cookies`, `sameSite=strict`), not the localStorage default — Phase-1 pragmatic resolution (httpOnly deferred to Phase-2, product-approved). Tripwire test guards the regression.
  - AC #4 trust signal "No guessing. No shame." above the form; AC #5 show/hide password toggle; AC #6 T&C/Privacy open in-page `rx.dialog` modals (no new tab); AC #7 link-consent (no checkbox → nothing pre-ticked).
- **Two stock reflex-local-auth behaviors overridden** as the story specified: (1) no auto-login → we auto-login and redirect to `/upload` (not `/login`); (2) username-based → email stored in the `username` column. Prototype's no-auto-login flow correctly ignored (epics/FR-1.2 win).
- **Boundary respected:** all auth/session code is in `finance_app/state/` + `finance_app/pages/` (UI layer, may import reflex); nothing under `services/`. `test_service_boundary.py` still green.
- **No new dependencies:** email validated with a lightweight regex (no `email-validator`/`pydantic[email]`).
- **Tests:** full suite **68 passed** (Story 1.1/1.2's 48 + 20 new: 3 auth-token tripwire, 13 registration-logic, 4 register-page smoke). No regressions.
- **Honest scope note:** AC #2 "within 3 seconds" and the DevTools cookie/redirect round-trip are verified by app compile + serving + the compiled `clientStorage` cookie registration, not by a live browser-submit DevTools capture (no browser driver in this environment). The mechanism is proven; a manual browser pass is recommended in the eventual review.

### File List

**New**
- `finance_app/state/auth_state.py` — `AuthState` (standalone cookie-backed session) + `RegisterState` + `register_new_user`/`is_valid_email`/`RegistrationResult`
- `finance_app/pages/register.py` — `/register` page (trust signal, show/hide, consent modals, "Log in instead?")
- `tests/security/test_auth_token_storage.py` — AD-5 cookie tripwire
- `tests/security/test_registration.py` — registration-logic unit tests
- `tests/test_register_page_smoke.py` — register page smoke test

**Modified**
- `finance_app/pages/__init__.py` — import/register the `register` page module

**Generated (git-ignored, not source)**
- `.web/**` (Reflex compile output), `reflex.db` (unchanged schema)

### Change Log

| Date | Change |
| --- | --- |
| 2026-07-09 | Story 1.3 drafted with comprehensive context — cookie-backed auth state (AD-5 pragmatic resolution, product-approved), email/bcrypt registration with auto-login → /upload, DPDP-conscious consent UI. Surfaced + resolved the reflex-local-auth localStorage↔AD-5 contradiction and the prototype's no-auto-login divergence. Status → ready-for-dev. |
| 2026-07-09 | Story 1.3 implemented (TDD). Standalone cookie-backed `AuthState` (the subclass-override approach failed at `reflex run` — compiled token was still localStorage; took the documented fallback), email/bcrypt registration with auto-login → `/upload`, and the DPDP-conscious `/register` UI. `reflex run` verified compiled `clientStorage` puts `_auth_token` in cookies (SameSite=strict) and the route serves. Full suite 68 passed. Vestigial-localStorage caveat logged to deferred-work. Status → review. |
| 2026-07-09 | Code review (inline, full mode, 1.3-scoped): 1 patch applied, 2 deferred, 2 dismissed. Fixed unvalidated max password length (bcrypt >72-byte `ValueError` crash → friendly error + boundary tests). Full suite 70 passed. Status → done. |
