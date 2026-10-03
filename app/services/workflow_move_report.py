# app/services/workflow_move_report.py
"""Impact report for moving a workflow between workspaces.

The move never fails because of a broken dependency — whatever would stop
working at the destination comes out of here as a warning. This is a deliberate
choice: the workflow's `workspace_id` is the tenant key for almost everything
(credentials, Drive, executor, portal, webhook allowlist), and blocking the move
on each of those ties would make the operation unusable in practice. In return,
the user needs to see precisely what breaks.

Nothing here writes to the database, and nothing raises to the caller:
`collect_warnings` already wraps everything and returns `report_incomplete` if
the computation itself fails.
"""

from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import func, select

from app.core.authorization.credential_loader import workspace_credential_owners
from app.core.utils.allowlist import hostname_matches_allowlist
from app.core.utils.logger import get_logger
from app.core.utils.workflow_nodes import node_props
from app.core.utils.workflow_triggers import has_webhook_trigger
from app.models.artifact import Artifact
from app.models.credential import Credential
from app.models.models import Workflow, WorkflowRun
from app.models.portal_layer import PortalLayer
from app.models.workflow_group import WorkflowGroup
from app.models.workspace import Workspace
from app.models.workspace_file import WorkspaceFile

logger = get_logger(__name__)

# File ids that the read nodes accept. `driveFileId` points to
# WorkspaceFile, `artifactId` to Artifact — both tied to the workspace where
# they were created (see DataInput and the Read* nodes).
_DRIVE_ID_PROP = "driveFileId"
_ARTIFACT_ID_PROP = "artifactId"


def warn(code: str, message: str, *, severity: str = "warning", **details: Any) -> Dict[str, Any]:
    """Single builder of the warning format — also used by `workflow_move_service`."""
    return {"code": code, "severity": severity, "message": message, "details": details}


def _iter_nodes(definition: dict) -> Iterable[dict]:
    return definition.get("nodes") or []


def _collect_prop(definition: dict, prop: str) -> Dict[str, List[str]]:
    """Map `property value -> ids of the nodes that use it`.

    Uses `node_props`, which applies the `data.properties` → `properties` chain.
    The canvas format (XYFlow) writes to `data.properties`, so reading only
    `properties` would produce a false negative — and a warning that does not
    show up is worse than no report at all, because it gives the impression
    that everything is fine.
    """
    encontrados: Dict[str, List[str]] = {}
    for node in _iter_nodes(definition):
        valor = node_props(node).get(prop)
        if isinstance(valor, str) and valor.strip():
            encontrados.setdefault(valor.strip(), []).append(node.get("id"))
    return encontrados


def _collect_subworkflow_refs(definition: dict) -> Dict[str, List[str]]:
    """`workflowHash -> ids of the SubWorkflow nodes that reference it`.

    A local collector instead of `collect_subworkflow_references` from
    `flow/utils/workflow_contract.py`: that one reads only `node["properties"]`,
    without the `node_props` chain. We do not change it because it also feeds
    save validation, which is a security path — changing what it sees would
    change the write behavior along with it.
    """
    refs: Dict[str, List[str]] = {}
    for node in _iter_nodes(definition):
        if node.get("name") != "SubWorkflow":
            continue
        wh = (node_props(node).get("workflowHash") or "").strip()
        if wh:
            refs.setdefault(wh, []).append(node.get("id"))
    return refs


