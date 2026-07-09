# 02: Priya Protects What Matters

**Project:** AI-Powered-Personal-Finance-Analyzer
**Created:** 2026-07-08
**Method:** Whiteport Design Studio (WDS)

---

## Transaction (Q1)

**What this scenario covers:**
Log back in and add a recurring commitment (her electricity bill) so it's correctly ring-fenced by the Safe-to-Spend engine.

---

## Business Goal (Q2)

**Goal:** 🌟 ECOSYSTEM & MEMBER BENEFIT — Make users genuinely more prepared, not just calmer
**Objective:** Confidence Score trending up for ≥ 80% of users in their first 30 days; reinforces the PRIMARY goal's non-negotiable safety guarantee (Safe-to-Spend must never recommend spending that causes a missed committed obligation)

---

## User & Situation (Q3)

**Persona:** Priya — The Overwhelmed Earner (Primary)
**Situation:** A few days into using the app now, she opens it again one evening specifically because she remembers her electricity bill is due soon and wants to make sure it's accounted for.

---

## Driving Forces (Q4)

**Hope:** Adding this bill will make her Safe-to-Spend number account for it correctly, so she can't accidentally spend money she needs for it.

**Worry:** If she doesn't add it, the app won't know about it and might let her overspend into a missed payment.

---

## Device & Starting Point (Q5 + Q6)

**Device:** Desktop (localhost, single-user browser app)
**Entry:** Returning user, she opens the app that evening specifically to check her upcoming bills. She logs in (returning-user /login, not a numbered scenario step) and navigates directly to Commitments.

---

## Best Outcome (Q7)

**User Success:**
Her electricity bill is now ring-fenced with the correct amount, due-day, and criticality, and her Safe-to-Spend number recalculates to reflect it — she feels confident it's protected.

**Business Success:**
Demonstrates the conservative-by-default ring-fencing mechanism working correctly — the kill-signal prevention layer in action, supporting the "Confidence Score up for ≥80% of users" target.

---

## Shortest Path (Q8)

1. **Commitments Management** — she adds her electricity bill (amount, due-day, criticality) and sees her Safe-to-Spend number update to reflect it, protected ✓

> **Note:** The returning-user Login page is a prerequisite that Priya completes before entering this scenario. Login is documented as a standalone page at `/login` (not a numbered scenario step) since it is a shared, recurring entry point across scenarios — not specific to this journey.

---

## Trigger Map Connections

**Persona:** Priya — The Overwhelmed Earner (Primary)

**Driving Forces Addressed:**
- ✅ **Want:** To feel like a capable adult, not a failing student
- ❌ **Fear:** The end-of-month shock

**Business Goal:** 🌟 Make users genuinely more prepared — Confidence Score up for ≥ 80% of users

---

## Scenario Steps

| Step | Folder | Purpose | Exit Action |
|------|--------|---------|-------------|
| 02.1 | `02.1-commitments-management/` | Add her electricity bill as a protected commitment | Final — scenario success ✓ |

**First step** (02.1) includes full entry context (Q3 + Q4 + Q5 + Q6).
**On-step interactions** (that don't leave the step) are documented as storyboard items within each page spec.
