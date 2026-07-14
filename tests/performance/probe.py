"""Wire-format probe: validate we can drive Reflex event handlers over socket.io.

Read-only w.r.t. app code. Run INSIDE the container:
    docker compose exec -T app python tests/performance/probe.py
"""
from __future__ import annotations

import asyncio
import time
import uuid

import socketio

BACKEND = "http://localhost:8000"
NS = "/_event"

ROOT = "reflex___state____state"
AUTH = f"{ROOT}.finance_app___state___auth_state____auth_state"
LOGIN = f"{AUTH}.finance_app___state___auth_state____login_state"
DASH = f"{AUTH}.finance_app___state___dashboard_state____dashboard_state"


def router_data(path: str = "/dashboard") -> dict:
    return {"pathname": path, "asPath": path, "query": {}}


async def main() -> None:
    token = str(uuid.uuid4())
    sio = socketio.AsyncClient()
    deltas: list[tuple[float, dict]] = []

    @sio.on("event", namespace=NS)
    async def on_event(update):  # noqa: ANN001
        deltas.append((time.perf_counter(), update))
        print(f"  <- delta keys={list((update.get('delta') or {}).keys())} "
              f"events={len(update.get('events') or [])}")

    await sio.connect(
        f"{BACKEND}?token={token}",
        socketio_path=NS,
        namespaces=[NS],
        transports=["websocket"],
    )
    print(f"connected sid={sio.get_sid(namespace=NS)} token={token}")

    async def emit(name: str, payload: dict, path: str = "/dashboard") -> None:
        print(f"-> {name} {payload if 'password' not in str(payload) else '<creds>'}")
        await sio.emit(
            "event",
            {"name": name, "payload": payload, "router_data": router_data(path)},
            namespace=NS,
        )

    # 1. Hydrate (what the real frontend does on connect).
    await emit(f"{ROOT}.hydrate", {})
    await asyncio.sleep(1.5)

    # 2. Log in as the demo user.
    t0 = time.perf_counter()
    await emit(
        f"{LOGIN}.handle_login",
        {"form_data": {"email": "demo@example.com", "password": "demodemo1"}},
        "/login",
    )
    await asyncio.sleep(3.0)
    print(f"login window elapsed={time.perf_counter()-t0:.3f}s")

    # 3. Did auth_token actually get set server-side? Check the delta.
    for _, u in deltas:
        d = u.get("delta") or {}
        if AUTH in d and "auth_token" in d[AUTH]:
            print(f"AUTH TOKEN SET server-side: {str(d[AUTH]['auth_token'])[:12]}...")

    # 4. Now drive load_dashboard and see if it does REAL work.
    deltas.clear()
    t0 = time.perf_counter()
    await emit(f"{DASH}.load_dashboard", {})
    await asyncio.sleep(15.0)
    print(f"\nload_dashboard: {len(deltas)} deltas over {time.perf_counter()-t0:.3f}s")
    for t, u in deltas:
        d = (u.get("delta") or {}).get(DASH, {})
        interesting = {k: v for k, v in d.items()
                       if k in ("safe_to_spend_today", "has_data", "loaded",
                                "briefing_loading", "confidence_label")}
        brief = d.get("briefing")
        if brief:
            interesting["briefing"] = str(brief)[:60] + "..."
        print(f"  +{t-t0:7.3f}s  {interesting}")

    await sio.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
