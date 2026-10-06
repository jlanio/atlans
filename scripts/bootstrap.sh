#!/usr/bin/env bash
# scripts/bootstrap.sh
# Prepares a host to bring up Atlans, in stages:
#   1. language       of these scripts (pt, en, es), saved as ATLANS_LANG in .env
#   2. prerequisites  docker, compose v2, openssl
#   3. mode           dev (this computer) or prod (a server with a domain)
#   4. secrets        .env from .env.example with strong secrets, secrets/stepca_password.txt,
#                     the external volume step-ca-data and the host directories
#   5. CA             the password of the internal CA: .env, secrets/ and the CA
#                     already in the volume must agree (or every executor enrollment fails)
#   6. database       asks for the PostgreSQL and tests it before writing DATABASE_URL
#   7. domain         (prod) the three hosts and the addresses derived from them
#   8. e-mail         (prod) Resend, SMTP or none
#   9. network        a free range for proxy-net
#  10. summary        what is left to do, for the chosen mode
#
# Usage: ./scripts/bootstrap.sh [--no-prompt] [--lang pt|en|es] [--dev|--prod]
#        (make bootstrap ARGS="--lang en")
#   --no-prompt  asks nothing: .env keeps the example values, to edit by hand.
#                Without a terminal (CI, a pipe) it never asks either.
#   --lang       the language of the messages (default: ATLANS_LANG in .env, then
#                the system's LANG).
#   --dev/--prod skips the mode question.
#
# Idempotent: running it again destroys nothing, asks only for what is still
# the example value, and works as a checkup of what is already there.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
# shellcheck source=lib/ui.sh
. scripts/lib/ui.sh
# shellcheck source=lib/ca.sh
. scripts/lib/ca.sh

# ── Options ──────────────────────────────────────────────────────────────────
PERGUNTAR=1
LANG_OPT=""
MODO=""
while [ $# -gt 0 ]; do
    case "$1" in
        --no-prompt) PERGUNTAR=0 ;;
        --lang) LANG_OPT="${2:-}"; shift ;;
        --lang=*) LANG_OPT="${1#--lang=}" ;;
        --dev) MODO="dev" ;;
        --prod) MODO="prod" ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)
            ui_lang_load "$(ui_lang_guess)"
            ui_err "$(t opt_unknown "$1")"
            exit 2 ;;
    esac
    shift
done
# No terminal (CI, a pipe): never ask.
if [ ! -t 0 ] || [ ! -t 1 ]; then
    PERGUNTAR=0
fi

# ── .env helpers ─────────────────────────────────────────────────────────────
# Replaces (or adds) key="value" in a .env file.
upsert_env() {
    local file="$1" key="$2" value="$3" escaped
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
    grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true
}
gen_secret() { openssl rand -base64 32 | tr -d '\n'; }

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

# ── 1. Language ──────────────────────────────────────────────────────────────
IDIOMA="${LANG_OPT:-${ATLANS_LANG:-$(env_get ATLANS_LANG)}}"
ESCOLHEU_IDIOMA=0
if [ -z "$IDIOMA" ] && [ "$PERGUNTAR" = "1" ]; then
    ui_lang_load "$(ui_lang_guess)"
    ui_banner "$(t banner_bootstrap)"
    printf '\n'
    IDIOMA="$(ui_menu "Idioma · Language · Idioma" "$(ui_lang_guess)" \
        "pt|Português (Brasil)" "en|English" "es|Español")"
    ESCOLHEU_IDIOMA=1
fi
[ -z "$IDIOMA" ] && IDIOMA="$(ui_lang_guess)"
ui_lang_load "$IDIOMA"

if [ "$ESCOLHEU_IDIOMA" = "0" ]; then
    ui_banner "$(t banner_bootstrap)"
fi
ui_stages "lang prereq mode secrets ca database domain email network summary"
ui_stage lang
ui_ok "$(t lang_chosen "$(t lang_name)")"
ui_hint "$(t lang_change_hint)"

