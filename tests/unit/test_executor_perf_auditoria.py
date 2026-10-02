# tests/unit/test_executor_perf_auditoria.py
"""Regressao do PR audit-executor-perf: tirar geopandas/I-O pesado do event loop.

Cada conserto ganha um teste; a docstring nomeia a mutacao que derruba SO ele.
Onde o "roda em thread" nao e observavel por comportamento (precisaria de um
harness async com cronometragem), o teste e um source-check via AST/string — o
mesmo padrao dos source-checks do timeout do PythonScript (#162): a mutacao
(desembrulhar o `asyncio.to_thread`) reverte a fonte e derruba o teste.

Os consertos com logica propria (helpers puros e o lock) tem teste de
COMPORTAMENTO: `_montar_envelope_gzip`, `_concat_chunks`, o lock do
ResourceTracker e a compilacao concorrente do ExpressionService.
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


def _fonte(rel: str) -> str:
    return (RAIZ / rel).read_text(encoding="utf-8")


def _alvos_de_to_thread(fonte: str) -> list[str]:
    """Nomes/atributos que sao o PRIMEIRO argumento de `asyncio.to_thread(...)`
    (a funcao que efetivamente roda na thread). Lambda vira '<lambda>'."""
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
    """Fonte (unparse) de cada lambda passada como 1o arg a `asyncio.to_thread`."""
    arvore = ast.parse(fonte)
    fontes: list[str] = []
    for n in ast.walk(arvore):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "to_thread" and n.args
                and isinstance(n.args[0], ast.Lambda)):
            fontes.append(ast.unparse(n.args[0]))
    return fontes


# ── Helpers puros (teste de comportamento) ───────────────────────────────────

def test_montar_envelope_gzip_embute_geojson_sem_reparsar():
    """Mutacao: quebrar o splice `cabeca[:-1] + ',\"geojson\":' + geojson_str + '}'`
    (ex.: voltar a json.dumps com o geojson ja parseado, ou concatenar errado).

    O helper tem de produzir JSON VALIDO com o geojson embutido cru e devolver
    (comprimido, tamanho_do_payload)."""
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
    obj = json.loads(cru)  # tem de ser JSON valido
    assert obj["workflow_hash"] == "wf1"
    assert obj["publish_config"]["title"] == "T"
    # o geojson entrou inteiro, sem virar string nem se perder
    assert obj["geojson"]["type"] == "FeatureCollection"
    assert len(obj["geojson"]["features"]) == 2


def test_concat_chunks_junta_e_reindexa():
    """Mutacao: `_concat_chunks` devolvendo so o 1o chunk, ou sem ignore_index.

    Junta os DataFrames de cada chunk preservando a ordem e com indice 0..n-1
    (paridade com o antigo DataFrame unico); lista vazia -> DataFrame vazio."""
    from flow.nodes.datasource.database_query import _concat_chunks

    assert _concat_chunks([]).empty
    a = pd.DataFrame([{"x": 1}, {"x": 2}])
    b = pd.DataFrame([{"x": 3}])
    juntos = _concat_chunks([a, b])
    assert list(juntos["x"]) == [1, 2, 3]
    assert list(juntos.index) == [0, 1, 2]  # RangeIndex reindexado


# ── ResourceTracker: lock (concorrencia) ─────────────────────────────────────

def test_resource_tracker_amostra_concorrente_nao_perde_amostras():
    """Mutacao: remover o `with self._lock:` de `sample()`.

    50 threads amostram o MESMO tracker (o run_tracker e compartilhado, e
    end_node passou a rodar em thread). Com o lock, todas as amostras entram e
    `summary()` nao estoura; sem ele, `_samples.append` corre com a iteracao de
    `summary()` (list changed size) ou perde amostras."""
    from flow.metrics.collector import ResourceTracker

    tr = ResourceTracker()

    def amostra(_):
        tr.sample()

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(amostra, range(50)))

    assert tr.summary()["samples"] == 50


def test_resource_tracker_usa_lock_na_fonte():
    """Mutacao: tirar o lock do ResourceTracker (o catcher deterministico).

    O teste concorrente acima e probabilistico; este trava a presenca do lock."""
    fonte = _fonte("flow/metrics/collector.py")
    assert "self._lock = threading.Lock()" in fonte
    assert "with self._lock:" in fonte


# ── ExpressionService: cache LRU com lock ────────────────────────────────────

def test_expression_service_compila_concorrente_sem_corromper():
    """Mutacao: remover o lock/double-check de `_compiled`.

    300 sources distintos compilados por 16 threads (repetidos p/ exercitar o
    cache): sem o lock, `move_to_end`/`popitem`/`__setitem__` corrompem o
    OrderedDict (tamanho errado) ou levantam."""
    from flow.utils.expression_service import ExpressionService

    svc = ExpressionService()
    fontes = [f"{{{{ {i} }}}}" for i in range(300)]

    def um(s: str) -> str:
        return svc._compiled(s).render()

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(um, fontes * 4))

    assert len(res) == 1200
    # 300 < teto (512): todos cacheados, um por source, sem duplicar nem perder
    assert len(svc._template_cache) == 300


def test_expression_service_tem_lock_na_fonte():
    """Mutacao: tirar o lock do _compiled (catcher deterministico do de cima)."""
    fonte = _fonte("flow/utils/expression_service.py")
    assert "import threading" in fonte
    assert "self._template_cache_lock = threading.Lock()" in fonte
    assert "with self._template_cache_lock:" in fonte


# ── Source-checks: o pesado sai do event loop (asyncio.to_thread) ─────────────

def test_leitura_de_spill_vai_para_thread():
    """Mutacao: `parent_outputs = _load_from_disk(...)` sincrono de volta."""
    alvos = _alvos_de_to_thread(_fonte("flow/executor/core.py"))
    assert "_load_from_disk" in alvos, "a leitura do spill tem de ir para thread"


def test_metricas_end_node_vao_para_thread():
    """Mutacao: `self.metrics_collector.end_node(...)` sincrono de volta."""
    alvos = _alvos_de_to_thread(_fonte("flow/executor/core.py"))
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
def test_upload_de_artefato_vai_para_thread(rel, func):
    """Mutacao: desembrulhar o `asyncio.to_thread` de um upload (chamada direta).

    O upload (httpx/disco bloqueante) tem de rodar em thread — a funcao aparece
    como 1o ARG de `to_thread`, nao como `func` de um Call direto."""
    alvos = _alvos_de_to_thread(_fonte(rel))
    assert func in alvos, f"{rel}: {func} tem de rodar em asyncio.to_thread"


def test_purgar_vai_para_thread():
    """Mutacao: `n = purgar(...)` sincrono no _receive_loop de volta."""
    alvos = _alvos_de_to_thread(_fonte("executor/connection.py"))
    assert "purgar" in alvos, "purgar (I/O de disco) tem de ir para thread"


def test_buffer_valida_geometrias_em_thread():
    """Mutacao: filtro `is_valid` sincrono no loop de volta."""
    fonte = _fonte("flow/nodes/spatial/buffer.py")
    assert any("is_valid" in s for s in _lambdas_de_to_thread(fonte)), (
        "o pre-filtro is_valid (GEOS, O(n)) tem de rodar em asyncio.to_thread"
    )


def test_dispatch_serializa_payload_em_thread():
    """Mutacao: `plaintext = json.dumps(agent_payload...)` inline de volta."""
    fonte = _fonte("app/services/workflow_execution_service.py")
    assert any("agent_payload" in s and "dumps" in s
               for s in _lambdas_de_to_thread(fonte)), (
        "o json.dumps do payload (multi-MB) tem de rodar em asyncio.to_thread"
    )


def test_publish_map_envelope_gzip_em_thread_sem_reparsar():
    """Mutacoes: (a) inline do envelope+gzip no loop; (b) voltar o
    `json.loads(geojson_str)` redundante + contar features pelo dict parseado."""
    fonte = _fonte("flow/nodes/outputs/publish_map.py")
    assert "_montar_envelope_gzip" in _alvos_de_to_thread(fonte), (
        "envelope + gzip tem de rodar em asyncio.to_thread"
    )
    # AST (imune a comentario): nenhuma chamada a json.loads no modulo — o parse
    # redundante do geojson (json.loads -> json.dumps) foi eliminado.
    chamadas_loads = [
        n for n in ast.walk(ast.parse(fonte))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "loads"
    ]
    assert not chamadas_loads, (
        "o parse redundante do geojson (json.loads->json.dumps) nao pode voltar"
    )
    assert "features_count = len(value)" in fonte, (
        "a contagem O(1) por len(value) foi revertida para o parse"
    )


def test_database_query_streama_em_chunks():
    """Mutacao: voltar a `connection.fetch(prepared_query, *values)` de tudo."""
    fonte = _fonte("flow/nodes/datasource/database_query.py")
    assert "cursor.fetch(_CHUNK_SIZE)" in fonte, "tem de usar cursor em chunks"
    assert ".cursor(prepared_query" in fonte
    assert "connection.fetch(prepared_query" not in fonte, (
        "o fetch de tudo de uma vez nao pode voltar"
    )
