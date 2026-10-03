# app/services/artifact_service.py
"""
Listing of a workspace's artifacts, with no FastAPI in between.

The query was born whole inside `GET /artifacts` and stayed there because there
was only one caller. Now there are two: the screen and the MCP server, which goes
through no request at all. Copying the query into the second transport would
duplicate seven filters, the search escaping rule, the sort tie-breaker and the
decision about when to pay for the `outerjoin` — and the first time one of them
changed, the two would start giving different answers to the same question.

The boundary is the same one `app/core/authorization/workflow_access.py`
establishes for the guards: the rule becomes a function of `(db, ids, filtros)`,
and each transport plugs in its own port. The caller has already resolved WHO is
asking; here we resolve WHAT to answer.

What does **not** live here, on purpose: signing download URLs. The listing
returns `content_location` and `s3_key` and lets each transport decide — REST
hands out the link through another route, and MCP refuses a link for content
that sits on the executor, with `available=false`, instead of an error.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization.workflow_access import verify_workspace_access
from app.core.utils.busca import contem
from app.models.artifact import Artifact
from app.models.models import Workflow
from app.models.portal_layer import PortalLayer

# Hard page ceiling, mirroring the `le=200` the route declares in `Query`.
# Here it is clamped instead of validated: MCP has no Pydantic at the edge, and
# a large `limit` coming from a tool must not turn into a table scan.
LIMITE_MAXIMO = 200


def _filtros(
    workspace_ids: list[str],
    *,
    workspace_id: Optional[str],
    workflow_id: Optional[str],
    run_id: Optional[str],
    fmt: Optional[str],
    search: Optional[str],
    kind: Optional[str],
    include_pinned: bool,
) -> list:
    """The WHERE conditions, in the order the route used to build them."""
    # A specific workspace still has to be among the user's — the
    # parameter narrows the scope, never widens it.
    if workspace_id:
        verify_workspace_access(workspace_id, workspace_ids)
        filtros = [Artifact.workspace_id == workspace_id]
    else:
        filtros = [Artifact.workspace_id.in_(workspace_ids)]

    # Excludes pin-cache artifacts by default (they are internal to the system)
    if not include_pinned:
        filtros.append(Artifact.is_pinned != True)  # noqa: E712

    if workflow_id:
        filtros.append(Artifact.workflow_hash == workflow_id)
    if run_id:
        filtros.append(Artifact.run_id == run_id)
    if fmt:
        filtros.append(Artifact.format == fmt)
    # The screen's tabs. The criterion is the same one the client applied to the
    # whole list (`is_published || is_portal_active`, and the second implies the
    # first) — now in SQL, because filtering on the client required the whole list.
    if kind == "publication":
        filtros.append(Artifact.is_published == True)  # noqa: E712
    elif kind == "execution":
        filtros.append(Artifact.is_published == False)  # noqa: E712

    if search:
        # The user's `%` and `_` are literals, not wildcards (see `contem`).
        # `Workflow.name` is part of the search because the 'Workflow' column is
        # the most visible one in the table: when the search ran on the client it
        # matched all three fields, and when it was pushed down to SQL the workflow
        # name was left out — typing 'Cadastro Ambiental' returned "Nenhum
        # artefato encontrado" (no artifact found) with that workflow's rows
        # visible a second earlier. And no partial degradation is possible: the
        # page no longer keeps the whole collection.
        filtros.append(or_(
            contem(Artifact.filename, search),
            contem(Artifact.output_key, search),
            contem(Workflow.name, search),
        ))

    return filtros


def _item(
    artefato: Artifact,
    nome_do_workflow: Optional[str],
    portal_run_ids: set,
    *,
    incluir_chave: bool,
) -> dict:
    """One row of the response, with the defensive `getattr`s the route already had.

    `incluir_chave` exists so that the extraction does not change what the screen
    receives. The `s3_key` is what lets us decide whether there is an object to
    sign — MCP needs it, the interface does not, and adding it to the REST
    response would widen a contract as a side effect of a refactor.
    """
    return {
        "id_hash":        artefato.id_hash,
        "workspace_id":   artefato.workspace_id,
        "workflow_id":    artefato.workflow_hash,
        "workflow_name":  nome_do_workflow or artefato.workflow_hash or "",
        "run_id":         artefato.run_id,
        "node_id":        artefato.node_id,
        "output_key":     artefato.output_key,
        "filename":       artefato.filename,
        "format":         artefato.format,
        "size_bytes":     artefato.size_bytes,
        "features":       artefato.features,
        "protected":          artefato.credential_id is not None,
        "is_published":       getattr(artefato, "is_published", False),
        "is_portal_active":   getattr(artefato, "is_published", False)
        and artefato.run_id in portal_run_ids,
        "executor_id":           getattr(artefato, "executor_id", None),
        # Without this the UI cannot tell a local artifact apart: not for
        # the badge, not to explain that the download does not exist, not to
        # show that a removal is pending until the executor comes back.
        # `expires_at` in the past + local = being removed.
        "content_location":   getattr(artefato, "content_location", "minio"),
        "is_pinned":          getattr(artefato, "is_pinned", False),
        "created_at":         artefato.created_at.isoformat() if artefato.created_at else None,
        "expires_at":         artefato.expires_at.isoformat() if artefato.expires_at else None,
        **({"s3_key": getattr(artefato, "s3_key", None)} if incluir_chave else {}),
    }


async def listar_artefatos(
    db: AsyncSession,
    workspace_ids: list[str],
    *,
    workspace_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    run_id: Optional[str] = None,
    fmt: Optional[str] = None,
    search: Optional[str] = None,
    kind: Optional[str] = None,
    include_pinned: bool = False,
    limit: int = 50,
    offset: int = 0,
    incluir_chave: bool = False,
) -> dict[str, Any]:
    """Page of artifacts from the given workspaces, with a consistent `total`.

    `workspace_ids` is the list the caller has already worked out — the route via
    the dependency, MCP via the token's scope. This function does not discover it
    on its own, and that is why it has no way to leak across accounts: whatever is
    not in the list does not enter the WHERE.

    `include_pinned` defaults to `False` because a pin-cache artifact is internal
    engine state, not output someone asked for.
    """
    limite = max(1, min(int(limit), LIMITE_MAXIMO))
    salto = max(0, int(offset))

    filtros = _filtros(
        workspace_ids,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        run_id=run_id,
        fmt=fmt,
        search=search,
        kind=kind,
        include_pinned=include_pinned,
    )

    # The join only comes in when there is a search — the count without `search`
    # does not need it. `Workflow.id_hash` is unique, so the outerjoin does not
    # multiply rows and the count keeps matching the page.
    count_query = select(func.count(Artifact.id))
    if search:
        count_query = count_query.outerjoin(Workflow, Workflow.id_hash == Artifact.workflow_hash)
    total = (await db.execute(count_query.where(*filtros))).scalar() or 0

    query = (
        select(Artifact, Workflow.name.label("workflow_name"))
        .outerjoin(Workflow, Workflow.id_hash == Artifact.workflow_hash)
        .where(*filtros)
        .order_by(Artifact.created_at.desc(), Artifact.id.desc())
        .limit(limite)
        .offset(salto)
    )

    rows = (await db.execute(query)).all()

    # run_ids active on the portal, only to mark which version is published.
    # PERF: scoped to the run_ids of this results page. Before, it scanned the
    # WHOLE portal_layers table (all workspaces) on every request just to build
    # this set.
    run_ids = {a.run_id for a, _ in rows if a.run_id}
    portal_run_ids: set[str] = set()
    if run_ids:
        portal_result = await db.execute(
            select(PortalLayer.run_id).where(PortalLayer.run_id.in_(run_ids))
        )
        portal_run_ids = {row[0] for row in portal_result.fetchall()}

    items = [_item(a, nome, portal_run_ids, incluir_chave=incluir_chave) for a, nome in rows]

    return {
        "items":  items,
        "total":  total,
        "limit":  limite,
        "offset": salto,
        "has_more": salto + len(items) < total,
    }
