# tests/unit/test_colunas_sugeridas.py
"""Column-list fields became chips with a shared parser.

The chips field stores a JSON string (JSON.stringify); the definitions already
saved hold a real list (object editor) or comma-separated text. The tolerant
parser that was born in AttributeJoin moved up to
`flow.utils.parameter_validation.colunas_pedidas`, and every migrated node must
behave THE SAME with any of the three formats — no data migration.

ChangeDetector is tested in test_change_detector.py (which already has the fake
backend); the descriptor assertions (type "chips" + `suggest_columns`) live in
test_node_service_visible_when.py, alongside the rest of the catalog's.
"""
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point  # noqa: E402

from flow.nodes.action.remove_duplicates import RemoveDuplicates  # noqa: E402
from flow.nodes.outputs.publish_map import PublishMap  # noqa: E402
from flow.utils.parameter_validation import colunas_pedidas  # noqa: E402


# ── O parser compartilhado ───────────────────────────────────────────────────

def test_join_delegou_para_o_utilitario_sem_mudar_de_nome():
    """`_colunas_pedidas` is still importable from the join (execute and tests
    reference it), but it is the SAME object as the utility: a single parser
    for every chips field."""
    from flow.nodes.action.attribute_join import _colunas_pedidas
    assert _colunas_pedidas is colunas_pedidas


def test_parser_aceita_lista_json_csv_e_none():
    assert colunas_pedidas(["a", " b ", ""]) == ["a", "b"]
    assert colunas_pedidas('["a","b"]') == ["a", "b"]
    assert colunas_pedidas("a, b,, ") == ["a", "b"]
    assert colunas_pedidas("") == []
    assert colunas_pedidas(None) == []


# ── RemoveDuplicates: `fields` em fichas ─────────────────────────────────────

def _gdf_com_duplicatas():
    # ("a", 1) appears twice; ("a", 2) differs only in the value. So the subset
    # ["cod"] and the subset ["cod", "valor"] give DIFFERENT results — proof
    # that the parser read both columns, not just the first.
    return gpd.GeoDataFrame(
        {"cod": ["a", "a", "a", "b"], "valor": [1, 1, 2, 9]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 3)],
        crs="EPSG:4326",
    )


@pytest.mark.parametrize("guardado", [
    ["cod"],         # a real list (object editor)
    '["cod"]',       # JSON string — what the chips field stores
    "cod",           # text — old format, already saved
])
async def test_remove_duplicates_mesmo_resultado_nos_tres_formatos(guardado):
    saida = await RemoveDuplicates("n", {"fields": guardado}).execute(
        {"input": _gdf_com_duplicatas()}
    )
    assert len(saida["output"]) == 2          # um "a", um "b"
    assert saida["removed_count"] == 2


@pytest.mark.parametrize("guardado", [
    ["cod", "valor"],
    '["cod","valor"]',
    "cod, valor",
])
async def test_remove_duplicates_duas_colunas_nos_tres_formatos(guardado):
    saida = await RemoveDuplicates("n", {"fields": guardado}).execute(
        {"input": _gdf_com_duplicatas()}
    )
    # So a linha ("a", 1) repetida sai; ("a", 2) e ("b", 9) ficam.
    assert len(saida["output"]) == 3
    assert saida["removed_count"] == 1


async def test_remove_duplicates_vazio_continua_usando_todas_as_colunas():
    """An empty field keeps the usual behavior: uniqueness over all the
    non-geometry columns."""
    saida = await RemoveDuplicates("n", {"fields": ""}).execute(
        {"input": _gdf_com_duplicatas()}
    )
    assert saida["removed_count"] == 1


# ── PublishMap: `visible_fields` em fichas ───────────────────────────────────

async def _publicar(monkeypatch, guardado):
    """Runs the node with the portal mocked and returns the visible_fields sent."""
    capturado: dict = {}

    async def _fake_publish(self, **kwargs):
        capturado.update(kwargs["publish_config"])
        return "layer-1"

    monkeypatch.setattr(PublishMap, "_publish_to_api", _fake_publish)
    # The machine's policy must not block the submission in this test.
    monkeypatch.delenv("EXECUTOR_SYNC_MODE", raising=False)

    no = PublishMap("n", {"title": "Lotes", "visible_fields": guardado})
    no._task_id = "run-1"
    no._workflow_hash = "wf-1"
    no._workspace_id = "ws-1"

    gdf = gpd.GeoDataFrame({"nome": ["x"]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    resultado = await no.execute({"input": gdf})
    assert resultado["output"]["published_layer_id"] == "layer-1"
    return capturado["visible_fields"]


@pytest.mark.parametrize("guardado", [
    ["nome", "area"],
    '["nome","area"]',
    "nome, area",        # old format, already saved in the definitions
])
async def test_publish_map_mesmos_campos_nos_tres_formatos(monkeypatch, guardado):
    assert await _publicar(monkeypatch, guardado) == ["nome", "area"]


async def test_publish_map_vazio_continua_exibindo_todos(monkeypatch):
    assert await _publicar(monkeypatch, "") == []
