#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  Atlans Executor — Quickstart installer
# ═══════════════════════════════════════════════════════════════════════════════
#
# Uso (o comando pronto, com o endereco desta instalacao, sai da tela de
# matricula do executor):
#   curl -fsSL https://<site>/executores/install | bash -s -- \
#       --executor-id=<ID> --otp=<OTP>
#
# Flags:
#   --executor-id=<ID>    id_hash do executor (recebido do admin)
#   --otp=<OTP>           OTP de enrollment (gerado pelo admin)
#   --server=<URL>        URL do host dos executores (default: o do servidor que
#                         serviu este script)
#   --public-server=<URL> URL publica para baixar ca-bundle (default: idem)
#   --dir=<PATH>          Diretorio de instalacao (default: ~/atlans-executor)
#   --repo=<URL>          Repo a clonar (default: o que o servidor configurou)
#   --memoria=<N>G        Limite de memoria do container (default: 75% da memoria
#                         que o Docker enxerga, minimo 2G; ex.: 12G, 1536M)
#   --force               Sobrescreve instalacao existente (apaga certs antigos)
#
# Modo interativo: se nao passar --executor-id ou --otp, o script pede.
#
# Requisitos: docker (com plugin compose), git, curl. O script verifica.
# ═══════════════════════════════════════════════════════════════════════════════

# -E: o trap de erro (abaixo) vale tambem dentro de main().
set -Eeuo pipefail

# ── Defaults ────────────────────────────────────────────────────────────────────
EXECUTOR_ID=""
OTP=""
# Scheme wss: o executor abre WebSocket. O enrollment converte para https
# internamente quando precisa fazer POST. Gravar com wss:// no .env evita
# o erro "scheme isn't ws or wss" no connect.
#
# As tres linhas vazias abaixo sao preenchidas pelo servidor ao servir
# /executores/install, com os enderecos DELE (AGENTS_URL, FRONTEND_URL e
# EXECUTOR_REPO_URL). O arquivo no repositorio nao aponta para instalacao
# nenhuma; um servidor sem a configuracao deixa as tres vazias, e o script pede
# as flags.
SERVER=""
PUBLIC_SERVER=""
INSTALL_DIR="${HOME}/atlans-executor"
REPO_URL=""
FORCE=0
MEMORIA=""

# Fingerprint SHA-256 do root cert da CA interna.
#
# O servidor SUBSTITUI a linha abaixo ao servir /executores/install, injetando o
# valor de STEPCA_ROOT_FINGERPRINT. Sem isso o download do ca-bundle e puro TOFU:
# quem conseguisse responder no lugar do servidor entregaria a propria CA e
# passaria a assinar certs que o executor confiaria.
#
# Um valor no ambiente tem prioridade, para o operador que prefere transportar o
# fingerprint por outro canal. Vazio mantem o comportamento antigo (sem pinning),
# com aviso — e o que acontece num servidor que nao configurou a variavel.
CA_SHA256_PIN="${ATLANS_CA_SHA256:-}"

# ── Helpers de output ──────────────────────────────────────────────────────────
# Cores so quando stdout e TTY — evita ANSI codes em logs redirecionados.
if [[ -t 1 ]]; then
    _NC='\033[0m'; _G='\033[32m'; _Y='\033[33m'; _R='\033[31m'; _B='\033[1m'
else
    _NC=''; _G=''; _Y=''; _R=''; _B=''
fi
say()  { printf "  %b%s%b\n" "$_B" "$*" "$_NC"; }
ok()   { printf "  %b✓%b %s\n" "$_G" "$_NC" "$*"; }
warn() { printf "  %b!%b %s\n" "$_Y" "$_NC" "$*"; }
err()  { printf "  %b✗%b %s\n" "$_R" "$_NC" "$*" >&2; }
die()  { err "$*"; exit 1; }

# ── Trap de erro: limpeza parcial em falha ─────────────────────────────────────
# Variaveis de estado atualizadas ao longo do script para o trap saber onde
# limpar. Falhas no clone removem diretorio pela metade; falhas pos-build
# preservam (operador deve reusar / inspecionar).
_INSTALL_STAGE="init"
_DIR_CREATED=0

