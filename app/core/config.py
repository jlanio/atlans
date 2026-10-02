# app/core/config.py
import ipaddress
import logging
import os
import re
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL   = os.getenv("DATABASE_URL")

# URL de conexão ao Redis — usado por pub/sub, filas run_creates/run_results e cache.
# Ex: redis://:senha@redis:6379/0
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
ECHO_SQL       = os.getenv("ECHO_SQL", "false").lower() == "true"

# Roteamento por POLÍTICA de workspace (docs/specs/executor-isolation-routing.md).
#   off → caminho legado: executor dedicado do workspace, depois o pool inteiro.
#   on  → cadeia da política: nível 1 → nível 2 → terminal (falhar | pool).
# Com o backfill da migração 20260907_0002, `on` produz exatamente os mesmos
# candidatos que `off` para todo workspace existente — a flag existe para
# reversão, não para sombra. Lida em tempo de chamada para que testes possam
# alternar via patch do módulo.
EXECUTOR_POLICY_ROUTING = os.getenv("EXECUTOR_POLICY_ROUTING", "off").strip().lower()


def policy_routing_enabled() -> bool:
    return EXECUTOR_POLICY_ROUTING == "on"

# PERF: Connection pool dimensionado para 4 workers uvicorn em produção.
#
# O teto é POR WORKER e POR ENGINE, não global. Hoje há um engine só (o async,
# em app/core/db.py), então o total é `workers × (POOL_SIZE + MAX_OVERFLOW)`
# = 4 × 13 = 52 conexões.
#
# Duas armadilhas que já cobraram o preço aqui:
#
# 1. O comentário anterior calculava "4 × 20 = 80; overflow +10", tratando o
#    overflow como global. Com os valores de então (20/10) o teto real era
#    4 × 30 = 120, ACIMA do `max_connections` padrão do Postgres, que é 100.
#    Estourar esse limite não deixa lento: devolve `FATAL: sorry, too many
#    clients already`, que aparece como instabilidade intermitente.
# 2. Existia um segundo engine (síncrono) reaproveitando estas mesmas
#    constantes, o que dobrava o teto. Ele foi removido — se algum dia voltar
#    um engine novo, ou ele tem pool próprio e explícito, ou esta conta muda.
#
# Ao aumentar POOL_SIZE/MAX_OVERFLOW, confira `SHOW max_connections` no servidor
# e reserve folga para migrations, psql e outros clientes.
#
# POOL_RECYCLE=600s evita conexões mortas (cloud providers timeout ~10min).
POOL_SIZE      = int(os.getenv("POOL_SIZE", 8))
MAX_OVERFLOW   = int(os.getenv("MAX_OVERFLOW", 5))
POOL_TIMEOUT   = int(os.getenv("POOL_TIMEOUT", 30))
POOL_RECYCLE   = int(os.getenv("POOL_RECYCLE", 600))
POOL_PRE_PING  = os.getenv("POOL_PRE_PING", "true").lower() == "true"

# Prazos de cada comando no banco, em segundos (app/core/db.py). O POOL_TIMEOUT
# acima só limita a espera por uma conexão livre; sem estes, uma consulta
# travada (lock esperando outro, plano ruim, rede que some sem derrubar a
# conexão) segura a conexão sem fim, e poucas presas esgotam o pool do worker.
# - DB_STATEMENT_TIMEOUT: o Postgres cancela o comando e responde com erro
#   claro (`statement_timeout` da sessão). Conta a espera por lock.
# - DB_COMMAND_TIMEOUT: o asyncpg desiste de esperar a resposta — o banco que
#   nem responde. Maior que o anterior, para que no caso normal quem cancela
#   seja o Postgres.
# 0 desliga cada um. Uma tarefa que precise de mais tempo abre exceção só na
# transação dela, `SET LOCAL statement_timeout = '80s'` — até o
# DB_COMMAND_TIMEOUT, que é do cliente e não se ergue por transação.
def _segundos_do_env(nome: str, padrao: int) -> int:
    """Segundos inteiros de `nome`; vazia vale o padrão (o compose repassa as
    duas com `${VAR:-}`). Um valor que não é inteiro ("60s", "5min", "1.5")
    vale o padrão com aviso, em vez de derrubar a importação — e com ela a API.
    O teto é o do Postgres (statement_timeout é um int de milissegundos): acima
    dele o servidor recusaria TODA conexão nova."""
    bruto = (os.getenv(nome) or "").strip()
    if not bruto:
        return padrao
    try:
        valor = int(bruto)
    except ValueError:
        logging.getLogger(__name__).warning(
            "%s=%r não é um número inteiro de segundos; vale o padrão (%ss).", nome, bruto, padrao,
        )
        return padrao
    return max(0, min(valor, 2_147_483))


