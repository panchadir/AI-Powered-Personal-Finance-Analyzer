# Scenario 01 + 02 Prototype — Priya's First Honest Morning & Priya Protects What Matters

Interactive, **branded**, **desktop-web** prototype of the AI Financial Copilot (Scenario 01 golden path + Scenario 02 Commitments Management), built in WDS Phase 5 (Agentic Development → Prototyping). No backend — everything runs off a local demo dataset.

**Desktop-only (Phase 1 MVP):** PRD open item X1 is resolved — this is a localhost, single-user desktop web app (1280px+ baseline). Mobile/responsive layout is an optional future-phase concern, not committed Phase-1 scope. See `_bmad-output/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md`.

---

## Run it

```bash
cd prototypes/01-priyas-first-honest-morning-Prototype
python -m http.server 8000
# open http://localhost:8000/          (index.html → redirects to the Login page)
```

> Pages should be served over **http** (they `fetch` `data/demo-data.json`). If you open a page directly from disk (`file://`) instead, that fetch is blocked by the browser and `shared/data.js` **automatically falls back to an embedded copy of the same dataset** (2026-07-09) — every page still shows full data either way, just prefer a local server for the real fetch path.
> Live Server (VS Code) on port 5500 also works: open the folder root (`…/01-priyas-first-honest-morning-Prototype/`).

**App entry point:** `index.html` → **Login** (the app always starts at Login).

**Existing-user path:** Login → Upload → **Dashboard** (default landing page after upload, changed 2026-07-09) → Transactions (via "View All Transactions") → Insights → Copilot. The four sidebar screens (Dashboard, Transactions, Insights, Copilot) are freely reachable from one another at any time via the persistent left sidebar; Commitments is reached via the Dashboard's "+ Add a commitment" button, not the sidebar (reverted 2026-07-09).
**New-user path:** Login → *Register User* → Register → *Registration successful* → *Return to Login* → Login → Upload → …

**Demo account (seeded):** email **`priya@example.com`**, password **`priya123`**.
Register any new unique email + 8-char password to create another account (stored in `localStorage`). A second registration of the same email is rejected as a duplicate.
Upload validation test hooks: name a file `unsupported.*` / `servererror.*` / `network.*` / `parsefail.*` to exercise those error paths.

---

## The 8 screens

| # | File | What it shows |
|---|------|---------------|
| — | `index.html` | App entry — redirects to Login |
| 01.2 | `01.2-login.html` | **Login landing page** — email/password auth, "Register User", "Forgot password?" (reset modal), redirects authed users to Upload |
| 01.1 | `01.1-register.html` | Registration form, client + server validation, unique-email check, **"Registration successful → Return to Login"** (no auto-login) |
| 01.3 | `01.3-statement-upload.html` | **PDF/CSV validation** (type/MIME/size/empty/corrupted + server checks) with friendly errors; transparent parse progress — "18 by rules · 3 by AI · **3 need your help**"; completes to **"Go to my Dashboard →"** (changed 2026-07-09, was "Review my transactions") |
| 01.5 | `01.5-dashboard.html` | **Default landing page immediately after upload** (changed 2026-07-09, was Transactions). Safe-to-Spend hero, confidence chip + **Confidence Score Drill-In panel**, "Why?" expander, and a **responsive below-fold card grid** (Morning Briefing, **"View All Transactions" CTA**, donut chart, commitments timeline) that fills the window on wider screens instead of stacking in one narrow column |
| 01.4 | `01.4-transactions-table.html` | Reached from the Dashboard's "View All Transactions" CTA or the sidebar (no longer the automatic post-upload page). 24 transactions, wrapping filter chips, inline **Teach Me** correction, Dashboard CTA |
| 01.6 | `01.6-ai-insights-recommendations.html` | Observation→Evidence→Explanation→Action insight cards, dismiss, Ask-Copilot handoff |
| 01.7 | `01.7-copilot-chat.html` | Simulated token streaming, data-trace chips, honesty contract, pre-populated context |
| 02.1 | `02.1-commitments-management.html` | **Commitments Management** (Scenario 02, P1 — still committed scope, just not a sidebar item, see below) — impact bar ("Protecting ₹X" / "Safe to spend ₹Y"), commitment list, Add/Edit modal, delete confirm — all changes update Safe-to-Spend everywhere |

Pre-app onboarding screens (Register / Login / Upload) have **no nav**. The four sidebar screens (Dashboard / Transactions / Insights / Copilot) share a **persistent left sidebar navigation** — desktop-only, always the full 208px labeled rail:
**Dashboard · Transactions · Insights · Copilot Chat**.

