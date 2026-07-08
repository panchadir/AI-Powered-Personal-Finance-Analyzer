# Epics & Stories — Phase 1 MVP (3-Day Reflex Build)

**Created:** 2026-07-08
**Author:** ALPHA
**Pairs with:** [`prd.md`](prd.md) · [technical research](planning-artifacts/research/technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md) · [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md) (engine gate) · [`ux-spec-mvp.md`](ux-spec-mvp.md) (layout + microcopy)

> Backlog for a single developer over 3 days. Story IDs map to PRD functional requirements (FR-n). Each story is small enough to finish and demo. **Priority:** P0 = MVP-blocking · P1 = MVP-complete · P2 = cut first if behind. Estimates are relative (S/M/L) for a solo dev.

---

## Build order & day mapping

| Day | Epics | Checkpoint (must be demoable) |
|---|---|---|
| **Day 1** | E1 Foundation & Auth · E2 Ingestion · E3 Categorization (Tier 1) | Upload your own statement → see categorized transactions in a table |
| **Day 2** | E3 (Tier 2) · E4 Financial Engine · E5 Dashboard & Briefing · E7 Commitments | Dashboard shows Safe-to-Spend + Confidence Score, each explained |
| **Day 3** | E9 Hardening (must) · **E6 Copilot + E8 Insights = stretch** | Sign up → upload → dashboard → briefing (golden path). Stretch: ask Copilot 3 questions; 1 insight |

**Golden path vs. stretch (2026-07-08):** the must-ship MVP is **E1–E5 + E7 + E9** (capabilities 1–6, each explained). **E6 (Copilot) and E8 (Insights) are demo-stretch** — build on Day 3 only if the S4.2 engine gate is green and time remains; if cut, the MVP still passes. Never fake the Copilot's numbers to save time (cut it instead).

**Reflex go/no-go — Day 2, noon:** if `rx.State` reactivity / the app skeleton is still fighting you at midday Day 2, invoke the pre-agreed **Streamlit escape hatch** (the framework-agnostic `services/` layer makes the swap cheap). Don't discover this on Day 3.

**Golden rule for every story:** business logic goes in `services/`; Reflex `State` classes and components only orchestrate and display.

---

## E1 — Foundation & Auth (P0, Day 1) → FR-1
**Goal:** a running Reflex app a user can register into and log into, with local persistence.

- **S1.1 (S)** `reflex init`; project skeleton — pages, `services/{ingestion,categorize,engine,narrate}/`, `models.py`, `.env`, `requirements.txt`. *(Do the Reflex chat-app tutorial first if new to `rx.State` — this is the ½-day ramp.)*
  - AC: `reflex run` serves a blank multi-page app locally.
- **S1.2 (M)** `rx.Model` tables (users + app schema) + `reflex db init/makemigrations/migrate` on SQLite.
  - AC: DB file created; tables match the PRD data model.
- **S1.3 (M)** Integrate `reflex-local-auth`: register / login / logout pages; `@reflex_local_auth.require_login` on protected pages.
  - AC: register → logout → login works; passwords bcrypt-hashed; unauthenticated access redirects to login.
- **S1.4 (S)** Scope every data query by `user_id`.
  - AC: a second test user sees none of the first user's data.

## E2 — Statement Ingestion (P0, Day 1) → FR-2
**Goal:** a real statement becomes clean, de-duplicated transaction rows.

- **S2.1 (S)** Canonical transaction schema + `StatementParser` protocol (ports/adapters).
  - AC: one interface all parsers return.
- **S2.2 (M)** CSV parser + per-bank column mapper (≥2 common Indian-bank shapes) → canonical schema.
  - AC: a CSV statement parses with correct dates/amounts/direction.
- **S2.3 (L)** PDF parser chain: statementsparser (supported banks) → pdfplumber → camelot fallback.
  - AC: a text-PDF statement parses to correct transaction count/values. *(Validate against YOUR real statements first thing.)*
- **S2.4 (M)** `rx.upload` page + `State` handler: normalize → dedupe (hash of date+amount+description) → persist; render results in `rx.data_table`/`rx.table`.
  - AC: upload shows honest progress ("Parsed N; …"); re-upload creates no duplicates.
