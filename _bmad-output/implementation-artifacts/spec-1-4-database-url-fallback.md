---
title: 'DATABASE_URL dev fallback for fresh-checkout runnability'
type: 'bugfix'
created: '2026-07-09'
status: 'done'
route: 'one-shot'
---

# DATABASE_URL dev fallback for fresh-checkout runnability

## Intent

**Problem:** `rxconfig.py` read `db_url=os.environ["DATABASE_URL"]`, and with no committed `.env` (it is git-ignored) a fresh checkout crashed at `pytest` collection (`KeyError: 'DATABASE_URL'`) and `reflex run` would not start. `alembic/env.py` had the same hard-require, so `alembic upgrade head` failed the same way.

**Approach:** Resolve `db_url` via `os.environ.get("DATABASE_URL") or "<local Postgres DSN>"`, falling back to the canonical local Postgres DSN from `.env.example` (Postgres is the Phase-1 store per product directive). Applied the identical fallback in `alembic/env.py` for consistency; the two are cross-referenced by comment. `docker-entrypoint.sh` intentionally keeps its hard-require — it only runs in-container where docker-compose always sets `DATABASE_URL`. Using `or` (not `.get`'s default) also covers a present-but-empty var. Docker/other deployments are unaffected because they always set `DATABASE_URL`.

## Suggested Review Order

1. [`../../rxconfig.py`](../../rxconfig.py) — the core change: `db_url` fallback resolution and its rationale comment.
2. [`../../alembic/env.py`](../../alembic/env.py) — the mirrored fallback so migrations run on a fresh checkout; confirm it stays in sync with rxconfig.
3. [`deferred-work.md`](deferred-work.md) — the story-1.4 item marked ✅ RESOLVED, plus the newly-deferred pre-existing `docker-entrypoint.sh` regex-parsing finding.
