# app/core/config.py
import ipaddress
import logging
import os
import re
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL   = os.getenv("DATABASE_URL")

# Redis connection URL — used by pub/sub, the run_creates/run_results queues and the cache.
# Ex: redis://:senha@redis:6379/0
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
ECHO_SQL       = os.getenv("ECHO_SQL", "false").lower() == "true"

# Routing by workspace POLICY (docs/specs/executor-isolation-routing.md).
#   off → legacy path: the workspace's dedicated executor, then the whole pool.
#   on  → policy chain: tier 1 → tier 2 → terminal (fail | pool).
# With the backfill from migration 20260907_0002, `on` produces exactly the same
# candidates as `off` for every existing workspace — the flag exists for
# rollback, not for shadowing. Read at call time so that tests can
# toggle it by patching the module.
EXECUTOR_POLICY_ROUTING = os.getenv("EXECUTOR_POLICY_ROUTING", "off").strip().lower()


def policy_routing_enabled() -> bool:
    return EXECUTOR_POLICY_ROUTING == "on"

# PERF: Connection pool sized for 4 uvicorn workers in production.
#
# The ceiling is PER WORKER and PER ENGINE, not global. Today there is a single engine (the async one,
# in app/core/db.py), so the total is `workers × (POOL_SIZE + MAX_OVERFLOW)`
# = 4 × 13 = 52 connections.
#
# Two pitfalls that have already exacted their price here:
#
# 1. The previous comment computed "4 × 20 = 80; overflow +10", treating the
#    overflow as global. With the values of the time (20/10) the real ceiling was
#    4 × 30 = 120, ABOVE Postgres's default `max_connections`, which is 100.
#    Exceeding that limit does not slow things down: it returns `FATAL: sorry, too many
#    clients already`, which shows up as intermittent instability.
# 2. There was a second (synchronous) engine reusing these same
#    constants, which doubled the ceiling. It was removed — if a new engine ever comes
#    back, either it has its own explicit pool, or this math changes.
#
# When raising POOL_SIZE/MAX_OVERFLOW, check `SHOW max_connections` on the server
# and leave headroom for migrations, psql and other clients.
#
# POOL_RECYCLE=600s avoids dead connections (cloud providers time out at ~10min).
POOL_SIZE      = int(os.getenv("POOL_SIZE", 8))
MAX_OVERFLOW   = int(os.getenv("MAX_OVERFLOW", 5))
POOL_TIMEOUT   = int(os.getenv("POOL_TIMEOUT", 30))
POOL_RECYCLE   = int(os.getenv("POOL_RECYCLE", 600))
POOL_PRE_PING  = os.getenv("POOL_PRE_PING", "true").lower() == "true"

# Deadlines for each database command, in seconds (app/core/db.py). The POOL_TIMEOUT
# above only limits the wait for a free connection; without these, a stuck
# query (a lock waiting on another, a bad plan, a network that vanishes without dropping the
# connection) holds the connection forever, and a few stuck ones exhaust the worker's pool.
# - DB_STATEMENT_TIMEOUT: Postgres cancels the command and responds with a clear
#   error (the session's `statement_timeout`). Lock waiting counts.
# - DB_COMMAND_TIMEOUT: asyncpg gives up waiting for the response — the database that
#   doesn't even respond. Larger than the previous one, so that in the normal case the one that cancels
#   is Postgres.
# 0 disables each one. A task that needs more time makes an exception only in
# its own transaction, `SET LOCAL statement_timeout = '80s'` — up to
# DB_COMMAND_TIMEOUT, which is client-side and cannot be raised per transaction.
def _seconds_from_env(nome: str, padrao: int) -> int:
    """Whole seconds of `nome`; empty means the default (compose passes both
    through with `${VAR:-}`). A value that is not an integer ("60s", "5min", "1.5")
    means the default with a warning, instead of breaking the import — and with it the API.
    The ceiling is Postgres's (statement_timeout is an int in milliseconds): above
    it the server would refuse EVERY new connection."""
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


DB_STATEMENT_TIMEOUT = _seconds_from_env("DB_STATEMENT_TIMEOUT", 60)
DB_COMMAND_TIMEOUT   = _seconds_from_env("DB_COMMAND_TIMEOUT", 90)