- **S2.5 (S)** Detect no-text-layer (scanned) PDF → honest refusal message.
  - AC: a scanned PDF yields a plain-language "I can't read this one," not a crash or wrong data.
- **S2.6 (M, P2)** LLM-text extraction fallback for unrecognized text-PDF layouts.
  - AC: an unparseable-by-rules text PDF still yields usable transactions via Claude.

## E3 — Categorization (P0, Day 1→2) → FR-3
**Goal:** transactions get categories with provenance + confidence, and the user can teach corrections.

- **S3.1 (M)** Tier-1 rules engine: ~40–60 India-relevant merchant/keyword rules → category; store `category_source='rule'`.
  - AC: bulk of demo transactions categorized instantly.
- **S3.2 (L)** Tier-2 Claude batch categorizer via `messages.parse()` with a Pydantic schema (category **enum** + confidence + reasoning); store `source='llm'`, confidence, reasoning. Behind a `Categorizer` interface (mockable). **Model: `claude-haiku-4-5`** (per PRD NFR-4 — cheap, fast, enum-constrained; the hard enum also blocks prompt injection from a hostile merchant string).
  - AC: no invented categories; remaining transactions categorized; confidence stored.
- **S3.3 (M)** "Teach Me" correction flow → writes a `merchant_rules` row → re-applies to matching transactions; store `source='user'`.
  - AC: a correction persists and auto-categorizes future matching merchants.

## E4 — Financial Engine (P0, Day 2) → FR-4, FR-5 · **the critical, tested epic**
**Goal:** deterministic, unit-tested Safe-to-Spend and Confidence Score. No LLM in this epic.

- **S4.0 (S, Day 0/pre-flight)** Confirm the engine spec: read [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md) — the 10 enumerated scenarios (7 core + 3 boundary), the Reservation Rule (DD-1), and the buffer decision (DD-2). *(This story replaces the old phantom "7 WoZ scenarios" reference — the scenarios now exist in build-ready form; ~2h, must be done before S4.1.)*
  - AC: the scenario file's expected outputs are the contract S4.1 implements and S4.2 asserts.
- **S4.1 (L)** `engine/safe_to_spend.py`: implements the formula per DD-1 (known commitments due on-or-before income fully reserved; predicted ones only inside the 7/5/3 proximity window; variable bills top-of-range; STS floored at ₹0); two-layer today/after-income output; freshness caveat data.
  - AC: returns the two-layer figure + evidence pack (reserved_total, spendable_pool, days_to_income, prediction_confidence, drivers, data-quality flags, safety_ok).
- **S4.2 (L)** **pytest suite** — table-driven over the 10 scenarios in [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md), asserting each evidence-pack field + the CS-1..CS-4 Confidence-Score companion assertions.
  - AC: **all green**; `safety_ok` True for scenarios 1–9 and honest-shortfall for 10; never recommends spending that misses a ring-fenced commitment. *(This suite is the MVP quality gate — green before the dashboard is wired.)*
- **S4.3 (M)** `engine/confidence_score.py`: 0–100 preparedness score + separate Low/Med/High Prediction Confidence; cold-start = compute-now-with-low-confidence.
  - AC: score reflects preparedness only (never engagement); prediction confidence reflects data completeness.
- **S4.4 (M)** `score_events` writeback: every score change binds (delta, trigger event, explanation, action); score rendered from the event log.
  - AC: no score change without a matching explanation row; score never contradicts Safe-to-Spend.

## E5 — Dashboard & Briefing (P0/P1, Day 2) → FR-6
**Goal:** the three headline numbers, explained, on one calm screen. **Layout + microcopy: follow [`ux-spec-mvp.md`](ux-spec-mvp.md)** (hero number + "why" above any chart; two-layer Safe-to-Spend never merged; paste-ready tone-of-voice strings).

- **S5.1 (M)** `DashboardState` + dashboard page: Safe-to-Spend hero card (`rx.card` + Tailwind), Confidence Score + visible drivers, `rx.plotly` category/trend charts, commitment timeline.
  - AC: leads with number + "why," not a chart wall; charts are supporting evidence.
- **S5.2 (M)** `narrate/` evidence-pack builder + Claude narrator with the brief's tone-of-voice system prompt (prompt-cached).
  - AC: briefing reads as a calm, honest sentence; **every number in prose equals the engine output** (spot-checked).
