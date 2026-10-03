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

def test_edge_definition_preserves_the_keys():
    edge = EdgeDefinition(source="a", target="b", from_key="bbox_string", to_key="layerA")

    assert edge.from_key == "bbox_string"
    assert edge.to_key == "layerA"


def test_edge_definition_preserves_the_branch_condition():
    assert EdgeDefinition(source="a", target="b", condition=False).condition is False


def test_keys_are_optional():
    edge = EdgeDefinition(source="a", target="b")

    assert edge.from_key is None and edge.to_key is None and edge.condition is None


def test_keys_survive_the_dict_sent_to_the_executor():
    """Regression: this is where they got lost, before WorkflowExecutor(payload)."""
    d = WorkflowDefinition(
        nodes=[{"id": "n1", "name": "WFS", "type": "datasource"}],
        edges=[{"source": "n1", "target": "n2", "from_key": "output", "to_key": "layer"}],
    ).dict()

    assert d["edges"][0]["from_key"] == "output"
    assert d["edges"][0]["to_key"] == "layer"


def test_properties_becomes_parameters_and_alias_survives_model_dump():
    """The persisted definition uses `properties` and keeps `alias` at the top
    level; pasting it into validation must not lose either (the alias lint
    depends on it)."""
    from app.services.validate_service import NodeParameter

    d = NodeParameter(id="n1", name="WFS", type="datasource", properties={"a": 1}, alias="Caixa").model_dump()

    assert d["parameters"] == {"a": 1}
    assert d["alias"] == "Caixa"
    assert "properties" not in d


def test_parameters_wins_over_properties_on_conflict():
    from app.services.validate_service import NodeParameter

    d = NodeParameter(
        id="n1", name="WFS", type="datasource",
        properties={"a": 1, "b": 2}, parameters={"a": 9},
    ).model_dump()

    assert d["parameters"] == {"a": 9, "b": 2}


# ── 2. The catalog publishes the fields of `outputs` ─────────────────────────

async def _catalog(outputs) -> list[str]:
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

    from app.services.node_service import _full_catalog

    # The catalog is cached (@lru_cache): clear it BEFORE, to build from the fake
    # registry, and AFTER, so that registry does not leak into the next tests.
    with patch("app.services.node_service.NODE_REGISTRY", {"_NoFalso": _NoFalso}), \
         patch("app.services.node_service.disabled_names", new=AsyncMock(return_value=set())):
        _full_catalog.cache_clear()
        defs = await NodeService().list_nodes(db=None)
    _full_catalog.cache_clear()

    return [f.name for f in (defs[0].outputs or [])]


@pytest.mark.asyncio
async def test_catalog_reads_the_fields_in_order():
    campos = [{"name": "output", "type": "geodataframe"}, {"name": "branch", "type": "boolean"}]

    assert await _catalog(campos) == ["output", "branch"]


@pytest.mark.asyncio
async def test_catalog_tolerates_garbage():
    assert await _catalog([None, {"type": "x"}, 42]) == []
    assert await _catalog(None) == []


@pytest.mark.asyncio
async def test_internal_protocol_keys_are_left_out():
    """`__response__` and `__artifact__` are protocol keys, not outputs: the
    executor removes them from what the node delivers (core.py::_actual_keys).
    Without the filter, the Response's `__response__` would show up in the
    schema panel and in autocomplete as if it could be referenced."""
    assert await _catalog([{"name": "__response__"}, {"name": "status_code"}]) == ["status_code"]


@pytest.mark.asyncio
async def test_response_does_not_expose_the_internal_key():
    from flow.nodes.outputs.response_node import ResponseNode

    campos = await _catalog(ResponseNode.description().get("outputs"))

    assert campos == []


@pytest.mark.asyncio
async def test_change_detector_no_longer_outputs_without_fields():
    """The node promised 4 keys and the catalog delivered none."""
    from flow.nodes.control.change_detector import ChangeDetector

    campos = await _catalog(ChangeDetector.description().get("outputs"))

    assert "output" in campos and "branch" in campos


# ── 3. An ambiguous layer choice needs to show up in the panel ───────────────

def _node_with_log():
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


def test_one_layer_does_not_warn():
    no, linhas = _node_with_log()

    no.get_first_gdf({"output": _gdf()})

    assert linhas == []


def test_two_layers_warn_on_the_panel():
    """Regression: it processed one and ignored the other without saying anything."""
    no, linhas = _node_with_log()

    escolhido = no.get_first_gdf({"cadastro": _gdf(2), "visitas": _gdf(3)})

    assert len(escolhido) == 2          # segue usando a primeira
    assert len(linhas) == 1
    assert "cadastro" in linhas[0] and "visitas" in linhas[0]


def test_empty_gdf_does_not_count_as_candidate():
    no, linhas = _node_with_log()

    no.get_first_gdf({"vazio": _gdf(0), "cheio": _gdf(2)})

    assert linhas == []


def test_with_no_layer_still_fails_loudly():
    no, _lines = _node_with_log()

    with pytest.raises(ValueError, match="Nenhum GeoDataFrame"):
        no.get_first_gdf({"texto": "abc"})
