# app/core/utils/jwt_utils.py
"""
JWT utilities — creation and validation of access and refresh tokens — and
password hashing.

The password hash is the `bcrypt_sha256` that passlib defined, reproduced here
on top of `bcrypt` directly (passlib is gone: unmaintained since 2020, it broke
with bcrypt 4.1+ and carried a compound license into the third-party notice).
The format stored in the database is the same, so every existing hash remains
valid and a new hash is still read by the previous version of the code:

    $bcrypt-sha256$v=2,t=2b,r=12$<22-char salt>$<31-char digest>

The pre-key is the HMAC-SHA256 of the password keyed with the salt, in base64
(44 bytes): it is what removes bcrypt's 72-byte limit and what prevents the
prefix trick. Hashes from version 1 of the scheme (plain SHA-256, format
`$bcrypt-sha256$2b,12$…`) also verify, in case any exist.
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
# Audience per context: prevents a token issued for one purpose from being
# used for another (e.g., a refresh_token presented as an access_token to
# a vulnerable endpoint). Each decoder requires its specific audience.
AUDIENCE_ACCESS  = "atlas-studio:access"
AUDIENCE_REFRESH = "atlas-studio:refresh"

# ── Refresh token rotation ────────────────────────────────────────────────────
# Each login opens a "family" of refresh tokens. Redis stores which jti is the
# family's currently valid one; on each refresh the jti rotates. If an old jti
# (already rotated) reappears, it is a sign of theft → we revoke the whole family.
_REFRESH_FAMILY_PREFIX = "refresh_family:"
_REFRESH_PREV_PREFIX   = "refresh_prev:"
_REFRESH_FAMILY_TTL    = _REFRESH_EXPIRE_DAYS * 24 * 60 * 60
# Grace window: tolerates the immediately previous jti for a few seconds so the
# session is not dropped when the client fires concurrent refreshes
# (e.g., NextAuth's jwt callback on parallel requests).
_REFRESH_GRACE_SECONDS = 30

# ── Password hash (bcrypt_sha256, version 2) ────────────────────────────────
_ROUNDS = 12
_HASH = re.compile(
    r"^\$bcrypt-sha256\$"
    r"(?:v=(?P<versao>\d+),t=(?P<tipo>2[ab]),r=(?P<rounds>\d{1,2})"   # version 2
    r"|(?P<tipo1>2[ab]),(?P<rounds1>\d{1,2}))"                         # version 1
    r"\$(?P<salt>[./A-Za-z0-9]{22})\$(?P<digest>[./A-Za-z0-9]{31})$"
)


def _pre_key(plain: str, salt: str, versao: int) -> bytes:
    """The password as bcrypt receives it: HMAC-SHA256 with the salt (v2) or plain
    SHA-256 (v1), in base64 — 44 bytes, within bcrypt's 72-byte limit."""
    senha = plain.encode("utf-8")
    if versao >= 2:
        digest = hmac.new(salt.encode("ascii"), senha, hashlib.sha256).digest()
    else:
        digest = hashlib.sha256(senha).digest()
    return base64.b64encode(digest)


def hash_password(plain: str) -> str:
    """A new `bcrypt_sha256` v2 hash, with its own salt."""
    config = bcrypt.gensalt(rounds=_ROUNDS, prefix=b"2b")          # b"$2b$12$<salt>"
    salt = config[-22:].decode("ascii")
    completo = bcrypt.hashpw(_pre_key(plain, salt, 2), config).decode("ascii")
    return f"$bcrypt-sha256$v=2,t=2b,r={_ROUNDS}${salt}${completo[-31:]}"


def verify_password(plain: str, hashed: str) -> bool:
    """Does the password match the hash? A malformed (or empty) hash is just
    false — never an exception at login."""
    partes = _HASH.match(hashed or "")
    if not partes or not isinstance(plain, str):
        return False
    versao = int(partes["versao"]) if partes["versao"] else 1
    tipo = partes["tipo"] or partes["tipo1"]
    rounds = int(partes["rounds"] or partes["rounds1"])
    config = f"${tipo}${rounds:02d}${partes['salt']}".encode("ascii")
    try:
        calculado = bcrypt.hashpw(_pre_key(plain, partes["salt"], versao), config)
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
    """Decodes and validates the token, requiring a specific audience.

    expected_audience: pass AUDIENCE_ACCESS or AUDIENCE_REFRESH according to
    the use. Tokens with a different audience are rejected.
    """
    return jwt.decode(
        token, APP_SECRET, algorithms=[_ALGORITHM], audience=expected_audience,
        options={"require": ["exp", "aud", "sub"]},
    )


