# app/services/artifact_service.py
"""
Listagem de artefatos de um workspace, sem FastAPI no meio.

A consulta nasceu inteira dentro de `GET /artifacts` e ficou lá porque só havia
um chamador. Agora há dois: a tela e o servidor MCP, que não passa por request
nenhuma. Copiar a consulta para o segundo transporte duplicaria sete filtros, a
regra de escape da busca, o desempate da ordenação e a decisão de quando pagar
o `outerjoin` — e a primeira vez que um deles mudasse, os dois passariam a
responder coisas diferentes para a mesma pergunta.

A fronteira é a mesma que `app/core/authorization/workflow_access.py` estabelece
para as guardas: a regra vira função de `(db, ids, filtros)`, e cada transporte
encaixa a própria porta. Quem chama já resolveu QUEM pergunta; aqui se resolve
O QUE responder.

O que **não** mora aqui, de propósito: assinar URL de download. A listagem
devolve `content_location` e `s3_key` e deixa cada transporte decidir — a REST
dá o link por outra rota, e o MCP recusa link para conteúdo que está no
executor, com `available=false`, em vez de erro.
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

# Teto duro da página, espelhando o `le=200` que a rota declara no `Query`.
# Aqui ele é grampeado em vez de validado: o MCP não tem Pydantic na borda, e
# um `limit` grande vindo de uma tool não pode virar varredura de tabela.
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
    """As condições do WHERE, na ordem em que a rota as montava."""
    # Um workspace específico ainda tem de estar entre os do usuário — o
    # parâmetro estreita o escopo, nunca o amplia.
    if workspace_id:
        verify_workspace_access(workspace_id, workspace_ids)
        filtros = [Artifact.workspace_id == workspace_id]
    else:
        filtros = [Artifact.workspace_id.in_(workspace_ids)]

    # Exclui artefatos de pin-cache por padrao (sao internos do sistema)
    if not include_pinned:
        filtros.append(Artifact.is_pinned != True)  # noqa: E712

    if workflow_id:
        filtros.append(Artifact.workflow_hash == workflow_id)
    if run_id:
        filtros.append(Artifact.run_id == run_id)
    if fmt:
        filtros.append(Artifact.format == fmt)
    # As abas da tela. O critério é o mesmo que o cliente aplicava sobre a lista
    # inteira (`is_published || is_portal_active`, e o segundo implica o
    # primeiro) — agora no SQL, porque filtrar no cliente exigia a lista inteira.
    if kind == "publication":
        filtros.append(Artifact.is_published == True)  # noqa: E712
    elif kind == "execution":
        filtros.append(Artifact.is_published == False)  # noqa: E712

    if search:
        # `%` e `_` do usuario sao literais, nao curingas (ver `contem`).
        # `Workflow.name` faz parte da busca porque a coluna 'Workflow' e a mais
        # visivel da tabela: quando a busca era no cliente ela casava com os tres
        # campos, e ao empurra-la para o SQL o nome do fluxo ficou de fora —
        # digitar 'Cadastro Ambiental' devolvia "Nenhum artefato encontrado" com
        # as linhas daquele fluxo visiveis um segundo antes. E nao ha degradacao
        # parcial possivel: a pagina nao guarda mais a colecao inteira.
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
    """Uma linha da resposta, com os `getattr` defensivos que a rota já tinha.

    `incluir_chave` existe para que a extração não mude o que a tela recebe. A
    `s3_key` é o que permite decidir se há objeto a assinar — o MCP precisa
    dela, a interface não, e acrescentá-la à resposta da REST seria alargar um
    contrato por efeito colateral de um refactor.
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
        # Sem isto a UI nao consegue distinguir um artefato local: nem para
        # o badge, nem para explicar que o download nao existe, nem para
        # mostrar que uma remocao ficou pendente do executor voltar.
        # `expires_at` no passado + local = removendo.
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
    """Página de artefatos dos workspaces recebidos, com `total` coerente.

    `workspace_ids` é a lista que quem chama já apurou — a rota pela dependency,
    o MCP pelo escopo do token. Esta função não a descobre sozinha, e é por isso
    que ela não tem como vazar entre contas: o que não estiver na lista não entra
    no WHERE.

    `include_pinned` entra `False` por padrão porque artefato de pin-cache é
    estado interno do motor, não saída que alguém pediu.
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

    # O join so entra quando ha busca — a contagem sem `search` nao precisa dele.
    # `Workflow.id_hash` e unico, entao o outerjoin nao multiplica linhas e a
    # contagem continua batendo com a pagina.
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

    # run_ids ativos no portal, apenas para marcar qual versao esta publicada.
    # PERF: escopado aos run_ids desta pagina de resultados. Antes varria TODA a
    # tabela portal_layers (todos os workspaces) a cada request so pra montar
    # este set.
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