cleanup_on_error() {
    local exit_code=$?
    err "Falha na etapa: $_INSTALL_STAGE (exit $exit_code)"
    case "$_INSTALL_STAGE" in
        clone)
            if [[ "$_DIR_CREATED" == "1" ]] && [[ -d "$INSTALL_DIR" ]]; then
                rm -rf "$INSTALL_DIR"
                warn "Diretorio removido: $INSTALL_DIR"
            fi
            ;;
        cabundle|env|build)
            warn "Reverter manualmente: rm -rf $INSTALL_DIR"
            ;;
        enroll|up)
            warn "Para reinstalar do zero: rm -rf $INSTALL_DIR && curl ... | bash -s -- --force"
            ;;
    esac
    exit $exit_code
}
trap cleanup_on_error ERR

# Tudo daqui para baixo roda dentro de main(), chamada na ULTIMA linha: o bash
# so executa uma funcao depois de le-la inteira, entao um `curl … | bash` que
# caia no meio do download nao roda meio script (um `rm -rf` dos certs sem o
# enrollment que viria depois). Os defaults la em cima ficam fora dela de
# proposito: e neles que o servidor injeta os enderecos da instalacao.
main() {

# ── Parse args ─────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --executor-id=*)   EXECUTOR_ID="${1#*=}"; shift ;;
        --executor-id)     EXECUTOR_ID="$2"; shift 2 ;;
        --otp=*)           OTP="${1#*=}"; shift ;;
        --otp)             OTP="$2"; shift 2 ;;
        --server=*)        SERVER="${1#*=}"; shift ;;
        --server)          SERVER="$2"; shift 2 ;;
        --public-server=*) PUBLIC_SERVER="${1#*=}"; shift ;;
        --public-server)   PUBLIC_SERVER="$2"; shift 2 ;;
        --dir=*)           INSTALL_DIR="${1#*=}"; shift ;;
        --dir)             INSTALL_DIR="$2"; shift 2 ;;
        --repo=*)          REPO_URL="${1#*=}"; shift ;;
        --repo)            REPO_URL="$2"; shift 2 ;;
        --memoria=*)       MEMORIA="${1#*=}"; shift ;;
        --memoria)         MEMORIA="$2"; shift 2 ;;
        --force)           FORCE=1; shift ;;
        -h|--help)
            sed -n '2,26p' "$0"
            exit 0
            ;;
        *) die "Flag desconhecida: $1 (use --help)" ;;
    esac
done

# Sem padrao do servidor nem flag, nao ha para onde ir: melhor parar aqui do que
# clonar ou matricular contra um endereco vazio. O repositorio so faz falta para
# clonar: uma instalacao que ja existe atualiza com `git pull`, sem a URL.
[[ -n "$SERVER" ]] || die "Informe o host dos executores: --server=wss://agents.<dominio> (o servidor que serviu este script nao tem AGENTS_URL)."
[[ -n "$PUBLIC_SERVER" ]] || die "Informe o site da instalacao: --public-server=https://<dominio>."
if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    [[ -n "$REPO_URL" ]] || die "Informe o repositorio a clonar: --repo=<URL git> (o servidor nao tem EXECUTOR_REPO_URL)."
fi

# ── 1. Verifica dependencias ───────────────────────────────────────────────────
_INSTALL_STAGE="deps"
say "[1/7] Verificando dependencias..."
command -v docker >/dev/null 2>&1 || \
    die "docker nao instalado. Instale: https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || \
    die "plugin 'docker compose' (v2) nao instalado. Instale: https://docs.docker.com/compose/install/"
command -v git >/dev/null 2>&1 || \
    die "git nao instalado. Instale: https://git-scm.com/downloads"
command -v curl >/dev/null 2>&1 || \
    die "curl nao instalado. Use o gerenciador de pacotes do SO (apt/dnf/brew)."
ok "docker + docker compose + git + curl OK"

# ── 2. Modo interativo se faltar executor-id ou otp ────────────────────────────
if [[ -z "$EXECUTOR_ID" ]]; then
    read -r -p "  EXECUTOR_ID: " EXECUTOR_ID
    [[ -z "$EXECUTOR_ID" ]] && die "EXECUTOR_ID obrigatorio."
fi
if [[ -z "$OTP" ]]; then
    read -r -s -p "  OTP de enrollment: " OTP
    echo
    [[ -z "$OTP" ]] && die "OTP obrigatorio."
fi

