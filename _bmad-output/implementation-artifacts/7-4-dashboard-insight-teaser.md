---
baseline_commit: bc4e17c9528a0c1e2cbdd03a155071a856f35b33
---

# Story 7.4: Dashboard Insight Teaser

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user on the Dashboard,
I want to see a brief preview of my top insight without navigating away,
so that I notice actionable patterns at a glance.

## Story Context

**Epic 7 — Proactive Insights, story 4 of 4 (last story in the epic).** Stories 7.1 (done — five detectors), 7.2 (done — O→E→E→A narration + SEBI guard), and 7.3 (done — the real `/insights` page, persistence, dismiss lifecycle, resurface/dedup state machine) are all complete. This story is a small, purely additive UI story: one read-only teaser card on the Dashboard, plus a deep-link from it into the Insights page.

**What this story delivers:**
1. A read-only bridge function, `finance_app/state/insights_bridge.py::top_active_insight(session, user_id) -> Insight | None` — the single highest-priority active insight (same severity-tier/newest-first ordering `_load_active` already uses), reusing that existing private helper. **Deliberately does not run detectors or call the narrator** (see "Why this is read-only" below).
2. `DashboardState` (`finance_app/state/dashboard_state.py`) gains teaser display fields, populated inside the existing `load_dashboard` handler.
3. A new `_insight_teaser()` component in `finance_app/pages/dashboard.py`, reusing `.insight-card`/`.insight-card-head`/`.insight-icon`/`.insight-name`/`.insight-observation` — all already compiled into `assets/wds.css` from Story 7.3. No new CSS.
4. A highlight-and-scroll mechanism on the Insights page: tapping the teaser links to `/insights?highlight={id}`; `InsightsState` reads that param and scrolls the matching card into view via `rx.call_script` (Reflex 0.9.6 — confirmed present: `rx.call_script(javascript_code, callback=None) -> EventSpec`, executes arbitrary client-side JS). Each insight card gets a stable `id="insight-{db_id}"` attribute to scroll to.

**Why this is read-only (no detector run from the Dashboard):** Story 7.1's AC originally imagined detectors firing "after every successful ingestion or categorisation batch," but that webhook doesn't exist — Story 7.3's Dev Notes already resolved this to **on-Insights-page-load** detection only (`InsightsState.load_insights` is the only caller of `refresh_insights`, which can make LLM narration calls). If the Dashboard's teaser also called `refresh_insights`, every Dashboard page load would risk an LLM call too — doubling narration cost and latency for a card that only needs to *read* whatever is already persisted. Read-only also means: a user who has never opened `/insights` will correctly see no teaser (zero rows exist yet) — this is indistinguishable from "ran and found nothing" and both are correct per this story's own AC ("teaser is absent when no active insights exist").

