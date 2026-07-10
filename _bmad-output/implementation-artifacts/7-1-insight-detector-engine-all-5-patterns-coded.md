---
baseline_commit: 9b96699559d9502e6369ddb29af4be968be8c3d7
---

# Story 7.1: Insight Detector Engine — All 5 Patterns Coded

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the system,
I want all five insight detectors implemented as pure, framework-agnostic classes that turn a user's transaction history into structured insight candidates,
so that the insight feed can be produced deterministically — with exact evidence, zero invented numbers, and zero LLM calls — ready for narration (Story 7.2) and display (Story 7.3).

## Story Context

**Epic 7 — Proactive Insights.** This is the epic's first story and its pure-backend heart. Like Epic 4 (the Safe-to-Spend engine), it has **no user-visible output of its own** — its only observable artifact is a green `pytest tests/engine/insights/` run. It is deliberately built ahead of the Epic 7 UI stories (7.3 Insights page, 7.4 Dashboard teaser) and the still-backlog Epics 2/3, because it is pure, contract-defined, and depends only on the canonical transaction shape.

**What this story delivers:** the `InsightDetector` protocol, five detector classes (1:1 with the FR-8.1 named patterns), a typed `InsightCandidate` result carrying the exact evidence data points, named threshold constants, and a unit-test suite (≥1 true-positive + ≥1 true-negative per detector) plus a demo-representative fixture proving ≥3 detectors fire.

**What this story does NOT deliver (explicit scope boundary — do not build):**
- ❌ Narration / O→E→E→A prose → **Story 7.2** (`services/narrate/insight_narrator.py`). Detectors output structured facts, never sentences.
- ❌ Persisting to the `insights` table, the dismiss lifecycle, the ≥15% "materially changed" re-surface rule → **Story 7.3**.
- ❌ The Insights page UI, Dashboard teaser, `rx.State` wiring, the post-ingestion trigger hook → **Stories 7.3 / 7.4** and their `rx.State` handlers.
- ❌ Any DB read, `db_session` handling, or `user_id`-scoped query → **the caller** (see "Architecture seam" below). Detectors receive plain in-memory data.

## Acceptance Criteria

1. **Five detector classes exist, 1:1 with FR-8.1's named patterns**, in `services/engine/insights/detectors.py` (or one module per detector under `services/engine/insights/`):
   - `PostPaydaySpikeDetector` — post-payday spike
   - `DeathBySmallPurchasesDetector` — death-by-small-purchases
   - `ZombieSubscriptionDetector` — zombie subscriptions
   - `WeekendWeekdayPaceDetector` — weekend-vs-weekday pace
   - `UpcomingCommitmentCollisionDetector` — upcoming-commitment collision
   No detector class exists without a named FR-8.1 pattern, and vice versa.

2. Each detector is a class implementing the `InsightDetector` protocol (a `typing.Protocol` defined in `services/engine/insights/protocol.py`) with a single detection method that returns `list[InsightCandidate]` (empty list when the pattern does not fire — never `None`, never a raised exception for "no match").

3. **`InsightCandidate` is a frozen dataclass** carrying only structured facts (no prose): `pattern_name` (str), `severity` (`critical|important|flexible` — reuses `services/utils/enums.Criticality`), `evidence` (a tuple of 2–3 `EvidencePoint` records, each `{date, merchant, amount}`), `metrics` (a mapping of the exact figures the narrator will cite verbatim, e.g. `{"spike_pct": Decimal(...)}`), and `data_months` (int). Every figure a downstream narrator could cite is present here — the narrator does no arithmetic (AD-1 / FR-8.2).

4. **Detectors live in `services/engine/insights/` and import no Reflex / `rx.*` / `finance_app`** — verified automatically by the existing `tests/test_service_boundary.py` (it globs all of `services/**`). All money arithmetic uses `Decimal`, never `float` (AD-8).

