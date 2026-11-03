#!/usr/bin/env bash
# scripts/update.sh
# Updates a running installation to a new version, with the way back ready:
#   1. checks       Docker, the mode that is running, the code with no local
#                   changes, the disk
#   2. changes      fetches the new version and shows what it brings: the
#                   commits, the new migrations, the new .env variables (and
#                   stops if a required one is missing)
#   3. backup       the CA volume, the database (pg_dump in a container, on the
#                   API's own network) and the current images, kept as
#                   atlans-rollback/*:<commit>
#   4. code         git: fast-forward to the new version
#   5. start        scripts/up.sh: builds, recreates what changed, migrates
#   6. verify       scripts/smoke.sh and, in prod, the Traefik routes
#   7. ready        the summary, and `make rollback` if anything is wrong
#
# Usage: ./scripts/update.sh [dev|prod] [--to <tag|commit>] [--check] [--yes]
#                            [--no-prompt] [--skip-db-backup]
#        make update | make update ARGS="--check" | make update ARGS="--to v2.21.0"
#   dev|prod          the mode; by default, the one running (api-prod or api)
#   --to <ref>        a tag or commit instead of the branch's upstream
#   --check           only shows what would change, changing nothing
#   --yes             answers yes to the confirmations (here and in up.sh)
#   --no-prompt       asks nothing; without --yes, stops before changing
#                     anything. Without a terminal it never asks either.
#   --skip-db-backup  no pg_dump (for a database backed up elsewhere)
#
# Every update leaves a record in backups/atualizacoes/ (see
# scripts/lib/atualizacao.sh), which `make rollback` reads.

# The whole script is one block: bash reads all of it before running any, so
# the git step below, which may rewrite this very file, cannot change what
# the rest of this run does.
{
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
# shellcheck source=lib/ui.sh
. scripts/lib/ui.sh
# shellcheck source=lib/atualizacao.sh
. scripts/lib/atualizacao.sh

ui_lang_load "${ATLANS_LANG:-$(env_get ATLANS_LANG)}"
[ -z "${ATLANS_LANG:-$(env_get ATLANS_LANG)}" ] && ui_lang_load "$(ui_lang_guess)"

# ── Options ──────────────────────────────────────────────────────────────────
MODO=""
ALVO_PEDIDO=""
SO_VERIFICAR=0
SIM=0
PERGUNTAR=1
BACKUP_BANCO=1
while [ $# -gt 0 ]; do
    case "$1" in
        dev|prod) MODO="$1" ;;
        --to)
            [ $# -ge 2 ] || { ui_err "$(t upd_to_needs_ref)"; exit 2; }
            ALVO_PEDIDO="$2"; shift ;;
        --to=*) ALVO_PEDIDO="${1#--to=}" ;;
        --check) SO_VERIFICAR=1 ;;
        --yes|-y) SIM=1 ;;
        --no-prompt) PERGUNTAR=0 ;;
        --skip-db-backup) BACKUP_BANCO=0 ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) ui_err "$(t opt_unknown "$1")"; exit 2 ;;
    esac
    shift
done
if [ ! -t 0 ] || [ ! -t 1 ]; then
    PERGUNTAR=0
fi
confirmar() {  # <text>
    [ "$SIM" = "1" ] && return 0
    [ "$PERGUNTAR" = "1" ] || return 1
    ui_confirm "$1" y
}

ui_banner "$(t banner_update)"
ui_stages "checks changes backup code start verify ready"

# ── 1. Checks ────────────────────────────────────────────────────────────────
ui_stage checks
if ! docker info >/dev/null 2>&1; then
    ui_err "$(t prereq_docker_down)"
    ui_cmd "sudo systemctl start docker"
    exit 1
fi
ui_ok "$(t up_docker_ok)"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    ui_err "$(t upd_not_git)"
    exit 1
fi
if [ ! -f .env ]; then
    ui_err "$(t upd_no_env)"
    ui_cmd "make bootstrap"
    exit 1
