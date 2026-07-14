# LLM (Claude) Flows — Where and How the App Calls the Model

_Reference documentation for every place the app calls the Anthropic (Claude) API — what
triggers it, the full path from start to end, what is sent, and how it degrades._

---

## Governing principle (AD-1)

**The deterministic engine computes every number; the LLM only turns numbers into language
(or picks a label).** No financial figure is ever invented by the model.

- All LLM calls live in exactly **two packages**: `services/categorize/` and `services/narrate/`.
- The money engine (`services/engine/`) makes **zero** LLM calls.
- Model IDs are centralised in **[`services/narrate/config.py`](../services/narrate/config.py)** — never hardcoded at call sites.
- The API key comes from the **`ANTHROPIC_API_KEY`** environment variable (loaded from `.env`).
  When it is absent, narration flows degrade to deterministic fallbacks instead of crashing (NFR-1).

### The four flows at a glance

| # | Flow | Model's job | Model | # of Claude calls | When |
|---|------|-------------|-------|-------------------|------|
| 1 | **Transaction Categorization** | classify unlabelled rows | `claude-haiku-4-5` | 1 batch (only if any `Uncategorized`) | on statement upload |
| 2 | **Dashboard Briefing** | narrate the engine's figures | `claude-opus-4-8` | 1 per Dashboard load | every Dashboard load |
| 3 | **Insights Narration** | narrate an already-detected pattern | `claude-opus-4-8` | 1 per new/changed insight | Insights page load |
| 4 | **Copilot Chat** | answer questions via read-only tools | `claude-opus-4-8` | up to 2 (tool round-trip) | per chat message |

---

## Flow 1 — Transaction Categorization (Tier-1 rules → Tier-2 LLM)

**Trigger:** the user uploads a bank statement (CSV/PDF) on the Upload page.

**Two tiers.** Deterministic rules run first; only what they leave `Uncategorized` goes to Claude.

### Start → end

```
Upload statement
 └─ finance_app/state/upload_state.py
      ├─ :246  categorize_rules(transactions, user_rules)         ── Tier-1 (Python, no LLM)
      │        services/categorize/rules.py
      │          • RULES registry (:40) — Swiggy→Food & Dining, etc.
      │          • user "Teach Me" rules checked BEFORE built-in rules
      │          • unmatched DEBIT  → category = "Uncategorized"   (goes to Tier-2)
      │          • unmatched CREDIT → "Transfer In"               (skips Tier-2)
      │
      └─ :258  _categorizer.categorize(rows)                       ── Tier-2 (Claude)
               services/categorize/llm_categorizer.py
                 ├─ :116  keep ONLY rows where category == "Uncategorized"
                 ├─ :118  if none uncategorized → return (NO Claude call)
                 ├─ :89   build payload = [{index, description}, …]  (description only —
                 │                          no amounts/dates/balances sent)
                 ├─ :122  client.messages.parse(...)  ← CLAUDE CALL  (Haiku, structured output)
                 └─ :144  map results back by index; category is a fixed enum (AD-7)
```