async def _avisar_credenciais(db, definition: dict, target_ws: str) -> List[Dict[str, Any]]:
    """Credentials that stop resolving at the destination.

    The credential scope is derived at runtime from the members of the
    workflow's workspace (`workspace_credential_owners`) — `credentials` has no
    workspace column. If the owner does not reach the destination, the
    credential simply vanishes from the dispatch, and the only sign is a
    WARNING in the server log (`_explain_missing`). It is the quietest side
    effect of the move.
    """
    # A single sweep: the three pieces of information the warning needs (which
    # credentials, in which nodes, and whether any of them is a trigger) come out
    # of the same pass. Collecting them separately forced reconciling maps that
    # could diverge.
    usos: Dict[str, Dict[str, Any]] = {}
    for node in _iter_nodes(definition):
        cid = node_props(node).get("credential_id")
        if not isinstance(cid, str) or not cid.strip():
            continue
        uso = usos.setdefault(cid.strip(), {"nodes": [], "is_trigger": False})
        uso["nodes"].append(node.get("id"))
        if node.get("type") == "trigger":
            uso["is_trigger"] = True
    if not usos:
        return []

    # `Credential.id` is UUID(as_uuid=True); asyncpg does not cast automatically.
    uuids: List[UUID] = []
    for cid in usos:
        try:
            uuids.append(UUID(cid))
        except (ValueError, AttributeError, TypeError):
            continue
    if not uuids:
        return []

    permitidos = await workspace_credential_owners(db, target_ws)
    # Metadata only — the report never touches `Credential.data`.
    linhas = (await db.execute(
        select(Credential.id, Credential.name, Credential.owner_id)
        .where(Credential.id.in_(uuids))
    )).all()
    conhecidas = {str(cid): (nome, dono) for cid, nome, dono in linhas}

    avisos: List[Dict[str, Any]] = []
    for chave, uso in usos.items():
        nodes, is_trigger = uso["nodes"], uso["is_trigger"]
        if chave not in conhecidas:
            avisos.append(warn(
                "credential_not_found",
                f"A credencial {chave} referenciada no workflow não existe mais.",
                credential_id=chave, node_ids=nodes, is_trigger=is_trigger,
            ))
            continue

        nome, dono = conhecidas[chave]
        if dono and dono in permitidos:
            continue

        # On a trigger the effect is loud: `_validate_trigger_credentials_only` is
        # fail-closed and returns 403, killing the trigger firing. In the other
        # nodes the credential is just not injected and the node fails later on.
        efeito = (
            "o disparo por webhook passará a falhar com 403"
            if is_trigger else
            "o nó falhará ao executar"
        )
        avisos.append(warn(
            "credentials_unresolvable",
            f"A credencial '{nome}' pertence a alguém sem acesso ao workspace de "
            f"destino e deixará de ser resolvida — {efeito}.",
            credential_id=chave, credential_name=nome, owner_id=dono,
            node_ids=nodes, is_trigger=is_trigger,
        ))
    return avisos


async def _avisar_subworkflows(db, definition: dict, target_ws: str) -> List[Dict[str, Any]]:
    """Called sub-workflows that end up outside the destination.

    Execution requires the target to live in the same workspace as the parent —
    see `validate_subworkflow_references_against_db`.
    """
    refs = _collect_subworkflow_refs(definition)
    if not refs:
        return []

    linhas = (await db.execute(
        select(Workflow.id_hash, Workflow.name, Workflow.workspace_id)
        .where(Workflow.id_hash.in_(list(refs)))
    )).all()
    alvos = {h: (nome, ws) for h, nome, ws in linhas}

    avisos: List[Dict[str, Any]] = []
    for wh, nodes in refs.items():
        if wh not in alvos:
            avisos.append(warn(
                "subworkflow_not_found",
                f"O sub-workflow {wh} referenciado não existe.",
                workflow_hash=wh, node_ids=nodes,
            ))
            continue
        nome, ws = alvos[wh]
        if ws != target_ws:
            avisos.append(warn(
                "subworkflow_out_of_scope",
                f"O sub-workflow '{nome}' fica em outro workspace e deixará de "
                "poder ser chamado por este fluxo.",
                workflow_hash=wh, workflow_name=nome, workspace_id=ws, node_ids=nodes,
            ))
    return avisos


async def _avisar_dependentes(db, id_hash: str, origin_ws: str | None) -> List[Dict[str, Any]]:
    """Workflows that call THIS one as a sub-workflow and are left behind.

    An easy side effect to forget, because it is not in the definition of the
    workflow being moved — it is in the others'. We only sweep the origin:
    dependents in a third workspace were already broken before the move.
    """
    if not origin_ws:
        return []

    # Database pre-filter so we don't fetch the definition of the whole workspace.
    # It is just a LIKE over the text of the nodes array: the real confirmation
    # comes from the collector below, because the hash may appear in any other
    # field of the JSON.
    candidatos = (await db.execute(
        select(Workflow.id_hash, Workflow.name, Workflow.definition).where(
            Workflow.deleted_at.is_(None),
            Workflow.workspace_id == origin_ws,
            Workflow.id_hash != id_hash,
            Workflow.definition["nodes"].as_string().contains(id_hash),
        )
    )).all()

    avisos: List[Dict[str, Any]] = []
    for dep_hash, dep_name, dep_def in candidatos:
        nodes = _collect_subworkflow_refs(dep_def or {}).get(id_hash)
        if nodes:
            avisos.append(warn(
                "reverse_dependents",
                f"O workflow '{dep_name}' chama este como sub-fluxo e vai parar "
                "de funcionar, pois ficará em outro workspace.",
                workflow_hash=dep_hash, workflow_name=dep_name, node_ids=nodes,
            ))
    return avisos