# ── 2. Prerequisites ─────────────────────────────────────────────────────────
ui_stage prereq
if ! command -v docker >/dev/null 2>&1; then
    ui_err "$(t prereq_no_docker)"
    ui_hint "https://docs.docker.com/engine/install/"
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    ui_err "$(t prereq_docker_down)"
    ui_cmd "sudo systemctl start docker"
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    ui_err "$(t prereq_no_compose)"
    exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
    ui_err "$(t prereq_no_openssl)"
    exit 1
fi
ui_ok "Docker $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '?')"
ui_ok "Docker Compose $(docker compose version --short 2>/dev/null || echo v2)"
ui_ok "OpenSSL"

# ── 3. Mode ──────────────────────────────────────────────────────────────────
# Asked on a first configuration only (DATABASE_URL still the example). Later
# runs infer it from .env: a real PUBLIC_HOST is a production install.
ui_stage mode
PRIMEIRA_VEZ=0
if [ ! -f .env ] || env_get DATABASE_URL | grep -q '<usuario>'; then
    PRIMEIRA_VEZ=1
fi
if [ -z "$MODO" ]; then
    if [ "$PRIMEIRA_VEZ" = "1" ] && [ "$PERGUNTAR" = "1" ]; then
        MODO="$(ui_menu "$(t mode_question)" dev "dev|$(t mode_dev)" "prod|$(t mode_prod)")"
    elif [ -f .env ] && [ "$(env_get PUBLIC_HOST)" != "localhost" ] && [ -n "$(env_get PUBLIC_HOST)" ]; then
        MODO="prod"
    else
        MODO="dev"
    fi
fi
ui_ok "$(t "mode_chosen_$MODO")"
if [ "$MODO" = "dev" ]; then
    ui_skip domain
    ui_skip email
fi

# ── 4. Secrets ───────────────────────────────────────────────────────────────
ui_stage secrets
if docker volume inspect step-ca-data >/dev/null 2>&1; then
    ui_info "$(t secrets_volume_kept)"
else
    docker volume create step-ca-data >/dev/null
    ui_ok "$(t secrets_volume_created)"
fi

mkdir -p secrets traefik/atlans-ca certs backups
ui_ok "$(t secrets_dirs)"

if [ -s secrets/stepca_password.txt ]; then
    ui_info "$(t secrets_stepca_kept)"
else
    # umask in the subshell: the file is BORN 600 (no window between creating it and the chmod).
    ( umask 077 && openssl rand -base64 48 | tr -d '\n' > secrets/stepca_password.txt )
    chmod 600 secrets/stepca_password.txt
    ui_ok "$(t secrets_stepca_created)"
fi

# step-ca runs as the step user (UID 1000) and reads this file through the
# compose secret, which mounts it with the host's owner and mode: with another
# owner and mode 600, it cannot read it and never becomes healthy (and the API,
# which depends on it, does not come up).
# Linux only: on Docker Desktop (Mac, Windows) the host's owner does not reach the container.
conferir_dono_do_segredo() {  # [quieto]
    local dono
    dono="$(ls -n secrets/stepca_password.txt | awk '{print $3}')"
    if [ "$(uname -s)" = "Linux" ] && [ "$dono" != "1000" ]; then
        if [ "$(id -u)" = "0" ]; then
            chown 1000:1000 secrets/stepca_password.txt
            [ -n "${1:-}" ] || ui_ok "$(t secrets_stepca_chown)"
        else
            ui_warn "$(t secrets_stepca_owner "$dono")"
            ui_cmd "sudo chown 1000:1000 secrets/stepca_password.txt"
        fi
    fi
}
conferir_dono_do_segredo

if [ -f .env ]; then
    ui_info "$(t secrets_env_kept)"
