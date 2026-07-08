---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/A-Product-Brief/project-brief.md
  - _bmad-output/brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/brainstorm-intent.md
  - _bmad-output/problem-solution-2026-07-07.md
  - _bmad-output/innovation-strategy-2026-07-07.md
  - _bmad-output/design-thinking-2026-07-07.md
  - _bmad-output/planning-artifacts/research/domain-ai-driven-personal-finance-management-apps-india-research-2026-07-07.md
  - _bmad-output/planning-artifacts/research/market-personal-finance-copilot-market-india-research-2026-07-07.md
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'AI Financial Copilot — Phase 1 MVP Technical Architecture & Stack (3-Day Local Build)'
research_goals: 'Produce a verified, build-ready reference architecture and technology-stack recommendation for a Phase 1 MVP buildable in 3 days on a local dev setup (no complex infrastructure): secure sign-up/login; PDF/CSV bank-statement upload; automatic transaction extraction + categorization; financial dashboard with charts/summaries; Safe-to-Spend recommendation with plain-language explanation; Confidence Score with visible drivers; natural-language AI Copilot Q&A; personalized insights and proactive guidance. Every stack choice verified against current (2026) sources, optimized for build speed, with the product''s honesty/confidence pillars preserved. AA/WhatsApp/cloud infrastructure explicitly out of Phase 1 scope (deferred, with an evolution path noted).'
user_name: 'ALPHA'
date: '2026-07-07'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-07-07
**Author:** ALPHA
**Research Type:** technical

---

## Research Overview

This report is the technical foundation for the **Phase 1 MVP of the AI-Powered Personal Finance Analyzer**: a locally-run web application, buildable in **3 days** by a single developer, that lets a user sign up, upload a bank statement (PDF/CSV), see extracted and categorized transactions on a dashboard, receive a **Safe-to-Spend** recommendation and **Confidence Score** with plain-language explanations, and converse with an AI Copilot about their finances. The scope was set directly by the product owner and deliberately **excludes** the Account Aggregator integration, WhatsApp delivery, and cloud infrastructure described in the project brief — those remain the Phase 2+ production path, and an evolution route to them is preserved in the recommended architecture.

**Headline recommendation:** a single **Reflex** application ("modular monolith", pure Python compiling to a React frontend + FastAPI/Starlette backend) — Reflex for UI + built-in state/routing, `reflex-local-auth` for auth, Reflex's built-in ORM (`rx.Model`, sqlmodel over SQLAlchemy) on SQLite, `rx.plotly` for charts, pdfplumber + pandas for statement extraction, and the Anthropic Claude API (`claude-opus-4-8`) for categorization fallback, explanation narration, and the conversational Copilot — with the Safe-to-Spend and Confidence Score engines implemented as **deterministic Python code** that the LLM explains but never computes. **UI-framework note:** the product owner selected Reflex over Streamlit on 2026-07-08 for balanced UI/backend flows and full UI control (see the Application Framework decision below); the deterministic-engine + LLM-narration architecture is framework-agnostic and unchanged. All claims were verified against current (2026) public sources; the full executive summary is in the Research Synthesis section at the end of this document.

---

## Technical Research Scope Confirmation

**Research Topic:** AI Financial Copilot — Phase 1 MVP Technical Architecture & Stack (3-Day Local Build)
**Research Goals:** Build-ready reference architecture and stack for the user-defined MVP scope (sign-up/login, PDF/CSV upload, extraction + categorization, dashboard, Safe-to-Spend + explanation, Confidence Score + drivers, NL Q&A Copilot, proactive insights), local dev setup only, 3-day timeline.

**Technical Research Scope:**

- Architecture Analysis — design patterns, frameworks, system architecture
- Implementation Approaches — development methodologies, coding patterns, 3-day build plan
- Technology Stack — languages, frameworks, tools, platforms
- Integration Patterns — Claude API, internal module boundaries, data formats
- Performance Considerations — cost, latency, and the evolution path to Phase 2

**Research Methodology:**

- Current web data with source verification; multi-source validation for critical claims; explicit confidence levels for uncertain information
- Grounded in the six prior BMAD artifacts (project brief, brainstorming intent, problem-solving session, innovation strategy, design thinking, domain + market research)

**Scope Confirmed:** 2026-07-07 — *scope and full-pass execution directed explicitly by the product owner (ALPHA); the step-by-step [C] confirmation gates were waived by that directive and this deviation is recorded in PROJECT-PROGRESS.md.*

**Explicitly out of Phase 1 scope (deferred, not dropped):** Account Aggregator / FIU integration, WhatsApp Business Platform delivery, DPDP consent-manager architecture, native mobile app, cloud deployment, multi-bank reconciliation, vernacular statement parsing at scale.