DB_STATEMENT_TIMEOUT = _segundos_do_env("DB_STATEMENT_TIMEOUT", 60)
DB_COMMAND_TIMEOUT   = _segundos_do_env("DB_COMMAND_TIMEOUT", 90)


APP_SECRET = os.getenv("APP_SECRET")
if not APP_SECRET:
    raise ValueError("A variável de ambiente APP_SECRET precisa ser definida.")
# Auditoria (SEG-65): APP_SECRET assina os JWTs (HS256). Um segredo curto é
# forçável offline. Exige pelo menos 32 caracteres — o suficiente para 256 bits
# de entropia quando gerado com `secrets.token_urlsafe(32)`.
_APP_SECRET_MIN = 32
if len(APP_SECRET) < _APP_SECRET_MIN:
    raise ValueError(
        f"APP_SECRET precisa ter pelo menos {_APP_SECRET_MIN} caracteres "
        "(gere com `python -c \"import secrets; print(secrets.token_urlsafe(32))\"`)."
    )

# Chave Fernet para criptografia de credenciais (connection strings).
# Deve ser um valor base64url de 32 bytes gerado com Fernet.generate_key().
# É separada de APP_SECRET e obrigatória — o app NÃO deriva a chave de cifra do
# APP_SECRET (evita reaproveitar segredo de propósito diferente).
FERNET_KEY: str = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("A variável de ambiente FERNET_KEY precisa ser definida.")

# Rotação de chave (opcional): FERNET_KEYS aceita VÁRIAS chaves separadas por
# vírgula. A PRIMEIRA da lista efetiva é a que CIFRA; TODAS decifram (MultiFernet
# em encryption.py). Para rotacionar, PREPONHA a chave nova:
#   FERNET_KEYS="<nova>,<antiga>"  → passa a cifrar com <nova> e ainda lê <antiga>.
#
# Rede de segurança contra erro de operação: FERNET_KEY é SEMPRE mantida na lista
# de decriptação (anexada ao fim se não estiver em FERNET_KEYS). Assim, esquecer
# de re-listar a chave atual não torna ilegível ("orfaniza") tudo o que já foi
# cifrado com ela — o pior caso vira "cifra com a nova, ainda lê a antiga", nunca
# perda de dados. Para de fato APOSENTAR uma chave, troque FERNET_KEY (ato
# explícito), não apenas FERNET_KEYS. Sem FERNET_KEYS ⇒ usa só FERNET_KEY,
# idêntico ao comportamento anterior.
_raw_fernet_keys = os.getenv("FERNET_KEYS", "")
_fernet_keys = [k.strip() for k in _raw_fernet_keys.split(",") if k.strip()]
if FERNET_KEY not in _fernet_keys:
    _fernet_keys.append(FERNET_KEY)
FERNET_KEYS: list[str] = _fernet_keys

# ── Criptografia de Jobs para Executores ─────────────────────────────────────────
# Chave privada Ed25519 do servidor para assinar envelopes de jobs.
# Gere com: python -c "
#   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
#   import base64; k = Ed25519PrivateKey.generate()
#   print(base64.b64encode(k.private_bytes_raw()).decode())
# "
EXECUTOR_SIGNING_KEY: str | None = os.getenv("EXECUTOR_SIGNING_KEY")