### Key facts
- **One batched call** for all uncategorised rows in an upload (cost control — NFR-4), not one per row.
- **Structured output**: the `category` field is constrained to a fixed enum in
  [`services/categorize/schema.py`](../services/categorize/schema.py) — the model cannot invent a category,
  which also blocks prompt-injection (a hostile merchant string can't forge a bogus category).
- **Only the description text** is sent — never amounts, dates, or balances (privacy + cost).
- **Failure handling** ([`llm_categorizer.py:138`](../services/categorize/llm_categorizer.py#L138)): a network/auth/malformed
  response leaves rows `Uncategorized` — never crashes the upload.
- **Composition root** (where the client is built): [`upload_state.py:49`](../finance_app/state/upload_state.py#L49) — `ClaudeCategorizer(Anthropic())`.

### Debug
Breakpoint at `llm_categorizer.py:116` (the filter) and `:122` (the call) → debug
`tests/categorize/test_llm_categorizer.py` (injects a mock client — no key needed).

---

## Flow 2 — Dashboard Briefing

**Trigger:** the Dashboard page loads (its `on_load`).

The engine computes the figures first; the briefing just phrases them in 2–4 sentences.

### Start → end

```
Open Dashboard
 └─ finance_app/pages/dashboard.py:274   on_load = [check_auth, load_dashboard]
      └─ finance_app/state/dashboard_state.py:248  load_dashboard()
           ├─ compute_dashboard(...)          engine figures (deterministic)
           ├─ :295  build BriefingContext      (already-formatted numbers/strings)
           └─ :302  generate_briefing(context)
                    services/narrate/briefing.py:157  generate_briefing()
                      ├─ :167  if ANTHROPIC_API_KEY unset → build_fallback_briefing()  ── returns here
                      ├─ :91   _facts_block(context)   → "<FACTS> …numbers… </FACTS>"
                      ├─ :178  client.messages.create(...)  ← CLAUDE CALL  (Opus, temp 0)
                      ├─ :196  extract text
                      └─ :203  on any error → build_fallback_briefing()
```

### Key facts
- **Fires on every Dashboard load** — there is no content filter (unlike categorization). Opening the
  Dashboard 5 times = 5 Claude calls. (A future optimisation could cache until the numbers change.)
- **The model may only copy numbers verbatim** from the `<FACTS>` block — the system prompt forbids it
  from deriving/summing/rounding any figure ([`briefing.py:64`](../services/narrate/briefing.py#L64)).
- **Prompt-injection seam**: user-derived text (merchant/insight strings) enters as delimited *data*
  inside the user turn ([`_facts_block`, :91](../services/narrate/briefing.py#L91)), never in the system prompt.
- **Skips the call** when: no API key (`:167`), no data (dashboard returns early), or an error → fallback prose.

### Debug
Breakpoint at `briefing.py:178` (the call) and `:91` (the facts) → debug `tests/narrate/test_briefing.py`.
⚠️ Live: with an empty key it stops at `:167` (fallback) and never reaches `:178`.

---

## Flow 3 — Insights Narration (⚠️ detect first, then narrate)

**Trigger:** the Insights page loads (its `on_load` runs the insights sync).

> **Important:** the LLM does **not** analyse your data or "generate insights." **Deterministic Python
> detectors** find the patterns; Claude is called only to write each detected pattern as a sentence.

### Start → end

```
Open Insights
 └─ Insights page on_load → insights sync   (finance_app/state/insights_bridge.py)
      ├─ load_insight_context(...)                     transactions + commitments → detector input
      │
      ├─ run_all_detectors(context)                    ── DETECT (services/engine/insights/detectors.py)
      │     • pure Python — NO anthropic import anywhere in this package
      │     • finds: post-payday spike, zombie subscriptions, death-by-small-purchases,
      │       weekend-vs-weekday pace, upcoming-commitment collision, commitments-covered
      │
      └─ for each detected candidate:                  ── NARRATE (only when needed)
           ├─ :301  existing insight & materially changed? → generate_insight_narration()
           ├─         unchanged / dismissed-unchanged?      → skip (reuse cached DB narration)
           └─ :329  new insight?                            → generate_insight_narration()
                    services/narrate/insight_narrator.py:429  generate_insight_narration()
                      ├─ :442  if ANTHROPIC_API_KEY unset → fallback narration  ── returns here
                      ├─ :463  _facts_block(input)   ← only the PATTERN's facts/evidence,
                      │                                 NOT the raw transactions
                      ├─ :453  client.messages.create(...)  ← CLAUDE CALL  (Opus)
                      ├─ :468  parse the O→E→E→A response
                      └─ :472  _apply_sebi_guard  → appends "This is not investment advice." if needed
```

### Key facts
- **Detection is 100% deterministic** — proven by the detectors having no `anthropic`/`claude` import.
  The numbers and which patterns exist are decided by code, not the model.
- **Narration is cached in the DB** (the `Insight` row's `observation` etc.). A new Claude call happens
  **only** for a **new** pattern or one whose numbers **materially changed**
  ([`insights_bridge.py:301`](../finance_app/state/insights_bridge.py#L301)) — otherwise the stored text is reused (no call).
- **What is sent to Claude:** the detected pattern's name + evidence points — *not* the raw transactions.
- **SEBI guard** ([`insight_narrator.py:472`](../services/narrate/insight_narrator.py#L472)): regulated-advice phrasing gets a disclaimer;
  the model is also told it may suggest, never prescribe, a financial product.

### Debug
- The call: breakpoint `insight_narrator.py:453` → debug `tests/narrate/test_insight_narrator.py`.
- The detect-vs-cache decision: breakpoint `insights_bridge.py:301` and `:329`.

---

## Flow 4 — Copilot Chat (streaming + read-only tools)

**Trigger:** the user sends a message on the Copilot page. Also: opening the page restores history.

The model can request **read-only tools** to fetch real data, then answers — so it never invents figures.

### Start → end

```
━━ Open Copilot page (restore history) ━━
 finance_app/pages/copilot.py:241  on_load = [check_auth, load_history]
   └─ finance_app/state/copilot_state.py:136  load_history()
        ├─ :167  SELECT * FROM chat_messages WHERE user_id=? ORDER BY timestamp
        └─ :171  → self.messages   (past conversation restored; empty for a new user)

━━ Send a question ━━
 finance_app/state/copilot_state.py:227  send_message()
   ├─ :280  add your bubble to self.messages          (shown instantly)
   ├─ :290  SAVE your turn → chat_messages DB
   ├─ :303  api_messages = [ALL prior turns] + [new question]   ⭐ whole history re-sent
   └─ :315  astream_events(api_messages, data_factory=open_copilot_data)
        services/narrate/copilot.py:112  astream_events()
          ├─ :137  build AsyncAnthropic client
          ├─ ROUND 1  :149  client.messages.stream(system=_SYSTEM, tools=TOOL_SCHEMAS, messages=history)
          │            ← CLAUDE CALL #1     (streams tokens live)
          │      └─ :160  model requested a tool?
          │             └─ YES → :174  run_tool()  → queries the DB (user-scoped) → real numbers
          │                       :186  append tool result → loop
          ├─ ROUND 2  :149  client.messages.stream(… now with tool results …)
          │            ← CLAUDE CALL #2     (streams the final answer)
          ├─ :200  yield trace event   → "Based on: …" source chips
          └─ :212  finally: yield done  (ALWAYS — the browser never hangs)
   ┌── back in send_message(), consuming events:
   ├─ :322  token → streaming_content grows (answer types out live)
   ├─ :341  done  → append the assistant message to self.messages
   └─ :367  SAVE the assistant reply → chat_messages DB
```

### Key facts
- **The model is stateless — the app is the memory.** Every question re-sends the *entire* conversation
  (`api_messages`, [`:303`](../finance_app/state/copilot_state.py#L303)). On the **first** question the history is empty, so `messages`
  is just `[{"role":"user","content": the question}]` — but the **system prompt + tools are always sent**.
- **Two calls per question:** call #1 lets the model pick tools; your code runs them; call #2 answers with
  the results. If the model answers directly (no tool), it's one call.
- **Read-only tools only** ([`services/narrate/tools.py`](../services/narrate/tools.py)): `get_safe_to_spend`,
  `get_confidence_score`, `query_transactions`, `get_spending_by_category`, `get_upcoming_commitments`,
  `get_spending_trend`, … Each is scoped to the user (AD-4); there is **no write tool**.
- **Answers about money come strictly from the DB** via these tools; the 4 hardcoded honesty rules in
  `_SYSTEM` forbid inventing figures and require the trace field.
- **History lives in two places:** the `chat_messages` DB table (persistent, per-user) and `self.messages`
  (in-memory, drives the UI + the request).
- **No pre-check of the key:** unlike flows 2/3, the call at `:149` is attempted even with an empty key —
  it then fails into the error event. A real key is required for a real round-trip.

### Debug
Breakpoints: `copilot_state.py:303` (the assembled history), `copilot.py:149` (the Claude call — hits
**twice**), `copilot.py:174` (tool execution) → debug `tests/narrate/test_copilot_stream.py` (mock client).

---

## Appendix — model routing & fallbacks

| Concern | Where |
|---|---|
| Model IDs (Haiku / Opus / Sonnet cost lever) | [`services/narrate/config.py`](../services/narrate/config.py) |
| Category enum (constrains Tier-2 output) | [`services/categorize/schema.py`](../services/categorize/schema.py) |
| Copilot read-only tools | [`services/narrate/tools.py`](../services/narrate/tools.py) |
| Deterministic fallbacks | `build_fallback_briefing` (briefing.py:127), `build_fallback_insight_narration` (insight_narrator.py) |

**Where the Anthropic client is constructed** (composition roots — services never build their own):
`upload_state.py:49`, `briefing.py:175`, `insight_narrator.py:450`, `copilot.py:137`.

**Debug tests (mock client, no API key needed):**
`tests/categorize/test_llm_categorizer.py`, `tests/narrate/test_briefing.py`,
`tests/narrate/test_insight_narrator.py`, `tests/narrate/test_copilot_stream.py`.
