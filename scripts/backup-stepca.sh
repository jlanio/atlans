#!/usr/bin/env bash
# scripts/backup-stepca.sh
# Backs up the step-ca-data volume to backups/step-ca-YYYY-MM-DD-HHMM.tar.gz.
# Keeps the 14 most recent backups; removes the older ones.
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

mkdir -p "$BACKUP_DIR"
STAMP=$(date +%F-%H%M)
TARGET="${BACKUP_DIR}/step-ca-${STAMP}.tar.gz"

log "Criando ${TARGET}..."
docker run --rm \
    -v step-ca-data:/data:ro \
    -v "${BACKUP_DIR}:/backup" \
    alpine tar czf "/backup/step-ca-${STAMP}.tar.gz" -C /data .

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
