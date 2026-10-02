# app/core/utils/jwt_utils.py
"""
Utilitários JWT — criação e validação de tokens de acesso e refresh — e o
hash de senha.

O hash de senha é o `bcrypt_sha256` que o passlib definiu, reproduzido aqui
sobre o `bcrypt` direto (o passlib saiu: sem manutenção desde 2020, quebrava
com o bcrypt 4.1+ e carregava uma licença composta no aviso de terceiros).
O formato gravado no banco é o mesmo, então todo hash existente continua
válido e um hash novo ainda é lido pela versão anterior do código:

    $bcrypt-sha256$v=2,t=2b,r=12$<salt de 22>$<digest de 31>

A pré-chave é o HMAC-SHA256 da senha com o salt como chave, em base64 (44
bytes): é o que tira o limite de 72 bytes do bcrypt e o que impede o truque
do prefixo. Os hashes da versão 1 do esquema (SHA-256 puro, formato
`$bcrypt-sha256$2b,12$…`) também verificam, caso exista algum.
"""
import base64
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from fastapi import HTTPException, status as http_status

from app.core.config import APP_SECRET
from app.core.utils.logger import get_logger

_logger = get_logger(__name__)

_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = int(30)
_REFRESH_EXPIRE_DAYS = int(2)
# Audience por contexto: impede que um token emitido para um proposito
# seja usado em outro (ex: refresh_token apresentado como access_token a
# um endpoint vulneravel). Cada decoder exige sua audience especifica.
AUDIENCE_ACCESS  = "atlas-studio:access"
AUDIENCE_REFRESH = "atlas-studio:refresh"

# ── Rotação de refresh token ──────────────────────────────────────────────────
# Cada login abre uma "família" de refresh tokens. O Redis guarda qual jti é o
# válido no momento da família; a cada refresh o jti rotaciona. Se um jti antigo
# (já rotacionado) reaparece, é sinal de roubo → revogamos a família inteira.
_REFRESH_FAMILY_PREFIX = "refresh_family:"
_REFRESH_PREV_PREFIX   = "refresh_prev:"
_REFRESH_FAMILY_TTL    = _REFRESH_EXPIRE_DAYS * 24 * 60 * 60
# Janela de graça: tolera o jti imediatamente anterior por alguns segundos para
# não derrubar a sessão quando o cliente dispara refreshes concorrentes
# (ex.: o callback jwt do NextAuth em requisições paralelas).
_REFRESH_GRACE_SECONDS = 30

# ── Hash de senha (bcrypt_sha256, versão 2) ─────────────────────────────────
_ROUNDS = 12
_HASH = re.compile(
    r"^\$bcrypt-sha256\$"
    r"(?:v=(?P<versao>\d+),t=(?P<tipo>2[ab]),r=(?P<rounds>\d{1,2})"   # versão 2
    r"|(?P<tipo1>2[ab]),(?P<rounds1>\d{1,2}))"                         # versão 1
    r"\$(?P<salt>[./A-Za-z0-9]{22})\$(?P<digest>[./A-Za-z0-9]{31})$"
)


def _pre_chave(plain: str, salt: str, versao: int) -> bytes:
    """A senha como o bcrypt a recebe: HMAC-SHA256 com o salt (v2) ou SHA-256
    puro (v1), em base64 — 44 bytes, dentro do limite de 72 do bcrypt."""
    senha = plain.encode("utf-8")
    if versao >= 2:
        digest = hmac.new(salt.encode("ascii"), senha, hashlib.sha256).digest()
    else:
        digest = hashlib.sha256(senha).digest()
    return base64.b64encode(digest)


def hash_password(plain: str) -> str:
    """Um hash `bcrypt_sha256` v2 novo, com salt próprio."""
    config = bcrypt.gensalt(rounds=_ROUNDS, prefix=b"2b")          # b"$2b$12$<salt>"
    salt = config[-22:].decode("ascii")
    completo = bcrypt.hashpw(_pre_chave(plain, salt, 2), config).decode("ascii")
    return f"$bcrypt-sha256$v=2,t=2b,r={_ROUNDS}${salt}${completo[-31:]}"


