# tests/unit/test_ux_diagnostico.py
"""Informação errada mostrada ao usuário — os três casos do backend.

1. A validacao (`validate_service`) descartava from_key/to_key no schema
   Pydantic, entao a simulacao entrava sempre no ramo "sem from_key" e nomeava
   as entradas com o parent_id: o schema do preview divergia do que o run
   produzia.

2. O catalogo publica os campos de `outputs` (a fonte unica do A13):
   tipados, filtrando as chaves internas do protocolo. Antes havia duas
   formas de declarar e a plana era descartada — sem campos no painel,
   sem autocomplete, sem seletor de porta.

3. `get_first_gdf` escolhia entre varias camadas em silencio, e a escolha
   depende da ordem das arestas na definition.
"""
import pytest

from app.services.validate_service import EdgeDefinition, WorkflowDefinition


# ── 1. O preview precisa receber as chaves da aresta ─────────────────────────

def test_edge_definition_preserva_as_chaves():
    edge = EdgeDefinition(source="a", target="b", from_key="bbox_string", to_key="layerA")

    assert edge.from_key == "bbox_string"
    assert edge.to_key == "layerA"


def test_edge_definition_preserva_a_condicao_do_ramo():
    assert EdgeDefinition(source="a", target="b", condition=False).condition is False


def test_chaves_sao_opcionais():
    edge = EdgeDefinition(source="a", target="b")

    assert edge.from_key is None and edge.to_key is None and edge.condition is None


def test_chaves_sobrevivem_ao_dict_que_vai_para_o_executor():
    """Regressão: era aqui que se perdiam, antes de WorkflowExecutor(payload)."""
    d = WorkflowDefinition(
        nodes=[{"id": "n1", "name": "WFS", "type": "datasource"}],
        edges=[{"source": "n1", "target": "n2", "from_key": "output", "to_key": "layer"}],
    ).dict()

    assert d["edges"][0]["from_key"] == "output"
    assert d["edges"][0]["to_key"] == "layer"


def test_properties_vira_parameters_e_alias_sobrevive_ao_model_dump():
    """A definition persistida usa `properties` e guarda `alias` no topo; colar
    na validação não pode perder nenhum dos dois (o lint de alias depende)."""
    from app.services.validate_service import NodeParameter

    d = NodeParameter(id="n1", name="WFS", type="datasource", properties={"a": 1}, alias="Caixa").model_dump()

    assert d["parameters"] == {"a": 1}
    assert d["alias"] == "Caixa"
    assert "properties" not in d


def test_parameters_vence_properties_em_conflito():
    from app.services.validate_service import NodeParameter

    d = NodeParameter(
        id="n1", name="WFS", type="datasource",
        properties={"a": 1, "b": 2}, parameters={"a": 9},
    ).model_dump()

    assert d["parameters"] == {"a": 9, "b": 2}


# ── 2. O catálogo publica os campos de `outputs` ─────────────────────────────

async def _catalogo(outputs) -> list[str]:
    """Exercita o NodeService de verdade, com um nó de descriptor controlado."""
    from unittest.mock import AsyncMock, patch
    from app.services.node_service import NodeService
    from flow.nodes.base import BaseNode

    class _NoFalso(BaseNode):
        @classmethod
        def description(cls):
            return {"name": "_NoFalso", "type": "action", "properties": [],
                    "outputs": outputs}

        async def execute(self, inputs):
            return {}

    from app.services.node_service import _catalogo_completo

    # O catalogo e cacheado (@lru_cache): limpa ANTES para montar do registry
    # fingido e DEPOIS para nao vazar esse registry para os proximos testes.
    with patch("app.services.node_service.NODE_REGISTRY", {"_NoFalso": _NoFalso}), \
         patch("app.services.node_service.disabled_names", new=AsyncMock(return_value=set())):
        _catalogo_completo.cache_clear()
        defs = await NodeService().list_nodes(db=None)
    _catalogo_completo.cache_clear()

    return [f.name for f in (defs[0].outputs or [])]


@pytest.mark.asyncio
async def test_catalogo_le_os_campos_na_ordem():
    campos = [{"name": "output", "type": "geodataframe"}, {"name": "branch", "type": "boolean"}]

    assert await _catalogo(campos) == ["output", "branch"]


@pytest.mark.asyncio
async def test_catalogo_tolera_lixo():
    assert await _catalogo([None, {"type": "x"}, 42]) == []
    assert await _catalogo(None) == []


@pytest.mark.asyncio
async def test_chaves_internas_do_protocolo_ficam_de_fora():
    """`__response__` e `__artifact__` sao chaves do protocolo, nao saidas: o
    executor as remove do que o no entrega (core.py::_actual_keys). Sem o
    filtro, `__response__` do Response apareceria no painel de schema e no
    autocomplete como se desse para referenciar."""
    assert await _catalogo([{"name": "__response__"}, {"name": "status_code"}]) == ["status_code"]


@pytest.mark.asyncio
async def test_response_nao_expoe_a_chave_interna():
    from flow.nodes.outputs.response_node import ResponseNode

    campos = await _catalogo(ResponseNode.description().get("outputs"))

    assert campos == []


@pytest.mark.asyncio
async def test_change_detector_deixa_de_sair_sem_campos():
    """O nó prometia 4 chaves e o catálogo não entregava nenhuma."""
    from flow.nodes.control.change_detector import ChangeDetector

    campos = await _catalogo(ChangeDetector.description().get("outputs"))

    assert "output" in campos and "branch" in campos


# ── 3. Escolha ambígua de camada precisa aparecer no painel ──────────────────

def _no_com_log():
    """Nó mínimo que grava as mensagens de painel numa lista."""
    from flow.nodes.base import BaseNode

    class _No(BaseNode):
        @classmethod
        def description(cls):
            return {"name": "_No", "properties": []}

        async def execute(self, inputs):
            return {}

    no = _No("n1", {})
    linhas: list[str] = []
    no.log = linhas.append          # type: ignore[method-assign]
    return no, linhas


def _gdf(n=1):
    import geopandas as gpd
    from shapely.geometry import Point
    return gpd.GeoDataFrame({"geometry": [Point(i, i) for i in range(n)]}, crs="EPSG:4326")


def test_uma_camada_nao_avisa():
    no, linhas = _no_com_log()

    no.get_first_gdf({"output": _gdf()})

    assert linhas == []


def test_duas_camadas_avisam_no_painel():
    """Regressão: processava uma e ignorava a outra sem dizer nada."""
    no, linhas = _no_com_log()

    escolhido = no.get_first_gdf({"cadastro": _gdf(2), "visitas": _gdf(3)})

    assert len(escolhido) == 2          # segue usando a primeira
    assert len(linhas) == 1
    assert "cadastro" in linhas[0] and "visitas" in linhas[0]


def test_gdf_vazio_nao_conta_como_candidato():
    no, linhas = _no_com_log()

    no.get_first_gdf({"vazio": _gdf(0), "cheio": _gdf(2)})

    assert linhas == []


def test_sem_camada_nenhuma_continua_falhando_alto():
    no, _linhas = _no_com_log()

    with pytest.raises(ValueError, match="Nenhum GeoDataFrame"):
        no.get_first_gdf({"texto": "abc"})
