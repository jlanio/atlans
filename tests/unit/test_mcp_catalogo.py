# tests/unit/test_mcp_catalogo.py
"""
The node catalog over MCP: fitting in the context and not lying about what exists.

Two properties underpin the catalog tools:

- **size.** The `description()` of all registered nodes exceeds 70 KB.
  A conversation that started with that would spend the context budget before the
  first question. The compact index has to fit with room to spare — the 16 KB
  ceiling here is the alarm that goes off if someone goes back to stuffing the whole
  description into the index;
- **truth.** A node disabled by the platform must not appear in the index
  or be described: whoever built a workflow with it would get the refusal only at
  execution, after all the work.

The tests run over the REAL node registry, not over a fake catalog: it is the
registry that grows without anyone watching, and that is where the risk comes from.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp import guia, infra
from app.mcp.catalogo import descrever, compact_index, one_line, catalog_types
from app.mcp.tools.catalogo import describe_node, get_authoring_guide, search_nodes
from app.services import node_service
from app.services.node_service import NodeService
from tests.unit._mcp_harness import fake_ctx, fake_scope

INDEX_CEILING = 16 * 1024


def corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


@pytest.fixture
def catalogo(monkeypatch):
    """Real catalog, no database: the list of disabled nodes is the only I/O point."""
    desabilitados: set = set()

    async def _disabled_names(db):
        return set(desabilitados)

    @asynccontextmanager
    async def _session():
        yield None

    monkeypatch.setattr(node_service, "disabled_names", _disabled_names)
    monkeypatch.setattr(infra, "sessao", _session)
    return desabilitados


async def real_definitions() -> list:
    """The registry's `NodeDefinition`s, with the `catalogo` fixture already applied."""
    return await NodeService().list_nodes(None)


def ctx():
    return fake_ctx(fake_scope(scopes={"workflows:read"}))


# ── Helpers puros ─────────────────────────────────────────────────────────────


def test_one_line_takes_the_first_sentence():
    assert one_line({"description": "Recorta camadas. Aceita GeoJSON e SHP."}) == "Recorta camadas"
    assert one_line({"description": "Sem ponto final"}) == "Sem ponto final"
    assert one_line({"description": ""}) == ""
    assert one_line("Texto direto. Resto.") == "Texto direto"


def test_one_line_does_not_return_a_paragraph():
    """A multi-line description becomes ONE line — the index is read whole."""
    linha = one_line({"description": "Primeira frase\n\nParágrafo longo com detalhes."})
    assert linha == "Primeira frase"


def test_one_line_cuts_a_huge_sentence():
    linha = one_line({"description": "a" * 400})
    assert len(linha) <= 160


