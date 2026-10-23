#!/usr/bin/env bash
# scripts/e2e/descer.sh
# Takes down what scripts/e2e/subir.sh brought up, volumes included: the
# compose stack (down -v), the Postgres container, the external step-ca-data
# volume (down -v keeps it on purpose) and the E2E .env and CA password, so the
# next subir.sh starts from zero.
#
# Usage: scripts/e2e/descer.sh
#
# The step-ca-data volume is the same name a dev install on this machine uses:
# it is removed only when this checkout's .env is the E2E one.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

export COMPOSE_FILE="docker-compose.yml:scripts/e2e/compose.e2e.yml"

PG_CONTAINER="atlans-e2e-postgres"
PG_PORT="${E2E_PG_PORT:-55432}"

env_get() {
    grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true
}

if [ -f .env ] && ! env_get DATABASE_URL | grep -q "@host.docker.internal:${PG_PORT}/atlans_e2e\$"; then
    echo "O .env deste clone não é o do E2E (DATABASE_URL de outro banco): nada foi derrubado." >&2
    exit 1
fi

if [ -f .env ]; then
    docker compose --profile dev --profile executor-local down -v --remove-orphans
fi
docker rm -f -v "$PG_CONTAINER" >/dev/null 2>&1 || true
docker volume rm step-ca-data >/dev/null 2>&1 || true
# The CA password is UID 1000's after subir.sh; the directory is ours, so rm works.
rm -f .env secrets/stepca_password.txt
echo "Stack do E2E derrubada, volumes removidos."
