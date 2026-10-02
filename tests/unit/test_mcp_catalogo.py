# tests/unit/test_mcp_catalogo.py
"""
O catálogo de nós pelo MCP: caber no contexto e não mentir sobre o que existe.

Duas propriedades sustentam as ferramentas de catálogo:

- **tamanho.** O `description()` de todos os nós registrados passa de 70 KB.
  Uma conversa que começasse por isso gastaria o orçamento de contexto antes da
  primeira pergunta. O índice compacto tem de caber com folga — o teto de 16 KB
  aqui é o alarme que dispara se alguém voltar a enfiar a descrição inteira no
  índice;
- **verdade.** Um nó desabilitado pela plataforma não pode aparecer no índice
  nem ser detalhado: quem montasse um fluxo com ele receberia a recusa só na
  execução, depois de todo o trabalho.

Os testes correm sobre o registro REAL de nós, e não sobre um catálogo de
mentira: é o registro que cresce sem ninguém olhar, e é dele que vem o risco.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp import guia, infra
from app.mcp.catalogo import descrever, indice_compacto, one_line, tipos_do_catalogo
from app.mcp.tools.catalogo import describe_node, get_authoring_guide, search_nodes
from app.services import node_service
from app.services.node_service import NodeService
from tests.unit._mcp_harness import ctx_falso, escopo_falso

TETO_DO_INDICE = 16 * 1024


def corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


@pytest.fixture
def catalogo(monkeypatch):
    """Catálogo real, sem banco: a lista de desabilitados é o único ponto de I/O."""
    desabilitados: set = set()

    async def _desabilitados(db):
        return set(desabilitados)

    @asynccontextmanager
    async def _sessao():
        yield None

    monkeypatch.setattr(node_service, "disabled_names", _desabilitados)
    monkeypatch.setattr(infra, "sessao", _sessao)
    return desabilitados


async def definicoes_reais() -> list:
    """As `NodeDefinition` do registro, com a fixture `catalogo` já aplicada."""
    return await NodeService().list_nodes(None)


def ctx():
    return ctx_falso(escopo_falso(scopes={"workflows:read"}))


# ── Helpers puros ─────────────────────────────────────────────────────────────


def test_one_line_pega_a_primeira_frase():
    assert one_line({"description": "Recorta camadas. Aceita GeoJSON e SHP."}) == "Recorta camadas"
    assert one_line({"description": "Sem ponto final"}) == "Sem ponto final"
    assert one_line({"description": ""}) == ""
    assert one_line("Texto direto. Resto.") == "Texto direto"


def test_one_line_nao_devolve_paragrafo():
    """Descrição de várias linhas vira UMA linha — o índice é lido inteiro."""
    linha = one_line({"description": "Primeira frase\n\nParágrafo longo com detalhes."})
    assert linha == "Primeira frase"


def test_one_line_corta_frase_quilometrica():
    linha = one_line({"description": "a" * 400})
    assert len(linha) <= 160


def test_one_line_nao_corta_na_abreviacao():
    """"Ex." e "etc." terminam em ponto sem terminar a frase.

    Cortar ali entregaria um índice de linhas "Ex" e "etc": o cliente teria de
    chamar `describe_node` em cada nó só para descobrir para que serve — que é
    exatamente o gasto de contexto que o índice existe para evitar. O segmento
    curto demais se junta ao próximo, nunca é descartado.
    """
    assert one_line({"description": "Ex. recorta camadas de um GeoJSON. Depois exporta."}) == (
        "Ex. recorta camadas de um GeoJSON"
    )
    assert one_line({"description": "Junta arquivos: SHP, GeoJSON, etc. Aceita ZIP."}) == (
        "Junta arquivos: SHP, GeoJSON, etc. Aceita ZIP"
    )
    assert one_line({"description": "p. ex. une camadas vizinhas. Resto."}) == (
        "p. ex. une camadas vizinhas"
    )
    # Mesmo sem frase nenhuma depois, a abreviação sobra sozinha em vez de sumir.
    assert one_line({"description": "Ex."}) == "Ex"


def test_one_line_nao_quebra_um_decimal():
    """O ponto de "0.5" não é fim de frase — o corte exige o espaço depois."""
    assert one_line({"description": "Aplica um buffer de 0.5 m. Aceita metros."}) == (
        "Aplica um buffer de 0.5 m"
    )
    assert one_line({"description": "Tolerância 0.5 m"}) == "Tolerância 0.5 m"


def test_one_line_ainda_corta_na_primeira_frase_de_verdade():
    """A junção vale só para o segmento curto: frase real continua sendo uma só."""
    assert one_line({"description": "Recorta camadas. Aceita GeoJSON e SHP."}) == "Recorta camadas"


# ── search_nodes ──────────────────────────────────────────────────────────────


async def test_o_indice_compacto_cabe_no_contexto(catalogo):
    resposta = await search_nodes(ctx())
    tamanho = len(json.dumps(resposta, ensure_ascii=False).encode("utf-8"))
    assert tamanho < TETO_DO_INDICE, f"índice com {tamanho} bytes"
    assert resposta["total"] == len(resposta["items"]) > 10


async def test_cada_item_do_indice_tem_so_o_que_serve_para_escolher(catalogo):
    resposta = await search_nodes(ctx())
    for item in resposta["items"]:
        assert set(item) == {"name", "type", "one_line", "requires_credential"}


async def test_o_indice_traz_o_mapa_de_tipos(catalogo):
    resposta = await search_nodes(ctx())
    tipos = {t["type"] for t in resposta["types"]}
    assert "trigger" in tipos
    assert all(t["count"] >= 1 for t in resposta["types"])


async def test_filtro_por_tipo_e_por_texto(catalogo):
    todos = await search_nodes(ctx())
    gatilhos = await search_nodes(ctx(), type="trigger")
    assert 0 < gatilhos["total"] < todos["total"]
    assert {i["type"] for i in gatilhos["items"]} == {"trigger"}

    algum = todos["items"][0]["name"]
    achado = await search_nodes(ctx(), query=algum.lower())
    assert algum in {i["name"] for i in achado["items"]}


async def test_no_desabilitado_some_do_indice_e_do_detalhe(catalogo):
    todos = await search_nodes(ctx())
    alvo = todos["items"][0]["name"]

    catalogo.add(alvo)
    depois = await search_nodes(ctx())
    assert alvo not in {i["name"] for i in depois["items"]}
    assert depois["total"] == todos["total"] - 1

    # E detalhar responde como um nó inexistente — a diferença só confundiria.
    with pytest.raises(ToolError) as exc:
        await describe_node(ctx(), name=alvo)
    assert corpo(exc.value)["code"] == "not_found"


# ── describe_node ─────────────────────────────────────────────────────────────


async def test_nome_desconhecido_e_not_found(catalogo):
    with pytest.raises(ToolError) as exc:
        await describe_node(ctx(), name="NoQueNuncaExistiu")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "not_found"
    assert "search_nodes" in detalhe["hint"]


async def test_brief_traz_o_essencial_da_propriedade(catalogo):
    ficha = await describe_node(ctx(), name="DatabaseQuery", brief=True)
    assert ficha["name"] == "DatabaseQuery"
    assert ficha["requires_credential"] is True
    for propriedade in ficha["properties"]:
        # Rótulo, ajuda e visibilidade condicional são assunto do editor visual.
        assert set(propriedade) <= {
            "name",
            "type",
            "required",
            "default",
            "options",
            "credential_types",
        }


async def test_completo_traz_mais_que_o_brief(catalogo):
    breve = await describe_node(ctx(), name="DatabaseQuery", brief=True)
    inteiro = await describe_node(ctx(), name="DatabaseQuery", brief=False)
    assert set(breve) - {"hints"} <= set(inteiro) | {"inputs", "outputs"}
    # A ficha completa carrega os campos que o resumo corta.
    chaves_de_propriedade = {chave for p in inteiro["properties"] for chave in p}
    assert "label" in chaves_de_propriedade
    assert len(json.dumps(inteiro)) > len(json.dumps(breve))


async def test_no_que_exige_credencial_diz_como_referencia_la(catalogo):
    ficha = await describe_node(ctx(), name="DatabaseQuery", brief=True)
    assert any("list_credentials" in dica for dica in ficha["hints"])


def test_dicas_explicam_o_que_nenhum_campo_diz():
    """Saída dinâmica e coluna sugerida não têm campo próprio na ficha."""
    from types import SimpleNamespace

    no = SimpleNamespace(
        name="Exemplo",
        type="transform",
        description="Faz algo.",
        properties=[SimpleNamespace(name="campo", type="string", suggest_columns="input")],
        inputs=[],
        outputs=[],
        dynamic_output=True,
        dynamic_inputs=False,
        outputs_from_ports=True,
        requires_credential=False,
    )
    dicas = descrever(no, brief=True)["hints"]
    assert any("output_vars" in d for d in dicas)
    assert any("`ports`" in d for d in dicas)
    assert any("NOME DE UMA COLUNA" in d for d in dicas)


def test_indice_compacto_ordena_por_nome():
    from types import SimpleNamespace

    defs = [
        SimpleNamespace(name="Zebra", type="t", description="Z.", requires_credential=False, alias=None),
        SimpleNamespace(name="Abelha", type="t", description="A.", requires_credential=True, alias=None),
    ]
    assert [i["name"] for i in indice_compacto(defs)] == ["Abelha", "Zebra"]
    assert tipos_do_catalogo(defs) == [{"type": "t", "count": 2}]


def test_busca_ignora_acento_e_caixa():
    from types import SimpleNamespace

    defs = [
        SimpleNamespace(
            name="AreaCalc", type="t", description="Calcula a área do polígono.",
            requires_credential=False, alias=None,
        ),
    ]
    assert indice_compacto(defs, query="AREA") != []
    assert indice_compacto(defs, query="área") != []
    assert indice_compacto(defs, query="volume") == []


# ── get_authoring_guide ───────────────────────────────────────────────────────


async def test_guia_devolve_markdown_e_o_uri_do_resource(monkeypatch):
    monkeypatch.setattr(guia, "ler_topico", lambda topic: f"# {topic}\n\ntexto")
    resposta = await get_authoring_guide(ctx(), topic="overview")
    assert resposta["topic"] == "overview"
    assert resposta["markdown"].startswith("# overview")
    # Tool e resource entregam o MESMO texto; o URI vai junto para quem preferir
    # ler pelo caminho de resource.
    assert resposta["resource_uri"] == "atlans://guide/authoring/overview"
    assert len(resposta["topics"]) == 9 and "sources" in resposta["topics"]


async def test_topico_desconhecido_e_not_found_com_a_lista(monkeypatch):
    with pytest.raises(ToolError) as exc:
        await get_authoring_guide(ctx(), topic="../../etc/passwd")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "not_found"
    # A recusa lista os tópicos válidos — e nunca ecoa um caminho de arquivo.
    assert detalhe["topics"] == list(guia.TOPICOS)


async def test_guia_sem_o_arquivo_instalado_nao_vira_erro_interno(monkeypatch):
    """Falta de arquivo é indisponibilidade, e a mensagem não expõe o caminho."""

    def _sem_arquivo(topic):
        raise FileNotFoundError("/caminho/interno/guia/overview.md")

    monkeypatch.setattr(guia, "ler_topico", _sem_arquivo)
    with pytest.raises(ToolError) as exc:
        await get_authoring_guide(ctx(), topic="overview")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "unavailable"
    assert "/caminho/interno" not in json.dumps(detalhe)


async def test_guia_le_o_arquivo_de_verdade_do_topico():
    """Sem substituto nenhum: a tool entrega o markdown que está no disco."""
    resposta = await get_authoring_guide(ctx(), topic="overview")
    assert resposta["markdown"].strip() == guia.ler_topico("overview").strip()
    assert resposta["markdown"].strip() != ""


def test_no_que_le_fonte_externa_manda_consultar_o_catalogo():
    """`source_kind` é o que liga o nó ao catálogo de fontes — a dica é o que
    faz o modelo chamar `search_sources` em vez de inventar url/typeName."""
    from types import SimpleNamespace

    from app.mcp.catalogo import descrever

    no = SimpleNamespace(name="WFS", type="datasource", description="Lê feições de um WFS.",
                         properties=[], inputs=None, outputs=None, source_kind="wfs")
    dicas = descrever(no, brief=True)["hints"]
    assert any('search_sources(kind="wfs")' in dica and "describe_source" in dica for dica in dicas)

    sem = SimpleNamespace(name="Buffer", type="spatial", description="Faixa.", properties=[], inputs=None, outputs=None)
    assert not any("search_sources" in dica for dica in descrever(sem, brief=True)["hints"])


async def test_o_catalogo_expoe_o_source_kind_do_wfs(catalogo):
    """O flag atravessa `NodeService.list_nodes`, que monta a ficha campo a campo."""
    from app.mcp.tools.catalogo import describe_node

    ficha = await describe_node(ctx(), name="WFS", brief=False)
    assert ficha["source_kind"] == "wfs"
    assert any("search_sources" in dica for dica in ficha["hints"])


# ── describe_node em lote ─────────────────────────────────────────────────────
# `name` aceita uma lista (até 8): as fichas de todos os nós do fluxo numa
# chamada só, em vez de uma volta do modelo por nó.


async def test_lista_devolve_as_fichas_na_ordem_e_deduplicada(catalogo):
    defs = await definicoes_reais()
    a, b = defs[0].name, defs[1].name

    saida = await describe_node(ctx(), name=[a, b, a])

    assert [f["name"] for f in saida["nodes"]] == [a, b]
    assert saida["total"] == 2
    assert "not_found" not in saida
    assert "skipped" not in saida


async def test_lista_com_desconhecido_nao_derruba_o_lote(catalogo):
    """O modelo corrige só o nome que errou, sem pagar outra rodada pelos certos."""
    defs = await definicoes_reais()
    a = defs[0].name

    saida = await describe_node(ctx(), name=[a, "NoQueNuncaExistiu"])

    assert [f["name"] for f in saida["nodes"]] == [a]
    assert saida["not_found"] == ["NoQueNuncaExistiu"]
    assert "search_nodes" in saida["hint"]


async def test_no_desabilitado_responde_igual_a_inexistente_tambem_no_lote(catalogo):
    defs = await definicoes_reais()
    a, b = defs[0].name, defs[1].name
    catalogo.add(a)

    saida = await describe_node(ctx(), name=[a, b])

    assert saida["not_found"] == [a]
    assert [f["name"] for f in saida["nodes"]] == [b]


async def test_lista_respeita_o_teto_e_anuncia_o_corte(catalogo):
    defs = await definicoes_reais()
    nomes = [d.name for d in defs[:9]]
    assert len(nomes) == 9, "o registro encolheu a menos de 9 nós?"

    saida = await describe_node(ctx(), name=nomes)

    assert saida["total"] == 8
    assert [f["name"] for f in saida["nodes"]] == nomes[:8]
    assert saida["skipped"] == [nomes[8]]
    assert "8" in saida["hint"]


async def test_lista_vazia_e_validation(catalogo):
    with pytest.raises(ToolError) as exc:
        await describe_node(ctx(), name=["", "  "])
    assert corpo(exc.value)["code"] == "validation"


async def test_nome_unico_segue_devolvendo_a_ficha_crua(catalogo):
    """Regressão do contrato: string devolve a ficha direto, sem envelope de lote
    — é a forma que os clientes MCP externos já consomem."""
    ficha = await describe_node(ctx(), name="DatabaseQuery")
    assert ficha["name"] == "DatabaseQuery"
    assert "nodes" not in ficha


async def test_nome_e_apelido_do_mesmo_no_viram_uma_ficha_so(catalogo):
    """Dedupe por RESOLUÇÃO, não só por grafia: pedir o nó pelo nome E pelo
    apelido devolve uma ficha — duas iguais só queimariam o contexto que o
    teto existe para proteger."""
    defs = await definicoes_reais()
    com_alias = next((d for d in defs if d.alias), None)
    if com_alias is None:
        pytest.skip("nenhum nó com apelido no registro")

    saida = await describe_node(ctx(), name=[com_alias.name, com_alias.alias])

    assert [f["name"] for f in saida["nodes"]] == [com_alias.name]
    assert saida["total"] == 1
    assert "not_found" not in saida
