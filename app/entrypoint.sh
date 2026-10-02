#!/bin/sh
# app/entrypoint.sh
# Aplica migrations Alembic antes de subir o uvicorn.
#
# Idempotente: `alembic upgrade head` e no-op se schema ja esta atualizado.
# Se DB nao estiver disponivel, Alembic falha rapido e o container reinicia
# (restart policy do compose). Schema vazio resulta em logs claros, sem
# requests com 500 mascarando o problema real.

set -e

echo "[entrypoint] Aplicando migrations Alembic..."
alembic upgrade head
echo "[entrypoint] Migrations OK. Iniciando aplicacao."

exec "$@"
