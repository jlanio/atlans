#!/usr/bin/env bash
# scripts/bootstrap.sh
# Prepares a clean host to bring up Atlans:
#   - creates the external volume `step-ca-data`
#   - creates the directories secrets/, traefik/atlans-ca/, certs/, backups/
#   - generates secrets/stepca_password.txt
#   - copies .env.example -> .env and replaces the dev placeholders with strong secrets
#   - asks for what only you know (the database; in production, the domain and
#     the e-mail transport) and writes it to .env
#
# Usage: ./scripts/bootstrap.sh [--no-prompt]   (make bootstrap ARGS=--no-prompt)
#   --no-prompt  asks nothing: .env keeps the example values, to edit by hand.
#                Without a terminal (CI, a pipe) it never asks either.
#
# Idempotent: running it twice does not destroy anything created before, and it
# only asks for what is still the example value.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

log()  { printf '\033[1;36m[bootstrap]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[bootstrap]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[bootstrap]\033[0m %s\n' "$*" >&2; }
ok()   { printf '\033[1;32m[bootstrap]\033[0m %s\n' "$*"; }

PERGUNTAR=1
for arg in "$@"; do
    case "$arg" in
        --no-prompt) PERGUNTAR=0 ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)
            err "Opcao desconhecida: $arg (use --help)."
            exit 2 ;;
    esac
done
# No terminal (CI, a pipe): never ask.
if [ ! -t 0 ] || [ ! -t 1 ]; then
    PERGUNTAR=0
fi

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

# ── 3. Host directories ──────────────────────────────────────────────────────
mkdir -p secrets traefik/atlans-ca certs backups
log "Diretorios secrets/, traefik/atlans-ca/, certs/, backups/ prontos."

# ── 4. Secret stepca_password ────────────────────────────────────────────────
if [ -s secrets/stepca_password.txt ]; then
    log "secrets/stepca_password.txt ja existe (preservado)."
    STEPCA_PASS="$(cat secrets/stepca_password.txt)"
else
    STEPCA_PASS="$(openssl rand -base64 48 | tr -d '\n')"
    # umask in the subshell: the file is BORN 600 (no window between creating it and the chmod).
    ( umask 077 && printf '%s' "$STEPCA_PASS" > secrets/stepca_password.txt )
    chmod 600 secrets/stepca_password.txt
    ok "secrets/stepca_password.txt gerado (chmod 600)."
fi

# step-ca runs as the step user (UID 1000) and reads this file through the
# compose secret, which mounts it with the host's owner and mode: with another
# owner and mode 600, it cannot read it and never becomes healthy (and the API,
# which depends on it, does not come up).
# Linux only: on Docker Desktop (Mac, Windows) the host's owner does not reach the container.
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

# ── 5. .env from .env.example ────────────────────────────────────────────────
# Helper: replaces (or injects) key=value in a .env file.
upsert_env() {
    local file="$1" key="$2" value="$3"
    # Escapes special characters for sed
    local escaped
    escaped=$(printf '%s' "$value" | sed -e 's/[\/&|]/\\&/g')
    if grep -qE "^${key}=" "$file"; then
        sed -i.bak -E "s|^${key}=.*|${key}=\"${escaped}\"|" "$file" && rm -f "$file.bak"
    else
        # A file with no final newline would glue the new key onto its last line.
        [ -s "$file" ] && [ -n "$(tail -c 1 "$file")" ] && printf '\n' >> "$file"
        printf '%s="%s"\n' "$key" "$value" >> "$file"
    fi
}

# Literal value, in single quotes: neither compose nor python-dotenv expands a
# `$` there. For what the person types (an SMTP password), not for generated values.
upsert_env_literal() {
    local file="$1" key="$2" value="$3"
    grep -vE "^${key}=" "$file" > "$file.tmp" || true
    [ -s "$file.tmp" ] && [ -n "$(tail -c 1 "$file.tmp")" ] && printf '\n' >> "$file.tmp"
    printf "%s='%s'\n" "$key" "$value" >> "$file.tmp"
    cat "$file.tmp" > "$file" && rm -f "$file.tmp"
}