# ── mTLS + step-ca (enrollment de executores) ─────────────────────────────────────
# URL interna da step-ca CA (root + intermediate). Em prod, normalmente
# https://step-ca:9000 dentro da rede proxy-net.
STEPCA_URL: str = os.getenv("STEPCA_URL", "https://step-ca:9000")

# Provisioner JWK que o app usa para assinar CSRs em nome dos executores.
# Criado uma vez via: `step ca provisioner add atlans-app --type=jwk --create`.
STEPCA_PROVISIONER_NAME: str = os.getenv("STEPCA_PROVISIONER_NAME", "atlans-app")
STEPCA_PROVISIONER_PASSWORD: str | None = os.getenv("STEPCA_PROVISIONER_PASSWORD")

# Path do ca.json da step-ca dentro do container api-prod.
# Necessario para decifrar `encryptedKey` do provisioner JWK e gerar OTTs (one-time
# tokens) assinados com ES256, como esperado pela step-ca.
# O ca.json e montado como `:ro` via volume step-ca-data — ver docker-compose.yml.
STEPCA_CA_CONFIG_PATH: str = os.getenv("STEPCA_CA_CONFIG_PATH", "/etc/step-ca/config/ca.json")

# Path do root cert da CA interna (root_ca.crt), montado read-only no api-prod
# via step-ca-data:/etc/step-ca. Inclui no response do enroll para o executor
# poder validar a chain completa do cert TLS do host dos executores (root como
# trust anchor; intermediate vem do response /1.0/sign da step-ca).
STEPCA_ROOT_CERT_PATH: str = os.getenv("STEPCA_ROOT_CERT_PATH", "/etc/step-ca/certs/root_ca.crt")

# Fingerprint SHA-256 do root cert da CA — usado para pinning quando o
# servidor expoe o ca_pem no enrollment response.
STEPCA_ROOT_FINGERPRINT: str = os.getenv("STEPCA_ROOT_FINGERPRINT", "")

# Pepper usado no HMAC-SHA256 dos OTPs de enrollment. Gere com:
#   python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
# CRITICO: rotacionar invalida TODOS os OTPs em voo. Nunca commitar.
OTP_PEPPER: str = os.getenv("OTP_PEPPER", "")

# TTL do cert mTLS emitido (dias). Curto o suficiente para limitar exposicao
# de chave vazada, longo o suficiente para tolerar executores offline.
EXECUTOR_CERT_TTL_DAYS: int = int(os.getenv("EXECUTOR_CERT_TTL_DAYS", "90"))

# TTL do OTP de bootstrap (horas). 24h cobre delivery + setup mas evita
# janela longa de leak.
EXECUTOR_OTP_TTL_HOURS: int = int(os.getenv("EXECUTOR_OTP_TTL_HOURS", "24"))

# Origens permitidas pelo CORS. Em produção, defina explicitamente, ex:
# ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["*"]
)
# Valida formato das origens (exceto wildcard)
for _origin in ALLOWED_ORIGINS:
    if _origin != "*" and not (_origin.startswith("http://") or _origin.startswith("https://")):
        raise ValueError(f"Origem CORS inválida: {_origin!r}. Use http:// ou https://")

# ── Endereços desta instalação ───────────────────────────────────────────────
# Nada aqui aponta para uma instalação específica: o código é o mesmo para quem
# hospeda o próprio Atlans. Cada endereço vem do ambiente, e os que têm uma
# convenção (o host dos executores, o MCP, o remetente) partem do FRONTEND_URL.

def _host_de(url: str) -> str:
    """O host de uma URL, sem porta, em minúsculas e em ASCII; vazio se ela não
    tiver. Um domínio com acento vira punycode (`xn--`), que é como ele chega no
    header Host e como entra num script."""
    try:
        host = (urlsplit(url.strip()).hostname or "").lower()
    except ValueError:
        return ""
    if host.isascii():
        return host
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return ""


