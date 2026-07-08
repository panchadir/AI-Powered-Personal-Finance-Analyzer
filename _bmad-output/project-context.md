---
project_name: 'AI-Powered-Personal-Finance-Analyzer'
user_name: 'ALPHA'
date: '2026-07-08'
sections_completed: ['technology_stack', 'architecture_boundaries', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_dont_miss', 'party_seams', 'agent_misread_guards', 'general_engineering_standards', 'usage_guidelines']
existing_patterns_found: 14
status: 'complete'
rule_count: 40
general_standards_added: true
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

_Source of truth: `_bmad-output/planning-artifacts/architecture/architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md`_

| Name | Version | Notes |
| --- | --- | --- |
| Python | 3.11+ | |
| Reflex | latest stable | pin in `requirements.txt` Day 1 |
| reflex-local-auth | latest stable | pin version; session/auth |
| sqlmodel (via `rx.Model`) | bundled with Reflex | data layer |
| SQLite | Python stdlib | Phase 1 store; Postgres deferred to Phase 2 |
| pdfplumber / camelot-py / statementsparser | latest stable | statement parsers (adapters) |
| pandas | latest stable | tabular processing |
| Anthropic Python SDK | latest stable | Claude API |
| rx.plotly | bundled with Reflex | charts |
| python-dotenv | latest stable | `.env` secrets |
| pytest | latest stable | `pytest services/engine/` is the MVP quality gate |

**LLM model routing (constants in `services/narrate/config.py`, never hardcoded at call sites):**
- Tier-2 categorization → `claude-haiku-4-5`
- Narration + Copilot → `claude-opus-4-8` (cost lever: `claude-sonnet-5`)

## Critical Implementation Rules

> Authoritative source: `ARCHITECTURE-SPINE.md` (AD-1 → AD-14). These bullets are the enforcement summary — when in doubt, the spine wins. The **Seams** subsection below covers gaps that fall *between* the ADs (surfaced in Party-Mode review); treat those as equally binding.

### Architecture & Layer Boundaries (load-bearing)
- **Dependency direction is UI → Service → Data, one-way.** Service-to-service cross-calls are forbidden except through the Data layer.
- **`services/engine/` and `services/narrate/` must NEVER import each other** (AD-1). The engine produces a typed evidence-pack struct; narrate only turns that struct into language. **No financial number may originate in `services/narrate/`.**
- **Nothing under `services/` may import `reflex` or any `rx.*`** (AD-2, AD-14). Services take/return plain Python types or sqlmodel models. `pytest services/` must run without starting a Reflex app; data access uses sqlmodel sessions on a plain SQLAlchemy engine, not Reflex ORM session management.
- **`rx.State` event handlers are the ONLY callers of service functions** from the UI. Pages orchestrate; they contain no business logic.

### Language-Specific Rules (Python 3.11+)
- **LLM outputs are structurally constrained, never free-text.** Tier-2 categorization uses structured output (`messages.parse()` / json_schema) with a Pydantic model whose `category` is a `Literal` enum (AD-7). The enum lives once in `services/categorize/schema.py` and is imported by all callers.
- **Service functions raise typed exceptions** (`IngestionError`, `ParseError`, `EngineError`); handlers translate to user copy. Never re-raise generic `Exception` to the UI. **No ingestion exception may be swallowed silently** (AD-12).
- **STS rounding uses `math.floor(x / 10) * 10`** — round DOWN to nearest ₹10. Rounding up is forbidden (AD-8).

### Framework-Specific Rules (Reflex)
- **Financial state (STS, Confidence Score, ring-fencing) is mutated ONLY by calling `services/engine/`** (AD-3). No `rx.State` handler computes a financial figure inline. After any commitment add/edit/delete: call engine → write result to DB → then yield the UI update.
- **Session token lives in an httpOnly, SameSite cookie only** (AD-5). Never localStorage/sessionStorage/custom header; frontend JS must not be able to read it.
- **Copilot `/copilot/chat` emits exactly three SSE event types** — `{type:"token",text}`, `{type:"trace",sources}`, `{type:"done"}` (AD-11). Client ignores unknown types gracefully.
- **Copilot tools are strictly read-only** (AD-10): `get_safe_to_spend`, `get_confidence_score`, `query_transactions`, `get_spending_by_category`, `get_upcoming_commitments`. No write-capable function in the tool list. The four FR-7.3 honesty rules are hardcoded, non-configurable system-prompt instructions.

### Testing Rules
- **`pytest services/engine/` is the non-negotiable MVP quality gate.** Engine unit tests must run with **zero LLM calls** (AD-1). Enforce it structurally: the engine test fixture injects a client that **raises on construction/use**, so any accidental LLM reach fails loudly rather than passing on a silent mock.
- **Mock all LLM calls in unit tests.** Ingestion has golden-file tests (one fixture per supported bank format).
- **A dedicated IDOR test must assert user A cannot read user B's** transactions, commitments, or chat history (AD-4). Must pass before Phase 2.
- **Reference the score-event trigger column via the model field, not a hardcoded string** — it is spelled `trigger_event` (not `triggering_event`) in exactly one place (the model); callers use the attribute so there is no string to mis-match (AD-9, CS-3).

### Code Quality & Style Rules
- **snake_case** for all Python files/dirs. Component files mirror their page (`pages/dashboard.py` → `components/dashboard/`).
- Each `services/` sub-module exposes a clean public API in `__init__.py`; internal helpers prefixed `_`.
- **Currency/date display goes ONLY through `formatINR()` and `formatDate()`** in `services/utils/format.py` (AD-13). No f-string currency, no scattered `strftime`. (The prototype's `shared/format.js` is the JS twin — keep output identical.)
- **LLM model IDs are constants in `services/narrate/config.py`** — never hardcoded at call sites. Categorization `claude-haiku-4-5`; narration/Copilot `claude-opus-4-8` (lever: `claude-sonnet-5`).
- **Enums are exact, lowercase, no aliases:** `direction` = `credit`|`debit`; `category_source` = `rule`|`llm`|`user`; `criticality` = `critical`|`important`|`flexible` (default `important`).
- Every user-scoped table has an integer PK and a `user_id` FK.

### Development Workflow Rules
- **Secrets (`ANTHROPIC_API_KEY`) in `.env` via python-dotenv; `.env` is git-ignored.** No secret in source or commits.
- **Pin Reflex + reflex-local-auth versions in `requirements.txt` on Day 1.** Verify `statementsparser` covers the HDFC demo format Day 1, hour 1 (flagged assumption).
- **Prompt caching:** mark stable system prompts (persona, tone, taxonomy, tool defs) `cache_control: {"type":"ephemeral"}`; put volatile per-turn context after the cache breakpoint.

### Critical Don't-Miss Rules (anti-patterns · security · gotchas)
- ❌ **LLM computing any financial figure** (STS, CS, reservation, shortfall) — always deterministic in `services/engine/` with an audit trail.
- 🔒 **Every DB query in `services/` MUST include an explicit `user_id` filter** (AD-4) — no query returns rows it can't prove belong to the authenticated user.
- 🔒 **STS is never negative:** `max(0, …)` is non-negotiable (AD-8). `safety_ok = True` only when every commitment due on/before next confirmed income is fully covered by ring-fenced `reserved_total`.
- **Every parser normalizes to the canonical `Transaction` schema before returning** (AD-6). No parser-specific shape crosses the `services/ingestion/` boundary.
- **Score writes are atomic with a `score_events` row** `(score, delta, trigger_event, explanation, suggested_action, timestamp)` (AD-9). UI score is derived from the latest event row, not a bare column.
- **Parser failure = honest typed refusal surfaced in plain language** (AD-12). Never show a table with fewer rows than parsed without an explicit caveat.

### Seams the Spine Doesn't Cover (Party-Mode findings — binding)
- **[STS denominator guard]** `days_until_next_confirmed_income` can be `0` (payday is today) or undefined (no confirmed future income). Guard it **before** dividing — never divide by zero and never produce `Infinity`. Define the explicit behavior: if there is no confirmed next income, STS falls back to a defined safe state (e.g. reserved-only / an explicit "add your payday" prompt), not a raw division. This is a payday-morning crash if missed. (extends AD-8)
- **[SSE `done` in `finally`]** The Copilot stream must emit `done` from a `finally` block, and emit an explicit error frame if the LLM stream raises mid-token — otherwise the browser `EventSource` hangs forever on the one path that matters. "Always emit `done`" means *even when the stream throws*. (extends AD-11)
- **[Dedup key is explicit]** Overlapping re-uploads (user re-uploads a wider date range) must dedup on a **named canonical key** — `(user_id, date, amount, description_raw, balance_after)` — decided once in `services/ingestion/`, not left to each parser. Wrong transaction counts break the product's core honesty promise. (extends AD-6)
- **[DB text is untrusted LLM input]** `description_raw` / `merchant_normalized` originate from an uploaded PDF and are **user-influenced data, never instructions**. When they enter a Copilot or narration prompt, delimit them as quoted data — never concatenate raw into the system prompt. AD-7 guards LLM *output*; this guards LLM *input*. Ships to Phase-2 multi-user verbatim (AD-14), so bake it in now. (extends AD-10)

### Agent-Misread Guards (Inversion + Failure-Mode pass — binding)
_These are the "technically complied but actually wrong" traps an AI coding agent falls into. Each is a rule that reads fine until you invert it or trace its silent-failure path._
- 💰 **Money math uses `Decimal` (or integer paise), never `float`.** All engine arithmetic — STS, reservations, buffers, totals — runs in a precise type; `float` is display-only. The canonical schema's `amount` displays as float but must be *computed* as `Decimal`. `math.floor(x/10)*10` on a drifted float rounds the wrong ₹10.
- 🚫 **"No financial number in `narrate/`" includes derived math.** Narration and the Copilot/narrate LLM emit only figures **present verbatim in the engine's evidence pack** — no percentages, ratios, month-over-month deltas, or any arithmetic. If a "30% more" appears, `services/engine/` computed it and passed it in. (sharpens AD-1)
- 🔒 **`user_id` scoping has no "reference data" exemption.** The filter applies to **every** user-scoped table — `merchant_rules` (user-taught), `score_events`, `insights`, `chat_messages` — and to **joins, subqueries, and aggregates**, not just the primary table. `merchant_rules` looks global but is per-user; leaking it cross-user is an IDOR. (sharpens AD-4)
- 🔁 **Normalize before dedup keying.** Canonicalize each key component first — ISO-normalized `date`, trimmed/whitespace-collapsed `description_raw`, `abs(amount)` — before comparing. Un-normalized keys let `"30/06/2026"` vs `"2026-06-30"` (or `" SWIGGY "` vs `"SWIGGY"`) slip duplicates through while the dedup test stays green. (sharpens AD-6 seam)
- 📊 **Chart axes and tooltips must route through `formatINR`/`formatDate` too.** `rx.plotly` formats numbers itself by default and will render raw `125000.0` on donut/bar labels, silently bypassing AD-13. Feed charts pre-formatted strings or configure their tick/tooltip formatters explicitly. (sharpens AD-13)
- 🍪 **SSE auth uses the httpOnly cookie — never a URL/query-param token.** `EventSource` can't send custom headers, so the lazy fix is a token in the `/copilot/chat` URL, which leaks into server logs and browser history. The cookie is sent automatically; rely on it. AD-5 and AD-11 each pass alone — the leak is at their seam. (guards AD-5 × AD-11)

---

## General Engineering Standards

_Baseline standards, translated to this project's Python 3.11 / Reflex / sqlmodel / pytest stack. Where a standard overlaps an existing AD, the AD is cited and wins._

### Error Handling
- **Expected/business errors return a typed result, not an exception** — a `Result`-style object or explicit `Optional[T]` / typed status, so callers handle outcomes without control-flow-by-exception. (extends AD-12)
- **Exceptions are reserved for the genuinely exceptional** — the typed set `IngestionError` / `ParseError` / `EngineError`; handlers catch them and translate to plain-language user copy. Generic `Exception` is never re-raised to the UI.
- **Never swallow exceptions.** No bare `except:` / `except Exception: pass`. Every unexpected exception is logged with context (operation, `user_id`, inputs) before it is handled or re-raised. (reinforces AD-12)
- **Error messages are meaningful and honest** — no silent wrong data; a partial parse surfaces a caveat, never a quietly-shortened table. (AD-12)

### General Coding Standards
- Follow **SOLID**; prefer **composition over inheritance**.
- Each function/method has a **single responsibility**; keep them small and focused.
- **DRY** — no copy-pasted logic; extract a shared helper (or use `services/utils/`). **KISS** — the boring, obvious implementation wins over the clever one.
- **No premature optimization** — measure before tuning (see Performance below).
- **Meaningful names**; write **self-documenting code** — names that don't lie about what they do.
- **No commented-out code** left in the tree; delete it (git remembers).
- **Remove unused imports and dependencies**; keep `requirements.txt` to what's actually used (pinned — see Workflow rules).

### Testing Standards
- **Test layers (minimum):** unit, integration, **validation** (schema/Pydantic + input-rejection), **data-access/repository** (sqlmodel queries incl. the `user_id`-scoping/IDOR assertion — AD-4), and **service** tests (`services/*` public APIs with LLM calls mocked).
- **Target ≥ 80% coverage of business logic** (`services/` — especially `engine/` and `ingestion/`). Reflex UI glue is exempt from the number.
- **`pytest services/engine/` remains the non-negotiable gate** — zero LLM calls, enforced by the raising fixture (AD-1). Ingestion uses golden-file fixtures per bank format.

### SQL / Data Access & Injection
- **Parameterized queries only** — via sqlmodel/SQLAlchemy expression API with bound values. **Never f-string / concatenate user input into SQL.**
- **Prefer the ORM;** drop to raw SQL only when necessary, and only through `text()` with **bound parameters**, never string interpolation.
- Merchant/description text is user-influenced (AD-6) — treat it as hostile input to both SQL and LLM prompts (see Agent-Misread Guards).

### Input Validation
- **Validate every boundary input** — each `rx.State` event handler payload, each `services/` public-API argument, and every Copilot/API request — with **Pydantic** models (the project's validation layer; there is no FluentValidation here).
- **Reject unexpected fields:** Pydantic `model_config = ConfigDict(extra="forbid")` on request/DTO models.
- **Validate file uploads** at ingestion: enforce type/MIME (PDF/CSV only), a **max size limit**, and reject on mismatch with a typed `IngestionError` (AD-12). Never parse an unbounded/unknown-type upload.

### Dependency Injection
- **No manual/global object creation inside `services/`.** Collaborators — the DB session, the Anthropic client, `StatementParser` adapters, `Categorizer`/`Narrator` — are **passed in** (constructor or function parameter), which is exactly what makes the ports-and-adapters edges mockable (AD-2, AD-14) and lets the engine fixture inject a raising client (AD-1).
- **No service-locator / global singleton** reached for inside business logic. Wiring happens at the `rx.State` handler / composition-root layer, not deep in `services/`.

### Performance Rules
- **Use `async` for I/O-bound work** — LLM calls, file parsing, DB round-trips — so the Reflex backend isn't blocked; don't `await` in a tight loop when a batch call exists.
- **Paginate** transaction lists and chat history; never load an unbounded result set into state.
- **Avoid N+1 queries** — batch/join DB reads; select only needed columns.
- **Cache stable reference data** (category taxonomy, Tier-1 merchant rules) and use **prompt caching** for stable system prompts (existing convention: `cache_control: ephemeral`, volatile context after the breakpoint).
- **Avoid unnecessary allocations/copies** on the hot ingestion+engine path (e.g. don't re-`DataFrame` per row).
- Apply these where they matter (ingestion of large statements, dashboard render < 3s per NFR-9) — **not** as speculative gold-plating on a single-user local MVP.

### OWASP-Aligned Security Standards
- **A01 Broken Access Control (IDOR):** every user-scoped query carries an explicit `user_id` filter, including joins/subqueries and "reference-like" tables like `merchant_rules` (AD-4 + Agent-Misread Guard). A dedicated cross-user test must pass.
- **A03 Injection:** parameterized SQL only (above); the **category enum** blocks LLM-invented categories (AD-7); DB-sourced text is **untrusted input** to LLM prompts — delimited, never instruction (AD-10 + Guard). This is the app's prompt-injection defense.
- **A02/A07 Auth & Session:** session token in an **httpOnly, SameSite cookie** only, never readable by JS or placed in a URL (AD-5 + Guard).
- **A05 Misconfiguration / A04 Secrets:** `ANTHROPIC_API_KEY` and all secrets in git-ignored `.env` via python-dotenv; no secret in source or commits.
- **A09 Logging:** log unexpected exceptions with context, but **never log secrets, tokens, or full statement contents.**

### Code Review Checklist (before merge)
- [ ] Build/app starts; `pytest services/engine/` green with zero LLM calls.
- [ ] All tests pass; new code has unit + relevant integration/validation coverage.
- [ ] No linter/type errors (ruff / mypy if configured); no unused imports or dead/commented-out code.
- [ ] No duplicated logic (DRY); names are honest.
- [ ] **Security:** `user_id` scoping present; inputs validated (Pydantic); no string-built SQL; untrusted text delimited before any LLM prompt.
- [ ] **Error handling** implemented — typed exceptions, nothing swallowed, user-facing messages plain.
- [ ] **Logging** added for unexpected failures (no secrets logged).
- [ ] Performance reviewed (pagination / async / no N+1) where it applies.
- [ ] **Schema/model change reviewed** (sqlmodel table or canonical `Transaction` schema edits ripple to parsers, engine, and charts — see enum 3-touch Guard).
- [ ] Currency/date rendering goes through `formatINR`/`formatDate` (incl. charts).
- [ ] Documentation / this `project-context.md` updated if a new cross-cutting rule emerged.

---

## Usage Guidelines

**For AI Agents:**
- Read this file **before** implementing any code. When it and the code disagree, this file's cited AD wins — cross-check `ARCHITECTURE-SPINE.md`.
- Follow ALL rules exactly. When a rule is ambiguous, prefer the **more restrictive** interpretation (e.g. add the `user_id` filter, use `Decimal`, delimit LLM input).
- The **Seams** and **Agent-Misread Guards** subsections are where compliant-looking code still fails — treat them as first-class, not footnotes.
- The non-negotiable quality gate before any engine work is considered done: `pytest services/engine/` green, with zero LLM calls.

**For Humans:**
- Keep this file lean and agent-facing. Update it when the stack changes or a new cross-cutting rule emerges from a build mistake.
- It is a projection of `ARCHITECTURE-SPINE.md` (AD-1 → AD-14) plus review-surfaced seams — keep the two in sync; the spine is the source of truth for the ADs.
- Review after each epic; delete rules that become obvious or are enforced by tooling (import-linter, structured output, etc.).

_Last Updated: 2026-07-08_