env_get() {
    grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true
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
    # The user too: `change-me` is public (it is in .env.example), and nobody
    # types it, since the API and MinIO read it from the same .env. Only on a
    # new .env: on a MinIO that already has data, changing it is not harmless.
    upsert_env .env MINIO_ROOT_USER             "atlans-$(openssl rand -hex 6)"
    upsert_env .env STEPCA_PROVISIONER_PASSWORD "$STEPCA_PASS"

    ok ".env gerado com secrets novos. NUNCA commite este arquivo."
fi

# ── 5b. What only you know ───────────────────────────────────────────────────
# Asked only on a terminal, and only while DATABASE_URL is still the example:
# a second run asks nothing. Enter takes the value in brackets.
perguntar() {  # <texto> [padrao]: the answer, never empty
    local resposta
    while :; do
        if [ -n "${2:-}" ]; then
            read -r -p "  $1 [$2]: " resposta </dev/tty
            resposta="${resposta:-$2}"
        else
            read -r -p "  $1: " resposta </dev/tty
        fi
        [ -n "$resposta" ] && break
    done
    printf '%s' "$resposta"
}
perguntar_opcional() {  # <texto>: the answer, maybe empty
    local resposta
    read -r -p "  $1 (Enter para deixar vazio): " resposta </dev/tty
    printf '%s' "$resposta"
}
perguntar_segredo() {  # <texto>: not echoed, never empty
    local resposta
    while :; do
        read -r -s -p "  $1: " resposta </dev/tty
        printf '\n' >&2
        [ -n "$resposta" ] && break
    done
    printf '%s' "$resposta"
}
perguntar_opcao() {  # <texto> <padrao> <opcao>...: one of the options
    local texto="$1" padrao="$2" resposta opcao
    shift 2
    while :; do
        resposta="$(perguntar "$texto ($(IFS=/; echo "$*"))" "$padrao")"
        for opcao in "$@"; do
            [ "$resposta" = "$opcao" ] && { printf '%s' "$resposta"; return; }
        done
        printf '  Responda %s.\n' "$(IFS=,; echo "$*")" >&2
    done
}
perguntar_host() {  # <texto> [padrao]: a host name, without scheme or path
    local resposta
    while :; do
        resposta="$(perguntar "$1" "${2:-}")"
        printf '%s' "$resposta" | grep -qE '^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$' && break
        printf '  So o nome do host (ex.: atlans.exemplo.org), sem https:// nem barra.\n' >&2
    done
    printf '%s' "$resposta"
}
# Percent-encodes a URL component: a password with @ : / # % ? breaks the URL.
urlencode() {
    local LC_ALL=C texto="$1" i c saida=""
    for (( i = 0; i < ${#texto}; i++ )); do
        c="${texto:i:1}"
        case "$c" in
            [A-Za-z0-9.~_-]) saida+="$c" ;;
            *) saida+="$(printf '%%%02X' "'$c")" ;;
        esac
    done
    printf '%s' "$saida"
}

if [ "$PERGUNTAR" = "1" ] && env_get DATABASE_URL | grep -q '<usuario>'; then
    echo
    log "Configuracao inicial. Enter aceita o valor entre colchetes; --no-prompt pula esta etapa."
    MODO="$(perguntar_opcao "Instalacao" "dev" dev prod)"

    echo
    log "Banco PostgreSQL (com PostGIS). Na mesma maquina, use host.docker.internal: dentro do container, localhost e o proprio container."
    DB_HOST="$(perguntar_host "Host" "host.docker.internal")"
    while :; do
        DB_PORTA="$(perguntar "Porta" "5432")"
        printf '%s' "$DB_PORTA" | grep -qE '^[0-9]{1,5}$' && break
        printf '  Um numero de porta.\n' >&2
    done
    DB_NOME="$(perguntar "Nome do banco" "atlans")"
    DB_USUARIO="$(perguntar "Usuario" "atlans")"
    DB_SENHA="$(perguntar_segredo "Senha")"
    DB_TLS="$(perguntar_opcao "TLS na conexao" "nao" nao require verify-full)"
    DATABASE_URL="postgresql+asyncpg://$(urlencode "$DB_USUARIO"):$(urlencode "$DB_SENHA")@${DB_HOST}:${DB_PORTA}/$(urlencode "$DB_NOME")"
    [ "$DB_TLS" != "nao" ] && DATABASE_URL="${DATABASE_URL}?ssl=${DB_TLS}"
    upsert_env .env DATABASE_URL "$DATABASE_URL"
    unset DB_SENHA DATABASE_URL
    ok "DATABASE_URL gravado (a senha vai codificada na URL)."

    if [ "$MODO" = "prod" ]; then
        echo
        log "Os tres nomes do dominio, cada um com DNS para este servidor (docs/self-hosting.md)."
        PUBLIC="$(perguntar_host "Site (PUBLIC_HOST)")"
        AGENTS="$(perguntar_host "Executores (AGENTS_HOST, nunca atras de CDN)" "agents.${PUBLIC}")"
        S3="$(perguntar_host "Arquivos (S3_HOST)" "s3.${PUBLIC}")"
        upsert_env .env PUBLIC_HOST "$PUBLIC"
        upsert_env .env AGENTS_HOST "$AGENTS"
        upsert_env .env S3_HOST "$S3"
        # The addresses that derive from them (the minimum of docs/self-hosting.md).
        upsert_env .env FRONTEND_URL "https://${PUBLIC}"
        upsert_env .env AUTH_URL "https://${PUBLIC}"
        upsert_env .env ALLOWED_ORIGINS "https://${PUBLIC}"
        upsert_env .env MINIO_EXTERNAL_ENDPOINT "https://${S3}"
        upsert_env .env MINIO_API_CORS_ALLOW_ORIGIN "https://${PUBLIC}"
        ok "Hosts e enderecos gravados (FRONTEND_URL, AUTH_URL, ALLOWED_ORIGINS, MINIO_EXTERNAL_ENDPOINT)."

        echo
        log "Envio de e-mail (verificacao de conta, senha, alertas)."
        TRANSPORTE="$(perguntar_opcao "Transporte" "resend" resend smtp nenhum)"
        case "$TRANSPORTE" in
            resend)
                upsert_env .env RESEND_API_KEY "$(perguntar_segredo "Chave da API do Resend")"
                ;;
            smtp)
                upsert_env .env SMTP_HOST "$(perguntar_host "Servidor SMTP")"
                upsert_env .env SMTP_PORT "$(perguntar "Porta" "587")"
                upsert_env .env SMTP_SEGURANCA "$(perguntar_opcao "Seguranca" "starttls" starttls ssl nenhuma)"
                SMTP_USUARIO="$(perguntar_opcional "Usuario")"
                if [ -n "$SMTP_USUARIO" ]; then
                    upsert_env .env SMTP_USERNAME "$SMTP_USUARIO"
                    while :; do
                        SMTP_SENHA="$(perguntar_segredo "Senha")"
                        case "$SMTP_SENHA" in
                            *"'"*) printf "  A senha tem aspas simples ('): grave-a a mao no .env depois.\n" >&2 ;;
                            *) upsert_env_literal .env SMTP_PASSWORD "$SMTP_SENHA"; break ;;
                        esac
                    done
                    unset SMTP_SENHA
                fi
                ;;
            nenhum)
                warn "Sem transporte, os e-mails vao para o log da API. Quem se cadastrar nao recebe a verificacao: veja EXIGIR_EMAIL_VERIFICADO no .env.example."
                ;;
        esac
        if [ "$TRANSPORTE" != "nenhum" ]; then
            upsert_env .env EMAIL_FROM "$(perguntar "Remetente" "Atlans <noreply@${PUBLIC}>")"
        fi
        ok "E-mail configurado."
    fi
    echo
