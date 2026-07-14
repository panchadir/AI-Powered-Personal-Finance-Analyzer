# --- appended to _harness.py -------------------------------------------------
"""EXPLAIN (ANALYZE, BUFFERS) on the real query the code issues, + cProfile hotspots."""
import cProfile
import io
import pstats
import sys

from finance_app.state import engine_bridge, insights_bridge
from services.categorize.rules import categorize_rules
from services.engine.insights import run_all_detectors

out = {}

with rx.session() as s:
    uid = get_perf_user(s)
    n = s.exec(
        text("SELECT count(*) FROM transactions WHERE user_id = :u").bindparams(u=uid)
    ).one()
    out["rows_at_measurement"] = n[0] if isinstance(n, tuple) else n

# ---- 1. The exact SQL engine_bridge.load_transactions issues -------------------
# (from engine_bridge.py:load_transactions -> select(Txn).where(user_id==).order_by(date))
REAL_QUERY = """
SELECT transactions.id, transactions.user_id, transactions.source_file_id, transactions.date,
       transactions.description_raw, transactions.merchant_normalized, transactions.amount,
       transactions.direction, transactions.balance_after, transactions.category,
       transactions.category_source, transactions.category_confidence, transactions.reasoning,
       transactions.created_at
FROM transactions
WHERE transactions.user_id = %(uid)s
ORDER BY transactions.date
"""

with rx.session() as s:
    plan = s.exec(
        text("EXPLAIN (ANALYZE, BUFFERS, COSTS) " + REAL_QUERY.replace("%(uid)s", str(uid)))
    ).all()
    out["explain_load_transactions"] = [r[0] for r in plan]

    idx = s.exec(
        text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename='transactions'")
    ).all()
    out["indexes"] = [list(r) for r in idx]

    # The Copilot's query_transactions -- filters user_id, orders by date DESC, LIMIT 20.
    plan2 = s.exec(
        text(
            "EXPLAIN (ANALYZE, BUFFERS, COSTS) SELECT * FROM transactions "
            f"WHERE user_id = {uid} ORDER BY date DESC LIMIT 20"
        )
    ).all()
    out["explain_copilot_query_transactions_limit20"] = [r[0] for r in plan2]

    # What the same query would cost WITH a composite index -- measured, not guessed.
    s.exec(text(f"CREATE INDEX IF NOT EXISTS ix_perf_tmp_user_date ON transactions (user_id, date)"))
    s.commit()
    s.exec(text("ANALYZE transactions"))
    plan3 = s.exec(
        text("EXPLAIN (ANALYZE, BUFFERS, COSTS) " + REAL_QUERY.replace("%(uid)s", str(uid)))
    ).all()
    out["explain_load_transactions_WITH_composite_index"] = [r[0] for r in plan3]
    plan4 = s.exec(
        text(
            "EXPLAIN (ANALYZE, BUFFERS, COSTS) SELECT * FROM transactions "
            f"WHERE user_id = {uid} ORDER BY date DESC LIMIT 20"
        )
    ).all()
    out["explain_copilot_limit20_WITH_composite_index"] = [r[0] for r in plan4]


# Time load_transactions WITH the index present, to see if it actually helps.
def _load():
    with rx.session() as s:
        return engine_bridge.load_transactions(s, uid)


out["load_transactions_WITH_index"] = timeit(_load, runs=5)

with rx.session() as s:
    s.exec(text("DROP INDEX IF EXISTS ix_perf_tmp_user_date"))
    s.commit()
    s.exec(text("ANALYZE transactions"))

out["load_transactions_WITHOUT_index"] = timeit(_load, runs=5)


# ---- 2. cProfile the slowest functions ----------------------------------------
def top_frames(fn, label, n=12):
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(3):
        fn()
    pr.disable()
    sio = io.StringIO()
    st = pstats.Stats(pr, stream=sio).sort_stats("cumulative")
    st.print_stats(n)
    return sio.getvalue()


def _dash():
    with rx.session() as s:
        return engine_bridge.compute_dashboard(s, uid)


with rx.session() as s:
    txns = engine_bridge.load_transactions(s, uid)
    ctx = insights_bridge.load_insight_context(s, uid)

out["cprofile_compute_dashboard"] = top_frames(_dash, "compute_dashboard")
out["cprofile_load_transactions"] = top_frames(_load, "load_transactions")
out["cprofile_categorize_rules"] = top_frames(lambda: categorize_rules(txns), "categorize_rules")
out["cprofile_run_all_detectors"] = top_frames(lambda: run_all_detectors(ctx), "run_all_detectors")

emit(out)
