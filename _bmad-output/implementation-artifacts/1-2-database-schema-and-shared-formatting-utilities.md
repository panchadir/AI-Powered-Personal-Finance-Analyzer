---
baseline_commit: 8d6d010a49265ae0debdf9e998f9de752c925a64
---

# Story 1.2: Database Schema & Shared Formatting Utilities

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want all database tables created and shared currency/date formatting utilities in place,
so that every subsequent story can persist data and display numbers consistently without reinventing formatting.

## Acceptance Criteria

Source: [epics.md — Story 1.2](../planning-artifacts/epics.md) (lines 254–271)

1. **Given** the Reflex app is running, **When** `reflex db init && reflex db makemigrations && reflex db migrate` are run, **Then** an SQLite DB file is created with all 8 tables: `users`, `uploaded_files`, `transactions`, `merchant_rules`, `commitments`, `score_events`, `insights`, `chat_messages`.
2. **And** each user-scoped table has an integer primary key and a `user_id` foreign key.
3. **And** `direction` enum is `credit`|`debit`; `category_source` is `rule`|`llm`|`user`; `criticality` is `critical`|`important`|`flexible` with default `important`.
4. **And** `services/utils/format.py` exports `formatINR(amount: float) -> str` using Indian number grouping (e.g. `₹1,25,000` for `125000.0`).
5. **And** `services/utils/format.py` exports `formatDate(iso: str) -> str` returning `"30 Jun 2026"` for `"2026-06-30"`.
6. **And** `pytest tests/utils/` passes with edge cases: zero (`₹0`), crore amounts (`₹1,00,00,000`), leap-year dates, and invalid input raises `ValueError`.
7. **And** all arithmetic in `services/` uses `Decimal`, never `float` (format functions accept `float` for display only).

## Tasks / Subtasks

