#!/usr/bin/env bash
# scripts/e2e/subir.sh
# Brings up the real stack for the browser tests (E2E), locally or in CI:
#   1. checks      Docker, Compose 2.24.4+, E2E_EMAIL/E2E_SENHA, a .env that is ours
#   2. postgres    a postgis/postgis container with postgis and uuid-ossp
#   3. bootstrap   scripts/bootstrap.sh --no-prompt, then a real DATABASE_URL in .env
#   4. up          scripts/up.sh dev --yes --no-prompt, with the local executor
#                  and the web from the production build (compose.e2e.yml)
#   5. user        the test user: python -m app.cli create-admin
#   6. executor    waits for "Executor local (dev)" to be online
#   7. web         waits for the site on http://localhost:3000
#   8. login       POST /auth/login with the test user must answer 200
#
# Usage: E2E_EMAIL=e2e@example.com E2E_SENHA='<12+ characters>' scripts/e2e/subir.sh
#   E2E_PG_PORT   host port of the Postgres (default 55432)
#
# Idempotent: running it again on a stack that is up recreates nothing that did
# not change. scripts/e2e/descer.sh takes everything down, volumes included.
#
# The .env of this checkout becomes the E2E one. A .env pointing to another
# database (your dev install) is left alone and the script stops: use another
# clone, or move that .env away.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

# Every `docker compose` from here on (up.sh, smoke.sh, the logs) sees the
# production web in place of the dev server.
export COMPOSE_FILE="docker-compose.yml:scripts/e2e/compose.e2e.yml"

PG_CONTAINER="atlans-e2e-postgres"
PG_IMAGE="${E2E_PG_IMAGE:-postgis/postgis:16-3.4}"
PG_PORT="${E2E_PG_PORT:-55432}"
PG_DB="atlans_e2e"
PG_USER="atlans_e2e"
EXECUTOR_NOME="Executor local (dev)"
WEB_URL="http://localhost:3000"
API_URL="http://localhost:8000"

etapa() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok() { printf '\033[1;32m  ok\033[0m  %s\n' "$*"; }
erro() { printf '\033[1;31merro\033[0m  %s\n' "$*" >&2; }

env_get() {
    grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true
}
# Replaces (or adds) key="value" in .env, as bootstrap.sh does.
upsert_env() {
    local key="$1" value="$2" escaped
    escaped=$(printf '%s' "$value" | sed -e 's/[\/&|]/\\&/g')
    if grep -qE "^${key}=" .env; then
        sed -i.bak -E "s|^${key}=.*|${key}=\"${escaped}\"|" .env && rm -f .env.bak
    else
        printf '%s="%s"\n' "$key" "$value" >> .env
    fi
}
# The DATABASE_URL this script writes: any other one is not ours to replace.
banco_e2e() { env_get DATABASE_URL | grep -q "://${PG_USER}:[^@]*@host.docker.internal:${PG_PORT}/${PG_DB}\$"; }

INICIO=$SECONDS

# ── 1. Checks ────────────────────────────────────────────────────────────────
etapa "Verificações"
if ! docker info >/dev/null 2>&1; then
    erro "Docker não está rodando."
    exit 1
fi
VERSAO_COMPOSE="$(docker compose version --short 2>/dev/null | sed 's/^v//')"
if [ "$(printf '%s\n%s\n' 2.24.4 "$VERSAO_COMPOSE" | sort -V | head -n 1)" != "2.24.4" ]; then
    erro "Docker Compose $VERSAO_COMPOSE: o compose.e2e.yml precisa da 2.24.4 ou mais nova (!reset)."
    exit 1
fi
ok "Docker Compose $VERSAO_COMPOSE"
if [ -z "${E2E_EMAIL:-}" ] || [ -z "${E2E_SENHA:-}" ]; then
    erro "Defina E2E_EMAIL e E2E_SENHA (o usuário de teste)."
    exit 2
fi
if [ "${#E2E_SENHA}" -lt 12 ]; then
    erro "E2E_SENHA precisa ter pelo menos 12 caracteres."
    exit 2
fi
if [ -f .env ] && ! env_get DATABASE_URL | grep -q '<usuario>' && ! banco_e2e; then
    erro "O .env deste clone aponta para outro banco: não é o do E2E, e este script não o substitui."
    printf '      Use outro clone, ou tire o .env daqui antes.\n' >&2
    exit 1
fi
ok "E2E_EMAIL=$E2E_EMAIL"

# ── 2. Postgres ──────────────────────────────────────────────────────────────
etapa "Postgres ($PG_IMAGE na porta $PG_PORT)"
if docker container inspect "$PG_CONTAINER" >/dev/null 2>&1; then
    PG_SENHA="$(docker container inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$PG_CONTAINER" \
        | sed -n 's/^POSTGRES_PASSWORD=//p')"
    docker start "$PG_CONTAINER" >/dev/null
    ok "container $PG_CONTAINER reaproveitado"
else
    PG_SENHA="$(openssl rand -hex 24)"
    # Published on every interface: the API reaches it as host.docker.internal,
    # the host's address on the Docker bridge, not its loopback.
    docker run -d --name "$PG_CONTAINER" \
        -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_SENHA" -e POSTGRES_DB="$PG_DB" \
        -p "$PG_PORT:5432" "$PG_IMAGE" >/dev/null
    ok "container $PG_CONTAINER criado"