else
    ( umask 077 && cp .env.example .env )
    chmod 600 .env
    upsert_env .env APP_SECRET                  "$(gen_secret)"
    upsert_env .env FERNET_KEY                  "$(gen_secret)"
    upsert_env .env EXECUTOR_SIGNING_KEY        "$(gen_secret)"
    upsert_env .env OTP_PEPPER                  "$(gen_secret)"
    upsert_env .env AUTH_SECRET                 "$(gen_secret)"
    upsert_env .env REDIS_PASSWORD              "$(openssl rand -hex 32)"
    upsert_env .env MINIO_ROOT_PASSWORD         "$(gen_secret)"
    # The user too: `change-me` is public (it is in .env.example), and nobody
    # types it, since the API and MinIO read it from the same .env. Only on a
    # new .env: on a MinIO that already has data, changing it is not harmless.
    upsert_env .env MINIO_ROOT_USER             "atlans-$(openssl rand -hex 6)"
    upsert_env .env STEPCA_PROVISIONER_PASSWORD "$(cat secrets/stepca_password.txt)"
    ui_ok "$(t secrets_env_created)"
    ui_hint "$(t secrets_env_never_commit)"
fi
# The language goes in .env, for up.sh and the next runs.
if [ "$(env_get ATLANS_LANG)" != "$UI_LANG" ]; then
    upsert_env .env ATLANS_LANG "$UI_LANG"
fi
# The assistant answers in the language of the installation, unless set.
if ! grep -qE '^ASSISTENTE_IDIOMA=' .env; then
    upsert_env .env ASSISTENTE_IDIOMA "$(t assistant_language)"
fi

# ── 5. CA ────────────────────────────────────────────────────────────────────
# The API opens the provisioner key with STEPCA_PROVISIONER_PASSWORD (.env);
# the CA is created on the first start with secrets/stepca_password.txt and the
# volume is external, so it outlives a .env or secrets/ generated again. See
# scripts/lib/ca.sh.
ui_stage ca
SENHA_ENV="$(env_get STEPCA_PROVISIONER_PASSWORD)"
SENHA_ARQ="$(cat secrets/stepca_password.txt)"
ui_run "$(t ca_checking)" ca_state secrets/stepca_password.txt || true
ESTADO_CA="$(tail -n 1 "$UI_LOG")"

alinhar_env_com_arquivo() {
    if [ "$SENHA_ENV" != "$SENHA_ARQ" ]; then
        upsert_env .env STEPCA_PROVISIONER_PASSWORD "$SENHA_ARQ"
        SENHA_ENV="$SENHA_ARQ"
        ui_ok "$(t ca_env_synced)"
        ui_hint "$(t ca_env_synced_hint)"
    fi
}

case "$ESTADO_CA" in
    none)
        ui_ok "$(t ca_none)"
        alinhar_env_com_arquivo
        ;;
    ok)
        ui_ok "$(t ca_ok)"
        alinhar_env_com_arquivo
        ;;
    unknown)
        ui_warn "$(t ca_unknown)"
        ;;
    wrong)
        ui_warn "$(t ca_wrong)"
        ui_hint "$(t ca_wrong_why)"
        if ca_own_password_opens; then
            # The CA's own copy of its password works: realign secrets/ and .env
            # with it. Nothing in the CA changes, no certificate is lost.
            CORRIGIR=1
            if [ "$PERGUNTAR" = "1" ]; then
                ui_confirm "$(t ca_fix_question)" y || CORRIGIR=0
            fi
            if [ "$CORRIGIR" = "1" ]; then
                cp -p secrets/stepca_password.txt "secrets/stepca_password.txt.antes-$(date +%Y%m%d%H%M%S)"
                ca_copy_own_password secrets/stepca_password.txt.novo
                mv secrets/stepca_password.txt.novo secrets/stepca_password.txt
                SENHA_ARQ="$(cat secrets/stepca_password.txt)"
                if [ "$SENHA_ENV" != "$SENHA_ARQ" ]; then
                    upsert_env .env STEPCA_PROVISIONER_PASSWORD "$SENHA_ARQ"
                    SENHA_ENV="$SENHA_ARQ"
                fi
                ui_ok "$(t ca_fixed)"
                conferir_dono_do_segredo quieto
                ui_hint "$(t ca_fixed_backup)"
                ui_hint "$(t ca_fixed_restart)"
                ui_cmd "docker compose --profile $MODO up -d"
            else
                ui_hint "$(t ca_fix_later)"
            fi
        else
            # Not even the CA's own copy opens it: the volume is damaged or was
            # copied without its secrets. Recreating is only safe where no real
            # executor depends on the CA.
            ui_err "$(t ca_broken)"
            if [ "$MODO" = "dev" ]; then
                ui_hint "$(t ca_recreate_dev)"
                ui_cmd "make down"
                ui_cmd "docker volume rm step-ca-data && docker volume create step-ca-data"
                ui_cmd "make up-dev"
            else
                ui_hint "$(t ca_recreate_prod)"
                ui_hint "docs/operations.md"
            fi
        fi
        ;;