APP_SECRET = os.getenv("APP_SECRET")
if not APP_SECRET:
    raise ValueError("A variável de ambiente APP_SECRET precisa ser definida.")
# Audit (SEG-65): APP_SECRET signs the JWTs (HS256). A short secret can be
# brute-forced offline. Requires at least 32 characters — enough for 256 bits
# of entropy when generated with `secrets.token_urlsafe(32)`.
_APP_SECRET_MIN = 32
if len(APP_SECRET) < _APP_SECRET_MIN:
    raise ValueError(
        f"APP_SECRET precisa ter pelo menos {_APP_SECRET_MIN} caracteres "
        "(gere com `python -c \"import secrets; print(secrets.token_urlsafe(32))\"`)."
    )

# Fernet key for credential encryption (connection strings).
# Must be a 32-byte base64url value generated with Fernet.generate_key().
# It is separate from APP_SECRET and mandatory — the app does NOT derive the cipher key from
# APP_SECRET (avoids reusing a secret meant for a different purpose).
FERNET_KEY: str = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("A variável de ambiente FERNET_KEY precisa ser definida.")

# Key rotation (optional): FERNET_KEYS accepts SEVERAL comma-separated
# keys. The FIRST in the effective list is the one that ENCRYPTS; ALL decrypt (MultiFernet
# in encryption.py). To rotate, PREPEND the new key:
#   FERNET_KEYS="<nova>,<antiga>"  → starts encrypting with <nova> (new) and still reads <antiga> (old).
#
# Safety net against operator error: FERNET_KEY is ALWAYS kept in the
# decryption list (appended at the end if it is not in FERNET_KEYS). That way, forgetting
# to re-list the current key does not make unreadable ("orphan") everything already
# encrypted with it — the worst case becomes "encrypts with the new one, still reads the old one", never
# data loss. To actually RETIRE a key, change FERNET_KEY (an
# explicit act), not just FERNET_KEYS. Without FERNET_KEYS ⇒ uses only FERNET_KEY,
# identical to the previous behavior.
_raw_fernet_keys = os.getenv("FERNET_KEYS", "")
_fernet_keys = [k.strip() for k in _raw_fernet_keys.split(",") if k.strip()]
if FERNET_KEY not in _fernet_keys:
    _fernet_keys.append(FERNET_KEY)
FERNET_KEYS: list[str] = _fernet_keys

# ── Job encryption for Executors ─────────────────────────────────────────────────
# The server's Ed25519 private key for signing job envelopes.
# Generate with: python -c "
#   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
#   import base64; k = Ed25519PrivateKey.generate()
#   print(base64.b64encode(k.private_bytes_raw()).decode())
# "
EXECUTOR_SIGNING_KEY: str | None = os.getenv("EXECUTOR_SIGNING_KEY")

# ── mTLS + step-ca (executor enrollment) ──────────────────────────────────────────
# Internal URL of the step-ca CA (root + intermediate). In prod, usually
# https://step-ca:9000 inside the proxy-net network.
STEPCA_URL: str = os.getenv("STEPCA_URL", "https://step-ca:9000")

# JWK provisioner the app uses to sign CSRs on behalf of the executors.
# Created once via: `step ca provisioner add atlans-app --type=jwk --create`.
STEPCA_PROVISIONER_NAME: str = os.getenv("STEPCA_PROVISIONER_NAME", "atlans-app")
STEPCA_PROVISIONER_PASSWORD: str | None = os.getenv("STEPCA_PROVISIONER_PASSWORD")

# Path of step-ca's ca.json inside the api-prod container.
# Needed to decrypt the JWK provisioner's `encryptedKey` and generate OTTs (one-time
# tokens) signed with ES256, as step-ca expects.
# The ca.json is mounted as `:ro` via the step-ca-data volume — see docker-compose.yml.
STEPCA_CA_CONFIG_PATH: str = os.getenv("STEPCA_CA_CONFIG_PATH", "/etc/step-ca/config/ca.json")

# Path of the internal CA's root cert (root_ca.crt), mounted read-only in api-prod
# via step-ca-data:/etc/step-ca. Included in the enroll response so the executor
# can validate the full chain of the executors host's TLS cert (root as
# trust anchor; the intermediate comes from step-ca's /1.0/sign response).
STEPCA_ROOT_CERT_PATH: str = os.getenv("STEPCA_ROOT_CERT_PATH", "/etc/step-ca/certs/root_ca.crt")

