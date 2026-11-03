#!/usr/bin/env bash
# scripts/rollback.sh
# Undoes the last `make update`: the code back to the commit before it and the
# containers back to the images that ran then (kept by scripts/update.sh as
# atlans-rollback/*:<commit>), with no build.
#   1. checks   Docker, the record of the update, the code with no local changes
#   2. plan     what goes back, and what does NOT: the database
#   3. code     git: back to the commit before the update
#   4. start    the kept images under their names again; scripts/up.sh --no-build
#   5. verify   scripts/smoke.sh
#   6. ready
#
# The database is not touched. When the update brought migrations, the old
# code meets a newer schema: this script says so before going on and shows the
# two ways out (alembic downgrade, with the new code still in place, or
# restoring the dump the update took).
#
# Usage: ./scripts/rollback.sh [--yes] [--no-prompt] [--list] [<record>]
#        make rollback | make rollback ARGS="--list"
#   <record>     a file of backups/atualizacoes/ (default: the last update)
#   --list       lists the updates on record and stops
#   --yes        answers yes to the confirmations
#   --no-prompt  asks nothing; without --yes, stops before changing anything

# One block: bash reads it all before running any, so the git step, which may
# rewrite this very file, cannot change the rest of this run.
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
REGISTRO=""
LISTAR=0
SIM=0
PERGUNTAR=1
while [ $# -gt 0 ]; do
    case "$1" in
        --list) LISTAR=1 ;;
        --yes|-y) SIM=1 ;;
        --no-prompt) PERGUNTAR=0 ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        -*) ui_err "$(t opt_unknown "$1")"; exit 2 ;;
        *) REGISTRO="$1" ;;
    esac
    shift
done
if [ ! -t 0 ] || [ ! -t 1 ]; then
    PERGUNTAR=0
fi
confirmar() {  # <text> <default y|n>
    [ "$SIM" = "1" ] && return 0
    [ "$PERGUNTAR" = "1" ] || return 1
    ui_confirm "$1" "$2"
}

if [ "$LISTAR" = "1" ]; then
    LISTA="$(registros)"
    if [ -z "$LISTA" ]; then
        ui_info "$(t rb_none)"
        exit 0
    fi
    printf '%s\n' "$LISTA" | while IFS= read -r r; do
        printf '  %s  %-10s %s → %s\n' "$(basename "$r" .txt)" "$(registro_get "$r" ESTADO)" \
            "$(curto "$(registro_get "$r" DE)")" "$(curto "$(registro_get "$r" PARA)")"
    done
    exit 0
fi

ui_banner "$(t banner_rollback)"
ui_stages "checks plan code start verify ready"

# ── 1. Checks ────────────────────────────────────────────────────────────────
ui_stage checks
if ! docker info >/dev/null 2>&1; then
    ui_err "$(t prereq_docker_down)"
    ui_cmd "sudo systemctl start docker"
    exit 1
fi
ui_ok "$(t up_docker_ok)"
if [ -z "$REGISTRO" ]; then
    # The newest update that changed something: one that stopped before the
    # code moved (a failed backup, say) left nothing to undo.
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        if [ "$(registro_get "$r" ESTADO)" = "falhou" ] && [ "$(registro_get "$r" ETAPA)" != "codigo" ]; then
            continue
        fi
        REGISTRO="$r"
        break
    done <<< "$(registros | sort -r)"
    if [ -z "$REGISTRO" ]; then
        ui_err "$(t rb_none)"
        exit 1
    fi
    if [ "$(registro_get "$REGISTRO" ESTADO)" = "revertida" ]; then
        ui_err "$(t rb_already "$(basename "$REGISTRO" .txt)")"
        ui_hint "$(t rb_already_hint)"
        ui_cmd "make rollback ARGS=--list"
        exit 1
    fi
elif [ ! -f "$REGISTRO" ] && [ -f "$DIR_ATUALIZACOES/$REGISTRO" ]; then
    REGISTRO="$DIR_ATUALIZACOES/$REGISTRO"
elif [ ! -f "$REGISTRO" ] && [ -f "$DIR_ATUALIZACOES/$REGISTRO.txt" ]; then
    REGISTRO="$DIR_ATUALIZACOES/$REGISTRO.txt"
fi
if [ ! -f "$REGISTRO" ]; then
    ui_err "$(t rb_record_missing "$REGISTRO")"
    exit 1
fi
MODO="$(registro_get "$REGISTRO" MODO)"
DE="$(registro_get "$REGISTRO" DE)"
PARA="$(registro_get "$REGISTRO" PARA)"
RAMO="$(registro_get "$REGISTRO" RAMO)"
EXECUTOR="$(registro_get "$REGISTRO" EXECUTOR)"
BANCO="$(registro_get "$REGISTRO" BANCO)"
IMAGENS="$(registro_get "$REGISTRO" IMAGENS)"
case "$MODO" in dev|prod) ;; *) ui_err "$(t rb_record_bad "$REGISTRO")"; exit 1 ;; esac
if [ -z "$DE" ] || ! git cat-file -e "$DE^{commit}" 2>/dev/null; then
    ui_err "$(t rb_record_bad "$REGISTRO")"
    exit 1
fi
ui_ok "$(t rb_record "$(basename "$REGISTRO" .txt)" "$(registro_get "$REGISTRO" ESTADO)")"
ALTERADOS="$(git_alterados)"
if [ -n "$ALTERADOS" ]; then
    ui_err "$(t upd_dirty)"
    printf '%s\n' "$ALTERADOS" | sed 's/^/      /' >&2
    ui_hint "$(t upd_dirty_hint)"
    ui_cmd "git stash"
    exit 1
fi
ui_ok "$(t upd_clean)"
if [ "$MODO" = "prod" ]; then
    PERFIS=(--profile prod)
