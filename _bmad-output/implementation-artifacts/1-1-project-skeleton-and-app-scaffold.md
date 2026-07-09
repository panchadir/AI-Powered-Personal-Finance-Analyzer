---
baseline_commit: 17193db0707565d3535868d20a6135cf9c7b4936
---

# Story 1.1: Project Skeleton & App Scaffold

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a running Reflex app with the correct project structure, pinned dependencies, and validated assumptions,
so that every subsequent story has a consistent foundation and no surprises on Day 1.

## Acceptance Criteria

Source: [epics.md — Story 1.1](../planning-artifacts/epics.md) (lines 237–252)

1. **Given** a fresh clone of the repo, **When** `reflex run` is executed, **Then** the app serves a blank multi-page app locally with no errors.
2. **And** the directory structure matches the architecture spine: `finance_app/pages/`, `finance_app/components/`, `finance_app/state/`, `finance_app/models.py`, `services/{ingestion,categorize,engine,narrate,utils}/`, `tests/`, `data/`, `.env.example`, `requirements.txt`.
3. **And** Reflex and reflex-local-auth versions are **pinned** in `requirements.txt` (exact `==` pins, not ranges).
4. **And** `statementsparser` is validated to cover the HDFC demo bank format (Day 1, Hour 1 — flagged assumption; if it fails, document the gap immediately — do not silently proceed).
5. **And** `.env` is git-ignored; `.env.example` contains `ANTHROPIC_API_KEY=` as a placeholder.
6. **And** no file under `services/` imports `reflex` or any `rx.*` namespace — verified by `grep -r "import reflex" services/` **and** `grep -rn "rx\." services/` both returning empty.

## Tasks / Subtasks

