#!/usr/bin/env bash
# scripts/smoke.sh
# Validates after startup that the stack came up correctly.
# Automatically detects whether the prod profile is active by the presence of
# the api-prod or step-ca containers. The production API and web do not publish
# a port on the host (Traefik talks to them over the compose network): their
# checks run inside their own container.
#
# Exit 0 = all checks OK; exit 1 = at least one failed.

set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PASS=0
FAIL=0
WARN=0

pass() { printf '\033[1;32m  OK\033[0m  %s\n' "$*";  PASS=$((PASS + 1)); }
fail() { printf '\033[1;31m FAIL\033[0m  %s\n' "$*"; FAIL=$((FAIL + 1)); }
warn() { printf '\033[1;33m WARN\033[0m  %s\n' "$*"; WARN=$((WARN + 1)); }
info() { printf '\033[1;36m  ::\033[0m  %s\n' "$*"; }

# Detecta profile ativo
if docker compose ps --services --filter status=running 2>/dev/null | grep -q "^api-prod$"; then
    PROFILE=prod
    API_SVC=api-prod
    WEB_SVC=web-prod
elif docker compose ps --services --filter status=running 2>/dev/null | grep -q "^api$"; then
    PROFILE=dev
    API_SVC=api
    WEB_SVC=web-dev
else
    fail "Nenhum container api/api-prod rodando. Suba a stack antes (make up-dev|up-prod)."
    exit 1
fi
info "Profile detectado: $PROFILE (api service: $API_SVC)"

# An API URL, read from inside its own container (the image's Python).
api_get() {
    docker compose exec -T "$API_SVC" python -c \
        "import sys, urllib.request; sys.stdout.write(urllib.request.urlopen(sys.argv[1], timeout=10).read().decode())" \
        "http://localhost:8000$1" 2>/dev/null
}

# 1. API ping
if api_get /ping >/dev/null; then
    pass "API responde em /ping"
else
    fail "API nao responde em /ping (docker compose logs $API_SVC)"
fi

# 2. Alembic schema atualizado
if docker compose exec -T "$API_SVC" alembic current 2>/dev/null | grep -qE '[a-f0-9]+'; then
    pass "Schema Alembic aplicado"
else
    fail "alembic current vazio — schema nao aplicado ou DB inacessivel"
fi

# 3. Redis ping
REDIS_PASS=$(grep -E '^REDIS_PASSWORD=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"')
# The password goes via the REDISCLI_AUTH variable, not `-a`: in argv it shows up in `ps`.
if [ -n "$REDIS_PASS" ] && docker compose exec -T -e REDISCLI_AUTH="$REDIS_PASS" redis redis-cli --no-auth-warning ping 2>/dev/null | grep -q PONG; then
    pass "Redis responde PONG"
else
    fail "Redis nao responde (verifique REDIS_PASSWORD no .env e container redis)"
fi

# 4. MinIO ready (/minio/health/live requires no auth). From inside the API
# container, over the compose network: depends neither on curl on the host
# nor on port 9000 being published.
if docker compose exec -T "$API_SVC" python -c \
        "import urllib.request; urllib.request.urlopen('http://minio:9000/minio/health/live', timeout=10)" 2>/dev/null; then
    pass "MinIO healthy"
else
    fail "MinIO nao responde em http://minio:9000/minio/health/live (docker compose logs minio)"
fi

# 5. step-ca (apenas prod)
if [ "$PROFILE" = "prod" ]; then
    if docker compose --profile prod ps step-ca 2>/dev/null | grep -q "healthy"; then
        pass "step-ca healthy"
    else
        fail "step-ca nao esta healthy"
    fi
fi

# 6. Web frontend (the image's Alpine wget)
if docker compose exec -T "$WEB_SVC" wget -q -O /dev/null "http://localhost:3000/" 2>/dev/null; then
    pass "Web frontend responde em :3000"
else
    fail "Web frontend nao responde em :3000 (docker compose logs $WEB_SVC)"
fi

