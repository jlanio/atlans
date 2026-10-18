#!/usr/bin/env bash
# scripts/rollback-rehearsal.sh
# Rollback rehearsal, executed for real: the previous version goes up on an empty
# database, the new one migrates it, and the previous one comes back over the
# migrated database, without touching it. Then the pre-upgrade backup is restored
# into a new database. It is what docs/operations.md tells the operator to do on a
# release, run end to end (CI: .github/workflows/rollback-rehearsal.yml).
#
# Usage:
#   DATABASE_URL=postgresql+asyncpg://user@host:5432/db scripts/rollback-rehearsal.sh
#
# Environment:
#   DATABASE_URL   EMPTY Postgres + PostGIS database (required). asyncpg or plain
#                  postgresql:// URL; the libpq tools get it without the driver
#                  and without the query string.
#   OLD_REF        previous version (default 3bf789a, Atlans v2.17.0).
#   NEW_REF        new version (default HEAD).
#   EXPECTED_REV   alembic revision both versions must report (default 9ed006ca1660).
#   PYTHON         interpreter for the venvs (default python3; the image uses 3.12).
#   API_PORT       port for uvicorn (default 8765).
#   REHEARSAL_DIR  worktrees, venvs, dump and logs (default: a mktemp -d, removed
#                  at the end; a given directory is kept).
#   APP_SECRET / FERNET_KEY  throwaway values are generated when absent.
#   REDIS_URL      passed through to the API (it starts without Redis, with errors in the log).
#
# Needs git, curl, psql, pg_dump and pg_restore on the PATH (client of the same
# major version as the server). It also creates, and drops at the end, a second
# database (`<db>_restore_drill`) on the same server for the restore drill.
#
# Exit 0 = every step PASS; anything else = at least one FAIL (the summary at the
# end says which).

set -euo pipefail

OLD_REF="${OLD_REF:-3bf789a}"
NEW_REF="${NEW_REF:-HEAD}"
EXPECTED_REV="${EXPECTED_REV:-9ed006ca1660}"
PYTHON="${PYTHON:-python3}"
API_PORT="${API_PORT:-8765}"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "DATABASE_URL vazio: aponte para um Postgres + PostGIS vazio." >&2
    exit 2
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# The two URL forms: the API's (asyncpg) and libpq's (psql, pg_dump), as
# the hint in app/cli.py builds it.
case "$DATABASE_URL" in
    postgresql+asyncpg://*) APP_URL="$DATABASE_URL" ;;
    postgresql://*) APP_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}" ;;
    postgres://*) APP_URL="postgresql+asyncpg://${DATABASE_URL#postgres://}" ;;
    *) echo "DATABASE_URL precisa ser postgresql:// ou postgresql+asyncpg://" >&2; exit 2 ;;
esac
PG_URL="$(printf %s "$APP_URL" | sed -e 's/+asyncpg//' -e 's/?.*//')"
DB_NAME="${PG_URL##*/}"
RESTORE_DB="${DB_NAME}_restore_drill"
RESTORE_URL="${PG_URL%/*}/${RESTORE_DB}"

# Throwaway secrets: nothing here is encrypted for later.
APP_SECRET="${APP_SECRET:-$(head -c 32 /dev/urandom | base64)}"
FERNET_KEY="${FERNET_KEY:-$(head -c 32 /dev/urandom | base64 | tr '+/' '-_')}"
export APP_SECRET FERNET_KEY

if [ -n "${REHEARSAL_DIR:-}" ]; then
    WORK="$REHEARSAL_DIR"
    KEEP_WORK=1
    mkdir -p "$WORK"
else
    WORK="$(mktemp -d)"
    KEEP_WORK=0
fi
OLD_WT="$WORK/old"
NEW_WT="$WORK/new"
DUMP="$WORK/pre-upgrade.dump"
LOGS="$WORK/logs"
mkdir -p "$LOGS"

SENTINEL_OLD="rollback_rehearsal_old"
SENTINEL_NEW="rollback_rehearsal_new"