async def _avisar_arquivos(db, definition: dict, target_ws: str) -> List[Dict[str, Any]]:
    """Referenced Drive files and artifacts that belong to the origin."""
    avisos: List[Dict[str, Any]] = []

    drive_ids = _collect_prop(definition, _DRIVE_ID_PROP)
    if drive_ids:
        linhas = (await db.execute(
            select(WorkspaceFile.id_hash, WorkspaceFile.original_name, WorkspaceFile.workspace_id)
            .where(WorkspaceFile.id_hash.in_(list(drive_ids)))
        )).all()
        achados = {h: (nome, ws) for h, nome, ws in linhas}
        for fid, nodes in drive_ids.items():
            nome, ws = achados.get(fid, (None, None))
            if ws != target_ws:
                avisos.append(warn(
                    "drive_refs_out_of_scope",
                    f"O arquivo do Drive '{nome or fid}' não existe no workspace de "
                    "destino — os nós que o leem vão falhar.",
                    file_id=fid, filename=nome, workspace_id=ws, node_ids=nodes,
                ))

    artifact_ids = _collect_prop(definition, _ARTIFACT_ID_PROP)
    if artifact_ids:
        linhas = (await db.execute(
            select(Artifact.id_hash, Artifact.filename, Artifact.workspace_id)
            .where(Artifact.id_hash.in_(list(artifact_ids)))
        )).all()
        achados = {h: (nome, ws) for h, nome, ws in linhas}
        for aid, nodes in artifact_ids.items():
            nome, ws = achados.get(aid, (None, None))
            if ws != target_ws:
                avisos.append(warn(
                    "artifact_refs_out_of_scope",
                    f"O artefato '{nome or aid}' pertence a outro workspace — os nós "
                    "que o leem vão falhar.",
                    artifact_id=aid, filename=nome, workspace_id=ws, node_ids=nodes,
                ))
    return avisos


async def _avisar_workspace(db, wf, origin_ws: str | None, target_ws: str) -> List[Dict[str, Any]]:
    """Configuration differences between the two workspaces.

    Dedicated executor and notification allowlist are per workspace, so they
    change silently along with the tenant.
    """
    linhas = (await db.execute(
        select(
            Workspace.id_hash, Workspace.name,
            Workspace.target_executor_id, Workspace.notification_url_allowlist,
        ).where(Workspace.id_hash.in_([w for w in (origin_ws, target_ws) if w]))
    )).all()
    by_task_id = {h: (nome, executor, allowlist) for h, nome, executor, allowlist in linhas}

    avisos: List[Dict[str, Any]] = []
    _, origin_exec, _ = by_task_id.get(origin_ws, (None, None, None))
    target_name, target_exec, allowlist = by_task_id.get(target_ws, (None, None, None))

    if origin_exec != target_exec:
        target_txt = (
            "o pool de executores padrão" if not target_exec
            else "outro executor dedicado"
        )
        avisos.append(warn(
            "executor_changed",
            f"As execuções passarão a rodar em {target_txt}, que pode não ter o "
            "mesmo acesso de rede e a bancos internos.",
            from_executor_id=origin_exec, to_executor_id=target_exec,
        ))

    url = getattr(wf, "notification_url", None)
    if url and allowlist:
        host = ""
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            host = ""
        if not hostname_matches_allowlist(host, allowlist):
            avisos.append(warn(
                "notification_url_blocked",
                f"A URL de notificação não é permitida no workspace "
                f"'{target_name}' e passará a ser bloqueada após cada execução.",
                notification_url=url, host=host, allowlist=allowlist,
            ))
    return avisos


