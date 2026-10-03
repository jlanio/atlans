# tests/unit/test_crs_camadas_binarias.py
"""
Binary layers (A, B): lookup, validation and CRS in a single place.

  UTM         OverlapPercentage estimated A's UTM and B's SEPARATELY. With
              the centers on opposite sides of a zone meridian, A went to
              22S and B to 23S, and `gpd.overlay` between different CRSs only
              WARNS: the intersection came out empty and the percentage
              vanished, with no error. `para_crs_metrico` picks ONE CRS for both.

  POLICY      Each node keeps the policy it had — whoever rejects a different
              CRS keeps rejecting, whoever aligns keeps aligning —, now via
              `BaseNode.get_pair`. The single policy is a follow-up; here it
              is only ANCHORED.

  CLONES      Difference and Symmetric Difference become one base with `how`
              without a saved workflow noticing: identical name, descriptor,
              parameters and messages.

  EVENT LOOP  SpatialFilter reprojected the mask, and Conditional and
              OverlapPercentage estimated the UTM, on the event loop.
"""
from __future__ import annotations

import threading
from unittest.mock import patch

import geopandas as gpd
import pytest
from geopandas.array import GeometryArray
from shapely.geometry import GeometryCollection, Point, box

from flow.nodes.action.overlap_percentage import OverlapPercentage
from flow.nodes.control.conditional import Conditional
from flow.nodes.spatial.clip import ClipNode
from flow.nodes.spatial.compute_area import ComputeArea
from flow.nodes.spatial.difference import DifferenceNode
from flow.nodes.spatial.intersection import IntersectionNode
from flow.nodes.spatial.spatial_filter import SpatialFilterNode
from flow.nodes.spatial.spatial_join import SpatialJoinNode
from flow.nodes.spatial.symmetric_difference import SymmetricDifferenceNode
from flow.nodes.spatial.union import UnionNode


