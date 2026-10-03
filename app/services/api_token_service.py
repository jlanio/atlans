# app/services/api_token_service.py
"""
Personal access tokens (PAT): creation, listing, revocation and resolution.

Security rules concentrated here (see app/models/api_token.py):
- The secret only exists in the return value of `criar`; the database keeps the SHA-256.
- `resolver` is the ONLY PAT authentication path (used by the MCP
  server): hash → row → not revoked → not expired → active user.
- Revocation never deletes; the cascade (password reset, suspension, deletion)
  runs in the caller's session and does NOT commit — whoever opened the
  transaction closes it.
- `mark_used` is best-effort with a throttle in Redis: it never fails a
  request, and it COMMITS by default — the request session
  (`get_session_async`) rolls back in the `finally`, so an uncommitted stamp
  would be silently lost.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from fastapi import status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization.pat import (
    MAX_ACTIVE_TOKENS_PER_USER,
    MAX_VALIDITY_DAYS,
    DEFAULT_VALIDITY_DAYS,
    is_pat_secret,
    invalid_scopes,
    generate_secret,
    hash_secret,
    displayable_prefix,
)
from app.core.exceptions import AtlasBaseError
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.api_token import ApiToken
from app.models.user import User

logger = get_logger(__name__)

LAST_USED_THROTTLE_SECONDS = 60


class ApiTokenError(AtlasBaseError):
    """Invalid input when creating a token (scope, workspace, validity, name)."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "api_token_invalid"


