# app/services/workflow_move_report.py
"""Relatório de impactos de mover um workflow entre workspaces.

A movimentação nunca falha por dependência quebrada — o que deixaria de
funcionar no destino sai daqui como aviso. Isso é uma escolha deliberada: o
`workspace_id` do workflow é a chave de tenant de quase tudo (credenciais,
Drive, executor, portal, allowlist de webhook), e barrar o move em cada uma
dessas amarras tornaria a operação inutilizável na prática. Em troca, o usuário
precisa ver com precisão o que quebra.

Nada aqui escreve no banco, e nada levanta para o chamador: `collect_warnings`
já embrulha tudo e devolve `report_incomplete` se o próprio cálculo falhar.
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

# Ids de arquivo que os nós de leitura aceitam. `driveFileId` aponta para
# WorkspaceFile, `artifactId` para Artifact — ambos presos ao workspace onde
# foram criados (ver DataInput e os nós Read*).
_DRIVE_ID_PROP = "driveFileId"
_ARTIFACT_ID_PROP = "artifactId"


def warn(code: str, message: str, *, severity: str = "warning", **details: Any) -> Dict[str, Any]:
    """Construtor único do formato de aviso — usado também pelo `workflow_move_service`."""
    return {"code": code, "severity": severity, "message": message, "details": details}


def _iter_nodes(definition: dict) -> Iterable[dict]:
    return definition.get("nodes") or []


def _collect_prop(definition: dict, prop: str) -> Dict[str, List[str]]:
    """Mapa `valor da propriedade -> ids dos nós que a usam`.

    Usa `node_props`, que aplica a cadeia `data.properties` → `properties`. O
    formato do canvas (XYFlow) grava em `data.properties`, então ler só
    `properties` produziria falso-negativo — e um aviso que não aparece é pior
    do que nenhum relatório, porque passa a impressão de que está tudo certo.
    """
    encontrados: Dict[str, List[str]] = {}
    for node in _iter_nodes(definition):
        valor = node_props(node).get(prop)
        if isinstance(valor, str) and valor.strip():
            encontrados.setdefault(valor.strip(), []).append(node.get("id"))
    return encontrados


def _collect_subworkflow_refs(definition: dict) -> Dict[str, List[str]]:
    """`workflowHash -> ids dos nós SubWorkflow que o referenciam`.

    Coletor local em vez de `collect_subworkflow_references` de
    `flow/utils/workflow_contract.py`: aquele lê apenas `node["properties"]`, sem
    a cadeia do `node_props`. Não o alteramos porque ele também alimenta a
    validação de save, que é caminho de segurança — mudar o que ele enxerga
    mudaria o comportamento de gravação junto.
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
    """Credenciais que deixam de resolver no destino.

    O escopo de credenciais é derivado em runtime dos membros do workspace do
    workflow (`workspace_credential_owners`) — `credentials` não tem coluna de
    workspace. Se o dono não alcança o destino, a credencial simplesmente some
    do dispatch, e o único sinal é um WARNING no log do servidor
    (`_explain_missing`). É o colateral mais silencioso do move.
    """
    # Uma varredura só: as três informações de que o aviso precisa (quais
    # credenciais, em que nós, e se algum deles é trigger) saem do mesmo passo.
    # Coletá-las separadamente obrigava a reconciliar mapas que podiam divergir.
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

    # `Credential.id` é UUID(as_uuid=True); asyncpg não faz cast automático.
    uuids: List[UUID] = []
    for cid in usos:
        try:
            uuids.append(UUID(cid))
        except (ValueError, AttributeError, TypeError):
            continue
    if not uuids:
        return []

    permitidos = await workspace_credential_owners(db, target_ws)
    # Só metadados — o relatório nunca toca em `Credential.data`.
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

        # Em trigger o efeito é ruidoso: `_validate_trigger_credentials_only` é
        # fail-closed e devolve 403, derrubando o disparo. Nos demais nós a
        # credencial só não é injetada e o nó falha lá na frente.
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
    """Sub-workflows chamados que ficam fora do destino.

    A execução exige que o alvo viva no mesmo workspace do pai — ver
    `validate_subworkflow_references_against_db`.
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
    """Workflows que chamam ESTE como sub-fluxo e ficam para trás.

    Colateral fácil de esquecer, porque não está na definition do workflow que
    se move — está na dos outros. Só varremos a origem: dependentes num terceiro
    workspace já estavam quebrados antes do move.
    """
    if not origin_ws:
        return []

    # Pré-filtro no banco para não trazer a definition de todo o workspace. É só
    # um LIKE sobre o texto do array de nós: a confirmação real vem do coletor
    # abaixo, porque o hash pode aparecer em qualquer outro campo do JSON.
    candidatos = (await db.execute(
        select(Workflow.id_hash, Workflow.name, Workflow.definition).where(
            Workflow.deleted_at.is_(None),
            Workflow.workspace_id == origin_ws,
            Workflow.id_hash != id_hash,
            Workflow.definition["nodes"].as_string().contains(id_hash),
        )
    )).all()

    avisos: List[Dict[str, Any]] = []
    for dep_hash, dep_nome, dep_def in candidatos:
        nodes = _collect_subworkflow_refs(dep_def or {}).get(id_hash)
        if nodes:
            avisos.append(warn(
                "reverse_dependents",
                f"O workflow '{dep_nome}' chama este como sub-fluxo e vai parar "
                "de funcionar, pois ficará em outro workspace.",
                workflow_hash=dep_hash, workflow_name=dep_nome, node_ids=nodes,
            ))
    return avisos


async def _avisar_arquivos(db, definition: dict, target_ws: str) -> List[Dict[str, Any]]:
    """Arquivos de Drive e artefatos referenciados que pertencem à origem."""
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
    """Diferenças de configuração entre os dois workspaces.

    Executor dedicado e allowlist de notificação são por workspace, então mudam
    silenciosamente junto com o tenant.
    """
    linhas = (await db.execute(
        select(
            Workspace.id_hash, Workspace.name,
            Workspace.target_executor_id, Workspace.notification_url_allowlist,
        ).where(Workspace.id_hash.in_([w for w in (origin_ws, target_ws) if w]))
    )).all()
    por_id = {h: (nome, executor, allowlist) for h, nome, executor, allowlist in linhas}

    avisos: List[Dict[str, Any]] = []
    _, exec_origem, _ = por_id.get(origin_ws, (None, None, None))
    nome_destino, exec_destino, allowlist = por_id.get(target_ws, (None, None, None))

    if exec_origem != exec_destino:
        destino_txt = (
            "o pool de executores padrão" if not exec_destino
            else "outro executor dedicado"
        )
        avisos.append(warn(
            "executor_changed",
            f"As execuções passarão a rodar em {destino_txt}, que pode não ter o "
            "mesmo acesso de rede e a bancos internos.",
            from_executor_id=exec_origem, to_executor_id=exec_destino,
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
                f"'{nome_destino}' e passará a ser bloqueada após cada execução.",
                notification_url=url, host=host, allowlist=allowlist,
            ))
    return avisos


async def _avisar_estado(db, wf, definition: dict) -> List[Dict[str, Any]]:
    """Consequências determinísticas da operação e estado que fica para trás."""
    avisos: List[Dict[str, Any]] = []
    id_hash = wf.id_hash

    # COUNT separado do SELECT de ids: contar o resultado de um `limit(5)` faria
    # a mensagem dizer "5" para qualquer número acima disso.
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

    tem_camadas = (await db.execute(
        select(func.count()).select_from(PortalLayer)
        .where(PortalLayer.workflow_hash == id_hash)
    )).scalar_one_or_none() or 0
    if tem_camadas:
        avisos.append(warn(
            "portal_layers_retained",
            f"As {tem_camadas} camada(s) já publicadas acompanham o workflow. Se o "
            "portal for reativado no destino, elas voltam a ficar visíveis lá.",
            severity="info", layers=tem_camadas,
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
    """Reúne todos os avisos. Nunca levanta.

    Um relatório que falha não pode derrubar a movimentação — essa é a regra do
    recurso. Se algo aqui quebrar, o move segue e o usuário recebe
    `report_incomplete` em vez de uma lista silenciosamente vazia, que ele leria
    como "não há impacto nenhum".
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

    # Warnings antes de infos: o que quebra tem de aparecer primeiro na tela.
    avisos.sort(key=lambda a: 0 if a["severity"] == "warning" else 1)
    return avisos