fi
# Over TCP: during the image's first start the init server answers only on the
# socket, and the real one comes up after it.
i=0
until docker exec "$PG_CONTAINER" pg_isready -q -h 127.0.0.1 -U "$PG_USER" -d "$PG_DB"; do
    i=$((i + 1))
    if [ "$i" -ge 90 ]; then
        erro "o Postgres não respondeu em 3 min."
        docker logs --tail 40 "$PG_CONTAINER" >&2
        exit 1
    fi
    sleep 2
done
docker exec "$PG_CONTAINER" psql -q -h 127.0.0.1 -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 \
    -c 'CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
ok "banco $PG_DB pronto, com postgis e uuid-ossp"

# ── 3. Bootstrap ─────────────────────────────────────────────────────────────
etapa "Bootstrap"
./scripts/bootstrap.sh --no-prompt --dev --lang pt
upsert_env DATABASE_URL "postgresql+asyncpg://${PG_USER}:${PG_SENHA}@host.docker.internal:${PG_PORT}/${PG_DB}"
unset PG_SENHA
ok "DATABASE_URL do E2E gravado no .env"
# Two files born 600 and owned by whoever ran bootstrap are read, through a
# bind mount, by containers that run as UID 1000: the step-ca reads its
# password, and the API reads the .env (slowapi loads ./.env at import, and the
# PermissionError there kills the API before it serves anything). bootstrap.sh
# only fixes the first one, and only as root. A CI runner is UID 1001, with
# sudo: give both to UID 1000, readable by our group. After the last write to
# the .env above: upsert_env's `sed -i` gives the file back to us.
dar_ao_uid_1000() {  # <file> <who reads it>
    local arquivo="$1" quem="$2"
    [ "$(uname -s)" = "Linux" ] || return 0
    [ "$(stat -c %u "$arquivo")" != "1000" ] || return 0
    if sudo -n true 2>/dev/null; then
        sudo chown "1000:$(id -g)" "$arquivo"
        sudo chmod 640 "$arquivo"
        ok "$arquivo legível $quem (UID 1000)"
    else
        erro "$arquivo não é do UID 1000 e não há sudo sem senha: $quem não vai conseguir lê-lo."
        printf '      sudo chown 1000:%s %s && sudo chmod 640 %s\n' "$(id -g)" "$arquivo" "$arquivo" >&2
        exit 1
    fi
}
dar_ao_uid_1000 secrets/stepca_password.txt "pelo step-ca"
dar_ao_uid_1000 .env "pela API"

# ── 4. Up ────────────────────────────────────────────────────────────────────
etapa "Subindo a stack (up.sh dev, com o executor local)"
./scripts/up.sh dev --yes --no-prompt

dc() { docker compose --profile dev --profile executor-local "$@"; }

# ── 5. Test user ─────────────────────────────────────────────────────────────
etapa "Usuário de teste"
# The password through stdin, never on a command line.
printf '%s\n' "$E2E_SENHA" | dc exec -T api python -m app.cli create-admin --email "$E2E_EMAIL" --password-stdin
ok "usuário $E2E_EMAIL"

# ── 6. Local executor ────────────────────────────────────────────────────────
etapa "Esperando o executor \"$EXECUTOR_NOME\" ficar online"
executor_online() {
    local status
    status="$(dc exec -T api python -m app.cli status 2>/dev/null | tail -n 1)" || return 1
    # One JSON line (app/services/situacao_instalacao.py); the same match as up.sh.
    [[ "$status" =~ \"nome\":\ \"Executor\ local\ \(dev\)\",\ \"status\":\ \"[a-z]*\",\ \"online\":\ true ]]
}
i=0
until executor_online; do
    i=$((i + 1))
    if [ "$i" -ge 100 ]; then
        erro "o executor local não ficou online em 5 min."
        dc logs --tail 40 executor-local executor-local-init >&2 || true
        exit 1
    fi
    sleep 3
done
ok "$EXECUTOR_NOME online"

# ── 7. Web ───────────────────────────────────────────────────────────────────
etapa "Esperando o web (build de produção) em $WEB_URL"
i=0
until curl -fsS -o /dev/null "$WEB_URL/login" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        erro "o web não respondeu em 2 min."
        dc logs --tail 40 web-dev >&2 || true
        exit 1
    fi
    sleep 2
done
ok "GET $WEB_URL/login respondeu"

# ── 8. Login ─────────────────────────────────────────────────────────────────
etapa "Login do usuário de teste"
json_str() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
CORPO="$(mktemp)"
trap 'rm -f "$CORPO"' EXIT
# The body through stdin (--data-binary @-), so the password stays out of `ps`.
CODIGO="$(printf '{"identifier": "%s", "password": "%s"}' "$(json_str "$E2E_EMAIL")" "$(json_str "$E2E_SENHA")" \
    | curl -sS -o "$CORPO" -w '%{http_code}' -X POST "$API_URL/auth/login" \
        -H 'Content-Type: application/json' --data-binary @-)"
if [ "$CODIGO" != "200" ]; then
    erro "POST /auth/login respondeu $CODIGO"
    head -c 300 "$CORPO" >&2; printf '\n' >&2
    exit 1
fi
grep -q '"access_token"' "$CORPO" || { erro "POST /auth/login respondeu 200 sem access_token"; exit 1; }
ok "POST $API_URL/auth/login -> 200 (access_token emitido)"

printf '\n\033[1;32mStack do E2E pronta em %ds.\033[0m Web: %s  API: %s\n' "$((SECONDS - INICIO))" "$WEB_URL" "$API_URL"
