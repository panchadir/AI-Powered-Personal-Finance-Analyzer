# --- appended to _harness.py -------------------------------------------------
"""Composite: the DB portion of each handler exactly as the handler calls it, at each volume.

Mirrors dashboard_state.load_dashboard (lines 273-293) and insights_state (line 176) so the
per-handler DB budget is measured, not summed from parts. LLM calls are excluded here and
measured separately -- see results/llm.json.
"""
import sys

from finance_app.state import engine_bridge, insights_bridge
from finance_app.state.engine_bridge import (
    compute_dashboard,
    load_commitments,
    load_transactions,
    recent_score_events,
    sync_confidence_score,
)

CLEANUP = "--cleanup" in sys.argv
out = {"volumes": {}}

with rx.session() as s:
    uid = get_perf_user(s)
    ensure_commitments(s, uid)

# stub the narrator: this measures the DB portion only
_real = insights_bridge.generate_insight_narration
from services.narrate.insight_narrator import build_fallback_insight_narration  # noqa: E402

insights_bridge.generate_insight_narration = build_fallback_insight_narration

for n in [100, 1000, 5000, 20000]:
    with rx.session() as s:
        set_transaction_count(s, uid, n)
        clear_derived(s, uid)

    def dashboard_db_path():
        """Exactly what DashboardState.load_dashboard does, minus the LLM + the 0.8s sleep."""
        with rx.session() as session:
            data = compute_dashboard(session, uid)          # full txn load #1
            event = sync_confidence_score(
                session, uid, data.evidence, trigger_event="dashboard_view"
            )
            recent_score_events(session, uid)
            load_transactions(session, uid)                  # full txn load #2 (DUPLICATE)
            load_commitments(session, uid)                   # commitments load #2 (DUPLICATE)
            return data

    t = timeit(dashboard_db_path, runs=5)
    with count_queries() as q:
        dashboard_db_path()
    t["sql"] = summarize_queries(list(q))

    def insights_db_path():
        with rx.session() as session:
            return insights_bridge.refresh_insights(session, uid)

    with rx.session() as s:
        clear_derived(s, uid)
    t2c = time.perf_counter()
    with count_queries() as q2:
        insights_db_path()
    first_ms = (time.perf_counter() - t2c) * 1000
    first_sql = summarize_queries(list(q2))

    t2 = timeit(insights_db_path, runs=3)
    with count_queries() as q2b:
        insights_db_path()
    t2["sql"] = summarize_queries(list(q2b))

    out["volumes"][str(n)] = {
        "dashboard_db_path": t,
        "insights_db_path_steady": t2,
        "insights_db_path_first_run_ms": round(first_ms, 1),
        "insights_db_path_first_run_sql": first_sql,
    }
    print(
        f"[composite] {n}: dashboard {t['warm_p50_ms']:.0f}ms/{t['sql']['total']}q | "
        f"insights(first) {first_ms:.0f}ms/{first_sql['total']}q",
        file=sys.stderr,
    )

insights_bridge.generate_insight_narration = _real

if CLEANUP:
    with rx.session() as s:
        cleanup(s, uid)
        n = s.exec(
            text("SELECT count(*) FROM transactions WHERE user_id = :u").bindparams(u=uid)
        ).one()
    out["cleanup"] = {"perf_user_id": uid, "remaining_rows": n[0] if isinstance(n, tuple) else n}
    print(f"[cleanup] perf user {uid} rows now: {out['cleanup']['remaining_rows']}", file=sys.stderr)

# Sanity: confirm the demo user (id=2) was never touched.
with rx.session() as s:
    demo = s.exec(
        text("SELECT count(*) FROM transactions WHERE user_id = 2")
    ).one()
out["demo_user_2_txn_count"] = demo[0] if isinstance(demo, tuple) else demo
print(f"[check] demo user_id=2 txn count: {out['demo_user_2_txn_count']}", file=sys.stderr)

emit(out)