def _site_normalizado(url: str) -> str:
    """A URL do site sem espaços nem `/` no fim, com o host em ASCII.

    Um espaço colado no valor do secret virava, em silêncio, um host inválido
    nos valores que partem daqui (o MCP respondia 421 a tudo, e o install.sh
    saía sem servidor).
    """
    url = url.strip().rstrip("/")
    try:
        partes = urlsplit(url)
        host, porta = partes.hostname or "", partes.port
    except ValueError:
        return url
    if not host or host.isascii():
        return url
    em_ascii = _host_de(url)
    if not em_ascii:
        return url
    return urlunsplit(partes._replace(netloc=em_ascii + (f":{porta}" if porta else "")))


# URL pública do site, a que o navegador abre. Vai nos links dos e-mails e é a
# origem das convenções abaixo.
FRONTEND_URL: str = _site_normalizado(os.getenv("FRONTEND_URL", "")) or "http://localhost:3000"
# Sem esquema (`atlans.example.org`) a URL passava por todos os portões e
# desligava as convenções em silêncio: remetente `noreply@localhost`, MCP sem o
# host do site, tela de matrícula sem o host dos executores — três sintomas
# longe da causa. A mesma política de ALLOWED_ORIGINS: parar a API diz.
if not re.match(r"^https?://", FRONTEND_URL, re.IGNORECASE):
    raise ValueError(f"FRONTEND_URL={FRONTEND_URL!r} precisa começar com http:// ou https://")


def _host_com_dominio(url: str) -> str:
    """O host da URL quando ele tem domínio; vazio para localhost, `*.localhost`
    e IP, que não servem de base para convenção nenhuma."""
    host = _host_de(url)
    if not host or host == "localhost" or host.endswith(".localhost"):
        return ""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    return ""


def agents_por_convencao(frontend_url: str) -> str:
    """`https://agents.<host do site>`, a convenção que o executor usa no caminho
    inverso (executor/_ca_bootstrap.py). Sem domínio ou sem https, nenhuma."""
    host = _host_com_dominio(frontend_url)
    if host and frontend_url.strip().lower().startswith("https://"):
        return f"https://agents.{host}"
    return ""


def _ip_do_site(url: str) -> str:
    """O host da URL quando ele é um IP (uma instalação sem domínio)."""
    host = _host_de(url)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return ""
    return host


def hosts_mcp_padrao(frontend_url: str) -> list[str]:
    """O host do site (com e sem porta) mais o dev local. Um site por IP entra
    com o IP: a proteção contra DNS rebinding é para nomes, e um Host que já é
    IP não sofre rebinding — sem ele, `/mcp` respondia 421 até alguém definir
    MCP_ALLOWED_HOSTS."""
    host = _host_com_dominio(frontend_url) or _ip_do_site(frontend_url)
    return ([host, f"{host}:*"] if host else []) + ["localhost:*", "127.0.0.1:*"]


def remetente_padrao(frontend_url: str) -> str:
    """`noreply@` no host do site; sem domínio, `localhost`."""
    return f"Atlans <noreply@{_host_com_dominio(frontend_url) or 'localhost'}>"


# URL do host dos executores (o de mTLS), em https: o `--server` dos comandos de
# matrícula e o padrão do install.sh servido. Vazio = a convenção acima; num host
# sem domínio também fica vazio, e a tela de matrícula pede o endereço.
AGENTS_URL: str = (
    os.getenv("AGENTS_URL", "").strip().rstrip("/") or agents_por_convencao(FRONTEND_URL)
)

# Repositório git que o install.sh clona na máquina do executor. Vazio: o script
# servido não traz padrão e pede `--repo=`.
EXECUTOR_REPO_URL: str = os.getenv("EXECUTOR_REPO_URL", "").strip()

