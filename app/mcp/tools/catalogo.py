# app/mcp/tools/catalogo.py
"""Tools de catalogo. As guardas de cada uma estão em app/mcp/guardas.py."""
from __future__ import annotations

from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from app.mcp import guia, infra
from app.mcp.catalogo import descrever, indice_compacto, tipos_do_catalogo
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.tools.base import ferramenta
from app.services.node_service import NodeService

# O prefixo do resource equivalente. A tool e o resource entregam o MESMO texto;
# devolver o URI junto evita que quem integra tenha de montá-lo por conta.
URI_DO_GUIA = "atlans://guide/authoring/{topic}"


async def _definicoes():
    """O catálogo de nós vigente — já sem os nós desabilitados pela plataforma."""
    async with infra.sessao() as db:
        return await NodeService().list_nodes(db)


@ferramenta
async def search_nodes(
    ctx: Context, query: str | None = None, type: str | None = None
) -> dict:
    """Índice compacto dos nós disponíveis.

    Devolve nome, tipo, uma linha de descrição e se o nó exige credencial — o
    suficiente para escolher. A ficha de configuração vem depois, por
    `describe_node`: o catálogo inteiro em detalhe passa de 70 KB e não cabe no
    orçamento de contexto de uma conversa.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    definicoes = await _definicoes()
    itens = indice_compacto(definicoes, query=query, tipo=type)
    return {
        "items": itens,
        "total": len(itens),
        "types": tipos_do_catalogo(definicoes),
    }


# O teto de fichas por chamada. Protege o contexto da conversa (a ficha
# completa é grande) sem devolver o modelo para o padrão de uma volta por nó.
TETO_DE_FICHAS = 8


def _achar(definicoes, pedido: str):
    """A MESMA resolução do caminho antigo: nome ou apelido, na ordem do catálogo."""
    for d in definicoes:
        if d.name == pedido or (d.alias and d.alias == pedido):
            return d
    return None


@ferramenta
async def describe_node(ctx: Context, name: str | list[str], brief: bool = True) -> dict:
    """A ficha de um nó — ou de VÁRIOS numa chamada só.

    `name` aceita um nome ou uma LISTA de nomes (até 8): peça as fichas de
    todos os nós do fluxo de uma vez, em vez de gastar uma rodada por nó.
    `brief=true` (o padrão) traz o essencial para configurar. `brief=false`
    traz a ficha completa do catálogo — use quando a propriedade procurada não
    aparecer no resumo.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    if isinstance(name, list):
        # Deduplicado preservando a ordem: o modelo repete nome sem perceber, e
        # duas fichas iguais só queimariam contexto.
        pedidos = list(dict.fromkeys(n for n in (str(item).strip() for item in name) if n))
        if not pedidos:
            raise erro(
                "validation",
                "A lista de `name` veio vazia.",
                "informe ao menos um nome de nó",
            )
        ignorados = pedidos[TETO_DE_FICHAS:]
        pedidos = pedidos[:TETO_DE_FICHAS]

        definicoes = await _definicoes()
        fichas: list[dict] = []
        # Nome desconhecido NÃO derruba o lote: as fichas achadas voltam e
        # `not_found` nomeia as que faltaram — o modelo corrige só o que errou,
        # sem pagar outra rodada pelas que acertou. Um nó desabilitado responde
        # igual a um inexistente, como no caminho de um nome só.
        nao_achados: list[str] = []
        # Dedupe também por RESOLUÇÃO: nome e apelido do mesmo nó na lista
        # devolveriam a mesma ficha duas vezes — o gasto de contexto que este
        # teto existe para evitar.
        descritos: set[str] = set()
        for pedido in pedidos:
            d = _achar(definicoes, pedido)
            if d is None:
                nao_achados.append(pedido)
            elif d.name not in descritos:
                descritos.add(d.name)
                fichas.append(descrever(d, brief=brief))
        saida: dict = {"nodes": fichas, "total": len(fichas)}
        dicas: list[str] = []
        if nao_achados:
            saida["not_found"] = nao_achados
            dicas.append("use search_nodes para conferir os nomes em not_found")
        if ignorados:
            saida["skipped"] = ignorados
            dicas.append(
                f"o teto é {TETO_DE_FICHAS} nomes por chamada; peça os de skipped na próxima"
            )
        if dicas:
            saida["hint"] = "; ".join(dicas)
        return saida

    procurado = str(name).strip()
    d = _achar(await _definicoes(), procurado)
    if d is not None:
        return descrever(d, brief=brief)

    # Nome desconhecido é `not_found`, e não uma lista de sugestões: o índice
    # já existe em `search_nodes`, e um nó desabilitado pela plataforma tem de
    # responder igual a um nó inexistente.
    raise erro(
        "not_found",
        f"Nenhum nó chamado '{procurado}' está disponível.",
        "use search_nodes para ver os nós disponíveis",
    )


@ferramenta
async def get_authoring_guide(ctx: Context, topic: str) -> dict:
    """O guia de autoria de fluxos, por tópico.

    Um tópico por chamada, de propósito: o guia inteiro de uma vez desperdiça
    contexto com o que não se vai usar naquela tarefa.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    pedido = str(topic).strip()
    try:
        markdown = guia.ler_topico(pedido)
    except ValueError as exc:
        raise erro(
            "not_found",
            str(exc),
            "escolha um dos tópicos disponíveis em topics",
            topics=list(guia.TOPICOS),
        ) from exc
    except OSError as exc:
        # O tópico existe na lista mas o arquivo não pôde ser lido: é defeito de
        # implantação, não pedido inválido — e o cliente precisa saber que o
        # conteúdo não está lá, sem receber o caminho do arquivo.
        raise erro(
            "unavailable",
            f"O guia do tópico '{pedido}' não está disponível nesta instalação.",
            "tente outro tópico ou avise quem administra a plataforma",
        ) from exc

    return {
        "topic": pedido,
        "markdown": markdown,
        "resource_uri": URI_DO_GUIA.replace("{topic}", pedido),
        "topics": list(guia.TOPICOS),
    }


_SOMENTE_LEITURA = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def registrar(server) -> None:
    """Registra as tools deste domínio."""
    server.tool(
        name="search_nodes",
        title="Buscar nós",
        description=(
            "Índice compacto dos nós disponíveis para montar um fluxo: nome, tipo, uma "
            "linha de descrição e se o nó exige credencial. Filtre por texto (`query`, "
            "sobre nome, apelido e descrição) e por `type`."
        ),
        annotations=_SOMENTE_LEITURA,
    )(search_nodes)

    server.tool(
        name="describe_node",
        title="Detalhar nó",
        description=(
            "Ficha de um nó do catálogo: propriedades aceitas, entradas, saídas e dicas "
            "de uso. `name` aceita um nome ou uma LISTA de nomes (até 8) — peça as fichas "
            "de todos os nós do fluxo numa chamada só. Com `brief=false` devolve a ficha "
            "completa. Use os nomes exatamente como aparecem aqui — propriedade não "
            "declarada falha na validação."
        ),
        annotations=_SOMENTE_LEITURA,
    )(describe_node)

    server.tool(
        name="get_authoring_guide",
        title="Guia de autoria",
        description=(
            "Guia de como escrever um fluxo do Atlans, por tópico: overview, edges, "
            "credentials, expressions, inputs, sources, sql, pitfalls e recipes. Leia antes "
            "de montar uma definição nova; `sources` diz como achar uma fonte externa sem "
            "adivinhar url/typeName."
        ),
        annotations=_SOMENTE_LEITURA,
    )(get_authoring_guide)
