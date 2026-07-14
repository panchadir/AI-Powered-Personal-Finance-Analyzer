# --- appended to _harness.py and piped into the container -------------------
"""Scale curve + SQL query counts for every engine/detector/bridge service call.

For each row-volume, times the DB-backed bridge functions and the pure engine functions,
and counts the SQL statements each issues -- the N+1 test.
"""
import sys

from finance_app.state import engine_bridge, insights_bridge
from services.categorize.rules import categorize_rules
from services.engine import (
    build_engine_input,
    compute_confidence_score,
    compute_safe_to_spend,
    detect_recurring_commitments,
)
from services.engine.insights import run_all_detectors
from services.analytics import monthly_spend, spending_by_category
from services.ingestion.persist import persist_transactions

VOLUMES = [int(x) for x in (sys.argv[1:] or ["100", "1000", "5000", "20000"])]

results = {"volumes": {}, "notes": []}

with rx.session() as s:
    uid = get_perf_user(s)
    ensure_commitments(s, uid)
results["user_id"] = uid

# The narrator makes a live billed LLM call per candidate. For the SQL/scale measurement we
# stub it so we measure the *database* behaviour of refresh_insights in isolation; the real
# LLM latency is measured separately (run_llm.py), at most 3 samples.
_narration_calls = {"n": 0}
_real_narrator = insights_bridge.generate_insight_narration


def _stub_narration(inp):
    _narration_calls["n"] += 1
    from services.narrate.insight_narrator import build_fallback_insight_narration

    return build_fallback_insight_narration(inp)


insights_bridge.generate_insight_narration = _stub_narration

for n in VOLUMES:
    with rx.session() as s:
        actual = set_transaction_count(s, uid, n)
        clear_derived(s, uid)

    vol = {"rows": actual, "functions": {}}

    def record(name, fn, runs=5):
        with rx.session() as s:
            pass
        timing = timeit(fn, runs=runs)
        with count_queries() as q:
            fn()
        timing["sql"] = summarize_queries(list(q))
        vol["functions"][name] = timing
        return timing

    # ---- DB-backed bridge functions (the real request path) ----
    def _load_txns():
        with rx.session() as s:
            return engine_bridge.load_transactions(s, uid)

    record("engine_bridge.load_transactions", _load_txns)

    def _compute_dashboard():
        with rx.session() as s:
            return engine_bridge.compute_dashboard(s, uid)

    record("engine_bridge.compute_dashboard", _compute_dashboard)

    def _detect_candidates():
        with rx.session() as s:
            return engine_bridge.detect_commitment_candidates(s, uid)

    record("engine_bridge.detect_commitment_candidates", _detect_candidates)

    def _load_insight_ctx():
        with rx.session() as s:
            return insights_bridge.load_insight_context(s, uid)

    record("insights_bridge.load_insight_context", _load_insight_ctx)

    # refresh_insights: first call inserts rows (the expensive path), subsequent calls
    # hit the "unchanged -> leave alone" branch. Measure BOTH: cold-insert vs steady-state.
    with rx.session() as s:
        clear_derived(s, uid)
    _narration_calls["n"] = 0
    t = time.perf_counter()
    with count_queries() as q:
        with rx.session() as s:
            insights_bridge.refresh_insights(s, uid)
    first_ms = (time.perf_counter() - t) * 1000
    first_sql = summarize_queries(list(q))
    first_narrations = _narration_calls["n"]

    def _refresh():
        with rx.session() as s:
            return insights_bridge.refresh_insights(s, uid)

    steady = timeit(_refresh, runs=3)
    with count_queries() as q:
        _refresh()
    steady["sql"] = summarize_queries(list(q))
    vol["functions"]["insights_bridge.refresh_insights (steady-state)"] = steady
    vol["functions"]["insights_bridge.refresh_insights (first run, inserts)"] = {
        "cold_ms": round(first_ms, 2),
        "warm_p50_ms": round(first_ms, 2),
        "warm_max_ms": round(first_ms, 2),
        "sql": first_sql,
        "llm_narration_calls_STUBBED": first_narrations,
        "note": "narrator stubbed; each of these would be a real Opus call in production",
    }

    # ---- pure engine functions (no DB) ----
    with rx.session() as s:
        txns = engine_bridge.load_transactions(s, uid)
        commits = engine_bridge.to_commitment_records(engine_bridge.load_commitments(s, uid))
        ctx = insights_bridge.load_insight_context(s, uid)

    ei = build_engine_input(txns, commits)
    ev = compute_safe_to_spend(ei)

    record("engine.build_engine_input (pure)", lambda: build_engine_input(txns, commits), runs=7)
    record("engine.compute_safe_to_spend (pure)", lambda: compute_safe_to_spend(ei), runs=7)
    record(
        "engine.compute_confidence_score (pure)",
        lambda: compute_confidence_score(ev, previous_score=50),
        runs=7,
    )
    record(
        "engine.detect_recurring_commitments (pure)",
        lambda: detect_recurring_commitments(txns),
        runs=7,
    )
    record("insights.run_all_detectors (pure)", lambda: run_all_detectors(ctx), runs=7)
    record("categorize.categorize_rules (pure)", lambda: categorize_rules(txns), runs=5)
    record("analytics.spending_by_category (pure)", lambda: spending_by_category(txns), runs=7)
    record("analytics.monthly_spend (pure)", lambda: monthly_spend(txns), runs=7)

    # ---- persist_transactions: the upload path's dedup read ----
    # Re-persisting the same rows exercises the "read every existing key" path with 0 inserts.
    def _persist():
        with rx.session() as s:
            return persist_transactions(s, TxnModel, uid, None, txns[:50])

    record("ingestion.persist_transactions (50 new rows vs existing)", _persist, runs=3)

    results["volumes"][str(n)] = vol
    print(f"[done] {n} rows", file=sys.stderr)

insights_bridge.generate_insight_narration = _real_narrator

emit(results)