esac

# ── 6. Database ──────────────────────────────────────────────────────────────
ui_stage database

# Tests the database answers from a throwaway container: the same network path
# the API takes (host.docker.internal is the host, via host-gateway). psql
# speaks libpq and the API asyncpg, so sslmode is passed explicitly to behave
# like the API: no TLS is `disable`, as in app/core/db.py. The password goes in
# the environment, never on the command line.
# Returns 0 (ok), 1 (the database refused) or 2 (could not test from here), and
# leaves the extensions' situation in BANCO_EXT (ok, super, falta, sem-pacote).
IMAGEM_PSQL="postgres:16-alpine"
CONSULTA_BANCO="SELECT current_user || '|' || (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) || '|' || coalesce((SELECT string_agg(extname, ',') FROM pg_extension WHERE extname IN ('postgis', 'uuid-ossp')), '') || '|' || (SELECT count(*) FROM pg_available_extensions WHERE name = 'postgis')"
BANCO_EXT=""
testar_banco() {  # <host> <porta> <banco> <usuario> <senha> <tls>
    local ssl saida usuario super instaladas disponivel
    case "$6" in
        require) ssl="sslmode=require" ;;
        verify-full) ssl="sslmode=verify-full&sslrootcert=system" ;;
        *) ssl="sslmode=disable" ;;
    esac
    if ! docker image inspect "$IMAGEM_PSQL" >/dev/null 2>&1 \
        && ! ui_run "$(t db_pulling "$IMAGEM_PSQL")" docker pull -q "$IMAGEM_PSQL"; then
        ui_warn "$(t db_no_image "$IMAGEM_PSQL")"
        return 2
    fi
    export PGPASSWORD="$5"
    if ! ui_run "$(t db_testing "$1" "$2")" docker run --rm -e PGPASSWORD -e PGCONNECT_TIMEOUT=10 \
            --add-host host.docker.internal:host-gateway "$IMAGEM_PSQL" \
            psql "postgresql://$(urlencode "$4")@$1:$2/$(urlencode "$3")?${ssl}" \
            -XtAq -v ON_ERROR_STOP=1 -c "$CONSULTA_BANCO"; then
        unset PGPASSWORD
        saida="$(cat "$UI_LOG")"
        case "$saida" in
            *pg_hba.conf*) ui_warn "$(t db_hint_hba)" ;;
            *LDAP*) ui_warn "$(t db_hint_ldap)" ;;
            *"password authentication failed"*) ui_warn "$(t db_hint_password)" ;;
            *"does not exist"*) ui_warn "$(t db_hint_missing)" ;;
            *"could not translate host name"*) ui_warn "$(t db_hint_host)" ;;
            *"Connection refused"*) ui_warn "$(t db_hint_refused)" ;;
            *timeout*|*"timed out"*) ui_warn "$(t db_hint_timeout)" ;;
        esac
        return 1
    fi
    unset PGPASSWORD
    IFS='|' read -r usuario super instaladas disponivel <<< "$(tail -n 1 "$UI_LOG")"
    ui_ok "$(t db_connected "$usuario")"
    case ",$instaladas," in
        *,postgis,*) case ",$instaladas," in *,uuid-ossp,*) ui_ok "$(t db_ext_ok)"; BANCO_EXT="ok"; return 0 ;; esac ;;
    esac
    if [ "$disponivel" = "0" ]; then
        ui_warn "$(t db_ext_no_package)"
        BANCO_EXT="sem-pacote"
    elif [ "$super" = "true" ]; then
        ui_info "$(t db_ext_super "$usuario")"
        BANCO_EXT="super"
    else
        ui_warn "$(t db_ext_missing "$usuario")"
        ui_cmd "psql -d $3 -c 'CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";'"
        BANCO_EXT="falta"
    fi
    return 0
}

