#!/usr/bin/env bash
# scripts/backup-stepca.sh
# Backs up the step-ca-data volume to backups/step-ca-YYYY-MM-DD-HHMM.tar.gz.
# Keeps the 14 most recent backups; removes the older ones. The directory is
# 0700 and each archive 0600, owned by whoever runs the script.
#
# Recommended to run daily via cron:
#   0 3 * * * cd /caminho/do/deploy && ./scripts/backup-stepca.sh >> backups/cron.log 2>&1

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
RETAIN="${BACKUP_RETAIN:-14}"

log() { printf '\033[1;36m[backup-stepca]\033[0m %s\n' "$*"; }
ok()  { printf '\033[1;32m[backup-stepca]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[backup-stepca]\033[0m %s\n' "$*" >&2; }

if ! docker volume inspect step-ca-data >/dev/null 2>&1; then
    err "Volume step-ca-data nao existe. Nada para fazer backup."
    exit 1
fi

# The archive holds the CA's private keys and secrets/password (the password of
# those keys, in clear text): only whoever runs the backup may read it. umask
# 077 before anything is created makes a new directory 0700 and each archive
# 0600; an existing directory keeps the mode it was born with, so it is
# tightened too. If that fails (a directory owned by root while the backup
# runs as a docker-group user, an NFS export with root_squash), the backup is
# still written — skipping it would lose the CA's only copy — UNLESS other
# users can write in the directory: then one of them could plant the file the
# archive goes into, and the keys would land in a file they own.
umask 077
mkdir -p "$BACKUP_DIR"
if ! chmod 700 "$BACKUP_DIR" 2>/dev/null; then
    if [ -n "$(find "$BACKUP_DIR" -maxdepth 0 -perm /022 2>/dev/null)" ]; then
        err "${BACKUP_DIR} e gravavel por outros usuarios e nao pode ser restrito a 0700: backup NAO gravado (as chaves da CA ficariam expostas)."
        exit 1
    fi
    err "AVISO: nao foi possivel restringir ${BACKUP_DIR} a 0700 (o diretorio e de outro usuario?); o arquivo do backup e criado 0600 mesmo assim."
fi
# Archives written by earlier versions of this script were born 0644.
chmod 600 "$BACKUP_DIR"/step-ca-*.tar.gz 2>/dev/null || true

STAMP=$(date +%F-%H%M)
TARGET="${BACKUP_DIR}/step-ca-${STAMP}.tar.gz"
# A NEW file with an unpredictable name, created exclusively by this user
# (mktemp: O_EXCL, 0600): never one someone else prepared under a known name.
PARTIAL=$(mktemp "${BACKUP_DIR}/.step-ca-${STAMP}.XXXXXX") || {
    err "Nao foi possivel criar o arquivo temporario em ${BACKUP_DIR}."
    exit 1
}

log "Criando ${TARGET}..."
# tar writes to stdout and the file is created HERE, by this shell (with the
# umask above): it belongs to whoever runs the script. Written by the
# container, it was root's and 0644 — readable by every user of the host. The
# temporary name keeps an interrupted tar from counting as a backup in the
# retention below.
if ! docker run --rm \
    -v step-ca-data:/data:ro \
    alpine tar czf - -C /data . > "$PARTIAL"; then
    rm -f "$PARTIAL"
    err "Falha ao gerar o backup (docker run alpine tar)."
    exit 1
fi
mv -f "$PARTIAL" "$TARGET"

SIZE=$(du -h "$TARGET" | cut -f1)
ok "Backup criado: ${TARGET} (${SIZE})"

# Retention: keeps the RETAIN most recent.
KEEP="$RETAIN"
DELETED=$(cd "$BACKUP_DIR" && ls -1t step-ca-*.tar.gz 2>/dev/null | tail -n "+$((KEEP + 1))" || true)
if [ -n "$DELETED" ]; then
    echo "$DELETED" | while read -r f; do
        rm -f "${BACKUP_DIR}/${f}"
        log "Removido (retencao ${RETAIN}): ${f}"
    done
fi

# Total atual
COUNT=$(cd "$BACKUP_DIR" && ls -1 step-ca-*.tar.gz 2>/dev/null | wc -l)
log "Total de backups em ${BACKUP_DIR}: ${COUNT}"