- [x] **Task 1 — Shared enums in a framework-agnostic module** (AC: #3)
  - [x] RED: write `tests/utils/test_enums.py` asserting: `Direction` has exactly `{"credit","debit"}`; `CategorySource` has exactly `{"rule","llm","user"}`; `Criticality` has exactly `{"critical","important","flexible"}`; each is a `str` enum so `Direction.credit == "credit"`; and a helper/const exposes the `criticality` **default** value `"important"`.
  - [x] GREEN: create `services/utils/enums.py` defining `Direction`, `CategorySource`, `Criticality` as `class X(str, Enum)` with lowercase values exactly as above. Add `CRITICALITY_DEFAULT = Criticality.important`.
  - [x] **Boundary rule (AD-2 — load-bearing):** these enums MUST live under `services/` (framework-agnostic) because `services/engine/` and `services/ingestion/` import them. Do **NOT** define them in `finance_app/models.py` and import them into `services/` — that reverses the dependency direction and will trip `tests/test_service_boundary.py::test_no_ui_layer_import_in_services`. `finance_app/models.py` imports FROM `services/utils/enums.py` (UI→Service is allowed); never the reverse.
- [x] **Task 2 — `formatINR` with Indian digit grouping** (AC: #4, #6)
  - [x] RED: write `tests/utils/test_format.py` cases for `formatINR`: `0 → "₹0"`, `125000 → "₹1,25,000"`, `2840 → "₹2,840"`, `10000000 → "₹1,00,00,000"` (crore), `-640 → "-₹640"` (sign before `₹`), and `formatINR("abc")` / `formatINR(None)` → raises `ValueError`.
  - [x] GREEN: implement `formatINR(amount: float) -> str` in `services/utils/format.py`. Round to whole rupees (no paise; `maximumFractionDigits: 0` parity with the JS twin). Implement Indian grouping manually (last 3 digits, then groups of 2) — do **not** rely on a locale being installed.
- [x] **Task 3 — `formatDate` ISO → "30 Jun 2026"** (AC: #5, #6)
  - [x] RED: add `formatDate` cases to `tests/utils/test_format.py`: `"2026-06-30" → "30 Jun 2026"`, `"2026-06-05" → "5 Jun 2026"` (day NOT zero-padded), `"2024-02-29" → "29 Feb 2024"` (valid leap year), and invalid input `"2023-02-29"` (non-leap) / `"not-a-date"` / `""` → raises `ValueError`.
  - [x] GREEN: implement `formatDate(iso: str) -> str` using `datetime.strptime(iso, "%Y-%m-%d")` (which raises `ValueError` on invalid dates for free), a hardcoded 3-letter month array, unpadded day, 4-digit year.
- [x] **Task 4 — Define all 8 tables in `finance_app/models.py`** (AC: #1, #2, #3, #7)
  - [x] Wire the `users` table via reflex-local-auth: `import reflex_local_auth` in `models.py` so its `LocalUser` (+ `LocalAuthSession`) models are registered with the metadata and picked up by migrations. Do **NOT** hand-roll a second `users` table (see Dev Notes → "The `users` table decision"). **Verify the actual tablename** the library uses (`reflex_local_auth.LocalUser.__tablename__`) and use it as the FK target; document it in Completion Notes.
  - [x] Define `UploadedFile` (`uploaded_files`): `id` PK, `user_id` FK, `filename`, `uploaded_at`, plus status/count fields as needed by Epic 2 (keep minimal; note later stories may extend).
  - [x] Define `Transaction` (`transactions`) to the **canonical AD-6 schema exactly**: `id, user_id (FK), source_file_id (FK→uploaded_files.id), date, description_raw, merchant_normalized, amount, direction, balance_after, category, category_source, category_confidence, created_at`. `amount` and `balance_after` are money → `Decimal` columns (see Dev Notes → "Money columns"). `direction`/`category_source` stored as `str`, typed via the shared enums.
  - [x] Define `MerchantRule` (`merchant_rules`): `id` PK, `user_id` FK, `pattern`, `category`, `source`, `created_at`. (User-taught rules — Story 3.3.)
  - [x] Define `Commitment` (`commitments`): `id` PK, `user_id` FK, `name`, `amount` (`Decimal`), `due_day` (int 1–31), `criticality` (str, default `"important"`), `created_at`.
  - [x] Define `ScoreEvent` (`score_events`) to the **AD-9 schema exactly**: `id` PK, `user_id` FK, `score`, `delta`, `trigger_event` (⚠️ spelled `trigger_event`, NOT `triggering_event`), `explanation`, `suggested_action`, `timestamp`.
  - [x] Define `Insight` (`insights`): `id` PK, `user_id` FK, `pattern_name`, `observation`, `evidence`, `explanation`, `action_suggestion`, `status` (e.g. `active`|`dismissed`, default `active`), `created_at`. (O-E-E-A shape — Epic 7.)
  - [x] Define `ChatMessage` (`chat_messages`): `id` PK, `user_id` FK, `role`, `content`, `trace_sources`, `timestamp`. (Story 6.1.)
  - [x] RED→GREEN: write `tests/test_models_schema.py` that creates the schema against a **temporary SQLite** (in-memory or tmp file via a plain SQLAlchemy engine + `SQLModel.metadata.create_all`), then asserts: all 8 tables exist; every user-scoped table has an integer `id` PK and a `user_id` column; `commitments.criticality` default resolves to `"important"`. This makes the schema a permanent regression guard, independent of the Reflex CLI.
- [x] **Task 5 — Generate the migration and verify the real DB** (AC: #1)
  - [x] Run `reflex db init` (if not already initialized), then `reflex db makemigrations` and `reflex db migrate`. Confirm the SQLite file is created and contains all 8 app/auth tables (inspect with `sqlite3 <db> ".tables"` or `sqlalchemy.inspect`).
  - [x] Record the migration outcome, the DB filename, and the confirmed table list in Completion Notes / Debug Log.
- [x] **Task 6 — Decimal boundary & float-is-display-only guard** (AC: #7)
  - [x] Confirm `services/` money columns/values use `Decimal` (Task 4) and that `formatINR`/`formatDate` are the ONLY places a `float`/display coercion happens. Add a short assertion or docstring note that `format.py`'s `float` parameter is display-only.
  - [x] Re-run `pytest` (full suite) and confirm the existing Story 1.1 guards still pass — especially `tests/test_service_boundary.py` (no `services/`→`finance_app` import introduced by the enums), and `pytest tests/utils/` green.

### Review Findings

_Code review 2026-07-09 (inline, full mode against this spec, vs `baseline_commit 8d6d010`). All 7 ACs verified met; 45 tests pass. Caveat: review run in the same session/LLM that implemented the story — reviewed adversarially against the ACs and AD-guards to compensate. No high-severity defects._

- [x] [Review][Decision→Patch] **`formatINR` rejects `Decimal` — the engine's money type (AD-8)** — `formatINR(Decimal('125000.50'))` raised `ValueError`. AC #4/#7 literally specify `float`, so it was AC-compliant, but AD-8 makes all engine money `Decimal` and AD-13 makes `formatINR` the *only* display path — a foot-gun for every Epic-5/6 call site. **Resolved (user chose option 1):** `formatINR` now accepts `float | Decimal` (finite check via `Decimal.is_finite()` for Decimals); added `test_accepts_decimal_the_engine_money_type` + non-finite-Decimal test. [services/utils/format.py:41]
- [x] [Review][Patch] **Unused import `Direction` in models.py** — `Direction` was imported but referenced only in a comment. **Fixed:** dropped from the import (`CategorySource`/`Criticality` remain, both used). Surfaced that `tests/test_models_schema.py` was reaching the enums via the models re-export; repointed it to import from `services.utils.enums` (their canonical home). [finance_app/models.py:31]
- [x] [Review][Defer] **tz-aware `_utcnow()` default flows into naive `DateTime` columns** [finance_app/models.py:38] — deferred; no consumer reads these timestamps yet (Epic 4/5). All `created_at`/`timestamp`/`uploaded_at` defaults are tz-aware UTC written into SQLAlchemy naive columns; standardize the tz convention (naive-UTC everywhere, or tz-aware columns) when timestamps are first consumed.

_Dismissed (1): AC #1 literally names a `users` table; the schema uses reflex-local-auth's `localuser`. Intentional and documented (Dev Notes → "The `users` table decision"); every `user_id` FK resolves to it. Not a defect._

## Dev Notes

### What this story IS (and is NOT)
- **IS:** the 8-table data schema (via `rx.Model`/sqlmodel) + a working migration that stands up the SQLite DB + the two shared formatting utilities (`formatINR`, `formatDate`) + the three shared enums. This is the persistence + display foundation every later epic builds on.
- **IS NOT:** auth flows (Story 1.3/1.4), parsers/ingestion (Epic 2), categorization (Epic 3), engine math (Epic 4), or any UI beyond what already exists. Do NOT implement registration, login, the canonical `Transaction` *parser DTO/protocol* (that's Story 2.1 — this story creates the DB **table**), the category enum (AD-7, Story 3.2), or engine arithmetic here.
- Story 1.1 left `finance_app/models.py` as a documented placeholder and `services/utils/format.py` as a placeholder — **this story fills both**. Confirmed at [1-1 story](./1-1-project-skeleton-and-app-scaffold.md) (File List) and current [models.py](../../finance_app/models.py).

### The `users` table decision (READ FIRST — prevents fragmented identity)
The AC lists a `users` table, but **reflex-local-auth owns user identity**. It ships its own `LocalUser` SQLModel table (username + `password_hash` + `enabled`) and a `LocalAuthSession` table. Story 1.3 registers users through this library. **Decision: reflex-local-auth's user model IS the `users` table.** Do NOT create a second, hand-rolled `users` table — that fragments identity, duplicates the password field, and breaks Story 1.3's auto-login wiring.

- In `models.py`, `import reflex_local_auth` so its models register with the shared metadata → migrations create the auth tables alongside ours.
- Every user-scoped table's `user_id` FK targets the reflex-local-auth user table's `id`.
- ⚠️ **Verify the real tablename** from the installed pinned version (Story 1.1 pinned `reflex-local-auth==0.5.0`): check `reflex_local_auth.LocalUser.__tablename__` (it may be `localuser`, not literally `users`). Use whatever it actually is as the FK target, and document the exact name in Completion Notes. The AC's intent — "a users table exists and everything FKs to it" — is satisfied by the library's table; a name of `localuser` is acceptable and expected. If (and only if) the team later mandates a literal `users` tablename, the alternative is a thin `User(rx.Model)` extending/wrapping the library — but that is out of scope here and not recommended.
- The local `.venv` is **not** in this working tree (Story 1.1 was built in a separate env), so confirm the model shape against the actually-installed package before writing FKs — do not guess field names.

### The enum-location trap (AD-2 boundary — the #1 way this story breaks the build)
`direction` and `category_source` are consumed by `services/ingestion/` and `services/engine/`; `criticality` by `services/engine/`. They are ALSO used as `finance_app/models.py` column types. Because **nothing under `services/` may import `finance_app`** (AD-2, enforced by `tests/test_service_boundary.py::test_no_ui_layer_import_in_services`), the enums must live **under `services/`** — recommended home `services/utils/enums.py` (framework-agnostic, next to `format.py`). `models.py` then imports them (UI→Service, allowed). Putting the enums in `models.py` would force a `services/`→`finance_app/` import later and fail the boundary test. This is the concrete, testable reason for Task 1's placement.

- Store enum values as plain `str` columns in SQLite (no native DB enum); use the Python `str`-enum for typing/validation at the Python boundary. `criticality` column default = `Criticality.important` value (`"important"`).
- The AD-7 **category** enum is a *separate* concern (approved category taxonomy) that lives in `services/categorize/schema.py` and is built in Story 3.2 — **not** part of this story.

### Money columns — Decimal, not float (AD-8 guard)
`transactions.amount`, `transactions.balance_after`, and `commitments.amount` are money. Per project-context ("Money math uses `Decimal`, never `float`") define them as `Decimal` columns (sqlmodel supports `Decimal` with `max_digits`/`decimal_places`, e.g. `max_digits=12, decimal_places=2`). Integer-paise is the sanctioned alternative. **SQLite caveat:** SQLite has `NUMERIC` affinity and can round-trip `Decimal` as `float` unless read carefully — the engine (Epic 4) must convert to `Decimal` on read regardless. This story does no money math, so the only requirement here is: **don't declare money columns as `float`.** `formatINR(amount: float)` is the sanctioned display-only float boundary (AC #7).

### `formatINR` / `formatDate` — parity with the JS twin, one deliberate divergence
The prototype [`shared/format.js`](../../prototypes/01-priyas-first-honest-morning-Prototype/shared/format.js) is the reference twin — **keep output identical** (AD-13) for the happy path:
- `formatINR`: `₹` prefix, Indian grouping (`₹1,25,000`, `₹18,00,000`, `₹1,00,00,000`), whole rupees (no decimals), negative sign **before** the `₹` (`-₹640`), zero → `₹0`.
- `formatDate`: `"30 Jun 2026"`; day **not** zero-padded; 3-letter month; 4-digit year.
- **Deliberate divergence (AC #6 overrides the JS):** the JS coerces bad input to `₹0` / echoes the raw string; the Python utilities must **raise `ValueError`** on invalid input. This is required by the AC and is the correct Python contract. Do not silently coerce.
- Do not depend on `locale`/`toLocaleString` equivalents or `babel` — implement Indian grouping by hand so it works on any machine (no new dependency; project-context: keep `requirements.txt` lean).

### Migrations (AC #1)
Reflex discovers `rx.Model(table=True)` models that are imported at app import time. Ensure `finance_app/models.py` is imported by the app (it is, transitively, via the app entrypoint) and that `import reflex_local_auth` runs so auth tables are included. Sequence: `reflex db init` → `reflex db makemigrations` → `reflex db migrate`. The DB file (default `alchemy.db` / `reflex.db` per `rxconfig.py`) must end up with all 8 tables. Keep the generated migration file(s) in the repo (`alembic/versions/…`).

### Previous story intelligence (Story 1.1)
- Environment gotchas that may recur: `reflex run`/CLI on Windows hit a **bun cache EPERM** on first run — a warm retry succeeds (not a code defect). See [1-1 Debug Log](./1-1-project-skeleton-and-app-scaffold.md).
- Story 1.1 added an **AST-based boundary guard** (`tests/test_service_boundary.py`) that flags both `import reflex` **and** `from finance_app import …` inside `services/`. Your enum placement (Task 1) is specifically constrained by this test — respect it.
- `services/utils/format.py`, `services/categorize/schema.py`, `services/narrate/config.py` exist as **placeholders** — fill `format.py` here; leave the other two for their stories.
- Toolchain (pinned, Story 1.1): reflex 0.9.6.post1, reflex-local-auth 0.5.0, sqlmodel bundled, pytest 9.1.1, Python 3.11+ (1.1 ran 3.12.6).

### Testing standards
- `pytest tests/utils/` is the explicit gate for AC #6 — write it first (RED) so the format contract drives the implementation.
- Schema test (`tests/test_models_schema.py`) should build the schema on a **plain SQLAlchemy engine + temp SQLite** (not the Reflex runtime) so it satisfies AD-14 (`services`/data layer testable without starting a Reflex app) and runs fast in CI.
- Full-suite regression: Story 1.1's suite (6 passed) must stay green — re-run `pytest` at the end (Task 6).

### Project Structure Notes
- New files land exactly where the spine's source tree says: `services/utils/format.py` (fill placeholder), `services/utils/enums.py` (new), `finance_app/models.py` (fill placeholder), `tests/utils/test_format.py`, `tests/utils/test_enums.py`, `tests/test_models_schema.py`, plus generated `alembic/` migration(s).
- No structural variance expected. The only judgment call — enum module location — is resolved above (`services/utils/enums.py`) with a testable rationale.

### References
- [Source: epics.md#Story-1.2-Database-Schema--Shared-Formatting-Utilities] (lines 254–271) — acceptance criteria origin
- [Source: ARCHITECTURE-SPINE.md#AD-6] (lines 107–111) — canonical `transactions` schema
- [Source: ARCHITECTURE-SPINE.md#AD-9] (lines 129–133) — `score_events` schema, `trigger_event` spelling
- [Source: ARCHITECTURE-SPINE.md#AD-13] (lines 157–161) — `formatINR`/`formatDate` as the only display path
- [Source: ARCHITECTURE-SPINE.md#AD-2] (lines 83–87) & [#AD-14] (lines 163–167) — services/ framework-agnostic boundary (enum placement)
- [Source: ARCHITECTURE-SPINE.md#Consistency-Conventions] (lines 173–189) — enum values, integer PK + user_id FK convention
- [Source: project-context.md#Agent-Misread-Guards] — `Decimal` money math; enum 3-touch; charts route through format (later)
- [Source: shared/format.js] — JS twin for output parity (AD-13)
- [Source: 1-1 story] (./1-1-project-skeleton-and-app-scaffold.md) — scaffold state, boundary guard, placeholders filled here

## Dev Agent Record

### Agent Model Used

Amelia (Senior Software Engineer persona) · claude-opus-4-8

### Debug Log References

- **Environment bootstrap:** this working tree had no `.venv` and only Python 3.14.6 (Story 1.1 built on 3.12). Created `.venv` (3.14.6) and installed the full pinned `requirements.txt` — reflex 0.9.6.post1, reflex-local-auth 0.5.0, sqlmodel 0.0.39, pandas 3.0.3, camelot-py 2.0.0, statementsparser 0.1.0, anthropic 0.116.0, etc. all resolved cleanly on 3.14 (wheels available; no build failures).
- **`rx.Model` deprecation warning** (expected, non-blocking): `reflex.Model has been deprecated in 0.9.2 … removed in 1.0.0`. Reflex still fully supports it and the architecture spine mandates `rx.Model`/sqlmodel + `reflex db` migrations, so it remains the sanctioned path for Phase 1. Analogous to Story 1.1's Radix deprecation note. Flagged for the Epic-1 retro / a future migration to a plain-SQLModel base.
- **`reflex db init` required `db_url`:** initially failed with "db_url is not configured". Added `db_url="sqlite:///reflex.db"` to `rxconfig.py` (Phase-1 SQLite per spine). Re-ran init → alembic scaffold + initial autogenerated migration `alembic/versions/31751a886cde_.py`; `makemigrations`/`migrate` applied cleanly.
- **Migration discovery wiring:** `finance_app/finance_app.py` did not import `models`, so alembic autogenerate could not see the tables. Added `from finance_app import models` to the entrypoint. Verified the generated migration emits `create_table(...)` for all 9 tables.

### Completion Notes List

- **`users` table = reflex-local-auth's `LocalUser`** (tablename **`localuser`**; fields `id, username, password_hash, enabled`, bcrypt built in) — confirmed by inspecting the installed package. Did NOT create a second `users` table; every user-scoped table's `user_id` FKs to `localuser.id`. The library's `localauthsession` table is also created (needed by Story 1.3/1.4). AC #1's "users" table intent is satisfied by `localuser`.
- **All 7 ACs verified.** AC #1: `reflex.db` created via migration with all 8 required tables (+`localauthsession`, `alembic_version`). AC #2: schema test asserts integer `id` PK + `user_id` FK on all 7 user-scoped tables. AC #3: enums exact/lowercase, `criticality` default `important`. AC #4/#5: `formatINR`/`formatDate` match the JS twin. AC #6: `pytest tests/utils/` green incl. zero, crore, leap-day, and `ValueError` on invalid input. AC #7: money columns are `NUMERIC(12,2)` (Decimal), not float; `formatINR`'s float param documented as display-only.
- **Shared enums placed in `services/utils/enums.py`** (framework-agnostic) so `finance_app/models.py` imports them one-way (UI→Service) — the AD-2 boundary guard (`test_no_ui_layer_import_in_services`) stays green.
- **Deliberate divergence from the JS twin:** the Python formatters raise `ValueError` on invalid input where the JS coerces to `₹0`/echoes the string — required by AC #6.
- **Test results:** full suite **45 passed** in ~58s (Story 1.1's 6 guards + 39 new: 6 enum, 26 format, 7 schema). No regressions; boundary + statementsparser guards still green.
- **Note for committer:** `reflex.db` is git-ignored (`*.db`) — local runtime data, not source. `alembic/` + `alembic.ini` + the migration file ARE source and should be committed (fresh-clone reproducibility for AC #1). `.venv/` ignored.

### File List

**New**
- `services/utils/enums.py` — `Direction`, `CategorySource`, `Criticality` (+ `CRITICALITY_DEFAULT`)
- `tests/utils/test_enums.py`
- `tests/utils/test_format.py`
- `tests/test_models_schema.py`
- `alembic.ini`
- `alembic/` (env.py, README, script.py.mako, `versions/31751a886cde_.py` — initial schema migration)

**Modified**
- `finance_app/models.py` — placeholder → 7 `rx.Model` tables + reflex-local-auth wiring
- `finance_app/finance_app.py` — import `models` so migrations discover tables
- `services/utils/format.py` — placeholder → `formatINR`, `formatDate`
- `rxconfig.py` — added `db_url="sqlite:///reflex.db"`

**Generated (git-ignored, not source)**
- `reflex.db` — local SQLite DB produced by `reflex db migrate`

## Change Log

| Date | Change |
| --- | --- |
| 2026-07-09 | Story 1.2 drafted with comprehensive context — 8-table schema, shared enums (boundary-safe placement), and formatINR/formatDate utilities. Status → ready-for-dev. |
| 2026-07-09 | Story 1.2 implemented (TDD): shared enums, `formatINR`/`formatDate` (JS-twin parity + `ValueError` divergence), 7 `rx.Model` tables FK'd to reflex-local-auth `localuser`, `db_url` + migration wiring; `reflex db` migration stands up all 8 tables in `reflex.db`. Full suite 45 passed, no regressions. Status → review. |
| 2026-07-09 | Code review (inline, full mode): 1 decision + 1 patch applied, 1 deferred, 1 dismissed. `formatINR` broadened to accept `Decimal` (AD-8×AD-13 seam); removed unused `Direction` import and repointed schema test to the enums' canonical home. Full suite 48 passed. Status → done. |