# Two neighboring geographic layers: A's center falls in UTM zone 22S
# (-54° to -48°) and B's in 23S (-48° to -42°). The intersection is 1/3 of each.
def _a(crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame({"a": [1]}, geometry=[box(-49.0, -16.0, -48.1, -15.1)], crs="EPSG:4326")
    return gdf.to_crs(crs)


def _b(crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame({"b": [1]}, geometry=[box(-48.4, -16.0, -47.5, -15.1)], crs="EPSG:4326")
    return gdf.to_crs(crs)


def _percentuais_de_referencia(A, B) -> tuple[float, float]:
    """% of A and of B covered by the intersection, in an EQUAL-AREA projection."""
    area_igual = "EPSG:6933"
    a, b = A.to_crs(area_igual), B.to_crs(area_igual)
    inter = gpd.overlay(a, b, how="intersection").area.sum()
    return inter / a.area.sum() * 100, inter / b.area.sum() * 100


async def _overlap(A, B) -> gpd.GeoDataFrame:
    no = OverlapPercentage("n", {"reference": "both"})
    return (await no.execute({"layerA": A, "layerB": B}))["output"]


# ── UTM: OverlapPercentage ───────────────────────────────────────────────────

async def test_overlap_de_camadas_geograficas_em_zonas_utm_diferentes():
    A, B = _a(), _b()
    assert A.estimate_utm_crs() != B.estimate_utm_crs()  # scenario premise

    out = await _overlap(A, B)

    pct_a, pct_b = _percentuais_de_referencia(A, B)
    assert len(out) == 1, "a intersecao sumiu: A e B foram medidas em UTMs diferentes"
    assert out["percentA"].iloc[0] == pytest.approx(pct_a, rel=2e-3)
    assert out["percentB"].iloc[0] == pytest.approx(pct_b, rel=2e-3)


async def test_overlap_de_camada_projetada_com_geografica_usa_o_crs_de_a():
    """A already projected (SIRGAS 2000 / UTM 22S), B geographic centered in 23S:
    B goes to A's CRS — and the output stays in A's CRS, as before."""
    A, B = _a("EPSG:31982"), _b()

    out = await _overlap(A, B)

    pct_a, pct_b = _percentuais_de_referencia(A, B)
    assert out.crs == A.crs
    assert len(out) == 1
    assert out["percentA"].iloc[0] == pytest.approx(pct_a, rel=2e-3)
    assert out["percentB"].iloc[0] == pytest.approx(pct_b, rel=2e-3)


async def test_overlap_no_mesmo_crs_projetado_nao_reprojeta():
    A, B = _a("EPSG:31982"), _b("EPSG:31982")

    out = await _overlap(A, B)

    esperado_a = gpd.overlay(A, B, how="intersection").area.sum() / A.area.sum() * 100
    assert out.crs == A.crs
    assert out["percentA"].iloc[0] == pytest.approx(esperado_a)


async def test_overlap_com_a_geografica_e_b_ja_projetada_nao_troca_a_zona_de_a():
    """A municipality in eastern SP (A, geographic) against a state layer already
    in SIRGAS 2000 / UTM 23S (B): the COMBINED extent has its center in zone 22,
    and the metric CRS derived from it put both in 22 — changing the percentage,
    the downstream area and the output CRS, which used to be A's."""
    A = gpd.GeoDataFrame({"a": [1]}, geometry=[box(-46.6, -23.7, -46.2, -23.4)], crs="EPSG:4674")
    B = gpd.GeoDataFrame({"b": [1]}, geometry=[box(-53.0, -25.0, -44.0, -20.0)], crs="EPSG:4674").to_crs(
        "EPSG:31983"
    )
    utm_de_a = A.estimate_utm_crs()

    out = await _overlap(A, B)

    assert out.crs == utm_de_a
    assert len(out) == 1


async def test_overlap_com_b_sem_geometria_valida_fica_no_crs_de_a():
    A = _a()
    B = gpd.GeoDataFrame({"b": [1]}, geometry=[None], crs="EPSG:4326")

    out = await _overlap(A, B)

    assert out.crs == A.estimate_utm_crs()
    assert out.empty


@pytest.mark.parametrize("geometrias", [[], [None, None]])
async def test_camada_geografica_sem_geometria_valida_e_erro_de_uso(geometrias):
    """With no valid geometry `estimate_utm_crs` rejects with ValueError (a user
    error: a filter that left nothing). Through the extent, `box(nan, ...)`
    became a GEOSException — "Erro interno inesperado" (unexpected internal
    error) in the panel."""
    vazio = gpd.GeoDataFrame({"a": [1] * len(geometrias)}, geometry=geometrias, crs="EPSG:4326")
    no = Conditional("c", {"metric": "area", "operator": ">", "compareTo": "0"})

    with pytest.raises(RuntimeError) as exc:
        await no.execute({"in": vazio})

    assert isinstance(exc.value.__context__, ValueError)


# ── O helper ─────────────────────────────────────────────────────────────────

def test_para_crs_metrico_com_uma_camada_geografica_e_a_utm_dela():
    """The ComputeArea and Conditional path: the same UTM as before."""
    from flow.utils.geo_helpers import para_crs_metrico

    A = _a()
    (metrica,) = para_crs_metrico(A)
    assert metrica.crs == A.estimate_utm_crs()
    assert A.crs == "EPSG:4326"  # the input one is not touched


def test_para_crs_metrico_nao_mexe_em_crs_projetado_nem_em_camada_sem_crs():
    from flow.utils.geo_helpers import para_crs_metrico

    projetada = _a("EPSG:31982")
    sem_crs = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)])
    assert para_crs_metrico(projetada)[0] is projetada
    assert para_crs_metrico(sem_crs)[0] is sem_crs


def test_para_crs_metrico_poe_as_camadas_no_mesmo_crs():
    from flow.utils.geo_helpers import para_crs_metrico

    A, B = para_crs_metrico(_a(), _b("EPSG:4674"))
    assert A.crs == B.crs
    assert A.crs.is_projected


# ── Os outros dois "geografico -> UTM" continuam medindo igual ───────────────

async def test_compute_area_geografica_mede_na_utm_da_camada():
    A = _a()
    out = (await ComputeArea("n", {"unit": "m2"}).execute({"in": A}))["output"]
    assert out.crs == A.estimate_utm_crs()
    assert out["area"].iloc[0] == pytest.approx(A.to_crs(A.estimate_utm_crs()).area.iloc[0])


async def test_conditional_area_geografica_mede_na_utm_da_camada():
    A = _a()
    no = Conditional("c", {"metric": "area", "operator": ">", "compareTo": "0"})
    out = await no.execute({"in": A})
    assert out["value"] == pytest.approx(A.to_crs(A.estimate_utm_crs()).area.sum())
    assert out["branch"] is True


# ── Reprojection off the event loop ──────────────────────────────────────────