fi
EM_EXECUCAO="$(modo_em_execucao)"
if [ -z "$MODO" ]; then
    MODO="$EM_EXECUCAO"
    if [ -z "$MODO" ]; then
        ui_err "$(t upd_nothing_running)"
        ui_cmd "make update ARGS=prod"
        exit 1
    fi
elif [ -n "$EM_EXECUCAO" ] && [ "$EM_EXECUCAO" != "$MODO" ]; then
    ui_err "$(t upd_mode_mismatch "$MODO" "$EM_EXECUCAO")"
    exit 1
fi
EXECUTOR=0
if [ "$MODO" = "prod" ]; then
    API="api-prod"
    PERFIS=(--profile prod)
else
    API="api"
    PERFIS=(--profile dev)
    # Dev comes up with the local executor (make up-dev), unless the one
    # running came up without it (make up-dev-no-executor).
    if [ -z "$EM_EXECUCAO" ] || executor_local_em_execucao; then
        EXECUTOR=1
        PERFIS+=(--profile executor-local)
    fi
fi
dc() { docker compose "${PERFIS[@]}" "$@"; }
ui_ok "$(t upd_mode "$MODO")"

ALTERADOS="$(git_alterados)"
if [ -n "$ALTERADOS" ]; then
    ui_err "$(t upd_dirty)"
    printf '%s\n' "$ALTERADOS" | sed 's/^/      /' >&2
    ui_hint "$(t upd_dirty_hint)"
    ui_cmd "git stash"
    exit 1
fi
ui_ok "$(t upd_clean)"

# The build needs room for a second copy of the images while the first one
# still runs.
DIR_DOCKER="$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || echo /)"
LIVRE_KB="$(df -Pk "$DIR_DOCKER" 2>/dev/null | awk 'NR==2 {print $4}')"
case "${LIVRE_KB:-}" in
    ''|*[!0-9]*) ;;
    *)
        if [ "$LIVRE_KB" -lt 5242880 ]; then
            ui_warn "$(t upd_low_disk "$((LIVRE_KB / 1048576))" "$DIR_DOCKER")"
            ui_cmd "docker image prune"
        else
            ui_ok "$(t upd_disk_ok "$((LIVRE_KB / 1048576))")"
        fi ;;
esac

# ── 2. Changes ───────────────────────────────────────────────────────────────
ui_stage changes
RAMO="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
UPSTREAM=""
if [ -n "$RAMO" ]; then
    UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
fi
if [ -z "$ALVO_PEDIDO" ] && [ -z "$UPSTREAM" ]; then
    if [ -z "$RAMO" ]; then
        ui_err "$(t upd_detached)"
    else
        ui_err "$(t upd_no_upstream "$RAMO")"
    fi
    ui_cmd "make update ARGS=\"--to <tag>\""
    exit 1
fi
REMOTO="origin"
[ -n "$UPSTREAM" ] && REMOTO="${UPSTREAM%%/*}"
# No prompt can show while the spinner runs: a remote that asks for a
# password or a key passphrase fails right away instead of hanging.
# shellcheck disable=SC2317,SC2329 # called through ui_run
buscar() {
    GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes}" \
        git fetch --tags "$REMOTO"
}
if ! ui_run "$(t upd_fetching "$REMOTO")" buscar; then
    ui_err "$(t upd_fetch_failed "$REMOTO")"
    exit 1
fi

DE="$(git rev-parse HEAD)"
if [ -n "$ALVO_PEDIDO" ]; then
    ALVO="$(git rev-parse --verify --quiet "$ALVO_PEDIDO^{commit}" 2>/dev/null \
        || git rev-parse --verify --quiet "$REMOTO/$ALVO_PEDIDO^{commit}" 2>/dev/null || true)"
    if [ -z "$ALVO" ]; then
        ui_err "$(t upd_ref_unknown "$ALVO_PEDIDO")"
        exit 1
    fi