5. **Detectors take plain input data, not a DB session** (see "Architecture seam" — this is the documented, approved resolution of the epic's `detect(user_id, db_session)` wording under AD-2). The detection method signature is:
   `detect(self, ctx: InsightContext) -> list[InsightCandidate]`
   where `InsightContext` is a frozen dataclass of plain inputs: `transactions: tuple[TxnRecord, ...]`, `commitments: tuple[CommitmentRecord, ...]`, `as_of: date`, and `income_dates: tuple[date, ...]` (detected paydays; may be empty). No `user_id`, no `Session`, no query inside `services/engine/insights/`.

6. **`pytest tests/engine/insights/` covers every detector with at least one true-positive and one true-negative fixture** — 10 cases minimum (5 detectors × TP+TN). Tests inherit the autouse `_forbid_anthropic` fixture from `tests/engine/conftest.py` (zero-LLM gate, AD-1) by living under `tests/engine/`.

7. **The demo-representative fixture fires ≥3 of the 5 detectors.** A self-contained fixture modelling the June-2026 Priya dataset (24 transactions, one salary credit, ≥1 recurring subscription, a post-payday cluster) lives in the test suite and asserts that running all five detectors over it yields candidates from **at least 3 distinct detectors** — proving "the demo is never a blank Insights page" without depending on the not-yet-built `data/demo-data.json`.

8. **Named threshold constants live in `services/engine/insights/config.py`** (no magic numbers inside detector logic): e.g. `POST_PAYDAY_WINDOW_DAYS`, `POST_PAYDAY_SPIKE_MIN_PCT`, `SMALL_PURCHASE_MAX_AMOUNT`, `SMALL_PURCHASE_MIN_COUNT`, `SUBSCRIPTION_AMOUNT_TOLERANCE_PCT`, `SUBSCRIPTION_MIN_OCCURRENCES`, `WEEKEND_PACE_MIN_RATIO`, `COLLISION_LOOKAHEAD_DAYS`, `MIN_DATA_MONTHS_FOOTNOTE` (=3, FR-8.5). Each detector reads its thresholds from here.

9. **Insufficient-data honesty (FR-8.4 / FR-8.5 inputs):** every `InsightCandidate` reports `data_months`; a detector returns `[]` rather than a low-confidence guess when it has too little history to be honest (e.g. a monthly-cadence detector with <2 cycles). `data_months` is computed from the span of `ctx.transactions`. (The "<30 transactions positive framing" and the "More data sharpens these patterns" footnote are rendered in Story 7.3; this story only supplies the `data_months` signal.)

10. `services/engine/insights/__init__.py` exposes a clean public API: the protocol, `InsightCandidate`, `EvidencePoint`, `InsightContext`, the five detector classes, and a convenience `ALL_DETECTORS` tuple + a `run_all_detectors(ctx) -> list[InsightCandidate]` orchestrator that runs the five in the FR-8.1 order and concatenates results. Internal helpers are `_`-prefixed.

11. `pytest tests/engine/` (whole engine suite, including the new insights tests) stays green and runs in **zero LLM calls, < 10 seconds**, with no new third-party dependency required beyond what the engine already uses (`pandas` is permitted per FR-8.1 "deterministic pandas detectors" but is optional — plain-Python/`statistics` is acceptable if simpler; do not add pandas solely to satisfy the word "pandas").

## Tasks / Subtasks

- [x] **Task 1 — Package scaffold & public API (AC: 1, 4, 10)**
  - [x] Create `services/engine/insights/__init__.py`, `protocol.py`, `types.py`, `config.py`, `detectors.py` (or a per-detector module layout — dev's call, keep it small).
  - [x] Confirm no `reflex` / `finance_app` import creeps in (the boundary test will enforce this).
- [x] **Task 2 — Types & protocol (AC: 2, 3, 5, 9)**
  - [x] `EvidencePoint(date: str, merchant: str, amount: Decimal)` — frozen dataclass; `date` ISO string to match the canonical `Transaction.date`.
  - [x] `TxnRecord` / `CommitmentRecord` — minimal frozen dataclasses of exactly the fields detectors need (see Dev Notes "Input shape"). These are the services-side plain inputs; the caller maps DB rows → these.
  - [x] `InsightContext(transactions, commitments, as_of, income_dates)` frozen dataclass.
  - [x] `InsightCandidate(pattern_name, severity, evidence, metrics, data_months)` frozen dataclass.
  - [x] `InsightDetector` `Protocol` with `detect(self, ctx: InsightContext) -> list[InsightCandidate]`.
- [x] **Task 3 — Threshold constants (AC: 8)** — populate `config.py` with named, documented constants; cite FR-8.1 for each.
- [x] **Task 4 — Implement the 5 detectors (AC: 1, 3, 9)** — each pure, deterministic, `Decimal` math, reads thresholds from `config.py`, returns candidates with 2–3 exact evidence points and the metrics the narrator will cite. Return `[]` on no-fire / insufficient data.
- [x] **Task 5 — `run_all_detectors` orchestrator (AC: 10)** — runs the five in FR-8.1 order, concatenates.
- [x] **Task 6 — Unit tests (AC: 6, 7, 11)** — `tests/engine/insights/` with a TP + TN per detector, plus the demo-representative fixture asserting ≥3 distinct detectors fire. Verify inheritance of the `_forbid_anthropic` gate.
- [x] **Task 7 — Green gate** — `pytest tests/engine/` passes (zero LLM, <10s); `pytest tests/test_service_boundary.py` still green for the new package.

## Dev Notes

### ⚠️ Architecture seam — the `detect(user_id, db_session)` conflict (READ FIRST)

The Epic 7 story text (epics.md §7.1) writes the detector signature as `detect(user_id, db_session) → list[InsightCandidate]`. **Implementing that literally violates AD-2** — `services/**` must not import `finance_app` (where the `Transaction`/`Commitment` `rx.Model`s live) and must run without a Reflex/ORM session (`tests/test_service_boundary.py` enforces this; `pytest services/` must run with no Reflex app). This is exactly the boundary-spanning-AC trap the Epic 4 retro flagged (retro §3, lesson 4).

**Approved resolution (mirror Epic 4 precisely):** detectors are pure and take **plain in-memory input** (`InsightContext`), never a `db_session` or `user_id`. The DB read and the mandatory `user_id`-scoped query (AD-4) happen in the **caller** — the Epic 7 `rx.State` handler / a thin repository added in Story 7.3 — which maps DB rows → `TxnRecord`/`CommitmentRecord`. This is identical to how Epic 4's engine takes `EngineInput`/`CommitmentInput` (plain dataclasses) while the DB mapping + `score_events` writeback were deferred to the Epic 5 handler. It keeps detectors trivially unit-testable with fixture lists (no DB), preserves AD-2, and puts `user_id` scoping where every other service query already does it.

This deviation from the epic's literal wording is intentional and is raised for confirmation (see "Questions for the user" at the end of this file). Do not "fix" it back to a `db_session` signature.

### Epic 4 pattern intelligence — this story's template

Epic 4 (`services/engine/safe_to_spend.py`, `confidence_score.py`) is the directly analogous, completed, reviewed work. **Follow its conventions verbatim:**
- **Pure `Decimal`, frozen dataclasses for all I/O** (`@dataclass(frozen=True)`), `from __future__ import annotations`, rich module docstrings citing the FR/AD.
- **`_ZERO = Decimal("0")` module constant**; helpers `_`-prefixed; public API re-exported in `__init__.py` with `__all__`.
- **Dependency injection / no globals** — detectors receive all inputs; no module-level DB or client.
- **Currency/date in any human-facing string goes through `formatINR`/`formatDate`** (AD-13) — but note detectors emit **structured facts, not prose**, so prefer raw `Decimal`/ISO-string in `metrics`/`evidence` and let Story 7.2 format. (Epic 4 retro §3 caught raw `₹9500` in engine strings — avoid emitting pre-formatted currency here at all; keep it structured.)
- **Test gate:** tests live under `tests/engine/` and inherit `tests/engine/conftest.py`'s autouse `_forbid_anthropic` fixture (any Anthropic client construction raises). Put new tests in `tests/engine/insights/` so they inherit it automatically. Zero network, <10s.

### Input shape (`TxnRecord` — the fields detectors actually need)

Derived from the canonical `Transaction` (finance_app/models.py:52 — but **do not import it**; define the plain services-side twin here):
`date: str` (ISO `YYYY-MM-DD`), `description_raw: str`, `merchant_normalized: str | None`, `amount: Decimal`, `direction: str` (`credit|debit`), `category: str | None`.
`CommitmentRecord`: `name: str`, `amount: Decimal`, `due_date: date` (resolved from `due_day`; the day→date resolution is the caller's job, matching Epic 4's `CommitmentInput.due_date`), `criticality: str`.

> Note: Epic 2's Story 2.1 will define the canonical services-side `Transaction` type formally. Since 2.1 is still backlog and 7.1 is built ahead of it (like Epic 4), define the minimal `TxnRecord` you need now; when 2.1 lands, align to it. Keep `TxnRecord` intentionally minimal so that alignment is cheap.

### Detector semantics (FR-8.1) — deterministic definitions

Ground each detector in FR-8.1 / PRD §FR-8 and the journey example ("Post-payday spike — spending jumps 40% in the 3 days after salary", evidence = 3 specific transactions). Suggested deterministic definitions (thresholds → `config.py`):
- **PostPaydaySpike:** identify payday = a salary-sized recurring `credit` (or from `ctx.income_dates`). Compare mean daily debit spend in the `POST_PAYDAY_WINDOW_DAYS` after payday vs the rest of the cycle; fire when the post-payday rate exceeds the baseline by `POST_PAYDAY_SPIKE_MIN_PCT`. Evidence = the top 2–3 post-payday debits.
- **DeathBySmallPurchases:** count debits ≤ `SMALL_PURCHASE_MAX_AMOUNT`; fire when count ≥ `SMALL_PURCHASE_MIN_COUNT` and their sum is material. Evidence = 2–3 representative small debits; `metrics` carries the count and summed total.
- **ZombieSubscription:** group by `merchant_normalized`; a subscription = ≥ `SUBSCRIPTION_MIN_OCCURRENCES` debits of near-equal amount (±`SUBSCRIPTION_AMOUNT_TOLERANCE_PCT`) at ~monthly cadence. "Zombie" = still recurring. Evidence = the recurring charges. (This detector shares recurring-cadence logic with Story 5.6's commitment auto-detector — factor a shared `_recurring` helper if it reduces duplication, but do not build 5.6 here.)
- **WeekendWeekdayPace:** compare mean weekend (Sat/Sun) daily debit spend vs weekday; fire when weekend/weekday ratio ≥ `WEEKEND_PACE_MIN_RATIO`. Evidence = 2–3 largest weekend debits.
- **UpcomingCommitmentCollision:** for each `ctx.commitments` due within `COLLISION_LOOKAHEAD_DAYS` of `as_of`, fire when the projected balance at due date would be tight/negative (use available balance − intervening reserved commitments; keep it deterministic and conservative — "safety beats precision"). Evidence = the colliding commitment(s). This is the only detector needing `commitments`; the other four need only `transactions`.

Exact numeric thresholds are the dev's calibration call — pick honest, defensible defaults, name them in `config.py`, and make the demo fixture (AC 7) satisfy ≥3. Do not over-tune; KISS.

### Severity & the `insights` table (forward-compat with 7.2/7.3)

The persisted `Insight` model (finance_app/models.py:114) is `pattern_name, observation, evidence, explanation, action_suggestion, status`. **Story 7.2** maps an `InsightCandidate` → those prose fields; **Story 7.3** persists + manages `status`. So `InsightCandidate` must carry everything 7.2 needs to write those fields **without arithmetic**: the observation metric(s), the 2–3 exact evidence points, and any effect figure — all in `metrics`/`evidence`. Set `severity` per pattern (e.g. collision → `critical`, zombie → `flexible`) so 7.3 can order "newest-first within severity tier".

### Project Structure Notes

- **New package:** `services/engine/insights/` (source) + `tests/engine/insights/` (tests). This is consistent with the repo's `services/**` ↔ `tests/**` mirroring (e.g. `services/engine/` ↔ `tests/engine/`).
- **Detected variance from epic wording:** the epic AC says `pytest services/engine/insights/`. The repo convention (Epic 4) keeps tests under `tests/engine/`, and only `tests/engine/conftest.py` carries the AD-1 raising-LLM fixture. **Resolution:** place tests in `tests/engine/insights/` so they inherit that fixture; the `services/engine/` gate remains the mirror. Functionally equivalent to the epic's intent (detector tests run zero-LLM).
- **Detected variance (raised, not silently resolved):** the `detect(user_id, db_session)` signature — resolved to plain-input `detect(ctx)` per AD-2 (see "Architecture seam").
- **No `finance_app` import** anywhere under the new package (AD-2, enforced by `tests/test_service_boundary.py`).

### Testing standards summary

- Framework: `pytest`. Location `tests/engine/insights/`. Table-driven where it reduces repetition (Epic 4's `tests/engine/test_scenarios.py` is the style reference).
- **Zero LLM (AD-1):** inherited via `tests/engine/conftest.py` autouse fixture — do not add an LLM mock; there are no LLM calls in this layer at all.
- Each detector: ≥1 true-positive fixture (asserts it fires with the right `pattern_name`, evidence count 2–3, and expected `metrics`) + ≥1 true-negative (asserts `[]`).
- Demo-representative fixture: asserts `len({c.pattern_name for c in run_all_detectors(demo_ctx)}) >= 3`.
- Boundary: `pytest tests/test_service_boundary.py` (already green) auto-verifies the new package imports no `reflex`/`finance_app`.
- Target ≥80% coverage of the new detector logic (project general standard).

### References

- Epic & ACs: [epics.md §Epic 7 / Story 7.1](../planning-artifacts/epics.md) (lines ~819–841)
- FR-8.1–8.6 detail + demo AC: [prd.md](../planning-artifacts/prd.md) §FR-8 (lines ~250–262); journey step 6 (line ~76)
- Architecture mapping (FR-8 → `services/engine/` detectors + `insights` table, AD-1/AD-3): [ARCHITECTURE-SPINE.md](../planning-artifacts/architecture/architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md) line 297
- Project rules (AD-1 zero-LLM, AD-2 boundary, AD-4 user_id scoping, AD-8 Decimal, AD-13 format): [project-context.md](../project-context.md)
- Pattern to mirror: [services/engine/safe_to_spend.py](../../services/engine/safe_to_spend.py), [confidence_score.py](../../services/engine/confidence_score.py); test gate [tests/engine/conftest.py](../../tests/engine/conftest.py); boundary guard [tests/test_service_boundary.py](../../tests/test_service_boundary.py)
- Data model: [finance_app/models.py](../../finance_app/models.py) — `Transaction` (l.52), `Commitment` (l.87), `Insight` (l.114); enums [services/utils/enums.py](../../services/utils/enums.py)
- Epic 4 retro lessons applied (boundary-spanning AC split; AD-13 in engine strings; scenario-vs-path tests): [epic-4-retro-2026-07-10.md](./epic-4-retro-2026-07-10.md)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story workflow)

### Debug Log References

- `pytest tests/engine/insights/ tests/test_service_boundary.py` → 19 passed (0.13s).
- `pytest tests/engine/ tests/test_service_boundary.py` → **164 passed, 6 skipped (0.25s)** — +16 new tests, zero regressions vs the 148-passed baseline, zero LLM calls (inherited autouse `_forbid_anthropic` gate, AD-1), well under the <10s gate.
- `compileall` clean. ruff not present in the pytest-only `.venv` (matches Epic 4's env); manual unused-import scan clean.
- pandas is absent from the `.venv`; detectors implemented in stdlib-only Python (`statistics`-free, plain `Decimal`), per AC #11's allowance — no new third-party dependency added.

### Completion Notes List

- Delivered the pure-backend detector engine: `services/engine/insights/` with `types.py`, `protocol.py`, `config.py`, `detectors.py`, `__init__.py`. Zero `reflex`/`finance_app` imports (AD-2, verified by the existing `tests/test_service_boundary.py` which globs all of `services/**`). All money `Decimal` (AD-8).
- Five detector classes 1:1 with FR-8.1 (AC #1): `PostPaydaySpikeDetector`, `DeathBySmallPurchasesDetector`, `ZombieSubscriptionDetector`, `WeekendWeekdayPaceDetector`, `UpcomingCommitmentCollisionDetector`. Each returns `[]` (never `None`) on no-fire/insufficient data.
- `InsightCandidate` carries structured facts only — `evidence` (2–3 exact `EvidencePoint`s), `metrics` (every figure the 7.2 narrator will cite verbatim → narrator does no arithmetic), `severity` (Criticality values), `data_months` (FR-8.5 signal). No prose, no pre-formatted currency (AD-1/AD-13; Epic 4 retro §3 lesson applied).
- **Architecture-seam resolution (documented + confirmed by the raised question):** the epic's literal `detect(user_id, db_session)` was resolved to a pure `detect(ctx: InsightContext)` with plain in-memory input, because AD-2 forbids `services/**` importing `finance_app` models or holding a Reflex/ORM session. DB read + `user_id` scoping (AD-4) belong to the caller (Story 7.3), exactly as Epic 4 deferred its DB mapping/writeback to Epic 5.
- **Demo AC (#7) without `data/demo-data.json`:** proven with a self-contained June-2026 Priya-style in-test fixture (`_demo_context`) that fires 4 of 5 detectors (Post-payday, Death-by-small, Weekend pace, Collision; Zombie needs multi-month history so it correctly abstains on a single month) — assertion is `>= 3`. A follow-up should assert ≥3 fire on the real `demo-data.json` when Epic 2/8 produces it.
- Named thresholds live in `config.py` (AC #8); `run_all_detectors` runs the five in FR-8.1 order (AC #10), asserted by a test.
- Tests placed in `tests/engine/insights/` so they inherit `tests/engine/conftest.py`'s autouse zero-LLM fixture (AC #6) — resolves the epic's `pytest services/engine/insights/` wording to the repo's `tests/` mirror convention.

### File List

- `services/engine/insights/__init__.py` (new) — package public API (`__all__`).
- `services/engine/insights/types.py` (new) — `TxnRecord`, `CommitmentRecord`, `InsightContext`, `EvidencePoint`, `InsightCandidate`.
- `services/engine/insights/protocol.py` (new) — `InsightDetector` protocol.
- `services/engine/insights/config.py` (new) — named detector thresholds.
- `services/engine/insights/detectors.py` (new) — 5 detectors + shared helpers + `ALL_DETECTORS` + `run_all_detectors`.
- `tests/engine/insights/__init__.py` (new).
- `tests/engine/insights/test_detectors.py` (new) — TP+TN per detector, protocol/orchestrator checks, ≥3-fire demo fixture (16 tests).
- `_bmad-output/implementation-artifacts/7-1-insight-detector-engine-all-5-patterns-coded.md` (updated) — story record.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (updated) — status transitions.

### Change Log

- 2026-07-10 — Implemented Story 7.1 insight detector engine (5 FR-8.1 detectors, pure/stdlib, zero-LLM). 164 passed / 6 skipped; status → review.

---

## Questions for the user (raised per project-context "raise conflicts before implementing")

1. **`detect(user_id, db_session)` → `detect(ctx)` (plain input).** Story 7.1's AC in epics.md literally specifies a `db_session` signature; this story resolves it to a pure plain-input signature to satisfy AD-2 (services/ cannot import `finance_app` models or hold a Reflex session), exactly as Epic 4 did. DB read + `user_id` scoping move to the caller (Story 7.3). **Confirm this resolution** (recommended), or state you want the detectors to query the DB directly (which would require relaxing AD-2 / relocating the models).
2. **`demo-data.json` does not exist yet** (only `data/.gitkeep`). AC 7 is satisfied here with a self-contained in-test demo fixture that proves ≥3 detectors fire, decoupled from the file. The real `data/demo-data.json` (24-txn June-2026 Priya dataset) is produced in Epic 2/8; when it lands, a follow-up test should assert ≥3 fire on it too. **Confirm** the in-test fixture approach for now.