---

## Technology Stack Analysis

### Programming Language: Python 3.11+

Python is the unambiguous choice: it is the only language where all five workloads of this MVP (PDF table extraction, dataframe manipulation, ML/LLM SDKs, charting, and rapid web UI) have first-class, mature libraries, and every open-source personal-finance-analyzer reference project surveyed uses it. No secondary language is needed — avoiding a JS frontend is the single biggest 3-day time saver.

_Popular Languages: Python dominates the statement-parsing and data-app ecosystem (pdfplumber, camelot, pandas, Reflex, and Streamlit are all Python-native)._
_Confidence: **High**._
_Source: [Parsing Bank Statement PDFs: 5 Tools Compared (2026)](https://dev.to/urios/parsing-bank-statement-pdfs-5-tools-compared-for-developers-2026-4b70), [Reflex — full-stack Python](https://reflex.dev/)_

### Application Framework: Reflex (SELECTED) — decision record

**Decision (2026-07-08):** The product owner chose **Reflex** over Streamlit, prioritizing *balanced UI and backend flows* and the ability to freely modify the UI — the two areas where Streamlit's model is weakest. Reflex is pure Python that **compiles to a real React frontend + FastAPI/Starlette backend**, giving pixel-level UI control (Tailwind classes + CSS props on every component, 60+ components, wrap-any-React-component) and an explicit frontend/backend split (`rx.State` classes = backend, components = UI) — while keeping a single language.

| Option | Verdict for this MVP |
|---|---|
| **Reflex** ✅ SELECTED | Full UI control + built-in backend/frontend separation, still one Python codebase. First-class fits for every MVP feature: `reflex-local-auth` (login/registration/bcrypt), built-in ORM `rx.Model` (sqlmodel/SQLAlchemy → SQLite), `rx.plotly` charts, native streaming chat (the canonical Reflex tutorial is a chat app). Ships routing, uploads, migrations, background tasks. **Cost:** a learning curve — `State` classes, event handlers, async flows — budget ~½ day to ramp, which tightens the 3-day clock. |
| Streamlit (runner-up) | Fastest to ship, zero ramp, but a customization ceiling: theming is easy, bespoke UI needs CSS injection or React components. Rejected for this project because UI flexibility is a stated priority; remains the fallback if the Reflex ramp threatens the deadline. |
| FastAPI + HTMX + Tailwind | Maximum control + a real REST API, but the most hand-building (auth, chat streaming, chart embedding). Heavier than Reflex for the same result at this scope. |
| FastAPI + React / Dash / Gradio / NiceGUI | Two-codebase (React) is not 3-day-realistic; Dash/Gradio more constrained for this feature mix; NiceGUI viable but smaller ecosystem than Reflex. |

**Recommendation: Reflex**, with all business logic in framework-agnostic `services/` modules (engine, narrate, ingestion, categorize) — because Reflex already runs on FastAPI/Starlette, the Phase 2 backend split is essentially free rather than a rewrite.
_Confidence: **High** on the capability comparison (Reflex's own migration/comparison docs + independent 2025 comparisons); **Medium** on the ½-day ramp estimate (depends on prior web-dev familiarity — the one item to validate early)._
_Source: [Reflex vs Streamlit (Reflex)](https://reflex.dev/migration/streamlit/), [Reflex vs Streamlit comparison](https://reflex.dev/blog/2025-08-20-reflex-streamlit/), [Reflex chat-app tutorial](https://reflex.dev/docs/getting-started/chatapp-tutorial/), [Build LLM chat app in Reflex](https://reflex.dev/blog/build-chatbot-llm-python/), [Reflex data-viz / rx.plotly](https://reflex.dev/blog/top-10-data-visualization-libraries/), [FastAPI+HTMX alternative](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb)_

### Statement Extraction: pdfplumber (primary) + pandas (CSV) + statementsparser (accelerator)

- **CSV**: trivial — `pandas.read_csv` with a per-bank column-mapping layer (Indian banks export different column names/date formats; normalize to one canonical schema).
- **PDF (text-based)**: **pdfplumber** — best-in-class for financial statements with complex tables, merged cells, and varying border styles, with visual debugging to tune extraction. **Camelot** (lattice/stream modes) is the fallback when pdfplumber's table heuristics fail on a specific bank's layout.
- **India accelerator**: **statementsparser** (PyPI) parses SBI/HDFC/ICICI/Axis statements into a unified pandas DataFrame, handles password-protected PDFs, extracts UPI metadata, and verifies balances — worth trying first for supported banks; fall back to the pdfplumber pipeline for anything it can't handle.
- **Scanned/image PDFs**: **out of MVP scope** — pdfplumber/camelot only work on text-layer PDFs; OCR is a Phase 2 concern. The UI should detect a no-text-layer PDF and say so honestly (this is exactly the product's "honest about limits" tone).
- **LLM extraction fallback**: for unrecognized text-PDF layouts, pass the raw extracted text to Claude with a structured-output schema — slower and costlier per statement, but rescues the demo when a parser fails.

_Confidence: **High** for pdfplumber/camelot capabilities (multi-source); **Medium** for statementsparser (single source, small project — verify against your own statements on Day 1)._
_Source: [pdfplumber vs Camelot vs Tabula](https://invoicedataextraction.com/blog/python-pdf-table-extraction-invoices), [Extract Tables from PDF — 2026 Guide](https://unstract.com/blog/extract-tables-from-pdf-python/), [statementsparser · PyPI](https://pypi.org/project/statementsparser/), [HDFC PDF parser write-up](https://dev.to/vishwaraja_pathivishwa/building-a-pdf-parser-for-hdfc-bank-statements-from-165-pages-to-csv-in-minutes-34c6), [pdfplumber deep-dive](https://www.blog.brightcoding.dev/2025/09/29/pdfplumber-the-ultimate-python-library-for-precision-pdf-table-and-text-extraction-with-visual-debugging/)_

### Categorization: Hybrid rules-first, LLM-fallback

Industry practice (and the project brief's own directive) is **hybrid, not LLM-for-everything**:

1. **Tier 1 — deterministic rules** (instant, free): keyword/merchant-pattern matching on transaction narration — UPI handles, NEFT/IMPS counterparty names, common Indian merchants (Zomato, Swiggy, BigBasket, Jio, rent/EMI patterns). Covers the bulk of urban Indian transactions.
2. **Tier 2 — Claude batch categorization** (for the remainder): send uncategorized transactions in batches with a **structured-output schema** (category enum + confidence + reasoning). Real-world deployments validate this: ANNA (UK business bank) runs LLM categorization in production with category + reasoning outputs, cutting cost 75% via batching and prompt caching; a 2025 study reports ~90% accuracy on high-confidence predictions in semi-automated flows.
3. **Tier 3 — user correction** ("Teach Me"): a correction writes a new Tier-1 merchant rule — the human-in-the-loop learning loop from the brainstorming session, implemented as a simple `merchant_rules` table.

Every categorization stores `source` (rule / llm / user) and `confidence` — this feeds Prediction Confidence and the provenance-transparency pillar.
_Confidence: **High** for the hybrid pattern; **Medium** on any specific accuracy number (benchmarks vary widely by dataset)._
_Source: [ANNA LLM transaction categorization case study](https://www.zenml.io/llmops-database/cost-effective-llm-transaction-categorization-for-business-banking), [SME bank-transaction classification study](https://arxiv.org/pdf/2508.05425), [LLMs on structured financial data](https://arxiv.org/html/2512.13040v2), [local-LLM expense categorization](https://padulaguruge.medium.com/analyzing-personal-finances-locally-with-ai-using-llms-and-python-panel-for-secure-expense-eb0f3831517c)_

### LLM: Anthropic Claude API — `claude-opus-4-8`

Verified against current (2026-07) Anthropic documentation:

| Capability | Fact (verified) |
|---|---|
| Recommended model | `claude-opus-4-8` — $5.00 / $25.00 per 1M input/output tokens, 1M context, 128K max output |
| Cheaper options | `claude-sonnet-5` $3/$15 ($2/$10 intro through 2026-08-31); `claude-haiku-4-5` $1/$5 — viable for Tier-2 categorization if cost matters later |
| Structured outputs | `client.messages.parse()` with a Pydantic model (or `output_config.format` json_schema) — guarantees valid categorization/score-explanation JSON |
| Thinking | `thinking={"type": "adaptive"}` (do **not** use `budget_tokens` — removed on Opus 4.8) |
| Batch API | 50% price reduction for non-latency-sensitive jobs (bulk categorization of a large statement) |
| Prompt caching | Cache the stable system prompt (persona, tone rules, category taxonomy) — ~90% savings on the cached portion across chat turns |
| Streaming | `client.messages.stream()` for the Copilot chat — an async Reflex `State` handler `yield`s tokens as they arrive, updating the chat UI live |

**Single-user demo cost estimate** (realistic, at Opus 4.8 prices): parsing-fallback + categorizing a ~500-transaction statement ≈ 100–150K input / 20–30K output tokens ≈ **$1.25–1.50** (half that via Batch API); a day of heavy Copilot use (30 Q&As at ~3K in / 400 out each, with prompt caching) ≈ **$0.60–1.00/day**. Total for the entire 3-day build-and-demo cycle: **well under $15**. Dropping Tier-2 categorization to Haiku 4.5 cuts categorization cost ~5x if desired.
_Confidence: **High** — model IDs, pricing, and API patterns taken from current Anthropic reference documentation (2026-06-24 cache)._
_Source: [Anthropic models overview](https://platform.claude.com/docs/en/about-claude/models/overview.md), [pricing](https://platform.claude.com/docs/en/pricing.md), [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md), [batch processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing.md), [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md)_

### Authentication: reflex-local-auth

Reflex's community-standard local-auth library: drop-in login and registration pages, a `@reflex_local_auth.require_login` decorator to gate protected routes, and a `User` model with bcrypt password hashing/verification built on Reflex's own ORM. Setup is `pip install reflex-local-auth` + `reflex db init / makemigrations / migrate`, then extend the `User` model with app fields — a few hours for a local single-user MVP. (Fallback if the library's conventions get in the way: roll a minimal `rx.State`-based auth over a `users` table with `bcrypt` directly — also a few hours.)
_Confidence: **High** for the library existing and covering login/register/bcrypt; **Medium** on exact API stability — pin the version and follow its README._
_Source: [reflex-local-auth (GitHub)](https://github.com/masenf/reflex-local-auth), [PyPI](https://pypi.org/project/reflex-local-auth/), [Reflex authentication overview](https://reflex.dev/docs/authentication/authentication-overview/), [local-auth setup walkthrough](https://dev.to/emmakodes_/setup-user-auth-for-your-reflex-app-using-localauth-4nj8)_

### Database: SQLite

Zero-configuration, in-process, single file — the consensus recommendation for single-user local apps, demos, and prototypes; PostgreSQL's concurrency and scale advantages are irrelevant here and would cost setup time. Access via Reflex's **built-in ORM `rx.Model`** (sqlmodel, which wraps SQLAlchemy) — so models, migrations (`reflex db makemigrations/migrate`), and the SQLite connection are first-party, and the Phase 2 swap to Postgres is a connection-string change. `reflex-local-auth` uses this same ORM, so auth and app tables share one schema.
_Confidence: **High** — uniform across sources; Reflex ORM confirmed in Reflex database docs._
_Source: [PostgreSQL vs SQLite (Better Stack)](https://betterstack.com/community/guides/databases/postgresql-vs-sqlite/), [DataCamp comparison](https://www.datacamp.com/blog/sqlite-vs-postgresql-detailed-comparison), [when SQLite wins](https://medium.com/the-software-journal/postgresql-vs-sqlite-when-you-should-choose-the-wrong-database-70860f36bfad)_

### Dashboard & Charts: Plotly (via `rx.plotly`)

Reflex embeds Plotly natively through the `rx.plotly` component — the same interactive pie/bar/line/treemap charts with hover detail, driven from `rx.State` (a state change re-renders only the affected chart, no full-page rerun). Plotly is built as a Python `Figure` in a `services/` helper and passed to `rx.plotly(data=fig)`. Note the product brief's design directive still applies: **the briefing text is the hero; charts are supporting evidence**, not the primary interface — and Reflex's full layout control makes that hierarchy easy to enforce visually.
_Confidence: **High**._
_Source: [Reflex data-viz libraries / rx.plotly](https://reflex.dev/blog/top-10-data-visualization-libraries/), [Reflex vs Plotly Dash](https://reflex.dev/blog/2025-06-20-reflex-dash/)_

### Full Stack Summary

```
Python 3.11+ · Reflex (UI + state + routing + streaming chat; React+FastAPI under the hood)
reflex-local-auth (auth, bcrypt) · rx.Model / sqlmodel → SQLite (storage) · rx.plotly (charts)
pdfplumber / camelot / statementsparser + pandas (extraction)
Anthropic SDK → claude-opus-4-8 (categorization fallback, narration, Copilot)
python-dotenv (secrets) · pytest (engine tests) · `reflex run` (local dev)
```

---

## Integration Patterns Analysis

### Claude API Integration Patterns

**Pattern 1 — Structured categorization (batch):** uncategorized transactions → one request per ~50-transaction chunk → `client.messages.parse()` against a Pydantic schema `[{txn_id, category (enum), confidence (0-1), reasoning}]`. Use the category **enum** to prevent invented categories. For large statements, the Batch API halves cost.

**Pattern 2 — Narration (the honesty layer):** the deterministic engines produce a JSON "evidence pack" (numbers + drivers + data-quality flags); Claude turns it into plain-language text under a system prompt encoding the tone-of-voice rules from the project brief (honest, calm, non-judgmental, no jargon; never bury the confidence caveat). **The LLM never computes the numbers — it only explains them.** This is the single most important integration decision: it makes the "never cause financial harm through a wrong number" constraint testable, because the number path is deterministic and unit-testable.

**Pattern 3 — Conversational Copilot (tool use):** the chat endpoint gives Claude a small set of **read-only tools** over the user's data — e.g. `get_safe_to_spend()`, `get_confidence_score()`, `query_transactions(filters)`, `get_spending_by_category(period)`, `get_upcoming_commitments()`. Claude answers "Can I afford ₹3,000 for a concert this weekend?" by calling tools, then reasoning over real data. Use the SDK tool runner (or a manual loop) with streaming for responsive UX. Read-only tools keep the "information, never advice / never act" boundary structurally enforced.

**Pattern 4 — Prompt caching:** the system prompt (persona + tone rules + category taxonomy + tool definitions) is stable — mark it with `cache_control: {"type": "ephemeral"}`; volatile per-turn context (today's evidence pack, the user question) goes after the breakpoint.

_Source: [tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md), [streaming](https://platform.claude.com/docs/en/build-with-claude/streaming.md), [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md)_

### Internal Data Formats

**Canonical transaction schema** (everything normalizes to this, regardless of source bank/format):

```
Transaction: id, user_id, date, description_raw, merchant_normalized,
             amount, direction (debit|credit), balance_after (nullable),
             category, category_source (rule|llm|user), category_confidence,
             source_file_id, created_at
```

Supporting tables: `users`, `uploaded_files` (name, bank, format, parse status), `merchant_rules` (pattern → category, learned from corrections), `commitments` (detected/declared recurring obligations: name, amount, due_day, criticality), `score_events` (score, delta, trigger_event, explanation, timestamp — the event-to-explanation binding from the problem-solving session), `chat_messages`.

### Ingestion Pipeline (per upload)

```
file → format detect (CSV/PDF) → parser (pandas | statementsparser | pdfplumber → camelot → LLM-fallback)
  → normalize to canonical schema → dedupe (hash of date+amount+description)
  → Tier-1 rules categorize → Tier-2 LLM categorize remainder → persist
  → recompute commitments, Safe-to-Spend, Confidence Score → generate insight narration
```

Each stage records status so the UI can show honest progress ("Parsed 214 transactions; 187 categorized by rules, 27 by AI, 3 need your help").

### Security Patterns (right-sized for local MVP)

- Passwords: bcrypt via reflex-local-auth (never plaintext).
- API key: `.env` via python-dotenv, `.gitignore`d; never in code or the repo.
- Session: reflex-local-auth session/token; every query scoped by `user_id`.
- PII: data stays in the local SQLite file; only transaction text needed for categorization/Q&A is sent to the Claude API — note this boundary in the UI (provenance transparency doubles as the privacy story).
- Deferred to Phase 2: TLS, encryption at rest, DPDP consent flows, audit logging.

_Source: [reflex-local-auth](https://github.com/masenf/reflex-local-auth); Claude API auth per [Anthropic docs](https://platform.claude.com/docs/en/api/rate-limits.md)_

---

## Architectural Patterns and Design

### System Architecture: Modular Monolith

One process, strict internal module boundaries — the consensus pattern for an MVP of this size (microservices at this scope is pure overhead; a single-file app with business logic tangled into UI callbacks is unmigratable — precisely why the `services/` layer stays framework-agnostic and the Reflex `State` classes only orchestrate it). The layering:

```
┌────────────────────────────────────────────────────────────┐
│  UI LAYER (Reflex pages + components; rx.State per page)   │
│  login/signup · upload · dashboard · briefing · copilot    │
│  (rx.State handlers call the service layer — no logic here)│
├────────────────────────────────────────────────────────────┤
│  SERVICE LAYER (framework-agnostic Python)                 │
│  ingestion/   parsers, normalizer, dedupe                  │
│  categorize/  rules engine, llm categorizer, teach-me      │
│  engine/      safe_to_spend.py, confidence_score.py,       │
│               commitments.py          ← DETERMINISTIC      │
│  narrate/     evidence-pack builder, claude narrator,      │
│               copilot (tools + chat)  ← LLM                │
├────────────────────────────────────────────────────────────┤
│  DATA LAYER   SQLAlchemy models · SQLite file              │
└────────────────────────────────────────────────────────────┘
```

The **engine/ vs narrate/ split is the load-bearing wall**: deterministic money math on one side, LLM language on the other. It implements the brief's "Confidence with Humility" pillar safely and is what Phase 2 lifts unchanged into a FastAPI backend.

### Safe-to-Spend Engine (from the problem-solving session — now implementable)

```
safe_to_spend_today =
    (current_known_balance
     − Σ ring_fenced_commitments(within adaptive window)
     − buffer)
    ÷ days_until_next_confirmed_income
```

Design rules carried from `problem-solution-2026-07-07.md`, all implementable in plain Python:
- **Proximity-weighted ring-fencing**: critical commitments (rent/EMI/insurance) locked ~7 days out, medium ~5, low ~3 — commitments inside the window are fully subtracted regardless of confidence.
- **Two-layer display**: "Today: ₹X" and "After confirmed salary on the 1st: ₹Y" — never present tomorrow's money as today's.
- **Conservative under uncertainty**: variable bills reserve top-of-range; unknown data lowers Prediction Confidence, never inflates Safe-to-Spend.
- **Statement-data caveat (new, MVP-specific)**: balances come from an uploaded statement, so freshness = statement end date. The narration must always carry "based on your statement up to {date}" — this is the MVP analogue of the AA-latency freshness indicator.

### Confidence Score Engine (two-indicator architecture)

- 🛡️ **Confidence Score (0–100)** — financial preparedness only: commitment coverage, buffer vs. upcoming obligations, spending pace vs. income, savings trend. **Never** app-engagement points.
- 🎯 **Prediction Confidence (Low/Med/High)** — data completeness: statement recency, categorization coverage, commitment-detection certainty.
- **Event-to-explanation binding**: score changes only via `score_events` rows that carry (delta, triggering event, explanation, suggested action). The UI renders the score *from* the event log, so an unexplained change is structurally impossible — the root-cause fix from the problem-solving session.
- Cold start (open question Q2 from that session — resolved for MVP): compute from the uploaded statement immediately with Prediction Confidence = Low/Medium and say why; no fake neutral-50.

### Proactive Insights (pattern detection, MVP tier)

Deterministic pandas detectors over the statement history — post-payday spike, repeated-merchant "death by small purchases", zombie subscriptions (recurring similar debits), weekend-vs-weekday pace, upcoming-commitment collision — each emitting an evidence pack that Claude narrates in the brief's Observation → Evidence → Explanation → Action shape. Detectors are cheap, testable, and honest; no ML training needed at this scope.

### Design Principles Applied

- **Separation of computation and narration** (above) — the project's trust moat, expressed in architecture.
- **Ports & adapters at the edges**: parsers behind a `StatementParser` protocol (add banks without touching the pipeline); LLM calls behind a `Narrator`/`Categorizer` interface (mockable in tests; model-swappable).
- **Fail-honest defaults**: any pipeline failure degrades to a visible, plainly-worded state ("I couldn't read pages 3–4 of this statement") rather than a silent wrong number — the kill-signal constraint applied at MVP scale.

_Source: modular-monolith + ports/adapters are framework-agnostic; Reflex's built-in `State`(backend)/component(UI) separation is documented in [Reflex vs Streamlit](https://reflex.dev/migration/streamlit/); engine design constraints from `problem-solution-2026-07-07.md` and `project-brief.md` (internal, previously validated)._

---

## Implementation Approaches and Technology Adoption

### 3-Day Build Plan

**Day 1 — Skeleton + data in** *(goal: a real statement renders as a table)* — *front-load the ~½-day Reflex ramp here*
1. `reflex init`; project scaffold: Reflex app (pages as `rx.page`s), `services/{ingestion,categorize,engine,narrate}/`, `rx.Model` definitions, `.env`, `requirements.txt`. Do the [Reflex chat-app tutorial](https://reflex.dev/docs/getting-started/chatapp-tutorial/) first if new to `rx.State`.
2. `reflex-local-auth` sign-up/login/logout + `@reflex_local_auth.require_login` on protected pages.
3. `rx.Model` tables + `reflex db init/makemigrations/migrate` (SQLite).
4. Upload page (`rx.upload`): CSV path (pandas + column mapper) first, then PDF path (statementsparser → pdfplumber fallback); a `State` handler normalizes, dedupes, persists.
5. Tier-1 rules categorizer (~40–60 India-relevant merchant/keyword rules).
   *Checkpoint: upload your own bank statement, see categorized transactions in an `rx.data_table`/`rx.table`.*

**Day 2 — Intelligence + dashboard** *(goal: the three headline numbers, explained)*
1. Tier-2 Claude batch categorization with structured outputs; store confidence + reasoning.
2. Commitment detection (recurring debit heuristics: similar amount ±10%, ~monthly cadence) + manual add/edit UI.
3. `engine/safe_to_spend.py` + `engine/confidence_score.py` with **pytest unit tests for the 7 WoZ scenarios** from the innovation strategy (the formula "survives all 7 scenarios" gate).
4. Dashboard page: Safe-to-Spend hero card (`rx.card` + Tailwind), Confidence Score + drivers, `rx.plotly` category/trend charts, commitment timeline — all bound to a `DashboardState`.
5. Evidence-pack builder + Claude narrator (tone-of-voice system prompt from the brief) → the daily-briefing panel.
   *Checkpoint: dashboard shows Safe-to-Spend with a plain-language 'why' and a Confidence Score whose drivers are visible.*

**Day 3 — Copilot + insights + hardening** *(goal: the demo loop end-to-end)*
1. Copilot chat page: Reflex chat pattern (async `State` handler that `yield`s tokens as Claude streams) + read-only tools over the user's data; "gut-check" quick-prompt buttons.
2. Insight detectors (3–5 of the pattern list) surfaced on the dashboard + woven into the briefing.
3. "Teach Me" correction flow → `merchant_rules` writeback.
4. Edge-case pass: empty statement, unparseable PDF, single-day data, no detectable income — each must fail honest, not blank.
5. Polish: onboarding empty-states in the brief's microcopy voice; README with run instructions (`reflex run`).
   *Checkpoint: sign up → upload → dashboard → briefing → ask the Copilot three questions → leave more informed. That is the MVP acceptance test.*

**Scope guards (what to cut first if behind):** insight detector count (5→3), commitment auto-detection (keep manual entry), LLM parse-fallback for exotic PDFs (support CSV + 1–2 known banks), 2FA/password-reset flows.

### Testing & Quality (right-sized)

- **pytest on `engine/`** is non-negotiable — the deterministic money math is where a wrong number = the product's kill-signal. Table-driven tests over the 7 WoZ scenarios + boundary dates (due-date today, payday tomorrow, negative balance).
- Parser golden-files: one anonymized sample per supported bank format; assert canonical-schema output.
- LLM calls mocked in tests (interfaces from the architecture section); one live smoke test per pattern.
- Manual E2E once per day against a real statement.

### Cost & Resource Envelope

- **Infra: ₹0** — everything local; no cloud accounts needed.
- **Claude API: < $15 total** for build + demo cycle (estimate verified in the stack section; halve categorization via Batch API, or 5x-cut it via Haiku if it ever matters).
- **Team: 1 developer**, intermediate Python — every component has a documented reference implementation.

### Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| PDF layout defeats parsers on demo statement | Medium | Test *your actual statements* Day 1 hour 1; CSV path as guaranteed fallback; LLM-extraction rescue for text PDFs |
| LLM invents categories / bad JSON | Low | Structured outputs with category **enum** via `messages.parse()` — schema-enforced |
| Copilot states a wrong number | Medium | Numbers only via read-only tools over the deterministic engines; system prompt forbids arithmetic-from-memory; spot-check in demo script |
| Safe-to-Spend wrong on edge dates | Medium | The pytest scenario suite is the gate — the brief's kill-signal logic applied pre-launch |
| 3-day timeline slips | Medium | Scope guards above; day-order chosen so each checkpoint is independently demoable |
| Reflex learning curve eats into the 3 days | Medium | Front-load the ramp in Day 1 hour 1 (do the Reflex chat-app tutorial first); keep UI thin — `State` handlers only call `services/`, no logic in components; **Streamlit is the pre-agreed escape hatch** if the Day 1 checkpoint slips badly (the framework-agnostic `services/` layer makes the swap cheap) |

### Evolution Path (so Phase 1 work survives Phase 2)

| Phase 1 component | Phase 2 destination |
|---|---|
| `services/` modules | Already invoked from Reflex's FastAPI/Starlette backend — extract to a standalone FastAPI service unchanged if/when the UI is replaced |
| `rx.Model` + SQLite | Connection-string swap to Postgres (sqlmodel/SQLAlchemy underneath) |
| Statement upload ingestion | Becomes the multi-source pillar **alongside** AA feeds (brief already mandates upload as load-bearing MVP infra — this work is not throwaway) |
| Reflex UI | Replaced/complemented by WhatsApp-first delivery + native app; briefing/narration prompts carry over verbatim |
| reflex-local-auth | Replaced by production IdP + DPDP-compliant consent flows |
| Claude prompts/tools | Carry over; add confidence-calibration + regional-language work |

---

## Technical Research Recommendations

### Implementation Roadmap
Build in the Day 1→2→3 order above; treat each day's checkpoint as a go/no-go. The pytest engine suite is the only hard quality gate.

### Technology Stack (final)
**Python 3.11+ · Reflex (UI + state + routing + streaming chat) · reflex-local-auth · rx.Model/sqlmodel → SQLite · rx.plotly · pdfplumber (+ camelot fallback, statementsparser accelerator) · pandas · Anthropic SDK (`claude-opus-4-8`, structured outputs, tool use, streaming, prompt caching) · python-dotenv · pytest.**

### Skill Development Requirements
None blocking for an intermediate Python developer. Two 30-minute pre-reads pay for themselves: pdfplumber's table-settings tuning, and Anthropic structured outputs + tool use quickstarts.

### Success Metrics & KPIs (MVP acceptance)
1. All 9 user-scope bullets demonstrable end-to-end on a real statement.
2. Engine test suite green across the 7 WoZ scenarios + edge dates.
3. ≥90% of transactions on the demo statement categorized without user help; every remaining one resolvable via Teach-Me.
4. Every displayed number traceable: source data → engine → evidence pack → narration (the honesty pillar, verifiable by inspection).
5. Copilot answers 10 scripted questions with zero invented numbers.

---

## Research Synthesis — Executive Summary

**The one-paragraph verdict:** the re-scoped 3-day MVP is realistic with a pure-Python **Reflex** modular monolith (real React frontend + FastAPI backend, one codebase), because every risky component has a mature off-the-shelf answer — pdfplumber-class extraction for Indian bank statements, schema-enforced Claude categorization with production precedents, and a chat framework built into the UI layer — leaving the developer's actual creative work exactly where the product's differentiation lives: the deterministic Safe-to-Spend/Confidence-Score engines and the honesty-first narration layer on top of them.

**Key technical findings:**
1. **Reflex was selected (over Streamlit) for balanced UI/backend flows and full UI control** — pure Python that compiles to React + FastAPI, giving pixel-level UI control and an explicit `State`(backend)/component(UI) split in one codebase, with first-party fits for auth (`reflex-local-auth`), ORM (`rx.Model`), charts (`rx.plotly`), and streaming chat. The one tradeoff is a ~½-day learning curve, front-loaded into Day 1 with Streamlit held as an escape hatch; the framework-agnostic `services/` layer makes that safety net cheap.
2. **Text-PDF extraction is solved; scanned PDFs are not** — scope to text-layer PDFs + CSV, detect and honestly refuse image PDFs.
3. **Hybrid categorization (rules → LLM → user-teach) is confirmed industry practice**, echoed independently by the project brief, production case studies (ANNA), and academic benchmarks. Provenance + confidence per transaction is cheap to store and powers the trust story.
4. **The engine/narration split is the architecture's core decision** — deterministic, unit-tested money math; LLM confined to language. This makes the brief's kill-signal constraint ("never a harmful wrong number") an engineering property rather than a hope.
5. **Claude Opus 4.8 with structured outputs, read-only tools, streaming, and prompt caching** covers all three LLM roles (categorize / narrate / converse) at trivial single-user cost (<$15 for the whole build-and-demo cycle).
6. **Prior-session design decisions are directly implementable**: adaptive ring-fencing windows, two-layer Safe-to-Spend display, two-indicator score architecture, and event-to-explanation binding all translate to plain Python + one `score_events` table.

**Strategic implications:** Phase 1 de-risks the product thesis (does an honest, explained Safe-to-Spend number feel different from a tracker?) at near-zero infrastructure cost, while producing three durable assets for Phase 2 — the engine code, the prompt/tone system, and the multi-source ingestion pipeline the brief already declared load-bearing.

### Source Documentation

**Primary technical sources:** Anthropic platform documentation (models/pricing/structured-outputs/batches/caching/tool-use, 2026); Reflex docs, Reflex-vs-Streamlit comparisons, chat-app tutorial, and reflex-local-auth (2025–2026); pdfplumber/camelot/statementsparser docs and comparative analyses (2025–2026); SQLite-vs-Postgres engineering guides (2025). **Secondary:** ANNA LLMOps case study; arXiv transaction-classification studies (2508.05425, 2512.13040); reference personal-finance-dashboard implementations (GitHub). **Internal inputs:** the six BMAD artifacts listed in frontmatter. Confidence levels are marked per section; the three Medium-confidence items to verify hands-on Day 1 are (a) statementsparser's coverage of your specific banks, (b) pdfplumber's handling of your specific statement layouts, and (c) the ~½-day Reflex learning-curve estimate against your own web-dev familiarity.

### Next Steps

1. **Hour 1 of Day 1:** run your real bank statements through statementsparser and pdfplumber — this single test retires the biggest technical risk.
2. Feed this report + the project brief into **`bmad-prd`** (or proceed straight to build via `bmad-quick-dev`, given the 3-day timeline).
3. Carry the three open constraint questions from the problem-solving session into the build as resolved-for-MVP: freshness = statement date (displayed), cold-start = compute immediately with visible Low confidence, multi-bank = single-statement scope with caveat.

---

**Technical Research Completion Date:** 2026-07-07
**Source Verification:** all external claims cited inline with current sources; confidence levels marked per section
**Deviation note:** executed as a single full pass on the product owner's explicit instruction, superseding the per-step [C] gates in the workflow definition.

_Generated using BMAD Technical Research Workflow_