else
    ALVO="$(git rev-parse "$UPSTREAM")"
    if ! git merge-base --is-ancestor HEAD "$ALVO"; then
        ui_err "$(t upd_diverged "$RAMO" "$UPSTREAM")"
        ui_hint "$(t upd_diverged_hint)"
        exit 1
    fi
fi

# The last record says which version the containers run: with the code
# already at the target, there is only something to do when that version is
# not the one that came up (a git pull without the rebuild, an update that
# failed halfway, or no record at all, before this script existed).
ULTIMO="$(registros | tail -n 1)"
# An update that failed after moving the code, to this same version: run
# again, it picks up where it stopped, with the backups and images taken
# before it (those of now would be the broken state).
RETOMAR=0
if [ -n "$ULTIMO" ] && [ "$(registro_get "$ULTIMO" ESTADO)" = "falhou" ] \
    && [ "$(registro_get "$ULTIMO" ETAPA)" = "codigo" ] \
    && [ "$(registro_get "$ULTIMO" PARA)" = "$ALVO" ] && [ "$DE" = "$ALVO" ]; then
    RETOMAR=1
fi
if [ "$ALVO" = "$DE" ] && [ "$RETOMAR" = "1" ]; then
    ui_info "$(t upd_resuming "$(basename "$ULTIMO" .txt)" "$(resumo_commit "$ALVO")")"
elif [ "$ALVO" = "$DE" ]; then
    if [ -n "$ULTIMO" ] && [ "$(registro_get "$ULTIMO" PARA)" = "$ALVO" ] \
        && [ "$(registro_get "$ULTIMO" ESTADO)" = "concluida" ]; then
        ui_ok "$(t upd_up_to_date "$(resumo_commit "$ALVO")")"
        exit 0
    fi
    ui_info "$(t upd_code_current "$(resumo_commit "$ALVO")")"
    ui_hint "$(t upd_code_current_hint)"
else
    ui_info "$(t upd_from "$(resumo_commit "$DE")")"
    ui_info "$(t upd_to "$(resumo_commit "$ALVO")")"
    if git merge-base --is-ancestor HEAD "$ALVO"; then
        N="$(git rev-list --count "HEAD..$ALVO")"
        ui_ok "$(t upd_commits "$N")"
        git log --no-merges --format='%h %s' -n 12 "HEAD..$ALVO" | cut -c1-76 | sed 's/^/      /'
        [ "$N" -gt 12 ] && ui_hint "$(t upd_commits_more)"
    else
        ui_warn "$(t upd_not_ahead)"
    fi
    MIGRACOES="$(git diff --name-only --diff-filter=A HEAD "$ALVO" -- alembic/versions | grep -c '\.py$' || true)"
    if [ "${MIGRACOES:-0}" -gt 0 ]; then
        ui_warn "$(t upd_migrations "$MIGRACOES")"
    else
        ui_ok "$(t upd_no_migrations)"
    fi
fi

# The .env does not change on its own. A variable the new compose file
# requires (${VAR:?...}) stops the update here, before anything is touched; a
# new one in .env.example only gets a mention, as it has a default.
EXEMPLO="$(git show "$ALVO:.env.example" 2>/dev/null || true)"
COMPOSE_NOVO="$(git show "$ALVO:docker-compose.yml" 2>/dev/null || true)"
FALTAM=""
for nome in $(printf '%s\n' "$COMPOSE_NOVO" | grep -oE '\$\{[A-Z0-9_]+:\?' | sed -e 's/^\${//' -e 's/:?$//' | sort -u); do
    [ -n "$(env_get "$nome")" ] || FALTAM="${FALTAM:+$FALTAM }$nome"
done
NOVAS=""
for nome in $(printf '%s\n' "$EXEMPLO" | grep -oE '^[A-Z][A-Z0-9_]*=' | tr -d '=' | sort -u); do
    grep -qE "^$nome=" .env || NOVAS="${NOVAS:+$NOVAS }$nome"
