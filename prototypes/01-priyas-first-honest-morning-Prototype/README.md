# Scenario 01 Prototype — Priya's First Honest Morning

Interactive, responsive, **branded** prototype of the AI Financial Copilot golden path, built in WDS Phase 5 (Agentic Development → Prototyping). No backend — everything runs off a local demo dataset.

---

## Run it

```bash
cd prototypes/01-priyas-first-honest-morning-Prototype
python -m http.server 8000
# open http://localhost:8000/          (index.html → redirects to the Login page)
```

> Pages must be served over **http** (they `fetch` `data/demo-data.json`; `file://` will fail).
> Live Server (VS Code) on port 5500 also works: open the folder root (`…/01-priyas-first-honest-morning-Prototype/`).

**App entry point:** `index.html` → **Login** (the app always starts at Login).

**Existing-user path:** Login → Upload → Transactions → Dashboard → Insights → Copilot.
**New-user path:** Login → *Register User* → Register → *Registration successful* → *Return to Login* → Login → Upload → …

**Demo account (seeded):** email **`priya@example.com`**, password **`priya123`**.
Register any new unique email + 8-char password to create another account (stored in `localStorage`). A second registration of the same email is rejected as a duplicate.
Upload validation test hooks: name a file `unsupported.*` / `servererror.*` / `network.*` / `parsefail.*` to exercise those error paths.

---

## The 7 screens

| # | File | What it shows |
|---|------|---------------|
| — | `index.html` | App entry — redirects to Login |
| 01.2 | `01.2-login.html` | **Login landing page** — email/password auth, "Register User", "Forgot password?" (reset modal), redirects authed users to Upload |
| 01.1 | `01.1-register.html` | Registration form, client + server validation, unique-email check, **"Registration successful → Return to Login"** (no auto-login) |
| 01.3 | `01.3-statement-upload.html` | **PDF/CSV validation** (type/MIME/size/empty/corrupted + server checks) with friendly errors; transparent parse progress — "18 by rules · 3 by AI · **3 need your help**" |
| 01.4 | `01.4-transactions-table.html` | 24 transactions, wrapping filter chips, inline **Teach Me** correction, Dashboard CTA |
| 01.5 | `01.5-dashboard.html` | Safe-to-Spend hero, confidence chip + tooltip, "Why?" expander, donut, commitments + **Add-commitment form** |
| 01.6 | `01.6-ai-insights-recommendations.html` | Observation→Evidence→Explanation→Action insight cards, dismiss, Ask-Copilot handoff |
| 01.7 | `01.7-copilot-chat.html` | Simulated token streaming, data-trace chips, honesty contract, pre-populated context |

Pre-app onboarding screens (Register / Login / Upload) have **no nav**. The four authenticated app screens (Transactions / Dashboard / Insights / Copilot) share a **persistent left navigation**:
**Transactions · Dashboard · Insights · Copilot Chat** (76px icon rail on mobile, 208px labeled sidebar on desktop).

---

## Structure

```
01-priyas-first-honest-morning-Prototype/
├── README.md                 ← you are here
├── HANDOFF.md                ← how the prototype extends/diverges from the specs (read before dev)
├── PROTOTYPE-ROADMAP.md      ← setup decisions + build status
├── index.html                ← app entry → redirects to Login
├── 01.1 … 01.7 *.html        ← the 7 pages
├── data/demo-data.json       ← single source of truth (Priya dataset)
├── shared/
│   ├── styles.css            ← branded theme — retheme everything from :root tokens
│   ├── auth.js               ← MOCK auth backend + session/route guards (see Authentication)
│   ├── format.js             ← formatINR(), formatDate()
│   ├── data.js               ← loadDemoData()
│   └── nav.js                ← renderSideNav() (+ Logout) / renderBottomNav() + routing
├── work/                     ← Logical-View-Map.md, Register-Work.yaml
├── stories/                  ← per-section build stories
└── assets/                   ← verification screenshots
```

---

## Design

- **Fidelity:** started Gray Model, upgraded to a **branded theme** — calm **teal** fintech identity (`--primary #10796b`), warm accents, elevated cards, pill buttons, designed donut palette. All theming lives in the `:root` tokens in `shared/styles.css`; change the palette there to reskin the whole prototype.
- **Responsive:** mobile-first, verified at 390px and 1280px. No horizontal overflow on any screen.
- **Dependency-free:** no CDN/Tailwind/external fonts — self-contained, works offline once served.

## The honesty layer (the product's moat — realized in the UI, not just specified)

- Data **freshness caveats** wherever a number appears ("Based on your statement from 30 Jun 2026")
- Confidence shown **only as a chip** (High/Medium/Low + tooltip), never a raw number
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

Every screen was verified with headless Chrome + DevTools Protocol (functional assertions + screenshots), and the full golden path passes an end-to-end integration test — **zero console errors**, no horizontal overflow. See `assets/` for screenshots.

## Not in scope (yet)

- **Real backend** — auth/session/validation are simulated client-side (`localStorage`/`sessionStorage`); statement parsing is mocked from `data/demo-data.json`. No real server, hashing, or DB.
- Scenario 02 (Commitments Management page) and Scenario 03 (Copilot return-visit) — not built
- Persistence: added commitments live only in the current session (in memory); registered users persist in `localStorage` per browser
