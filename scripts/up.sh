#!/usr/bin/env bash
# scripts/up.sh
# Brings Atlans up and leaves it ready to use, in stages:
#   1. checks        bootstrap done, Docker up, the CA password consistent
#   2. start         docker compose up -d --build, for the mode
#   3. health        waits for the API to answer
#   4. database      alembic upgrade head (in prod, after confirming)
#   5. CA            (prod) the second phase of the CA: scripts/bootstrap-stepca.sh
#   6. admin         creates the first admin when there is none
#   7. executor      (dev) waits for the local executor to connect
#   8. ready         the addresses and the everyday commands
#
# Usage: ./scripts/up.sh dev|prod [--no-executor] [--yes] [--no-prompt]
#        make up-dev | make up-dev-no-executor | make up-prod   (ARGS="--yes")
#   --no-executor  dev without the local executor
#   --yes          answers yes to the confirmations (prod migrations, CA phase 2)
#   --no-prompt    asks nothing: what would need an answer is only reported.
#                  Without a terminal it never asks either.
#
# Running it again on a running install is a quick checkup: compose only
# recreates what changed, and the migrations and the admin are idempotent.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
# shellcheck source=lib/ui.sh
. scripts/lib/ui.sh
# shellcheck source=lib/ca.sh
. scripts/lib/ca.sh

env_get() {
    grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true
}
ui_lang_load "${ATLANS_LANG:-$(env_get ATLANS_LANG)}"
[ -z "${ATLANS_LANG:-$(env_get ATLANS_LANG)}" ] && ui_lang_load "$(ui_lang_guess)"

# ── Options ──────────────────────────────────────────────────────────────────
MODO="${1:-}"
case "$MODO" in
    dev|prod) shift ;;
    -h|--help|"")
        sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
        [ -z "$MODO" ] && exit 2 || exit 0 ;;
    *) ui_err "$(t up_bad_mode "$MODO")"; exit 2 ;;
esac
EXECUTOR_LOCAL=1
SIM=0
PERGUNTAR=1
for arg in "$@"; do
    case "$arg" in
        --no-executor) EXECUTOR_LOCAL=0 ;;
        --yes|-y) SIM=1 ;;
        --no-prompt) PERGUNTAR=0 ;;
        *) ui_err "$(t opt_unknown "$arg")"; exit 2 ;;
    esac
done
if [ ! -t 0 ] || [ ! -t 1 ]; then
    PERGUNTAR=0
fi
[ "$MODO" = "prod" ] && EXECUTOR_LOCAL=0

if [ "$MODO" = "dev" ]; then
    API="api"
    PERFIS=(--profile dev)
    [ "$EXECUTOR_LOCAL" = "1" ] && PERFIS+=(--profile executor-local)
else
    API="api-prod"
    PERFIS=(--profile prod)
fi
dc() { docker compose "${PERFIS[@]}" "$@"; }

# Yes when --yes, or when the person says so; no without a terminal.
confirmar() {  # <text>
    [ "$SIM" = "1" ] && return 0
    [ "$PERGUNTAR" = "1" ] || return 1
    ui_confirm "$1" y
}

# `python -m app.cli status`: one JSON line (schema, admins, executors).
STATUS=""
ler_status() {
    STATUS="$(dc exec -T "$API" python -m app.cli status 2>/dev/null | tail -n 1)" || STATUS=""
}
status_schema() { printf '%s' "$STATUS" | grep -q '"schema": true'; }
status_admins() { printf '%s' "$STATUS" | sed -n 's/.*"admins": \([0-9]*\).*/\1/p'; }
status_revisao() { printf '%s' "$STATUS" | sed -n 's/.*"revisao": "\([^"]*\)".*/\1/p'; }
status_local_online() { printf '%s' "$STATUS" | grep -q '"nome": "Executor local (dev)", "status": "[a-z]*", "online": true'; }

if [ "$MODO" = "dev" ]; then
    ui_banner "$(t banner_up_dev)"
    ui_stages "checks start health database admin executor ready"
    [ "$EXECUTOR_LOCAL" = "1" ] || ui_skip executor
else
    ui_banner "$(t banner_up_prod)"
    ui_stages "checks start health database ca2 admin ready"
fi

# ── 1. Checks ────────────────────────────────────────────────────────────────
ui_stage checks
if ! docker info >/dev/null 2>&1; then
    ui_err "$(t prereq_docker_down)"
    ui_cmd "sudo systemctl start docker"
    exit 1
fi
ui_ok "$(t up_docker_ok)"
if [ ! -f .env ] || [ ! -s secrets/stepca_password.txt ]; then
    ui_warn "$(t up_no_bootstrap)"
    if [ "$PERGUNTAR" = "1" ] && confirmar "$(t up_run_bootstrap)"; then
        "$ROOT_DIR/scripts/bootstrap.sh" "--$MODO"
        exec "$0" "$MODO" "$@"
    fi
    ui_cmd "make bootstrap"
    exit 1