# Repositório do GitHub (`dono/nome`) cujas releases `desktop/v*` trazem o
# instalador Windows que o painel oferece. Vazio desliga a oferta.
_raw_desktop_repo = os.getenv("DESKTOP_RELEASES_REPO", "").strip().strip("/")
if _raw_desktop_repo and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", _raw_desktop_repo):
    logging.getLogger(__name__).error(
        "DESKTOP_RELEASES_REPO=%r não é `dono/nome` — o painel não oferece o app desktop.",
        _raw_desktop_repo,
    )
    _raw_desktop_repo = ""
DESKTOP_RELEASES_REPO: str = _raw_desktop_repo

# ── Servidor MCP (/mcp) ───────────────────────────────────────────────────────
# `Host` aceitos pelo transporte streamable HTTP. É defesa contra DNS rebinding:
# um site qualquer não consegue apontar um nome próprio para 127.0.0.1 e falar
# com o MCP do desenvolvedor. Lista separada por vírgula; `*` só depois da porta
# (ex.: "localhost:*"). Vazio = o host do FRONTEND_URL (com e sem porta) mais o
# dev local.
_raw_mcp_hosts = os.getenv("MCP_ALLOWED_HOSTS", "")
MCP_ALLOWED_HOSTS: list[str] = (
    [h.strip() for h in _raw_mcp_hosts.split(",") if h.strip()]
    or hosts_mcp_padrao(FRONTEND_URL)
)

# ── Assistente (montar fluxos por linguagem natural) ─────────────────────────
# O modelo vem de qualquer API compatível com a da OpenAI (`/chat/completions`,
# `app/services/openrouter.py`): o OpenRouter (o padrão), um gateway (LiteLLM)
# ou um servidor local (Ollama, vLLM, llama.cpp), com um modelo que saiba
# chamar ferramentas. A chave é da PLATAFORMA, não do usuário: quem paga os
# tokens do modelo é a instalação, e o teto por pessoa vive no Redis
# (`app/mcp/cotas.py`). Sem chave o assistente simplesmente não existe — a rota
# responde que está desligado e o resto do editor continua inteiro.
#
# LLM_API_KEY e LLM_BASE_URL são os nomes genéricos; OPENROUTER_API_KEY e
# OPENROUTER_BASE_URL continuam valendo. Um servidor local que não pede chave
# aceita qualquer valor não vazio (ex.: `local`).
OPENROUTER_API_KEY: str = os.getenv("LLM_API_KEY", "").strip() or os.getenv("OPENROUTER_API_KEY", "")
# A base da API (`.../v1`). Vazio = a pública do OpenRouter. `.strip() or` pelo
# motivo de ASSISTENTE_MODELO.
OPENROUTER_BASE_URL: str = (
    os.getenv("LLM_BASE_URL", "").strip()
    or os.getenv("OPENROUTER_BASE_URL", "").strip()
    or "https://openrouter.ai/api/v1"
)
# Atribuição do app no OpenRouter (os cabeçalhos X-Title e HTTP-Referer, que
# põem o nome e o FRONTEND_URL da instalação no ranking público de apps dele).
# Desligada por padrão: cada instalação decide se aparece.
ASSISTENTE_ATRIBUICAO: bool = (
    os.getenv("ASSISTENTE_ATRIBUICAO", "").strip().lower() in ("true", "1", "on", "yes", "sim")
)


def _env_ou_legado(nova: str, legada: str) -> str:
    """Le a env NOVA; ausente/vazia, cai na LEGADA — com aviso.

    A F4 renomeou COPILOTO_{ATIVO,MODELO,IDIOMA} -> ASSISTENTE_{...} sem periodo
    de convivencia: um .env de servidor ainda com os nomes antigos reconfigurava
    o assistente EM SILENCIO (ativo por default, modelo/idioma de fabrica). O
    fallback e temporario — remova depois que os .env de producao migrarem; o
    aviso no arranque e o lembrete.
    """
    valor = os.getenv(nova, "").strip()
    antigo = os.getenv(legada, "").strip()
    if valor:
        if antigo:
            logging.getLogger("atlans.config").warning(
                "%s e %s definidas: usando %s (a legada sera ignorada — apague-a do .env).",
                nova, legada, nova,
            )
        return valor
    if antigo:
        logging.getLogger("atlans.config").warning(
            "%s nao definida, mas %s sim: usando o valor LEGADO. Renomeie no .env — este fallback sera removido.",
            nova, legada,
        )
        return antigo
    return ""


