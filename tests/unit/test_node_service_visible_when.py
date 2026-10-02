"""
Regressao: as propriedades dos nos declaram `visibleWhen` (visibilidade
condicional), mas o schema NodeProperty e a montagem em NodeService.list_nodes
nao repassavam a chave — o Pydantic a descartava e o frontend nunca a recebia,
deixando TODOS os campos sempre visiveis (os dois pickers do DataInput, o token
Bearer do DataOutput mesmo quando publico, etc.).

Este teste percorre o caminho real do servico e garante que `visibleWhen`
chega serializado para o frontend.
"""
from unittest.mock import patch

import pytest

from flow.registry import auto_discover_nodes
from app.services.node_service import NodeService

auto_discover_nodes()


async def _list():
    async def _no_disabled(_db):
        return set()

    with patch("app.services.node_service.disabled_names", _no_disabled):
        return await NodeService().list_nodes(db=None)


def _props(defs, node_name):
    for d in defs:
        if d.name == node_name:
            return {p.name: p for p in d.properties}
    raise AssertionError(f"no '{node_name}' ausente do catalogo")


@pytest.mark.asyncio
async def test_datainput_pickers_tem_visible_when():
    defs = await _list()
    props = _props(defs, "DataInput")
    assert props["driveFileId"].visibleWhen == {"field": "context", "in": ["drive"]}
    assert props["artifactId"].visibleWhen == {"field": "context", "in": ["artifacts"]}
    # `context` e `crs` sao sempre visiveis — sem visibleWhen.
    assert props["context"].visibleWhen is None
    assert props["crs"].visibleWhen is None


@pytest.mark.asyncio
async def test_dataoutput_credencial_e_publico_tem_visible_when():
    defs = await _list()
    props = _props(defs, "DataOutput")
    # isPublic: contexto Artefatos E conteudo que sai da maquina. Um artefato
    # mantido no executor nao tem download, entao nao ha acesso a controlar.
    vw = props["isPublic"].visibleWhen
    assert isinstance(vw, list) and len(vw) == 2
    assert {"field": "context", "in": ["artifacts"]} in vw
    assert {"field": "localidade", "in": ["herdar"]} in vw

    # credential_id: as duas acima MAIS nao-publico.
    vw = props["credential_id"].visibleWhen
    assert isinstance(vw, list) and len(vw) == 3
    assert {"field": "context", "in": ["artifacts"]} in vw
    assert {"field": "localidade", "in": ["herdar"]} in vw
    assert any(r["field"] == "isPublic" and False in r["in"] for r in vw)


@pytest.mark.asyncio
async def test_localidade_esta_em_todos_os_nos_que_gravam_artefato():
    """O `if` que escolhe local vs nuvem nao pode existir em um no so.

    Foi assim que a politica nasceu — `keepLocal` no DataOutput e mais nada — e
    o resultado era um executor configurado para reter dados que continuava
    enviando tudo que os OUTROS nos de saida produziam.
    """
    defs = await _list()
    for nome in ("DataOutput", "SaveGeoJSON", "SaveToGeoParquet", "SaveToShapefile", "SaveToS3", "CartaImagem"):
        prop = _props(defs, nome).get("localidade")
        assert prop is not None, f"no '{nome}' sem o campo de localidade"
        assert prop.default == "herdar", f"no '{nome}': o padrao tem de ser herdar da maquina"
        # Sem a opcao de enviar: seria a unica capaz de contrariar a politica da
        # maquina, e o executor a ignoraria em silencio.
        assert [o.value for o in prop.options] == ["herdar", "executor"], nome


@pytest.mark.asyncio
async def test_keeplocal_nao_existe_mais_em_no_nenhum():
    """Substituido por `localidade`, sem shim. Se voltasse a aparecer em algum
    no, `validate_node_parameters` aceitaria os dois e a politica passaria a
    depender de qual deles o fluxo salvou."""
    defs = await _list()
    for d in defs:
        assert all(p.name != "keepLocal" for p in d.properties), f"no '{d.name}'"


