# tests/unit/test_executor_perf_auditoria.py
"""Regression for PR audit-executor-perf: move geopandas/heavy I/O off the event loop.

Each fix gets a test; the docstring names the mutation that breaks ONLY it.
Where "runs in a thread" is not observable through behavior (it would need an
async harness with timing), the test is a source check via AST/string — the
same pattern as the PythonScript timeout source checks (#162): the mutation
(unwrapping the `asyncio.to_thread`) reverts the source and breaks the test.

The fixes with their own logic (pure helpers and the lock) have BEHAVIOR
tests: `_montar_envelope_gzip`, `_concat_chunks`, the ResourceTracker lock and
the ExpressionService concurrent compilation.
"""
from __future__ import annotations

import ast
import concurrent.futures
import gzip
import json
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _source(rel: str) -> str:
    return (RAIZ / rel).read_text(encoding="utf-8")


def _to_thread_targets(fonte: str) -> list[str]:
    """Names/attributes that are the FIRST argument of `asyncio.to_thread(...)`
    (the function that actually runs in the thread). A lambda becomes '<lambda>'."""
    arvore = ast.parse(fonte)
    alvos: list[str] = []
    for n in ast.walk(arvore):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "to_thread" and n.args):
            continue
        primeiro = n.args[0]
        if isinstance(primeiro, ast.Name):
            alvos.append(primeiro.id)
        elif isinstance(primeiro, ast.Attribute):
            alvos.append(primeiro.attr)
        elif isinstance(primeiro, ast.Lambda):
            alvos.append("<lambda>")
    return alvos


def _lambdas_de_to_thread(fonte: str) -> list[str]:
    """Source (unparse) of each lambda passed as the 1st arg to `asyncio.to_thread`."""
    arvore = ast.parse(fonte)
    fontes: list[str] = []
    for n in ast.walk(arvore):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "to_thread" and n.args
                and isinstance(n.args[0], ast.Lambda)):
            fontes.append(ast.unparse(n.args[0]))
    return fontes


# ── Pure helpers (behavior test) ─────────────────────────────────────────────

def test_build_gzip_envelope_embeds_geojson_without_reparsing():
    """Mutation: break the splice `cabeca[:-1] + ',\"geojson\":' + geojson_str + '}'`
    (e.g.: go back to json.dumps with the already parsed geojson, or concatenate wrongly).

    The helper must produce VALID JSON with the raw geojson embedded and return
    (compressed, payload_size)."""
    from flow.nodes.outputs.publish_map import _montar_envelope_gzip

    cabecalho = {
        "workflow_hash": "wf1", "workspace_id": "ws1", "run_id": "r1",
        "layer_key": "camada", "publish_config": {"title": "T", "color": "#fff"},
    }
    geojson_str = '{"type":"FeatureCollection","features":[{"a":1},{"a":2}]}'

    comprimido, tamanho = _montar_envelope_gzip(cabecalho, geojson_str)
    assert isinstance(comprimido, bytes)
    cru = gzip.decompress(comprimido)
    assert len(cru) == tamanho
    obj = json.loads(cru)  # must be valid JSON
    assert obj["workflow_hash"] == "wf1"
    assert obj["publish_config"]["title"] == "T"
    # the geojson went in whole, without becoming a string or getting lost
    assert obj["geojson"]["type"] == "FeatureCollection"
    assert len(obj["geojson"]["features"]) == 2


def test_concat_chunks_junta_e_reindexa():
    """Mutation: `_concat_chunks` returning only the 1st chunk, or without ignore_index.

    Joins each chunk's DataFrames preserving the order and with index 0..n-1
    (parity with the old single DataFrame); empty list -> empty DataFrame."""
    from flow.nodes.datasource.database_query import _concat_chunks

    assert _concat_chunks([]).empty
    a = pd.DataFrame([{"x": 1}, {"x": 2}])
    b = pd.DataFrame([{"x": 3}])
    juntos = _concat_chunks([a, b])
    assert list(juntos["x"]) == [1, 2, 3]
    assert list(juntos.index) == [0, 1, 2]  # RangeIndex reindexado


# ── ResourceTracker: lock (concorrencia) ─────────────────────────────────────

def test_resource_tracker_concurrent_sampling_loses_no_samples():
    """Mutation: remove the `with self._lock:` from `sample()`.

    50 threads sample the SAME tracker (run_tracker is shared, and end_node now
    runs in a thread). With the lock, all samples get in and `summary()` does
    not blow up; without it, `_samples.append` races with the iteration in
    `summary()` (list changed size) or loses samples."""
    from flow.metrics.collector import ResourceTracker

    tr = ResourceTracker()

    def amostra(_):
        tr.sample()

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(amostra, range(50)))

    assert tr.summary()["samples"] == 50


def test_resource_tracker_uses_lock_in_source():
    """Mutation: remove the ResourceTracker lock (the deterministic catcher).

    The concurrent test above is probabilistic; this one pins the lock's presence."""
    fonte = _source("flow/metrics/collector.py")
    assert "self._lock = threading.Lock()" in fonte
    assert "with self._lock:" in fonte


# ── ExpressionService: LRU cache with lock ───────────────────────────────────