ASSISTENTE_ATIVO: bool = bool(OPENROUTER_API_KEY) and (
    _env_ou_legado("ASSISTENTE_ATIVO", "COPILOTO_ATIVO") or "true"
).lower() not in ("false", "0", "off", "no")

# O modelo é variável de ambiente, e não constante no código, para que trocá-lo
# seja uma edição do `.env` e um reinício — não um deploy. Modelo novo sai com
# frequência bem maior que a deste repositório, e a alternativa é o valor
# envelhecer dentro de um módulo que ninguém tem motivo para abrir.
#
# O nome é o do catálogo do provedor: no OpenRouter, `fornecedor/modelo` (ex.:
# `anthropic/claude-opus-5`, `openai/gpt-5`, `google/gemini-2.5-pro`; a lista
# viva está em https://openrouter.ai/models); num servidor local, o nome dele
# (`qwen3:14b` no Ollama). O padrão abaixo só existe no OpenRouter.
#
# `.strip() or` e não o default do `getenv`: o compose passa
# `ASSISTENTE_MODELO: ${ASSISTENTE_MODELO:-}`, que DEFINE a variável como string
# vazia quando ninguém a configurou. O default do `getenv` só cobre "não
# definida", então sem isto a instalação padrão subiria pedindo um modelo de
# nome vazio — e o erro só apareceria na primeira conversa. Mesmo cuidado que
# `MCP_ALLOWED_HOSTS` acima.
ASSISTENTE_MODELO: str = _env_ou_legado("ASSISTENTE_MODELO", "COPILOTO_MODELO") or "anthropic/claude-opus-5"

# O idioma da resposta. `INSTRUCOES` esta em portugues, mas nunca MANDAVA
# responder nele — e um modelo espelha o idioma de quem escreve, entao uma
# pergunta em ingles voltava em ingles no meio de uma interface em pt-BR.
ASSISTENTE_IDIOMA: str = _env_ou_legado("ASSISTENTE_IDIOMA", "COPILOTO_IDIOMA") or "português do Brasil"

# Quantos tokens do assistente cada pessoa gasta numa janela de 24 h (a cota em
# `app/mcp/cotas.py`, que explica o padrão). É o teto de todos; uma extensão de
# planos parte dele para o teto de cada plano. Zero ou negativo travaria toda
# conversa depois do primeiro turno: um valor assim impede a API de subir.
def _teto_do_assistente() -> int:
    bruto = os.getenv("ASSISTENTE_TETO_DE_TOKENS_POR_DIA", "").strip()
    if not bruto:
        return 1_500_000
    try:
        teto = int(bruto)
    except ValueError:
        teto = 0
    if teto <= 0:
        raise ValueError(
            f"ASSISTENTE_TETO_DE_TOKENS_POR_DIA={bruto!r}: o teto precisa ser um inteiro positivo."
        )
    return teto


ASSISTENTE_TETO_DE_TOKENS_POR_DIA: int = _teto_do_assistente()

