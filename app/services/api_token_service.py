# app/services/api_token_service.py
"""
Tokens pessoais de acesso (PAT): criação, listagem, revogação e resolução.

Regras de segurança concentradas aqui (ver app/models/api_token.py):
- O segredo só existe no retorno de `criar`; no banco fica o SHA-256.
- `resolver` é o ÚNICO caminho de autenticação por PAT (usado pelo servidor
  MCP): hash → linha → não revogado → não expirado → usuário ativo.
- Revogação nunca apaga; a cascata (reset de senha, suspensão, exclusão)
  roda na sessão do chamador e NÃO commita — quem abriu a transação fecha.
- `marcar_uso` é best-effort com throttle no Redis: nunca falha uma request,
  e COMMITA por padrão — a sessão de request (`get_session_async`) faz
  rollback no `finally`, então um carimbo sem commit se perderia em silêncio.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from fastapi import status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization.pat import (
    MAX_TOKENS_ATIVOS_POR_USUARIO,
    VALIDADE_MAX_DIAS,
    VALIDADE_PADRAO_DIAS,
    e_segredo_pat,
    escopos_invalidos,
    gerar_segredo,
    hash_segredo,
    prefixo_exibivel,
)
from app.core.exceptions import AtlasBaseError
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.api_token import ApiToken
from app.models.user import User

logger = get_logger(__name__)

THROTTLE_ULTIMO_USO_SEGUNDOS = 60


class ApiTokenError(AtlasBaseError):
    """Entrada inválida ao criar um token (escopo, workspace, validade, nome)."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "api_token_invalid"


