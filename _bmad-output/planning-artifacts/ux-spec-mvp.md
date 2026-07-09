# UX Spec — Phase 1 MVP (lightweight, build-along)

**Created:** 2026-07-08
**Author:** Sally (UX)
**Status:** Build-ready reference for a solo dev. Pairs with [`prd.md`](prd.md) FR-6/FR-7 and the Product Brief's **Tone of Voice** section.
**Device target:** Desktop web only (localhost, single-user) — resolved PRD open item X1. No responsive/mobile layout in Phase 1.

> **Why this exists.** The BMAD Phase-4 UX step was skipped, so the dashboard, briefing, and chat were about to be built with zero wireframes and an unenforced tone. This is the minimum spec that keeps the brief's promise — **"leads with the number + its why, not a chart wall"** — and turns the tone-of-voice examples into copy a developer can paste. Not a full design system; a north star + a microcopy sheet.

---

## Layout hierarchy (non-negotiable order)

The brief's rule: **the number and its plain-language "why" are the hero; charts are supporting evidence.** Enforce visually — hero first, charts below the fold.

### 1. Dashboard (FR-6)
```
┌──────────────────────────────────────────────────────────┐
│  Good morning, Priya.              🛡 Well prepared [Why?] │  ← greeting + score chip label only (no raw number; FR-5.5)
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Safe to spend today                               │ │  ← HERO card (rx.card)
│  │            ₹830                                     │ │     big number
│  │  Rent (₹15,000, due in 6 days) is set aside.       │ │     the "why", one calm sentence
│  │  Based on your statement up to 26 Jul.  [Show me why]│ │   ← freshness caveat + drill-in
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  After your salary on 1 Aug: about ₹1,250/day           │  ← second layer, never merged with today
│                                                          │
│  Your morning briefing ─────────────────────────────    │  ← narration panel (FR-6.2), 2–4 sentences
│  "You're on track this week. Your spending pace is …"    │
│                                                          │
│  ▸ Where your money went   ▸ This month's pace          │  ← charts (rx.plotly) — collapsed / below hero
│  ▸ Upcoming commitments (timeline)                      │
└──────────────────────────────────────────────────────────┘
```

### 2. Confidence Score drill-in (FR-5.3/FR-5.5) — reached from the score chip
> **FR-5.5 enforcement:** the raw score number (e.g. 87) must never be displayed. The chip shows a label only ("Well prepared" / "On track" / "Watch this").
```
You're well prepared  ·  Confidence chip: green "Well prepared"
Prediction confidence: Medium — some cash spends may be missing.
What moved it (from score_events):
  +4  Rent covered with buffer to spare      · 3 days ago
  −2  Spending pace up vs. last week         · yesterday
[ every row = a real event; no unexplained changes ]
```

### 3. Copilot chat (FR-7) — *must-ship (scope locked 2026-07-08)*
```
┌──────────────────────────────────────────────┐
│  Ask me anything about your money            │
│  ─────────────────────────────────────────   │
│  You: Can I afford ₹3,000 for a concert?     │
│  🤖 Your safe-to-spend today is ₹830, and    │  ← streams token-by-token
│     rent's already set aside. ₹3,000 would   │
│     dip into next week's cushion — here's …  │
│  ─────────────────────────────────────────   │
│  [Can I afford ₹___?] [How am I doing?]      │  ← gut-check quick prompts (P1)
└──────────────────────────────────────────────┘
```

### 4. Upload (FR-2) — honest progress, honest refusal
```
Drop your bank statement (PDF or CSV)   [ choose file ]
→ "Parsed 214 transactions · 187 by rules, 24 by AI, 3 need your help"
→ scanned image PDF: "I can't read this one — it's a scanned image, not
   text. Try the CSV export from your bank instead."
```

---

## Microcopy sheet (paste-ready; from the brief's Tone of Voice)

Tone: **honest · calm · non-judgmental · plain-language · warm-not-saccharine.** Always pair a number with its reason; never shame; never bury the confidence caveat.

| State | ✅ Use this | ❌ Never this |
|---|---|---|
| Upload error (scanned PDF) | "I can't read this one — it's a scanned image, not text. Try your bank's CSV export." | "Error: no text layer (code 422)." |
| Empty dashboard (no data) | "Upload a statement and I'll show you what's safe to spend — and why." | "No data available." |
| Category taught | "Got it — I'll call Swiggy 'Dining' from now on." | "Category updated successfully." |
| Low prediction confidence | "I'm fairly sure, but some cash spends may be missing — add them and I'll sharpen this." | "Confidence: LOW." |
| Shortfall (Scenario 10) | "Your committed bills before payday come to ₹9,500 more than your balance. Here's what I'd protect first." | "Insufficient funds." |
| Spending pace up | "Your spending pace picked up this week." | "You overspent." |
| Drill-in button | "Show me why" | "View details" |
| Safe-to-Spend, always | "₹830 — rent's already set aside." | "₹830" (bare number) |

## Enforcement checklist (the 7 things that must survive the build)
1. Hero number + one-sentence why is **above** any chart.
2. Two-layer Safe-to-Spend never merged into one figure.
3. Every number in prose == engine output (spot-check per FR-6 AC).
4. Freshness caveat ("based on your statement up to {date}") is **on the hero card**, not buried.
5. No shame-adjacent language anywhere — reframe as observation.
6. **Persistent left nav** (Dashboard / Transactions / Commitments / Insights / Copilot) present on all 5 app screens — FR-6.4 P0. Note: wireframes above are full-width; add a left-sidebar column (width ~200px) to every app-screen layout at implementation.
7. "**Step 1 of 3**" step indicator (Upload → Review → Dashboard) visible on the Upload page — FR-2.5 P0 (functional onboarding contract, not decoration).

*Generated by BMAD party-mode cross-functional review — closes the "UX/UI Design spec missing" row in the Alignment Matrix.*
