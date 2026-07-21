# Story — Register § Section 1: Shared Infra + Page Shell + Header

**View:** 01.1 Register · **Section:** 1 of 6 · **Est:** 20 min
**Spec:** UX Scenario 01.1 — Register (Priya's First Honest Morning)
**Output:** `01.1-register.html` + `shared/styles.css`, `shared/format.js`, `shared/data.js`, `shared/nav.js`

---

## Purpose

Lay the reusable foundation for the entire Scenario 01 prototype (design tokens, data loader, formatting, nav) and render the Register page shell + brand header. Gray Model fidelity — grayscale, functional, no brand color.

---

## Objects

| Object ID | Type | Content / Behavior | State |
|---|---|---|---|
| `register-header` | container | Vertical stack, centered. Padding: space-lg top, space-md bottom; element gap space-sm | default |
| `register-header-logo` | logo mark | Gray rounded-square placeholder (48px) with a simple glyph — no real asset yet | default |
| `register-header-app-name` | H1 display text | "AI Financial Copilot" — text-2xl, bold, display family | default |

---

## HTML Structure

```
<main class="page page--auth">           <!-- centered responsive column, max-width 420px, grows to comfortable desktop width -->
  <div class="auth-card">                 <!-- the register content wrapper -->
    <header id="register-header" class="register-header">
      <div id="register-header-logo" class="logo-mark" aria-hidden="true">₹</div>
      <h1 id="register-header-app-name" class="app-name">AI Financial Copilot</h1>
    </header>
    <!-- Sections 2-5 inject below here -->
  </div>
</main>
```

## Design Tokens (`shared/styles.css`)

- **Reset/base:** box-sizing, system font stack; `--font-display` = same stack, bold usage.
- **Grayscale palette:** `--gray-50 … --gray-900`, `--ink` (#1f2937), `--muted` (#6b7280), `--line` (#e5e7eb), `--bg` (#f9fafb), `--surface` (#ffffff).
- **Spacing scale:** `--space-xs:4px --space-sm:8px --space-md:16px --space-lg:24px --space-xl:40px`.
- **Type scale:** `--text-xs:12px … --text-lg:20px --text-2xl:28px --text-4xl:40px`; weights normal/medium/semibold/bold.
- **Radius/shadow:** `--radius:12px`, subtle `--shadow`.
- **Layout:** `.page--auth` = min-height:100vh, flex center, padding space-md; `.auth-card` = width 100%, max-width 420px.
- **Responsive:** mobile-first. `@media (min-width:768px)` slightly larger type; `@media (min-width:1280px)` card sits centered with a touch more padding. No horizontal page scroll at any width.
- Primitives to define now (reused by later sections/pages): `.btn`, `.btn--primary`, `.field`, `.field label`, `.field input`, `.field .error`, `.toast`, `.link`.

## JavaScript

- **`shared/format.js`** — `formatINR(n)` → "₹2,840" (Indian grouping); `formatDate(iso, style)` → "30 Jun 2026".
- **`shared/data.js`** — `loadDemoData()` fetches `data/demo-data.json` (async), caches, returns object; exposes `window.DEMO` after load. Fallback: if `fetch` of local file is blocked (file://), embed a note in console — pages must be served over http (documented in roadmap).
- **`shared/nav.js`** — `renderBottomNav(activeTab)` builds Home/Transactions/Commitments/Copilot bar; `goNext(currentPage)` for linear routing. Stubbed/available; not shown on Register (public page).
- Register page itself needs no JS in Section 1 (static header).

## Demo Data

None required for the header. `data.js` is wired but the header is static.

---

## Acceptance Criteria

**Agent-verifiable (Puppeteer/headless):**
- [ ] `01.1-register.html` loads with no console errors when served over http.
- [ ] `#register-header-app-name` text is exactly "AI Financial Copilot".
- [ ] `#register-header-logo` renders (visible, 48px box).
- [ ] `shared/styles.css`, `format.js`, `data.js`, `nav.js` all load (200, no 404).
- [ ] `formatINR(2840)` returns "₹2,840"; `formatDate('2026-06-30')` returns "30 Jun 2026".
- [ ] No horizontal scrollbar at 375px and 1280px viewports.

**User-evaluable (qualitative):**
- [ ] Header looks clean and trustworthy at a glance (Gray Model, not broken).
- [ ] Centered layout feels right on both a phone and a desktop width.
- [ ] Brand name is prominent without shouting.

## Test Instructions

1. Serve the prototype folder over http (e.g. `python -m http.server` in the prototype dir).
2. Load `01.1-register.html` at 375px then 1280px.
3. Check console clean; run `formatINR`/`formatDate` sanity in console.
4. Present screenshot(s) for user review.