# ── 2.5. Conectividade com o servidor (falha rapido, antes do clone) ─────────
_INSTALL_STAGE="connectivity"
say "[2/7] Validando conectividade com $PUBLIC_SERVER..."
if ! curl -fsS --connect-timeout 5 --max-time 10 -o /dev/null "$PUBLIC_SERVER/executores/ca-bundle"; then
    err "Nao foi possivel conectar a $PUBLIC_SERVER/executores/ca-bundle"
    err "Verifique:"
    err "  - DNS:      dig +short $(echo "$PUBLIC_SERVER" | sed 's|https\?://||;s|/.*||')"
    err "  - Firewall: nc -zv $(echo "$PUBLIC_SERVER" | sed 's|https\?://||;s|/.*||') 443"
    err "  - VPN:      necessaria se o servidor e privado"
    die "Falha de conectividade. Resolva e tente de novo."
fi
ok "Servidor acessivel."

# ── 3. Clona ou atualiza o repo ────────────────────────────────────────────────
_INSTALL_STAGE="clone"
say "[3/7] Preparando diretorio em $INSTALL_DIR..."

# Detecta instalacao previa com cert valido — exige --force para sobrescrever.
# git pull (atualizacao de codigo) e permitido sem --force; substituicao de cert
# nao e, para evitar revogar um executor funcionando por engano.
if [[ -f "$INSTALL_DIR/executor-certs/atlans-root.crt" ]] || [[ -d "$INSTALL_DIR/data/certs" ]]; then
    if [[ "$FORCE" != "1" ]]; then
        warn "Instalacao existente detectada em $INSTALL_DIR"
        warn "Para atualizar so o codigo: rode 'git pull' manualmente em $INSTALL_DIR."
        die "Para reinstalar (substituir cert), use --force OU rm -rf $INSTALL_DIR antes."
    else
        warn "--force: removendo certs antigos. O executor atual ficara revogado."
        rm -rf "$INSTALL_DIR/executor-certs" "$INSTALL_DIR/data/certs" 2>/dev/null || true
    fi
fi

if [[ -d "$INSTALL_DIR/.git" ]]; then
    (cd "$INSTALL_DIR" && git pull --ff-only) || warn "git pull falhou — usando codigo atual."
    ok "Repo atualizado."
else
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
    _DIR_CREATED=1
    ok "Repo clonado em $INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ── 4. Baixa root cert da CA interna ───────────────────────────────────────────
_INSTALL_STAGE="cabundle"
say "[4/7] Baixando root cert da CA interna..."
mkdir -p ./executor-certs
curl -fsSL "$PUBLIC_SERVER/executores/ca-bundle" -o ./executor-certs/atlans-root.crt
test -s ./executor-certs/atlans-root.crt || die "ca-bundle veio vazio."