# ── Token Blacklist (Redis) ──────────────────────────────────────────────────

import hashlib as _hashlib


def _token_blacklist_key(token: str) -> str:
    """Redis key for the blacklist — a hash of the token so the whole JWT is not stored."""
    return f"token_blacklist:{_hashlib.sha256(token.encode()).hexdigest()}"


async def blacklist_token(token: str) -> None:
    """Adds the token to the blacklist with a TTL based on the token's expiration."""
    from app.core.redis import get_redis_pool

    try:
        # The blacklist is audience-agnostic — accepts any valid token
        # to compute the TTL from the exp claim.
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
    """Checks whether the token is on the blacklist.

    Fail-CLOSED: if Redis is unavailable (network, timeout, error), raises
    HTTP 503 instead of returning `False`. The previous behavior accepted
    any token when the backing store was down — tokens revoked via logout
    remained valid until their natural expiration, defeating the logout.

    Fail-closed trades availability ↓ for security ↑ — we prefer refusing
    legitimate access for a few minutes (until Redis comes back) over
    accepting potentially compromised tokens.
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


# ── Refresh token rotation (Redis) ─────────────────────────────────────────────

# Lua script for atomic rotation (compare-and-swap) — avoids a TOCTOU race between
# concurrent refresh requests that could produce divergent jtis.
#   KEYS[1] = family key         KEYS[2] = previous jti key (grace)
#   ARGV[1] = received jti       ARGV[2] = new candidate jti
#   ARGV[3] = family TTL          ARGV[4] = grace window TTL
# Returns: "NOFAMILY" | "REUSE" | <jti to embed in the new refresh>
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
    """Registers the initial jti of a refresh token family (at login)."""
    from app.core.redis import get_redis_pool

    r = get_redis_pool()
    await r.setex(f"{_REFRESH_FAMILY_PREFIX}{family}", _REFRESH_FAMILY_TTL, jti)


async def rotate_refresh_family(family: str, jti: str) -> tuple[str, str | None]:
    """Validates and rotates the family's refresh token.

    Returns (status, jti_para_novo_token):
      - ("ok", novo_jti)   → valid rotation; embed novo_jti in the issued refresh
      - ("invalid", None)  → family nonexistent/expired
      - ("reuse", None)    → an already-rotated jti reappeared (theft) → family revoked
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
    """Revokes the whole session (at logout) by removing the family and its grace."""
    from app.core.redis import get_redis_pool

    r = get_redis_pool()
    await r.delete(f"{_REFRESH_FAMILY_PREFIX}{family}", f"{_REFRESH_PREV_PREFIX}{family}")


# ── Refresh rate limit per FAMILY (not per IP) ─────────────────────────────────
# /auth/refresh cannot be limited per IP: Next.js renews server→server, so all
# users arrive with the SAME IP (the web pod's) and would share a single
# platform bucket — overflowing that bucket returned 429, which the frontend
# treated as "refresh expired" and logged everyone out. The refresh token is
# signed and already protected by rotation + reuse detection, so the right
# dimension for the limit is the SESSION (family), not the IP: each family has
# its own bucket.
_REFRESH_RATE_PREFIX = "refresh_rate:"
# Generous on purpose: a healthy session renews ~1×/30min; the ceiling only exists
# to contain a client in a loop (e.g., a tab retrying after a transient failure).
_REFRESH_RATE_LIMIT  = 30
_REFRESH_RATE_WINDOW = 60


async def refresh_rate_exceeded(family: str) -> bool:
    """True if this family has already exceeded the refresh ceiling in the window.

    Fixed-window Redis counter (`count_in_window`: the deadline starts at the
    first count and does not move). Keyed by family — immune to the single-IP
    problem of the internal hop.
    """
    from app.core.redis import count_in_window

    count, _ = await count_in_window(f"{_REFRESH_RATE_PREFIX}{family}", _REFRESH_RATE_WINDOW)
    return count > _REFRESH_RATE_LIMIT