done
if [ -n "$FALTAM" ]; then
    ui_err "$(t upd_env_required "$FALTAM")"
    ui_hint "$(t upd_env_required_hint)"
    exit 1
fi
if [ -n "$NOVAS" ]; then
    ui_warn "$(t upd_env_new "$NOVAS")"
    ui_hint "$(t upd_env_new_hint)"
else
    ui_ok "$(t upd_env_ok)"
fi

if [ "$SO_VERIFICAR" = "1" ]; then
    ui_panel "$(t upd_check_title)" \
        "$(t upd_check_nothing_changed)" \
        "" \
        "$(t upd_check_apply)" \
        "$ make update$([ -n "$ALVO_PEDIDO" ] && printf ' ARGS="--to %s"' "$ALVO_PEDIDO")"
    exit 0
fi
if ! confirmar "$(t upd_confirm "$(curto "$DE")" "$(curto "$ALVO")")"; then
    ui_warn "$(t upd_cancelled)"
    [ "$PERGUNTAR" = "1" ] || ui_cmd "make update ARGS=--yes"
    exit 1
fi

# Two updates at once would build and recreate the same containers.
( umask 077 && mkdir -p "$DIR_ATUALIZACOES" )
if command -v flock >/dev/null 2>&1; then
    exec 9>"$DIR_ATUALIZACOES/.trava"
    if ! flock -n 9; then
        ui_err "$(t upd_locked)"
        exit 1
    fi
fi

# ── 3. Backup ────────────────────────────────────────────────────────────────
ui_stage backup
BANCO=""
if [ "$RETOMAR" = "1" ]; then
    REGISTRO="$ULTIMO"
    registro_set "$REGISTRO" ESTADO iniciada
    BANCO="$(registro_get "$REGISTRO" BANCO)"
    ui_ok "$(t upd_resume_backups)"
else
REGISTRO="$(registro_novo)"
registro_set "$REGISTRO" INICIO "$(date '+%Y-%m-%d %H:%M:%S')"
registro_set "$REGISTRO" MODO "$MODO"
registro_set "$REGISTRO" EXECUTOR "$EXECUTOR"
registro_set "$REGISTRO" RAMO "$RAMO"
registro_set "$REGISTRO" DE "$DE"
registro_set "$REGISTRO" PARA "$ALVO"
registro_set "$REGISTRO" ESTADO iniciada
registro_set "$REGISTRO" CA ""
registro_set "$REGISTRO" BANCO ""
registro_set "$REGISTRO" IMAGENS ""
DIR_BACKUP="$ROOT_DIR/backups"