if env_get DATABASE_URL | grep -q '<usuario>'; then
    if [ "$PERGUNTAR" = "1" ]; then
        ui_info "$(t db_intro)"
        ui_hint "$(t db_intro_localhost)"
        printf '\n'
        DB_HOST="host.docker.internal"; DB_PORTA="5432"; DB_NOME="atlans"; DB_USUARIO="atlans"; DB_TLS="nao"
        while :; do
            # The answers of a failed try are the defaults of the next one.
            DB_HOST="$(ui_ask_host "$(t db_host)" "$DB_HOST")"
            DB_PORTA="$(ui_ask_port "$(t db_port)" "$DB_PORTA")"
            DB_NOME="$(ui_ask "$(t db_name)" "$DB_NOME")"
            DB_USUARIO="$(ui_ask "$(t db_user)" "$DB_USUARIO")"
            DB_SENHA="$(ui_ask_secret "$(t db_password)")"
            DB_TLS="$(ui_menu "$(t db_tls)" "$DB_TLS" "nao||$(t db_tls_none)" "require||$(t db_tls_require)" "verify-full||$(t db_tls_verify)")"
            printf '\n'
            while :; do
                set +e
                testar_banco "$DB_HOST" "$DB_PORTA" "$DB_NOME" "$DB_USUARIO" "$DB_SENHA" "$DB_TLS"
                RESULTADO=$?
                set -e
                [ "$RESULTADO" != "1" ] && break 2
                printf '\n'
                case "$(ui_menu "$(t db_what_now)" corrigir "corrigir||$(t db_fix)" "tentar||$(t db_retry)" "gravar||$(t db_save_anyway)")" in
                    corrigir) printf '\n'; break ;;
                    tentar) ;;
                    gravar) break 2 ;;
                esac
            done
        done
        DATABASE_URL="postgresql+asyncpg://$(urlencode "$DB_USUARIO"):$(urlencode "$DB_SENHA")@${DB_HOST}:${DB_PORTA}/$(urlencode "$DB_NOME")"
        [ "$DB_TLS" != "nao" ] && DATABASE_URL="${DATABASE_URL}?ssl=${DB_TLS}"
        upsert_env .env DATABASE_URL "$DATABASE_URL"
        unset DB_SENHA DATABASE_URL
        ui_ok "$(t db_saved)"
    else
        ui_warn "$(t db_still_example)"
        BANCO_EXT="nao-testado"
    fi
else
    ui_info "$(t db_already)"
    ui_hint "$(t db_check_hint)"
    BANCO_EXT="nao-testado"
fi

# ── 7. Domain (prod) ─────────────────────────────────────────────────────────
ui_stage domain
if [ "$MODO" = "dev" ]; then
    ui_info "$(t skipped_in_dev)"
elif [ "$(env_get PUBLIC_HOST)" != "localhost" ] && [ -n "$(env_get PUBLIC_HOST)" ]; then
    ui_ok "$(t domain_already "$(env_get PUBLIC_HOST)")"
elif [ "$PERGUNTAR" = "1" ]; then
    ui_info "$(t domain_intro)"
    printf '\n'
    PUBLIC="$(ui_ask_host "$(t domain_public)")"
    AGENTS="$(ui_ask_host "$(t domain_agents)" "agents.${PUBLIC}")"
    S3="$(ui_ask_host "$(t domain_s3)" "s3.${PUBLIC}")"
    upsert_env .env PUBLIC_HOST "$PUBLIC"
    upsert_env .env AGENTS_HOST "$AGENTS"
    upsert_env .env S3_HOST "$S3"
    # The addresses that derive from them (the minimum of docs/self-hosting.md).
    upsert_env .env FRONTEND_URL "https://${PUBLIC}"
    upsert_env .env AUTH_URL "https://${PUBLIC}"
    upsert_env .env ALLOWED_ORIGINS "https://${PUBLIC}"
    upsert_env .env MINIO_EXTERNAL_ENDPOINT "https://${S3}"
    upsert_env .env MINIO_API_CORS_ALLOW_ORIGIN "https://${PUBLIC}"
    printf '\n'
    ui_ok "$(t domain_saved)"