**Commitments is not a sidebar item** (reverted 2026-07-09, matches `epics.md` FR-6.4's 4-screen nav exactly) — reach it via the **"+ Add a commitment"** link in the Dashboard's Upcoming Commitments card. `02.1-commitments-management.html` still renders the same 4-item sidebar (for "Log out" and quick navigation elsewhere) but with no item marked active, since it isn't one of the 4 primary destinations.

---

## Structure

```
01-priyas-first-honest-morning-Prototype/
├── README.md                 ← you are here
├── HANDOFF.md                ← how the prototype extends/diverges from the specs (read before dev)
├── PROTOTYPE-ROADMAP.md      ← setup decisions + build status
├── index.html                ← app entry → redirects to Login
├── 01.1 … 01.7 *.html        ← Scenario 01, the 7 golden-path pages
├── 02.1-commitments-management.html  ← Scenario 02, Commitments Management
├── data/demo-data.json       ← single source of truth (Priya dataset)
├── shared/
│   ├── styles.css            ← branded theme — retheme everything from :root tokens
│   ├── auth.js               ← MOCK auth backend + session/route guards (see Authentication)
│   ├── format.js             ← formatINR(), formatDate()
│   ├── data.js               ← loadDemoData() — fetches demo-data.json, falls back to an embedded copy if that fails
│   ├── commitments.js        ← shared, persisted commitment state (Dashboard ⇄ Commitments page)
│   └── nav.js                ← renderSideNav() (+ Logout) + routing
├── work/                     ← Logical-View-Map.md, Register-Work.yaml
├── stories/                  ← per-section build stories
└── assets/                   ← verification screenshots
```

---

## Design

- **Fidelity:** started Gray Model, upgraded to a **branded theme** — calm **teal** fintech identity (`--primary #10796b`), warm accents, elevated cards, pill buttons, designed donut palette. All theming lives in the `:root` tokens in `shared/styles.css`; change the palette there to reskin the whole prototype.
- **Desktop-only, fluid layout (updated 2026-07-09):** designed and verified across 1366×768, 1440×900, and 1920×1080+. No mobile breakpoints, and no fixed-width content column either — `.dash`/`.page--flow.has-sidenav` fill the available window (capped at 1680px so ultra-wide monitors don't over-stretch text) instead of sitting in a narrow centered column. The Dashboard and Insights below-fold content render as a **CSS Grid card layout** (`auto-fit`, no manual breakpoints) that adds columns as the window widens and collapses to one column if it narrows — see `dash-grid`/`insights-list` in `shared/styles.css`.
- **Dependency-free:** no CDN/Tailwind/external fonts — self-contained, works offline once served.

## The honesty layer (the product's moat — realized in the UI, not just specified)

- Data **freshness caveats** wherever a number appears ("Based on your statement from 30 Jun 2026")
- Confidence shown **only as a labelled chip** (Well prepared / On track / Watch this), never a raw number — tapping it opens a **Confidence Score Drill-In panel** (epics.md Story 5.2) tracing every point change to a real `score_events` row (delta + explanation + time elapsed)
- **"Why?"** reasoning derived from real demo data
- **Transparent parse** breakdown (rules vs AI vs needs-help)
- Insight **evidence blocks** use exact data (amounts, dates, merchants)
- Copilot answers carry **data-trace chips** and disclose uncertainty ("one month of data → Medium")
- **Observation, never judgment**; **"information not advice"** framing (SEBI boundary)

---

## Authentication & access control (simulated)

`shared/auth.js` **simulates a backend** so the whole flow is clickable with no server:
- **"Database"** = `localStorage` (`afc_users`); **"session"** = `sessionStorage` (`afc_session`, 60-min TTL); **"server-side validation"** = checks run inside async calls with latency.
- **Login-first:** `index.html` and every protected page route to Login unless a valid session exists.
- **Protected routes:** Upload, Transactions, Dashboard, Insights, Copilot — guarded by an inline `<head>` check (blocks direct-URL access) **and** `Auth.requireAuth()`.
- **Register:** unique-email + server-side validation; on success shows "Return to Login" — **no auto-login**.
- **Forgot password:** reset flow on the Login page (demo sets a new password directly; production would email a signed link).
- **Logout:** in the left-nav footer (app screens) and the Upload header — clears the session and returns to Login.

> ⚠️ Passwords are stored in plain text in `localStorage` for the demo **only**. A real backend must hash them and enforce every rule server-side. See `HANDOFF.md`.

## Verification

Every screen was verified with headless Chrome + DevTools Protocol (functional assertions + screenshots) across all three target desktop resolutions — **1366×768, 1440×900, 1920×1080** — with the new flow (Upload → Dashboard → Transactions) and the fluid grid layout: **zero console errors, zero horizontal overflow** on every page at every resolution. `assets/` holds the current screenshot set (2026-07-09), including `dashboard-wide-1920.png` showing all four below-fold cards filling a single row at 1920px.

## Not in scope (yet)

- **Real backend** — auth/session/validation are simulated client-side (`localStorage`/`sessionStorage`); statement parsing is mocked from `data/demo-data.json`. No real server, hashing, or DB.
- Scenario 03 (Copilot return-visit) — not built
- Mobile/responsive layout — optional future-phase per the resolved PRD X1 decision, not attempted here
- Persistence: commitments persist in `localStorage` (`afc_commitments`) across the Dashboard and Commitments pages within the same browser; registered users persist in `localStorage` per browser