def verify_password(plain: str, hashed: str) -> bool:
    """A senha confere com o hash? Um hash fora do formato (ou vazio) é só
    falso — nunca uma exceção no login."""
    partes = _HASH.match(hashed or "")
    if not partes or not isinstance(plain, str):
        return False
    versao = int(partes["versao"]) if partes["versao"] else 1
    tipo = partes["tipo"] or partes["tipo1"]
    rounds = int(partes["rounds"] or partes["rounds1"])
    config = f"${tipo}${rounds:02d}${partes['salt']}".encode("ascii")
    try:
        calculado = bcrypt.hashpw(_pre_chave(plain, partes["salt"], versao), config)
    except ValueError:
        return False
    return hmac.compare_digest(calculado[-31:], partes["digest"].encode("ascii"))


def _encode(data: dict, expires_delta: timedelta, audience: str) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    payload["aud"] = audience
    return jwt.encode(payload, APP_SECRET, algorithm=_ALGORITHM)


def create_access_token(data: dict) -> str:
    return _encode(
        {**data, "type": "access"},
        timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
        AUDIENCE_ACCESS,
    )


def create_refresh_token(data: dict) -> str:
    return _encode(
        {**data, "type": "refresh"},
        timedelta(days=_REFRESH_EXPIRE_DAYS),
        AUDIENCE_REFRESH,
    )


def decode_token(token: str, *, expected_audience: str) -> dict:
    """Decodifica e valida o token, exigindo audience especifica.

    expected_audience: passe AUDIENCE_ACCESS ou AUDIENCE_REFRESH conforme o
    uso. Tokens com audience diferente sao rejeitados.
    """
    return jwt.decode(
        token, APP_SECRET, algorithms=[_ALGORITHM], audience=expected_audience,
        options={"require": ["exp", "aud", "sub"]},
    )


# ── Token Blacklist (Redis) ──────────────────────────────────────────────────

import hashlib as _hashlib


def _token_blacklist_key(token: str) -> str:
    """Chave Redis para blacklist — hash do token para não armazenar o JWT inteiro."""
    return f"token_blacklist:{_hashlib.sha256(token.encode()).hexdigest()}"


async def blacklist_token(token: str) -> None:
    """Adiciona token à blacklist com TTL baseado na expiração do token."""
    from app.core.redis import get_redis_pool

    try:
        # Blacklist e agnostica a audience — aceita qualquer token valido
        # para calcular TTL pelo claim exp.
        claims = jwt.decode(
            token, APP_SECRET, algorithms=[_ALGORITHM],
            audience=[AUDIENCE_ACCESS, AUDIENCE_REFRESH],
            options={"verify_exp": False},
        )
        exp = claims.get("exp", 0)
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 60)
    except jwt.PyJWTError:
        ttl = _ACCESS_EXPIRE_MINUTES * 60

    r = get_redis_pool()
    await r.setex(_token_blacklist_key(token), ttl, "1")


async def is_token_blacklisted(token: str) -> bool:
    """Verifica se token está na blacklist.

    Fail-CLOSED: se o Redis estiver indisponível (rede, timeout, erro), levanta
    HTTP 503 em vez de retornar `False`. O comportamento anterior aceitava
    qualquer token quando o backing store estava down — tokens revogados via
    logout permaneciam válidos até a expiração natural, anulando o logout.

    Fail-closed escolhe disponibilidade ↓ vs segurança ↑ — preferimos recusar
    acessos legítimos por alguns minutos (até Redis voltar) do que aceitar
    tokens potencialmente comprometidos.
    """
    from app.core.redis import get_redis_pool

    try:
        r = get_redis_pool()
        return await r.exists(_token_blacklist_key(token)) > 0
    except Exception as exc:
        _logger.error(
            "is_token_blacklisted: backing store de blacklist indisponível — "
            "rejeitando autenticação (fail-closed): %s",
            exc,
        )
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação temporariamente indisponível. Tente novamente em instantes.",
        ) from exc


# ── Rotação de refresh token (Redis) ───────────────────────────────────────────