# 7. install.sh with the CA fingerprint (prod only). The API container reads
# .env only when it is created: after bootstrap-stepca, without recreating the
# API, the executors' installer goes out without the pinned CA.
if [ "$PROFILE" = "prod" ]; then
    INSTALL_SH=$(api_get /executores/install || true)
    if printf '%s' "$INSTALL_SH" | grep -qiE 'ATLANS_CA_SHA256:-[0-9a-f]{64}'; then
        pass "install.sh servido com o fingerprint da CA"
    else
        fail "install.sh sem o fingerprint da CA: rode o bootstrap-stepca e recrie a API (docker compose --profile prod up -d api-prod)"
    fi
    # The host that install.sh announces to the executors must be the one Traefik
    # routes (AGENTS_HOST): a diverging AGENTS_URL would only show up on the
    # executor's machine, as a DNS failure.
    AGENTS_HOST_ENV=$(grep -E '^AGENTS_HOST=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"')
    SERVIDO=$(printf '%s' "$INSTALL_SH" | grep -E '^SERVER="' | head -1 | cut -d'"' -f2)
    if [ -z "$AGENTS_HOST_ENV" ]; then
        warn "AGENTS_HOST vazio no .env — pulando a conferencia do host anunciado no install.sh"
    elif [ "$SERVIDO" = "wss://$AGENTS_HOST_ENV" ]; then
        pass "install.sh anuncia o AGENTS_HOST (wss://$AGENTS_HOST_ENV)"
    else
        fail "install.sh anuncia '$SERVIDO', mas o Traefik roteia os executores em '$AGENTS_HOST_ENV': acerte AGENTS_URL no .env (ou apague-a) e recrie a API"
    fi
fi

# 8. DNS-only check em prod
if [ "$PROFILE" = "prod" ]; then
    AGENTS_DOMAIN="${AGENTS_DOMAIN:-$(grep -E '^AGENTS_HOST=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' || true)}"
    EXPECTED=$(grep -E '^STEPCA_ROOT_FINGERPRINT=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr 'A-Z' 'a-z')
    if [ -z "$EXPECTED" ]; then
        warn "STEPCA_ROOT_FINGERPRINT vazio em .env — pulando DNS-only check"
    elif ! command -v openssl >/dev/null 2>&1; then
        warn "openssl nao instalado no host — pulando DNS-only check"
    else
        # Grabs the served cert and computes the issuer fingerprint (the full chain is not reachable via a one-shot openssl — we check the subject CN).
        # Simpler, more robust validation: the remote cert must be signed by the internal CA.
        # If Cloudflare is proxied, the remote cert will be Cloudflare's (issuer != step-ca).
        ISSUER=$(echo | openssl s_client -connect "${AGENTS_DOMAIN}:443" -servername "$AGENTS_DOMAIN" 2>/dev/null | openssl x509 -issuer -noout 2>/dev/null | head -1)
        if echo "$ISSUER" | grep -qiE "step|atlans"; then
            pass "${AGENTS_DOMAIN} servido com cert da CA interna (DNS-only OK)"
        elif [ -z "$ISSUER" ]; then
            warn "${AGENTS_DOMAIN:-AGENTS_HOST} inacessivel publicamente (DNS resolve? firewall? AGENTS_HOST no .env?)"
        else
            fail "${AGENTS_DOMAIN} servido por '$ISSUER' — provavel CDN na frente; mTLS quebrara"
        fi
    fi
fi

# ── Resumo ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL + WARN))
echo
if [ $FAIL -eq 0 ]; then
    printf '\033[1;32mResultado: %d/%d OK\033[0m' "$PASS" "$TOTAL"
    [ $WARN -gt 0 ] && printf ' (%d warns)' "$WARN"
    echo
    exit 0
else
    printf '\033[1;31mResultado: %d falhas, %d ok, %d warns (total %d)\033[0m\n' \
        "$FAIL" "$PASS" "$WARN" "$TOTAL"
    exit 1
fi
