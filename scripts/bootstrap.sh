#!/usr/bin/env bash
# scripts/bootstrap.sh
# Prepara um host limpo para subir o Atlans:
#   - cria volume external `step-ca-data`
#   - cria diretorios secrets/, traefik/atlans-ca/, certs/, backups/
#   - gera secrets/stepca_password.txt
#   - copia .env.example -> .env e substitui placeholders dev por secrets fortes
#
# Idempotente: rodar duas vezes nao destroi nada criado antes.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

log()  { printf '\033[1;36m[bootstrap]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[bootstrap]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[bootstrap]\033[0m %s\n' "$*" >&2; }
ok()   { printf '\033[1;32m[bootstrap]\033[0m %s\n' "$*"; }

# ── 1. Verificar pre-requisitos ──────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
    err "Docker nao encontrado. Instale antes: https://docs.docker.com/engine/install/"
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    err "Docker Compose v2 nao encontrado (use 'docker compose', nao 'docker-compose')."
    exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
    err "openssl nao encontrado. Necessario para gerar secrets."
    exit 1
fi
log "Pre-requisitos OK (docker, compose v2, openssl)."

# ── 2. Volume external step-ca-data ──────────────────────────────────────────
if docker volume inspect step-ca-data >/dev/null 2>&1; then
    log "Volume step-ca-data ja existe (preservado)."
else
    docker volume create step-ca-data >/dev/null
    ok "Volume step-ca-data criado."
fi

# ── 3. Diretorios do host ────────────────────────────────────────────────────
mkdir -p secrets traefik/atlans-ca certs backups
log "Diretorios secrets/, traefik/atlans-ca/, certs/, backups/ prontos."

# ── 4. Secret stepca_password ────────────────────────────────────────────────
if [ -s secrets/stepca_password.txt ]; then
    log "secrets/stepca_password.txt ja existe (preservado)."
    STEPCA_PASS="$(cat secrets/stepca_password.txt)"
else
    STEPCA_PASS="$(openssl rand -base64 48 | tr -d '\n')"
    # umask no subshell: o arquivo ja NASCE 600 (sem a janela entre criar e o chmod).
    ( umask 077 && printf '%s' "$STEPCA_PASS" > secrets/stepca_password.txt )
    chmod 600 secrets/stepca_password.txt
    ok "secrets/stepca_password.txt gerado (chmod 600)."
fi

# A step-ca roda como o usuario step (UID 1000) e le este arquivo pelo secret do
# compose, que o monta com o dono e o modo do host: com outro dono e modo 600,
# ela nao o le e nunca fica healthy (e a API, que depende dela, nao sobe).
# So no Linux: no Docker Desktop (Mac, Windows) o dono do host nao chega ao container.
DONO_DO_SEGREDO="$(ls -n secrets/stepca_password.txt | awk '{print $3}')"
if [ "$(uname -s)" = "Linux" ] && [ "$DONO_DO_SEGREDO" != "1000" ]; then
    if [ "$(id -u)" = "0" ]; then
        chown 1000:1000 secrets/stepca_password.txt
        ok "secrets/stepca_password.txt agora e do UID 1000, o usuario da step-ca."
    else
        warn "secrets/stepca_password.txt e do UID $DONO_DO_SEGREDO, e a step-ca (UID 1000) nao vai le-lo:"
        warn "  sudo chown 1000:1000 secrets/stepca_password.txt"
    fi
fi

# ── 5. .env a partir do .env.example ─────────────────────────────────────────
# Helper: substitui (ou injeta) chave=valor em um arquivo .env.
upsert_env() {
    local file="$1" key="$2" value="$3"
    # Escapa caracteres especiais para sed
    local escaped
    escaped=$(printf '%s' "$value" | sed -e 's/[\/&|]/\\&/g')
    if grep -qE "^${key}=" "$file"; then
        sed -i.bak -E "s|^${key}=.*|${key}=\"${escaped}\"|" "$file" && rm -f "$file.bak"
    else
        printf '%s="%s"\n' "$key" "$value" >> "$file"
    fi
}

gen_secret() { openssl rand -base64 32 | tr -d '\n'; }

if [ -f .env ]; then
    log ".env ja existe (preservado). Pulando geracao de secrets."
else
    ( umask 077 && cp .env.example .env )
    chmod 600 .env
    log ".env criado a partir de .env.example (chmod 600). Rotacionando secrets de dev..."

    upsert_env .env APP_SECRET                  "$(gen_secret)"
    upsert_env .env FERNET_KEY                  "$(gen_secret)"
    upsert_env .env EXECUTOR_SIGNING_KEY           "$(gen_secret)"
    upsert_env .env OTP_PEPPER                  "$(gen_secret)"
    upsert_env .env AUTH_SECRET                 "$(gen_secret)"
    upsert_env .env REDIS_PASSWORD              "$(openssl rand -hex 32)"
    upsert_env .env MINIO_ROOT_PASSWORD         "$(gen_secret)"
    upsert_env .env STEPCA_PROVISIONER_PASSWORD "$STEPCA_PASS"

    ok ".env gerado com secrets novos. NUNCA commite este arquivo."
fi

# ── 6. Checklist final ───────────────────────────────────────────────────────
cat <<'EOF'

╭──────────────────────────────────────────────────────────────────╮
│  Bootstrap concluido. Proximos passos manuais:                   │
╰──────────────────────────────────────────────────────────────────╯

  1. Edite .env:
       - DATABASE_URL ........ aponte para seu Postgres + extensions postgis/uuid-ossp
       - ALLOWED_ORIGINS ..... dominios reais em prod (NUNCA '*' em prod)
       - FRONTEND_URL ........ URL publica do frontend
       - PUBLIC_HOST, AGENTS_HOST, S3_HOST ... os hosts do site, dos executores
         e do S3 (as regras do Traefik)
       - BORDA_MIDDLEWARE e BORDA_FAIXAS_CONFIAVEIS ... com ou sem CDN na
         frente (ver .env.example)
       - RESEND_API_KEY ou SMTP_HOST/SMTP_* ... o transporte de e-mail, e
         EMAIL_FROM, o remetente
       - MINIO_ROOT_USER ..... troque o change-me
       - AUTH_URL e MINIO_EXTERNAL_ENDPOINT ... as URLs publicas do site e do S3

  2. (Apenas prod) coloque o certificado do site em ./certs/
       cert.pem  e  key.pem (o de origem da Cloudflare, um do Let's Encrypt
       ou outro; ou aponte SSL_CERT_DIR para onde eles estao)

  3. Configure o DNS:
       <PUBLIC_HOST>   A  -> IP   (atras do CDN, se usar um)
       <AGENTS_HOST>   A  -> IP   (direto, NUNCA atras de CDN)  *obrigatorio*
       <S3_HOST>       A  -> IP   (atras do CDN, se usar um)

  4. Suba:
       make up-dev     # dev
       make up-prod    # prod
       ./scripts/bootstrap-stepca.sh   # apenas prod, apos step-ca healthy
       make smoke
       make seed-admin

  Documentacao:
       README.md
       docs/operations.md
       docs/mtls-bootstrap.md
EOF
