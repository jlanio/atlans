# app/mcp/resolucao.py
"""
Resolving "what the client wrote" into "the resource it is allowed to reach".

Whoever talks to an MCP server writes the name they see on screen ("Produção",
"Recorte mensal"), not a 36-character identifier. Accepting both is what makes
the tools usable; doing so without opening an authorization hole is the reason
this module exists instead of an `if` in every tool.

Three rules that hold for everything here:

1. **Ambiguity is refusal, never choice.** Two workflows with the same name in
   different workspaces become `ambiguous` with the list of candidates;
   guessing "the first one" would make the tool act on a resource nobody
   pointed at.
2. **Does not exist and cannot reach answer the same.** For a workflow, the id
   that does not exist and the id that exists in another account's workspace
   come out with the same `code` and the same sentence: the difference would be
   an existence oracle between tenants, and an MCP client has the loop ready to
   sweep identifiers. The core keeps returning separate 404 and 403 — that is
   what REST uses —; the conversion happens here, at the edge. Lookup by name
   reaches the same place by another path: it filters by scope BEFORE counting
   results.
3. **The token's scope cuts before the user's role.** A token issued for a
   single workspace does not see the others even when its owner is a platform
   administrator. That is why the `escopo.workspace_ids` check happens on top of
   the result of user authorization, not in place of it: both apply, and the
   more restrictive one wins.
"""
from __future__ import annotations

import uuid
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization.workflow_access import (
    carregar_workflow_acessivel,
    get_workspace_member_role,
)
from app.core.utils.logger import scrub_text
from app.mcp.erros import erro, to_tool_error
from app.mcp.escopo import EscopoEfetivo
from app.models.workflow import Workflow
from app.models.workspace import Workspace
from app.services.workflow_service import WorkflowService


def e_uuid(valor) -> bool:
    """True if the text is a UUID — the format of Atlans `id_hash` values.

    Used to decide "is this an id or a name?". A name that happens to be a
    valid UUID is a lab case; if it happens, the value is treated as an id,
    which is the most predictable reading.
    """
    try:
        uuid.UUID(str(valor))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


# A workflow's "not found" refusal is a SINGLE one, in text and in code, whether
# it comes from an id that does not exist, an id that exists in someone else's
# workspace or an unknown name. Two different texts for the same `not_found`
# would reopen through the message body the oracle that the code closed:
# whoever varied the id and read the sentence would learn which ones exist on
# the other side of the wall. The message also does not echo the reference
# received, for the same reason.
MSG_WORKFLOW_NAO_ENCONTRADO = "Nenhum workflow com esta referência está ao alcance do token."
HINT_WORKFLOW_NAO_ENCONTRADO = "use list_workflows para ver o que este token alcança"


def _workflow_nao_encontrado():
    return erro("not_found", MSG_WORKFLOW_NAO_ENCONTRADO, HINT_WORKFLOW_NAO_ENCONTRADO)


def _candidatos(linhas) -> list:
    """Candidates for an `ambiguous` error: id at the top level, sanitized name."""
    return [{"id": id_hash, "name": scrub_text(str(nome or ""))} for id_hash, nome in linhas]


async def resolver_workspace(db: AsyncSession, escopo: EscopoEfetivo, ref: str | None) -> str:
    """The `id_hash` of the workspace the call indicated — id, name or omission.

    Omitting it is legitimate when the token reaches a single workspace: asking
    for the parameter in that case is red tape. With two or more, the omission
    becomes `ambiguous` with the list — the client chooses, the server does
    not.
    """
    alcance = escopo.workspace_ids
    if not alcance:
        raise erro(
            "forbidden",
            "Este token não alcança nenhum workspace.",
            "peça acesso a um workspace, ou crie em /settings/tokens um token sem "
            "restrição de workspace (hoje, página só de administradores do sistema)",
        )

    if ref is None:
        unico = escopo.workspace_unico()
        if unico:
            return unico
        raise erro(
            "ambiguous",
            "Este token alcança mais de um workspace: informe workspace_id.",
            "escolha um dos candidates e repita a chamada",
            candidates=_candidatos(await _workspaces_do_escopo(db, alcance)),
        )

    referencia = str(ref).strip()
    if referencia in alcance:
        return referencia

    resultado = await db.execute(
        select(Workspace.id_hash, Workspace.name).where(
            Workspace.name == referencia,
            Workspace.deleted_at.is_(None),
            Workspace.id_hash.in_(list(alcance)),
        )
    )
    achados = resultado.all()
    if len(achados) == 1:
        return achados[0][0]
    if len(achados) > 1:
        raise erro(
            "ambiguous",
            "Mais de um workspace atende por este nome.",
            "use o id do workspace desejado",
            candidates=_candidatos(achados),
        )

    # Nothing within reach. An id is refused as "forbidden" without querying
    # the database: saying "does not exist" for an id of another owner would
    # reveal, by the difference, when it does exist. A name is "not found" —
    # names do not identify a third party's resource.
    if e_uuid(referencia):
        raise erro(
            "forbidden",
            "Este token não alcança o workspace informado.",
            "use list_workspaces para ver o que este token alcança",
        )
    raise erro(
        "not_found",
        "Nenhum workspace com este nome está ao alcance do token.",
        "use list_workspaces para ver os nomes disponíveis",
    )