def _registrar_threads(monkeypatch) -> list[bool]:
    """Records, on each to_crs/estimate_utm_crs, whether it ran on the event loop thread."""
    no_loop: list[bool] = []
    for metodo in ("to_crs", "estimate_utm_crs"):
        original = getattr(GeometryArray, metodo)

        def _espiao(self, *args, _original=original, **kwargs):
            no_loop.append(threading.current_thread() is threading.main_thread())
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(GeometryArray, metodo, _espiao)
    return no_loop


async def test_spatial_filter_reprojeta_a_mascara_fora_do_event_loop(monkeypatch):
    camada = gpd.GeoDataFrame({"id": [0, 1]}, geometry=[Point(1, 1), Point(50, 50)], crs="EPSG:3857")
    mascara = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:3857").to_crs("EPSG:4326")
    no_loop = _registrar_threads(monkeypatch)

    no = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects"})
    out = (await no.execute({"layer": camada, "mask": mascara}))["output"]

    assert set(out["id"]) == {0}  # still aligns the mask to the layer's CRS
    assert no_loop and not any(no_loop), "to_crs rodou no event loop"


@pytest.mark.parametrize("rodar", [
    lambda: Conditional("c", {"metric": "area", "compareTo": "0"}).execute({"in": _a()}),
    lambda: OverlapPercentage("n", {}).execute({"layerA": _a(), "layerB": _b()}),
], ids=["Conditional", "OverlapPercentage"])
async def test_utm_e_estimada_fora_do_event_loop(rodar, monkeypatch):
    coroutine = rodar()  # the layers are built before the spy
    no_loop = _registrar_threads(monkeypatch)
    await coroutine
    assert no_loop and not any(no_loop), "estimate_utm_crs/to_crs rodou no event loop"


# ── CRS policy: each node keeps its own ──────────────────────────────────────

