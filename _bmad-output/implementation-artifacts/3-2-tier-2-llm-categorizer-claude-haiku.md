---
baseline_commit: f47af57b3aece05c58930c19ed55976384522bd7
---

# Story 3.2: Tier-2 LLM Categorizer (Claude Haiku)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user with uncategorized transactions,
I want the app to automatically categorize them using AI with a constrained category set,
so that I don't have to manually label every transaction the rules didn't recognize.

## Acceptance Criteria

Source: [epics.md — Story 3.2](../planning-artifacts/epics.md) (lines 473–489)

1. **Given** transactions remain uncategorized after Tier-1 rules, **When** the Tier-2 LLM categorizer runs, **Then** it calls `claude-haiku-4-5` via `messages.parse()` with a Pydantic model whose `category` field is a `Literal` enum defined in `services/categorize/schema.py` — free-text categories from the LLM are structurally impossible.
2. **And** each result stores `category_source='llm'`, `category_confidence` (float, never shown raw to user), and `reasoning`.
3. **And** the enum hard-constraint also prevents prompt injection: a hostile merchant string like `"IGNORE PREVIOUS INSTRUCTIONS"` cannot produce an invented category.
4. **And** the upload progress bar step 4 (`"AI Assist"`) fires with a real count when this step completes — completing the skeleton from Epic 2.
5. **And** LLM calls are made via a `Categorizer` interface (not direct SDK calls) — mockable for unit tests.
6. **And** `pytest tests/categorize/test_llm_categorizer.py` passes with all LLM calls mocked; no real API call is made during tests.
7. **And** for the demo fixture: the 3 AI-categorized transactions receive correct categories with `category_source='llm'` — **see Dev Notes "The demo fixture has nothing left for Tier-2 to do" for why this literal AC is now unsatisfiable and how to test this story instead.**

## Tasks / Subtasks