if docker volume inspect step-ca-data >/dev/null 2>&1; then
    if ! ui_run "$(t upd_backup_ca)" ./scripts/backup-stepca.sh; then
        ui_err "$(t upd_backup_ca_failed)"
        registro_set "$REGISTRO" ESTADO falhou
        exit 1
    fi
    # shellcheck disable=SC2012 # names this project writes: step-ca-<date>.tar.gz
    CA="$(ls -1t "$DIR_BACKUP"/step-ca-*.tar.gz 2>/dev/null | head -n 1 || true)"
    registro_set "$REGISTRO" CA "$CA"
    ui_ok "$(t upd_backup_ca_ok "${CA#"$ROOT_DIR"/}")"
else
    ui_info "$(t upd_backup_ca_none)"
fi

# The database: pg_dump from the official postgres image of the server's own
# major version (an older pg_dump refuses a newer server), in a container that
# joins the API's network namespace — the same DNS, /etc/hosts and routes the
# API uses to reach the database, whatever DATABASE_URL points at. The URL
# goes in through the environment, never on a command line; the dump comes
# out on stdout into a file this shell creates 0600.
if [ "$BACKUP_BANCO" = "1" ]; then
    URL_BANCO="$(env_get DATABASE_URL | sed -e 's/+asyncpg//' -e 's/?.*//')"
    if [ -z "$URL_BANCO" ]; then
        ui_err "$(t upd_backup_db_no_url)"
        registro_set "$REGISTRO" ESTADO falhou
        exit 1
    fi
    ID_API="$(dc ps -q "$API" 2>/dev/null | head -n 1 || true)"
    if [ -n "$ID_API" ]; then
        REDE=(--network "container:$ID_API")
    else
        REDE=(--network host --add-host host.docker.internal:host-gateway)
    fi
    CLIENTE="${ATLANS_PG_CLIENT_IMAGE:-postgres:17-alpine}"
    ARQ_VERSAO="$(mktemp "${TMPDIR:-/tmp}/atlans-pgver.XXXXXX")"
    ui_cleanup "$ARQ_VERSAO"
    # shellcheck disable=SC2317,SC2329 # called through ui_run
    versao_do_banco() {
        PGURL="$URL_BANCO" docker run --rm "${REDE[@]}" -e PGURL "$CLIENTE" \
            sh -c 'psql "$PGURL" -Atc "show server_version_num"' > "$ARQ_VERSAO"
    }
    if ! ui_run "$(t upd_backup_db_version)" versao_do_banco; then
        ui_err "$(t upd_backup_db_failed)"
        ui_hint "$(t upd_backup_db_failed_hint)"
        registro_set "$REGISTRO" ESTADO falhou
        exit 1
    fi
    VERSAO="$(tr -dc '0-9' < "$ARQ_VERSAO")"
    MAIOR=$(( ${VERSAO:-0} / 10000 ))
    if [ "$MAIOR" -lt 10 ]; then
        ui_err "$(t upd_backup_db_failed)"
        registro_set "$REGISTRO" ESTADO falhou
        exit 1
    fi
    ui_ok "$(t upd_backup_db_server "$MAIOR")"
    CARIMBO="$(date +%F-%H%M)"
    ( umask 077 && mkdir -p "$DIR_BACKUP" )
    PARCIAL="$(mktemp "$DIR_BACKUP/.atlans-db-$CARIMBO.XXXXXX")"
    ui_cleanup "$PARCIAL"
    # shellcheck disable=SC2317,SC2329 # called through ui_run
    fazer_dump() {
        PGURL="$URL_BANCO" docker run --rm "${REDE[@]}" -e PGURL "postgres:$MAIOR-alpine" \
            sh -c 'pg_dump "$PGURL" --no-owner --no-privileges -F c' > "$PARCIAL"
    }
    if ! ui_run "$(t upd_backup_db)" fazer_dump || [ ! -s "$PARCIAL" ]; then
        ui_err "$(t upd_backup_db_failed)"
        ui_hint "$(t upd_backup_db_failed_hint)"
        registro_set "$REGISTRO" ESTADO falhou
        exit 1
    fi
    BANCO="$DIR_BACKUP/atlans-db-$CARIMBO.dump"
    mv -f "$PARCIAL" "$BANCO"
    chmod 600 "$BANCO"
    registro_set "$REGISTRO" BANCO "$BANCO"
    ui_ok "$(t upd_backup_db_ok "${BANCO#"$ROOT_DIR"/}" "$(du -h "$BANCO" | cut -f1)")"
    # The dumps this script makes: the newest ATLANS_DB_BACKUP_RETAIN (10).
    RETER="${ATLANS_DB_BACKUP_RETAIN:-10}"
    # shellcheck disable=SC2012 # names this script writes: atlans-db-<date>.dump
    ( cd "$DIR_BACKUP" && ls -1t atlans-db-*.dump 2>/dev/null | tail -n "+$((RETER + 1))" | while IFS= read -r velho; do
        rm -f -- "$velho"
    done ) || true
else
    ui_warn "$(t upd_backup_db_skipped)"
fi

# The images of what runs now, the way back for `make rollback`.
IDS="$(dc ps -q 2>/dev/null || true)"
# shellcheck disable=SC2086 # one id per word
if ! IMAGENS="$(guardar_imagens "$(git rev-parse --short=12 "$DE")" $IDS)"; then
    ui_err "$(t upd_images_failed)"
    registro_set "$REGISTRO" ESTADO falhou
    exit 1
fi
registro_set "$REGISTRO" IMAGENS "$IMAGENS"
ui_ok "$(t upd_images_kept "$(printf '%s' "$IMAGENS" | wc -w | tr -d ' ')")"
fi

# ── 4. Code ──────────────────────────────────────────────────────────────────
ui_stage code
if [ "$ALVO" = "$DE" ]; then
    ui_ok "$(t upd_code_same)"
else
    if [ -n "$ALVO_PEDIDO" ]; then
        MUDAR=(git checkout --quiet --detach "$ALVO")
    else
        MUDAR=(git merge --ff-only --quiet "$ALVO")
    fi
    if ! ui_run "$(t upd_code_moving "$(curto "$ALVO")")" "${MUDAR[@]}"; then
        ui_err "$(t upd_code_failed)"
        registro_set "$REGISTRO" ESTADO falhou
        exit 1
    fi
    ui_ok "$(t upd_code_ok "$(resumo_commit HEAD)")"
fi
# From here on, the code is the new version: what fails is undone with
# make rollback, or picked up again by running make update once more.
registro_set "$REGISTRO" ETAPA codigo

falhou() {  # <message>: the update stops, with the way back
    registro_set "$REGISTRO" ESTADO falhou
    registro_set "$REGISTRO" FIM "$(date '+%Y-%m-%d %H:%M:%S')"
    ui_err "$1"
    ui_hint "$(t upd_rollback_hint)"
    ui_cmd "make rollback"
    exit 1
}

# ── 5. Start ─────────────────────────────────────────────────────────────────
ui_stage start
INICIO_SUBIDA="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ARGS_UP=("$MODO")
[ "$MODO" = "dev" ] && [ "$EXECUTOR" = "0" ] && ARGS_UP+=(--no-executor)
[ "$SIM" = "1" ] && ARGS_UP+=(--yes)
[ "$PERGUNTAR" = "0" ] && ARGS_UP+=(--no-prompt)
if ! ./scripts/up.sh "${ARGS_UP[@]}"; then
    falhou "$(t upd_up_failed)"
fi

# ── 6. Verify ────────────────────────────────────────────────────────────────
ui_stage verify
if ! ./scripts/smoke.sh; then
    falhou "$(t upd_smoke_failed)"
fi
# A router that names a middleware the new dynamic.yml does not have is
# dropped without a sound on HTTP; only the Traefik log tells.
if [ "$MODO" = "prod" ]; then
    ROTAS="$(dc logs --since "$INICIO_SUBIDA" traefik 2>&1 | grep -i 'does not exist' | tail -n 5 || true)"
    if [ -n "$ROTAS" ]; then
        printf '%s\n' "$ROTAS" | sed 's/^/      /'
        falhou "$(t upd_traefik_routes)"
    fi
    ui_ok "$(t upd_traefik_ok)"
fi

# ── 7. Ready ─────────────────────────────────────────────────────────────────
ui_stage ready
registro_set "$REGISTRO" ESTADO concluida
registro_set "$REGISTRO" FIM "$(date '+%Y-%m-%d %H:%M:%S')"
limpar_imagens_antigas "${ATLANS_ROLLBACK_KEEP:-2}"
LINHAS=("$(t upd_ready_now "$(resumo_commit HEAD)")" "$(t upd_ready_record "${REGISTRO#"$ROOT_DIR"/}")")
[ -n "$BANCO" ] && LINHAS+=("$(t upd_ready_db "${BANCO#"$ROOT_DIR"/}")")
LINHAS+=("" "$(t upd_ready_back)" "$ make rollback")
ui_panel "$(t upd_ready_title)" "${LINHAS[@]}"
printf '\n'
exit 0
}
