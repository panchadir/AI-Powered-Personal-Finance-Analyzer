#!/bin/sh
set -e

# Validate DATABASE_URL once, up front. A malformed DSN is a configuration error, not a
# transient one -- it must abort with a readable message rather than be retried forever by the
# wait loop below.
#
# DATABASE_URL is hard-required here on purpose: this script only ever runs in-container, where
# docker-compose always sets it. (rxconfig.py and alembic/env.py apply a local-Postgres default
# for the fresh-checkout case; those two are cross-referenced by comment.)
#
# Parsed with SQLAlchemy rather than a regex. The previous
# `re.match(r".*://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)", url)` mis-parsed any password
# containing '@', ':' or '/', and returned None (-> AttributeError) on anything it could not
# match, so a typo'd DSN died with a traceback instead of a message.
python - <<'EOF' || exit 1
import os
import sys

from sqlalchemy.engine import make_url

raw = os.environ.get("DATABASE_URL")
if not raw:
    sys.exit("DATABASE_URL is not set. docker-compose should provide it.")
try:
    url = make_url(raw)
except Exception as exc:
    sys.exit(f"DATABASE_URL is not a valid database URL: {exc}")
if not url.host or not url.database:
    sys.exit(f"DATABASE_URL must include a host and a database name (got {url!r}).")
EOF

echo "Waiting for Postgres..."
until python - <<'EOF'
import os

import psycopg2
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
psycopg2.connect(
    host=url.host,
    port=url.port or 5432,
    user=url.username,
    password=url.password,
    dbname=url.database,
)
EOF
do
  sleep 1
done

echo "Postgres ready. Running migrations..."
alembic -c /app/backend/alembic.ini upgrade head

echo "Starting Reflex..."
cd /app/frontend
exec reflex run --backend-host 0.0.0.0
