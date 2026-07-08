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
| **Auth flow** | Register auto-authenticated (01.2 was an auto-login transition) | **Login-first**: `index.html`→Login; register → success → *Return to Login* (no auto-login); manual login → Upload | Requested rework — matches a standard secure flow |
| **Auth backend** | httpOnly cookie + server DB | **Simulated** in `shared/auth.js`: `localStorage` "DB" (`afc_users`), `sessionStorage` "session" (`afc_session`, 60-min TTL), server-side validation mocked with latency; passwords in plaintext (demo only) | No backend in the prototype |
| **Route protection** | Server session / middleware | Inline `<head>` guard on every protected page + `Auth.requireAuth()`; unauthenticated/direct-URL access → Login | Client-side simulation of access control |
| **Statement file validation** | Server-side type/size/parse | Client-side **extension + MIME + empty + size (10 MB) + content-sniff** (PDF `%PDF-` header, CSV text/columns) + a simulated server-validate pass; PDF **and CSV** accepted | Section-2 requirement; server must re-validate |

## Known cosmetic gap (open)

- **Dashboard briefing vs hero after adding a commitment:** the hero Safe-to-Spend updates live (e.g. ₹2,840 → ₹1,840), but the **morning briefing narration** still cites the original ₹2,840. Defensible (briefing = morning snapshot; hero = live), but flagged for a decision. Fix = string-replace the figure in the briefing on commitment add, or regenerate the narration server-side in production.

## Faithful to spec (verify these in acceptance testing)

- Honesty layer on every screen (freshness caveats, confidence-as-chip, "Why?", transparent parse, exact-data evidence, Copilot data-trace + uncertainty, observation tone, "information not advice").
- All Object IDs from the specs are present on their elements (e.g. `dashboard-hero-today-amount`, `txn-list-row-{id}`, `insights-card-{n}-observation`, `copilot-thread-copilot-msg-{n}-trace`).
- Confidence is **never** rendered as a raw number.
- Copilot never invents figures — the answer engine only cites values from `demo-data.json`, with an honest "not enough data" fallback.

## For production development

- **Data contract:** `data/demo-data.json` mirrors the shape the real APIs should return (`safe_to_spend`, `confidence`, `spending_by_category`, `commitments`, `transactions`, `insights`, `copilot_samples`). Use it as the reference payload.
- **APIs to implement** (from the specs + auth rework):
  - `POST /auth/register` (unique-email + password policy, **no session on success**), `POST /auth/login` (credential check → session cookie), `POST /auth/logout`, `POST /auth/forgot-password` (email a signed reset link) + `POST /auth/reset-password`, `GET /auth/session`.
  - `POST /statements/upload` — **re-validate server-side**: allowed types PDF/CSV, size cap, empty/corrupt detection, MIME sniffing, reject malicious uploads; then parse (SSE/poll status). Return friendly errors for unsupported-format / parse-failure / server errors.
  - `GET /statements/{id}/transactions`, `PATCH /transactions/{id}/categorise`, `GET /dashboard`, `GET /insights`, `POST /copilot/chat` (SSE).
- **Auth security (production):** hash passwords (bcrypt/argon2), httpOnly+Secure+SameSite session cookies, server-enforced route auth (middleware), rate-limit login/reset, generic "incorrect email or password" to avoid user enumeration, signed time-limited reset tokens. The prototype's `auth.js` mirrors the *shape* of these calls but enforces nothing securely.
- **Honesty constraints are load-bearing**, not cosmetic — enforce the observation-framing + no-invented-numbers + information-not-advice rules in the LLM system prompts (Insights generation, Copilot, briefing text).
- **Safe-to-Spend + Confidence** must be computed by deterministic engines server-side (see Step 12 technical research), with the LLM only narrating.

## Open questions carried from the specs

Data-latency display, Confidence cold-start behavior, multi-bank gap, salary-not-detected fallback, current-vs-last-month chart comparison — see each page spec's "Open Questions" and the design log Backlog.
