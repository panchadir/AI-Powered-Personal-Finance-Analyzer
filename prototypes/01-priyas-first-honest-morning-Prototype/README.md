# Scenario 01 Prototype — Priya's First Honest Morning

Interactive, responsive, **branded** prototype of the AI Financial Copilot golden path, built in WDS Phase 5 (Agentic Development → Prototyping). No backend — everything runs off a local demo dataset.

---

## Run it

```bash
cd prototypes/01-priyas-first-honest-morning-Prototype
python -m http.server 8000
# open http://localhost:8000/01.1-register.html
```

> Pages must be served over **http** (they `fetch` `data/demo-data.json`; `file://` will fail).
> Live Server (VS Code) on port 5500 also works: `http://127.0.0.1:5500/prototypes/01-priyas-first-honest-morning-Prototype/01.1-register.html`

**Golden path:** Register → Login (auto) → Upload → Transactions → Dashboard → Insights → Copilot.
Demo login shortcuts: on Register, submit any valid email/8+char password (matching confirm). `taken@example.com` triggers the "email already registered" path; `network@example.com` triggers the network-error toast.

---

## The 7 screens

| # | File | What it shows |
|---|------|---------------|
| 01.1 | `01.1-register.html` | Registration form, 7 validation rules, show/hide password, legal modal, auto-auth redirect |
| 01.2 | `01.2-login.html` | Auto-authentication transition ("Account created!") + auto-advance; `?fail=1` = error fallback |
| 01.3 | `01.3-statement-upload.html` | Transparent parse progress — "18 by rules · 3 by AI · **3 need your help**" |
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
├── 01.1 … 01.7 *.html        ← the 7 pages
├── data/demo-data.json       ← single source of truth (Priya dataset)
├── shared/
│   ├── styles.css            ← branded theme — retheme everything from :root tokens
│   ├── format.js             ← formatINR(), formatDate()
│   ├── data.js               ← loadDemoData()
│   └── nav.js                ← renderSideNav() / renderBottomNav() + routing
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

## Verification

Every screen was verified with headless Chrome + DevTools Protocol (functional assertions + screenshots), and the full golden path passes an end-to-end integration test — **zero console errors**, no horizontal overflow. See `assets/` for screenshots.

## Not in scope (yet)

- Real backend / auth / statement parsing (all mocked from `data/demo-data.json`)
- Scenario 02 (Commitments Management page) and Scenario 03 (Copilot return-visit) — not built
- Persistence: added commitments live only in the current session (in memory)
