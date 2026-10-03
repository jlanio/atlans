# tests/unit/test_ux_diagnostico.py
"""Wrong information shown to the user — the three backend cases.

1. Validation (`validate_service`) dropped from_key/to_key in the Pydantic
   schema, so the simulation always took the "no from_key" branch and named
   the inputs with the parent_id: the preview's schema diverged from what the
   run produced.

2. The catalog publishes the fields of `outputs` (the single source from A13):
   typed, filtering out the protocol's internal keys. Before, there were two
   ways to declare them and the flat one was dropped — no fields in the panel,
   no autocomplete, no port selector.

3. `get_first_gdf` silently chose among several layers, and the choice
   depends on the order of the edges in the definition.
"""
import pytest

from app.services.validate_service import EdgeDefinition, WorkflowDefinition


# ── 1. The preview needs to receive the edge's keys ──────────────────────────

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
    """Regression: this is where they got lost, before WorkflowExecutor(payload)."""
    d = WorkflowDefinition(
        nodes=[{"id": "n1", "name": "WFS", "type": "datasource"}],
        edges=[{"source": "n1", "target": "n2", "from_key": "output", "to_key": "layer"}],
    ).dict()

    assert d["edges"][0]["from_key"] == "output"
    assert d["edges"][0]["to_key"] == "layer"


def test_properties_vira_parameters_e_alias_sobrevive_ao_model_dump():
    """The persisted definition uses `properties` and keeps `alias` at the top
    level; pasting it into validation must not lose either (the alias lint
    depends on it)."""
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


# ── 2. The catalog publishes the fields of `outputs` ─────────────────────────

async def _catalogo(outputs) -> list[str]:
    """Exercises the real NodeService, with a node whose descriptor is controlled."""
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

    # The catalog is cached (@lru_cache): clear it BEFORE, to build from the fake
    # registry, and AFTER, so that registry does not leak into the next tests.
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
    """`__response__` and `__artifact__` are protocol keys, not outputs: the
    executor removes them from what the node delivers (core.py::_actual_keys).
    Without the filter, the Response's `__response__` would show up in the
    schema panel and in autocomplete as if it could be referenced."""
    assert await _catalogo([{"name": "__response__"}, {"name": "status_code"}]) == ["status_code"]


@pytest.mark.asyncio
async def test_response_nao_expoe_a_chave_interna():
    from flow.nodes.outputs.response_node import ResponseNode

    campos = await _catalogo(ResponseNode.description().get("outputs"))

    assert campos == []


@pytest.mark.asyncio
async def test_change_detector_deixa_de_sair_sem_campos():
    """The node promised 4 keys and the catalog delivered none."""
    from flow.nodes.control.change_detector import ChangeDetector

    campos = await _catalogo(ChangeDetector.description().get("outputs"))

    assert "output" in campos and "branch" in campos


# ── 3. An ambiguous layer choice needs to show up in the panel ───────────────

def _no_com_log():
    """Minimal node that records the panel messages in a list."""
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
    """Regression: it processed one and ignored the other without saying anything."""
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