@pytest.mark.asyncio
async def test_registro_do_no_de_saida_tem_serializacao_completa():
    """Sanidade: model_dump nao perde visibleWhen (o que o FastAPI envia)."""
    defs = await _list()
    props = _props(defs, "DataInput")
    dumped = props["driveFileId"].model_dump(exclude_none=True)
    assert dumped.get("visibleWhen") == {"field": "context", "in": ["drive"]}


# ── Campos de coluna sugerida ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_campos_de_coluna_declaram_de_onde_vem_a_sugestao():
    """`suggest_columns` diz ao editor QUAL entrada olhar para sugerir nomes de
    coluna. No Join as duas chaves vem de lados diferentes: sugerir as colunas
    de A no campo da chave de B seria pior que nao sugerir nada."""
    props = _props(await _list(), "AttributeJoin")
    assert props["keyA"].suggest_columns == "layerA"
    assert props["keyB"].suggest_columns == "layerB"
    assert props["columns"].suggest_columns == "layerB"


@pytest.mark.asyncio
async def test_no_de_entrada_unica_sugere_de_todas():
    props = _props(await _list(), "AttributeFilter")
    assert props["attributeName"].suggest_columns == "*"


@pytest.mark.asyncio
async def test_campos_de_lista_de_colunas_viraram_fichas_com_sugestao():
    """Os campos que recebem VARIAS colunas declaram type 'chips' (o execute
    aceita lista, JSON-string e o CSV antigo) e `suggest_columns` para o editor
    oferecer as colunas vistas na ultima execucao. Nenhum desses nos tem portas
    declaradas, entao a sugestao e '*'.

    O DEFAULT importa para compat de versao: nos campos que eram type "string",
    ele continua "" — um executor com flow/ anterior ainda valida esses campos
    como string, e uma lista no default derrubava a run inteira so por o
    workflow ter sido salvo na UI nova. RemoveDuplicates ja era object/[] antes,
    entao [] la e o que o executor antigo espera."""
    defs = await _list()
    for no, campo, default in (
        ("RemoveDuplicates", "fields", []),
        ("ChangeDetector", "fields", ""),
        ("ChangeDetector", "ignore_fields", ""),
        ("PublishMap", "visible_fields", ""),
    ):
        prop = _props(defs, no)[campo]
        assert prop.type == "chips", f"{no}.{campo}"
        assert prop.suggest_columns == "*", f"{no}.{campo}"
        assert prop.default == default, f"{no}.{campo}"


@pytest.mark.asyncio
async def test_setfields_sugere_colunas_sem_mudar_o_tipo():
    """SetFields mantem type 'object' — um helper dedicado da web consome esses
    campos — mas os tres declaram `suggest_columns` para o bloco de sugestoes
    aparecer tambem la."""
    props = _props(await _list(), "SetFields")
    for campo in ("setFields", "removeFields", "renameFields"):
        assert props[campo].type == "object", campo
        assert props[campo].suggest_columns == "*", campo


@pytest.mark.asyncio
async def test_sort_e_switch_sugerem_colunas_sem_mudar_o_tipo():
    """Sort.sort_by e Switch.rules ganharam editores dedicados na web
    (linhas campo+direcao / campo+operador+valor+saida) que persistem a MESMA
    lista que o execute le — o type continua 'object' de proposito: mudar o
    formato quebraria fluxos salvos e executores antigos."""
    defs = await _list()
    for no, campo in (("Sort", "sort_by"), ("Switch", "rules")):
        prop = _props(defs, no)[campo]
        assert prop.type == "object", f"{no}.{campo}"
        assert prop.suggest_columns == "*", f"{no}.{campo}"


@pytest.mark.asyncio
async def test_todo_campo_string_que_pede_coluna_declara_sugestao():
    """O censo dos nos achou campos `string` que pedem NOME DE COLUNA sem o
    marcador — o operador via a dica no filtro e nada no Dissolve ao lado, o
    que parecia instabilidade. Fixa os que tem entrada unica (sugerir de todas
    as portas e correto por construcao)."""
    defs = await _list()
    for no, campo in [
        ("Dissolve", "byColumn"),
        ("Conditional", "fieldName"),
        ("GeocodeNode", "address_column"),
    ]:
        assert _props(defs, no)[campo].suggest_columns == "*", f"{no}.{campo}"


