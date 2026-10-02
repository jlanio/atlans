# app/services/observability/frota.py
# Lógica de negócio e consultas de observabilidade extraídas do router.
# Contrato com a web: docs/specs/metrics-history.md (§3).

import asyncio
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.logger import get_logger
from app.models.executor import Executor
from app.models.user import User
from app.models.workspace import Workspace

logger = get_logger(__name__)


# ── Executores (frota, presenca, capacidade) ─────────────────────────────────

def _executor_id_do_host(host: Optional[str]) -> Optional[str]:
    if host and host.startswith("executor:"):
        return host[len("executor:"):]
    return None


async def _executores_do_escopo(db: AsyncSession, user, *, como_admin: bool = False) -> list[dict]:
    """Frota que o usuario enxerga (spec §3.1): com `como_admin`, todos os
    ativos; senao, os acessiveis por `get_user_accessible_agents` (pool padrao
    + workspaces dele + atribuidos), tambem so os ativos — um executor inativo
    na conta "a de b online" faria a frota parecer maior do que e."""
    if como_admin:
        result = await db.execute(
            select(
                Executor.id_hash, Executor.name, Executor.executor_type,
                Executor.is_default, Executor.status,
            ).where(Executor.status == "active", Executor.deleted_at.is_(None))
        )
        return [
            {
                "id_hash": r.id_hash, "name": r.name, "executor_type": r.executor_type,
                "is_default": bool(r.is_default), "status": r.status,
            }
            for r in result.all()
        ]

    from app.services.user_executor_service import get_user_accessible_agents

    acessiveis = await get_user_accessible_agents(db, user.id_hash)
    return [
        {
            "id_hash": a["id_hash"], "name": a["name"], "executor_type": a.get("executor_type"),
            "is_default": bool(a.get("is_default")), "status": a.get("status"),
        }
        for a in acessiveis
        if a.get("status") == "active"
    ]


def _normalizar_capacidade(cap) -> Optional[dict]:
    """So os quatro campos do contrato; o executor pode publicar mais coisa."""
    if not isinstance(cap, dict):
        return None
    saida = {}
    for campo in ("running", "queued", "max_concurrent", "max_queue"):
        valor = cap.get(campo)
        saida[campo] = int(valor) if isinstance(valor, (int, float)) else None
    return saida


async def _presenca(executor_ids: Iterable[str]) -> tuple[dict[str, bool], dict[str, Optional[dict]]]:
    """Online (presenca no Redis) e capacidade publicada, por executor. Um
    Redis fora do ar vira "offline, sem capacidade" — nunca derruba a tela."""
    from app.core.executor_connections import executor_registry

    ids = list(executor_ids)

    # Uma ida ao Redis por executor, em paralelo — antes eram 2N idas em série
    # (presenca e depois capacidade, um executor de cada vez). Cada corrotina
    # engole a própria exceção e devolve o fallback, então o gather nunca levanta:
    # um Redis instável continua virando "offline, sem capacidade", nunca derruba
    # a tela.
    async def _online(eid: str) -> bool:
        try:
            return bool(await executor_registry.is_online(eid))
        except Exception as exc:
            logger.debug("Presenca do executor '%s' indisponivel: %s", eid, exc)
            return False

    online_vals = await asyncio.gather(*(_online(eid) for eid in ids))
    online: dict[str, bool] = dict(zip(ids, online_vals))

    async def _cap(eid: str) -> Optional[dict]:
        try:
            return _normalizar_capacidade(await executor_registry.read_capacity(eid))
        except Exception as exc:
            logger.debug("Capacidade do executor '%s' indisponivel: %s", eid, exc)
            return None

    # Só lê capacidade de quem está online (mesma regra de antes).
    online_ids = [eid for eid in ids if online[eid]]
    cap_vals = await asyncio.gather(*(_cap(eid) for eid in online_ids))
    capacidade: dict[str, Optional[dict]] = {eid: None for eid in ids}
    capacidade.update(dict(zip(online_ids, cap_vals)))
    return online, capacidade


async def _confirmacoes_atrasadas() -> Optional[int]:
    """Jobs em voo sem ACK alem do limiar — o mesmo `list_pending_acks` +
    `JOB_ACK_WARN_SECONDS` de que a aba Confirmacoes deriva "atrasado", para
    que o numero da faixa Agora e o da aba nunca discordem.

    `None` quando o registro nao responde (Redis fora, ou um dublê sem o
    metodo): a faixa mostra "nao sei" em vez de a tela inteira cair por causa
    de um numero secundario."""
    from app.core.executor_connections import executor_registry

    try:
        itens = await executor_registry.list_pending_acks()
        limiar = executor_registry.JOB_ACK_WARN_SECONDS
    except Exception as exc:
        logger.debug("Confirmacoes pendentes indisponiveis: %s", exc)
        return None
    return sum(1 for i in itens if (i.get("elapsed_seconds") or 0) >= limiar)


async def _nomes_de_executores(db: AsyncSession, executor_ids: Iterable[str]) -> dict[str, str]:
    ids = [i for i in set(executor_ids) if isinstance(i, str)]
    if not ids:
        return {}
    result = await db.execute(select(Executor.id_hash, Executor.name).where(Executor.id_hash.in_(ids)))
    return {r.id_hash: r.name for r in result.all()}


async def _resolve_agent_names(db: AsyncSession, runs) -> dict[str, str]:
    """Resolve nomes dos executores para hosts no formato 'executor:{id_hash}'."""
    return await _nomes_de_executores(
        db, [_executor_id_do_host(r.host) for r in runs if _executor_id_do_host(r.host)]
    )


async def _nomes_de_workspaces(db: AsyncSession, workspace_ids: Iterable[str]) -> dict[str, str]:
    """Nome pelo `workspace_id` DO RUN, nao pelo workspace atual do workflow:
    um run produzido antes de o workflow ser movido pertence ao workspace de
    origem, e e esse nome que a linha tem de mostrar."""
    ids = [i for i in set(workspace_ids) if isinstance(i, str)]
    if not ids:
        return {}
    result = await db.execute(select(Workspace.id_hash, Workspace.name).where(Workspace.id_hash.in_(ids)))
    return {r.id_hash: r.name for r in result.all()}


async def _nomes_de_usuarios(db: AsyncSession, user_ids: Iterable[str]) -> dict[str, str]:
    ids = [i for i in set(user_ids) if isinstance(i, str)]
    if not ids:
        return {}
    result = await db.execute(select(User.id_hash, User.username).where(User.id_hash.in_(ids)))
    return {r.id_hash: r.username for r in result.all()}