cleanup() {
    psql -q "$PG_URL" -c "DROP DATABASE IF EXISTS \"$RESTORE_DB\"" >/dev/null 2>&1 || true
    git -C "$ROOT_DIR" worktree remove --force "$OLD_WT" >/dev/null 2>&1 || true
    git -C "$ROOT_DIR" worktree remove --force "$NEW_WT" >/dev/null 2>&1 || true
    if [ "$KEEP_WORK" -eq 0 ]; then
        rm -rf "$WORK"
    fi
}
trap cleanup EXIT

# ── Helpers ──────────────────────────────────────────────────────────────────

header() {
    printf '\n==================================================================\n'
    printf '== %s\n' "$*"
    printf '==================================================================\n'
}

log() { printf '  -> %s\n' "$*"; }

sql() { psql -X -q -v ON_ERROR_STOP=1 -tA "$PG_URL" -c "$1"; }

# Runs a command of one version (alembic, app.cli) inside its worktree, with its venv.
in_version() {
    local wt="$1"; shift
    (cd "$wt" && export DATABASE_URL="$APP_URL" PATH="$wt/.venv/bin:$PATH" && "$@")
}

prepare_version() {
    local ref="$1" wt="$2"
    log "worktree de $ref em $wt"
    git -C "$ROOT_DIR" worktree add --detach "$wt" "$ref" >/dev/null
    log "commit $(git -C "$wt" log -1 --format='%h %s')"
    log "venv ($("$PYTHON" --version)) com o requirements.txt desta versao"
    "$PYTHON" -m venv "$wt/.venv"
    "$wt/.venv/bin/pip" install --quiet --disable-pip-version-check \
        --require-hashes --only-binary=:all: -r "$wt/requirements.txt"
}

check_current() {
    local wt="$1" out
    out="$(in_version "$wt" alembic current 2>&1)" || { printf '%s\n' "$out"; return 1; }
    printf '%s\n' "$out"
    if ! printf '%s\n' "$out" | grep -q "^${EXPECTED_REV}\b"; then
        log "alembic current nao e $EXPECTED_REV"
        return 1
    fi
    log "alembic current = $EXPECTED_REV"
}

check_db() {
    in_version "$1" python -m app.cli check-db
}

# Brings the API up, waits for 200 on /ping (the healthcheck endpoint) and takes it down.
check_api() {
    local wt="$1" logfile="$2" pid ok=1 code=000
    (cd "$wt" && DATABASE_URL="$APP_URL" exec "$wt/.venv/bin/uvicorn" app.main:app \
        --host 127.0.0.1 --port "$API_PORT") >"$logfile" 2>&1 &
    pid=$!
    for _ in $(seq 1 90); do
        code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${API_PORT}/ping" || true)"
        if [ "$code" = "200" ]; then
            ok=0
            break
        fi
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    kill -9 "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    if [ "$ok" -ne 0 ]; then
        log "API nao respondeu 200 em /ping (ultimo codigo: $code). Fim do log:"
        tail -n 40 "$logfile" | sed 's/^/     | /'
        return 1
    fi
    log "GET /ping -> 200"
}

write_sentinel() {
    sql "INSERT INTO system_config (key, value) VALUES ('$1', to_json('$2'::text))"
    log "sentinela $1 gravada"
}

# Prints how many rows with key $1 the database at URL $2 has.
count_sentinel() {
    psql -X -q -v ON_ERROR_STOP=1 -tA "$2" -c "SELECT count(*) FROM system_config WHERE key = '$1'"
}

expect_sentinel() {
    local key="$1" url="$2" want="$3" got
    got="$(count_sentinel "$key" "$url")"
    if [ "$got" != "$want" ]; then
        log "sentinela $key: esperado $want linha(s), achou $got"
        return 1
    fi
    log "sentinela $key: $got linha(s), como esperado"
}

# ── Steps ────────────────────────────────────────────────────────────────────

