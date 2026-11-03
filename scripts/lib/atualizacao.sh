# shellcheck shell=bash
# scripts/lib/atualizacao.sh
# What scripts/update.sh and scripts/rollback.sh share: the record of each
# update, the mode of the installation that is running, and the images kept
# as the way back.
#
# Sourced, not run, after scripts/lib/ui.sh. Expects ROOT_DIR as the current
# directory (both scripts cd into it).
#
# The record: one file per update in backups/atualizacoes/, named by the time
# it started, with KEY=VALUE lines. It is what `make rollback` reads to go back:
#   MODO      dev or prod
#   EXECUTOR  1 when dev ran with the local executor
#   RAMO      the branch the code was on (empty: detached HEAD)
#   DE        the commit before the update
#   PARA      the commit the update went to
#   IMAGENS   "<image as configured>=<copy kept>" pairs, space-separated
#   BANCO     the database dump taken before (empty: --skip-db-backup)
#   CA        the step-ca backup taken before (empty: no CA volume)
#   ETAPA     "codigo" once the code moved: from then on, a failure is
#             undone by make rollback or picked up again by make update
#   ESTADO    iniciada, concluida, falhou or revertida
#   INICIO, FIM, REVERTIDA_EM: dates

DIR_ATUALIZACOES="${ATLANS_UPDATES_DIR:-$ROOT_DIR/backups/atualizacoes}"

env_get() {
    grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true
}

# ── Record ───────────────────────────────────────────────────────────────────
registro_novo() {  # → the path of a new, empty record (0600, in a 0700 dir)
    local arquivo
    ( umask 077 && mkdir -p "$DIR_ATUALIZACOES" )
    chmod 700 "$DIR_ATUALIZACOES" 2>/dev/null || true
    # The name is the time, so that the names sort in order: two updates in
    # the same second wait for the next one rather than share a file.
    arquivo="$DIR_ATUALIZACOES/$(date +%Y-%m-%d-%H%M%S).txt"
    while [ -e "$arquivo" ]; do
        sleep 1
        arquivo="$DIR_ATUALIZACOES/$(date +%Y-%m-%d-%H%M%S).txt"
    done
    ( umask 077 && : > "$arquivo" )
    printf '%s' "$arquivo"
}
registro_set() {  # <file> <key> <value>
    local tmp
    tmp="$(mktemp "$1.XXXXXX")"
    grep -v "^$2=" "$1" > "$tmp" || true
    printf '%s=%s\n' "$2" "$3" >> "$tmp"
    chmod 600 "$tmp"
    mv -f "$tmp" "$1"
}
registro_get() {  # <file> <key>
    grep -E "^$2=" "$1" 2>/dev/null | tail -n 1 | cut -d= -f2- || true
}
registros() {  # every record, oldest first (the names are dates)
    # shellcheck disable=SC2012 # names this script writes: <date>.txt
    ls -1 "$DIR_ATUALIZACOES"/*.txt 2>/dev/null | sort || true
}

# ── The running installation ─────────────────────────────────────────────────
# Which API runs decides the mode, as scripts/smoke.sh does: api-prod is
# production, api is dev. Empty: nothing running.
modo_em_execucao() {
    local servicos
    servicos="$(docker compose ps --services --status running 2>/dev/null || true)"
    if printf '%s\n' "$servicos" | grep -qx 'api-prod'; then
        echo prod
    elif printf '%s\n' "$servicos" | grep -qx 'api'; then
        echo dev
    fi
}
executor_local_em_execucao() {
    docker compose ps --services --status running 2>/dev/null | grep -qx 'executor-local'
}

# ── Git ──────────────────────────────────────────────────────────────────────
# Tracked files changed by hand: an update on top of them would mix both, and
# a rollback would have to choose. Untracked files (a local certificate, an
# extra Traefik file) stay out of it.
git_alterados() {
    git status --porcelain --untracked-files=no 2>/dev/null || true
}
curto() { git rev-parse --short=12 "$1" 2>/dev/null || printf '%s' "$1"; }
resumo_commit() {  # <commit>: "abc123 2026-11-01 subject"
    git log -1 --format='%h %cs %s' "$1" 2>/dev/null | cut -c1-72
}

# ── Images kept as the way back ──────────────────────────────────────────────
# Every running container of the mode has its image tagged as
# atlans-rollback/<name>:<commit>. A tag copies nothing (it is a name for the
# same layers), and it keeps the image when the build reuses atlans-api:local
# for the new version and `docker image prune` would otherwise remove the old
# one. Images pinned by digest (name@sha256:...) never change: left out.
nome_seguro() {  # <image reference> → a valid repository name
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9._-' '-' \
        | sed -e 's/[._-]\{2,\}/-/g' -e 's/^[._-]*//' -e 's/[._-]*$//'
}
guardar_imagens() {  # <tag> <container ids...> → "configured=kept" pairs
    local etiqueta="$1" id configurada imagem guardada pares=""
    shift
    for id in "$@"; do
        configurada="$(docker inspect -f '{{.Config.Image}}' "$id" 2>/dev/null)" || continue
        imagem="$(docker inspect -f '{{.Image}}' "$id" 2>/dev/null)" || continue
        case "$configurada" in ''|*@*) continue ;; esac
        case " $pares " in *" $configurada="*) continue ;; esac
        guardada="atlans-rollback/$(nome_seguro "$configurada"):$etiqueta"
        docker tag "$imagem" "$guardada" || return 1
        pares="${pares:+$pares }$configurada=$guardada"
    done
    printf '%s' "$pares"
}
# The kept images of the older records go away, leaving those of the newest
# <keep> (ATLANS_ROLLBACK_KEEP, default 2): each version kept costs the disk
# of its images once they are no longer in use.
limpar_imagens_antigas() {  # <keep>
    local manter="$1" lista total n=0 registro par
    lista="$(registros)"
    total="$(printf '%s\n' "$lista" | grep -c . || true)"
    while IFS= read -r registro; do
        [ -n "$registro" ] || continue
        n=$((n + 1))
        [ "$n" -gt $((total - manter)) ] && break
        [ "$(registro_get "$registro" IMAGENS_REMOVIDAS)" = "1" ] && continue
        for par in $(registro_get "$registro" IMAGENS); do
            case "${par#*=}" in
                atlans-rollback/*) docker image rm "${par#*=}" >/dev/null 2>&1 || true ;;
            esac
        done
        registro_set "$registro" IMAGENS_REMOVIDAS 1
    done <<< "$lista"
}
