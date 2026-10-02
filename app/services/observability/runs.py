# app/services/observability/runs.py
# Lógica de negócio e consultas de observabilidade extraídas do router.
# Contrato com a web: docs/specs/metrics-history.md (§3).


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import NODE_STATS_RUN_META_KEY
from app.models.models import Workflow, WorkflowRun
from app.models.user import User
from app.models.workspace import Workspace


from app.services.observability.escopo import _iso
from app.services.observability.frota import _executor_id_do_host, _nomes_de_usuarios, _nomes_de_workspaces, _resolve_agent_names

# ── Serializacao de runs ──────────────────────────────────────────────────────

# Colunas que a listagem de execucoes realmente usa. `select(WorkflowRun)`
# trazia a entidade inteira — incluindo o JSON `node_stats`, que guarda os
# stats por no de todos os nos do fluxo e chega a megabytes — so para ler
# `retry_count`, um inteiro que a serializacao extrai e o resto e descartado.
# O tempo da lista passava a depender do TAMANHO dos workflows executados, nao
# do numero de linhas mostradas. `retry_count` agora sai por expressao JSON no
# proprio SQL; o blob fica no banco.
_RUN_LIST_COLUMNS = (
    WorkflowRun.task_id,
    WorkflowRun.id,
    WorkflowRun.status,
    WorkflowRun.start_time,
    WorkflowRun.end_time,
    WorkflowRun.duration_seconds,
    WorkflowRun.error_message,
    WorkflowRun.host,
    WorkflowRun.dispatch_tier,
    WorkflowRun.workflow_hash,
    WorkflowRun.workspace_id,
    WorkflowRun.trigger_source,
    WorkflowRun.triggered_by,
    WorkflowRun.error_category,
    WorkflowRun.schedule_id,
    WorkflowRun.node_stats[(NODE_STATS_RUN_META_KEY, "retry_count")]
    .as_integer()
    .label("retry_count"),
)


def _serialize_run(
    r,
    *,
    include_workflow_hash: bool = False,
    include_node_stats: bool = False,
    agent_names: dict | None = None,
    workflow_meta: dict | None = None,
    workspace_names: dict | None = None,
    user_names: dict | None = None,
    admin: bool = False,
) -> dict:
    """Serialização canônica de WorkflowRun — evita duplicação entre endpoints.

    `workflow_meta`, quando presente, deve ser o dict retornado por
    `_resolve_workflow_meta` (mapeando `workflow_hash -> meta`). Dele sai
    `workflow_name` para qualquer usuario no escopo; `workflow_active` e
    `owner_username` so entram com `admin=True` (spec §3.5) — e o default e
    a visao de membro, para que um chamador que esqueca o argumento erre
    para o lado de NAO vazar. O
    `workspace_id` e o DO RUN (o tenant que de fato produziu a execucao), e o
    nome vem de `workspace_names`; a meta do workflow so serve de nome quando
    aponta para o mesmo workspace.
    """
    host = r.host or None
    executor_id = _executor_id_do_host(host)
    executor_name = (agent_names or {}).get(executor_id) if executor_id else None
    if executor_id:
        # Formato historico do `agent_host` ("nome@sufixo"); a web tem
        # `executor_name` para o texto amigavel.
        agent_host = f"{executor_name}@{executor_id[-5:]}" if executor_name else host
    else:
        agent_host = host

    # Aceita tanto a entidade WorkflowRun (detalhe do run, que precisa mesmo do
    # node_stats) quanto a Row de colunas projetadas das listagens, onde
    # `retry_count` ja veio extraido pelo SQL.
    retry_count = getattr(r, "retry_count", None)
    if retry_count is None:
        retry_count = (
            (getattr(r, "node_stats", None) or {})
            .get(NODE_STATS_RUN_META_KEY, {})
            .get("retry_count", 0)
        )

    triggered_by = getattr(r, "triggered_by", None)
    workspace_id = getattr(r, "workspace_id", None)

    out = {
        "run_id":           r.task_id or str(r.id),
        "status":           r.status,
        "started_at":       _iso(r.start_time),
        "finished_at":      _iso(r.end_time),
        "duration_seconds": round(r.duration_seconds, 3) if r.duration_seconds else None,
        "error_message":    r.error_message,
        "retry_count":      retry_count,
        "agent_host":       agent_host,
        # Nível da política em que rodou ("primary" | "fallback" | "pool");
        # nulo em runs anteriores à coluna — a tela esconde o badge.
        "dispatch_tier":    getattr(r, "dispatch_tier", None),
        # Campos do redesenho do Historico (spec §3.5). Nulos em runs
        # anteriores a migracao — a web mostra "—".
        "executor_id":      executor_id,
        "executor_name":    executor_name,
        "trigger_source":   getattr(r, "trigger_source", None),
        "triggered_by":     triggered_by,
        "triggered_by_username": (user_names or {}).get(triggered_by) if triggered_by else None,
        "error_category":   getattr(r, "error_category", None),
        "schedule_id":      getattr(r, "schedule_id", None),
        "workspace_id":     workspace_id,
        "workspace_name":   (workspace_names or {}).get(workspace_id) if workspace_id else None,
        # Origem do FLUXO ("usuario" | "assistente"), nao do disparo — e o que
        # pinta o selo do assistente nas listas. Nula quando o workflow foi
        # deletado permanentemente (sem meta).
        "workflow_origem":  None,
    }
    if include_workflow_hash:
        out["workflow_hash"] = r.workflow_hash
    if include_node_stats:
        out["node_stats"] = {k: v for k, v in (r.node_stats or {}).items() if not k.startswith("__")}

    if workflow_meta is not None:
        meta = workflow_meta.get(r.workflow_hash)
        if meta is not None:
            out["workflow_name"] = meta.get("workflow_name")
            out["workflow_origem"] = meta.get("origem")
            if out["workspace_name"] is None and meta.get("workspace_id") == workspace_id:
                out["workspace_name"] = meta.get("workspace_name")
            if admin:
                out["workflow_active"] = meta.get("workflow_active")
                out["owner_username"] = meta.get("owner_username")

    return out


