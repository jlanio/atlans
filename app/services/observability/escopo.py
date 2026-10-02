# app/services/observability/escopo.py
# Lógica de negócio e consultas de observabilidade extraídas do router.
# Contrato com a web: docs/specs/metrics-history.md (§3).

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import (
    InvalidDateFormatError,
    WorkflowNotFoundError as _WfNotFound,
    WorkspaceAccessDeniedError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ROLE_ADMIN
from app.core.utils.logger import get_logger
from app.models.models import Workflow, WorkflowRun

logger = get_logger(__name__)


# Numeros de dashboard nao precisam ser transacionais: 45s de defasagem e
# invisivel na tela e corta as agregacoes repetidas de varias abas/usuarios
# olhando a mesma coisa. O botao "Atualizar" manda `force` e fura o cache.
_METRICS_CACHE_TTL = 45


# ── Helpers ───────────────────────────────────────────────────────────────────

def _agora_utc() -> datetime:
    """Instante atual UTC, AWARE.

    `WorkflowRun.start_time` e `DateTime(timezone=True)` — timestamptz. Um
    datetime NAIVE mandado como bind para timestamptz nao e lido como UTC: o
    codec do asyncpg faz `obj.astimezone(utc)`, que num naive assume o fuso
    LOCAL DO PROCESSO. Como o docker-compose injeta `TZ` na api (o .env.example
    traz America/Cuiaba, UTC-4), toda janela deste servico chegava ao Postgres
    deslocada em 4 horas: o card "Execucoes (24h)" contava so as ultimas 20h e
    omitia a madrugada inteira, sem erro nenhum.
    """
    return datetime.now(timezone.utc)


def _como_utc(valor: datetime) -> datetime:
    """Normaliza um datetime do usuario para AWARE, assumindo UTC se vier sem
    fuso — mesma armadilha de `_agora_utc`, agora vindo do `?date_from=`.

    Tambem serve para o que VOLTA do banco: o SQLite (testes, harness de
    capturas) nao guarda fuso e devolve naive, o que quebraria a subtracao
    com `_agora_utc()` e mandaria ISO sem offset para a web.
    """
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)


def _iso(valor: Optional[datetime]) -> Optional[str]:
    return _como_utc(valor).isoformat() if valor else None


def _zona(tz: str) -> ZoneInfo:
    """Fuso IANA do `?tz=`. O router ja recusa com 422; aqui e a rede de
    seguranca para chamadas diretas do servico."""
    try:
        return ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        raise InvalidDateFormatError(f"tz inválido: {tz}")


def _e_postgres(db) -> bool:
    """Decide entre SQL nativo do PostgreSQL (percentile_cont, AT TIME ZONE) e o
    fallback em Python. O SQLite entra nos testes e no harness de capturas; nao
    tem ordered-set aggregates nem fusos, e nao vale um dialeto proprio."""
    try:
        return str(db.bind.dialect.name) == "postgresql"
    except Exception:
        return False


def e_admin_global(user) -> bool:
    """Diz se o usuário tem o papel global `admin`.

    É a ÚNICA porta de entrada da visão total: quem decide que um admin vê
    tudo é a borda (o router REST, via `como_admin=e_admin_global(user)`), e
    não o service. O servidor MCP (docs/specs/mcp-server.md §6.12) chama os
    mesmos services com o `User` admin e a visão de membro — se o service
    deduzisse o papel do próprio objeto, um PAT de admin atravessaria o
    escopo de workspaces do token sem que nenhuma linha do MCP o tivesse
    permitido.
    """
    return getattr(user, "role", None) == ROLE_ADMIN


def _wf_filter(user, workspace_ids: List[str], *, como_admin: bool = False) -> list:
    """
    Filtro para a tabela Workflow.
    Com `como_admin=True` não há filtro; fora isso o usuário vê os workflows
    do(s) seu(s) workspace(s) — inclusive quando o `user` tem papel admin,
    porque o papel só vale o que a borda declarou (ver `e_admin_global`).

    O `OR workspace_id IS NULL` que existia aqui era um vazamento: entregava a
    qualquer autenticado todo workflow legado sem workspace. A coluna é NOT NULL
    desde a migration 20260828_0001, então não há mais o que acomodar.
    """
    if como_admin:
        return []
    return [Workflow.workspace_id.in_(workspace_ids)]


