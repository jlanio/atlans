#!/usr/bin/env bash
# scripts/bootstrap-stepca.sh
# Second phase of the bootstrap (prod only):
#   - captures the root CA fingerprint and injects it into .env
#   - extracts intermediate.crt so Traefik can validate mTLS client certs
#   - raises the provisioner's maximum certificate lifetime (step-ca starts
#     with 24 h) and restarts step-ca
#   - issues the TLS cert for the executors' host (AGENTS_HOST, served with a
#     step-ca cert) into traefik/atlans-ca/agents.crt and agents.key
#
# Prerequisites:
#   - ./scripts/bootstrap.sh has already run
#   - `make up-prod` is up and step-ca is healthy
#
# Idempotent: does not overwrite an existing cert.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

log()  { printf '\033[1;36m[bootstrap-stepca]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[bootstrap-stepca]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[bootstrap-stepca]\033[0m %s\n' "$*" >&2; }
ok()   { printf '\033[1;32m[bootstrap-stepca]\033[0m %s\n' "$*"; }

# The executors' host: AGENTS_HOST from .env, the same one as the Traefik routers.
AGENTS_DOMAIN="${AGENTS_DOMAIN:-$(grep -E '^AGENTS_HOST=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' || true)}"
if [ -z "$AGENTS_DOMAIN" ]; then
    err "Defina AGENTS_HOST no .env: o host dos executores (ex.: agents.seu-dominio)."
    exit 1
fi

# The step-ca provisioner: STEPCA_PROVISIONER_NAME from .env (default atlans-app).
PROVISIONER="${STEPCA_PROVISIONER_NAME:-$(grep -E '^STEPCA_PROVISIONER_NAME=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' || true)}"
PROVISIONER="${PROVISIONER:-atlans-app}"

# ── 1. step-ca healthy? ──────────────────────────────────────────────────────
if ! docker compose --profile prod ps step-ca 2>/dev/null | grep -q "healthy"; then
    err "Container step-ca nao esta healthy. Rode 'make up-prod' antes."
    err "Status atual:"
    docker compose --profile prod ps step-ca || true
    exit 1
fi
log "step-ca esta healthy."

# ── 2. Capture the root CA fingerprint ───────────────────────────────────────
FINGERPRINT=$(docker compose --profile prod exec -T step-ca \
    step certificate fingerprint /home/step/certs/root_ca.crt | tr -d '\r\n')

if [ -z "$FINGERPRINT" ]; then
    err "Falha ao capturar fingerprint do root CA."
    exit 1
fi
log "Fingerprint do root CA: $FINGERPRINT"

# Atualiza .env (idempotente)
if grep -qE '^STEPCA_ROOT_FINGERPRINT=' .env; then
    sed -i.bak -E "s|^STEPCA_ROOT_FINGERPRINT=.*|STEPCA_ROOT_FINGERPRINT=${FINGERPRINT}|" .env
    rm -f .env.bak
else
    printf 'STEPCA_ROOT_FINGERPRINT=%s\n' "$FINGERPRINT" >> .env
fi
ok "STEPCA_ROOT_FINGERPRINT gravado em .env."

# ── 3. Intermediate.crt for Traefik ──────────────────────────────────────────
mkdir -p traefik/atlans-ca
if [ -s traefik/atlans-ca/intermediate.crt ]; then
    log "traefik/atlans-ca/intermediate.crt ja existe (preservado)."
else
    docker compose --profile prod exec -T step-ca \
        cat /home/step/certs/intermediate_ca.crt > traefik/atlans-ca/intermediate.crt
    chmod 644 traefik/atlans-ca/intermediate.crt
    ok "intermediate.crt copiado para traefik/atlans-ca/."
fi

# ── 4. Certificate lifetime ─────────────────────────────────────────────────
# step-ca starts with a 24 h ceiling per certificate. The cert for the
# executors' host asks for one year (below), and each enrollment asks for
# EXECUTOR_CERT_TTL_DAYS (90 days by default, at most 365): without raising the
# provisioner's ceiling, the CA refuses both ("requested duration ... is more
# than the authorized maximum").
# Idempotent; step-ca only reads the new ca.json after a restart.
docker compose --profile prod exec -T step-ca \
    step ca provisioner update "$PROVISIONER" --x509-max-dur=8760h --x509-default-dur=2160h >/dev/null
docker compose --profile prod restart step-ca >/dev/null
for _ in $(seq 1 30); do
    if docker compose --profile prod exec -T step-ca step ca health 2>/dev/null | grep -q '^ok'; then
        break
    fi
    sleep 2
done
if ! docker compose --profile prod exec -T step-ca step ca health 2>/dev/null | grep -q '^ok'; then
    err "step-ca nao voltou depois de ajustar o prazo dos certificados."
    exit 1
fi
ok "Provisioner ${PROVISIONER}: certificados de ate 1 ano (padrao 90 dias)."

# ── 5. TLS cert for the executors' host ─────────────────────────────────────
# Fixed name, the one traefik-dynamic/dynamic.yml reads; the host goes in the certificate.
CRT_PATH="traefik/atlans-ca/agents.crt"
KEY_PATH="traefik/atlans-ca/agents.key"

if [ -s "$CRT_PATH" ] && [ -s "$KEY_PATH" ]; then
    log "$CRT_PATH e $KEY_PATH ja existem (preservados)."
    log "Para renovar, apague os 2 arquivos e re-rode este script."
else
    log "Emitindo cert TLS para ${AGENTS_DOMAIN} (TTL 1 ano)..."
    docker compose --profile prod exec -T step-ca \
        step ca certificate "$AGENTS_DOMAIN" \
            "/home/step/${AGENTS_DOMAIN}.crt" \
            "/home/step/${AGENTS_DOMAIN}.key" \
            --provisioner "$PROVISIONER" \
            --provisioner-password-file /run/secrets/stepca_password \
            --not-after 8760h \
            --force

    docker compose --profile prod exec -T step-ca \
        cat "/home/step/${AGENTS_DOMAIN}.crt" > "$CRT_PATH"
    # The private key is born 600 (umask in the subshell), with no window before the chmod.
    ( umask 077 && docker compose --profile prod exec -T step-ca \
        cat "/home/step/${AGENTS_DOMAIN}.key" > "$KEY_PATH" )

    # Cleans up the step-ca volume after copying.
    docker compose --profile prod exec -T step-ca \
        sh -c "rm -f /home/step/${AGENTS_DOMAIN}.crt /home/step/${AGENTS_DOMAIN}.key"

    chmod 644 "$CRT_PATH"
    chmod 600 "$KEY_PATH"
    ok "Cert $AGENTS_DOMAIN emitido para traefik/atlans-ca/."
fi

cat <<EOF

╭──────────────────────────────────────────────────────────────────╮
│  bootstrap-stepca concluido. Proximos passos:                    │
╰──────────────────────────────────────────────────────────────────╯

  1. Recrie a API (o container so le o .env, com o fingerprint, ao ser
     criado) e reinicie o Traefik (os certificados):
       docker compose --profile prod up -d api-prod
       docker compose --profile prod restart traefik

  2. Backup imediato do volume step-ca-data:
       make backup-stepca

  3. Smoke test:
       make smoke

  4. Criar admin inicial:
       make seed-admin

EOF