# ── Fundos de mapa ────────────────────────────────────────────────────────
# Os servidores de tiles da instalação. O código não traz nenhum além do
# OpenStreetMap (as ruas, quando MAPA_RUAS_URL está vazia): imagem de satélite
# exige um provedor e os termos dele, e cada instalação escolhe o seu. Os mesmos
# valores vão para o web (web/lib/fundos-do-mapa.ts, o mapa e o globo) e, por
# aqui, para os nós Carta: o servidor injeta o fundo escolhido no despacho
# (`app/services/fundos_do_mapa.py`), e o executor não precisa de configuração.
# Template com {z}, {x} e {y}; o crédito vai na atribuição do mapa e da carta.
def _fundo_do_ambiente(prefixo: str) -> dict[str, str] | None:
    url = os.getenv(f"MAPA_{prefixo}_URL", "").strip()
    if not url:
        return None
    if not re.match(r"^https?://", url) or any(m not in url for m in ("{z}", "{x}", "{y}")):
        logging.getLogger("atlans.config").error(
            "MAPA_%s_URL=%r não é um template de tiles (https://…/{z}/{x}/{y}…) — ignorada.",
            prefixo, url,
        )
        return None
    return {"url": url, "credito": os.getenv(f"MAPA_{prefixo}_CREDITO", "").strip()}


MAPA_FUNDOS: dict[str, dict[str, str]] = {
    nome: fundo
    for nome, prefixo in (("ruas", "RUAS"), ("satelite", "SATELITE"), ("hibrido", "HIBRIDO"))
    if (fundo := _fundo_do_ambiente(prefixo)) is not None
}
# Sem o híbrido, o satélite — como no web (web/lib/fundos-do-mapa.ts) e no
# executor (flow/utils/carta.py), para a Carta e a Home dizerem o mesmo.
if "hibrido" not in MAPA_FUNDOS and "satelite" in MAPA_FUNDOS:
    MAPA_FUNDOS["hibrido"] = MAPA_FUNDOS["satelite"]

# ── Catálogo de fontes pré-mapeadas ───────────────────────────────────────
# A pasta do Vault versionada no repositório (`catalogo/geoservicos/`), importada
# no arranque de forma idempotente. VAZIA ou inexistente = não importa nada;
# AUSENTE = a pasta do repositório. Não é o `.strip() or` das outras: com ele, o
# vazio que o .env.example e docs/sources.md ensinam voltava ao padrão, e não
# havia como desligar. O compose passa `${FONTES_CATALOGO_DIR-…}` (sem os
# dois-pontos) para o vazio do .env chegar vazio.
_catalogo_dir = os.getenv("FONTES_CATALOGO_DIR")
FONTES_CATALOGO_DIR: str = "catalogo/geoservicos" if _catalogo_dir is None else _catalogo_dir.strip()
# Toda execução bem-sucedida com nó WFS registra a fonte no catálogo do workspace.
FONTES_APRENDER_DAS_EXECUCOES: bool = os.getenv(
    "FONTES_APRENDER_DAS_EXECUCOES", "true"
).strip().lower() not in ("false", "0", "off", "no")
# Intervalo da verificação por endpoint (um GetCapabilities por URL distinta).
# 0 desliga o laço; a importação e o assistente continuam funcionando.
FONTES_VERIFICACAO_INTERVAL: int = int(os.getenv("FONTES_VERIFICACAO_INTERVAL", "").strip() or "86400")

# ── Senhas de exemplo ──────────────────────────────────────────────────────
# Os valores do .env.example não são senha: quem copia o arquivo à mão (sem o
# `make bootstrap`, que gera valores fortes) subiria o MinIO publicado em
# S3_HOST, e o Redis, com uma senha que está num repositório público. Parar a
# API diz; o APP_SECRET curto já parava.
for _nome in ("MINIO_ROOT_PASSWORD", "REDIS_PASSWORD", "REDIS_URL", "RATE_LIMIT_STORAGE_URI"):
    _valor = os.getenv(_nome, "")
    if "change-me" in _valor.lower() or "troque-me" in _valor.lower():
        raise ValueError(
            f"{_nome} ainda leva o valor de exemplo do .env.example: gere uma senha "
            "(openssl rand -base64 32) ou rode `make bootstrap`."
        )

