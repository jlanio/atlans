# app/core/authorization/pat.py
"""
Personal access token (PAT) — constants and pure primitives.

A PAT is what an agent (Claude Code, Cursor, a script) uses to talk to
Atlans on behalf of a user, without a browser session. This module knows neither
FastAPI nor the database: it only defines the secret's format, the possible scopes and how
the secret becomes the hash stored in the database.

Secret format: ``atl_pat_`` + 43 url-safe characters (32 random bytes,
256 bits of entropy — the same `secrets.token_urlsafe(32)` as the enrollment OTP).
The database stores only the SHA-256 of the secret (hex, 64 chars) and a short prefix
so the user can recognize the token on screen. With 256 bits of entropy an unsalted
hash is enough: a database dump does not allow recovering the secret.
"""
from __future__ import annotations

import hashlib
import re
import secrets

PREFIXO = "atl_pat_"

# Order is the display order on screen. Effective = scope ∩ the user's role in the
# workspace (write requires editor; execute/triggers require operator) — the
# intersection is applied by whoever consumes the token (Phase 1), not here.
ESCOPOS: tuple[str, ...] = (
    "workflows:read",
    "workflows:write",
    "runs:execute",
    "triggers:manage",
    "drive:read",
    "drive:write",
)

VALIDADE_PADRAO_DIAS = 90
VALIDADE_MAX_DIAS = 365
MAX_TOKENS_ATIVOS_POR_USUARIO = 20
TAMANHO_PREFIXO_EXIBIVEL = 12  # "atl_pat_" + 4 chars — enough to recognize, useless for guessing

# 43 = len(base64url(32 bytes)) sem o padding.
REGEX_SEGREDO = re.compile(r"atl_pat_[A-Za-z0-9_-]{43}")


def gerar_segredo() -> str:
    """New secret: prefix + 43 url-safe chars. Exists only in memory and in the creation response."""
    return PREFIXO + secrets.token_urlsafe(32)


def hash_segredo(segredo: str) -> str:
    """SHA-256 hex of the secret — this is what goes in the `token_hash` column."""
    return hashlib.sha256(segredo.encode("utf-8")).hexdigest()


def prefixo_exibivel(segredo: str) -> str:
    """The first 12 characters, for the screen to show `atl_pat_Ab3d…`."""
    return segredo[:TAMANHO_PREFIXO_EXIBIVEL]


def e_segredo_pat(valor: str | None) -> bool:
    """True if the value has exactly the format of a PAT (without querying the database)."""
    return bool(valor) and REGEX_SEGREDO.fullmatch(valor) is not None


def escopos_invalidos(escopos: list[str]) -> list[str]:
    """The scopes that do not exist, in the order they appeared."""
    return [e for e in escopos if e not in ESCOPOS]


def status_de(revoked_at, expires_at, agora) -> str:
    """"revoked" | "expired" | "active" — revocation takes precedence over expiry."""
    if revoked_at is not None:
        return "revoked"
    if expires_at is not None and expires_at <= agora:
        return "expired"
    return "active"
