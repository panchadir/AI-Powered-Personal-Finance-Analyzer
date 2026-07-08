# Prototype Handoff — deltas from the specs

Read this before acceptance testing or production development. The prototype faithfully implements the WDS page specs in `_bmad-output/C-UX-Scenarios/01-priyas-first-honest-morning/`, **with the deliberate decisions and divergences below**. These came from live review with ALPHA during the build.

---

## Deliberate divergences from the page specs

| Area | Spec says | Prototype does | Why |
|------|-----------|----------------|-----|
| **Design fidelity** | Gray Model (no design system) | Branded **teal** theme (color, elevation, chart palette) | ALPHA requested a polished visual design; tokens in `shared/styles.css :root` |
| **App navigation** | Dashboard has a bottom nav; other screens per spec | **Persistent left nav** on all 4 app screens (Transactions/Dashboard/Insights/Copilot) | ALPHA: left menu, consistent across followup screens |
| **Nav item "Commitments"** | Commitments Management is a Scenario-02 destination | Nav item **renamed "Insights"**, points to `01.6` | ALPHA: Commitments page not built; repurpose the slot for Insights |
| **Transactions top bar** | Sticky "Back / See my Dashboard" bar | Removed; replaced by the left nav + a **"See my Dashboard →"** button in the page header | Left nav supersedes the sticky bar; CTA kept per spec's "never trapped in review" intent |
| **Dashboard "+ Add a commitment"** | Links to `/commitments` (Scenario 02) | Opens an **inline modal form** (name / amount / date / criticality) that adds to the timeline and **updates Safe-to-Spend live** | Scenario-02 page not built; realizes that scenario's key "protection payoff" moment on the Dashboard |
| **Parse counts** | Illustrative "214 / 187 / 24 / 3" | Derived from the 24-txn demo array: **24 total, 18 rules, 3 AI, 3 need-help** | Keeps Upload → Transactions internally consistent |
| **Copilot streaming** | SSE token stream from server | Client-side **simulated** word-by-word streaming | No backend in the prototype |
| **Auth / cookie** | Token in httpOnly cookie | `sessionStorage` demo flag | No backend |

## Known cosmetic gap (open)

- **Dashboard briefing vs hero after adding a commitment:** the hero Safe-to-Spend updates live (e.g. ₹2,840 → ₹1,840), but the **morning briefing narration** still cites the original ₹2,840. Defensible (briefing = morning snapshot; hero = live), but flagged for a decision. Fix = string-replace the figure in the briefing on commitment add, or regenerate the narration server-side in production.

## Faithful to spec (verify these in acceptance testing)

- Honesty layer on every screen (freshness caveats, confidence-as-chip, "Why?", transparent parse, exact-data evidence, Copilot data-trace + uncertainty, observation tone, "information not advice").
- All Object IDs from the specs are present on their elements (e.g. `dashboard-hero-today-amount`, `txn-list-row-{id}`, `insights-card-{n}-observation`, `copilot-thread-copilot-msg-{n}-trace`).
- Confidence is **never** rendered as a raw number.
- Copilot never invents figures — the answer engine only cites values from `demo-data.json`, with an honest "not enough data" fallback.

## For production development

- **Data contract:** `data/demo-data.json` mirrors the shape the real APIs should return (`safe_to_spend`, `confidence`, `spending_by_category`, `commitments`, `transactions`, `insights`, `copilot_samples`). Use it as the reference payload.
- **APIs to implement** (from the specs): `POST /auth/register`, `POST /statements/upload` + parse status (SSE/poll), `GET /statements/{id}/transactions`, `PATCH /transactions/{id}/categorise`, `GET /dashboard`, `GET /insights`, `POST /copilot/chat` (SSE).
- **Honesty constraints are load-bearing**, not cosmetic — enforce the observation-framing + no-invented-numbers + information-not-advice rules in the LLM system prompts (Insights generation, Copilot, briefing text).
- **Safe-to-Spend + Confidence** must be computed by deterministic engines server-side (see Step 12 technical research), with the LLM only narrating.

## Open questions carried from the specs

Data-latency display, Confidence cold-start behavior, multi-bank gap, salary-not-detected fallback, current-vs-last-month chart comparison — see each page spec's "Open Questions" and the design log Backlog.