# Verificacao do material baixado contra o fingerprint publicado pelo servidor.
# Falha FECHADA: quem configurou o pinning optou por ele, entao nao verificar
# silenciosamente seria pior que abortar.
if [[ -n "$CA_SHA256_PIN" ]]; then
    command -v openssl >/dev/null 2>&1 || \
        die "openssl nao instalado, mas o servidor publicou um fingerprint de CA. Instale openssl e rode de novo."
    # Normaliza os dois lados: hex minusculo, sem ':' e sem espacos. O
    # fingerprint e calculado sobre o DER, que e como
    # 'openssl x509 -fingerprint -sha256' o produz.
    # Aceita varios fingerprints separados por virgula — e o que torna viavel
    # uma rotacao de CA com sobreposicao, em que o bundle legitimo carrega o
    # root velho E o novo.
    _esperados=$(printf '%s' "$CA_SHA256_PIN" | tr 'A-Z' 'a-z' | tr -d ': ' | tr ',;' '\n\n')

    # TODO cert do arquivo e verificado, e nao so o primeiro.
    #
    # `openssl x509 -in <arquivo>` le apenas o primeiro bloco PEM. O arquivo
    # inteiro vira trust store (o executor o concatena as CAs publicas), entao
    # um bundle [root_legitimo, ca_do_atacante] passava na conferencia e a CA
    # extra virava ancora de confianca — inclusive para o container de
    # enrollment, que carrega o OTP e gera a chave do cert mTLS.
    _tmp_split=$(mktemp -d)
    awk -v d="$_tmp_split" '
        /-----BEGIN( TRUSTED| X509)? CERTIFICATE-----/ { n++; f = sprintf("%s/c%03d.pem", d, n) }
        n { print > f }
    ' ./executor-certs/atlans-root.crt

    _blocos=$(find "$_tmp_split" -name 'c*.pem' | wc -l | tr -d '[:space:]')
    if [[ "$_blocos" -eq 0 ]]; then
        rm -rf "$_tmp_split"; rm -f ./executor-certs/atlans-root.crt
        die "ca-bundle nao contem nenhum certificado PEM valido."
    fi

    _intrusos=""
    for _bloco in "$_tmp_split"/c*.pem; do
        # Normaliza o rotulo: `openssl x509` nao le `TRUSTED CERTIFICATE`, mas o
        # OpenSSL o carrega como ancora — ignorar o bloco seria nao verifica-lo.
        sed -e 's/TRUSTED CERTIFICATE/CERTIFICATE/g; s/X509 CERTIFICATE/CERTIFICATE/g' \
            "$_bloco" > "$_bloco.norm"
        # `|| true`: sob `set -euo pipefail`, um bloco que o openssl nao le
        # abortava o script AQUI — antes do ramo de intruso, antes do
        # `rm -f` do bundle. O arquivo do atacante ficava em disco e o
        # instalador morria com "Falha na etapa: cabundle", sem dizer por que.
        # O bloco ilegivel tem de ser tratado como intruso, nao como crash.
        _fp=$(openssl x509 -in "$_bloco.norm" -noout -fingerprint -sha256 2>/dev/null \
            | cut -d= -f2 | tr 'A-Z' 'a-z' | tr -d ': ' || true)
        if [[ -z "$_fp" ]] || ! printf '%s\n' "$_esperados" | grep -qx "$_fp"; then
            _intrusos="$_intrusos ${_fp:-<bloco-ilegivel>}"
        fi
    done
    rm -rf "$_tmp_split"

    if [[ -n "$_intrusos" ]]; then
        rm -f ./executor-certs/atlans-root.crt
        err "O ca-bundle contem certificado(s) fora do fingerprint publicado."
        err "  aceitos:   $(printf '%s' "$_esperados" | tr '\n' ' ')"
        err "  intruso(s):$_intrusos"
        die "Abortando: o ca-bundle baixado nao e (so) a CA do Atlans. Confirme o fingerprint com o admin."
    fi
    ok "Root cert conferido contra o fingerprint publicado ($_blocos cert(s), todos esperados)."
else
    warn "Servidor nao publicou fingerprint de CA — root cert aceito sem verificacao (TOFU)."
fi

ok "Root cert salvo em ./executor-certs/atlans-root.crt"

# ── 5. Prepara .env (semeia do .env.example) ──────────────────────────────────
_INSTALL_STAGE="env"
say "[5/7] Preparando executor/.env..."
mkdir -p executor
# Semeia a partir do .env.example se o .env ainda nao foi criado. Isso garante
# que EXECUTOR_SERVER_URL, MINIO_EXTERNAL_ENDPOINT, LOG_LEVEL e demais defaults estejam presentes
# no primeiro boot. Defesa em profundidade — o enrollment tambem semeia em
# executor/_env_utils.py:seed_env_from_example().
if [[ ! -s executor/.env ]] && [[ -f executor/.env.example ]]; then
    cp executor/.env.example executor/.env
    ok ".env semeado a partir de .env.example"
else
    touch executor/.env
fi
# Permissoes: 0660 ao inves de 0666 (mundo nao le secrets).
# O container roda como UID 1000 (appuser). Tenta ajustar ownership; se o
# script roda como root, funciona. Se nao, deixa warning — o container tem
# bind volume read-write, write ainda funciona via group bit.
# Persiste o fingerprint no .env do executor.
#
# E AQUI que o pin passa a valer de verdade: `executor/_ca_bootstrap.bootstrap_ca`
# retorna cedo quando `SSL_CERT_FILE` ja esta setado, e o container de enrollment
# abaixo o seta — entao naquele passo o pin nao e lido. O servico de longa
# duracao do compose NAO seta `SSL_CERT_FILE`, roda o bootstrap inteiro, e e ele
# que confere a CA contra este valor a cada boot.
if [[ -n "$CA_SHA256_PIN" ]]; then
    _pin_normalizado=$(printf '%s' "$CA_SHA256_PIN" | tr 'A-Z' 'a-z' | tr -d ': ')
    # `export ` opcional: um .env escrito a mao costuma usa-lo (para poder ser
    # `source`ado), e o lado Python (`_env_utils._sem_export`) ja o tolera. Sem
    # a mesma tolerancia aqui, a linha antiga nao era atualizada e sim
    # DUPLICADA — e como `read_env_var` devolve a primeira ocorrencia, o
    # executor continuava pinando a CA velha e recusava o boot depois de uma
    # rotacao, logo apos o instalador ter gravado o pin novo.
    #
    # A substituicao preserva o `export ` que estava la: para um .env que e
    # `source`ado, tira-lo faria a variavel deixar de chegar aos filhos.
    if grep -qE '^[[:space:]]*(export[[:space:]]+)?ATLANS_CA_SHA256=' executor/.env 2>/dev/null; then
        sed -i.bak -E "s|^([[:space:]]*(export[[:space:]]+)?)ATLANS_CA_SHA256=.*|\1ATLANS_CA_SHA256=${_pin_normalizado}|" executor/.env
        rm -f executor/.env.bak
    else
        printf 'ATLANS_CA_SHA256=%s\n' "$_pin_normalizado" >> executor/.env
    fi
    ok "ATLANS_CA_SHA256 gravado em executor/.env — a CA e reconferida a cada boot do executor."