# SHA-256 fingerprint of the CA's root cert — used for pinning when the
# server exposes the ca_pem in the enrollment response.
STEPCA_ROOT_FINGERPRINT: str = os.getenv("STEPCA_ROOT_FINGERPRINT", "")

# Pepper used in the HMAC-SHA256 of the enrollment OTPs. Generate with:
#   python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
# CRITICAL: rotating it invalidates ALL in-flight OTPs. Never commit it.
OTP_PEPPER: str = os.getenv("OTP_PEPPER", "")

# TTL of the issued mTLS cert (days). Short enough to limit exposure
# of a leaked key, long enough to tolerate offline executors.
EXECUTOR_CERT_TTL_DAYS: int = int(os.getenv("EXECUTOR_CERT_TTL_DAYS", "90"))

# TTL of the bootstrap OTP (hours). 24h covers delivery + setup but avoids
# a long leak window.
EXECUTOR_OTP_TTL_HOURS: int = int(os.getenv("EXECUTOR_OTP_TTL_HOURS", "24"))

# Origins allowed by CORS. In production, set explicitly, e.g.:
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

# ── Addresses of this installation ───────────────────────────────────────────
# Nothing here points to a specific installation: the code is the same for anyone
# self-hosting Atlans. Each address comes from the environment, and the ones that have a
# convention (the executors host, the MCP, the sender) derive from FRONTEND_URL.

def _host_de(url: str) -> str:
    """The host of a URL, without port, lowercase and in ASCII; empty if it
    has none. A domain with accents becomes punycode (`xn--`), which is how it arrives in
    the Host header and how it goes into a script."""
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


def _normalized_site(url: str) -> str:
    """The site URL without spaces or a trailing `/`, with the host in ASCII.

    A space stuck to the secret's value silently became an invalid host
    in the values derived from here (the MCP answered 421 to everything, and install.sh
    exited without a server).
    """
    url = url.strip().rstrip("/")
    try:
        partes = urlsplit(url)
        host, porta = partes.hostname or "", partes.port
    except ValueError:
        return url
    if not host or host.isascii():
        return url
    as_ascii = _host_de(url)
    if not as_ascii:
        return url
    return urlunsplit(partes._replace(netloc=as_ascii + (f":{porta}" if porta else "")))


# Public URL of the site, the one the browser opens. It goes in the email links and is the
# origin of the conventions below.
FRONTEND_URL: str = _normalized_site(os.getenv("FRONTEND_URL", "")) or "http://localhost:3000"
# Without a scheme (`atlans.example.org`) the URL passed every gate and
# silently disabled the conventions: sender `noreply@localhost`, MCP without the
# site's host, enrollment screen without the executors host — three symptoms
# far from the cause. Same policy as ALLOWED_ORIGINS: stopping the API says so.
if not re.match(r"^https?://", FRONTEND_URL, re.IGNORECASE):
    raise ValueError(f"FRONTEND_URL={FRONTEND_URL!r} precisa começar com http:// ou https://")


def _host_with_domain(url: str) -> str:
    """The URL's host when it has a domain; empty for localhost, `*.localhost`
    and IPs, which serve as the basis for no convention at all."""
    host = _host_de(url)
    if not host or host == "localhost" or host.endswith(".localhost"):
        return ""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    return ""


def agents_by_convention(frontend_url: str) -> str:
    """`https://agents.<host do site>` (site host), the convention the executor uses in the reverse
    direction (executor/_ca_bootstrap.py). Without a domain or without https, none."""
    host = _host_with_domain(frontend_url)
    if host and frontend_url.strip().lower().startswith("https://"):
        return f"https://agents.{host}"
    return ""


def _ip_do_site(url: str) -> str:
    """The URL's host when it is an IP (an installation without a domain)."""
    host = _host_de(url)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return ""
    return host


def default_mcp_hosts(frontend_url: str) -> list[str]:
    """The site's host (with and without port) plus local dev. A site served by IP goes in
    with the IP: the DNS rebinding protection is for names, and a Host that is already an
    IP is not subject to rebinding — without it, `/mcp` answered 421 until someone set
    MCP_ALLOWED_HOSTS."""
    host = _host_with_domain(frontend_url) or _ip_do_site(frontend_url)
    return ([host, f"{host}:*"] if host else []) + ["localhost:*", "127.0.0.1:*"]


