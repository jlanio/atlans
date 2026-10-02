# app/mcp/resources.py
"""
Resources do servidor (`atlans://…`) — leitura cacheável, sem efeito colateral.

Cada resource é **alias de uma tool de leitura**, e alias aqui é literal: o
handler chama a mesma função que a tool chama, e devolve o que ela devolveu.
Não há uma segunda consulta, uma segunda redação nem um segundo formato de
saída para manter em sincronia — a única diferença é a embalagem (texto ou
JSON) e o fato de o cliente poder anexar um resource ao contexto e reusá-lo,
em vez de gastar uma chamada.

Três regras valem para todo handler daqui:

1. **Mesma guarda das tools.** O escopo é conferido dentro da função da tool,
   que é quem chama `escopo_da_chamada` + `exigir_escopo`. Um resource não é
   porta dos fundos: sem escopo, sem leitura. O que este módulo acrescenta é a
   tradução do erro e, nos handlers que leem dados de workspace, a MESMA guarda
   cronometrada de `call_tool` (`guarda_da_chamada`) — sem ela a leitura por URI
   seria o único caminho do servidor que não deixa linha de auditoria, e é
   justamente o caminho que o cliente repete sem pensar.

   A cota fica isenta nos resources, e isso é decisão, não esquecimento: um
   resource é alias de uma tool que já tem balde, cobrar de novo o mesmo
   trabalho não mede nada. O que segura o laço é o balde geral do token.

   Catálogo e guia não passam pela guarda: são texto fixo da instalação, iguais
   para todo token, e não há dado de ninguém a registrar — a conferência de
   escopo deles continua dentro da tool.

2. **Erro anticipado vira `ResourceError`.** O SDK só preserva a mensagem de um
   `ResourceError` (ou `ResourceNotFoundError`); um `ToolError` escapando de um
   resource conta como crash, e o cliente receberia um texto genérico com a
   URI. Como o formato de erro do Atlans é o JSON `{code, message, hint}`, a
   tradução só troca a classe, mantendo o corpo.

3. **Nada decifrado.** Vem de graça por (1): as tools carregam o workflow com
   `decifrar=False` e redigem a definition antes de entregar.
"""
from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError

from app.mcp import guia
from app.mcp.erros import codigo_do_erro, to_tool_error
from app.mcp.escopo import escopo_da_chamada
from app.mcp.tools.base import guarda_da_chamada
from app.mcp.tools.catalogo import describe_node, get_authoring_guide, search_nodes
from app.mcp.tools.execucao import get_run
from app.mcp.tools.workflows import get_workflow, get_workflow_contract, list_workflows

# Sem `type`, o catálogo sai só como mapa de grupos. O índice inteiro passa de
# 10 KB e a ficha completa dos 63 nós, de 70 KB: entregar isso como um blob
# único num `resources/read` gasta o orçamento de contexto de quem lê antes de
# a conversa começar. A dica diz como chegar ao que interessa.
DICA_CATALOGO = (
    "Leia atlans://catalog/nodes?type=<tipo> para o índice de um grupo, ou "
    "atlans://catalog/nodes/<Nome> para a ficha completa de um nó."
)


def _json(dados: Any) -> str:
    """JSON legível por humano e por máquina — sem escapar acento."""
    return json.dumps(dados, ensure_ascii=False, default=str)


def _como_erro_de_resource(exc: Exception) -> ResourceError:
    """Traduz uma exceção para o erro de resource, sem perder o `code`.

    `to_tool_error` continua sendo a única tabela de tradução do MCP (um
    `ToolError` já formatado passa por ela intacto); aqui só se troca a classe,
    porque o SDK trata as duas famílias por caminhos diferentes.

    Só `Exception`, nunca `BaseException`: um `CancelledError` (o cliente
    desistiu, o servidor está encerrando) não é erro do recurso, e convertê-lo
    em `ResourceError` engoliria o cancelamento — a task seguiria viva e a
    resposta sairia como se o recurso tivesse falhado.
    """
    convertido = to_tool_error(exc)
    corpo = str(convertido)
    if codigo_do_erro(convertido) == "not_found":
        return ResourceNotFoundError(corpo)
    return ResourceError(corpo)


