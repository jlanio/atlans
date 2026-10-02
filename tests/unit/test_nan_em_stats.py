# tests/unit/test_nan_em_stats.py
"""NaN nos stats prendia o run em 'running' para sempre.

Cadeia real, observada em producao: um filtro espacial retorna ZERO feicoes ->
`GeoDataFrame.total_bounds` e [nan, nan, nan, nan] -> `round(float('nan'), 6)`
devolve nan sem levantar, entao o try/except do collector nao pegava -> o nan
viaja nos stats (json.dumps do Python emite NaN, extensao fora da spec, e
json.loads o aceita de volta) -> chega em WorkflowRun.node_stats, que e JSONB ->
Postgres recusa o INSERT -> a excecao sobe ANTES do commit do status -> o run
fica 'running' e o resultado vai para run_dead_letter.

O workflow tinha concluido: 46 resultados estavam na fila morta quando isto foi
diagnosticado.
"""
import json
import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.run_result_consumer import _json_seguro, _update_run_status


# ── Origem: bbox de GeoDataFrame vazio ───────────────────────────────────────

def test_bbox_de_geodataframe_vazio_vira_none():
    import geopandas as gpd
    from flow.metrics.collector import _bbox_finito

    vazio = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")

    assert _bbox_finito(vazio) is None


def test_bbox_de_geodataframe_com_feicoes_e_preservado():
    import geopandas as gpd
    from shapely.geometry import Point
    from flow.metrics.collector import _bbox_finito

    gdf = gpd.GeoDataFrame(
        {"geometry": [Point(-60.5, -11.5), Point(-60.1, -11.1)]},
        geometry="geometry", crs="EPSG:4326",
    )

    assert _bbox_finito(gdf) == [-60.5, -11.5, -60.1, -11.1]


def test_metricas_leves_omitem_bbox_quando_vazio():
    import geopandas as gpd
    from flow.metrics.collector import _extract_lightweight_metrics

    vazio = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")
    out = _extract_lightweight_metrics(vazio)

    assert out["feature_count"] == 0
    assert "bbox" not in out


# ── Defesa: saneamento antes do JSONB ────────────────────────────────────────

def test_json_seguro_troca_nan_e_infinito_por_none():
    sujo = {
        "spatial": {"bbox": [float("nan")] * 4, "feature_count": 0},
        "lista": [1.5, float("inf"), float("-inf")],
        "ok": {"duration_ms": 12.5, "nome": "WFS", "flag": True, "nada": None},
    }

    limpo = _json_seguro(sujo)

    assert limpo["spatial"]["bbox"] == [None, None, None, None]
    assert limpo["lista"] == [1.5, None, None]
    # Valores válidos passam intactos.
    assert limpo["ok"] == {"duration_ms": 12.5, "nome": "WFS", "flag": True, "nada": None}


def test_json_seguro_produz_json_valido():
    """O critério real: `allow_nan=False` é o que o Postgres exige."""
    limpo = _json_seguro({"bbox": [float("nan"), float("inf")]})

    json.dumps(limpo, allow_nan=False)   # não pode levantar


@pytest.mark.asyncio
async def test_update_run_status_grava_com_stats_saneados():
    """Regressão: era aqui que o commit estourava e o run ficava 'running'."""
    run, db = MagicMock(), MagicMock(commit=AsyncMock())
    payload = {
        "task_id": "run-1",
        "status": "success",
        "error_message": None,
        "stats": {"no-1": {"spatial": {"bbox": [float("nan")] * 4}}},
        "end_time": "2026-08-05T13:00:27.154545+00:00",
        "duration_seconds": 7.075,
    }

    await _update_run_status(db, run, payload)

    assert run.status == "success"
    assert run.node_stats["no-1"]["spatial"]["bbox"] == [None, None, None, None]
    # O que o Postgres teria recusado agora serializa.
    json.dumps(run.node_stats, allow_nan=False)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_stats_validos_chegam_intactos():
    run, db = MagicMock(), MagicMock(commit=AsyncMock())
    stats = {"no-1": {"duration_ms": 2887.09, "spatial": {"bbox": [-63.1, -13.2, -60.5, -10.6]}}}
    payload = {
        "task_id": "run-1", "status": "success", "error_message": None,
        "stats": stats,
        "end_time": "2026-08-05T13:00:27+00:00", "duration_seconds": 7.0,
    }

    await _update_run_status(db, run, payload)

    assert run.node_stats["no-1"]["spatial"]["bbox"] == [-63.1, -13.2, -60.5, -10.6]
    assert math.isclose(run.node_stats["no-1"]["duration_ms"], 2887.09)


# ── As métricas: bbox, spatial_summary e operation_types ─────────────────────

@pytest.mark.asyncio
async def test_persist_metrics_saneia_nan_antes_das_colunas_json():
    """Regressão: 37 resultados na fila morta com `Token "NaN" is invalid`.

    O saneamento cobria só o node_stats; o bbox de node_run_metrics e o
    spatial_summary de workflow_run_metrics são colunas JSON também, e o
    INSERT delas morria no Postgres com um executor antigo (anterior ao
    `_bbox_finito`).
    """
    from datetime import datetime, timezone

    from app.core.run_result_consumer import _persist_metrics
    from app.models.run_metrics import NodeRunMetrics, WorkflowRunMetrics

    adicionados = []
    sem_linha = MagicMock()
    sem_linha.scalar_one_or_none.return_value = None
    db = MagicMock(
        commit=AsyncMock(),
        execute=AsyncMock(return_value=sem_linha),
        add=adicionados.append,
    )
    run = MagicMock(
        task_id="run-1", workflow_hash="wf-1", workspace_id="ws-1", host=None,
        start_time=datetime(2026, 8, 5, 13, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 8, 5, 13, 1, tzinfo=timezone.utc),
        duration_seconds=60.0, status="success", error_message=None,
    )
    metrics = {
        "run": {"cpu_avg_pct": float("nan"), "operation_types": {"clip": float("inf")}},
        "spatial_summary": {"bbox": [float("nan")] * 4},
        "nodes": {"no-1": {"node_name": "Clip", "spatial": {"bbox": [float("nan")] * 4}}},
    }

    await _persist_metrics(db, run, metrics, {})

    wrm = next(o for o in adicionados if isinstance(o, WorkflowRunMetrics))
    nrm = next(o for o in adicionados if isinstance(o, NodeRunMetrics))
    assert nrm.bbox == [None, None, None, None]
    assert wrm.spatial_summary == {"bbox": [None, None, None, None]}
    assert wrm.operation_types == {"clip": None}
    assert wrm.cpu_avg_pct is None
    # O que o Postgres teria recusado agora serializa.
    json.dumps([nrm.bbox, wrm.spatial_summary, wrm.operation_types], allow_nan=False)
    db.commit.assert_awaited_once()
