#!/bin/sh
# app/entrypoint.sh
# Applies Alembic migrations before starting uvicorn.
#
# Idempotent: `alembic upgrade head` is a no-op if the schema is already up to date.
# If the DB is not available, Alembic fails fast and the container restarts
# (the compose restart policy). An empty schema results in clear logs, without
# requests returning 500 masking the real problem.

set -e

echo "[entrypoint] Aplicando migrations Alembic..."
alembic upgrade head
echo "[entrypoint] Migrations OK. Iniciando aplicacao."

exec "$@"
