#!/bin/sh
set -e

cd /app

echo "[entrypoint] Applying Alembic migrations"
alembic upgrade head

echo "[entrypoint] Starting application: $*"
exec "$@"