class ApiTokenLimitError(AtlasBaseError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "api_token_limit"


class ApiTokenNotFoundError(AtlasBaseError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "api_token_not_found"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _normalize_scopes(scopes: Iterable[str] | None) -> list[str]:
    unicos = list(dict.fromkeys(s.strip() for s in (scopes or []) if s and s.strip()))
    if not unicos:
        raise ApiTokenError("Informe ao menos um escopo.")
    invalidos = invalid_scopes(unicos)
    if invalidos:
        raise ApiTokenError(f"Escopo desconhecido: {', '.join(invalidos)}.")
    return unicos


async def _count_active(db: AsyncSession, user_id: str, agora) -> int:
    resultado = await db.execute(
        select(func.count(ApiToken.id)).where(
            ApiToken.user_id == user_id,
            ApiToken.revoked_at.is_(None),
            ApiToken.expires_at > agora,
        )
    )
    return int(resultado.scalar_one() or 0)


# ── Lifecycle ─────────────────────────────────────────────────────────────────


async def criar(
    db: AsyncSession,
    user,
    *,
    name: str,
    scopes: Iterable[str],
    workspace_ids: Iterable[str] | None = None,
    expires_in_days: int = DEFAULT_VALIDITY_DAYS,
) -> tuple[ApiToken, str]:
    """Creates a token and returns (persisted row, plaintext secret).

    The secret is NOT stored or logged. `workspace_ids` must be a subset of
    the user's workspaces (owner or member); `None` = all of them, including
    future ones.
    """
    nome = (name or "").strip()
    if not nome or len(nome) > 80:
        raise ApiTokenError("O nome precisa ter entre 1 e 80 caracteres.")
    escopos = _normalize_scopes(scopes)
    if not isinstance(expires_in_days, int) or not 1 <= expires_in_days <= MAX_VALIDITY_DAYS:
        raise ApiTokenError(f"A validade precisa ficar entre 1 e {MAX_VALIDITY_DAYS} dias.")

    alcance: list[str] | None = None
    if workspace_ids is not None:
        alcance = list(dict.fromkeys(w.strip() for w in workspace_ids if w and w.strip()))
        if not alcance:
            raise ApiTokenError("Informe ao menos um workspace, ou deixe em branco para todos.")
        # The dependency accepts positional arguments outside FastAPI — it is the
        # SAME query (owner OR member, no workspaces in the trash) that
        # authorizes REST. Late import: app.api.dependencies imports services.
        from app.api.dependencies import get_user_workspace_ids

        permitidos = set(await get_user_workspace_ids(db, user))
        fora = [w for w in alcance if w not in permitidos]
        if fora:
            raise ApiTokenError("Você não participa de todos os workspaces informados.")

    agora = utc_now_naive()
    # The ceiling is a convenience, not security: two simultaneous POSTs can end
    # up at 21. A SELECT ... FOR UPDATE on the user's row would close the gap
    # at the cost of serializing every token creation per account — not worth
    # it for a limit that only exists so the list does not become a mess.
    if await _count_active(db, user.id_hash, agora) >= MAX_ACTIVE_TOKENS_PER_USER:
        raise ApiTokenLimitError(
            f"Limite de {MAX_ACTIVE_TOKENS_PER_USER} tokens ativos atingido. "
            "Revogue um token antes de criar outro."
        )

    segredo = generate_secret()
    token = ApiToken(
        user_id=user.id_hash,
        name=nome,
        token_prefix=displayable_prefix(segredo),
        token_hash=hash_secret(segredo),
        scopes=escopos,
        workspace_ids=alcance,
        expires_at=agora + timedelta(days=expires_in_days),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    # id_hash + prefix in the log, never the name: it is free text and a line
    # break in it would forge a whole log entry.
    logger.info(
        "Token de acesso %s (%s) criado por '%s': escopos=%s workspaces=%s expira=%s",
        token.id_hash, token.token_prefix, user.id_hash, ",".join(escopos),
        "todos" if alcance is None else len(alcance), token.expires_at.isoformat(),
    )
    return token, segredo


async def listar(db: AsyncSession, user_id: str) -> list[ApiToken]:
    """All of the user's tokens (active, expired and revoked), most recent first."""
    resultado = await db.execute(
        select(ApiToken)
        .where(ApiToken.user_id == user_id)
        .order_by(ApiToken.created_at.desc(), ApiToken.id.desc())
    )
    return list(resultado.scalars().all())


async def revogar(db: AsyncSession, user_id: str, id_hash: str, motivo: str = "user") -> ApiToken:
    """Revokes one of the user's own tokens. Idempotent; 404 if it is not theirs."""
    resultado = await db.execute(
        select(ApiToken).where(ApiToken.id_hash == id_hash, ApiToken.user_id == user_id)
    )
    token = resultado.scalar_one_or_none()
    if token is None:
        raise ApiTokenNotFoundError("Token não encontrado.")
    if token.revoked_at is None:
        token.revoked_at = utc_now_naive()
        token.revoked_reason = motivo
        await db.commit()
        await db.refresh(token)
        logger.info("Token de acesso %s (%s) revogado por '%s'.", token.id_hash, token.token_prefix, user_id)
    return token


async def revoke_all_for_user(db: AsyncSession, user_ids: Iterable[str] | str, motivo: str) -> int:
    """Cascade: revokes every active token of the users — ONE UPDATE, NO commit.

    Called inside the transaction of whoever changes the account's state
    (password reset, suspension, deletion); the caller is the one who commits.
    Returns how many rows were revoked when the driver reports it. Accepts a
    single `id_hash` (string) or several — a string iterated as letters would
    revoke nothing.
    """
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    ids = [u for u in dict.fromkeys(user_ids) if u]
    if not ids:
        return 0
    resultado = await db.execute(
        update(ApiToken)
        .where(ApiToken.user_id.in_(ids), ApiToken.revoked_at.is_(None))
        .values(revoked_at=utc_now_naive(), revoked_reason=motivo)
    )
    affected = getattr(resultado, "rowcount", None)
    n = affected if isinstance(affected, int) and affected >= 0 else 0
    if n:
        logger.info("%d token(s) de acesso revogado(s) em cascata (%s) para %s.", n, motivo, ", ".join(ids))
    return n


# ── Authentication ────────────────────────────────────────────────────────────


async def resolver(db: AsyncSession, segredo: str | None) -> tuple[ApiToken, User] | None:
    """From the secret to (token, user) — or None, without saying why.

    One query: hash → token not revoked and not expired → user with
    `status == "active"` (the column; `User.is_active` is a property and does not work in SQL).
    """
    if not is_pat_secret(segredo):
        return None
    agora = utc_now_naive()
    resultado = await db.execute(
        select(ApiToken, User)
        .join(User, User.id_hash == ApiToken.user_id)
        .where(
            ApiToken.token_hash == hash_secret(segredo),
            ApiToken.revoked_at.is_(None),
            ApiToken.expires_at > agora,
            User.status == "active",
        )
    )
    linha = resultado.first()
    if linha is None:
        return None
    return linha[0], linha[1]


async def mark_used(db: AsyncSession, redis, token: ApiToken, *, commit: bool = True) -> bool:
    """Stamps `last_used_at` at most once per minute — best-effort.

    The throttle is a `SET NX EX 60` in Redis: whoever wins the lock writes;
    the others do not even touch the database. Redis unavailable = no stamp.
    The UPDATE runs in a SAVEPOINT so as not to poison the caller's
    transaction (modeled on `credential_loader._mark_last_used`) and is
    COMMITTED right here: the request session rolls back in the `finally`,
    and a pending stamp would vanish without anyone noticing. `commit=False`
    only for those already inside their own transaction who will commit it.
    If the UPDATE fails, the Redis lock is released for the next request to
    try again — otherwise the minute would be burned without a stamp. Never
    raises.
    """
    chave = f"pat:lu:{token.id_hash}"
    try:
        won = await redis.set(chave, "1", nx=True, ex=LAST_USED_THROTTLE_SECONDS)
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.debug("Throttle de last_used_at indisponível: %s", exc)
        return False
    if not won:
        return False
    try:
        async with db.begin_nested():
            await db.execute(
                update(ApiToken)
                .where(ApiToken.id_hash == token.id_hash)
                .values(last_used_at=utc_now_naive())
            )
        if commit:
            await db.commit()
        return True
    except Exception as exc:
        logger.warning("Falha ao carimbar last_used_at do token %s: %s", token.token_prefix, exc)
        try:
            await redis.delete(chave)
        except Exception:  # pragma: no cover - best-effort
            pass
        return False