else
    ui_warn "$(t domain_still_example)"
fi

# ── 8. E-mail (prod) ─────────────────────────────────────────────────────────
ui_stage email
if [ "$MODO" = "dev" ]; then
    ui_info "$(t skipped_in_dev)"
elif [ -n "$(env_get RESEND_API_KEY)" ] || [ -n "$(env_get SMTP_HOST)" ]; then
    ui_ok "$(t email_already)"
elif [ "$PERGUNTAR" = "1" ]; then
    ui_info "$(t email_intro)"
    printf '\n'
    TRANSPORTE="$(ui_menu "$(t email_transport)" resend "resend||$(t email_resend)" "smtp||$(t email_smtp)" "nenhum||$(t email_none)")"
    case "$TRANSPORTE" in
        resend)
            upsert_env .env RESEND_API_KEY "$(ui_ask_secret "$(t email_resend_key)")"
            ;;
        smtp)
            upsert_env .env SMTP_HOST "$(ui_ask_host "$(t email_smtp_host)")"
            # The security first: each mode has its usual port.
            SMTP_MODO="$(ui_menu "$(t email_smtp_security)" starttls "starttls||$(t email_sec_starttls)" "ssl||$(t email_sec_ssl)" "nenhuma||$(t email_smtp_plain)")"
            case "$SMTP_MODO" in ssl) SMTP_PADRAO=465 ;; nenhuma) SMTP_PADRAO=25 ;; *) SMTP_PADRAO=587 ;; esac
            SMTP_PORTA="$(ui_ask_port "$(t email_smtp_port)" "$SMTP_PADRAO")"
            upsert_env .env SMTP_SEGURANCA "$SMTP_MODO"
            upsert_env .env SMTP_PORT "$SMTP_PORTA"
            SMTP_USUARIO="$(ui_ask_optional "$(t email_smtp_user)")"
            if [ -n "$SMTP_USUARIO" ]; then
                upsert_env .env SMTP_USERNAME "$SMTP_USUARIO"
                while :; do
                    SMTP_SENHA="$(ui_ask_secret "$(t email_smtp_password)")"
                    case "$SMTP_SENHA" in
                        *"'"*) ui_hint "$(t email_smtp_quote)" ;;
                        *) upsert_env_literal .env SMTP_PASSWORD "$SMTP_SENHA"; break ;;
                    esac
                done
                unset SMTP_SENHA
            fi
            ;;
        nenhum)
            ui_warn "$(t email_none_warn)"
            ;;
    esac
    if [ "$TRANSPORTE" != "nenhum" ]; then
        upsert_env .env EMAIL_FROM "$(ui_ask "$(t email_from)" "Atlans <noreply@$(env_get PUBLIC_HOST)>")"
    fi
    printf '\n'
    ui_ok "$(t email_saved)"
else
    ui_warn "$(t email_still_missing)"
fi

# ── 9. Network ───────────────────────────────────────────────────────────────
# proxy-net has a fixed range (PROXY_NET_SUBNET, default 172.18.0.0/16 in the
# compose file), and 172.18 is the first range Docker hands out on its own: any
# other network (another project's, or this project's backend/dev-net created
# first) takes it and `up` fails with "Pool overlaps with other one on this
# address space". So the range is pinned in .env here, after checking it is free.
# The compose default stays 172.18: compose recreates a network whose range
# changed, and a new default would move proxy-net on servers already running.
ui_stage network
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
        ui_ok "$(t net_pinned "$PROXY_SUBNET_ATUAL")"
    elif [ "$PROXY_SUBNET_ENV" != "$PROXY_SUBNET_ATUAL" ]; then
        ui_warn "$(t net_differs "$PROXY_SUBNET_ATUAL" "$PROXY_SUBNET_ENV")"
        ui_hint "$(t net_differs_hint "$PROXY_SUBNET_ATUAL")"
    else
        ui_ok "$(t net_same "$PROXY_SUBNET_ATUAL")"
    fi
    PROXY_SUBNET_FINAL="$PROXY_SUBNET_ENV"
    [ -z "$PROXY_SUBNET_FINAL" ] && PROXY_SUBNET_FINAL="$PROXY_SUBNET_ATUAL"
