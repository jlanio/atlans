# tests/unit/test_colunas_sugeridas.py
"""Campos de lista de colunas viraram fichas ("chips") com parser compartilhado.

O campo de fichas grava JSON-string (JSON.stringify); as definitions ja salvas
guardam lista de verdade (editor de objeto) ou texto separado por virgula. O
parser tolerante que nasceu no AttributeJoin subiu para
`flow.utils.parameter_validation.colunas_pedidas`, e cada no migrado tem de se
comportar IGUAL com qualquer um dos tres formatos — sem migration de dados.

ChangeDetector e testado em test_change_detector.py (que ja tem o backend
fake); as assercoes de descriptor (type "chips" + `suggest_columns`) moram em
test_node_service_visible_when.py, junto das demais do catalogo.
"""
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point  # noqa: E402

from flow.nodes.action.remove_duplicates import RemoveDuplicates  # noqa: E402
from flow.nodes.outputs.publish_map import PublishMap  # noqa: E402
from flow.utils.parameter_validation import colunas_pedidas  # noqa: E402


# ── O parser compartilhado ───────────────────────────────────────────────────

def test_join_delegou_para_o_utilitario_sem_mudar_de_nome():
    """`_colunas_pedidas` continua importavel do join (execute e testes o
    referenciam), mas e o MESMO objeto do utilitario: um parser so para todos
    os campos de fichas."""
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
    # ("a", 1) aparece duas vezes; ("a", 2) so difere no valor. Assim o subset
    # ["cod"] e o subset ["cod", "valor"] dao resultados DIFERENTES — prova que
    # o parser leu as duas colunas, nao so a primeira.
    return gpd.GeoDataFrame(
        {"cod": ["a", "a", "a", "b"], "valor": [1, 1, 2, 9]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 3)],
        crs="EPSG:4326",
    )


@pytest.mark.parametrize("guardado", [
    ["cod"],         # lista de verdade (editor de objeto)
    '["cod"]',       # JSON-string — o que o campo de fichas grava
    "cod",           # texto — formato antigo, ja salvo
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
    """Campo vazio mantem o comportamento de sempre: unicidade por todas as
    colunas nao-geometricas."""
    saida = await RemoveDuplicates("n", {"fields": ""}).execute(
        {"input": _gdf_com_duplicatas()}
    )
    assert saida["removed_count"] == 1


# ── PublishMap: `visible_fields` em fichas ───────────────────────────────────

async def _publicar(monkeypatch, guardado):
    """Roda o no com o portal mockado e devolve o visible_fields enviado."""
    capturado: dict = {}

    async def _fake_publish(self, **kwargs):
        capturado.update(kwargs["publish_config"])
        return "layer-1"

    monkeypatch.setattr(PublishMap, "_publish_to_api", _fake_publish)
    # Politica da maquina nao pode bloquear o envio neste teste.
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
    "nome, area",        # formato antigo, ja salvo nas definitions
])
async def test_publish_map_mesmos_campos_nos_tres_formatos(monkeypatch, guardado):
    assert await _publicar(monkeypatch, guardado) == ["nome", "area"]


async def test_publish_map_vazio_continua_exibindo_todos(monkeypatch):
    assert await _publicar(monkeypatch, "") == []
