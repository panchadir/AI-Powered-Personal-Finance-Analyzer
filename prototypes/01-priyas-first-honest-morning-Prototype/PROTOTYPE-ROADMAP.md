# Prototype Roadmap — Scenario 01: Priya's First Honest Morning

**Project:** AI-Powered-Personal-Finance-Analyzer
**Scenario:** 01 — Priya's First Honest Morning (Golden Path, P1)
**Created:** 2026-07-08
**Method:** Whiteport Design Studio (WDS) — Phase 5 Agentic Development / Prototyping

---

## Setup Decisions (Initiation Dialog)

| Question | Answer |
|----------|--------|
| **Device Compatibility** | Desktop + Mobile — **Fully Responsive** (375px → 1920px). Mobile-first layouts that adapt up to desktop. |
| **Design Fidelity** | Started **Generic Gray Model** (wireframe), then **upgraded to a branded visual theme** (2026-07-08, user request): a calm teal fintech identity with warm accents, elevated cards, pill buttons, and a designed chart palette. All 7 pages retheme from the `:root` tokens in `shared/styles.css`. |
| **Languages** | **English only.** No language switcher. |
| **Demo Data** | **Priya dataset** — internally consistent across all 7 pages (`data/demo-data.json`). |

**Testing viewports:** Mobile 375px (iPhone SE), 393px; Desktop 1280px+.

---

## Scenario Overview

Priya (32, salaried marketing exec in Mumbai, ~₹65k/month, EMI-carrying) registers, uploads her June bank statement, reviews categorized transactions, and receives her first honest **Safe-to-Spend** briefing + **Confidence Score**, one proactive insight, and a first Copilot conversation — all in one sitting.

**Business goal:** ⭐ Measurably reduce financial anxiety (THE ENGINE). WoZ gate: anxiety ≥ 3.5/5; Safe-to-Spend understood by 5/5 pilot users.

**The moat = the honesty layer.** Every page must carry it: freshness caveats, confidence chips, "Why?" reasoning, data-trace on Copilot answers, observation-not-judgment tone, and "information not advice" (SEBI boundary).

---

## Page Build Sequence

| # | Page | HTML | Status |
|---|------|------|--------|
| 01.1 | Register | `01.1-register.html` | ✅ Built |
| 01.2 | Login (auto-authentication transition) | `01.2-login.html` | ✅ Built |
| 01.3 | Statement Upload | `01.3-statement-upload.html` | ✅ Built |
| 01.4 | Transactions Table | `01.4-transactions-table.html` | ✅ Built |
| 01.5 | Dashboard | `01.5-dashboard.html` | ✅ Built |
| 01.6 | AI Insights & Recommendations | `01.6-ai-insights-recommendations.html` | ✅ Built |
| 01.7 | Copilot Chat | `01.7-copilot-chat.html` | ✅ Built |

**Status values:** ⬜ Not started → 🟡 Building → ✅ Built → ✔️ Approved

**All 7 views built & verified (2026-07-08).** Each passed CDP functional + visual verification (zero console errors); the full golden path passes an end-to-end integration test. Serve with `python -m http.server 8000` in this folder, then open `http://localhost:8000/01.1-register.html`.

---

## Folder Structure

```
01-priyas-first-honest-morning-Prototype/
├── PROTOTYPE-ROADMAP.md      (this file)
├── data/
│   └── demo-data.json        (Priya dataset — single source of truth)
├── work/                     (one work file per page, created just-in-time)
├── stories/                  (section implementation guides, just-in-time)
├── shared/                   (shared JS: data loader, formatting, nav)
├── components/               (reusable UI components)
├── pages/                    (page-specific scripts, if complex)
├── assets/                   (images, icons)
└── *.html                    (prototype pages, added to root as built)
```

---

## Key Data Anchors (from demo-data.json)

These numbers must stay consistent across every page — never invent contradictory figures:

- **Safe-to-Spend today:** ₹2,840 · **After salary:** ₹8,200
- **Confidence:** Medium (1 month of data)
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