# ── E-mail ─────────────────────────────────────────────────────────────────
# O transporte (app/services/email_transporte.py): `resend` (a API da Resend),
# `smtp` (qualquer servidor SMTP) ou `log` (nada sai; o e-mail vai para o log).
# Vazio = o que estiver configurado: Resend com RESEND_API_KEY, SMTP com
# SMTP_HOST, log sem nenhum dos dois.
EMAIL_BACKEND: str = os.getenv("EMAIL_BACKEND", "").strip().lower()
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
# `starttls` (padrão, porta 587), `ssl` (TLS desde a conexão, porta 465) ou
# `nenhuma` (relay local sem TLS, porta 25). SMTP_PORT vazia = a porta do modo.
SMTP_SEGURANCA: str = os.getenv("SMTP_SEGURANCA", "").strip().lower() or "starttls"
# Um erro de digitação aqui mandaria o e-mail por outro caminho (um modo de TLS
# desconhecido virava STARTTLS) ou só falharia no primeiro envio, com um erro
# do smtplib que não diz a causa. Parar a API diz.
if EMAIL_BACKEND not in ("", "resend", "smtp", "log"):
    raise ValueError(
        f"EMAIL_BACKEND={EMAIL_BACKEND!r}: use resend, smtp ou log (vazio = o que estiver configurado)."
    )
if SMTP_SEGURANCA not in ("starttls", "ssl", "nenhuma"):
    raise ValueError(f"SMTP_SEGURANCA={SMTP_SEGURANCA!r}: use starttls, ssl ou nenhuma.")
if EMAIL_BACKEND == "smtp" and not SMTP_HOST:
    raise ValueError("EMAIL_BACKEND=smtp sem SMTP_HOST: defina o servidor SMTP.")
if EMAIL_BACKEND == "resend" and not RESEND_API_KEY:
    raise ValueError("EMAIL_BACKEND=resend sem RESEND_API_KEY: defina a chave da Resend.")
SMTP_PORT: int = int(
    os.getenv("SMTP_PORT", "").strip()
    or {"ssl": "465", "nenhuma": "25"}.get(SMTP_SEGURANCA, "587")
)
SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
# `nenhuma` é para um relay local sem autenticação: com usuário, a senha iria
# em claro pela rede (LOGIN/PLAIN na porta 25). É o único erro de e-mail que
# não falhava no arranque.
if SMTP_HOST and SMTP_SEGURANCA == "nenhuma" and SMTP_USERNAME:
    raise ValueError(
        "SMTP_SEGURANCA=nenhuma com SMTP_USERNAME: a senha iria em claro pela rede. "
        "Use starttls ou ssl, ou tire o usuário (relay local sem autenticação)."
    )
# Remetente de todo e-mail, em qualquer transporte. RESEND_FROM_EMAIL é o nome
# antigo e continua valendo. Vazio = `noreply@` no host do FRONTEND_URL (o
# domínio precisa estar verificado no provedor). `.strip() or` porque o compose
# passa vazio.
EMAIL_FROM: str = _env_ou_legado("EMAIL_FROM", "RESEND_FROM_EMAIL") or remetente_padrao(FRONTEND_URL)
RESEND_FROM_EMAIL: str = EMAIL_FROM
# O login exige o e-mail verificado (padrão). Numa instalação sem transporte de
# e-mail, o link de verificação nunca chega: `false` deixa entrar sem ele — e o
# cadastro aberto, então, não confirma que o e-mail é de quem se cadastrou: um
# convite por e-mail chega a quem criou a conta com aquele endereço. Com
# transporte, o convite exige a conta verificada (`workspace_router`).
EXIGIR_EMAIL_VERIFICADO: bool = (
    os.getenv("EXIGIR_EMAIL_VERIFICADO", "").strip().lower() not in ("false", "0", "nao", "não", "no")
)

# TTLs dos tokens (em minutos)
EMAIL_VERIFY_TOKEN_TTL: int = int(os.getenv("EMAIL_VERIFY_TOKEN_TTL", "1440"))   # 24h
PASSWORD_RESET_TOKEN_TTL: int = int(os.getenv("PASSWORD_RESET_TOKEN_TTL", "30"))  # 30min
