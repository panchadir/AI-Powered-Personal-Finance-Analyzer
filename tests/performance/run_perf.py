"""Phase runner for the Reflex perf harness. Run INSIDE the container.

    docker compose exec -T app python /app/run_perf.py --phase baseline
    docker compose exec -T app python /app/run_perf.py --phase scale --rows 5000
    docker compose exec -T app python /app/run_perf.py --phase concurrency
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from perf_harness import (  # noqa: E402
    AUTH, AUTH as _A, BUDGET_MS, COMMIT, COPILOT, DASH, DEMO_EMAIL, DEMO_PASSWORD,
    INSIGHTS, LOGIN, REGISTER, RESULTS_DIR, ROOT, TXNS, UPLOAD,
    ReflexClient, Result, Sample, find_var, measure, read_handlers, sentinel_baseline,
    txn_count, v_commitments, v_copilot_history, v_dashboard, v_delta, v_insights,
    v_login, v_send_message, v_transactions,
)

DEMO_UID = 2


def save(name: str, payload: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    p = RESULTS_DIR / name
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n[saved] {p}")


def dump(results: list[Result]) -> list[dict]:
    return [{"handler": r.handler, "method": r.method, "note": r.note, "error": r.error,
             "stats": r.stats(), "samples": [vars(s) for s in r.samples]} for r in results]


# ============================================================ BASELINE
async def phase_baseline(n_cheap: int, n_llm: int) -> dict:
    rows = txn_count(DEMO_UID)
    print(f"\n=== BASELINE (user_id={DEMO_UID}, transactions={rows}) ===")
    c = ReflexClient()
    await c.connect()
    base = await sentinel_baseline(c)
    print(f"  sentinel overhead (harness+net+framework): p50={base['p50']}ms max={base['max']}ms\n")

    results: list[Result] = []

    # --- handle_login on a FRESH unauthenticated socket each sample ---
    rlogin = Result("LoginState.handle_login", "socket.io /_event (real E2E)",
                    note="fresh unauthenticated socket per sample; bcrypt verify")
    for _ in range(n_cheap):
        cc = ReflexClient(path="/login")
        await cc.connect()
        ms, ups, first = await cc.run(
            f"{LOGIN}.handle_login",
            {"form_data": {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}}, "/login")
        ok, ev = v_login(ups)
        rlogin.samples.append(Sample(ms=ms, ok=ok, evidence=ev, deltas=len(ups), first_delta_ms=first))
        await cc.close()
    s = rlogin.stats()
    print(f"  {'LoginState.handle_login':<36} n={s['n']:<3} p50={s['p50']:>8.1f} p95={s['p95']:>8.1f} "
          f"max={s['max']:>8.1f} {'PASS' if s['pass'] else 'FAIL'} | {s['evidence'][:50]}")
    results.append(rlogin)

    await c.login()
    print("  [authenticated as demo@example.com uid=2]")

    def v_check_auth(ups):
        """check_auth returns None (no delta) when the session IS valid; it emits a
        _redirect event when it is NOT. So a redirect means we measured the fast
        unauthenticated bail-out -- a FALSE PASS. Assert the redirect is absent."""
        for u in ups:
            for e in (u.get("events") or []):
                if e.get("name") == "_redirect":
                    return False, f"REDIRECTED to {e.get('payload', {}).get('path')} => NOT authenticated"
        return True, "no _redirect => session valid (user_for_token DB lookup succeeded)"

    results.append(await measure(
        c, "AuthState.check_auth", f"{AUTH}.check_auth", {}, v_check_auth,
        n_cheap, "/dashboard",
        note="returns None when authed; verified by ABSENCE of a _redirect event"))

    async def reg_setup(cl, i):
        return {"form_data": {"email": f"perf-{uuid.uuid4().hex[:10]}@example.com",
                              "password": "perftest12345", "confirm_password": "perftest12345"}}
    results.append(await measure(
        c, "RegisterState.handle_registration", f"{REGISTER}.handle_registration", {},
        v_delta(REGISTER, "registration_success", "registered"), n_cheap, "/register",
        setup=reg_setup, note="throwaway perf-* user per sample; bcrypt HASH (cost factor)"))

    forgot_email = f"perf-forgot-{uuid.uuid4().hex[:8]}@example.com"
    await c.fire(f"{REGISTER}.handle_registration",
                 {"form_data": {"email": forgot_email, "password": "perftest12345",
                                "confirm_password": "perftest12345"}}, "/register")
    results.append(await measure(
        c, "LoginState.handle_forgot", f"{LOGIN}.handle_forgot",
        {"form_data": {"email": forgot_email, "new_password": "perftest99999",
                       "confirm_password": "perftest99999"}},
        v_delta(LOGIN, "reset_notice", "notice"), n_cheap, "/login",
        note="targets a THROWAWAY user, never demo@example.com; bcrypt HASH"))

    # --- read handlers ---
    results += await read_handlers(c, n_cheap, n_llm, "baseline")

    # --- transactions cheap handlers ---
    ups = await c.fire(f"{TXNS}.load_transactions", {}, "/transactions")
    rws = find_var(ups, TXNS, "rows") or []
    row_ids = [r.get("id_rx_state_", r.get("id")) for r in rws][:60]
    print(f"  [{len(rws)} txn rows available for toggle_row / save_correction]")

    filters = ["all", "essentials", "discretionary", "income"]

    async def filt_setup(cl, i):
        return {"key": filters[i % len(filters)]}
    results.append(await measure(
        c, "TransactionsState.set_filter", f"{TXNS}.set_filter", {},
        v_delta(TXNS, "active_filter", "filter"), n_cheap, "/transactions", setup=filt_setup))

    async def toggle_setup(cl, i):
        if not row_ids:
            return None
        await cl.fire(f"{TXNS}.toggle_row", {"row_id": row_ids[(i + 1) % len(row_ids)]}, "/transactions")
        return {"row_id": row_ids[i % len(row_ids)]}
    results.append(await measure(
        c, "TransactionsState.toggle_row", f"{TXNS}.toggle_row", {},
        v_delta(TXNS, "open_row_id", "open_row"), n_cheap, "/transactions", setup=toggle_setup))

    # MUST be real members of services.categorize.schema.CATEGORIES -- select_category
    # silently ignores anything else, which would make save_correction a no-op (false PASS).
    cats = ["Groceries", "Travel & Transport", "Food & Dining", "Shopping"]

    async def corr_setup(cl, i):
        if not row_ids:
            return None
        await cl.fire(f"{TXNS}.toggle_row", {"row_id": row_ids[i % len(row_ids)]}, "/transactions")
        await cl.fire(f"{TXNS}.select_category", {"category": cats[i % len(cats)]}, "/transactions")
        return {}
    results.append(await measure(
        c, "TransactionsState.save_correction", f"{TXNS}.save_correction", {},
        v_delta(TXNS, "confirmation", "confirm"), n_cheap, "/transactions", setup=corr_setup,
        note="INSERT merchant_rule + optional re-apply UPDATE across all matching txns"))

    # --- insights dismiss (real ids only) ---
    ups = await c.fire(f"{INSIGHTS}.load_insights", {}, "/insights", timeout=240)
    cards = (find_var(ups, INSIGHTS, "cards") or []) + (find_var(ups, INSIGHTS, "win_cards") or [])
    ins_ids = [x.get("id_rx_state_", x.get("id")) for x in cards]
    print(f"  [{len(ins_ids)} active insights available to dismiss]")
    if not ins_ids:
        r = Result("InsightsState.dismiss", "socket.io /_event (real E2E)")
        r.error = "user_id=2 has 0 active insights -> NOT DRIVEABLE without fabricating data"
        print(f"  {'InsightsState.dismiss':<36} NOT DRIVEABLE (0 active insights)")
        results.append(r)
    else:
        async def dis_setup(cl, i):
            return {"insight_id": ins_ids[i]} if i < len(ins_ids) else None
        results.append(await measure(
            c, "InsightsState.dismiss", f"{INSIGHTS}.dismiss", {},
            v_delta(INSIGHTS, "cards", "cards"), min(n_cheap, len(ins_ids)), "/insights",
            setup=dis_setup, note=f"n capped at {len(ins_ids)} = number of REAL active insights"))

    # --- commitments: add N then delete the same N (net-zero on the dataset) ---
    async def savec_setup(cl, i):
        await cl.fire(f"{COMMIT}.open_add", {}, "/commitments")
        await cl.fire(f"{COMMIT}.set_form_name", {"value": f"PERF-{uuid.uuid4().hex[:6]}"}, "/commitments")
        await cl.fire(f"{COMMIT}.set_form_amount", {"value": "1234.00"}, "/commitments")
        await cl.fire(f"{COMMIT}.set_form_due_day", {"value": "12"}, "/commitments")
        await cl.fire(f"{COMMIT}.set_criticality", {"value": "flexible"}, "/commitments")
        return {}
    results.append(await measure(
        c, "CommitmentsState.save_commitment", f"{COMMIT}.save_commitment", {},
        v_commitments, n_cheap, "/commitments", setup=savec_setup,
        note="INSERT + _refresh (compute_dashboard + detect_commitment_candidates)"))

    ups = await c.fire(f"{COMMIT}.load_commitments_page", {}, "/commitments")
    sugg = find_var(ups, COMMIT, "suggestions") or []
    sigs = [x.get("signature_rx_state_", x.get("signature")) for x in sugg]
    if not sigs:
        r = Result("CommitmentsState.confirm_suggestion", "socket.io /_event (real E2E)")
        r.error = ("detect_commitment_candidates() returns 0 candidates for user_id=2 "
                   "-> NOT DRIVEABLE without fabricating data")
        print(f"  {'CommitmentsState.confirm_suggestion':<36} NOT DRIVEABLE (0 suggestions)")
        results.append(r)
    else:
        async def cs_setup(cl, i):
            return {"signature": sigs[i]} if i < len(sigs) else None
        results.append(await measure(
            c, "CommitmentsState.confirm_suggestion", f"{COMMIT}.confirm_suggestion", {},
            v_commitments, min(n_cheap, len(sigs)), "/commitments", setup=cs_setup,
            note=f"n capped at {len(sigs)} = REAL detected recurring-charge suggestions"))

    ups = await c.fire(f"{COMMIT}.load_commitments_page", {}, "/commitments")
    coms = find_var(ups, COMMIT, "commitments") or []
    perf_ids = [x.get("id_rx_state_", x.get("id")) for x in coms
                if str(x.get("name_rx_state_", x.get("name", ""))).startswith("PERF-")]
    print(f"  [{len(perf_ids)} PERF-* commitments queued for delete]")
    if perf_ids:
        async def del_setup(cl, i):
            if i >= len(perf_ids):
                return None
            await cl.fire(f"{COMMIT}.open_delete", {"commitment_id": perf_ids[i]}, "/commitments")
            return {}
        results.append(await measure(
            c, "CommitmentsState.confirm_delete", f"{COMMIT}.confirm_delete", {},
            v_commitments, len(perf_ids), "/commitments", setup=del_setup,
            note="DELETE + _refresh; also cleans up the PERF-* rows save_commitment created"))
    else:
        r = Result("CommitmentsState.confirm_delete", "socket.io /_event (real E2E)")
        r.error = "no PERF-* commitments were created to delete"
        results.append(r)

    # --- copilot ---
    # load_history is guarded by `_history_loaded`, so it only touches the DB on the FIRST
    # call per session. Re-calling it on the same socket is a no-op and would measure ~0ms
    # of nothing (a false PASS). Use a fresh authenticated socket for every sample.
    rlh = Result("CopilotState.load_history", "socket.io /_event (real E2E)",
                 note="fresh authenticated socket per sample: `_history_loaded` makes "
                      "repeat calls on one session a no-op")
    for _ in range(n_cheap):
        cc = ReflexClient(path="/copilot")
        await cc.connect()
        await cc.login()
        ms, ups, first = await cc.run(f"{COPILOT}.load_history", {}, "/copilot")
        ok, ev = v_copilot_history(ups)
        rlh.samples.append(Sample(ms=ms, ok=ok, evidence=ev, deltas=len(ups), first_delta_ms=first))
        await cc.close()
    s = rlh.stats()
    print(f"  {'CopilotState.load_history':<36} n={s['n']:<3} p50={s['p50']:>8.1f} p95={s['p95']:>8.1f} "
          f"max={s['max']:>8.1f} {'PASS' if s['pass'] else 'FAIL'} | {s['evidence'][:50]}")
    results.append(rlh)

    qs = ["How much can I safely spend today?", "What did I spend most on last month?",
          "Am I on track this month?", "Summarise my subscriptions."]

    async def sm_setup(cl, i):
        await cl.fire(f"{COPILOT}.load_history", {}, "/copilot")   # sets has_transactions
        await cl.fire(f"{COPILOT}.set_input", {"value": qs[i % len(qs)]}, "/copilot")
        return {}
    results.append(await measure(
        c, "CopilotState.send_message", f"{COPILOT}.send_message", {},
        v_send_message, n_llm, "/copilot", setup=sm_setup, timeout=240,
        note="REAL streaming LLM call with agentic tool loop over CopilotData"))

    await c.close()
    return {"phase": "baseline", "user_id": DEMO_UID, "rows": rows,
            "sentinel_overhead_ms": base, "results": dump(results)}


# ============================================================ UPLOAD (HTTP /_upload)
SAMPLE_CSV = (
    "Date,Description,Debit,Credit,Balance\n"
    "01/06/2026,SALARY CREDIT ACME CORP,,85000.00,120000.00\n"
    "02/06/2026,BIG BAZAAR GROCERIES,3250.50,,116749.50\n"
    "03/06/2026,UBER RIDE,420.00,,116329.50\n"
    "04/06/2026,NETFLIX SUBSCRIPTION,649.00,,115680.50\n"
    "05/06/2026,SWIGGY ORDER,780.25,,114900.25\n"
    "06/06/2026,ELECTRICITY BILL,2100.00,,112800.25\n"
    "07/06/2026,AMAZON SHOPPING,1899.00,,110901.25\n"
    "08/06/2026,PETROL PUMP HP,2500.00,,108401.25\n"
)


async def phase_upload(n: int) -> dict:
    """Reflex file upload is an HTTP POST to /_upload, not a socket event."""
    import httpx
    print(f"\n=== UPLOAD (/_upload HTTP endpoint) rows_before={txn_count(DEMO_UID)} ===")
    c = ReflexClient(path="/upload")
    await c.connect()
    await c.login()
    r = Result("UploadState.handle_upload", "HTTP POST /_upload (streamed deltas)",
               note="parse_statement + Tier-1 rules + Tier-2 Claude categorizer + bulk INSERT")
    for i in range(n):
        files = {"files": (f"perf-{i}.csv", SAMPLE_CSV.encode(), "text/csv")}
        headers = {"reflex-client-token": c.token,
                   "reflex-event-handler": f"{UPLOAD}.handle_upload"}
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=300) as h:
                resp = await h.post(f"http://localhost:8000/_upload", files=files, headers=headers)
            ms = (time.perf_counter() - t0) * 1000
            body = resp.text
            ok = resp.status_code == 200 and ("summary" in body or "total" in body or "done_steps" in body)
            ev = f"HTTP {resp.status_code}, {len(body)}B streamed"
            r.samples.append(Sample(ms=ms, ok=ok, evidence=ev, deltas=body.count("delta")))
            print(f"    upload sample {i}: {ms:.1f}ms  {ev}")
        except Exception as e:  # noqa: BLE001
            r.error = f"{type(e).__name__}: {e}"
            print(f"    upload sample {i} ERROR: {r.error}")
            break
    s = r.stats()
    if s.get("n"):
        print(f"  {'UploadState.handle_upload':<36} n={s['n']} p50={s['p50']:.1f} "
              f"p95={s['p95']:.1f} max={s['max']:.1f} {'PASS' if s['pass'] else 'FAIL'}")
    await c.close()
    return {"phase": "upload", "rows_after": txn_count(DEMO_UID), "results": dump([r])}


# ============================================================ SCALE
def seed(target: int, user_id: int = DEMO_UID) -> int:
    """Seed the demo user up to `target` transactions. Direct SQLModel bulk insert."""
    import datetime as dt
    import random
    from decimal import Decimal
    import sqlmodel
    from finance_app.models import Transaction, UploadedFile

    eng = sqlmodel.create_engine(os.environ["DATABASE_URL"])
    merchants = ["BIG BAZAAR", "SWIGGY", "UBER", "AMAZON", "NETFLIX", "HP PETROL",
                 "DMART", "ZOMATO", "FLIPKART", "JIO RECHARGE", "STARBUCKS", "IKEA"]
    cats = ["Groceries", "Dining", "Transport", "Shopping", "Subscriptions", "Utilities"]
    with sqlmodel.Session(eng) as s:
        cur = len(s.exec(sqlmodel.select(Transaction.id)
                         .where(Transaction.user_id == user_id)).all())
        need = target - cur
        if need <= 0:
            print(f"  [seed] already at {cur} rows (>= {target}); nothing to do")
            return cur
        sf = s.exec(sqlmodel.select(UploadedFile)
                    .where(UploadedFile.user_id == user_id)).first()
        if sf is None:
            sf = UploadedFile(user_id=user_id, filename="perf-scale.csv", status="parsed")
            s.add(sf)
            s.commit()
            s.refresh(sf)
        rnd = random.Random(1234)
        base = dt.date(2026, 6, 29)
        batch = []
        for i in range(need):
            m = merchants[i % len(merchants)]
            # `date` is a VARCHAR 'YYYY-MM-DD' column with NO index (see models.py).
            batch.append(Transaction(
                user_id=user_id, source_file_id=sf.id,
                date=(base - dt.timedelta(days=(i % 700))).isoformat(),
                description_raw=f"{m} PURCHASE REF{i:06d}",
                merchant_normalized=m,
                amount=Decimal(f"{rnd.randint(50, 4000)}.{rnd.randint(0, 99):02d}"),
                balance_after=Decimal("100000.00"),
                direction="debit",
                category=cats[i % len(cats)],
                category_source="rule",
            ))
            if len(batch) >= 1000:
                s.add_all(batch); s.commit(); batch = []
        if batch:
            s.add_all(batch); s.commit()
        total = len(s.exec(sqlmodel.select(Transaction.id)
                           .where(Transaction.user_id == user_id)).all())
    print(f"  [seed] user_id={user_id}: {cur} -> {total} transactions")
    return total


async def phase_scale(target: int, n_cheap: int, n_llm: int) -> dict:
    total = seed(target)
    print(f"\n=== SCALE (user_id={DEMO_UID}, transactions={total}) ===")
    c = ReflexClient()
    await c.connect()
    await c.login()
    base = await sentinel_baseline(c, 10)
    print(f"  sentinel overhead: p50={base['p50']}ms\n")
    results = await read_handlers(c, n_cheap, n_llm, f"scale{total}")
    await c.close()
    return {"phase": "scale", "user_id": DEMO_UID, "rows": total,
            "sentinel_overhead_ms": base, "results": dump(results)}


# ============================================================ CONCURRENCY
async def phase_concurrency(nclients: int) -> dict:
    rows = txn_count(DEMO_UID)
    print(f"\n=== CONCURRENCY (rows={rows}) ===")
    out: dict = {"phase": "concurrency", "rows": rows}

    # ---- TEST A: no-LLM handler. This is the CLEAN event-loop-blocking signal. ----
    # load_commitments_page is 100% synchronous psycopg2 + compute_dashboard, called
    # directly inside the async handler (no asyncio.to_thread). If the event loop is
    # blocked by that sync work, N concurrent clients must serialize: latency ~ N * serial.
    # If Reflex were servicing them concurrently, latency would stay ~flat.
    ca = ReflexClient(path="/commitments")
    await ca.connect()
    await ca.login()
    ser_c = []
    for _ in range(5):
        ms, ups, _ = await ca.run(f"{COMMIT}.load_commitments_page", {}, "/commitments", 240)
        ok, ev = v_commitments(ups)
        ser_c.append(ms)
    await ca.close()
    ser_c.sort()
    serial_c_p50 = statistics.median(ser_c)
    print(f"  SERIAL     load_commitments_page x5 (1 client): p50={serial_c_p50:.0f}ms")

    cc = [ReflexClient(path="/commitments") for _ in range(nclients)]
    await asyncio.gather(*(x.connect() for x in cc))
    await asyncio.gather(*(x.login() for x in cc))

    async def one_c(x):
        ms, ups, _ = await x.run(f"{COMMIT}.load_commitments_page", {}, "/commitments", 300)
        ok, ev = v_commitments(ups)
        return ms, ok, ev

    t0 = time.perf_counter()
    rc = await asyncio.gather(*(one_c(x) for x in cc))
    wall_c = (time.perf_counter() - t0) * 1000
    tc = sorted(r[0] for r in rc)
    conc_c_p50 = statistics.median(tc)
    print(f"  CONCURRENT load_commitments_page x{nclients}: p50={conc_c_p50:.0f}ms "
          f"max={tc[-1]:.0f}ms wall={wall_c:.0f}ms  "
          f"=> {conc_c_p50/serial_c_p50:.1f}x degradation vs serial")
    out["no_llm_event_loop_test"] = {
        "handler": "CommitmentsState.load_commitments_page (no LLM, pure sync DB)",
        "serial_p50": round(serial_c_p50, 1), "serial_ms": [round(x, 1) for x in ser_c],
        "concurrent_n": nclients, "concurrent_ms": [round(x, 1) for x in tc],
        "concurrent_p50": round(conc_c_p50, 1), "concurrent_max": round(tc[-1], 1),
        "wall_ms": round(wall_c, 1),
        "degradation_x": round(conc_c_p50 / serial_c_p50, 2),
        "verified": sum(1 for r in rc if r[1]),
    }
    await asyncio.gather(*(x.close() for x in cc))

    # --- serial baseline: one client, load_dashboard, n=5 ---
    c = ReflexClient()
    await c.connect()
    await c.login()
    serial = []
    for _ in range(5):
        ms, ups, _ = await c.run(f"{DASH}.load_dashboard", {}, "/dashboard", 240)
        ok, ev = v_dashboard(ups)
        serial.append(ms)
        if not ok:
            print(f"    !! serial unverified: {ev}")
    await c.close()
    serial.sort()
    print(f"  SERIAL   load_dashboard x5: p50={statistics.median(serial):.0f}ms max={serial[-1]:.0f}ms")
    out["serial_load_dashboard_ms"] = [round(x, 1) for x in serial]

    # --- N concurrent clients all calling load_dashboard simultaneously ---
    clients = [ReflexClient() for _ in range(nclients)]
    await asyncio.gather(*(x.connect() for x in clients))
    await asyncio.gather(*(x.login() for x in clients))
    print(f"  [{nclients} clients authenticated]")

    async def one(x: ReflexClient) -> tuple[float, bool, str]:
        ms, ups, _ = await x.run(f"{DASH}.load_dashboard", {}, "/dashboard", 300)
        ok, ev = v_dashboard(ups)
        return ms, ok, ev

    t0 = time.perf_counter()
    res = await asyncio.gather(*(one(x) for x in clients))
    wall = (time.perf_counter() - t0) * 1000
    times = sorted(r[0] for r in res)
    verified = sum(1 for r in res if r[1])
    print(f"  CONCURRENT load_dashboard x{nclients}: p50={statistics.median(times):.0f}ms "
          f"max={times[-1]:.0f}ms wall={wall:.0f}ms verified={verified}/{nclients}")
    out["concurrent_load_dashboard"] = {
        "n": nclients, "ms": [round(x, 1) for x in times],
        "p50": round(statistics.median(times), 1), "max": round(times[-1], 1),
        "wall_ms": round(wall, 1), "verified": verified,
        "serial_p50": round(statistics.median(serial), 1),
        "degradation_x": round(statistics.median(times) / statistics.median(serial), 2),
    }
    await asyncio.gather(*(x.close() for x in clients))

    # --- head-of-line blocking: 1 slow LLM send_message vs 6 x load_dashboard ---
    slow = ReflexClient(path="/copilot")
    await slow.connect(); await slow.login()
    await slow.fire(f"{COPILOT}.load_history", {}, "/copilot")
    await slow.fire(f"{COPILOT}.set_input",
                    {"value": "Give me a detailed breakdown of every category and my subscriptions."},
                    "/copilot")

    fast = [ReflexClient() for _ in range(6)]
    await asyncio.gather(*(x.connect() for x in fast))
    await asyncio.gather(*(x.login() for x in fast))

    async def slow_call():
        t = time.perf_counter()
        ms, ups, _ = await slow.run(f"{COPILOT}.send_message", {}, "/copilot", 300)
        ok, ev = v_send_message(ups)
        return ms, ok, ev

    async def fast_call(x):
        await asyncio.sleep(0.25)      # start just after the LLM call is in flight
        ms, ups, _ = await x.run(f"{DASH}.load_dashboard", {}, "/dashboard", 300)
        ok, ev = v_dashboard(ups)
        return ms, ok, ev

    got = await asyncio.gather(slow_call(), *(fast_call(x) for x in fast))
    sms, sok, sev = got[0]
    fms = sorted(g[0] for g in got[1:])
    print(f"  UNDER LLM LOAD: send_message={sms:.0f}ms (verified={sok}) | "
          f"load_dashboard x6 p50={statistics.median(fms):.0f}ms max={fms[-1]:.0f}ms")
    out["under_llm_load"] = {
        "send_message_ms": round(sms, 1), "send_message_verified": sok, "evidence": sev,
        "load_dashboard_ms": [round(x, 1) for x in fms],
        "load_dashboard_p50": round(statistics.median(fms), 1),
        "load_dashboard_max": round(fms[-1], 1),
    }
    await slow.close()
    await asyncio.gather(*(x.close() for x in fast))
    return out


# ============================================================ CLEANUP
def phase_cleanup() -> dict:
    """Remove perf-seeded transactions + throwaway users, restoring the demo dataset."""
    import sqlmodel
    from sqlmodel import delete, select
    from finance_app.models import Transaction, UploadedFile
    from reflex_local_auth.user import LocalUser
    eng = sqlmodel.create_engine(os.environ["DATABASE_URL"])
    with sqlmodel.Session(eng) as s:
        n = s.exec(delete(Transaction).where(  # type: ignore[arg-type]
            Transaction.user_id == DEMO_UID,
            Transaction.description.like("%REF%"))).rowcount  # type: ignore[union-attr]
        users = s.exec(select(LocalUser).where(LocalUser.username.like("perf-%"))).all()  # type: ignore[union-attr]
        for u in users:
            s.delete(u)
        s.commit()
        left = len(s.exec(select(Transaction.id).where(Transaction.user_id == DEMO_UID)).all())
    print(f"[cleanup] deleted {n} perf transactions, {len(users)} perf users; demo now has {left} txns")
    return {"deleted_txns": n, "deleted_users": len(users), "remaining": left}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["baseline", "upload", "scale", "concurrency", "cleanup"])
    ap.add_argument("--rows", type=int, default=5000)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--n-llm", type=int, default=3)
    ap.add_argument("--clients", type=int, default=10)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.phase == "baseline":
        res = await phase_baseline(a.n, a.n_llm)
        save(a.out or "baseline_24rows.json", res)
    elif a.phase == "upload":
        res = await phase_upload(a.n_llm)
        save(a.out or "upload.json", res)
    elif a.phase == "scale":
        res = await phase_scale(a.rows, a.n, a.n_llm)
        save(a.out or f"scale_{res['rows']}rows.json", res)
    elif a.phase == "concurrency":
        res = await phase_concurrency(a.clients)
        save(a.out or "concurrency.json", res)
    elif a.phase == "cleanup":
        res = phase_cleanup()
        save(a.out or "cleanup.json", res)


if __name__ == "__main__":
    asyncio.run(main())