@pytest.mark.asyncio
async def test_campo_sem_relacao_com_coluna_nao_declara_nada():
    """A ausencia importa: o editor so mostra o bloco de sugestoes onde ele faz
    sentido, e marcar tudo tornaria a dica ruido."""
    props = _props(await _list(), "AttributeJoin")
    assert props["how"].suggest_columns is None
    assert props["seDuplicado"].suggest_columns is None


# ── A classe de defeito, fechada de vez ──────────────────────────────────────

@pytest.mark.asyncio
async def test_nenhuma_chave_declarada_se_perde_no_caminho():
    """O NodeService copia as propriedades campo a campo (`p.get('x')`), e uma
    linha esquecida faz o descriptor declarar algo que o frontend nunca recebe.
    Ja aconteceu com `visibleWhen` (motivo deste arquivo), com `dynamic_inputs`,
    e de novo com `suggest_columns`.

    Em vez de mais um teste por chave, este percorre TODO o catalogo: para cada
    propriedade, toda chave que o descriptor declara E que o schema conhece tem
    de chegar com o mesmo valor.
    """
    from flow.registry import NODE_REGISTRY
    from app.schemas.node import NodeProperty

    conhecidas = set(NodeProperty.model_fields)
    # `model_dump` e o que permite comparar dado com dado: campos aninhados
    # (as `options` de um select) chegam como modelo Pydantic, e comparar o
    # modelo com o dict cru do descriptor acusaria os 34 selects do catalogo.
    servidos = {
        d.name: {p.name: p.model_dump() for p in d.properties}
        for d in await _list()
    }

    perdidas: list[str] = []
    for nome, cls in NODE_REGISTRY.items():
        if nome not in servidos:
            continue  # no desabilitado no ambiente de teste
        for bruta in (cls.description().get("properties") or []):
            servida = servidos[nome].get(bruta.get("name"))
            if servida is None:
                continue
            for chave in set(bruta) & conhecidas:
                if servida.get(chave) != bruta[chave]:
                    perdidas.append(f"{nome}.{bruta['name']}.{chave}")

    assert not perdidas, (
        "chaves declaradas no descriptor que nao chegam ao frontend: "
        + ", ".join(sorted(perdidas))
    )


# ── Flags de TOPO do NodeDefinition (fora de `properties`) ───────────────────

def _def(defs, node_name):
    for d in defs:
        if d.name == node_name:
            return d
    raise AssertionError(f"no '{node_name}' ausente do catalogo")


@pytest.mark.asyncio
async def test_subworkflowinput_expoe_outputs_from_ports():
    """O trigger do sub-fluxo declara `outputs_from_ports`: e o que faz o editor
    derivar UMA saida por porta declarada e, com isso, o seletor de chave na
    aresta ('escolher') aparecer. Sem repassar a flag pelo catalogo, o trigger
    volta ao handle anonimo/espalhamento e nao ha como escolher o que passar
    adiante — foi exatamente o defeito relatado."""
    d = _def(await _list(), "SubWorkflowInput")
    assert d.outputs_from_ports is True


@pytest.mark.asyncio
async def test_flags_de_topo_do_no_nao_se_perdem():
    """A irma de `test_nenhuma_chave_declarada_se_perde_no_caminho`, para as flags
    de TOPO do NodeDefinition (nao sao `properties`): uma flag nova na
    description() que o NodeService esquece de mapear e descartada pelo Pydantic.
    Ja aconteceu com `dynamic_inputs` e de novo com `outputs_from_ports` (o
    seletor de chave do trigger sumia). Percorre o catalogo inteiro."""
    from flow.registry import NODE_REGISTRY

    FLAGS = ("dynamic_inputs", "dynamic_output", "outputs_from_ports", "requires_credential")
    servidos = {d.name: d for d in await _list()}

    perdidas: list[str] = []
    for nome, cls in NODE_REGISTRY.items():
        servido = servidos.get(nome)
        if servido is None:
            continue  # no desabilitado no ambiente de teste
        info = cls.description() or {}
        for flag in FLAGS:
            if flag in info and getattr(servido, flag) != bool(info[flag]):
                perdidas.append(f"{nome}.{flag}")

    assert not perdidas, (
        "flags de topo declaradas na description() que nao chegam ao frontend: "
        + ", ".join(sorted(perdidas))
    )