def registrar_resources(server) -> None:
    """Registra os resources na instância recebida.

    Função, e não decoradores no topo do módulo, porque `create_mcp_server` é
    uma fábrica: cada instância precisa dos seus próprios registros.
    """

    @server.resource(
        "atlans://guide/authoring/{topic}",
        name="guia_de_autoria",
        title="Guia de autoria de workflows",
        description=(
            "O guia de autoria, por tópico: "
            + ", ".join(guia.TOPICOS)
            + ". Mesmo texto da ferramenta get_authoring_guide."
        ),
        mime_type="text/markdown",
    )
    async def guia_de_autoria(topic: str, ctx: Context) -> str:
        """Alias de `get_authoring_guide`: um arquivo, dois caminhos de entrega.

        Devolve o markdown puro, e não o envelope da tool: o resource declara
        `text/markdown`, então o corpo é o documento.
        """
        try:
            return (await get_authoring_guide(ctx, topic=topic))["markdown"]
        except Exception as exc:
            raise _como_erro_de_resource(exc) from exc

    @server.resource(
        "atlans://catalog/nodes{?type}",
        name="catalogo_de_nos",
        title="Catálogo de nós",
        description=(
            "Sem 'type', os grupos de nós e quantos há em cada um. Com 'type', o índice "
            "compacto daquele grupo (nome, tipo, uma linha, se exige credencial)."
        ),
        mime_type="application/json",
    )
    async def catalogo_de_nos(ctx: Context, type: str | None = None) -> str:
        """O catálogo em duas camadas — nunca os 63 nós inteiros num blob só.

        O parâmetro se chama `type` porque é o nome da variável na URI, e o SDK
        casa os dois pelo nome.
        """
        try:
            resultado = await search_nodes(ctx, type=type)
            if not type:
                # Sem filtro, só o mapa de grupos: `items` é montado pela tool e
                # descartado aqui de propósito. Passar por ela mesmo assim é o
                # que garante que a guarda de escopo roda nos DOIS caminhos.
                return _json({
                    "types": resultado["types"],
                    "total": resultado["total"],
                    "hint": DICA_CATALOGO,
                })
            return _json({
                "type": type,
                "total": resultado["total"],
                "items": resultado["items"],
            })
        except Exception as exc:
            raise _como_erro_de_resource(exc) from exc

    @server.resource(
        "atlans://catalog/nodes/{name}",
        name="no_do_catalogo",
        title="Nó do catálogo",
        description="A ficha completa de um nó: propriedades, entradas, saídas e dicas.",
        mime_type="application/json",
    )
    async def no_do_catalogo(name: str, ctx: Context) -> str:
        """Um nó inteiro — o mesmo `describe_node(brief=false)`.

        Nome desconhecido vira 404, e um nó desabilitado na instalação responde
        igual a um inexistente: a tool já trata os dois como `not_found`.
        """
        try:
            return _json(await describe_node(ctx, name=name, brief=False))
        except Exception as exc:
            raise _como_erro_de_resource(exc) from exc

    @server.resource(
        "atlans://workspaces/{id}/workflows",
        name="workflows_do_workspace",
        title="Workflows de um workspace",
        description="A mesma listagem leve de list_workflows, fixada num workspace.",
        mime_type="application/json",
    )
    async def workflows_do_workspace(id: str, ctx: Context) -> str:
        """Listagem leve — sem definition, sem params_schema, sem segredo."""
        try:
            escopo = escopo_da_chamada(ctx)
            async with guarda_da_chamada(
                "list_workflows", escopo, cobrar_cota=False, origem="resource"
            ):
                return _json(await list_workflows(ctx, workspace_id=id))
        except Exception as exc:
            raise _como_erro_de_resource(exc) from exc

    @server.resource(
        "atlans://workflows/{id}",
        name="workflow",
        title="Workflow",
        description="Um workflow e a sua definition REDIGIDA (segredo vira <REDACTED>).",
        mime_type="application/json",
    )
    async def workflow(id: str, ctx: Context) -> str:
        """O fluxo como referência: dá para ler a fiação, nunca a credencial.

        `include_definition=True` porque é disso que vive um resource — quem só
        quer o cabeçalho chama a tool com o default.
        """
        try:
            escopo = escopo_da_chamada(ctx)
            async with guarda_da_chamada(
                "get_workflow", escopo, cobrar_cota=False, origem="resource"
            ):
                return _json(
                    await get_workflow(ctx, workflow_id=id, include_definition=True)
                )
        except Exception as exc:
            raise _como_erro_de_resource(exc) from exc

    @server.resource(
        "atlans://workflows/{id}/contract",
        name="contrato_do_workflow",
        title="Contrato de sub-fluxo",
        description="Portas de entrada e saída declaradas para uso como sub-fluxo.",
        mime_type="application/json",
    )
    async def contrato_do_workflow(id: str, ctx: Context) -> str:
        """O que o fluxo aceita e devolve quando é chamado por outro."""
        try:
            escopo = escopo_da_chamada(ctx)
            async with guarda_da_chamada(
                "get_workflow_contract", escopo, cobrar_cota=False, origem="resource"
            ):
                return _json(await get_workflow_contract(ctx, workflow_id=id))
        except Exception as exc:
            raise _como_erro_de_resource(exc) from exc

    @server.resource(
        "atlans://runs/{id}",
        name="execucao",
        title="Execução",
        description=(
            "O desfecho de uma execução com o retrato COMPLETO de cada nó: status, "
            "duração, erro e saídas. Mesmo conteúdo de get_run(node_stats='full')."
        ),
        mime_type="application/json",
    )
    async def execucao(id: str, ctx: Context) -> str:
        """A execução inteira — e `full`, não `summary`, de propósito.

        Quem anexa uma execução ao contexto está investigando uma falha, e é
        justamente `output_keys`/`output_columns` que mostram onde a cadeia
        parou de produzir o que o nó seguinte esperava. A tool continua
        oferecendo o resumo a quem só quer o status.

        A mensagem de erro do run e a de cada nó descem higienizadas para
        `untrusted_data` (é o que `resumo_run` faz): são os campos mais
        prováveis de carregar segredo ou frase de comando de uma execução.
        """
        try:
            escopo = escopo_da_chamada(ctx)
            async with guarda_da_chamada(
                "get_run", escopo, cobrar_cota=False, origem="resource"
            ):
                return _json(await get_run(ctx, run_id=id, node_stats="full"))
        except Exception as exc:
            raise _como_erro_de_resource(exc) from exc