def default_sender(frontend_url: str) -> str:
    """`noreply@` at the site's host; without a domain, `localhost`."""
    return f"Atlans <noreply@{_host_with_domain(frontend_url) or 'localhost'}>"


# URL of the executors host (the mTLS one), in https: the `--server` of the
# enrollment commands and the default of the served install.sh. Empty = the convention above; on a host
# without a domain it also stays empty, and the enrollment screen asks for the address.
AGENTS_URL: str = (
    os.getenv("AGENTS_URL", "").strip().rstrip("/") or agents_by_convention(FRONTEND_URL)
)

# Git repository that install.sh clones on the executor's machine. Empty: the served
# script carries no default and asks for `--repo=`.
EXECUTOR_REPO_URL: str = os.getenv("EXECUTOR_REPO_URL", "").strip()

# GitHub repository (`dono/nome`) whose `desktop/v*` releases carry the
# Windows installer the dashboard offers. Empty disables the offer.
_raw_desktop_repo = os.getenv("DESKTOP_RELEASES_REPO", "").strip().strip("/")
if _raw_desktop_repo and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", _raw_desktop_repo):
    logging.getLogger(__name__).error(
        "DESKTOP_RELEASES_REPO=%r não é `dono/nome` — o painel não oferece o app desktop.",
        _raw_desktop_repo,
    )
    _raw_desktop_repo = ""
DESKTOP_RELEASES_REPO: str = _raw_desktop_repo

# ── MCP server (/mcp) ─────────────────────────────────────────────────────────
# `Host` values accepted by the streamable HTTP transport. It is a defense against DNS rebinding:
# an arbitrary site cannot point a name of its own at 127.0.0.1 and talk
# to the developer's MCP. Comma-separated list; `*` only after the port
# (e.g. "localhost:*"). Empty = the FRONTEND_URL host (with and without port) plus
# local dev.
_raw_mcp_hosts = os.getenv("MCP_ALLOWED_HOSTS", "")
MCP_ALLOWED_HOSTS: list[str] = (
    [h.strip() for h in _raw_mcp_hosts.split(",") if h.strip()]
    or default_mcp_hosts(FRONTEND_URL)
)

# ── Assistant (building workflows from natural language) ─────────────────────
# The model comes from any API compatible with OpenAI's (`/chat/completions`,
# `app/services/openrouter.py`): OpenRouter (the default), a gateway (LiteLLM)
# or a local server (Ollama, vLLM, llama.cpp), with a model that can
# call tools. The key belongs to the PLATFORM, not the user: the installation pays for the
# model's tokens, and the per-person ceiling lives in Redis
# (`app/mcp/cotas.py`). Without a key the assistant simply does not exist — the route
# answers that it is disabled and the rest of the editor stays whole.
#
# LLM_API_KEY and LLM_BASE_URL are the generic names; OPENROUTER_API_KEY and
# OPENROUTER_BASE_URL still work. A local server that requires no key
# accepts any non-empty value (e.g. `local`).
OPENROUTER_API_KEY: str = os.getenv("LLM_API_KEY", "").strip() or os.getenv("OPENROUTER_API_KEY", "")
# The API base (`.../v1`). Empty = OpenRouter's public one. `.strip() or` for the
# reason given at ASSISTENTE_MODELO.
OPENROUTER_BASE_URL: str = (
    os.getenv("LLM_BASE_URL", "").strip()
    or os.getenv("OPENROUTER_BASE_URL", "").strip()
    or "https://openrouter.ai/api/v1"
)
# App attribution on OpenRouter (the X-Title and HTTP-Referer headers, which
# put the installation's name and FRONTEND_URL in its public app ranking).
# Off by default: each installation decides whether it shows up.
ASSISTENTE_ATRIBUICAO: bool = (
    os.getenv("ASSISTENTE_ATRIBUICAO", "").strip().lower() in ("true", "1", "on", "yes", "sim")
)


