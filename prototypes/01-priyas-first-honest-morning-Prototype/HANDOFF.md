# Prototype Handoff — deltas from the specs

Read this before acceptance testing or production development. The prototype faithfully implements the UX scenario page specs (Scenarios 01 and 02), **with the deliberate decisions and divergences below**. These came from live review with ALPHA during the build.

**2026-07-09 reconciliation:** the architecture and UX-Scenarios specs were updated to (1) resolve PRD X1 — MVP is **desktop-only** (1280px+, non-responsive; mobile/responsive is optional future-phase) — and (2) promote **Commitments Management (02.1)** from P2 to committed P1 scope, and commit the **Confidence Score Drill-In Panel** (epics.md Story 5.2). The prototype was updated to match: the sidebar is now the desktop-only 208px labeled rail everywhere (no mobile icon-rail variant), the Commitments Management page (`02.1-commitments-management.html`) is built and reachable from the sidebar and the Dashboard, and the Dashboard's confidence chip now opens a Drill-In panel instead of a plain tooltip. Several rows in the table below that were previously "not built" divergences are now resolved and have been removed; the rest still stand.

**2026-07-09 navigation + layout update:** the golden path was re-sequenced — **Dashboard, not the Transactions Table, is now the default landing page immediately after Statement Upload** (`upload-cta-review` retargeted from `/transactions` to `/dashboard`; PRD's golden-path line, `01.3`/`01.4`/`01.5` specs, and `00-ux-scenarios.md` all updated to match). The Dashboard gained a **"View All Transactions" CTA card** (`dashboard-transactions-cta`) as the one-click path to the detail view. Separately, the content layout across all authenticated screens was changed from a fixed narrow column (max 560–760px, regardless of window size) to a **fluid layout that fills the available window** on laptop/desktop resolutions (1366×768–1920×1080+), with the Dashboard and Insights below-fold content laid out as a responsive CSS Grid card layout instead of one stacked column.

**2026-07-09 nav simplification (later same day):** **Commitments was removed from the persistent sidebar**, reverting the 5-item nav from earlier the same day back to the 4 screens `epics.md` FR-6.4 actually specifies (Dashboard/Transactions/Insights/Copilot). Commitments Management is still fully committed P1 scope (unchanged) — it's just no longer a sidebar destination; it's reached solely via the Dashboard's "+ Add a commitment" link, which is how it always worked before the brief 5-item detour. `shared/nav.js`, `01.5-dashboard.md`, and `02.1-commitments-management.md` all updated to match. Also: `shared/data.js` now has an **embedded fallback dataset** — if a page is opened via `file://` (where `fetch()` of the local JSON is blocked) it silently falls back to the same data instead of rendering blank/₹0.

---

## Deliberate divergences from the page specs

| Area | Spec says | Prototype does | Why |
|------|-----------|----------------|-----|
| **Design fidelity** | Gray Model (no design system) | Branded **teal** theme (color, elevation, chart palette) | ALPHA requested a polished visual design; tokens in `shared/styles.css :root` |
| **App navigation** | Sidebar nav per `dashboard-sidebar-nav` / `commitments-sidebar-nav` | **Persistent left sidebar** on all 5 app screens (Dashboard/Transactions/Commitments/Insights/Copilot), desktop-only 208px labeled rail (no mobile icon-rail variant) | Matches the resolved desktop-only architecture decision |
| **Transactions top bar** | Sticky "Back / See my Dashboard" bar | Removed; replaced by the left nav + a **"See my Dashboard →"** button in the page header | Left nav supersedes the sticky bar; CTA kept per spec's "never trapped in review" intent |
| **Commitment persistence** | `/commitments` REST API (GET/POST/PATCH/DELETE) | **Simulated** via `shared/commitments.js`: a shared, `localStorage`-persisted list (`afc_commitments`), read/written by both the Dashboard and the Commitments page, seeded from `demo-data.json`'s base commitments | No backend in the prototype; keeps the "protection payoff" number consistent across pages without a server round-trip |
| **Parse counts** | Illustrative "214 / 187 / 24 / 3" | Derived from the 24-txn demo array: **24 total, 18 rules, 3 AI, 3 need-help** | Keeps Upload → Transactions internally consistent |
| **Copilot streaming** | SSE token stream from server | Client-side **simulated** word-by-word streaming | No backend in the prototype |
| **Auth flow** | Register auto-authenticated (01.2 was an auto-login transition) | **Login-first**: `index.html`→Login; register → success → *Return to Login* (no auto-login); manual login → Upload | Requested rework — matches a standard secure flow |
| **Auth backend** | httpOnly cookie + server DB | **Simulated** in `shared/auth.js`: `localStorage` "DB" (`afc_users`), `sessionStorage` "session" (`afc_session`, 60-min TTL), server-side validation mocked with latency; passwords in plaintext (demo only) | No backend in the prototype |
| **Route protection** | Server session / middleware | Inline `<head>` guard on every protected page + `Auth.requireAuth()`; unauthenticated/direct-URL access → Login | Client-side simulation of access control |
| **Statement file validation** | Server-side type/size/parse | Client-side **extension + MIME + empty + size (10 MB) + content-sniff** (PDF `%PDF-` header, CSV text/columns) + a simulated server-validate pass; PDF **and CSV** accepted | Section-2 requirement; server must re-validate |

## Known cosmetic gap (open)

- **Dashboard briefing vs hero after adding a commitment:** the hero Safe-to-Spend reflects any commitments added on the Commitments page (recomputed on load), but the **morning briefing narration** text still cites the statement-time figure (₹2,840). Defensible (briefing = morning snapshot; hero = live), but flagged for a decision. Fix = string-replace the figure in the briefing on commitment change, or regenerate the narration server-side in production.
- **Cross-tab/live sync (02.1 Open Question #4, still open):** the Dashboard only recomputes Safe-to-Spend on page load, not while a user is idling on it in another tab. Acceptable for a single-user desktop prototype; would need a push mechanism (SSE/WebSocket) in production if this matters.

## Faithful to spec (verify these in acceptance testing)

- Honesty layer on every screen (freshness caveats, confidence-as-chip + Drill-In panel, "Why?", transparent parse, exact-data evidence, Copilot data-trace + uncertainty, observation tone, "information not advice").
- All Object IDs from the specs are present on their elements (e.g. `dashboard-hero-today-amount`, `dashboard-hero-confidence-drillin`, `txn-list-row-{id}`, `insights-card-{n}-observation`, `commitments-list-row-{n}`, `commitments-add-modal`, `copilot-thread-copilot-msg-{n}-trace`).
- Confidence is **never** rendered as a raw number — only the label (Well prepared / On track / Watch this) and, in the Drill-In panel, `score_events` deltas that are themselves explained deltas, not the underlying score.
- Copilot never invents figures — the answer engine only cites values from `demo-data.json`, with an honest "not enough data" fallback.

## For production development

- **Data contract:** `data/demo-data.json` mirrors the shape the real APIs should return (`safe_to_spend`, `confidence`, `score_events`, `spending_by_category`, `commitments`, `transactions`, `insights`, `copilot_samples`). Use it as the reference payload.
- **APIs to implement** (from the specs + auth rework):
  - `POST /auth/register` (unique-email + password policy, **no session on success**), `POST /auth/login` (credential check → session cookie), `POST /auth/logout`, `POST /auth/forgot-password` (email a signed reset link) + `POST /auth/reset-password`, `GET /auth/session`.
  - `POST /statements/upload` — **re-validate server-side**: allowed types PDF/CSV, size cap, empty/corrupt detection, MIME sniffing, reject malicious uploads; then parse (SSE/poll status). Return friendly errors for unsupported-format / parse-failure / server errors.
  - `GET /statements/{id}/transactions`, `PATCH /transactions/{id}/categorise`, `GET /dashboard`, `GET /insights`, `GET /confidence/score-events` (reverse-chronological, for the Drill-In panel), `POST /copilot/chat` (SSE).
  - `GET /commitments`, `POST /commitments`, `PATCH /commitments/{id}`, `DELETE /commitments/{id}` — each mutating call returns the updated `safe_to_spend` so the client never needs a separate dashboard fetch (see 02.1 spec's Data/API section).
- **Auth security (production):** hash passwords (bcrypt/argon2), httpOnly+Secure+SameSite session cookies, server-enforced route auth (middleware), rate-limit login/reset, generic "incorrect email or password" to avoid user enumeration, signed time-limited reset tokens. The prototype's `auth.js` mirrors the *shape* of these calls but enforces nothing securely.
- **Honesty constraints are load-bearing**, not cosmetic — enforce the observation-framing + no-invented-numbers + information-not-advice rules in the LLM system prompts (Insights generation, Copilot, briefing text).
- **Safe-to-Spend + Confidence** must be computed by deterministic engines server-side (see Step 12 technical research), with the LLM only narrating.

## Open questions carried from the specs

Data-latency display, Confidence cold-start behavior, multi-bank gap, salary-not-detected fallback, current-vs-last-month chart comparison — see each page spec's "Open Questions" and the design log Backlog.