else
    USED_RANGES="$(used_ranges)"
    if [ -n "$PROXY_SUBNET_ENV" ]; then
        if range_free "$PROXY_SUBNET_ENV"; then
            ui_ok "$(t net_env_free "$PROXY_SUBNET_ENV")"
        else
            ui_err "$(t net_env_taken "$PROXY_SUBNET_ENV")"
            ui_hint "$(t net_env_taken_hint)"
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
            ui_err "$(t net_none_free)"
            ui_hint "$(t net_none_free_hint)"
            exit 1
        fi
        upsert_env .env PROXY_NET_SUBNET "$PROXY_SUBNET_FINAL"
        ui_ok "$(t net_chosen "$PROXY_SUBNET_FINAL")"
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
        ui_warn "$(t net_trusted "$TRUSTED_ENV" "$PROXY_SUBNET_FINAL")"
    fi
fi

# ── 10. Summary ──────────────────────────────────────────────────────────────
# Only what is still to do: what the stages above filled in is not repeated.
ui_stage summary
PENDENCIAS=()
env_get DATABASE_URL | grep -q '<usuario>' && PENDENCIAS+=("$(t pending_database)")
[ "$(env_get MINIO_ROOT_USER)" = "change-me" ] && PENDENCIAS+=("$(t pending_minio)")
case "$BANCO_EXT" in
    falta|sem-pacote) PENDENCIAS+=("$(t pending_extensions)") ;;
esac
if [ "$MODO" = "prod" ]; then
    { [ "$(env_get PUBLIC_HOST)" = "localhost" ] || [ -z "$(env_get PUBLIC_HOST)" ]; } && PENDENCIAS+=("$(t pending_domain)")
    [ -z "$(env_get RESEND_API_KEY)" ] && [ -z "$(env_get SMTP_HOST)" ] && PENDENCIAS+=("$(t pending_email)")
    { [ ! -s certs/cert.pem ] || [ ! -s certs/key.pem ]; } && PENDENCIAS+=("$(t pending_cert)")
    PENDENCIAS+=("$(t pending_edge)")
fi
[ "$ESTADO_CA" = "wrong" ] && [ "$(ca_state secrets/stepca_password.txt)" = "wrong" ] && PENDENCIAS+=("$(t pending_ca)")

if [ "${#PENDENCIAS[@]}" -eq 0 ]; then
    ui_ok "$(t summary_nothing_pending)"
else
    ui_warn "$(t summary_pending)"
    for p in "${PENDENCIAS[@]}"; do ui_bullet "$p"; done
fi

if [ "$MODO" = "dev" ]; then
    ui_panel "$(t summary_title_dev)" \
        "$(t summary_dev_line1)" \
        "" \
        "$ make up-dev" \
        "" \
        "$(t summary_dev_line2)" \
        "$(t summary_dev_line3)"
else
    PH="$(env_get PUBLIC_HOST)"; AH="$(env_get AGENTS_HOST)"; SH="$(env_get S3_HOST)"
    ui_panel "$(t summary_title_prod)" \
        "$(t summary_prod_dns)" \
        "  ${PH:-<PUBLIC_HOST>}  A -> IP  $(t summary_prod_dns_cdn)" \
        "  ${AH:-<AGENTS_HOST>}  A -> IP  $(t summary_prod_dns_direct)" \
        "  ${SH:-<S3_HOST>}  A -> IP  $(t summary_prod_dns_cdn)" \
        "" \
        "$(t summary_prod_cert)" \
        "" \
        "$(t summary_prod_up)" \
        "$ make up-prod"
fi
printf '\n  %s%s%s\n\n' "$C_DIM" "$(t summary_docs)" "$C_RESET"