step_prepare() {
    local old_sha new_sha
    old_sha="$(git -C "$ROOT_DIR" rev-parse --verify "${OLD_REF}^{commit}")"
    new_sha="$(git -C "$ROOT_DIR" rev-parse --verify "${NEW_REF}^{commit}")"
    log "OLD_REF=$OLD_REF ($old_sha)"
    log "NEW_REF=$NEW_REF ($new_sha)"
    log "banco: ${PG_URL##*@}"
    if [ "$(sql "SELECT to_regclass('public.alembic_version') IS NULL AND to_regclass('public.users') IS NULL")" != "t" ]; then
        log "o banco nao esta vazio (alembic_version ou users existem)"
        return 1
    fi
    log "banco vazio"
    prepare_version "$old_sha" "$OLD_WT"
    prepare_version "$new_sha" "$NEW_WT"
}

step_old() {
    log "alembic upgrade head"
    in_version "$OLD_WT" alembic upgrade head
    check_current "$OLD_WT"
    check_db "$OLD_WT"
    check_api "$OLD_WT" "$LOGS/api-old.log"
    write_sentinel "$SENTINEL_OLD" "$OLD_REF"
}

step_backup() {
    pg_dump -Fc -f "$DUMP" "$PG_URL"
    log "pg_dump -Fc -> $DUMP ($(wc -c <"$DUMP") bytes)"
}

step_new() {
    log "alembic upgrade head"
    in_version "$NEW_WT" alembic upgrade head
    check_current "$NEW_WT"
    check_db "$NEW_WT"
    check_api "$NEW_WT" "$LOGS/api-new.log"
    expect_sentinel "$SENTINEL_OLD" "$PG_URL" 1
    write_sentinel "$SENTINEL_NEW" "$NEW_REF"
}

step_rollback() {
    log "sem migracao: a versao anterior volta sobre o banco como a nova o deixou"
    check_current "$OLD_WT"
    check_db "$OLD_WT"
    check_api "$OLD_WT" "$LOGS/api-rollback.log"
    expect_sentinel "$SENTINEL_OLD" "$PG_URL" 1
    expect_sentinel "$SENTINEL_NEW" "$PG_URL" 1
}

step_restore() {
    sql "DROP DATABASE IF EXISTS \"$RESTORE_DB\""
    sql "CREATE DATABASE \"$RESTORE_DB\""
    log "banco novo: $RESTORE_DB"
    pg_restore --clean --if-exists --no-owner --exit-on-error -d "$RESTORE_URL" "$DUMP"
    log "pg_restore --clean concluido"
    expect_sentinel "$SENTINEL_OLD" "$RESTORE_URL" 1
    expect_sentinel "$SENTINEL_NEW" "$RESTORE_URL" 0
}

# ── Runner ───────────────────────────────────────────────────────────────────

STEPS=(
    "step_prepare|0. Preparacao: banco vazio, worktrees e venvs"
    "step_old|1. OLD ($OLD_REF): upgrade, current, check-db, API, sentinela 1"
    "step_backup|2. Backup pre-upgrade (pg_dump -Fc)"
    "step_new|3. NEW ($NEW_REF): upgrade, current, check-db, API, sentinela 2"
    "step_rollback|4. ROLLBACK para OLD sem tocar no banco: current, check-db, API, sentinelas"
    "step_restore|5. Restore drill: pg_restore --clean num banco novo"
)
RESULTS=()
failed=0

for entry in "${STEPS[@]}"; do
    fn="${entry%%|*}"
    title="${entry#*|}"
    if [ "$failed" -ne 0 ]; then
        RESULTS+=("SKIP  $title")
        continue
    fi
    header "$title"
    # A subshell outside any `if`/`||`: there `set -e` stays active, and the first
    # failing command ends the step (and only the step).
    set +e
    ("$fn")
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        RESULTS+=("PASS  $title")
    else
        RESULTS+=("FAIL  $title")
        failed=1
    fi
done

header "Resumo"
{
    for r in "${RESULTS[@]}"; do
        printf '%s\n' "$r"
    done
    if [ "$failed" -eq 0 ]; then
        printf '\nRESULTADO: PASS\n'
    else
        printf '\nRESULTADO: FAIL\n'
    fi
} | tee "$LOGS/summary.txt"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
        printf '### Ensaio de rollback (%s -> %s -> %s)\n\n```\n' "$OLD_REF" "$NEW_REF" "$OLD_REF"
        cat "$LOGS/summary.txt"
        printf '```\n'
    } >>"$GITHUB_STEP_SUMMARY"
fi

exit "$failed"