def _run_filter(user, workspace_ids: List[str], *, como_admin: bool = False) -> list:
    """
    Filtro para WorkflowRun pelo workspace do PRÓPRIO run.
    Com `como_admin=True` não há filtro; o papel do `user` sozinho não basta
    (ver `e_admin_global`).

    Antes isto era uma subquery sobre `Workflow.workspace_id` — o workspace
    ATUAL do workflow. Como um workflow pode mudar de workspace (POST
    /workflows/{id}/move), autorizar pelo workflow entregava aos membros do
    novo workspace todo o histórico produzido no antigo (error_message,
    node_stats, host do executor), e tirava esse histórico de quem só tem
    acesso ao workspace onde ele de fato aconteceu.

    `WorkflowRun.workspace_id` é gravado no despacho e nunca muda: é o dado
    histórico correto, e já indexado. É também o mesmo critério que o WebSocket
    de logs sempre usou (log_workflows_router) e que os artefatos usam
    (artifacts_router filtra por Artifact.workspace_id).

    O `is_(None)` que acompanhava este filtro caiu junto com a nulabilidade da
    coluna (migration 20260828_0001). Ele existia para preservar histórico
    legado, mas o preço era entregar esse histórico — error_message, node_stats,
    host do executor — a qualquer usuário autenticado. A migration atribui os
    runs antigos ao workspace correto em vez de deixá-los públicos.
    """
    if como_admin:
        return []
    return [WorkflowRun.workspace_id.in_(workspace_ids)]


async def _resolver_escopo(
    db: AsyncSession,
    user,
    workspace_ids: List[str],
    *,
    workspace_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    como_admin: bool = False,
) -> tuple[list, list]:
    """Filtros comuns da spec §3 por cima do escopo de tenant.

    Devolve `(filtros de WorkflowRun, filtros de Workflow)`. O `workspace_id`
    pedido precisa estar entre os do usuario (403 `workspace_access_denied`) —
    com `como_admin=True` filtra qualquer um. O `workflow_id` precisa existir
    num workspace acessivel; fora disso e 404, o mesmo que "nao existe", para
    nao confirmar a existencia de workflows de outros tenants.
    """
    run_f = _run_filter(user, workspace_ids, como_admin=como_admin)
    wf_f = _wf_filter(user, workspace_ids, como_admin=como_admin)

    if workspace_id:
        if not como_admin and workspace_id not in workspace_ids:
            raise WorkspaceAccessDeniedError("Você não tem acesso a este workspace.")
        run_f.append(WorkflowRun.workspace_id == workspace_id)
        wf_f.append(Workflow.workspace_id == workspace_id)

    if workflow_id:
        existe = (await db.execute(
            select(Workflow.id_hash).where(Workflow.id_hash == workflow_id, *wf_f)
        )).scalar_one_or_none()
        if existe is None:
            raise _WfNotFound("Workflow não encontrado.")
        run_f.append(WorkflowRun.workflow_hash == workflow_id)
        wf_f.append(Workflow.id_hash == workflow_id)

    return run_f, wf_f


def _metrics_cache_key(
    prefix: str, user, workspace_ids: List[str], days: int, *, como_admin: bool = False, **filtros,
) -> str:
    """Chave do cache de metricas.

    SEG: o escopo de tenant faz PARTE da chave. A visao total (`como_admin`)
    tem chave propria, e o usuario comum e chaveado pela lista exata de
    workspaces que o `Depends(get_user_workspace_ids)` devolveu. Sem isso, o
    primeiro request a preencher o cache serviria os numeros do seu tenant a
    todo mundo. O mesmo admin com e sem `como_admin` (REST × MCP) tambem nao
    pode compartilhar chave: a resposta "todos" ficaria 45 s no cache e seria
    servida a um PAT restrito a um workspace.

    Os filtros opcionais (workspace_id, workflow_id, tz) tambem entram: sem
    eles, o primeiro pedido "todos os workspaces" seria servido a quem pediu
    "so o workspace X" pelos 45 s seguintes.
    """
    # O usuario entra na chave junto com os workspaces: a frota do bloco "now"
    # e de /metrics/executores vem de `get_user_accessible_agents`, que inclui
    # executores atribuidos DIRETAMENTE ao usuario — duas pessoas com os mesmos
    # workspaces nao tem necessariamente a mesma frota.
    visao = "todos" if como_admin else "membro"
    escopo = f"{visao}:{getattr(user, 'id_hash', '')}:" + ",".join(sorted(workspace_ids))
    chave = f"obs:{prefix}:{hashlib.sha256(escopo.encode()).hexdigest()[:16]}:{days}"
    extra = "&".join(f"{k}={v}" for k, v in sorted(filtros.items()) if v)
    if extra:
        chave += f":{hashlib.sha256(extra.encode()).hexdigest()[:12]}"
    return chave


async def _cache_get(key: str):
    """Le o cache. Redis fora do ar nunca pode derrubar o dashboard."""
    try:
        from app.core.redis import get_redis_pool
        raw = await get_redis_pool().get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("Cache de metricas indisponivel na leitura (%s): %s", key, exc)
        return None


async def _cache_set(key: str, value: dict) -> None:
    try:
        from app.core.redis import get_redis_pool
        await get_redis_pool().setex(key, _METRICS_CACHE_TTL, json.dumps(value))
    except Exception as exc:
        logger.debug("Cache de metricas indisponivel na escrita (%s): %s", key, exc)