def test_one_line_does_not_cut_at_the_abbreviation():
    """"Ex." and "etc." end in a period without ending the sentence.

    Cutting there would deliver an index of "Ex" and "etc" lines: the client would have
    to call `describe_node` on each node just to find out what it is for — which is
    exactly the context spending the index exists to avoid. A segment that is too
    short is joined to the next one, never discarded.
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
    # Even with no sentence at all afterwards, the abbreviation remains alone instead of vanishing.
    assert one_line({"description": "Ex."}) == "Ex"


def test_one_line_does_not_break_a_decimal():
    """The period in "0.5" is not the end of a sentence — the cut requires the space after it."""
    assert one_line({"description": "Aplica um buffer de 0.5 m. Aceita metros."}) == (
        "Aplica um buffer de 0.5 m"
    )
    assert one_line({"description": "Tolerância 0.5 m"}) == "Tolerância 0.5 m"


def test_one_line_still_cuts_at_the_real_first_sentence():
    """The joining only applies to the short segment: a real sentence stays a single one."""
    assert one_line({"description": "Recorta camadas. Aceita GeoJSON e SHP."}) == "Recorta camadas"


# ── search_nodes ──────────────────────────────────────────────────────────────


async def test_the_compact_index_fits_in_the_context(catalogo):
    resposta = await search_nodes(ctx())
    tamanho = len(json.dumps(resposta, ensure_ascii=False).encode("utf-8"))
    assert tamanho < INDEX_CEILING, f"índice com {tamanho} bytes"
    assert resposta["total"] == len(resposta["items"]) > 10


async def test_each_index_item_has_only_what_helps_to_choose(catalogo):
    resposta = await search_nodes(ctx())
    for item in resposta["items"]:
        assert set(item) == {"name", "type", "one_line", "requires_credential"}


async def test_the_index_carries_the_type_map(catalogo):
    resposta = await search_nodes(ctx())
    tipos = {t["type"] for t in resposta["types"]}
    assert "trigger" in tipos
    assert all(t["count"] >= 1 for t in resposta["types"])


async def test_filter_by_type_and_by_text(catalogo):
    todos = await search_nodes(ctx())
    gatilhos = await search_nodes(ctx(), type="trigger")
    assert 0 < gatilhos["total"] < todos["total"]
    assert {i["type"] for i in gatilhos["items"]} == {"trigger"}

    algum = todos["items"][0]["name"]
    achado = await search_nodes(ctx(), query=algum.lower())
    assert algum in {i["name"] for i in achado["items"]}


async def test_disabled_node_disappears_from_index_and_detail(catalogo):
    todos = await search_nodes(ctx())
    alvo = todos["items"][0]["name"]

    catalogo.add(alvo)
    depois = await search_nodes(ctx())
    assert alvo not in {i["name"] for i in depois["items"]}
    assert depois["total"] == todos["total"] - 1

    # And describing answers as for a nonexistent node — the difference would only confuse.
    with pytest.raises(ToolError) as exc:
        await describe_node(ctx(), name=alvo)
    assert corpo(exc.value)["code"] == "not_found"


# ── describe_node ─────────────────────────────────────────────────────────────


async def test_unknown_name_is_not_found(catalogo):
    with pytest.raises(ToolError) as exc:
        await describe_node(ctx(), name="NoQueNuncaExistiu")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "not_found"
    assert "search_nodes" in detalhe["hint"]


async def test_brief_carries_the_property_essentials(catalogo):
    ficha = await describe_node(ctx(), name="DatabaseQuery", brief=True)
    assert ficha["name"] == "DatabaseQuery"
    assert ficha["requires_credential"] is True
    for propriedade in ficha["properties"]:
        # Label, help and conditional visibility are the visual editor's business.
        assert set(propriedade) <= {
            "name",
            "type",
            "required",
            "default",
            "options",
            "credential_types",
        }


async def test_full_carries_more_than_the_brief(catalogo):
    breve = await describe_node(ctx(), name="DatabaseQuery", brief=True)
    inteiro = await describe_node(ctx(), name="DatabaseQuery", brief=False)
    assert set(breve) - {"hints"} <= set(inteiro) | {"inputs", "outputs"}
    # The full sheet carries the fields the summary cuts.
    property_keys = {chave for p in inteiro["properties"] for chave in p}
    assert "label" in property_keys
    assert len(json.dumps(inteiro)) > len(json.dumps(breve))


async def test_node_requiring_credential_says_how_to_reference_it(catalogo):
    ficha = await describe_node(ctx(), name="DatabaseQuery", brief=True)
    assert any("list_credentials" in dica for dica in ficha["hints"])


def test_hints_explain_what_no_field_says():
    """Dynamic output and suggested column have no field of their own in the sheet."""
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


def test_compact_index_sorts_by_name():
    from types import SimpleNamespace

    defs = [
        SimpleNamespace(name="Zebra", type="t", description="Z.", requires_credential=False, alias=None),
        SimpleNamespace(name="Abelha", type="t", description="A.", requires_credential=True, alias=None),
    ]
    assert [i["name"] for i in compact_index(defs)] == ["Abelha", "Zebra"]
    assert catalog_types(defs) == [{"type": "t", "count": 2}]


def test_search_ignores_accents_and_case():
    from types import SimpleNamespace

    defs = [
        SimpleNamespace(
            name="AreaCalc", type="t", description="Calcula a área do polígono.",
            requires_credential=False, alias=None,
        ),
    ]
    assert compact_index(defs, query="AREA") != []
    assert compact_index(defs, query="área") != []
    assert compact_index(defs, query="volume") == []


# ── get_authoring_guide ───────────────────────────────────────────────────────


async def test_guide_returns_markdown_and_the_resource_uri(monkeypatch):
    monkeypatch.setattr(guia, "ler_topico", lambda topic: f"# {topic}\n\ntexto")
    resposta = await get_authoring_guide(ctx(), topic="overview")
    assert resposta["topic"] == "overview"
    assert resposta["markdown"].startswith("# overview")
    # Tool and resource deliver the SAME text; the URI goes along for whoever prefers
    # to read through the resource path.
    assert resposta["resource_uri"] == "atlans://guide/authoring/overview"
    assert len(resposta["topics"]) == 9 and "sources" in resposta["topics"]


async def test_unknown_topic_is_not_found_with_the_list(monkeypatch):
    with pytest.raises(ToolError) as exc:
        await get_authoring_guide(ctx(), topic="../../etc/passwd")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "not_found"
    # The refusal lists the valid topics — and never echoes a file path.
    assert detalhe["topics"] == list(guia.TOPICS)


async def test_guide_without_the_installed_file_does_not_become_internal_error(monkeypatch):
    """A missing file is unavailability, and the message does not expose the path."""

    def _missing_file(topic):
        raise FileNotFoundError("/caminho/interno/guia/overview.md")

    monkeypatch.setattr(guia, "ler_topico", _missing_file)
    with pytest.raises(ToolError) as exc:
        await get_authoring_guide(ctx(), topic="overview")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "unavailable"
    assert "/caminho/interno" not in json.dumps(detalhe)


async def test_guide_reads_the_real_topic_file():
    """No substitute at all: the tool delivers the markdown that is on disk."""
    resposta = await get_authoring_guide(ctx(), topic="overview")
    assert resposta["markdown"].strip() == guia.ler_topico("overview").strip()
    assert resposta["markdown"].strip() != ""


def test_node_reading_external_source_says_to_check_the_catalog():
    """`source_kind` is what links the node to the source catalog — the hint is what
    makes the model call `search_sources` instead of inventing url/typeName."""
    from types import SimpleNamespace

    from app.mcp.catalogo import descrever

    no = SimpleNamespace(name="WFS", type="datasource", description="Lê feições de um WFS.",
                         properties=[], inputs=None, outputs=None, source_kind="wfs")
    dicas = descrever(no, brief=True)["hints"]
    assert any('search_sources(kind="wfs")' in dica and "describe_source" in dica for dica in dicas)

    sem = SimpleNamespace(name="Buffer", type="spatial", description="Faixa.", properties=[], inputs=None, outputs=None)
    assert not any("search_sources" in dica for dica in descrever(sem, brief=True)["hints"])


async def test_the_catalog_exposes_the_wfs_source_kind(catalogo):
    """O flag atravessa `NodeService.list_nodes`, que monta a ficha campo a campo."""
    from app.mcp.tools.catalogo import describe_node

    ficha = await describe_node(ctx(), name="WFS", brief=False)
    assert ficha["source_kind"] == "wfs"
    assert any("search_sources" in dica for dica in ficha["hints"])


# ── describe_node in batch ────────────────────────────────────────────────────
# `name` accepts a list (up to 8): the sheets of all the workflow's nodes in a
# single call, instead of one model round per node.


async def test_list_returns_the_cards_in_order_and_deduplicated(catalogo):
    defs = await real_definitions()
    a, b = defs[0].name, defs[1].name

    saida = await describe_node(ctx(), name=[a, b, a])

    assert [f["name"] for f in saida["nodes"]] == [a, b]
    assert saida["total"] == 2
    assert "not_found" not in saida
    assert "skipped" not in saida


async def test_list_with_unknown_does_not_break_the_batch(catalogo):
    """The model fixes only the name it got wrong, without paying another round for the right ones."""
    defs = await real_definitions()
    a = defs[0].name

    saida = await describe_node(ctx(), name=[a, "NoQueNuncaExistiu"])

    assert [f["name"] for f in saida["nodes"]] == [a]
    assert saida["not_found"] == ["NoQueNuncaExistiu"]
    assert "search_nodes" in saida["hint"]


async def test_disabled_node_answers_like_nonexistent_also_in_the_batch(catalogo):
    defs = await real_definitions()
    a, b = defs[0].name, defs[1].name
    catalogo.add(a)

    saida = await describe_node(ctx(), name=[a, b])

    assert saida["not_found"] == [a]
    assert [f["name"] for f in saida["nodes"]] == [b]


async def test_list_respects_the_ceiling_and_announces_the_cut(catalogo):
    defs = await real_definitions()
    nomes = [d.name for d in defs[:9]]
    assert len(nomes) == 9, "o registro encolheu a menos de 9 nós?"

    saida = await describe_node(ctx(), name=nomes)

    assert saida["total"] == 8
    assert [f["name"] for f in saida["nodes"]] == nomes[:8]
    assert saida["skipped"] == [nomes[8]]
    assert "8" in saida["hint"]


async def test_empty_list_is_validation(catalogo):
    with pytest.raises(ToolError) as exc:
        await describe_node(ctx(), name=["", "  "])
    assert corpo(exc.value)["code"] == "validation"


async def test_single_name_still_returns_the_raw_card(catalogo):
    """Contract regression: a string returns the sheet directly, without a batch envelope
    — it is the form the external MCP clients already consume."""
    ficha = await describe_node(ctx(), name="DatabaseQuery")
    assert ficha["name"] == "DatabaseQuery"
    assert "nodes" not in ficha


async def test_name_and_alias_of_the_same_node_become_a_single_card(catalogo):
    """Dedupe by RESOLUTION, not just by spelling: asking for the node by name AND by
    alias returns one sheet — two identical ones would only burn the context that the
    ceiling exists to protect."""
    defs = await real_definitions()
    with_alias = next((d for d in defs if d.alias), None)
    if with_alias is None:
        pytest.skip("nenhum nó com apelido no registro")

    saida = await describe_node(ctx(), name=[with_alias.name, with_alias.alias])

    assert [f["name"] for f in saida["nodes"]] == [with_alias.name]
    assert saida["total"] == 1
    assert "not_found" not in saida