async def _resolve_workflow_meta(
    db: AsyncSession, workflow_hashes: list[str]
) -> dict[str, dict]:
    """Busca em batch metadados dos workflows (nome, dono, workspace).

    Evita N+1 no serializer de runs. Retorna um dict `{workflow_hash:
    {workflow_name, workflow_active, owner_username, workspace_id,
    workspace_name}}` — chaves ausentes quando o workflow foi deletado
    permanentemente. `owner_username` / `workspace_name` podem ser None em
    legado (users deletados). Quem serializa para usuario comum descarta os
    campos admin-only (`_serialize_run(admin=False)`).
    """
    hashes = [h for h in set(workflow_hashes) if isinstance(h, str)]
    if not hashes:
        return {}

    # `select_from(Workflow)` explicito: sem isso, SQLAlchemy pode
    # escolher User ou Workspace como FROM base (o select tem colunas
    # das 3 tabelas), fazendo com que os outerjoin fiquem "invertidos"
    # e retornem NULL sempre para username/workspace_name.
    result = await db.execute(
        select(
            Workflow.id_hash.label("id_hash"),
            Workflow.name.label("name"),
            Workflow.flag_ative.label("flag_ative"),
            Workflow.workspace_id.label("workspace_id"),
            Workflow.origem.label("origem"),
            User.username.label("owner_username"),
            Workspace.name.label("workspace_name"),
        )
        .select_from(Workflow)
        .outerjoin(User, User.id_hash == Workflow.created_by_id)
        .outerjoin(Workspace, Workspace.id_hash == Workflow.workspace_id)
        .where(Workflow.id_hash.in_(hashes))
    )

    return {
        row.id_hash: {
            "workflow_name":   row.name,
            "workflow_active": bool(row.flag_ative),
            "owner_username":  row.owner_username,
            "workspace_id":    row.workspace_id,
            "workspace_name":  row.workspace_name,
            "origem":          row.origem,
        }
        for row in result.all()
    }


async def _contexto_dos_runs(db: AsyncSession, runs) -> dict:
    """Os quatro lookups em lote que a serializacao de uma pagina de runs
    precisa — um SELECT ... IN cada (executores, workflows, workspaces,
    usuarios), independentemente do numero de linhas."""
    return {
        "agent_names":     await _resolve_agent_names(db, runs),
        "workflow_meta":   await _resolve_workflow_meta(db, [r.workflow_hash for r in runs]),
        "workspace_names": await _nomes_de_workspaces(db, [getattr(r, "workspace_id", None) for r in runs]),
        "user_names":      await _nomes_de_usuarios(db, [getattr(r, "triggered_by", None) for r in runs]),
    }