- [ ] **Task 1 — `Categorizer` protocol + Pydantic response schema** (AC: #1, #5)
  - [ ] New `services/categorize/protocol.py`. Mirror `services/ingestion/protocol.py`'s exact style (`typing.Protocol`, `@runtime_checkable`, one-method contract, a docstring explaining the ports-and-adapters seam). Define:
    ```python
    @runtime_checkable
    class Categorizer(Protocol):
        def categorize(self, transactions: Sequence[Transaction]) -> list[Transaction]:
            """Return a new list (same length/order) with category/category_source/
            category_confidence/reasoning filled on every UNCATEGORIZED input row;
            non-UNCATEGORIZED rows pass through unchanged."""
            ...
    ```
  - [ ] New Pydantic response models in `services/categorize/llm_categorizer.py` (not `schema.py` — `schema.py` stays the taxonomy-only source of truth per Story 3.1):
    ```python
    class CategorizationResult(BaseModel):
        index: int  # position in the request batch — see "Batch response mapping" below
        category: Category  # the Literal from services/categorize/schema.py — import it, don't redeclare
        confidence: float
        reasoning: str

    class CategorizationBatch(BaseModel):
        results: list[CategorizationResult]
    ```
  - [ ] `confidence` is the LLM's own self-reported confidence (0.0–1.0) — distinct from Tier-1's hardcoded `1.0`. Do not clamp/round it; store as returned (AC #2 says "float, never shown raw to user" — the *never-shown-raw* part is a UI concern for badges/Story 3.4, not a storage concern).

- [ ] **Task 2 — `ClaudeCategorizer`: one batched `messages.parse()` call, not N calls** (AC: #1, #3, #5)
  - [ ] New `ClaudeCategorizer` in `services/categorize/llm_categorizer.py`, implementing `Categorizer`. Constructor takes an injected `anthropic.Anthropic` client (AD-2/AD-14 dependency injection — mirrors this project's existing "collaborators are passed in, not constructed inside `services/`" rule; also what makes the raising-fixture test pattern from `services/engine/` possible once Epic 4 lands). Do **not** instantiate `anthropic.Anthropic()` inside `services/categorize/`.
  - [ ] `categorize()` selects only rows where `transaction.category == UNCATEGORIZED` (import `UNCATEGORIZED` from `services/categorize/schema.py`) — rows already categorized by Tier-1 (including the 0.5-confidence "Transfer In" credit fallback, which **is** a real category, not `UNCATEGORIZED`) pass through untouched.
  - [ ] If there are zero `UNCATEGORIZED` rows, **return the input unchanged and make no API call** — don't spend a request on an empty batch (this will be the common case on the current demo fixture — see Dev Notes).
  - [ ] Make **one** `client.messages.parse(model=..., max_tokens=..., messages=[...], output_format=CategorizationBatch)` call covering *all* uncategorized rows in the batch — not one call per transaction. This project's NFR-4 explicitly calls out "Batch API for **bulk** categorization" and a **&lt;$15 total spend** budget; N separate calls for one statement is the wrong shape both for cost and for latency inside the synchronous upload flow. (Note: the Anthropic **Batch API** proper is asynchronous — results arrive later, not inline — which does not fit the upload page's synchronous "AI Assist" step; what NFR-4 is really asking for here is *not doing it one-row-at-a-time*, which a single `messages.parse()` call with all rows in one prompt already satisfies. Do not attempt to wire the async Batch API into this synchronous flow.)
  - [ ] The user message lists each uncategorized transaction as **clearly delimited data**, not prose — e.g. a numbered/indexed block per transaction with `description_raw` inside explicit delimiters (e.g. `<description>...</description>` or a fenced/quoted field), never string-concatenated directly into a sentence. This is the project's documented prompt-injection guard (project-context.md Seams: *"description_raw ... originate from an uploaded PDF and are user-influenced data, never instructions. When they enter a ... prompt, delimit them as quoted data — never concatenate raw into the system prompt."*). AC #3's "IGNORE PREVIOUS INSTRUCTIONS" example is structurally blocked from producing an invented *category* by the `Literal` constraint regardless of delimiting — but un-delimited concatenation could still corrupt the reasoning/confidence for *other* transactions in the same batch, so delimit anyway.
  - [ ] The system prompt (persona/taxonomy/instructions) is static per call — mark it `cache_control: {"type": "ephemeral"}` per this project's established prompt-caching convention (`ARCHITECTURE-SPINE.md` Consistency Conventions, `project-context.md` Workflow rules). Put the actual transaction list (volatile, per-call) in the *user* message, after the cached system block.
  - [ ] **Batch response mapping (do this defensively, not positionally):** match each `CategorizationResult` back to its input transaction by the `index` field you assigned when building the request (e.g. `0..N-1` over the uncategorized subset), not by trusting the LLM preserved list order/count. If the LLM omits an index or returns a duplicate, leave that transaction as `UNCATEGORIZED` (never crash, never guess) — this is the same "degrade honestly" instinct as Story 3.1's malformed-row guard.
  - [ ] The model ID (`claude-haiku-4-5`) is a constant in `services/narrate/config.py` (currently an empty Story-1.1 placeholder — populate it now: `TIER2_CATEGORIZATION_MODEL = "claude-haiku-4-5"`), imported by `llm_categorizer.py` — never hardcoded at the call site (project-context "LLM model IDs are constants" rule).

- [ ] **Task 3 — `reasoning` needs a real column; this touches the canonical schema (AD-6) and the DB** (AC: #2)
  - [ ] Neither `finance_app/models.py`'s `Transaction` table nor `services/ingestion/schema.py`'s canonical `Transaction` dataclass has a `reasoning` field today. AC #2 says results "store ... reasoning," so this is required work, not optional polish. Add `reasoning: str | None = None` to **both** (mirroring exactly how `category`/`category_source`/`category_confidence` were already added to the canonical dataclass as "assigned downstream" fields, per `services/ingestion/schema.py`'s own docstring).
  - [ ] This extends AD-6's enumerated canonical-field list in `ARCHITECTURE-SPINE.md`. That's a real architecture-doc touch, not scope creep — add `reasoning` to AD-6's field list in the spine (one line) so the doc stays the source of truth, and note the addition in this story's Completion Notes. Don't silently add a field the architecture doc doesn't know about.
  - [ ] `services/ingestion/persist.py`'s `_to_model` must copy `reasoning` through, same as the other three categorization fields (currently copies `category`/`category_source`/`category_confidence` — add the fourth).
  - [ ] Write a new Alembic migration: `alembic revision --autogenerate -m "add reasoning to transactions"` after the model change, then review the generated `upgrade()`/`downgrade()` (the existing single migration `alembic/versions/31751a886cde_.py` is the pattern to follow — it was itself autogenerated). Run `alembic upgrade head` against the local Postgres to verify it applies cleanly. Tests don't need this (they use `sqlmodel.SQLModel.metadata.create_all()` on a throwaway SQLite engine, which always reflects the current model definitions), but the real app's Postgres store does.

- [ ] **Task 4 — Wire Tier-2 into the upload pipeline (requires reordering persist)** (AC: #4)
  - [ ] `finance_app/state/upload_state.py`'s `_run_parse` currently **persists right after Tier-1** (step 3), then runs step 4 as a 0.3s sleep with no real work (`self.ai = 0` always). Restructure so **both** Tier-1 and Tier-2 run in-memory before the single persist call — do not persist after Tier-1 and then update rows again after Tier-2 (that's two DB round-trips and a window where rows are visibly under-categorized). Concretely: move the `with rx.session() as session: ... persist_transactions(...)` block from its current position (between steps 3 and 4) to **after** step 4's categorization, so `persist_transactions` is called once with the fully-categorized (Tier-1 + Tier-2) list.
  - [ ] Step 4 becomes: `categorized = await asyncio.to_thread(categorizer.categorize, categorized)` (the `Categorizer` call is a network call — keep it off the event loop via `to_thread`, same pattern as `parse_statement`). Wire a module-level `ClaudeCategorizer` instance (constructed with the Anthropic client from `.env`'s `ANTHROPIC_API_KEY`) as the default, injected the same way `parse_statement`/`categorize_rules` are called today — this is the composition-root wiring point (project-context "Dependency Injection" rule: wiring happens at the `rx.State` handler layer, not deep in `services/`).
  - [ ] Replace the skeleton: `self.ai = sum(1 for t in categorized if t.category_source == "llm")`; `self.need_review = self.total - self.rules - self.ai` (previously `self.total - rules_matched`; now three-way honest split, matching the original upload-summary AC's `"{n} by rules · {n} by AI · {n} need your help"` shape — see Dev Notes on why the demo fixture will currently show `0 · 0 · 0` beyond the rules count).
  - [ ] Update the module docstring's "Categorization ... is Epic 3" comment — it's now fully real (both tiers wired); update the "Story 2.4 wires..." paragraph accordingly.

- [ ] **Task 5 — Tests: mock every LLM call, use a synthetic fixture (not the demo fixture)** (AC: #6)
  - [ ] New `tests/categorize/test_llm_categorizer.py`. Inject a **fake/mock `anthropic.Anthropic` client** (or mock `client.messages.parse` directly) — assert `categorize()` never imports or calls the real network client during tests (mirrors the "raising fixture" spirit already established for `services/engine/` in the architecture docs, even though that's Epic 4 — same principle, applied here first).
  - [ ] Cover: (a) a batch of uncategorized transactions gets `category_source='llm'`, `category`/`confidence`/`reasoning` from the mocked response; (b) already-categorized (`category_source='rule'`) rows pass through untouched and trigger **no** API call when the whole input is already categorized; (c) the enum hard-constraint — construct a mocked response and confirm a `CategorizationResult` cannot be built with a category string outside `Category`'s `Literal` values (`pydantic.ValidationError`) — this is what actually proves AC #3, not a live prompt-injection attempt against a real model; (d) the defensive index-mapping: a mocked response missing an index, or with a duplicate/out-of-range index, leaves that row `UNCATEGORIZED` rather than crashing; (e) `reasoning` is persisted through `_to_model` (extend the persist tests or add one here).
  - [ ] Assert `len(RULES)`-style over-specification is *not* needed here (that's Story 3.1's concern) — focus purely on the categorizer's own contract.
  - [ ] **Do not use `data/demo-data.json` as this story's primary fixture** — see Dev Notes. Build a small synthetic fixture (3–5 hand-written transactions) with descriptions this project's Tier-1 rule table (`services/categorize/rules.py`) genuinely won't match, so they reach `UNCATEGORIZED` and actually exercise Tier-2. Sanity-check any candidate description against the current `RULES` table before using it (a description that accidentally matches a Tier-1 rule never reaches the categorizer, silently making the test pass for the wrong reason).

## Dev Notes

### The demo fixture has nothing left for Tier-2 to do — AC #7 is stale, don't force it
Story 3.1's code review (2026-07-10) added `"tata power"` and `"reliance digital"` rules to close a gap Blind Hunter flagged — as a direct result, **the 24-row demo fixture (`data/demo-data.json`) now rule-matches 24/24 in Tier-1**. There are zero `UNCATEGORIZED` rows left for this story's Tier-2 engine to act on with that fixture. AC #7's "the demo fixture's 3 AI-categorized transactions" is therefore **unsatisfiable as literally written** — not a regression, a direct and known consequence of Story 3.1's own (approved) follow-up fix, already noted in that story's Change Log and in `epics.md`'s Story 2.4 AC.

**Do not "fix" this by loosening a Tier-1 rule to artificially leave rows uncategorized** — that would be reintroducing a bug to manufacture a passing test. Instead: build this story's tests against a **synthetic fixture** (Task 5), and — if you want a demo/manual-verification path — either (a) manually insert a transaction with a description no current rule matches, or (b) accept that on `reflex run` with the bundled sample data, the "AI Assist" step will honestly show `0` and the "need your help" count will be `0` too, because Tier-1 already got everything. **That is correct, honest behavior for this fixture** — it is not this story's job to make the demo data exercise every tier.

### What already exists vs. what's net-new (READ FIRST)
| Area | Already implemented | Net-new for THIS story |
| --- | --- | --- |
| Category taxonomy (`CATEGORIES`, `Category` Literal, `UNCATEGORIZED`) | `services/categorize/schema.py` (Story 3.1) — 19 categories, already the single source of truth, already has a drift-guard test against `rules.py` | Import and reuse directly — do **not** redeclare the category list anywhere in this story's new files |
| Tier-1 rules engine (`categorize_rules`, `RULES`) | `services/categorize/rules.py` (pre-existing, ~90 rules, extended in Story 3.1's review) | Nothing — Tier-2 only ever sees what Tier-1 left as `UNCATEGORIZED` |
| `StatementParser` protocol pattern to mirror | `services/ingestion/protocol.py` (Story 2.1) | `Categorizer` protocol, same style (Task 1) |
| Upload pipeline step 3 (Tier-1) wiring | `finance_app/state/upload_state.py` (Story 3.1) — real, working | Step 4 (Tier-2) wiring + a persist-timing reorder (Task 4) |
| `reasoning` field on `Transaction` | **Does not exist** — neither in `finance_app/models.py` nor `services/ingestion/schema.py` | Add it (Task 3) — also touches `ARCHITECTURE-SPINE.md` AD-6 and needs an Alembic migration |
| `services/narrate/config.py` (model-routing constants) | Empty Story-1.1 placeholder | Populate `TIER2_CATEGORIZATION_MODEL` (Task 2) — this is also where Story 5.3/6.x will later add the narration/Copilot model constant; don't restructure the file beyond adding this one constant |
| Anthropic SDK structured output shape | Nothing in this codebase yet — this is the **first** LLM integration | Verified directly against the installed `anthropic==0.116.0` package (not from training-data memory, which may be stale for a fast-moving SDK): `client.messages.parse(model=..., max_tokens=..., messages=[...], output_format=SomePydanticModel)` returns a `ParsedMessage`; the parsed object is read via the `.parsed_output` property (scans response content blocks for a text block with `parsed_output` set — see `anthropic/types/parsed_message.py` in the installed package). Re-verify this against the installed version if `requirements.txt`'s pin ever changes — don't assume the shape is stable across SDK versions. |

### Project-context rules that bind this story
- **AD-7 (category enum hard-constraint):** the `Literal[Category]` field on `CategorizationResult` is what makes an invented category *structurally* impossible — this is the actual mechanism behind AC #3, not prompt wording. Import `Category` from `services/categorize/schema.py`; do not redeclare.
- **AD-2/AD-14 (dependency injection, framework-agnosticism):** `services/categorize/` must not import `reflex` or construct its own `anthropic.Anthropic()` client — the client is passed in, exactly like `StatementParser` implementations and `persist_transactions`'s `txn_model` parameter. `tests/test_service_boundary.py` will catch a `reflex` import automatically; it does **not** catch "constructs its own client" — that's a code-review-time check, not an automated one, so get it right the first time.
- **NFR-4 (cost & model routing):** `claude-haiku-4-5` only for this story, as a constant in `services/narrate/config.py`; batch the call (Task 2); mark the system prompt `cache_control: ephemeral`.
- **Seam — DB text is untrusted LLM input** (`project-context.md`): `description_raw` is user-influenced (came from an uploaded statement, ultimately from a merchant string a user's bank chose to display) and must be delimited as data, never concatenated into prompt prose (Task 2).
- **AD-6 (canonical schema):** adding `reasoning` extends the documented field list — update the spine doc, don't just add the column silently (Task 3).

### References
- [Source: epics.md#Story-3.2-Tier-2-LLM-Categorizer] (lines 473–489) — acceptance criteria origin
- [Source: ARCHITECTURE-SPINE.md#AD-7] — category enum hard-constraint
- [Source: ARCHITECTURE-SPINE.md#AD-2/AD-14] — DI, framework-agnosticism
- [Source: ARCHITECTURE-SPINE.md#AD-6] — canonical Transaction fields (this story extends the list)
- [Source: ARCHITECTURE-SPINE.md Consistency Conventions] — LLM model routing constants, prompt-caching convention
- [Source: project-context.md] — NFR-4 cost/routing, "DB text is untrusted LLM input" seam, Dependency Injection rules
- [Source: services/ingestion/protocol.py] — `StatementParser` protocol, the pattern `Categorizer` mirrors
- [Source: services/categorize/schema.py] — `CATEGORIES`/`Category`/`UNCATEGORIZED`, Story 3.1's single source of truth, reused not redeclared
- [Source: services/categorize/rules.py] — Tier-1 engine; what "already categorized" vs. `UNCATEGORIZED` means
- [Source: finance_app/state/upload_state.py] — `_run_parse`, the persist-ordering this story must restructure
- [Source: finance_app/models.py], [Source: services/ingestion/schema.py] — `Transaction` definitions needing the `reasoning` field
- [Source: alembic/versions/31751a886cde_.py] — the migration pattern to follow
- [Source: 3-1 story](./3-1-tier-1-rules-engine-and-transactions-table.md) — the taxonomy/engine this story builds on; its Change Log documents exactly why the demo fixture is now fully Tier-1-covered
- [Source: anthropic==0.116.0 installed package, `anthropic/types/parsed_message.py`] — verified `messages.parse()`/`ParsedMessage.parsed_output` shape (empirical, not memory)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