- [x] **Task 1 — Scaffold the Reflex app** (AC: #1, #2)
  - [x] Run `reflex init` at project root to generate the app; name the app module `finance_app` so the app root is `finance_app/`.
  - [x] Confirm `rxconfig.py` is generated at the project root and `app_name = "finance_app"`.
  - [x] Create the multi-page skeleton under `finance_app/pages/` — one file per route with a minimal blank page and `@rx.page(route=...)`: `auth.py`, `upload.py`, `transactions.py`, `dashboard.py`, `insights.py`, `copilot.py`. Each returns a placeholder (shared `coming_soon()` component) so `reflex run` serves without errors.
  - [x] Register all pages in `finance_app/finance_app.py` (the app entrypoint) — done via `@rx.page` decorators auto-registered by importing `finance_app.pages`.
- [x] **Task 2 — Create the directory tree exactly per the spine** (AC: #2)
  - [x] Create `finance_app/components/`, `finance_app/state/` (each with `__init__.py`).
  - [x] Create empty `finance_app/models.py` (table definitions land in Story 1.2 — module docstring placeholder, no `rx.Model` yet).
  - [x] Create `services/` with sub-packages `ingestion/`, `categorize/`, `engine/`, `narrate/`, `utils/` — each with an `__init__.py`.
  - [x] Add placeholder `services/categorize/schema.py`, `services/narrate/config.py`, `services/utils/format.py` as documented empty modules (no `formatINR`/`formatDate` implemented here).
  - [x] Create `tests/` with sub-dirs `tests/engine/`, `tests/ingestion/`, `tests/utils/`, `tests/security/` (each with `__init__.py`) and a `data/` directory.
- [x] **Task 3 — Dependencies & secrets hygiene** (AC: #3, #5)
  - [x] Create `requirements.txt` with **exact `==` pins** for every stack item — versions recorded from actual `pip show` output, not guessed.
  - [x] Create `.env.example` containing exactly `ANTHROPIC_API_KEY=` (placeholder, no value).
  - [x] Add `.env` to `.gitignore`. Verified: `git check-ignore .env` returns `.env`; `.env` is untracked; `.env.example` is not ignored. No secret committed.
- [x] **Task 4 — Validate the flagged statementsparser assumption** (AC: #4)
  - [x] Validated: `statementsparser==0.1.0` (import name `statementparser`) registers a dedicated HDFC parser (`['AXIS','HDFC','ICICI','SBI']`) with a `Decimal`-based `Transaction` model. Locked in as `tests/ingestion/test_statementsparser_smoke.py`.
  - [x] Documented result + caveats (import-name gotcha, schema-adaptation need, live-parse owed to Story 2.3) in `docs/day1-assumption-validations.md`.
- [x] **Task 5 — Enforce the framework-agnostic boundary (AD-2/AD-14)** (AC: #6)
  - [x] Confirmed no `services/**` file imports `reflex` or uses `rx.*`.
  - [x] Both greps return empty (exit 1). Added permanent AST-based guard `tests/test_service_boundary.py`.
- [x] **Task 6 — Verify the whole thing runs** (AC: #1)
  - [x] `reflex run` starts cleanly; app serves at `localhost:3000`, backend `:8000` (`/ping` 200); all six routes return 200; no errors in the run log.
  - [x] `pytest` runs green: 5 passed (2 boundary + 3 statementsparser), zero errors — test harness works from Day 1.

### Review Findings

_Code review 2026-07-09 (inline, full mode against this spec). All 6 ACs verified met; findings below are cleanups, none block the ACs._

- [x] [Review][Patch] Empty `data/` directory is not version-controlled — will vanish on a fresh clone, defeating AC #2's structure guarantee under AC #1's "fresh clone of the repo" framing. **Fixed:** added `data/.gitkeep`. [data/]
- [x] [Review][Patch] Unused `import pytest` — violates project-context "no unused imports" checklist (ruff F401). **Fixed:** removed. [tests/ingestion/test_statementsparser_smoke.py:19]
- [x] [Review][Patch] Missing trailing newline at end of file. **Fixed.** [rxconfig.py:12]
- [x] [Review][Patch] Malformed package docstring `""". tests."""` (leftover `.` dirname from scripted generation). **Fixed:** now `"""Test suite root."""`. [tests/__init__.py:1]
- [x] [Review][Defer→Resolved] AD-2 boundary guard detects only `import reflex`; it did not catch a `services/` module importing the UI layer (`from finance_app import …`), which also violates the one-way UI→Service→Data dependency direction. **Resolved 2026-07-09** (at user request, same session): guard generalized to AST-check top-level import roots and now also flags `finance_app` imports via `test_no_ui_layer_import_in_services`. Detection verified against synthetic offenders; relative imports correctly ignored; suite now 6 passed. [tests/test_service_boundary.py]

## Dev Notes

### What this story is (and is NOT)
- **IS:** the empty, runnable skeleton + dependency pinning + directory contract + the two flagged Day-1 validations (statementsparser, service boundary). This is greenfield — **no application code exists yet** (`finance_app/`, `services/`, `requirements.txt`, `rxconfig.py` are all absent at story start — confirmed).
- **IS NOT:** DB tables, auth, formatting utilities, or any business logic. Those are Story 1.2+ . Do **not** implement `formatINR`/`formatDate`, `rx.Model` tables, or auth here — creating them now risks diverging from 1.2's exact ACs. Leave the named files as documented placeholders only.

### Authoritative sources (read before coding)
- **Source tree contract:** [ARCHITECTURE-SPINE.md — Structural Seed / Source tree](../planning-artifacts/architecture/architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md) (lines 215–241). Match it exactly.
- **project-context.md** (loaded as persistent facts) — the enforcement summary of AD-1→AD-14. The rules most relevant to THIS story:
  - **AD-2 / AD-14:** Nothing under `services/` may import `reflex` or `rx.*`; `services/` must be independently importable (`pytest services/` runs without a Reflex app). This is AC #6 and the reason for the boundary guard test.
  - **Code Quality:** `snake_case` for all Python files/dirs. Each `services/` sub-module exposes a clean public API in `__init__.py`; internal helpers prefixed `_`.
  - **Workflow:** Secrets in `.env` via python-dotenv; `.env` git-ignored; **pin Reflex + reflex-local-auth Day 1**; **validate statementsparser covers HDFC Day 1 Hour 1**.

### Stack — pin these in requirements.txt (AC #3)
From [ARCHITECTURE-SPINE.md — Stack](../planning-artifacts/architecture/architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md) (lines 193–210). Pin the **actual installed** version with `==`:

| Package | Version guidance |
| --- | --- |
| Python | 3.11+ (runtime requirement, not a pip pin) |
| reflex | latest stable — **pin exact** |
| reflex-local-auth | latest stable — **pin exact** (session/auth, used in Story 1.3/1.4) |
| pdfplumber | latest stable |
| camelot-py | latest stable |
| statementsparser | latest stable — **and validate HDFC (AC #4)** |
| pandas | latest stable |
| anthropic | latest stable (Claude Python SDK) |
| python-dotenv | latest stable |
| pytest | latest stable |

`sqlmodel`, SQLite, and `rx.plotly` are bundled with Reflex / stdlib — no separate pin required (note this in a comment). Only list dependencies actually used (project-context: keep requirements.txt lean).

### `reflex init` gotcha
Vanilla `reflex init` generates `{app_name}/{app_name}.py` + a demo page and `rxconfig.py`. You must **reshape** that default into the spine's `finance_app/pages|components|state/` layout and strip the demo boilerplate. The entrypoint module stays `finance_app/finance_app.py`; move page definitions into `pages/` and import+register them there. Keep `rxconfig.py` at project root.

### Reflex go/no-go note (context, not this story's task)
project-context flags a **Day 2 noon Reflex go/no-go checkpoint** — if `rx.State` reactivity is blocking, the pre-agreed fallback is the Streamlit escape hatch (spine "Deferred" line 313). The whole point of the `services/` boundary you enforce in AC #6 is to make that swap cheap. Getting AC #6 right is load-bearing for the entire project's risk posture, not busywork.

### Testing standards
- `pytest services/engine/` is the non-negotiable MVP quality gate (arrives in Epic 4) — but the **harness must work from Day 1**. Task 6 establishes that `pytest` runs green now.
- Recommended first test: `tests/test_service_boundary.py` asserting no `services/**` file imports reflex — turns AC #6 into a permanent regression guard rather than a one-time grep.

### Project Structure Notes
- Full alignment with the spine source tree (lines 215–241). No variances expected — this story *creates* the structure the rest of the project depends on, so any deviation here ripples everywhere.
- A `prototypes/` directory already exists (HTML/CSS/JS clickable prototype). It is **reference only** — do not import from or wire it into the Reflex app. Note for Story 1.2: `prototypes/.../shared/format.js` is the JS twin of the future `formatINR`/`formatDate`; keep output identical when those are built (AD-13), but that is 1.2 work, not 1.1.
- `docs/` and `_bmad*/` already exist; leave them untouched.

### References
- [Source: epics.md#Story-1.1-Project-Skeleton--App-Scaffold] (lines 237–252) — acceptance criteria origin
- [Source: ARCHITECTURE-SPINE.md#Structural-Seed] (lines 215–241) — source tree contract
- [Source: ARCHITECTURE-SPINE.md#Stack] (lines 193–210) — dependency versions
- [Source: ARCHITECTURE-SPINE.md#AD-2] (lines 83–87) & [#AD-14] (lines 163–167) — services/ framework-agnostic boundary (AC #6)
- [Source: project-context.md#Development-Workflow-Rules] — pin deps Day 1, validate statementsparser, .env hygiene

## Dev Agent Record

### Agent Model Used

Amelia (Senior Software Engineer persona) · claude-opus-4-8

### Debug Log References

- `reflex run` (attempt 1) failed: bun frontend-dependency install hit a Windows filesystem error — `EPERM: Operation not permitted (NtSetInformationFile()) ... moving "autoprefixer" to cache dir`. This is a bun-on-Windows cache-permission issue, **not** a scaffold defect. Retry with a warm bun cache succeeded.
- Radix Themes implicit-enablement `DeprecationWarning` (0.9.0, removed in 1.0) resolved by adding `rx.plugins.RadixThemesPlugin()` to `rxconfig.py`. Second run compiled clean (28/27, 100%) with no warning.
- Verification (server up): frontend `http://localhost:3000/` 200 on all six routes (`/`, `/upload`, `/transactions`, `/dashboard`, `/insights`, `/copilot`); backend `http://localhost:8000/ping` 200. (Note: unregistered path `/nope` also returns 200 — expected Reflex dev-SPA fallback, not a routing defect; the six routes are compiled/registered.)
- `pytest -q` → `5 passed`.

### Completion Notes List

- Full skeleton scaffolded and **verified running**; all 6 ACs satisfied. Environment: Python 3.12.6, isolated `.venv`.
- Toolchain installed and pinned to actual versions: reflex 0.9.6.post1, reflex-local-auth 0.5.0, pdfplumber 0.11.10, camelot-py 2.0.0, statementsparser 0.1.0, pandas 3.0.3, anthropic 0.116.0, python-dotenv 1.2.2, pytest 9.1.1.
- **AC #4 (flagged assumption) — PASS with caveats** for Epic 2, recorded in `docs/day1-assumption-validations.md`: (1) PyPI `statementsparser` imports as `statementparser` (no trailing "s"); (2) its `Transaction` shape ≠ our canonical schema, so Story 2.1's adapter must normalize (AD-6); (3) a live parse of the actual Priya demo HDFC PDF is owed in Story 2.3 (no demo fixture exists yet).
- **AC #6** enforced by a permanent AST-based guard (`tests/test_service_boundary.py`), not just a one-time grep — every later epic re-verifies the `services/` boundary automatically.
- Scope discipline held: no DB tables, formatters, or auth implemented (those are Story 1.2+). Named modules (`models.py`, `utils/format.py`, `categorize/schema.py`, `narrate/config.py`) are documented placeholders only.
- **Note for reviewer/committer:** `.venv/`, `.web/`, `.pytest_cache/`, `reflex.lock` are git-ignored. `reflex init` also generated root `AGENTS.md` and `CLAUDE.md` (Reflex agent-guidance templates) — untracked; leave or remove at team discretion.

### File List

**New — app scaffold**
- `rxconfig.py` (generated by `reflex init`; edited to add `RadixThemesPlugin`)
- `finance_app/__init__.py` (generated)
- `finance_app/finance_app.py` (reshaped from demo → imports pages, constructs `rx.App()`)
- `finance_app/models.py` (placeholder)
- `finance_app/components/__init__.py`
- `finance_app/components/placeholder.py` (`coming_soon()` shared component)
- `finance_app/state/__init__.py`
- `finance_app/pages/__init__.py` (imports all page modules → registers routes)
- `finance_app/pages/auth.py`, `upload.py`, `transactions.py`, `dashboard.py`, `insights.py`, `copilot.py`

**New — services (framework-agnostic packages)**
- `services/__init__.py`
- `services/ingestion/__init__.py`
- `services/categorize/__init__.py`, `services/categorize/schema.py` (placeholder)
- `services/engine/__init__.py`
- `services/narrate/__init__.py`, `services/narrate/config.py` (placeholder)
- `services/utils/__init__.py`, `services/utils/format.py` (placeholder)

**New — tests**
- `tests/__init__.py`, `tests/engine/__init__.py`, `tests/ingestion/__init__.py`, `tests/utils/__init__.py`, `tests/security/__init__.py`
- `tests/test_service_boundary.py` (AC #6 guard)
- `tests/ingestion/test_statementsparser_smoke.py` (AC #4 guard)

**New — config / docs / data**
- `requirements.txt` (pinned; replaced reflex's one-liner)
- `.env.example` (`ANTHROPIC_API_KEY=`)
- `docs/day1-assumption-validations.md`
- `data/` (empty directory for demo fixtures)

**Modified**
- `.gitignore` (added `.env`, `.venv/`, `.pytest_cache/`, `reflex.lock`)

## Change Log

| Date | Change |
| --- | --- |
| 2026-07-09 | Story 1.1 implemented: Reflex app scaffolded to the architecture-spine source tree; 6 blank routes serving; deps pinned; `.env` hygiene; statementsparser→HDFC assumption validated (PASS + caveats); services/ boundary guarded by AST test. All 6 ACs met, `pytest` 5 passed, `reflex run` serves cleanly. Status → review. |
| 2026-07-09 | Code review (inline, full mode): 4 patch findings applied (`data/.gitkeep`, removed unused `import pytest`, `rxconfig.py` trailing newline, `tests/__init__.py` docstring), 1 enhancement deferred (boundary guard scope → `deferred-work.md`). Tests still 5 passed. Status → done. |
| 2026-07-09 | Deferred enhancement resolved (user request): `tests/test_service_boundary.py` generalized to also enforce AD-2 dependency direction — new `test_no_ui_layer_import_in_services` flags any `services/`→`finance_app` import. Suite now 6 passed. |