fi
ui_ok "$(t up_env_ok)"
if env_get DATABASE_URL | grep -q '<usuario>'; then
    ui_err "$(t up_db_example)"
    ui_cmd "make bootstrap"
    exit 1
fi
ui_run "$(t ca_checking)" ca_state secrets/stepca_password.txt || true
ESTADO_CA="$(tail -n 1 "$UI_LOG")"
if [ "$ESTADO_CA" = "wrong" ] || { [ "$ESTADO_CA" != "unknown" ] && [ "$(env_get STEPCA_PROVISIONER_PASSWORD)" != "$(cat secrets/stepca_password.txt)" ]; }; then
    ui_err "$(t up_ca_mismatch)"
    ui_hint "$(t up_ca_mismatch_hint)"
    ui_cmd "make bootstrap"
    exit 1
fi
case "$ESTADO_CA" in
    none) ui_ok "$(t ca_none)" ;;
    ok) ui_ok "$(t ca_ok)" ;;
    *) ui_warn "$(t ca_unknown)" ;;
esac

# ── 2. Start ─────────────────────────────────────────────────────────────────
ui_stage start
# Any image of the mode still missing: the first build, which takes minutes.
for imagem in $(dc config --images 2>/dev/null); do
    if ! docker image inspect "$imagem" >/dev/null 2>&1; then
        ui_info "$(t up_first_build)"
        break
    fi
done
if ! ui_run "$(t up_starting)" dc up -d --build; then
    case "$(cat "$UI_LOG")" in
        *"Pool overlaps"*) ui_hint "$(t up_hint_overlap)"; ui_cmd "make bootstrap" ;;
        *"port is already allocated"*|*"address already in use"*) ui_hint "$(t up_hint_port)" ;;
    esac
    exit 1
fi
SERVICOS="$(dc ps --services --status running 2>/dev/null | wc -l | tr -d ' ')"
ui_ok "$(t up_running "$SERVICOS")"

# ── 3. Health ────────────────────────────────────────────────────────────────
ui_stage health
esperar_api() {
    local id estado i=0
    id="$(dc ps -q "$API")"
    while [ "$i" -lt 120 ]; do
        estado="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id" 2>/dev/null || echo gone)"
        case "$estado" in
            healthy|running) return 0 ;;
            exited|dead|gone) return 1 ;;
        esac
        sleep 2
        i=$((i + 1))
    done
    return 1
}
if ! ui_run "$(t up_waiting_api)" esperar_api; then
    ui_err "$(t up_api_down)"
    dc logs --tail=25 "$API" 2>&1 | sed 's/^/      /' >&2
    case "$(dc logs --tail=200 "$API" 2>&1)" in
        *"password authentication failed"*|*"LDAP"*|*"pg_hba.conf"*|*"Connection refused"*) ui_cmd "make check-db" ;;
    esac
    exit 1
fi
ui_ok "$(t up_api_ok)"

# ── 4. Database ──────────────────────────────────────────────────────────────
ui_stage database
ler_status
ANTES="$(status_revisao)"
MIGRAR=1
if [ "$MODO" = "prod" ] && status_schema; then
    # A production schema already exists: migrating is a change to confirm.
    confirmar "$(t up_migrate_question)" || MIGRAR=0
fi
if [ "$MIGRAR" = "1" ]; then
    if ! ui_run "$(t up_migrating)" dc exec -T "$API" alembic upgrade head; then
        case "$(cat "$UI_LOG")" in
            *"permission denied to create extension"*) ui_hint "$(t up_hint_extension)" ;;
        esac
        ui_cmd "make check-db$([ "$MODO" = "prod" ] && printf ' SERVICE=api-prod')"
        exit 1
    fi
    ler_status
    if [ -n "$ANTES" ] && [ "$ANTES" = "$(status_revisao)" ]; then
        ui_ok "$(t up_schema_current "$(status_revisao)")"
    else
        ui_ok "$(t up_schema_migrated "$(status_revisao)")"
    fi
else
    ui_warn "$(t up_migrate_skipped)"
    ui_cmd "docker compose --profile prod exec $API alembic upgrade head"
fi