class ApiTokenLimitError(AtlasBaseError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "api_token_limit"


class ApiTokenNotFoundError(AtlasBaseError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "api_token_not_found"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _normalizar_escopos(scopes: Iterable[str] | None) -> list[str]:
    unicos = list(dict.fromkeys(s.strip() for s in (scopes or []) if s and s.strip()))
    if not unicos:
        raise ApiTokenError("Informe ao menos um escopo.")
    invalidos = escopos_invalidos(unicos)
    if invalidos:
        raise ApiTokenError(f"Escopo desconhecido: {', '.join(invalidos)}.")
    return unicos


async def _contar_ativos(db: AsyncSession, user_id: str, agora) -> int:
    resultado = await db.execute(
        select(func.count(ApiToken.id)).where(
            ApiToken.user_id == user_id,
            ApiToken.revoked_at.is_(None),
            ApiToken.expires_at > agora,
        )
    )
    return int(resultado.scalar_one() or 0)


# ── Ciclo de vida ─────────────────────────────────────────────────────────────


async def criar(
    db: AsyncSession,
    user,
    *,
    name: str,
    scopes: Iterable[str],
    workspace_ids: Iterable[str] | None = None,
    expires_in_days: int = VALIDADE_PADRAO_DIAS,
) -> tuple[ApiToken, str]:
    """Cria um token e devolve (linha persistida, segredo em texto claro).

    O segredo NÃO é guardado nem logado. `workspace_ids` precisa ser um
    subconjunto dos workspaces do usuário (dono ou membro); `None` = todos,
    inclusive os futuros.
    """
    nome = (name or "").strip()
    if not nome or len(nome) > 80:
        raise ApiTokenError("O nome precisa ter entre 1 e 80 caracteres.")
    escopos = _normalizar_escopos(scopes)
    if not isinstance(expires_in_days, int) or not 1 <= expires_in_days <= VALIDADE_MAX_DIAS:
        raise ApiTokenError(f"A validade precisa ficar entre 1 e {VALIDADE_MAX_DIAS} dias.")

    alcance: list[str] | None = None
    if workspace_ids is not None:
        alcance = list(dict.fromkeys(w.strip() for w in workspace_ids if w and w.strip()))
        if not alcance:
            raise ApiTokenError("Informe ao menos um workspace, ou deixe em branco para todos.")
        # A dependency aceita os argumentos posicionais fora do FastAPI — é a
        # MESMA query (dono OU membro, sem workspaces na lixeira) que autoriza a
        # REST. Import tardio: app.api.dependencies importa services.
        from app.api.dependencies import get_user_workspace_ids

        permitidos = set(await get_user_workspace_ids(db, user))
        fora = [w for w in alcance if w not in permitidos]
        if fora:
            raise ApiTokenError("Você não participa de todos os workspaces informados.")

    agora = utc_now_naive()
    # O teto é conforto, não segurança: dois POSTs simultâneos podem terminar
    # em 21. Um SELECT ... FOR UPDATE na linha do usuário fecharia a fresta ao
    # custo de serializar toda criação de token por conta — não vale por um
    # limite que só existe para a lista não virar bagunça.
    if await _contar_ativos(db, user.id_hash, agora) >= MAX_TOKENS_ATIVOS_POR_USUARIO:
        raise ApiTokenLimitError(
            f"Limite de {MAX_TOKENS_ATIVOS_POR_USUARIO} tokens ativos atingido. "
            "Revogue um token antes de criar outro."
        )

    segredo = gerar_segredo()
    token = ApiToken(
        user_id=user.id_hash,
        name=nome,
        token_prefix=prefixo_exibivel(segredo),
        token_hash=hash_segredo(segredo),
        scopes=escopos,
        workspace_ids=alcance,
        expires_at=agora + timedelta(days=expires_in_days),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    # id_hash + prefixo no log, nunca o nome: é texto livre e uma quebra de
    # linha nele forjaria um registro inteiro.
    logger.info(
        "Token de acesso %s (%s) criado por '%s': escopos=%s workspaces=%s expira=%s",
        token.id_hash, token.token_prefix, user.id_hash, ",".join(escopos),
        "todos" if alcance is None else len(alcance), token.expires_at.isoformat(),
    )
    return token, segredo


async def listar(db: AsyncSession, user_id: str) -> list[ApiToken]:
    """Todos os tokens do usuário (ativos, expirados e revogados), mais recentes primeiro."""
    resultado = await db.execute(
        select(ApiToken)
        .where(ApiToken.user_id == user_id)
        .order_by(ApiToken.created_at.desc(), ApiToken.id.desc())
    )
    return list(resultado.scalars().all())


async def revogar(db: AsyncSession, user_id: str, id_hash: str, motivo: str = "user") -> ApiToken:
    """Revoga um token do próprio usuário. Idempotente; 404 se não é dele."""
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


async def revogar_todos_do_usuario(db: AsyncSession, user_ids: Iterable[str] | str, motivo: str) -> int:
    """Cascata: revoga todo token ativo dos usuários — UM UPDATE, SEM commit.

    Chamado dentro da transação de quem muda o estado da conta (reset de
    senha, suspensão, exclusão); é o chamador que commita. Devolve quantas
    linhas foram revogadas quando o driver informa. Aceita um `id_hash` só
    (string) ou vários — uma string iterada como letras não revogaria nada.
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
    afetadas = getattr(resultado, "rowcount", None)
    n = afetadas if isinstance(afetadas, int) and afetadas >= 0 else 0
    if n:
        logger.info("%d token(s) de acesso revogado(s) em cascata (%s) para %s.", n, motivo, ", ".join(ids))
    return n


# ── Autenticação ──────────────────────────────────────────────────────────────


async def resolver(db: AsyncSession, segredo: str | None) -> tuple[ApiToken, User] | None:
    """Do segredo ao (token, usuário) — ou None, sem dizer por quê.

    Uma query: hash → token não revogado e não expirado → usuário com
    `status == "active"` (a coluna; `User.is_active` é property e não serve no SQL).
    """
    if not e_segredo_pat(segredo):
        return None
    agora = utc_now_naive()
    resultado = await db.execute(
        select(ApiToken, User)
        .join(User, User.id_hash == ApiToken.user_id)
        .where(
            ApiToken.token_hash == hash_segredo(segredo),
            ApiToken.revoked_at.is_(None),
            ApiToken.expires_at > agora,
            User.status == "active",
        )
    )
    linha = resultado.first()
    if linha is None:
        return None
    return linha[0], linha[1]


async def marcar_uso(db: AsyncSession, redis, token: ApiToken, *, commit: bool = True) -> bool:
    """Carimba `last_used_at` no máximo uma vez por minuto — best-effort.

    O throttle é um `SET NX EX 60` no Redis: quem ganha o lock escreve; os
    demais nem tocam no banco. Redis indisponível = não marca. O UPDATE roda
    num SAVEPOINT para não envenenar a transação do chamador (molde de
    `credential_loader._marcar_last_used`) e é COMMITADO aqui mesmo: a sessão
    de request faz rollback no `finally`, e um carimbo pendente sumiria sem
    ninguém notar. `commit=False` só para quem já está dentro de uma transação
    própria e vai commitá-la. Se o UPDATE falha, o lock do Redis é devolvido
    para a próxima request tentar de novo — senão o minuto ficaria queimado
    sem carimbo. Nunca levanta.
    """
    chave = f"pat:lu:{token.id_hash}"
    try:
        ganhou = await redis.set(chave, "1", nx=True, ex=THROTTLE_ULTIMO_USO_SEGUNDOS)
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.debug("Throttle de last_used_at indisponível: %s", exc)
        return False
    if not ganhou:
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
