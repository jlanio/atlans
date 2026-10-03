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


# ── Resolution of groupable workflows ────────────────────────────────────────
#
# The four routes that write `Workflow.group_id` check the user's role
# in the GROUP's workspace. Resolving the workflow only by `id_hash` let an editor
# drag a workflow from ANOTHER tenant into their own group — and then
# zero out `group_id` in bulk via DELETE. The workspace matching lives
# here so it cannot diverge between them again.
#
# `flag_ative` is NOT part of the criterion, on purpose: grouping is organization, not
# execution, and a deactivated workflow still shows up on the Projects screen.
# Filtering by it made an item the user had just checked in the list vanish
# from the result — and, with the explicit refusal below, bring down the whole creation
# with "nao encontrado" (not found). `deleted_at` is included: what is in the trash
# is not a target.


def _alvos_agrupaveis(workflow_ids, group) -> list:
    """Conditions a workflow must satisfy to enter this group."""
    return [
        Workflow.id_hash.in_(workflow_ids),
        Workflow.workspace_id == group.workspace_id,
        Workflow.deleted_at.is_(None),
    ]


def _recusar_ids_fora_do_grupo(pedidos, encontrados) -> None:
    """404 for an id that does not exist, is in the trash or belongs to another workspace.

    Refuse, rather than silently ignore: writing only the known part would leave the
    screen and the database diverging — same criterion as `reorder_groups`. The message
    does not distinguish "does not exist" from "belongs to another tenant", so as not
    to become an id_hash enumeration oracle.
    """
    desconhecidos = set(pedidos) - {wf.id_hash for wf in encontrados}
    if desconhecidos:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow(s) não encontrado(s) neste workspace: {', '.join(sorted(desconhecidos))}",
        )


# ── Group counts ─────────────────────────────────────────────────────────────
#
# `workflow_count` counts ALL non-deleted workflows in the group, and
# `active_count` only those with `flag_ative`. Before, only the active ones were
# counted, and the screen said "2 workflows" in a group of 3 when one was deactivated —
# the inactive one stays in the list, so the count has to match what is seen.
# A single aggregation, with `sum(case …)` instead of `count(*) FILTER`, so it works
# the same in the tests' SQLite and in PostgreSQL.


async def _contagens_por_grupo(db: AsyncSession, group_ids: list[str]) -> dict[str, tuple[int, int]]:
    """Group id_hash -> (workflow_count, active_count). A group without workflows
    does not appear in the dict; the reader uses (0, 0)."""
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
    """Serializes a group with both counts — the single-group routes
    (create, update) go through here so they do not diverge from the listing."""
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

    # End of the line: without this every new group is born at `position=0`, tied
    # with the existing ones, and the order among them again depends on the tiebreak.
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
    await db.flush()  # generates id_hash before linking workflows

    # Links workflows to the group. The workspace filter lives in the `select` (and not
    # in a check afterwards) so it works the same in the four routes that touch
    # `Workflow.group_id` — that was the divergence that opened cross-tenant writes.
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

    # `name` breaks ties: two equal positions (groups created before the column
    # existed, or an interrupted reordering) would again come out in undefined
    # order, which is exactly the defect the position came to fix.
    stmt = stmt.order_by(WorkflowGroup.position, WorkflowGroup.name)

    result = await db.execute(stmt)
    groups = result.scalars().all()

    # Both counts for all groups in one query
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
    """Saves the order of the groups, in the sequence received.

    Declared BEFORE `/{group_id}`: FastAPI matches routes in registration
    order, and the variable path would swallow "reorder" as if it were an id.
    """
    result = await db.execute(
        select(WorkflowGroup).where(WorkflowGroup.id_hash.in_(payload.group_ids))
    )
    grupos = {g.id_hash: g for g in result.scalars().all()}

    # Refuse, rather than silently ignore: an id that does not exist or belongs to another
    # workspace means the screen is working with a list different from the
    # database's, and writing only the known part would leave the two diverging.
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

    # Updates the group's members
    if payload.workflow_ids is not None:
        # Removes all workflows from the group
        old_result = await db.execute(
            select(Workflow).where(
                Workflow.group_id == group_id,
                Workflow.workspace_id == group.workspace_id,
            )
        )
        for wf in old_result.scalars().all():
            wf.group_id = None

        # Adds the new ones, by the same criterion as `create_group`.
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

    # Unlinks workflows before deleting. The workspace filter prevents
    # deleting one's own group from touching another tenant's workflow.
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

    # Same criterion as the batch routes — see `_alvos_agrupaveis`.
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