def _env_or_legacy(nova: str, legada: str) -> str:
    """Reads the NEW env var; if absent/empty, falls back to the LEGACY one — with a warning.

    F4 renamed COPILOTO_{ATIVO,MODEL,IDIOMA} -> ASSISTENTE_{...} with no
    coexistence period: a server .env still using the old names reconfigured
    the assistant SILENTLY (enabled by default, factory model/language). The
    fallback is temporary — remove it once the production .env files have migrated; the
    warning at startup is the reminder.
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
    _env_or_legacy("ASSISTENTE_ATIVO", "COPILOTO_ATIVO") or "true"
).lower() not in ("false", "0", "off", "no")

# The model is an environment variable, and not a constant in the code, so that changing it
# is an edit to `.env` and a restart — not a deploy. New models come out
# much more often than this repository changes, and the alternative is the value
# going stale inside a module nobody has a reason to open.
#
# The name is the one in the provider's catalog: on OpenRouter, `fornecedor/modelo` (vendor/model, e.g.
# `anthropic/claude-opus-5`, `openai/gpt-5`, `google/gemini-2.5-pro`; the live
# list is at https://openrouter.ai/models); on a local server, its own name
# (`qwen3:14b` on Ollama). The default below only exists on OpenRouter.
#
# `.strip() or` and not `getenv`'s default: compose passes
# `ASSISTENTE_MODELO: ${ASSISTENTE_MODELO:-}`, which SETS the variable to an empty
# string when nobody configured it. `getenv`'s default only covers "not
# set", so without this the default installation would start up requesting a model with an
# empty name — and the error would only show up in the first conversation. Same care as
# `MCP_ALLOWED_HOSTS` above.
ASSISTENTE_MODELO: str = _env_or_legacy("ASSISTENTE_MODELO", "COPILOTO_MODELO") or "anthropic/claude-opus-5"

# The response language. `INSTRUCTIONS` is in Portuguese, but it never TOLD the model to
# answer in it — and a model mirrors the language of whoever writes, so a
# question in English came back in English in the middle of a pt-BR interface.
ASSISTENTE_IDIOMA: str = _env_or_legacy("ASSISTENTE_IDIOMA", "COPILOTO_IDIOMA") or "português do Brasil"

# How many assistant tokens each person spends in a 24 h window (the quota in
# `app/mcp/cotas.py`, which explains the default). It is the ceiling for everyone; a plans
# extension derives each plan's ceiling from it. Zero or negative would block every
# conversation after the first turn: such a value prevents the API from starting.
def _assistant_ceiling() -> int:
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


ASSISTENTE_TETO_DE_TOKENS_POR_DIA: int = _assistant_ceiling()

# ── Map basemaps ──────────────────────────────────────────────────────────
# The installation's tile servers. The code ships none besides
# OpenStreetMap (the streets, when MAPA_RUAS_URL is empty): satellite imagery
# requires a provider and its terms, and each installation picks its own. The same
# values go to the web (web/lib/fundos-do-mapa.ts, the map and the globe) and, through
# here, to the Carta nodes: the server injects the chosen basemap into the dispatch
# (`app/services/fundos_do_mapa.py`), and the executor needs no configuration.
# Template with {z}, {x} and {y}; the credit goes in the map's and the image map's attribution.
def _env_fallback(prefixo: str) -> dict[str, str] | None:
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
    if (fundo := _env_fallback(prefixo)) is not None
}
# Without the hybrid, the satellite — as on the web (web/lib/fundos-do-mapa.ts) and in the
# executor (flow/utils/carta.py), so the Carta and the Home say the same thing.
if "hibrido" not in MAPA_FUNDOS and "satelite" in MAPA_FUNDOS:
    MAPA_FUNDOS["hibrido"] = MAPA_FUNDOS["satelite"]

# ── Catalog of pre-mapped sources ─────────────────────────────────────────
# The Vault folder versioned in the repository (`catalogo/geoservicos/`), imported
# idempotently at startup. EMPTY or nonexistent = imports nothing;
# ABSENT = the repository folder. It is not the `.strip() or` of the others: with it, the
# empty value that .env.example and docs/sources.md teach went back to the default, and there
# was no way to turn it off. Compose passes `${FONTES_CATALOGO_DIR-…}` (without the
# colon) so that the .env's empty value arrives empty.
_catalog_dir = os.getenv("FONTES_CATALOGO_DIR")
FONTES_CATALOGO_DIR: str = "catalogo/geoservicos" if _catalog_dir is None else _catalog_dir.strip()
# Every successful run with a WFS node registers the source in the workspace's catalog.
FONTES_APRENDER_DAS_EXECUCOES: bool = os.getenv(
    "FONTES_APRENDER_DAS_EXECUCOES", "true"
).strip().lower() not in ("false", "0", "off", "no")
# Interval of the per-endpoint check (one GetCapabilities per distinct URL).
# 0 disables the loop; the import and the assistant keep working.
FONTES_VERIFICACAO_INTERVAL: int = int(os.getenv("FONTES_VERIFICACAO_INTERVAL", "").strip() or "86400")

# ── Example passwords ──────────────────────────────────────────────────────
# The .env.example values are not passwords: whoever copies the file by hand (without
# `make bootstrap`, which generates strong values) would bring up MinIO published at
# S3_HOST, and Redis, with a password that sits in a public repository. Stopping the
# API says so; the short APP_SECRET already stopped it.
for _nome in ("MINIO_ROOT_PASSWORD", "REDIS_PASSWORD", "REDIS_URL", "RATE_LIMIT_STORAGE_URI"):
    _value = os.getenv(_nome, "")
    if "change-me" in _value.lower() or "troque-me" in _value.lower():
        raise ValueError(
            f"{_nome} ainda leva o valor de exemplo do .env.example: gere uma senha "
            "(openssl rand -base64 32) ou rode `make bootstrap`."
        )

# ── Email ──────────────────────────────────────────────────────────────────
# The transport (app/services/email_transporte.py): `resend` (the Resend API),
# `smtp` (any SMTP server) or `log` (nothing goes out; the email goes to the log).
# Empty = whatever is configured: Resend with RESEND_API_KEY, SMTP with
# SMTP_HOST, log with neither.
EMAIL_BACKEND: str = os.getenv("EMAIL_BACKEND", "").strip().lower()
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
# `starttls` (default, port 587), `ssl` (TLS from connection start, port 465) or
# `nenhuma` (none: local relay without TLS, port 25). Empty SMTP_PORT = the mode's port.
SMTP_SEGURANCA: str = os.getenv("SMTP_SEGURANCA", "").strip().lower() or "starttls"
# A typo here would send the email down another path (an unknown TLS mode
# became STARTTLS) or would only fail on the first send, with an smtplib error
# that doesn't state the cause. Stopping the API says so.
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
# `nenhuma` is for a local relay without authentication: with a user, the password would go
# in clear text over the network (LOGIN/PLAIN on port 25). It is the only email error that
# did not fail at startup.
if SMTP_HOST and SMTP_SEGURANCA == "nenhuma" and SMTP_USERNAME:
    raise ValueError(
        "SMTP_SEGURANCA=nenhuma com SMTP_USERNAME: a senha iria em claro pela rede. "
        "Use starttls ou ssl, ou tire o usuário (relay local sem autenticação)."
    )
# Sender of every email, on any transport. RESEND_FROM_EMAIL is the old
# name and still works. Empty = `noreply@` at the FRONTEND_URL host (the
# domain must be verified with the provider). `.strip() or` because compose
# passes it empty.
EMAIL_FROM: str = _env_or_legacy("EMAIL_FROM", "RESEND_FROM_EMAIL") or default_sender(FRONTEND_URL)
RESEND_FROM_EMAIL: str = EMAIL_FROM
# Login requires a verified email (default). On an installation without an email
# transport, the verification link never arrives: `false` lets people in without it — and
# open sign-up, then, does not confirm the email belongs to whoever signed up: an
# email invitation reaches whoever created the account with that address. With a
# transport, the invitation requires a verified account (`workspace_router`).
EXIGIR_EMAIL_VERIFICADO: bool = (
    os.getenv("EXIGIR_EMAIL_VERIFICADO", "").strip().lower() not in ("false", "0", "nao", "não", "no")
)

# Token TTLs (in minutes)
EMAIL_VERIFY_TOKEN_TTL: int = int(os.getenv("EMAIL_VERIFY_TOKEN_TTL", "1440"))   # 24h
PASSWORD_RESET_TOKEN_TTL: int = int(os.getenv("PASSWORD_RESET_TOKEN_TTL", "30"))  # 30min