fi

chmod 660 executor/.env
if [[ "$(id -u)" == "0" ]]; then
    chown 1000:1000 executor/.env
    ok "executor/.env: 0660 (owner UID 1000 do container)"
else
    chgrp 1000 executor/.env 2>/dev/null || \
        warn "Nao foi possivel ajustar group do executor/.env (rode como root para chown). Permissao mundo-r removida mesmo assim."
    ok "executor/.env: 0660"
fi

# ── 5b. Limite de memoria do container ───────────────────────────────────────
# O 2G fixo do compose matava o executor por OOM do cgroup numa maquina de 16 GB
# com 13 GB livres. Pergunta ao PROPRIO Docker quanta memoria ele
# enxerga — no Linux e a RAM da maquina; no Docker Desktop, a da VM, que e o
# teto real — e reserva 75% para o executor, nunca menos que os 2G de antes
# (numa maquina pequena o limite nao cai abaixo do que era). Vai para o .env do
# projeto, que o compose interpola em `memory: ${EXECUTOR_MEMORIA:-2G}`.
# >>> limite_de_memoria (executado de verdade por tests/unit/test_limite_de_memoria_do_executor.py)
limite_de_memoria() {
    local total_bytes="$1"
    local gb=$(( total_bytes * 3 / 4 / 1073741824 ))
    if (( gb < 2 )); then
        gb=2
    fi
    printf '%sG' "$gb"
}
# "12G" ou "1536M", e nunca abaixo da reserva de 512M do compose: o Docker so
# recusaria o container no enroll, depois do build inteiro.
memoria_valida() {
    [[ "$1" =~ ^([0-9]+)([GgMm])$ ]] || return 1
    local mib=$(( 10#${BASH_REMATCH[1]} ))
    if [[ "${BASH_REMATCH[2]}" == [Gg] ]]; then
        mib=$(( mib * 1024 ))
    fi
    (( mib >= 512 ))
}
# Um compose com edicao local (o cabecalho dele manda editar) faz o `git pull
# --ff-only` abortar, e o arquivo segue com o `memory: 2G` fixo: o .env ganharia
# um limite que nada le.
compose_le_o_limite() {
    grep -q 'EXECUTOR_MEMORIA' "${1:-docker-compose.executor.yml}" 2>/dev/null
}
# <<< limite_de_memoria
if [[ -z "$MEMORIA" ]]; then
    _mem_total=$(docker info --format '{{.MemTotal}}' 2>/dev/null || true)
    if [[ "$_mem_total" =~ ^[0-9]+$ ]] && (( _mem_total > 0 )); then
        MEMORIA=$(limite_de_memoria "$_mem_total")
    else
        MEMORIA="2G"
        warn "Nao foi possivel ler a memoria do Docker — limite fica em 2G (ajuste EXECUTOR_MEMORIA em $INSTALL_DIR/.env)."
    fi
fi
memoria_valida "$MEMORIA" || die "--memoria invalida: $MEMORIA (ex.: 12G, 1536M; minimo 512M, a reserva do compose)"
if grep -qE '^EXECUTOR_MEMORIA=' .env 2>/dev/null; then
    sed -i.bak -E "s|^EXECUTOR_MEMORIA=.*|EXECUTOR_MEMORIA=${MEMORIA}|" .env
    rm -f .env.bak
else
    printf 'EXECUTOR_MEMORIA=%s\n' "$MEMORIA" >> .env
fi
if compose_le_o_limite; then
    ok "Limite de memoria do executor: $MEMORIA (EXECUTOR_MEMORIA em $INSTALL_DIR/.env)."
else
    warn "EXECUTOR_MEMORIA=$MEMORIA gravado, mas o docker-compose.executor.yml daqui ainda tem o limite fixo (o git pull nao o atualizou — edicao local?). Atualize o arquivo para o limite valer."
fi

# ── 6. Build da imagem ────────────────────────────────────────────────────────
_INSTALL_STAGE="build"
say "[6/7] Buildando imagem (pode demorar alguns minutos na primeira vez)..."
# O build grava na imagem a versão que o painel mostra — a do produto mais o
# commit deste checkout (2.15.0+3f02f44, ver executor/versao.py): é o que diz
# se esta máquina já tem a correção de ontem.
docker compose -f docker-compose.executor.yml build

# ── 7. Enrollment + start ──────────────────────────────────────────────────────
_INSTALL_STAGE="enroll"
say "[7/7] Executando enrollment e subindo o executor..."
# -T: desabilita TTY e stdin forwarding.
# </dev/null: fecha stdin explicitamente. Sem isso, em alguns ambientes o
# `docker compose run` consome o resto do pipe do curl|bash e o script termina
# sem chegar no `up -d` final (bug reportado).
docker compose -f docker-compose.executor.yml run --rm -T \
    --entrypoint "" \
    -v "$(pwd)/executor-certs/atlans-root.crt:/atlans-root.crt:ro" \
    -v "$(pwd)/executor/.env:/app/executor/.env" \
    -e SSL_CERT_FILE=/atlans-root.crt \
    -e REQUESTS_CA_BUNDLE=/atlans-root.crt \
    -e ATLANS_QUICKSTART=1 \
    `# Inerte NESTE comando (SSL_CERT_FILE acima faz bootstrap_ca retornar antes` \
    `# de ler o pin), e mantido de proposito: o dia em que o enroll deixar de` \
    `# montar o cert pronto, a verificacao passa a valer sem ninguem lembrar.` \
    -e ATLANS_CA_SHA256="$CA_SHA256_PIN" \
    executor \
    python -m executor enroll \
        --executor-id="$EXECUTOR_ID" \
        --otp="$OTP" \
        --server="$SERVER" \
        --cert-dir=/data/certs \
    </dev/null

# Zera OTP da memoria do shell (placebo — pode ter vazado em ps aux,
# ver Onda 2 para fix definitivo com --otp-file)
OTP=""

ok "Enrollment concluido."
_INSTALL_STAGE="up"
say "Subindo o executor..."
# O container chamava-se atlas-executor (sem o n). Um que tenha ficado de uma
# instalacao antiga fora do compose impediria o nome novo; o do compose seria
# recriado de qualquer jeito. O volume e o mesmo: a matricula fica.
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "atlas-executor"; then
    warn "Removendo o container com o nome antigo (atlas-executor)."
    docker rm -f atlas-executor >/dev/null 2>&1 || true
fi
docker compose -f docker-compose.executor.yml up -d </dev/null
ok "Executor rodando em background."

# ── Sumario final ─────────────────────────────────────────────────────────────
_INSTALL_STAGE="done"
echo
printf "  %b═══════════════════════════════════════════════════════════════%b\n" "$_G" "$_NC"
ok "Instalacao concluida com sucesso!"
printf "  %b═══════════════════════════════════════════════════════════════%b\n" "$_G" "$_NC"
echo
say "Identidade do executor:"
echo "  Executor ID: $EXECUTOR_ID"
echo "  Servidor:    $SERVER"
echo "  Cert em:     $INSTALL_DIR/data/certs"
echo "  Config:      $INSTALL_DIR/executor/.env"
echo
say "Admin UI:"
echo "  $PUBLIC_SERVER/executores — o executor deve aparecer 'Ativo + Online' em poucos segundos."
echo
say "Comandos uteis:"
echo "  • Logs:       docker compose -f $INSTALL_DIR/docker-compose.executor.yml logs -f"
echo "  • Status:     docker compose -f $INSTALL_DIR/docker-compose.executor.yml ps"
echo "  • Restart:    docker compose -f $INSTALL_DIR/docker-compose.executor.yml restart"
echo "  • Parar:      docker compose -f $INSTALL_DIR/docker-compose.executor.yml down"
echo "  • Reinstalar: curl -fsSL $PUBLIC_SERVER/executores/install | bash -s -- --force --executor-id=... --otp=..."
echo

}

main "$@"
