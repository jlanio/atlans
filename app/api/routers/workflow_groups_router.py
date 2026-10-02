from app.core.utils.logger import get_logger
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, select, func

from app.models.models import WorkflowGroup, Workflow
from app.schemas.workflow_group import (
    WorkflowGroupCreate, WorkflowGroupUpdate, WorkflowGroupRead, WorkflowGroupReorder,
)
from app.api.dependencies import (
    get_db, get_current_user, get_user_workspace_ids, verify_workspace_access,
    exigir_papel_no_workspace,
)
from app.core.rate_limiter import limiter
from app.core.rbac import ROLE_EDITOR

logger = get_logger(__name__)

router = APIRouter(prefix="/workflow-groups", tags=["workflow-groups"])


# ── Resolucao de workflows agrupaveis ────────────────────────────────────────
#
# As quatro rotas que escrevem `Workflow.group_id` conferem o papel do usuario
# no workspace do GRUPO. Resolver o workflow so pelo `id_hash` deixava um editor
# arrastar workflow de OUTRO tenant para dentro do proprio grupo — e, em
# seguida, zerar `group_id` em massa via DELETE. O casamento de workspace mora
# aqui para nao poder divergir entre elas de novo.
#
# `flag_ative` NAO entra no criterio, de proposito: agrupar e organizacao, nao
# execucao, e um workflow desativado continua aparecendo na tela de Projetos.
# Filtrar por ele fazia um item que o usuario acabara de marcar na lista sumir
# do resultado — e, com a recusa explicita abaixo, derrubar a criacao inteira
# com "nao encontrado". `deleted_at` entra: o que esta na lixeira nao e alvo.


def _alvos_agrupaveis(workflow_ids, group) -> list:
    """Condicoes que um workflow tem de satisfazer para entrar neste grupo."""
    return [
        Workflow.id_hash.in_(workflow_ids),
        Workflow.workspace_id == group.workspace_id,
        Workflow.deleted_at.is_(None),
    ]


def _recusar_ids_fora_do_grupo(pedidos, encontrados) -> None:
    """404 para id inexistente, na lixeira ou de outro workspace.

    Recusar, e nao ignorar em silencio: gravar so a parte conhecida deixaria a
    tela e o banco divergentes — mesmo criterio de `reorder_groups`. A mensagem
    nao distingue "nao existe" de "e de outro tenant", para nao virar um oraculo
    de enumeracao de id_hash.
    """
    desconhecidos = set(pedidos) - {wf.id_hash for wf in encontrados}
    if desconhecidos:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow(s) não encontrado(s) neste workspace: {', '.join(sorted(desconhecidos))}",
        )


# ── Contagem dos grupos ──────────────────────────────────────────────────────
#
# `workflow_count` conta TODOS os workflows nao excluidos do grupo, e
# `active_count` so os com `flag_ative`. Antes contava-se so os ativos, e a
# tela dizia "2 workflows" num grupo de 3 quando um estava desativado — o
# inativo continua na lista, entao a contagem tem de bater com o que se ve.
# Uma agregacao so, com `sum(case …)` em vez de `count(*) FILTER`, para valer
# igual no SQLite dos testes e no PostgreSQL.


async def _contagens_por_grupo(db: AsyncSession, group_ids: list[str]) -> dict[str, tuple[int, int]]:
    """id_hash do grupo -> (workflow_count, active_count). Grupo sem workflow
    nao aparece no dict; quem le usa (0, 0)."""
    if not group_ids:
        return {}
    result = await db.execute(
        select(
            Workflow.group_id,
            func.count().label("total"),
            func.sum(case((Workflow.flag_ative.is_(True), 1), else_=0)).label("ativos"),
        )
        .where(Workflow.group_id.in_(group_ids), Workflow.deleted_at.is_(None))
        .group_by(Workflow.group_id)
    )
    return {row.group_id: (int(row.total or 0), int(row.ativos or 0)) for row in result}


