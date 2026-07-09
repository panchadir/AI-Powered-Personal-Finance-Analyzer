# Prototype Roadmap — Scenario 01: Priya's First Honest Morning (+ Scenario 02: Commitments Management)

**Project:** AI-Powered-Personal-Finance-Analyzer
**Scenario:** 01 — Priya's First Honest Morning (Golden Path, P1) + 02 — Priya Protects What Matters (Commitments Management, P1)
**Created:** 2026-07-08 · **Updated:** 2026-07-09 (desktop-only reconciliation + Scenario 02 build; navigation-flow + fluid-layout update)
**Method:** Whiteport Design Studio (WDS) — Phase 5 Agentic Development / Prototyping

---

## Setup Decisions (Initiation Dialog)

| Question | Answer |
|----------|--------|
| **Device Compatibility** | ~~Desktop + Mobile — Fully Responsive (375px → 1920px)~~ → **Desktop-only** (2026-07-09, architecture decision): PRD open item X1 resolved — Phase 1 MVP is a localhost, single-user desktop web app, 1280px+ baseline, non-responsive. Mobile/responsive is optional/future-phase, not a Phase-1 blocker. The left sidebar is now always the full 208px labeled rail (the mobile 76px icon-rail variant was removed). |
| **Design Fidelity** | Started **Generic Gray Model** (wireframe), then **upgraded to a branded visual theme** (2026-07-08, user request): a calm teal fintech identity with warm accents, elevated cards, pill buttons, and a designed chart palette. All pages retheme from the `:root` tokens in `shared/styles.css`. |
| **Languages** | **English only.** No language switcher. |
| **Demo Data** | **Priya dataset** — internally consistent across all pages (`data/demo-data.json`), including `score_events` for the Confidence Score Drill-In panel. |

**Testing viewports:** 1366×768, 1440×900, 1920×1080 (mobile viewports no longer in scope for Phase 1). Content areas are **fluid** — they fill the available window up to a 1680px cap, rather than sitting in a fixed narrow column regardless of window size (2026-07-09 update).

---

## Scenario Overview

Priya (32, salaried marketing exec in Mumbai, ~₹65k/month, EMI-carrying) registers, uploads her June bank statement, reviews categorized transactions, and receives her first honest **Safe-to-Spend** briefing + **Confidence Score**, one proactive insight, and a first Copilot conversation — all in one sitting.

**Business goal:** ⭐ Measurably reduce financial anxiety (THE ENGINE). WoZ gate: anxiety ≥ 3.5/5; Safe-to-Spend understood by 5/5 pilot users.

**The moat = the honesty layer.** Every page must carry it: freshness caveats, confidence chips + Drill-In panel, "Why?" reasoning, data-trace on Copilot answers, observation-not-judgment tone, and "information not advice" (SEBI boundary).

---

## Page Build Sequence

| # | Page | HTML | Status |
|---|------|------|--------|
| 01.1 | Register | `01.1-register.html` | ✅ Built |
| 01.2 | Login (auto-authentication transition) | `01.2-login.html` | ✅ Built |
| 01.3 | Statement Upload | `01.3-statement-upload.html` | ✅ Built — completes to Dashboard (2026-07-09, was Transactions) |
| 01.5 | Dashboard | `01.5-dashboard.html` | ✅ Built — **default post-upload landing page** (2026-07-09); below-fold responsive card grid incl. new "View All Transactions" CTA |
| 01.4 | Transactions Table | `01.4-transactions-table.html` | ✅ Built — reached from the Dashboard, not automatically after Upload |
| 01.6 | AI Insights & Recommendations | `01.6-ai-insights-recommendations.html` | ✅ Built |
| 01.7 | Copilot Chat | `01.7-copilot-chat.html` | ✅ Built |
| 02.1 | Commitments Management (Scenario 02, promoted P2→P1) | `02.1-commitments-management.html` | ✅ Built |

**Status values:** ⬜ Not started → 🟡 Building → ✅ Built → ✔️ Approved

**All 8 views built & verified.** Scenario 01's 7 views built 2026-07-08; Scenario 02's Commitments Management (02.1) built 2026-07-09 following the P2→P1 scope correction in `00-ux-scenarios.md`. Each passed CDP functional verification (zero console errors) — Dashboard ⇄ Commitments cross-page add/edit/delete flows verified end-to-end via the shared `shared/commitments.js` store. Serve with a static file server in this folder (e.g. `python -m http.server 8000`), then open `http://localhost:8000/`.

---

## Folder Structure

```
01-priyas-first-honest-morning-Prototype/
├── PROTOTYPE-ROADMAP.md      (this file)
├── data/
│   └── demo-data.json        (Priya dataset — single source of truth)
├── work/                     (one work file per page, created just-in-time)
├── stories/                  (section implementation guides, just-in-time)
├── shared/                   (shared JS: data loader, formatting, nav, commitments store)
├── components/               (reusable UI components)
├── pages/                    (page-specific scripts, if complex)
├── assets/                   (images, icons)
└── *.html                    (prototype pages, added to root as built)
```

---

## Key Data Anchors (from demo-data.json)

These numbers must stay consistent across every page — never invent contradictory figures:

- **Safe-to-Spend today:** ₹2,840 · **After salary:** ₹8,200
- **Confidence:** "On track" (amber, 1 month of data) — label only, never the raw score; drill-in shows `score_events`
- **Current balance:** ₹25,040 · **Ring-fenced EMIs:** ₹18,000 · **Recurring:** ₹4,200
- **Statement:** HDFC Bank ...4821, June 2026 (dated 2026-06-30)
- **Food spend:** ₹7,200 (up from ₹5,100) — the lead insight
- **Transactions:** 47 total, 3 need review
- **Upcoming EMIs:** Car Loan ₹6,500 (5 Jul), Personal Loan ₹3,000 (10 Jul), HDFC EMI ₹8,500 (15 Jul)

---

## Notes

- **Build one page at a time, section by section**, with approval gates.
- **Verify each page** (browser/Puppeteer) before presenting for testing.
- Every honesty-layer element is a requirement, not a nice-to-have.
