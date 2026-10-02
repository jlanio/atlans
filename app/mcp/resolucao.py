# app/mcp/resolucao.py
"""
Resolver "o que o cliente escreveu" para "o recurso que ele pode alcançar".

Quem conversa com um servidor MCP escreve o nome que vê na tela ("Produção",
"Recorte mensal"), não um identificador de 36 caracteres. Aceitar os dois é o
que torna as tools utilizáveis; fazê-lo sem abrir buraco de autorização é o
motivo deste módulo existir em vez de um `if` em cada tool.

Três regras que valem para tudo aqui:

1. **Ambiguidade é recusa, nunca escolha.** Dois workflows com o mesmo nome em
   workspaces diferentes viram `ambiguous` com a lista de candidatos; adivinhar
   "o primeiro" faria a tool agir sobre um recurso que ninguém apontou.
2. **Não existe e não alcanço respondem igual.** Para um workflow, o id que não
   existe e o id que existe no workspace de outra conta saem com o mesmo `code`
   e a mesma frase: a diferença seria um oráculo de existência entre inquilinos,
   e um cliente MCP tem o laço pronto para varrer identificadores. O núcleo
   continua devolvendo 404 e 403 separados — é o que a REST usa —; a conversão
   acontece aqui, na borda. A busca por nome chega ao mesmo lugar por outro
   caminho: filtra pelo escopo ANTES de contar resultados.
3. **O escopo do token corta antes do papel do usuário.** Um token emitido para
   um workspace só não enxerga os outros nem quando o dono é administrador da
   plataforma. Por isso a checagem de `escopo.workspace_ids` acontece sobre o
   resultado da autorização de usuário, e não no lugar dela: as duas valem, e a
   mais restritiva vence.
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
    """True se o texto é um UUID — o formato dos `id_hash` do Atlans.

    Serve para decidir "isto é um id ou um nome?". Um nome que por acaso seja um
    UUID válido é caso de laboratório; se acontecer, o valor é tratado como id,
    que é a leitura mais previsível.
    """
    try:
        uuid.UUID(str(valor))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


# A recusa de "não encontrado" de um workflow é UMA só, em texto e em código,
# venha ela de um id que não existe, de um id que existe em workspace alheio ou
# de um nome desconhecido. Dois textos diferentes para o mesmo `not_found`
# reabririam pelo corpo da mensagem o oráculo que o código fechou: quem variasse
# o id e lesse a frase saberia quais deles existem do outro lado do muro. A
# mensagem também não ecoa a referência recebida, pelo mesmo motivo.
MSG_WORKFLOW_NAO_ENCONTRADO = "Nenhum workflow com esta referência está ao alcance do token."
HINT_WORKFLOW_NAO_ENCONTRADO = "use list_workflows para ver o que este token alcança"


def _workflow_nao_encontrado():
    return erro("not_found", MSG_WORKFLOW_NAO_ENCONTRADO, HINT_WORKFLOW_NAO_ENCONTRADO)


def _candidatos(linhas) -> list:
    """Candidatos de um erro `ambiguous`: id no topo, nome higienizado."""
    return [{"id": id_hash, "name": scrub_text(str(nome or ""))} for id_hash, nome in linhas]


async def resolver_workspace(db: AsyncSession, escopo: EscopoEfetivo, ref: str | None) -> str:
    """O `id_hash` do workspace que a chamada indicou — id, nome ou omissão.

    Omitir é legítimo quando o token alcança um workspace só: pedir o parâmetro
    nesse caso é burocracia. Com dois ou mais, a omissão vira `ambiguous` com a
    lista — o cliente escolhe, o servidor não.
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

    # Nada dentro do alcance. Um id é recusado como "proibido" sem consultar o
    # banco: dizer "não existe" para um id de outro dono revelaria, pela
    # diferença, quando ele existe. Um nome é "não encontrado" — nomes não
    # identificam recurso de terceiro.
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
    """`(workflow, papel)` a partir de um id ou de um nome.

    `decifrar=False` é o default de propósito: quase toda tool lê metadados ou
    devolve a definition redigida, e uma definition decifrada presa a uma linha
    viva da sessão é exatamente o que um flush acidental grava em claro no banco.

    A checagem do escopo do token vem DEPOIS da autorização do usuário e é
    independente dela: quem passa por uma pode ser barrado pela outra.
    """
    referencia = str(ref).strip()
    servico = WorkflowService(db)

    if e_uuid(referencia):
        try:
            wf, papel = await carregar_workflow_acessivel(
                servico, db, referencia, escopo.user_id, decifrar=decifrar
            )
        except HTTPException as exc:
            # O núcleo responde em HTTP e separa os dois casos: 404 para o id que
            # não existe, 403 para o id que existe num workspace de outra conta.
            # Essa diferença é a resposta a uma pergunta que ninguém deveria
            # poder fazer aqui — "este identificador existe?" —, e um cliente MCP
            # tem justamente o laço para varrer ids. A REST mantém o 403 (é o
            # mesmo módulo do núcleo, usado pelos routers); a conversão vale só
            # nesta borda, e é para o MESMO `not_found` da busca por nome, texto
            # incluído: um código igual com frase diferente continuaria contando.
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
        # Inclui o caso "existe, mas fora do alcance": o filtro do escopo entra
        # na consulta, então a resposta não distingue um do outro.
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
    """O alcance do TOKEN, conferido antes de qualquer leitura de papel."""
    if workspace_id in escopo.workspace_ids:
        return
    raise erro(
        "forbidden",
        "Este token não alcança o workspace deste recurso.",
        "use list_workspaces para ver o que este token alcança",
    )