def test_expression_service_compiles_concurrently_without_corruption():
    """Mutation: remove the lock/double-check of `_compiled`.

    300 distinct sources compiled by 16 threads (repeated to exercise the
    cache): without the lock, `move_to_end`/`popitem`/`__setitem__` corrupt the
    OrderedDict (wrong size) or raise."""
    from flow.utils.expression_service import ExpressionService

    svc = ExpressionService()
    fontes = [f"{{{{ {i} }}}}" for i in range(300)]

    def um(s: str) -> str:
        return svc._compiled(s).render()

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(um, fontes * 4))

    assert len(res) == 1200
    # 300 < ceiling (512): all cached, one per source, with no duplicates or losses
    assert len(svc._template_cache) == 300


def test_expression_service_has_lock_in_source():
    """Mutation: remove the _compiled lock (deterministic catcher for the one above)."""
    fonte = _source("flow/utils/expression_service.py")
    assert "import threading" in fonte
    assert "self._template_cache_lock = threading.Lock()" in fonte
    assert "with self._template_cache_lock:" in fonte


# ── Source-checks: o pesado sai do event loop (asyncio.to_thread) ─────────────

def test_spill_read_goes_to_thread():
    """Mutacao: `parent_outputs = _load_from_disk(...)` sincrono de volta."""
    alvos = _to_thread_targets(_source("flow/executor/core.py"))
    assert "_load_from_disk" in alvos, "a leitura do spill tem de ir para thread"


def test_end_node_metrics_go_to_thread():
    """Mutacao: `self.metrics_collector.end_node(...)` sincrono de volta."""
    alvos = _to_thread_targets(_source("flow/executor/core.py"))
    assert "end_node" in alvos, "end_node (O(n)) tem de ir para thread"


@pytest.mark.parametrize("rel,func", [
    ("flow/nodes/outputs/save_geojson.py", "persistir_artefato"),
    ("flow/nodes/outputs/save_to_shapefile.py", "persistir_artefato"),
    ("flow/nodes/outputs/save_to_geoparquet.py", "persistir_artefato"),
    ("flow/nodes/outputs/save_to_s3.py", "persistir_artefato"),
    ("flow/nodes/outputs/data_output.py", "persistir_artefato"),
    ("flow/nodes/outputs/data_output.py", "upload_artifact_to_minio"),
    ("flow/nodes/outputs/carta_imagem.py", "persistir_artefato"),
    ("flow/nodes/outputs/send_email.py", "upload_artifact_to_minio"),
])
def test_artifact_upload_goes_to_thread(rel, func):
    """Mutation: unwrap the `asyncio.to_thread` of an upload (direct call).

    The upload (blocking httpx/disk) must run in a thread — the function appears
    as the 1st ARG of `to_thread`, not as the `func` of a direct Call."""
    alvos = _to_thread_targets(_source(rel))
    assert func in alvos, f"{rel}: {func} tem de rodar em asyncio.to_thread"


def test_purge_goes_to_thread():
    """Mutation: synchronous `n = purgar(...)` back in _receive_loop."""
    alvos = _to_thread_targets(_source("executor/connection.py"))
    assert "purgar" in alvos, "purgar (I/O de disco) tem de ir para thread"


def test_buffer_validates_geometries_in_thread():
    """Mutation: synchronous `is_valid` filter back in the loop."""
    fonte = _source("flow/nodes/spatial/buffer.py")
    assert any("is_valid" in s for s in _lambdas_de_to_thread(fonte)), (
        "o pre-filtro is_valid (GEOS, O(n)) tem de rodar em asyncio.to_thread"
    )


def test_dispatch_serializa_payload_em_thread():
    """Mutacao: `plaintext = json.dumps(agent_payload...)` inline de volta."""
    fonte = _source("app/services/workflow_execution_service.py")
    assert any("agent_payload" in s and "dumps" in s
               for s in _lambdas_de_to_thread(fonte)), (
        "o json.dumps do payload (multi-MB) tem de rodar em asyncio.to_thread"
    )


def test_publish_map_gzip_envelope_in_thread_without_reparsing():
    """Mutations: (a) inline envelope+gzip in the loop; (b) bring back the redundant
    `json.loads(geojson_str)` + counting features via the parsed dict."""
    fonte = _source("flow/nodes/outputs/publish_map.py")
    assert "_montar_envelope_gzip" in _to_thread_targets(fonte), (
        "envelope + gzip tem de rodar em asyncio.to_thread"
    )
    # AST (immune to comments): no call to json.loads in the module — the
    # redundant geojson parse (json.loads -> json.dumps) was eliminated.
    loads_calls = [
        n for n in ast.walk(ast.parse(fonte))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "loads"
    ]
    assert not loads_calls, (
        "o parse redundante do geojson (json.loads->json.dumps) nao pode voltar"
    )
    assert "features_count = len(value)" in fonte, (
        "a contagem O(1) por len(value) foi revertida para o parse"
    )


def test_database_query_streama_em_chunks():
    """Mutacao: voltar a `connection.fetch(prepared_query, *values)` de tudo."""
    fonte = _source("flow/nodes/datasource/database_query.py")
    assert "cursor.fetch(_CHUNK_SIZE)" in fonte, "tem de usar cursor em chunks"
    assert ".cursor(prepared_query" in fonte
    assert "connection.fetch(prepared_query" not in fonte, (
        "o fetch de tudo de uma vez nao pode voltar"
    )