# ── 5. CA, second phase (prod) ───────────────────────────────────────────────
if [ "$MODO" = "prod" ]; then
    ui_stage ca2
    if [ -s traefik/atlans-ca/agents.crt ] && [ -n "$(env_get STEPCA_ROOT_FINGERPRINT)" ]; then
        ui_ok "$(t up_ca2_done)"
    elif confirmar "$(t up_ca2_question)"; then
        ui_run "$(t up_ca2_issuing)" env ATLANS_UP=1 ./scripts/bootstrap-stepca.sh || exit 1
        # The API reads the .env (now with STEPCA_ROOT_FINGERPRINT) only when it is
        # created, and Traefik loads the new certificates on a restart.
        ui_run "$(t up_ca2_recreating)" sh -c "docker compose --profile prod up -d $API && docker compose --profile prod restart traefik"
        ui_run "$(t up_waiting_api)" esperar_api || true
        ui_ok "$(t up_ca2_done)"
        ui_warn "$(t up_ca2_backup)"
        ui_cmd "make backup-stepca"
    else
        ui_warn "$(t up_ca2_pending)"
        ui_cmd "make bootstrap-stepca"
    fi
fi

# ── 6. Admin ─────────────────────────────────────────────────────────────────
ui_stage admin
ADMINS="$(status_admins)"
if [ "${ADMINS:-0}" -gt 0 ]; then
    ui_ok "$(t up_admin_exists "$ADMINS")"
elif [ "$PERGUNTAR" = "1" ] && confirmar "$(t up_admin_question)"; then
    while :; do
        EMAIL="$(ui_ask "$(t up_admin_email)")"
        printf '%s' "$EMAIL" | grep -qE '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' && break
        ui_hint "$(t up_admin_email_invalid)"
    done
    while :; do
        SENHA="$(ui_ask_secret "$(t up_admin_password)")"
        if [ "${#SENHA}" -lt 12 ]; then ui_hint "$(t up_admin_password_short)"; continue; fi
        [ "$(ui_ask_secret "$(t up_admin_password_again)")" = "$SENHA" ] && break
        ui_hint "$(t up_admin_password_mismatch)"
    done
    # The password goes through stdin, never on a command line: from a file
    # born 600 and deleted right after (a background command, as in ui_run,
    # does not inherit a pipe).
    ARQ_SENHA="$(mktemp secrets/.admin.XXXXXX)"
    ui_cleanup "$ARQ_SENHA"
    chmod 600 "$ARQ_SENHA"
    printf '%s\n' "$SENHA" > "$ARQ_SENHA"
    unset SENHA
    criar_admin() { dc exec -T "$API" python -m app.cli create-admin --email "$EMAIL" --password-stdin < "$ARQ_SENHA"; }
    if ui_run "$(t up_admin_creating)" criar_admin; then
        ui_ok "$(t up_admin_created "$EMAIL")"
    else
        ui_warn "$(t up_admin_failed)"
        ui_cmd "docker compose ${PERFIS[*]} exec $API python -m app.cli create-admin"
    fi
    rm -f "$ARQ_SENHA"
else
    ui_warn "$(t up_admin_missing)"
    ui_cmd "docker compose ${PERFIS[*]} exec $API python -m app.cli create-admin"
fi

# ── 7. Local executor (dev) ──────────────────────────────────────────────────
if [ "$MODO" = "dev" ]; then
    ui_stage executor
    if [ "$EXECUTOR_LOCAL" = "0" ]; then
        ui_info "$(t up_executor_skipped)"
    else
        esperar_executor() {
            local i=0
            while [ "$i" -lt 60 ]; do
                ler_status
                status_local_online && return 0
                sleep 3
                i=$((i + 1))
            done
            return 1
        }
        if ui_run "$(t up_waiting_executor)" esperar_executor; then
            ui_ok "$(t up_executor_online)"
        else
            ui_warn "$(t up_executor_offline)"
            LOGS_API="$(dc logs --tail=300 "$API" 2>&1 || true)"
            case "$LOGS_API" in
                *"decifrar chave do provisioner"*)
                    ui_hint "$(t up_hint_ca_password)"
                    ui_cmd "make bootstrap" ;;
                *)
                    dc logs --tail=12 executor-local 2>&1 | sed 's/^/      /'
                    ui_cmd "docker compose logs -f executor-local executor-local-init" ;;
            esac
        fi
    fi
fi

# ── 8. Ready ─────────────────────────────────────────────────────────────────
ui_stage ready
if [ "$MODO" = "dev" ]; then
    PORTA_API="$(env_get API_PORT)"
    ui_panel "$(t up_ready_title)" \
        "$(t up_ready_web)     http://localhost:3000" \
        "$(t up_ready_api)     http://localhost:${PORTA_API:-8000}/docs" \
        "" \
        "$(t up_ready_everyday)" \
        "$ make logs-dev" \
        "$ make check-db" \
        "$ make down"
else
    ui_panel "$(t up_ready_title)" \
        "$(t up_ready_web)     https://$(env_get PUBLIC_HOST)" \
        "$(t up_ready_agents)  https://$(env_get AGENTS_HOST)" \
        "" \
        "$(t up_ready_everyday)" \
        "$ make logs-prod" \
        "$ make smoke" \
        "$ make backup-stepca"
fi
printf '\n'