- **S5.3 (S, P1)** Briefing follows Observation → Evidence → Explanation → Action.
  - AC: structure visible in output.

## E6 — AI Copilot (**Day 3 STRETCH**) → FR-7
**Goal:** conversational Q&A that reasons over real data and never invents numbers. *(Demo-stretch: build only if the S4.2 engine gate is green and time remains. If cut, the golden-path MVP still passes. Never fake the numbers to ship it.)*

- **S6.1 (L)** Chat page + async `CopilotState` handler that `yield`s Claude's streamed tokens into the chat UI.
  - AC: responses stream live; history persists in `chat_messages`.
- **S6.2 (L)** Read-only tools over user data (`get_safe_to_spend`, `get_confidence_score`, `query_transactions`, `get_spending_by_category`, `get_upcoming_commitments`); tool-runner/manual loop; system prompt forbids arithmetic-from-memory and any financial action.
  - AC: 10 scripted questions answered with zero invented numbers; every figure traces to a tool call.
- **S6.3 (S, P1)** "Gut-check" quick-prompt buttons.
  - AC: "Can I afford ₹X this weekend?" reasons over the real Safe-to-Spend.

## E7 — Commitments (P1, Day 2) → FR-9
**Goal:** recurring obligations feed ring-fencing.

- **S7.1 (M)** Recurring-debit detector (similar amount ±10%, ~monthly) → candidate commitments.
  - AC: rent/EMI-like patterns detected.
- **S7.2 (S)** Add/edit/delete commitment UI (name, amount, due-day, criticality).
  - AC: manual commitments feed Safe-to-Spend correctly.

## E8 — Proactive Insights (**Day 3 STRETCH**) → FR-8
**Goal:** named behavioral patterns, honestly framed. *(Demo-stretch. For MVP, ship **1** strong detector, not five — zombie-subscriptions or post-payday spike reads best in a demo.)*

- **S8.1 (L→M)** Deterministic pandas detectors (post-payday spike · death-by-small-purchases · zombie subscriptions · weekend/weekday pace · upcoming-commitment collision), each emitting an evidence pack. **MVP target: 1 detector; scale to ≥3 only if time.**
  - AC: at least 1 insight fires on a realistic statement with its evidence.
- **S8.2 (S)** Narrate insights in Observation → Evidence → Explanation → Action; surface on dashboard.
  - AC: each names a real pattern with evidence; tone is observation, never accusation.
- **S8.3 (S, P2)** Weave insights into the briefing.

## E9 — Hardening & Polish (P0/P1, Day 3) → NFR-1, capability 9
**Goal:** fail-honest everywhere; the demo loop is clean.

- **S9.1 (M)** Edge-case pass: empty statement · unparseable PDF · single-day data · no detectable income — each fails honest (visible, plainly-worded), never blank/wrong.
  - AC: every edge case shows an honest message.
- **S9.2 (S)** Onboarding empty-states in the brief's microcopy voice.
  - AC: first-run screens use the tone-of-voice examples (warm, non-judgmental).
- **S9.3 (S)** README: setup + `reflex run` instructions + `.env` (API key) note.
  - AC: a fresh clone runs from the README.
- **S9.4 (S)** Demo-script dry run of the full loop (sign up → upload → dashboard → briefing → 3 Copilot questions).
  - AC: the MVP acceptance loop completes end-to-end.

---

## Scope-guard cut order (if behind)
1. S8.3 → S6.3 → S5.3 (P2/P1 polish)
2. Insight detectors 5 → 3 (S8.1)
3. S7.1 (keep manual commitment entry S7.2; drop auto-detect)
4. S2.6 (drop LLM PDF fallback; support CSV + 1–2 known banks)
5. 2FA/password-reset (never in scope for MVP)

**Never cut:** S4.1–S4.4 (the engine + its tests) and S6.2 (read-only tools) — they are the honesty/safety spine.

---

*Generated by BMAD — direct authoring from the PRD + technical research. Next: `create the next story` (bmad-create-story) to expand any story into a full dev-context file under implementation-artifacts, or begin the build with `bmad-quick-dev`.*