else
    PERFIS=(--profile dev)
    [ "$EXECUTOR" = "1" ] && PERFIS+=(--profile executor-local)
fi

# ── 2. Plan ──────────────────────────────────────────────────────────────────
ui_stage plan
AGORA="$(git rev-parse HEAD)"
ui_info "$(t rb_now "$(resumo_commit "$AGORA")")"
ui_info "$(t rb_back_to "$(resumo_commit "$DE")")"
if [ "$AGORA" != "$PARA" ]; then
    ui_warn "$(t rb_moved_since "$(curto "$PARA")")"
fi

# The images: each one kept still has to be here (a docker image prune -a,
# or a removal by hand, takes them away). Missing any, the old version is
# built again from its code instead.
CONSTRUIR=0
FALTANTES=0
for par in $IMAGENS; do
    docker image inspect "${par#*=}" >/dev/null 2>&1 || FALTANTES=$((FALTANTES + 1))
done
if [ -z "$IMAGENS" ]; then
    CONSTRUIR=1
    ui_warn "$(t rb_images_none)"
elif [ "$FALTANTES" -gt 0 ]; then
    CONSTRUIR=1
    ui_warn "$(t rb_images_missing "$FALTANTES")"
else
    ui_ok "$(t rb_images_ok "$(printf '%s' "$IMAGENS" | wc -w | tr -d ' ')")"
fi

# The database stays as the update left it. With new migrations, the old code
# meets a schema it does not know: `alembic upgrade head` in scripts/up.sh
# fails ("Can't locate revision"), and the old API may break on the new
# columns. The two ways out are the person's call, not this script's.
MIGRACOES="$(git diff --name-only --diff-filter=A "$DE" "$PARA" -- alembic/versions 2>/dev/null | grep -c '\.py$' || true)"
ACEITE_PADRAO=y
if [ "${MIGRACOES:-0}" -gt 0 ]; then
    ACEITE_PADRAO=n
    ui_warn "$(t rb_migrations "$MIGRACOES")"
    ui_hint "$(t rb_migrations_downgrade)"
    ui_cmd "docker compose ${PERFIS[*]} exec $([ "$MODO" = "prod" ] && echo api-prod || echo api) alembic downgrade -$MIGRACOES"
    if [ -n "$BANCO" ]; then
        ui_hint "$(t rb_migrations_restore "${BANCO#"$ROOT_DIR"/}")"
    fi
else
    ui_ok "$(t rb_no_migrations)"
fi
if ! confirmar "$(t rb_confirm "$(curto "$DE")")" "$ACEITE_PADRAO"; then
    ui_warn "$(t upd_cancelled)"
    [ "$PERGUNTAR" = "1" ] || ui_cmd "make rollback ARGS=--yes"
    exit 1
fi

# ── 3. Code ──────────────────────────────────────────────────────────────────
# Back on the branch the update moved forward (reset --keep refuses to
# overwrite a local change); on the branch as it was, when the update had
# left it with --to (a detached HEAD); detached at the old commit otherwise.
ui_stage code
RAMO_AGORA="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [ "$AGORA" = "$DE" ]; then
    MUDAR=()
    ui_ok "$(t upd_code_same)"
elif [ -n "$RAMO" ] && [ "$RAMO_AGORA" = "$RAMO" ]; then
    MUDAR=(git reset --quiet --keep "$DE")
elif [ -n "$RAMO" ] && [ "$(git rev-parse --verify --quiet "refs/heads/$RAMO" || true)" = "$DE" ]; then
    MUDAR=(git checkout --quiet "$RAMO")
else
    MUDAR=(git checkout --quiet --detach "$DE")
fi
if [ "${#MUDAR[@]}" -gt 0 ]; then
    if ! ui_run "$(t upd_code_moving "$(curto "$DE")")" "${MUDAR[@]}"; then
        ui_err "$(t upd_code_failed)"
        exit 1
    fi
    ui_ok "$(t upd_code_ok "$(resumo_commit HEAD)")"
fi

# ── 4. Start ─────────────────────────────────────────────────────────────────
ui_stage start
if [ "$CONSTRUIR" = "0" ]; then
    for par in $IMAGENS; do
        if ! docker tag "${par#*=}" "${par%%=*}"; then
            ui_err "$(t rb_images_restore_failed "${par#*=}")"
            exit 1
        fi
    done
    ui_ok "$(t rb_images_restored)"
fi
ARGS_UP=("$MODO")
[ "$MODO" = "dev" ] && [ "$EXECUTOR" != "1" ] && ARGS_UP+=(--no-executor)
[ "$CONSTRUIR" = "0" ] && ARGS_UP+=(--no-build)
[ "$SIM" = "1" ] && ARGS_UP+=(--yes)
[ "$PERGUNTAR" = "0" ] && ARGS_UP+=(--no-prompt)
if ! ./scripts/up.sh "${ARGS_UP[@]}"; then
    ui_err "$(t rb_up_failed)"
    exit 1
fi

# ── 5. Verify ────────────────────────────────────────────────────────────────
ui_stage verify
if ! ./scripts/smoke.sh; then
    ui_err "$(t rb_smoke_failed)"
    exit 1
fi

# ── 6. Ready ─────────────────────────────────────────────────────────────────
ui_stage ready
registro_set "$REGISTRO" ESTADO revertida
registro_set "$REGISTRO" REVERTIDA_EM "$(date '+%Y-%m-%d %H:%M:%S')"
ui_panel "$(t rb_ready_title)" \
    "$(t upd_ready_now "$(resumo_commit HEAD)")" \
    "" \
    "$(t rb_ready_forward)" \
    "$ make update"
printf '\n'
exit 0
}
