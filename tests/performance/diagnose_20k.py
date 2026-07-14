"""Isolate WHERE load_transactions' cost goes at 20k rows.

Splits the handler into its three real stages and times each in-process, against the
real Postgres DB, so the socket-level timeout can be attributed precisely:
  1. SQL   : SELECT ... WHERE user_id ORDER BY date, id   (unbounded, no index on `date`)
  2. BUILD : the Python loop that turns 20k ORM rows into 20k TxnRow view models
  3. WIRE  : JSON-serializing those 20k TxnRow objects into the state delta

Also prints the Postgres EXPLAIN ANALYZE for the actual query.
"""
from __future__ import annotations

import json
import os
import time

import sqlmodel
from sqlmodel import Session, create_engine, select, text

from finance_app.models import Transaction as TxnModel
from finance_app.state.transactions_state import load_user_transaction_rows

UID = 2
eng = create_engine(os.environ["DATABASE_URL"])


def main() -> None:
    with Session(eng) as s:
        n = len(s.exec(select(TxnModel.id).where(TxnModel.user_id == UID)).all())
        print(f"user_id={UID} transactions={n}\n")

        # --- Stage 1: the raw SQL the handler runs ---
        t = time.perf_counter()
        rows = s.exec(
            select(TxnModel).where(TxnModel.user_id == UID)
            .order_by(TxnModel.date, TxnModel.id)
        ).all()
        sql_ms = (time.perf_counter() - t) * 1000
        print(f"1. SQL   fetch+ORM hydrate {len(rows):>6} rows : {sql_ms:9.1f} ms")

        # --- Stage 2: the view-model build loop ---
        t = time.perf_counter()
        views = load_user_transaction_rows(s, TxnModel, UID)
        build_ms = (time.perf_counter() - t) * 1000
        print(f"2. BUILD load_user_transaction_rows()     : {build_ms:9.1f} ms  "
              f"({len(views)} TxnRow)")

        # --- Stage 3: JSON serialization of the delta Reflex must push ---
        t = time.perf_counter()
        payload = json.dumps([v.dict() if hasattr(v, "dict") else vars(v) for v in views],
                             default=str)
        ser_ms = (time.perf_counter() - t) * 1000
        print(f"3. WIRE  json.dumps(rows) -> state delta   : {ser_ms:9.1f} ms  "
              f"({len(payload)/1024/1024:.2f} MB)")
        print(f"\n   => single websocket frame of {len(payload)/1024/1024:.2f} MB "
              f"pushed to the browser on every /transactions page load")

        # --- EXPLAIN ANALYZE: prove the sort is unindexed ---
        print("\n--- EXPLAIN ANALYZE (the handler's actual query) ---")
        q = text("EXPLAIN ANALYZE SELECT * FROM transactions "
                 "WHERE user_id = :uid ORDER BY date, id")
        for line in s.exec(q, params={"uid": UID}):  # type: ignore[call-arg]
            print("   ", line[0])

        print("\n--- indexes on transactions ---")
        for line in s.exec(text(
                "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='transactions'")):
            print(f"    {line[0]:<28} {line[1]}")


if __name__ == "__main__":
    main()