async def _ler_grupo(db: AsyncSession, group: WorkflowGroup) -> WorkflowGroupRead:
    """Serializa um grupo com as duas contagens — as rotas de um grupo so
    (criar, atualizar) passam por aqui para nao divergirem da listagem."""
    contagens = await _contagens_por_grupo(db, [group.id_hash])
    item = WorkflowGroupRead.model_validate(group)
    item.workflow_count, item.active_count = contagens.get(group.id_hash, (0, 0))
    return item


@router.post("", status_code=201, response_model=WorkflowGroupRead)
@limiter.limit("30/minute")
async def create_group(
    request: Request,
    payload: WorkflowGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await exigir_papel_no_workspace(db, payload.workspace_id, current_user.id_hash, ROLE_EDITOR)

    # Fim da fila: sem isto todo grupo novo nasce em `position=0`, empatado
    # com os que ja existem, e a ordem entre eles volta a depender do desempate.
    ultima = await db.execute(
        select(func.max(WorkflowGroup.position)).where(
            WorkflowGroup.workspace_id == payload.workspace_id
        )
    )
    group = WorkflowGroup(
        name=payload.name,
        description=payload.description,
        workspace_id=payload.workspace_id,
        position=(ultima.scalar() or 0) + 1,
    )
    db.add(group)
    await db.flush()  # gera id_hash antes de vincular workflows

    # Vincula workflows ao grupo. O filtro de workspace vive no `select` (e nao
    # numa checagem depois) para valer igual nas quatro rotas que mexem em
    # `Workflow.group_id` — era a divergencia que abria a escrita cross-tenant.
    if payload.workflow_ids:
        result = await db.execute(
            select(Workflow).where(*_alvos_agrupaveis(payload.workflow_ids, group))
        )
        workflows = result.scalars().all()
        _recusar_ids_fora_do_grupo(payload.workflow_ids, workflows)
        for wf in workflows:
            wf.group_id = group.id_hash

    await db.commit()
    await db.refresh(group)

    group_data = await _ler_grupo(db, group)
    logger.info("Grupo criado: id=%s name=%s workspace=%s", group.id_hash, group.name, group.workspace_id)
    return group_data


@router.get("", response_model=List[WorkflowGroupRead])
async def list_groups(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    if workspace_id:
        verify_workspace_access(workspace_id, workspace_ids)
        stmt = select(WorkflowGroup).where(WorkflowGroup.workspace_id == workspace_id)
    else:
        stmt = select(WorkflowGroup).where(WorkflowGroup.workspace_id.in_(workspace_ids))

    # `name` desempata: duas posicoes iguais (grupos criados antes da coluna
    # existir, ou uma reordenacao interrompida) voltariam a sair em ordem
    # indefinida, que e exatamente o defeito que a posicao veio resolver.
    stmt = stmt.order_by(WorkflowGroup.position, WorkflowGroup.name)

    result = await db.execute(stmt)
    groups = result.scalars().all()

    # As duas contagens de todos os grupos em uma query
    contagens = await _contagens_por_grupo(db, [g.id_hash for g in groups])

    out = []
    for g in groups:
        item = WorkflowGroupRead.model_validate(g)
        item.workflow_count, item.active_count = contagens.get(g.id_hash, (0, 0))
        out.append(item)
    return out


@router.put("/reorder", status_code=204)
async def reorder_groups(
    payload: WorkflowGroupReorder,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Grava a ordem dos grupos, na sequencia recebida.

    Declarada ANTES de `/{group_id}`: o FastAPI casa as rotas na ordem de
    registro, e o path variavel engoliria "reorder" como se fosse um id.
    """
    result = await db.execute(
        select(WorkflowGroup).where(WorkflowGroup.id_hash.in_(payload.group_ids))
    )
    grupos = {g.id_hash: g for g in result.scalars().all()}

    # Recusar, e nao ignorar em silencio: um id que nao existe ou e de outro
    # workspace significa que a tela esta trabalhando com uma lista diferente
    # da do banco, e gravar so a parte conhecida deixaria as duas divergentes.
    desconhecidos = [gid for gid in payload.group_ids if gid not in grupos]
    if desconhecidos:
        raise HTTPException(
            status_code=404,
            detail=f"Grupo(s) não encontrado(s): {', '.join(desconhecidos)}",
        )

    espacos = {g.workspace_id for g in grupos.values()}
    if len(espacos) > 1:
        raise HTTPException(
            status_code=400,
            detail="Todos os grupos reordenados precisam ser do mesmo workspace.",
        )
    workspace_id = espacos.pop()
    await exigir_papel_no_workspace(db, workspace_id, current_user.id_hash, ROLE_EDITOR)

    for indice, gid in enumerate(payload.group_ids):
        grupos[gid].position = indice

    await db.commit()
    logger.info(
        "Grupos reordenados: workspace=%s total=%d", workspace_id, len(payload.group_ids)
    )


@router.put("/{group_id}", response_model=WorkflowGroupRead)
async def update_group(
    group_id: str,
    payload: WorkflowGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(WorkflowGroup).where(WorkflowGroup.id_hash == group_id)
    )
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    await exigir_papel_no_workspace(db, group.workspace_id, current_user.id_hash, ROLE_EDITOR)

    if payload.name is not None:
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description

    # Atualiza membros do grupo
    if payload.workflow_ids is not None:
        # Remove todos os workflows do grupo
        old_result = await db.execute(
            select(Workflow).where(
                Workflow.group_id == group_id,
                Workflow.workspace_id == group.workspace_id,
            )
        )
        for wf in old_result.scalars().all():
            wf.group_id = None

        # Adiciona os novos, pelo mesmo criterio de `create_group`.
        if payload.workflow_ids:
            new_result = await db.execute(
                select(Workflow).where(*_alvos_agrupaveis(payload.workflow_ids, group))
            )
            encontrados = new_result.scalars().all()
            _recusar_ids_fora_do_grupo(payload.workflow_ids, encontrados)
            for wf in encontrados:
                wf.group_id = group.id_hash

    await db.commit()
    await db.refresh(group)

    return await _ler_grupo(db, group)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(WorkflowGroup).where(WorkflowGroup.id_hash == group_id)
    )
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    await exigir_papel_no_workspace(db, group.workspace_id, current_user.id_hash, ROLE_EDITOR)

    # Desvincula workflows antes de deletar. O filtro de workspace impede que
    # apagar um grupo proprio mexa em workflow de outro tenant.
    wf_result = await db.execute(
        select(Workflow).where(
            Workflow.group_id == group_id,
            Workflow.workspace_id == group.workspace_id,
        )
    )
    for wf in wf_result.scalars().all():
        wf.group_id = None

    await db.delete(group)
    await db.commit()
    logger.info("Grupo deletado: id=%s", group_id)


@router.post("/{group_id}/workflows/{workflow_id}", status_code=204)
async def add_workflow_to_group(
    group_id: str,
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Adiciona um workflow a um grupo."""
    group_result = await db.execute(
        select(WorkflowGroup).where(WorkflowGroup.id_hash == group_id)
    )
    group = group_result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    await exigir_papel_no_workspace(db, group.workspace_id, current_user.id_hash, ROLE_EDITOR)

    # Mesmo criterio das rotas em lote — ver `_alvos_agrupaveis`.
    wf_result = await db.execute(
        select(Workflow).where(*_alvos_agrupaveis([workflow_id], group))
    )
    wf = wf_result.scalars().first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow não encontrado")

    wf.group_id = group.id_hash
    await db.commit()


@router.delete("/{group_id}/workflows/{workflow_id}", status_code=204)
async def remove_workflow_from_group(
    group_id: str,
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove um workflow de um grupo."""
    group_result = await db.execute(
        select(WorkflowGroup).where(WorkflowGroup.id_hash == group_id)
    )
    group = group_result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    await exigir_papel_no_workspace(db, group.workspace_id, current_user.id_hash, ROLE_EDITOR)

    wf_result = await db.execute(
        select(Workflow).where(
            Workflow.id_hash == workflow_id,
            Workflow.group_id == group_id,
            Workflow.workspace_id == group.workspace_id,
        )
    )
    wf = wf_result.scalars().first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow não encontrado neste grupo")

    wf.group_id = None
    await db.commit()
