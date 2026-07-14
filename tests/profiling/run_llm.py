# --- appended to _harness.py -------------------------------------------------
"""LLM latency: TTFT vs full completion, timeout config, retry behaviour.

BILLED, LIVE CALLS. Hard cap: 3 samples per function.
"""
import asyncio
import os
from datetime import date

import anthropic

from finance_app.state import engine_bridge
from finance_app.state.copilot_data import open_copilot_data
from services.narrate.briefing import BriefingContext, generate_briefing
from services.narrate.copilot import astream_events
from services.narrate.insight_narrator import (
    InsightNarrationInput,
    NarrationEvidencePoint,
    generate_insight_narration,
)
from services.categorize.llm_categorizer import ClaudeCategorizer
from services.categorize.schema import UNCATEGORIZED
from services.engine.insights import run_all_detectors
from finance_app.state import insights_bridge

SAMPLES = 3
out = {"samples_per_fn": SAMPLES}

# ---- 0. Client configuration, as constructed by the app (no timeout= is passed) ----
c = anthropic.Anthropic()
ac = anthropic.AsyncAnthropic()
out["client_config"] = {
    "sync_timeout": str(c.timeout),
    "sync_max_retries": c.max_retries,
    "async_timeout": str(ac.timeout),
    "async_max_retries": ac.max_retries,
    "note": "these are the SDK DEFAULTS -- no timeout= or max_retries= is passed anywhere in services/narrate or services/categorize",
}
out["worst_case_seconds"] = {
    "single_attempt_read_timeout": 600,
    "attempts": 1 + c.max_retries,
    "unbounded_worst_case": 600 * (1 + c.max_retries),
}

# Use a realistic single-statement volume (100 rows) so we time the LLM, not the DB.
with rx.session() as s:
    uid = get_perf_user(s)
    ensure_commitments(s, uid)
    set_transaction_count(s, uid, 100)
    clear_derived(s, uid)

with rx.session() as s:
    data = engine_bridge.compute_dashboard(s, uid)
    ctx = insights_bridge.load_insight_context(s, uid)

candidates = run_all_detectors(ctx)
out["insight_candidates_at_100_rows"] = len(candidates)


def sample(label, fn, n=SAMPLES):
    times, errs = [], []
    for _ in range(n):
        t = time.perf_counter()
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            errs.append(repr(e))
        times.append((time.perf_counter() - t) * 1000)
    out[label] = {
        "samples_ms": [round(x, 1) for x in times],
        "min_ms": round(min(times), 1),
        "p50_ms": round(statistics.median(times), 1),
        "max_ms": round(max(times), 1),
        "errors": errs,
    }
    print(f"[llm] {label}: {[round(x) for x in times]}", file=sys.stderr)


import sys  # noqa: E402

# ---- 1. Briefing (Opus, non-streaming, blocking) ------------------------------
_ev = data.evidence
bctx = BriefingContext(  # mirrors DashboardState._briefing_context
    safe_to_spend_today=engine_bridge.format_money(_ev.safe_to_spend_today),
    statement_end_date=engine_bridge.format_day(data.statement_end_date),
    prediction_confidence=_ev.prediction_confidence,
    reserved_total=engine_bridge.format_money(_ev.reserved_total),
    safe_to_spend_after_income=engine_bridge.format_money(_ev.safe_to_spend_after_income)
    if _ev.safe_to_spend_after_income is not None
    else None,
    next_income_date=engine_bridge.format_day(data.next_income_date),
    days_to_income=_ev.days_to_income,
    safety_ok=_ev.safety_ok,
    drivers=_ev.drivers,
)
sample("generate_briefing (Opus, blocking)", lambda: generate_briefing(bctx))

# ---- 2. Insight narration (Opus, non-streaming) -- called ONCE PER CANDIDATE ----
cand = candidates[0]
narr_in = InsightNarrationInput(
    pattern_name=cand.pattern_name,
    severity=cand.severity,
    evidence=tuple(
        NarrationEvidencePoint(date=e.date, merchant=e.merchant, amount=e.amount)
        for e in cand.evidence
    ),
    metrics=cand.metrics,
    data_months=cand.data_months,
    tone=cand.tone,
)
sample("generate_insight_narration (Opus, blocking, x1)", lambda: generate_insight_narration(narr_in))

# ---- 3. Tier-2 LLM categorizer (Haiku, batch) ---------------------------------
with rx.session() as s:
    txns = engine_bridge.load_transactions(s, uid)
# The categorizer only touches rows the rule tier left UNCATEGORIZED -- mark them so, or the
# call is a no-op and we'd be timing nothing.
batch = [t.with_fields(category=UNCATEGORIZED) for t in txns[:15]]
cat = ClaudeCategorizer(anthropic.Anthropic())
sample("llm_categorizer.categorize (Haiku, 15-txn batch)", lambda: cat.categorize(batch))


# ---- 4. Copilot streaming: TTFT vs full completion -----------------------------
async def _copilot_once(question: str):
    t0 = time.perf_counter()
    ttft = None
    tool_rounds = 0
    n_tokens = 0
    async for ev in astream_events(
        [{"role": "user", "content": question}],
        user_id=uid,
        data_factory=lambda: open_copilot_data(uid),
    ):
        if ev.get("type") == "token":
            if ttft is None:
                ttft = (time.perf_counter() - t0) * 1000
            n_tokens += 1
        if ev.get("type") == "trace":
            tool_rounds = len(ev.get("sources", []) or [])
    total = (time.perf_counter() - t0) * 1000
    return {
        "ttft_ms": round(ttft, 1) if ttft else None,
        "total_ms": round(total, 1),
        "token_events": n_tokens,
        "tools_called": tool_rounds,
    }


async def _copilot_suite():
    res = []
    # A tool-using question (the realistic case) -- forces >=2 sequential Opus round-trips.
    for q in [
        "How much can I safely spend today?",
        "What are my biggest spending categories and any subscriptions I forgot?",
        "Hi",  # no tools -- the cheap path, for contrast
    ]:
        r = await _copilot_once(q)
        r["question"] = q
        print(f"[llm] copilot {q!r}: {r}", file=sys.stderr)
        res.append(r)
    return res


out["copilot_astream_events (Opus, streaming)"] = asyncio.run(_copilot_suite())

emit(out)