async def _workspaces_do_escopo(db: AsyncSession, alcance) -> list:
    resultado = await db.execute(
        select(Workspace.id_hash, Workspace.name)
        .where(Workspace.id_hash.in_(list(alcance)), Workspace.deleted_at.is_(None))
        .order_by(Workspace.name)
    )
    return resultado.all()


async def carregar_workflow(
    db: AsyncSession, escopo: EscopoEfetivo, ref: str, *, decifrar: bool = False
) -> Tuple[object, str]:
    """`(workflow, papel)` (workflow, role) from an id or a name.

    `decifrar=False` is the default on purpose: almost every tool reads
    metadata or returns the redacted definition, and a decrypted definition
    tied to a live session row is exactly what an accidental flush writes in
    plaintext to the database.

    The token scope check comes AFTER user authorization and is independent of
    it: whoever passes one may be stopped by the other.
    """
    referencia = str(ref).strip()
    servico = WorkflowService(db)

    if e_uuid(referencia):
        try:
            wf, papel = await carregar_workflow_acessivel(
                servico, db, referencia, escopo.user_id, decifrar=decifrar
            )
        except HTTPException as exc:
            # The core answers in HTTP and separates the two cases: 404 for the id
            # that does not exist, 403 for the id that exists in another
            # account's workspace. That difference is the answer to a question
            # nobody should be able to ask here — "does this identifier
            # exist?" —, and an MCP client has precisely the loop to sweep ids.
            # REST keeps the 403 (it is the same core module, used by the
            # routers); the conversion applies only at this edge, and it is to
            # the SAME `not_found` as the name lookup, text included: an
            # identical code with a different sentence would still tell.
            if exc.status_code in (403, 404):
                raise _workflow_nao_encontrado() from exc
            raise to_tool_error(exc) from exc
        _exigir_workspace_no_escopo(wf.workspace_id, escopo)
        return wf, papel

    resultado = await db.execute(
        select(Workflow).where(
            Workflow.name == referencia,
            Workflow.deleted_at.is_(None),
            Workflow.workspace_id.in_(list(escopo.workspace_ids)),
        )
    )
    achados = list(resultado.scalars().all())
    if not achados:
        # Includes the "exists, but out of reach" case: the scope filter goes
        # into the query, so the answer does not tell one from the other.
        raise _workflow_nao_encontrado()
    if len(achados) > 1:
        raise erro(
            "ambiguous",
            "Mais de um workflow atende por este nome.",
            "use o id do workflow desejado",
            candidates=[
                {
                    "id": wf.id_hash,
                    "workspace_id": wf.workspace_id,
                    "name": scrub_text(str(wf.name or "")),
                }
                for wf in achados
            ],
        )

    wf = achados[0]
    _exigir_workspace_no_escopo(wf.workspace_id, escopo)
    papel = await get_workspace_member_role(db, wf.workspace_id, escopo.user_id)
    if papel is None:
        raise erro("forbidden", "Acesso negado a este workflow.")
    return wf, papel


def _exigir_workspace_no_escopo(workspace_id: str | None, escopo: EscopoEfetivo) -> None:
    """The TOKEN's reach, checked before any role lookup."""
    if workspace_id in escopo.workspace_ids:
        return
    raise erro(
        "forbidden",
        "Este token não alcança o workspace deste recurso.",
        "use list_workspaces para ver o que este token alcança",
    )