# Script Lua para rotação atômica (compare-and-swap) — evita corrida TOCTOU entre
# requisições de refresh concorrentes que poderiam gerar jtis divergentes.
#   KEYS[1] = chave da família   KEYS[2] = chave do jti anterior (grace)
#   ARGV[1] = jti recebido       ARGV[2] = novo jti candidato
#   ARGV[3] = TTL da família      ARGV[4] = TTL da janela de graça
# Retorna: "NOFAMILY" | "REUSE" | <jti a embutir no novo refresh>
_ROTATE_LUA = """
local current = redis.call('GET', KEYS[1])
if not current then
  return 'NOFAMILY'
end
if ARGV[1] == current then
  redis.call('SETEX', KEYS[2], ARGV[4], current)
  redis.call('SETEX', KEYS[1], ARGV[3], ARGV[2])
  return ARGV[2]
end
local prev = redis.call('GET', KEYS[2])
if prev and ARGV[1] == prev then
  return current
end
redis.call('DEL', KEYS[1], KEYS[2])
return 'REUSE'
"""


def new_refresh_family() -> tuple[str, str]:
    """Gera (family_id, jti) para um novo login."""
    return str(uuid4()), str(uuid4())


async def register_refresh_family(family: str, jti: str) -> None:
    """Registra o jti inicial de uma família de refresh tokens (no login)."""
    from app.core.redis import get_redis_pool

    r = get_redis_pool()
    await r.setex(f"{_REFRESH_FAMILY_PREFIX}{family}", _REFRESH_FAMILY_TTL, jti)


async def rotate_refresh_family(family: str, jti: str) -> tuple[str, str | None]:
    """Valida e rotaciona o refresh token da família.

    Retorna (status, jti_para_novo_token):
      - ("ok", novo_jti)   → rotação válida; embuta novo_jti no refresh emitido
      - ("invalid", None)  → família inexistente/expirada
      - ("reuse", None)    → jti já rotacionado reapareceu (roubo) → família revogada
    """
    from app.core.redis import get_redis_pool

    r = get_redis_pool()
    res = await r.eval(
        _ROTATE_LUA, 2,
        f"{_REFRESH_FAMILY_PREFIX}{family}",
        f"{_REFRESH_PREV_PREFIX}{family}",
        jti, str(uuid4()), str(_REFRESH_FAMILY_TTL), str(_REFRESH_GRACE_SECONDS),
    )
    if isinstance(res, (bytes, bytearray)):
        res = res.decode()
    if res == "NOFAMILY":
        return "invalid", None
    if res == "REUSE":
        return "reuse", None
    return "ok", res


async def revoke_refresh_family(family: str) -> None:
    """Revoga a sessão inteira (no logout) removendo a família e seu grace."""
    from app.core.redis import get_redis_pool

    r = get_redis_pool()
    await r.delete(f"{_REFRESH_FAMILY_PREFIX}{family}", f"{_REFRESH_PREV_PREFIX}{family}")


# ── Rate limit de refresh por FAMÍLIA (não por IP) ─────────────────────────────
# O /auth/refresh não pode ser limitado por IP: o Next.js renova server→server,
# então todos os usuários chegam com o MESMO IP (o do pod web) e dividiriam um
# balde único de plataforma — estourar esse balde devolvia 429, que o front
# tratava como "refresh expirado" e deslogava todo mundo. O token de refresh é
# assinado e já protegido por rotação + detecção de reuso, então a dimensão certa
# de limite é a SESSÃO (família), não o IP: cada família tem seu próprio balde.
_REFRESH_RATE_PREFIX = "refresh_rate:"
# Generoso de propósito: uma sessão saudável renova ~1×/30min; o teto só existe
# para conter um cliente em loop (ex.: uma aba re-tentando após falha transitória).
_REFRESH_RATE_LIMIT  = 30
_REFRESH_RATE_WINDOW = 60


async def refresh_rate_exceeded(family: str) -> bool:
    """True se esta família já passou do teto de refreshes na janela.

    Contador Redis de janela fixa (`contar_na_janela`: o prazo nasce na
    primeira contagem e não anda). Keyed por família — imune ao problema do IP
    único do hop interno.
    """
    from app.core.redis import contar_na_janela

    count, _ = await contar_na_janela(f"{_REFRESH_RATE_PREFIX}{family}", _REFRESH_RATE_WINDOW)
    return count > _REFRESH_RATE_LIMIT