def _par_em_crs_diferentes():
    A = gpd.GeoDataFrame({"a": [1]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:3857")
    B = gpd.GeoDataFrame({"b": [1]}, geometry=[box(1, 1, 3, 3)], crs="EPSG:3857").to_crs("EPSG:4326")
    return A, B


@pytest.mark.parametrize("classe,operacao", [
    (DifferenceNode, "operação de diferença"),
    (SymmetricDifferenceNode, "diferença simétrica"),
    (UnionNode, "união"),
    (IntersectionNode, "operação de interseção"),
])
async def test_quem_recusava_crs_diferente_continua_recusando(classe, operacao):
    A, B = _par_em_crs_diferentes()
    with pytest.raises(ValueError) as erro:
        await classe("n", {}).execute({"layerA": A, "layerB": B})
    assert str(erro.value) == (
        "As camadas possuem CRS diferentes. Adicione um nó de reprojeção "
        f"para padronizar antes da {operacao}."
    )


async def test_quem_alinhava_crs_diferente_continua_alinhando():
    A, B = _par_em_crs_diferentes()

    recorte = (await ClipNode("n", {}).execute({"layerA": A, "layerB": B}))["output"]
    juncao = (await SpatialJoinNode("n", {"how": "inner", "predicate": "intersects"})
              .execute({"layerA": A, "layerB": B}))["output"]
    filtro = (await SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects"})
              .execute({"layer": A, "mask": B}))["output"]

    assert recorte.crs == A.crs and recorte.area.sum() == pytest.approx(1.0, rel=1e-6)
    assert len(juncao) == 1 and juncao.crs == A.crs
    assert len(filtro) == 1


@pytest.mark.parametrize("classe,params,sem_crs,mensagem", [
    (ClipNode, {}, "layerB",
     "A máscara 'layerB' de entrada não possui CRS definido. "
     "Adicione um nó de reprojeção antes desta operação."),
    (SpatialJoinNode, {"how": "inner", "predicate": "intersects"}, "layerA",
     "A camada 'layerA' de entrada não possui CRS definido. "
     "Adicione um nó de reprojeção antes desta operação."),
], ids=["Clip", "SpatialJoin"])
async def test_quem_alinha_exige_crs_nas_duas_camadas(classe, params, sem_crs, mensagem):
    entradas = {
        chave: gpd.GeoDataFrame(
            {"v": [1]}, geometry=[box(0, 0, 2, 2)],
            crs=None if chave == sem_crs else "EPSG:3857",
        )
        for chave in ("layerA", "layerB")
    }
    with pytest.raises(ValueError) as erro:
        await classe("n", params).execute(entradas)
    assert str(erro.value) == mensagem


async def test_spatial_filter_segue_tolerando_camada_sem_crs():
    camada = gpd.GeoDataFrame({"id": [0, 1]}, geometry=[Point(1, 1), Point(50, 50)])
    mascara = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    no = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects"})
    out = (await no.execute({"layer": camada, "mask": mascara}))["output"]
    assert set(out["id"]) == {0}


async def test_intersecao_confere_os_tipos_depois_da_higiene():
    """Layer A has only empty geometry: the hygiene step empties it and the result
    is empty — before looking at B's GeometryCollection, as it always was."""
    from shapely.geometry import Polygon

    A = gpd.GeoDataFrame({"a": [1]}, geometry=[Polygon()], crs="EPSG:3857")
    B = gpd.GeoDataFrame({"b": [1]}, geometry=[GeometryCollection([box(0, 0, 1, 1)])], crs="EPSG:3857")
    out = (await IntersectionNode("n", {}).execute({"layerA": A, "layerB": B}))["output"]
    assert out.empty


def test_get_pair_recusa_politica_desconhecida():
    A, B = _par_em_crs_diferentes()
    with pytest.raises(ValueError, match="alinha"):
        DifferenceNode("n", {}).get_pair({"layerA": A, "layerB": B}, crs="alinha")


# ── Diferenca e Diferenca Simetrica: clones -> uma base ──────────────────────

DESCRICAO_DIFERENCA = {
    'name': 'DifferenceNode',
    'alias': 'Diferença Espacial',
    'description': 'Realiza a operação de diferença espacial (A - B).',
    'type': 'spatial',
    'properties': [],
    'inputs': [
        {'name': 'layerA', 'type': 'geodataframe', 'description': 'Camada A (GeoDataFrame base).'},
        {'name': 'layerB', 'type': 'geodataframe', 'description': 'Camada B (GeoDataFrame a subtrair).'},
    ],
    'outputs': [
        {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da diferença espacial A - B'},
    ],
}

DESCRICAO_DIFERENCA_SIMETRICA = {
    'name': 'SymmetricDifferenceNode',
    'alias': 'Diferença Simétrica',
    'description': 'Realiza a operação de diferença simétrica (A △ B).',
    'type': 'spatial',
    'properties': [],
    'inputs': [
        {'name': 'layerA', 'type': 'geodataframe', 'description': 'Primeira camada (GeoDataFrame).'},
        {'name': 'layerB', 'type': 'geodataframe', 'description': 'Segunda camada (GeoDataFrame).'},
    ],
    'outputs': [
        {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da diferença simétrica entre as camadas'},
    ],
}


def test_workflow_salvo_nao_percebe_a_base_comum():
    from flow.registry import NODE_REGISTRY

    assert NODE_REGISTRY["DifferenceNode"] is DifferenceNode
    assert NODE_REGISTRY["SymmetricDifferenceNode"] is SymmetricDifferenceNode
    assert DifferenceNode.description() == DESCRICAO_DIFERENCA
    assert SymmetricDifferenceNode.description() == DESCRICAO_DIFERENCA_SIMETRICA


@pytest.mark.parametrize("classe,how,operacao,rotulo", [
    (DifferenceNode, "difference", "operação de diferença", "diferença"),
    (SymmetricDifferenceNode, "symmetric_difference", "diferença simétrica", "diferença simétrica"),
])
async def test_diferencas_mantem_resultado_e_mensagens(classe, how, operacao, rotulo):
    A = gpd.GeoDataFrame({"a": [1]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:3857")
    B = gpd.GeoDataFrame({"b": [1]}, geometry=[box(1, 1, 3, 3)], crs="EPSG:3857")

    out = (await classe("n", {}).execute({"layerA": A, "layerB": B}))["output"]
    esperado = gpd.overlay(A, B, how=how)
    assert out.geometry.union_all().equals(esperado.geometry.union_all())

    colecao = gpd.GeoDataFrame(geometry=[GeometryCollection([Point(0, 0), box(0, 0, 1, 1)])], crs="EPSG:3857")
    with pytest.raises(TypeError, match=f"^Geometria incompatível para {operacao}: "):
        await classe("n", {}).execute({"layerA": colecao, "layerB": B})

    with patch("geopandas.overlay", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match=f"^Erro na operação de {rotulo}: boom$"):
            await classe("n", {}).execute({"layerA": A, "layerB": B})