**What this story does NOT deliver (explicit scope boundary — do not build):**
- ❌ Any change to `services/engine/insights/*` or `services/narrate/insight_narrator.py` (Stories 7.1/7.2, done — this story only reads already-persisted `Insight` rows).
- ❌ Any change to the resurface/dedup state machine, `dismiss_insight`, or `refresh_insights` itself in `insights_bridge.py` — only a new, additive, read-only function is added alongside them.
- ❌ A visual "highlighted" style on the scrolled-to card (e.g. a colored border/glow). The AC only asks for scroll position ("scrolled to that specific insight"), not a persistent visual treatment — keep it to the literal AC (KISS, mirrors Story 7.3's own "ordering only, no color coding" decision for severity).
- ❌ Touching the Dashboard's existing "See my insights →" button inside `_briefing_card()` (Story 5.3) — that is a separate, already-shipped, generic CTA. This story's teaser adds its own distinct "See all insights →" link that is specific to the top insight (`href="/insights?highlight={id}"`), not a duplicate of the briefing card's button.

## Acceptance Criteria

1. **Teaser visibility:** when at least one active (non-dismissed) insight exists for the user, a teaser card renders on the Dashboard, below the narration/briefing panel (`_briefing_card()`). When no active insight exists (including: user has never opened `/insights`, or all insights are dismissed), the teaser renders nothing at all — no placeholder text, no "No insights yet" copy (UX-DR-4: the hero card already fills the screen; this must not add a second empty-state message competing with it).
2. **Teaser content:** pattern name (title), the **Observation sentence only** (not Explanation/Effect/Advice — those stay on the full Insights page), and a "See all insights →" link.
3. **Which insight is "top":** the same ordering `/insights` itself uses — severity tier first (`critical` → `important` → `flexible`), then newest-first within tier. Take the first row. Do not reimplement this ordering logic — reuse `insights_bridge._load_active`.
4. **Navigation:** tapping the teaser (or its link) navigates to `/insights?highlight={insight.id}`, and on that page load, the matching card scrolls into view. If the highlighted id no longer matches any active card (e.g. dismissed or materially-changed between the Dashboard load and the click), the page just loads normally with no scroll and no error — never a crash on a stale id.
5. **No arithmetic on the Dashboard from this story.** The teaser's pattern name and Observation sentence are copied verbatim from the `Insight` row — already-narrated prose from Story 7.2, already-persisted by Story 7.3. This story adds no new computation, only a read and a display (AD-1).

## Tasks / Subtasks

- [x] **Task 1 — `top_active_insight` in `finance_app/state/insights_bridge.py` (AC: 1, 3, 5)**
  - [x] Add `top_active_insight(session: Session, user_id: int) -> Insight | None`: calls the existing `_load_active(session, user_id)` (already implements the exact severity-tier/newest-first ordering this story needs — read its docstring at `insights_bridge.py:184` before touching anything) and returns `rows[0] if rows else None`. Add to `__all__`.
  - [x] Do **not** call `run_all_detectors` or `generate_insight_narration` here, and do not call `refresh_insights`. This function only reads what Story 7.3's `refresh_insights` has already persisted (see "Why this is read-only" in Story Context).
- [x] **Task 2 — `DashboardState` teaser fields (AC: 1, 2, 3, 5)**
  - [x] Read `finance_app/state/dashboard_state.py` in full first (Story 5.1/5.2/5.3's existing state — you will extend `load_dashboard`, not replace it). Add fields: `has_top_insight: bool = False`, `top_insight_pattern_name: str = ""`, `top_insight_observation: str = ""`, `top_insight_href: str = ""` (precompute the full `/insights?highlight={id}` string here — a `rx.foreach`/render function cannot easily f-string an int into a URL; precompute it as a plain Python string in the event handler, mirroring how `insights_state.py`'s `_to_card` precomputes `copilot_href` for the identical reason).
  - [x] Inside `load_dashboard`'s existing `with rx.session() as session:` block (after the current `data = compute_dashboard(session, user.id)` line, no need for a second session), call `insights_bridge.top_active_insight(session, user.id)`. If it returns a row: `has_top_insight = True`, `top_insight_pattern_name = row.pattern_name`, `top_insight_observation = row.observation`, `top_insight_href = f"/insights?highlight={row.id}"`. If `None`: `has_top_insight = False` and clear the other three fields.
  - [x] `_reset_to_empty()` (the no-`has_data` branch) must also reset the four new fields — mirrors every other field already reset there; a user with no statement cannot have an insight either, but keep the state consistent rather than relying on that invariant implicitly.
  - [x] This is a plain synchronous DB read (no LLM call) — do not wrap it in `asyncio.to_thread` (that pattern in this file exists specifically for the narration LLM call in the second phase; this new read belongs in the first, synchronous phase alongside `compute_dashboard`).
- [x] **Task 3 — `_insight_teaser()` in `finance_app/pages/dashboard.py` (AC: 1, 2, 4)**
  - [x] Read the current file in full first — you are adding one new component function and one call site, not restructuring the page.
  - [x] New `_insight_teaser() -> rx.Component`: `rx.el.article(rx.el.div(rx.el.span("💡", class_name="insight-icon", aria_hidden="true"), rx.el.h2(DashboardState.top_insight_pattern_name, class_name="insight-name"), class_name="insight-card-head"), rx.el.p(DashboardState.top_insight_observation, class_name="insight-observation"), rx.el.a("See all insights →", href=DashboardState.top_insight_href, class_name="btn btn--secondary"), class_name="insight-card")`. Reuses classes already compiled into `assets/wds.css` (Story 7.3) — do not add new CSS.
  - [x] Wrap the call site in `rx.cond(DashboardState.has_top_insight, _insight_teaser(), rx.el.div())` (exact pattern already used for `_stale_banner`/empty states elsewhere in this file) — renders nothing at all when false, per AC #1.
  - [x] Place it as its own top-level element directly after the existing `rx.el.div(_briefing_card(), _commitments_card(), class_name="dash-grid")` block inside `dashboard()`'s render tree — a **sibling** of `dash-grid`, not a third child inside it. `dash-grid`'s CSS is laid out for exactly 2 cards (Story 5.3/5.5); do not add a third child there.
- [x] **Task 4 — Highlight + scroll on the Insights page (AC: 4)**
  - [x] `finance_app/state/insights_state.py`: `InsightsState` gains `highlight_id: int = 0`. In `load_insights` (already `async`, already reads via `rx.session()`), after `self.cards = [...]` is set, read `self.router.page.params.get("highlight", "")`, parse to `int` inside a `try/except (ValueError, TypeError): pass` (mirrors `copilot_state.py`'s identical `?insight=` parsing exactly), and if it parses, set `self.highlight_id = parsed`. Then, if `self.highlight_id` is truthy, return `rx.call_script(...)` to scroll it into view — the `?.` optional-chaining guard means a stale/no-longer-active id (dismissed or materially-changed since the Dashboard loaded) is a silent no-op in the browser, never a JS error (AC #4's explicit "never a crash on a stale id"). **Implementation note:** used a plain `return` (not `yield`) — `load_insights` was not already an async generator, and adding a bare `yield` would have turned the existing early `return rx.redirect(LOGIN_ROUTE)` into a `SyntaxError` (the exact bug class already fixed once in `dashboard_state.load_dashboard`, Epic 5). Reading the query param and returning the scroll event after the `with rx.session()` block closes achieves the same effect without that risk.
  - [x] `finance_app/pages/insights.py`: `_insight_card(card)`'s outer `rx.el.article(...)` gains `id="insight-" + card.id.to_string()` — verified via `reflex compile --dry` that the inline `Var.to_string()` form compiles cleanly; no precomputed `dom_id` field was needed.
  - [x] Do **not** add a persistent highlight CSS class/style — see Story Context's explicit scope boundary on this.
- [x] **Task 5 — Tests (AC: all)**
  - [x] `tests/test_insights_bridge.py`: added `TestTopActiveInsight` (4 tests) covering — no active insights for a fresh user → `None`; one active insight → returns it; a dismissed-only insight (no active rows) → `None`; multiple active insights of different severities → returns the correct top one (critical before important before flexible).
  - [x] No test file exists today for `dashboard_state.py` or `insights_state.py` (confirmed — `tests/` has none; only bridge-level pure functions are unit-tested in this codebase). Kept `DashboardState`/`InsightsState`'s own new glue code (Tasks 2 and 4) covered by the Green Gate (compile + pytest + live route check), consistent with how the rest of both files are already (not) tested.
- [x] **Task 6 — Green gate** — `pytest tests/ -q` (whole repo): **505 passed, 6 skipped** (was 501; +4 new). `reflex compile --dry`: SUCCESS. Ran inside the project's Docker container.

## Dev Notes

### Why a new bridge function instead of reusing `refresh_insights`

`refresh_insights` runs all 5 detectors and can call `generate_insight_narration` (an LLM call) for every new/materially-changed pattern — appropriate once per Insights-page-load, wrong to also trigger on every Dashboard-page-load (doubles narration cost/latency for a feature that only needs to *display* what's already there). `top_active_insight` is a pure read: `_load_active` + `[0]`. This mirrors the general principle already established in this codebase (`engine_bridge.py` vs `dashboard_state.py`): compute/narrate once, read cheaply everywhere else.

### `_load_active`'s docstring (read before touching)

`finance_app/state/insights_bridge.py:184-199` — already implements exactly the ordering this story needs (severity tier via `_SEVERITY_ORDER`, then `created_at.desc()`/`id.desc()` as a stable secondary sort, fixed during Story 7.3's code review specifically so an in-place-updated row moves back to the top of its tier). `top_active_insight` must call this, not reimplement any part of it.

### `rx.call_script` — confirmed present and current (Reflex 0.9.6.post1, this project's pinned version)

Verified empirically in the project's own Docker container (no `reflex-docs` skill was installed in this environment despite AGENTS.md's instruction — following this session's own established precedent of empirical verification when that skill is unavailable, e.g. Step 61's `rx.Base` removal check):
```
inspect.signature(rx.call_script) -> (javascript_code: str | Var[str], callback: EventType | None = None) -> EventSpec
```
Use as a yielded event: `yield rx.call_script("...")`. `document.getElementById(id)?.scrollIntoView(...)` with the optional-chaining `?.` is what makes a stale/missing id a silent no-op rather than a JS exception — do not add a manual existence check in Python; the JS guard is sufficient and simpler.

### Deliberate deviation from the WDS prototype's per-card `id` convention

The static prototype (`01.6-ai-insights-recommendations.html`) ids each card by render-position index (`id="insights-card-N-..."`, `N` = loop counter). That cannot serve a deep-link: the same pattern's card can move position (severity/recency reordering, Story 7.3) or stop existing (dismissed) between when the Dashboard teaser is rendered and when the user clicks it. This story anchors by the **persisted DB row id** instead (`id="insight-{db_id}"`), which is stable across reordering and is exactly what the teaser's link already carries (`?highlight={id}`). Document this as an intentional divergence, not an oversight, if a future reviewer diffs against the prototype.

### `DashboardState`/`InsightsState` have no existing test files — do not introduce one just for this story

Confirmed via `tests/*.py` listing: `dashboard_state.py` and `insights_state.py` (both `rx.State` classes with `rx.session()`/`on_load` wiring) have zero dedicated pytest coverage anywhere in this repo — only the pure bridge/engine layers (`engine_bridge.py`, `insights_bridge.py`) are unit-tested. This is a pre-existing repo-wide pattern (not something to fix in this small story) — Reflex state classes are verified via `reflex compile --dry` + manual/live checks, consistent with how `DashboardState.load_dashboard` itself (Story 5.1-5.3, far larger than this story's addition) has never had a dedicated test file. Keep Task 2/Task 4's new state code to that same standard; put the one genuinely new piece of *pure logic* (`top_active_insight`) in the bridge layer, where it can and must be tested.

### Project Structure Notes

- New: nothing (no new files this story — every change is additive to existing files).
- Modified: `finance_app/state/insights_bridge.py` (+1 function), `finance_app/state/dashboard_state.py` (+4 fields, ~6 lines in `load_dashboard`), `finance_app/pages/dashboard.py` (+1 component, +1 call site), `finance_app/state/insights_state.py` (+1 field, a few lines in `load_insights`), `finance_app/pages/insights.py` (+1 attribute on the existing card), `tests/test_insights_bridge.py` (+1 test class).
- No new CSS, no new migration, no changes to `services/engine/insights/*` or `services/narrate/*`.

### References

- Epic & this story's exact AC text, plus Story 7.3's (for the ownership boundary already drawn there): [epics.md §Epic 7](../planning-artifacts/epics.md) (Story 7.3 lines ~861–889, Story 7.4 lines ~891–906).
- Function to reuse, not reimplement: [finance_app/state/insights_bridge.py](../../finance_app/state/insights_bridge.py) (`_load_active`, `Insight` model fields).
- Pattern to mirror for query-param parsing: [finance_app/state/copilot_state.py](../../finance_app/state/copilot_state.py)'s `?insight=`/`?pre=` handling in `load_history` (Story 6.4).
- Pattern to mirror for precomputed per-row href strings: [finance_app/state/insights_state.py](../../finance_app/state/insights_state.py)'s `_to_card`/`copilot_href` (Story 7.3).
- File this story extends (read in full before touching): [finance_app/state/dashboard_state.py](../../finance_app/state/dashboard_state.py), [finance_app/pages/dashboard.py](../../finance_app/pages/dashboard.py) (Stories 5.1/5.2/5.3).
- File this story extends (read in full before touching): [finance_app/state/insights_state.py](../../finance_app/state/insights_state.py), [finance_app/pages/insights.py](../../finance_app/pages/insights.py) (Story 7.3).
- CSS classes reused (already compiled, confirmed present): `assets/wds.css` — `.insight-card`, `.insight-card-head`, `.insight-icon`, `.insight-name`, `.insight-observation` (lines ~546-554).
- WDS prototype (layout inspiration only — no per-story teaser markup actually exists there; the prototype's dashboard only has a generic "See my insights →" button, already built in Story 5.3): [prototypes/01-priyas-first-honest-morning-Prototype/01.5-dashboard.html](../../prototypes/01-priyas-first-honest-morning-Prototype/01.5-dashboard.html); per-card id convention referenced above: [01.6-ai-insights-recommendations.html](../../prototypes/01-priyas-first-honest-morning-Prototype/01.6-ai-insights-recommendations.html).
- Project rules (AD-1 zero-computed-numbers, AD-13 formatINR/formatDate — not directly relevant here since the teaser shows no money figures, only already-narrated prose): [project-context.md](../project-context.md).
- Story 7.3 review lessons worth watching for here too: [7-3-insights-page-and-dismiss-lifecycle.md](./7-3-insights-page-and-dismiss-lifecycle.md) Review Findings (18 findings — in particular the "both metric values unknown" guard and the stale-Copilot-context-handoff pattern: this story's own stale-highlight-id case is the same *shape* of problem — a persisted reference that can outlive what it refers to — solved here via the `?.` JS guard rather than a DB filter, since there is no DB write on this path).

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (BMAD create-story + dev-story workflows, Amelia persona)

### Debug Log References

- `docker exec ... python -c "import reflex as rx; inspect.signature(rx.call_script)"` confirmed `rx.call_script(javascript_code, callback=None) -> EventSpec` exists in the project's pinned Reflex 0.9.6.post1 before committing to that approach in the story's own Dev Notes (no `reflex-docs` skill was installed in this environment).
- `pytest tests/test_insights_bridge.py` after Task 1 alone: 22 passed (was 18 before this story; +4 new `TestTopActiveInsight` tests) — confirmed red (`ImportError: cannot import name 'top_active_insight'`) before implementing, green after.
- After Tasks 2–4: `reflex compile --dry` → success on the first attempt, including the inline `"insight-" + card.id.to_string()` id-attribute concatenation (no fallback to a precomputed `dom_id` field was needed).
- Full-repo `pytest tests/ -q` after all tasks: **505 passed, 6 skipped** (was 501 before this story).
- Live check (Docker container's own `reflex run` process, already up): `curl http://localhost:3000/dashboard` → 200, `curl http://localhost:3000/insights` → 200, container logs show a clean recompile after each `docker cp`, no server-side error. **Not verified:** the actual browser-rendered teaser card appearance or the `scrollIntoView` JS behavior — this environment has no headless-browser/CDP tool available, so only server-side compile/route/test verification was performed, not a visual/interactive check.

### Completion Notes List

- `top_active_insight` (Task 1) is a thin, deliberately read-only wrapper around the already-tested `_load_active` — no new ordering logic, no LLM call, no detector run. This was the central design decision from story creation (see Dev Notes "Why this is read-only") and it held up unchanged during implementation.
- `insights_state.py::load_insights` gained the `?highlight=` handling via a plain `return rx.call_script(...)` rather than the story's own Dev Notes' suggested `yield` — the function was not already an async generator, and introducing a bare `yield` would have turned its existing early `return rx.redirect(LOGIN_ROUTE)` into a `SyntaxError` (the exact bug class already fixed once this session in `dashboard_state.load_dashboard`, Epic 5). Restructuring to read the param and `return` the scroll event after the `with rx.session()` block closes achieves the identical effect with strictly less risk — a deliberate, justified deviation from the story's literal Dev Notes text, not an oversight.
- `card.id.to_string()` (Task 4) worked inline on the first attempt — the story's own Dev Notes had hedged that a precomputed `dom_id` field on `InsightCardView` might be needed if this didn't "render cleanly," but `reflex compile --dry` confirmed it does, so no extra field was added (avoids an unused field the story didn't strictly require).
- The Dashboard's pre-existing "See my insights →" button (`_briefing_card`, Story 5.3) is untouched — confirmed by diff review that only one new component (`_insight_teaser`) and one new sibling call site were added to `dashboard.py`, nothing inside `_briefing_card` itself changed.

### File List

- `finance_app/state/insights_bridge.py` (extended) — new `top_active_insight(session, user_id) -> Insight | None`, added to `__all__`.
- `finance_app/state/dashboard_state.py` (extended) — 4 new fields (`has_top_insight`, `top_insight_pattern_name`, `top_insight_observation`, `top_insight_href`), new `_apply_top_insight` helper, wired into `load_dashboard` and `_reset_to_empty`.
- `finance_app/pages/dashboard.py` (extended) — new `_insight_teaser()` component, new `rx.cond(...)` call site as a sibling of `dash-grid`.
- `finance_app/state/insights_state.py` (extended) — new `highlight_id` field; `load_insights` reads `?highlight=` and returns a `rx.call_script(...)` scroll event when set.
- `finance_app/pages/insights.py` (extended) — `_insight_card`'s outer `article` gains `id="insight-" + card.id.to_string()`.
- `tests/test_insights_bridge.py` (extended) — new `TestTopActiveInsight` class, 4 tests.

### Change Log

- 2026-07-11 — Story file created (`bmad-create-story`), scoped as a small, purely-additive UI story off Story 7.3's completed bridge/page. Status → `ready-for-dev`.
- 2026-07-11 — Implemented Tasks 1–6 test-first (`top_active_insight` red via `ImportError` before the function existed, green after). Full-repo suite: 505 passed, 6 skipped, 0 failed; `reflex compile --dry` succeeds; live container routes `/dashboard` and `/insights` both return HTTP 200 with no server-side error (browser-level visual/JS verification not performed — no CDP tool available in this environment). Status → `review`.
- 2026-07-12 — Code review patches applied: (F1) added `test_cannot_see_another_users_insight` IDOR isolation test to `TestTopActiveInsight` — 5 tests now; (F2) replaced `rx.cond(..., _insight_teaser(), rx.el.div())` with 2-arg `rx.cond(..., _insight_teaser())` to avoid phantom empty DOM node when no insights exist. Deferred: hydration-race on `scrollIntoView` (no-crash, silent no-op — not patchable without Reflex lifecycle hooks outside story scope). Status → `done`.