fi

# ── 6. Range of the proxy-net network ────────────────────────────────────────
# proxy-net has a fixed range (PROXY_NET_SUBNET, default 172.18.0.0/16 in the
# compose file), and 172.18 is the first range Docker hands out on its own: any
# other network (another project's, or this project's backend/dev-net created
# first) takes it and `up` fails with "Pool overlaps with other one on this
# address space". So the range is pinned in .env here, after checking it is free.
# The compose default stays 172.18: compose recreates a network whose range
# changed, and a new default would move proxy-net on servers already running.
ip2int() {
    local IFS=.
    # shellcheck disable=SC2086
    set -- $1
    echo $(( ($1 << 24) | ($2 << 16) | ($3 << 8) | $4 ))
}
# cidr_overlap A B: true when the IPv4 ranges A and B share any address.
cidr_overlap() {
    local n1="${1%/*}" l1="${1#*/}" n2="${2%/*}" l2="${2#*/}" l mask
    [ "$l1" = "$1" ] && l1=32
    [ "$l2" = "$2" ] && l2=32
    l=$(( l1 < l2 ? l1 : l2 ))
    mask=$(( l == 0 ? 0 : (0xFFFFFFFF << (32 - l)) & 0xFFFFFFFF ))
    [ $(( $(ip2int "$n1") & mask )) -eq $(( $(ip2int "$n2") & mask )) ]
}
# cidr_contains OUTER INNER: true when INNER lies entirely inside OUTER.
cidr_contains() {
    local lo="${1#*/}" li="${2#*/}"
    [ "$lo" = "$1" ] && lo=32
    [ "$li" = "$2" ] && li=32
    [ "$lo" -le "$li" ] && cidr_overlap "$1" "$2"
}
# IPv4 ranges already in use: Docker networks (except proxy-net itself) and,
# on Linux, the host routes (VPN, the WSL network, the LAN).
used_ranges() {
    local net
    for net in $(docker network ls -q 2>/dev/null); do
        docker network inspect "$net" \
            --format '{{if ne .Name "proxy-net"}}{{range .IPAM.Config}}{{.Subnet}} {{end}}{{end}}' 2>/dev/null || true
    done | tr ' ' '\n'
    if command -v ip >/dev/null 2>&1; then
        ip -4 route show 2>/dev/null | awk '$1 != "default" {print $1}'
    fi
}
is_ipv4_cidr() { printf '%s' "$1" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+(/[0-9]+)?$'; }
range_free() {
    local r
    while read -r r; do
        is_ipv4_cidr "$r" || continue
        cidr_overlap "$1" "$r" && return 1
    done <<< "$USED_RANGES"
    return 0
}

PROXY_SUBNET_ATUAL="$(docker network inspect proxy-net \
    --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' 2>/dev/null | awk '{print $1}' || true)"
PROXY_SUBNET_ENV="$(env_get PROXY_NET_SUBNET)"

if [ -n "$PROXY_SUBNET_ATUAL" ]; then
    # The network already exists: keep its range (changing it moves Traefik
    # to another range and can break TRUSTED_PROXIES).
    if [ -z "$PROXY_SUBNET_ENV" ]; then
        upsert_env .env PROXY_NET_SUBNET "$PROXY_SUBNET_ATUAL"
        ok "proxy-net ja existe em $PROXY_SUBNET_ATUAL: fixado em PROXY_NET_SUBNET no .env."
    elif [ "$PROXY_SUBNET_ENV" != "$PROXY_SUBNET_ATUAL" ]; then
        warn "proxy-net existe em $PROXY_SUBNET_ATUAL, mas o .env pede PROXY_NET_SUBNET=$PROXY_SUBNET_ENV:"
        warn "  o proximo 'up' recria a rede na faixa do .env. Se nao era a intencao,"
        warn "  ajuste PROXY_NET_SUBNET=$PROXY_SUBNET_ATUAL no .env."
    else
        log "proxy-net em $PROXY_SUBNET_ATUAL (igual ao .env)."
    fi
    PROXY_SUBNET_FINAL="$PROXY_SUBNET_ENV"
    [ -z "$PROXY_SUBNET_FINAL" ] && PROXY_SUBNET_FINAL="$PROXY_SUBNET_ATUAL"
else
    USED_RANGES="$(used_ranges)"
    if [ -n "$PROXY_SUBNET_ENV" ]; then
        if range_free "$PROXY_SUBNET_ENV"; then
            log "PROXY_NET_SUBNET=$PROXY_SUBNET_ENV esta livre."
        else
            err "PROXY_NET_SUBNET=$PROXY_SUBNET_ENV (no .env) ja esta em uso por outra rede:"
            err "  o 'up' vai falhar com 'Pool overlaps'. Escolha outra faixa livre no .env"
            err "  (veja 'docker network ls' e 'ip -4 route')."
            exit 1
        fi
        PROXY_SUBNET_FINAL="$PROXY_SUBNET_ENV"
    else
        # /16 ranges inside 172.16.0.0/12 (the compose default of TRUSTED_PROXIES),
        # starting with the ones Docker reaches last when it picks on its own.
        PROXY_SUBNET_FINAL=""
        for oct in 29 30 31 28 27 26 25 24 23 22 21 20 19 18 16; do
            if range_free "172.$oct.0.0/16"; then
                PROXY_SUBNET_FINAL="172.$oct.0.0/16"
                break
            fi
        done
        if [ -z "$PROXY_SUBNET_FINAL" ]; then
            err "Nenhuma faixa /16 livre em 172.16.0.0/12 para a proxy-net."
            err "  Defina PROXY_NET_SUBNET no .env (e TRUSTED_PROXIES cobrindo-a)."
            exit 1
        fi
        upsert_env .env PROXY_NET_SUBNET "$PROXY_SUBNET_FINAL"
        ok "PROXY_NET_SUBNET=$PROXY_SUBNET_FINAL (faixa livre) gravado no .env."
    fi
fi

# The API only accepts the mTLS cert header from TRUSTED_PROXIES: proxy-net must be inside it.
TRUSTED_ENV="$(env_get TRUSTED_PROXIES)"
if [ -n "$TRUSTED_ENV" ] && is_ipv4_cidr "$PROXY_SUBNET_FINAL"; then
    COBERTO=false
    for faixa in $(printf '%s' "$TRUSTED_ENV" | tr ',' ' '); do
        if is_ipv4_cidr "$faixa" && cidr_contains "$faixa" "$PROXY_SUBNET_FINAL"; then
            COBERTO=true
            break
        fi
    done
    if [ "$COBERTO" = false ]; then
        warn "TRUSTED_PROXIES=$TRUSTED_ENV nao cobre a proxy-net ($PROXY_SUBNET_FINAL):"
        warn "  os executores vao receber 401. Inclua a faixa em TRUSTED_PROXIES no .env."
    fi
fi

# ── 7. Checklist final ───────────────────────────────────────────────────────
cat <<'EOF'

╭──────────────────────────────────────────────────────────────────╮
│  Bootstrap concluido. Proximos passos manuais:                   │
╰──────────────────────────────────────────────────────────────────╯

EOF

# Item 1 lists only what is still the example value: what the questions above
# filled in does not need editing again.
echo "  1. Revise o .env. Ainda falta:"
if env_get DATABASE_URL | grep -q '<usuario>'; then
    echo "       - DATABASE_URL ........ aponte para seu Postgres + extensions postgis/uuid-ossp"
fi
if [ "$(env_get MINIO_ROOT_USER)" = "change-me" ]; then
    echo "       - MINIO_ROOT_USER ..... troque o change-me"
fi
if [ "$(env_get PUBLIC_HOST)" = "localhost" ]; then
    cat <<'EOF'
       - (apenas prod) PUBLIC_HOST, AGENTS_HOST, S3_HOST ... os hosts do site,
         dos executores e do S3, e as URLs que derivam deles: FRONTEND_URL,
         AUTH_URL, ALLOWED_ORIGINS (NUNCA '*' em prod), MINIO_EXTERNAL_ENDPOINT
EOF
fi
if [ -z "$(env_get RESEND_API_KEY)" ] && [ -z "$(env_get SMTP_HOST)" ]; then
    echo "       - (apenas prod) RESEND_API_KEY ou SMTP_* ... o envio de e-mail, e EMAIL_FROM"
fi
cat <<'EOF'
       - BORDA_MIDDLEWARE e BORDA_FAIXAS_CONFIAVEIS ... com ou sem CDN na
         frente (ver .env.example)

  2. Crie as extensoes no banco do DATABASE_URL, uma vez, como SUPERUSUARIO
     (o usuario do Atlans nao precisa ser; sem isso o 'alembic upgrade head'
     para em "permission denied to create extension postgis"):
       sudo -u postgres psql -d <banco> -c 'CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
     Postgres em outro host: psql -h <host> -U postgres -d <banco> -c '...'
     Gerenciado (RDS, Azure, Cloud SQL): use o usuario admin do provedor.

  3. (Apenas prod) coloque o certificado do site em ./certs/
       cert.pem  e  key.pem (o de origem da Cloudflare, um do Let's Encrypt
       ou outro; ou aponte SSL_CERT_DIR para onde eles estao)

  4. Configure o DNS:
       <PUBLIC_HOST>   A  -> IP   (atras do CDN, se usar um)
       <AGENTS_HOST>   A  -> IP   (direto, NUNCA atras de CDN)  *obrigatorio*
       <S3_HOST>       A  -> IP   (atras do CDN, se usar um)

  5. Suba:
       make up-dev     # dev, ja com um executor local (cadastro automatico)
       make up-prod    # prod
       docker compose exec api alembic upgrade head        # dev (prod: api-prod)
       ./scripts/bootstrap-stepca.sh   # apenas prod, apos step-ca healthy
       make smoke
       make seed-admin

  Documentacao:
       README.md
       docs/operations.md
       docs/mtls-bootstrap.md
EOF
