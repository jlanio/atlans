# app/core/authorization/workflow_access.py
"""
Autorização de workflows e workspaces — a casa das guardas, sem FastAPI `Depends`.

Até aqui as regras de acesso (workspace do recurso, papel mínimo, workflow
apagado) viviam só nas dependencies e nos routers da REST. Um segundo
transporte — o servidor MCP (docs/specs/mcp-server.md §1) — precisa das
MESMAS regras sem passar por uma request FastAPI. Este módulo é a única
implementação; `app/api/dependencies.py` importa daqui e re-exporta os nomes
antigos, então nenhum router muda.

As respostas continuam `HTTPException` com os status e mensagens de sempre —
o MCP as traduz para o seu erro de ferramenta. Divergências que existem de
propósito e ficam preservadas:
- workflow inexistente ou apagado (`deleted_at`) é 404 ANTES de qualquer 403
  (não revela se o id existe em outro workspace);
- `verify_workspace_access` dá 403 (não 404) para recurso sem workspace;
- execução (`WorkflowRun`) se autoriza pelo workspace DO RUN, não pelo atual do
  workflow — um workflow movido não entrega o histórico antigo ao novo workspace;
- `owner` está acima de `admin` na hierarquia de workspace.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowNotFoundError
from app.core.rbac import ROLE_OWNER
from app.models.workspace import Workspace

# ── Papéis de workspace ───────────────────────────────────────────────────────

WORKSPACE_ROLE_ORDER: List[str] = ["viewer", "editor", "operator", "admin", ROLE_OWNER]


def _has_min_workspace_role(actual: Optional[str], minimum: str) -> bool:
    """True se `actual` >= `minimum` na hierarquia de papéis do workspace."""
    if actual is None:
        return False
    try:
        return WORKSPACE_ROLE_ORDER.index(actual) >= WORKSPACE_ROLE_ORDER.index(minimum)
    except ValueError:
        return False


tem_papel_minimo = _has_min_workspace_role


def exigir_papel(role: Optional[str], minimo: str, mensagem: Optional[str] = None) -> None:
    """403 se o papel não alcança o mínimo. A mensagem é a da rota, quando ela tem uma própria.

    A comparação de papel das rotas passa toda por aqui: a REST pela dependência
    `workflow_com_papel` e por `exigir_papel_no_workspace`, o MCP direto.
    """
    if not _has_min_workspace_role(role, minimo):
        raise HTTPException(
            status_code=403,
            detail=mensagem or f"Requer role '{minimo}' ou superior.",
        )


# ── Pertencimento a workspace ─────────────────────────────────────────────────


def verify_workspace_access(resource_workspace_id: Optional[str], user_workspace_ids: List[str]) -> None:
    """
    Lança HTTP 403 se o resource não pertence a nenhum workspace do usuário.
    Recursos sem workspace_id são bloqueados — devem ser migrados para ter workspace explícito.
    """
    if not resource_workspace_id:
        raise HTTPException(
            status_code=403,
            detail="Recurso sem workspace associado. Contate o administrador para migração.",
        )
    if resource_workspace_id not in user_workspace_ids:
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")


async def listar_workspace_ids(db: AsyncSession, user_id: str) -> List[str]:
    """id_hash dos workspaces acessíveis ao usuário: dono OU membro, nunca da lixeira.

    UMA query em vez de dois round-trips. Membros sobrevivem ao soft delete (a FK
    CASCADE só dispara no purge), então o filtro de `deleted_at` no Workspace
    externo vale para os dois casos — senão um workspace na lixeira continuaria
    dando acesso a artefatos, Drive e logs.
    """
    from app.models.workspace_member import WorkspaceMember

    resultado = await db.execute(
        select(Workspace.id_hash).where(
            Workspace.deleted_at.is_(None),
            or_(
                Workspace.owner_id == user_id,
                Workspace.id_hash.in_(
                    select(WorkspaceMember.workspace_id).where(
                        WorkspaceMember.user_id == user_id,
                    )
                ),
            ),
        )
    )
    return [row[0] for row in resultado.all()]


async def get_workspace_member_role(
    db: AsyncSession, workspace_id: str, user_id: str
) -> Optional[str]:
    """
    Retorna o role efetivo do usuário no workspace:
    - "owner" se for dono do workspace
    - o role do WorkspaceMember se for membro
    - None se não tiver acesso (ou se o workspace está na lixeira)
    """
    from app.models.workspace_member import WorkspaceMember

    ws_result = await db.execute(
        select(Workspace.owner_id).where(
            Workspace.id_hash == workspace_id,
            Workspace.deleted_at.is_(None),
        )
    )
    owner_id = ws_result.scalar_one_or_none()
    if owner_id is None:
        return None
    if owner_id == user_id:
        return ROLE_OWNER

    member_result = await db.execute(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    return member_result.scalar_one_or_none()


async def exigir_papel_no_workspace(
    db: AsyncSession,
    workspace_id: Optional[str],
    user_id: str,
    minimo: str,
    mensagem: Optional[str] = None,
) -> str:
    """Papel do usuário no workspace — ou 403 se ele não alcança `minimo`.

    É a dupla "busca o papel + compara" das rotas cujo workspace vem do corpo ou
    do recurso (grupos, membros, artefatos, Drive, criação de workflow): escrita
    à mão, ela se repetia rota a rota, e uma cópia esquecida é uma rota sem
    papel. Quem não é membro (ou workspace inexistente, ou na lixeira) cai no
    mesmo 403 — `get_workspace_member_role` devolve None nos três, e distinguir
    permitiria enumerar workspaces alheios pelo id.

    Rotas que carregam um WORKFLOW pelo path usam a dependência
    `workflow_com_papel` (app/api/dependencies.py), que também dá o 404 antes.
    """
    papel = await get_workspace_member_role(db, workspace_id, user_id)
    exigir_papel(papel, minimo, mensagem)
    return papel


# ── Workflows e execuções ─────────────────────────────────────────────────────


async def carregar_workflow_acessivel(
    service,
    db: AsyncSession,
    id_hash: str,
    user_id: str,
    *,
    decifrar: bool = True,
    aceitar_sem_papel: bool = False,
) -> Tuple[object, Optional[str]]:
    """(workflow, papel) — ou 404 se não existe/apagado, 403 se o usuário não está no workspace.

    `service` é um `WorkflowService`. Com `decifrar=True` (a REST) o workflow vem
    de `get_workflow_by_hash`, que descriptografa as `connectionString` e as
    atribui em `wf.definition`. Com `decifrar=False` vem cru de `crud.get_by_hash`:
    é o caminho de quem só vai ler metadados, redigir a definition ou executar —
    ninguém precisa do segredo em claro na sessão, e uma definition decifrada
    presa a um ORM dirty é exatamente o que um flush acidental vazaria. As
    regras de acesso são as mesmas nos dois caminhos.

    A ordem 404-antes-de-403 é deliberada: não revela se o id existe em outro
    workspace.
    """
    if decifrar:
        try:
            wf = await service.get_workflow_by_hash(id_hash)
        except WorkflowNotFoundError:
            raise HTTPException(status_code=404, detail=f"Workflow '{id_hash}' não encontrado")
    else:
        wf = await service.crud.get_by_hash(id_hash)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{id_hash}' não encontrado")
    if wf.deleted_at is not None:
        raise HTTPException(status_code=404, detail=f"Workflow '{id_hash}' não encontrado")
    role = await get_workspace_member_role(db, wf.workspace_id, user_id)
    if role is None:
        # Membro de workspace SEM dono (`owner_id` nulo: dado antigo ou editado
        # à mão) não tem papel, porque `get_workspace_member_role` sai cedo sem
        # dono. Mas pertence ao workspace, como diz `listar_workspace_ids`, e a
        # listagem mostra o fluxo a ele. Com `aceitar_sem_papel` (a REST), ele
        # recebe (wf, None): a leitura passa, e toda rota com papel mínimo o
        # recusa, como antes da guarda única.
        if aceitar_sem_papel and wf.workspace_id in await listar_workspace_ids(db, user_id):
            return wf, None
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
    return wf, role


async def papel_no_workspace_do_run(db: AsyncSession, run, user_id: str) -> Optional[str]:
    """Papel do usuário no workspace em que a execução de fato rodou (`run.workspace_id`).

    É o critério de cancelar/ver uma execução: um workflow pode ter sido movido
    depois do disparo, e quem controla o workspace novo não manda no histórico
    do antigo. Sem bypass de admin global — quem quiser esse atalho o faz na
    rota, explicitamente, como hoje.
    """
    return await get_workspace_member_role(db, run.workspace_id, user_id)