async def _avisar_estado(db, wf, definition: dict) -> List[Dict[str, Any]]:
    """Deterministic consequences of the operation and state left behind."""
    avisos: List[Dict[str, Any]] = []
    id_hash = wf.id_hash

    # COUNT separate from the SELECT of ids: counting the result of a `limit(5)`
    # would make the message say "5" for any number above that.
    em_andamento = (await db.execute(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.workflow_hash == id_hash,
            WorkflowRun.status.in_(("pending", "running")),
        )
    )).scalar_one_or_none() or 0
    if em_andamento:
        amostra = (await db.execute(
            select(WorkflowRun.task_id).where(
                WorkflowRun.workflow_hash == id_hash,
                WorkflowRun.status.in_(("pending", "running")),
            ).limit(5)
        )).scalars().all()
        avisos.append(warn(
            "active_runs",
            f"Há {em_andamento} execução(ões) em andamento. Elas terminam gravando "
            "no workspace de origem, como foram despachadas, e o cache de dados "
            "fixados que produzirem será descartado.",
            total=em_andamento, run_ids=list(amostra),
        ))

    if has_webhook_trigger(definition):
        avisos.append(warn(
            "webhook_url_still_live",
            "A URL de webhook não muda e continua ativa — quem já a possui seguirá "
            "disparando este workflow, agora produzindo dados no novo workspace.",
            severity="info",
        ))

    total_runs = (await db.execute(
        select(func.count()).select_from(WorkflowRun)
        .where(WorkflowRun.workflow_hash == id_hash)
    )).scalar_one_or_none() or 0
    if total_runs:
        avisos.append(warn(
            "history_left_behind",
            f"O histórico de {total_runs} execução(ões), com seus artefatos e "
            "métricas, permanece no workspace de origem.",
            severity="info", total_runs=total_runs,
        ))

    if wf.pinned_outputs:
        avisos.append(warn(
            "pins_cleared",
            "Os dados fixados (pins) serão removidos: os objetos ficam sob o "
            "prefixo do workspace de origem e não seriam legíveis no destino.",
            severity="info", node_ids=list(wf.pinned_outputs),
        ))

    if wf.group_id:
        nome_grupo = (await db.execute(
            select(WorkflowGroup.name).where(WorkflowGroup.id_hash == wf.group_id)
        )).scalar_one_or_none()
        avisos.append(warn(
            "group_cleared",
            f"O workflow sai do grupo '{nome_grupo or wf.group_id}', que pertence "
            "ao workspace de origem.",
            severity="info", group_id=wf.group_id, group_name=nome_grupo,
        ))

    if wf.portal_access and wf.portal_access != "disabled":
        avisos.append(warn(
            "portal_disabled",
            "O portal volta a 'desativado' e os links já compartilhados deixarão "
            "de funcionar.",
            portal_access=wf.portal_access,
        ))

    has_layers = (await db.execute(
        select(func.count()).select_from(PortalLayer)
        .where(PortalLayer.workflow_hash == id_hash)
    )).scalar_one_or_none() or 0
    if has_layers:
        avisos.append(warn(
            "portal_layers_retained",
            f"As {has_layers} camada(s) já publicadas acompanham o workflow. Se o "
            "portal for reativado no destino, elas voltam a ficar visíveis lá.",
            severity="info", layers=has_layers,
        ))

    from app.core.scheduling.hooks import extract_schedule_node
    if extract_schedule_node(definition) is not None:
        avisos.append(warn(
            "schedule_disabled",
            "O agendamento chega desligado no destino, para não disparar sozinho "
            "antes de você revisar o fluxo.",
            severity="info",
        ))

    return avisos


async def collect_warnings(db, wf, definition: dict, origin_ws: str | None, target_ws: str) -> List[Dict[str, Any]]:
    """Gathers all the warnings. Never raises.

    A report that fails must not bring down the move — that is the rule of the
    feature. If something here breaks, the move goes ahead and the user gets
    `report_incomplete` instead of a silently empty list, which they would read
    as "there is no impact at all".
    """
    avisos: List[Dict[str, Any]] = []
    try:
        avisos.extend(await _avisar_credenciais(db, definition, target_ws))
        avisos.extend(await _avisar_subworkflows(db, definition, target_ws))
        avisos.extend(await _avisar_dependentes(db, wf.id_hash, origin_ws))
        avisos.extend(await _avisar_arquivos(db, definition, target_ws))
        avisos.extend(await _avisar_workspace(db, wf, origin_ws, target_ws))
        avisos.extend(await _avisar_estado(db, wf, definition))
    except Exception as exc:
        logger.warning(
            "Falha ao montar o relatório de impacto do move do workflow %s: %s",
            getattr(wf, "id_hash", "?"), exc, exc_info=True,
        )
        avisos.append(warn(
            "report_incomplete",
            "Não foi possível verificar todos os impactos da movimentação. "
            "Revise credenciais, sub-fluxos e arquivos referenciados no destino.",
        ))

    # Warnings before infos: what breaks has to appear first on screen.
    avisos.sort(key=lambda a: 0 if a["severity"] == "warning" else 1)
    return avisos
