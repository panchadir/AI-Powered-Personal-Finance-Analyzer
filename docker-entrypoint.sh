#!/bin/sh
set -e

echo "Waiting for Postgres..."
until python - <<'EOF'
import os, re
url = os.environ["DATABASE_URL"]
m = re.match(r".*://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)", url)
user, pw, host, port, db = m.group(1), m.group(2), m.group(3), m.group(4) or "5432", m.group(5)
import psycopg2
psycopg2.connect(host=host, port=int(port), user=user, password=pw, dbname=db)
EOF
do
  sleep 1
done

echo "Postgres ready. Running migrations..."
alembic upgrade head

echo "Starting Reflex..."
exec reflex run --backend-host 0.0.0.0
