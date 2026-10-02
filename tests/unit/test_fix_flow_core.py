# tests/unit/test_fix_flow_core.py
"""
Regressões de flow/executor/core.py:

- P7: o log por nó não pode materializar o payload de inputs quando o nível
  está acima de DEBUG (f-string eager custava CPU/RAM em todo nó). O "qual nó
  está rodando" continua em INFO — é a única pista quando o WS cai.
- P3: o dict LEVE de referências de spill só pode viver em `all_node_outputs`,
  que é o caminho que rehidrata via `_load_from_disk`. `named[alias]` e
  `final_outputs` guardam o payload real de propósito: nada rehidrata o
  contexto Jinja, e o Parquet é apagado por `_free_node_outputs`.
- P3: o cleanup do spill precisa rodar mesmo quando o workflow falha, senão
  o _spill_cache (dict de módulo) vaza GeoDataFrames pelo resto da vida do
  processo do executor.
- P3.1b: as threads de spill precisam ser drenadas ANTES do rmtree do cleanup,
  senão um run cancelado deixa Parquet órfão em /tmp para sempre.
"""
import asyncio
import logging
import os

import pytest
from unittest.mock import MagicMock

import flow.executor.spill as spill_mod
from flow.executor.core import WorkflowExecutor, _LazySummary


# ── Helpers ──────────────────────────────────────────────────────────────────

def _node(node_id, alias=None):
    props = {"strategy": "first"}
    if alias:
        props["alias"] = alias
    return {"id": node_id, "type": "control", "name": "Merge", "properties": props}


def _trigger(node_id, alias=None):
    """Nó de entrada: `type == 'trigger'` faz o executor injetar initial_inputs.

    O `name` continua 'Merge' porque é o factory lookup — com strategy 'first'
    ele devolve o primeiro valor não-nulo dos inputs, que é o jeito mais curto
    de fazer um GeoDataFrame real sair do output de um nó.
    """
    node = _node(node_id, alias=alias)
    node["type"] = "trigger"
    return node


def _edge(source, target, from_key="output", to_key="output"):
    return {"source": source, "target": target, "from_key": from_key, "to_key": to_key}


def _publisher():
    pub = MagicMock()
    pub.publish_event = MagicMock()
    return pub


# ── P7: log lazy ─────────────────────────────────────────────────────────────

class TestLazySummary:
    def test_str_resume_dict_sem_materializar_payload(self):
        """__str__ devolve o resumo por chave, não o repr do payload."""
        payload = {"body": "x" * 10_000}
        resumo = str(_LazySummary(payload))
        assert "body" in resumo
        assert len(resumo) < 1_000, "resumo não pode carregar o payload inteiro"

    def test_nao_dict_nao_explode(self):
        assert str(_LazySummary(["a", "b"])) == "<list>"

    def test_logger_acima_de_debug_nao_chama_str(self, caplog):
        """
        Com o nível acima de DEBUG o logging nem toca no argumento — é isso
        que torna o log por nó gratuito. Se alguém voltar a usar f-string,
        este contrato some.
        """
        chamadas = []

        class _Espiao(_LazySummary):
            def __str__(self):
                chamadas.append(1)
                return "!"

        logger = logging.getLogger("teste.lazy.summary")
        logger.setLevel(logging.WARNING)
        logger.debug("inputs %s", _Espiao({"a": 1}))
        assert chamadas == [], "o resumo foi construído mesmo com nível acima de DEBUG"

    def test_run_node_nao_loga_inputs_em_info(self, caplog):
        """O payload de inputs não pode aparecer em logs de nível INFO."""
        definition = {"nodes": [_node("n1")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="fix-core-log-1", publisher=_publisher())
        with caplog.at_level(logging.INFO, logger="flow.executor.core"):
            asyncio.run(executor.run(initial_inputs={"n1": {"segredo": "conteudo-gigante"}}))
        assert "conteudo-gigante" not in caplog.text


# ── P3: spill devolve a referência leve ──────────────────────────────────────

class TestSpillSubstituiPayload:
    def test_alias_e_final_outputs_recebem_o_payload_real(self, tmp_path, monkeypatch):
        """O spill NÃO pode vazar a referência leve para `named`/`final_outputs`.

        Guarda de regressão. Devolver o dict spilled reduziria o pico de RAM,
        mas `named[alias]` alimenta o contexto Jinja (`context.update(named)`) e
        a rehidratação por `_load_from_disk` só existe no caminho de
        `parent_outputs`. Com a referência leve no alias, `{{ Alvo.output }}`
        renderizaria `{'__spilled__': True, …}` em vez do dado — corrupção
        silenciosa entre nós. `final_outputs` ainda ficaria apontando para
        Parquets que `_free_node_outputs` já apagou.

        `all_node_outputs` continua recebendo o dict leve (é o consumo por
        `parent_outputs`, que rehidrata).
        """
        # A referência de spill aponta para um Parquet REAL e legível — a
        # invariante de produção: uma ref de spill só existe porque o arquivo
        # foi escrito. Desde a correção do #164, `_load_from_disk` FALHA ALTO
        # quando não restaura (em vez de deixar a sentinela viajar); n2 consome
        # o output de n1 por esse caminho, então o Parquet precisa existir. O
        # que este teste prova é que a ref leve não vaza para `named`/
        # `final_outputs`; o caminho de falha do load tem teste próprio
        # (test_executor_correcao_auditoria::test_spill_nao_restaurado_levanta).
        real = tmp_path / "leve.parquet"
        _gdf(3).to_parquet(real)
        leve = {"output": {"__spilled__": True, "__spill_path__": str(real),
                           "__spill_key__": "output"}}
        spills = []

        def _fake_spill(task_id, node_id, outputs):
            spills.append(node_id)
            return leve

        monkeypatch.setattr("flow.executor.core._spill_to_disk", _fake_spill)
        monkeypatch.setattr("flow.executor.core._delete_spill_files",
                            lambda outputs: None)

        # Grafo com aresta: o Merge de n2 só produz output se receber input de n1,
        # e sem output não há spill — o teste passaria sem exercitar nada.
        definition = {
            "nodes": [_node("n1"), _node("n2", alias="Alvo")],
            "edges": [_edge("n1", "n2")],
        }
        executor = WorkflowExecutor(definition, task_id="fix-core-spill-1", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={"output": {"dado": "real"}}))
        # `_delete_spill_files` está anulado (acima), então a limpeza normal não
        # roda: tira o GDF relido do cache de módulo para não vazar entre testes.
        spill_mod._spill_cache.pop(str(real), None)

        assert "n2" in spills, "o spill precisa ter sido exercitado para o teste valer"
        assert executor.final_outputs["n2"] is not leve, (
            "final_outputs não pode guardar a referência de spill: o Parquet é "
            "apagado por _free_node_outputs e a ref fica pendurada"
        )
        assert executor.expression_context["named"]["Alvo"] is not leve, (
            "o alias não pode guardar a referência de spill — nada rehidrata "
            "`named` antes do Jinja"
        )

    def test_sem_spill_devolve_o_proprio_dict(self, monkeypatch):
        """Sem spill (retorno idêntico), nada muda: devolve o dict original."""
        monkeypatch.setattr("flow.executor.core._spill_to_disk",
                            lambda task_id, node_id, outputs: outputs)

        definition = {"nodes": [_node("n1")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="fix-core-spill-2", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={}))

        assert "output" in executor.final_outputs["n1"]


# ── P3/P3.1b: spill REAL, sem fake do mecanismo ──────────────────────────────

def _gdf(n=200):
    gpd = pytest.importorskip("geopandas")
    geom = pytest.importorskip("shapely.geometry")
    return gpd.GeoDataFrame(
        {"id": list(range(n)), "nome": [f"feicao-{i}" for i in range(n)]},
        geometry=[geom.Point(i, i) for i in range(n)],
        crs="EPSG:4326",
    )


class TestSpillReal:
    """Exercita `_spill_to_disk`/`_load_from_disk` de verdade.

    Os outros testes de spill do repo substituem `_spill_to_disk` por um fake,
    o que anula exatamente o que se quer provar: a escrita do Parquet, a
    rehidratação no consumo e a limpeza. Aqui o threshold vai a 1 KB e o
    diretório para tmp_path, então o código de produção escreve e relê o
    arquivo. O único wrapper é um espião que CHAMA a função real.
    """

    def _tmp_spill(self, tmp_path, monkeypatch):
        monkeypatch.setattr(spill_mod, "_SPILL_BASE_DIR", str(tmp_path / "spill"))
        monkeypatch.setattr(spill_mod, "_SPILL_THRESHOLD_MB", 0.001)

    def test_alias_entrega_o_dado_real_e_o_parquet_e_limpo(self, tmp_path, monkeypatch):
        gpd = pytest.importorskip("geopandas")
        self._tmp_spill(tmp_path, monkeypatch)

        real_spill = spill_mod._spill_to_disk
        paths: list[str] = []

        def _espia(task_id, node_id, outputs):
            resultado = real_spill(task_id, node_id, outputs)
            for valor in resultado.values():
                if isinstance(valor, dict) and valor.get("__spilled__"):
                    paths.append(valor["__spill_path__"])
                    assert os.path.isfile(valor["__spill_path__"]), (
                        "o spill devolveu uma referência sem ter escrito o Parquet"
                    )
            return resultado

        monkeypatch.setattr("flow.executor.core._spill_to_disk", _espia)

        origem = _gdf(200)
        definition = {
            "nodes": [_trigger("n1"), _node("n2", alias="Alvo")],
            "edges": [_edge("n1", "n2")],
        }
        executor = WorkflowExecutor(definition, task_id="spill-real-1", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={"gdf": origem}))

        assert paths, "nenhum spill real aconteceu — o teste não provaria nada"

        # n1 spillou; n2 só produz output porque `_load_from_disk` rehidratou o
        # Parquet no caminho de parent_outputs.
        assert executor.node_stats["n2"]["input_features"] == 200, (
            "o filho não recebeu o GeoDataFrame de volta do disco"
        )

        # O alias e o final_outputs guardam o DADO, nunca a referência de spill.
        alvo = executor.expression_context["named"]["Alvo"]["output"]
        assert isinstance(alvo, gpd.GeoDataFrame), f"alias virou {type(alvo).__name__}"
        assert len(alvo) == 200
        assert alvo.crs.to_epsg() == 4326
        assert list(alvo["nome"])[:2] == ["feicao-0", "feicao-1"]
        assert executor.final_outputs["n1"]["output"] is origem, (
            "o dict leve de spill vazou para final_outputs"
        )

        # Nada sobrou em disco nem no cache de módulo.
        assert list(tmp_path.rglob("*.parquet")) == [], "Parquet de spill não foi limpo"
        assert not os.path.isdir(str(tmp_path / "spill" / "spill-real-1"))
        assert [k for k in spill_mod._spill_cache if k in paths] == [], (
            "_spill_cache continua segurando os GeoDataFrames relidos"
        )

    def test_run_cancelado_nao_deixa_parquet_orfao(self, tmp_path, monkeypatch):
        """P3.1b: o rmtree do cleanup não pode correr antes da thread de spill.

        `asyncio.to_thread` não é cancelável. Sem o dreno, o `finally` de
        `run()` apagava o diretório enquanto a thread ainda escrevia — ela
        recriava o dir no `os.makedirs` e deixava o Parquet órfão para sempre
        (não há janitor). Reproduz o caminho de produção: o job_executor
        envolve `run()` num `asyncio.wait_for(..., JOB_TIMEOUT)`.
        """
        import asyncio
        import time

        self._tmp_spill(tmp_path, monkeypatch)
        real_spill = spill_mod._spill_to_disk

        def _lento(task_id, node_id, outputs):
            # Garante que a thread ainda esteja viva quando o wait_for estourar.
            time.sleep(0.4)
            return real_spill(task_id, node_id, outputs)

        monkeypatch.setattr("flow.executor.core._spill_to_disk", _lento)

        definition = {"nodes": [_trigger("n1")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="spill-cancel-1", publisher=_publisher())

        async def _corre():
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    executor.run(initial_inputs={"gdf": _gdf(200)}), timeout=0.1
                )

        asyncio.run(_corre())

        assert list(tmp_path.rglob("*.parquet")) == [], (
            "o cleanup correu antes da thread de spill terminar — Parquet órfão"
        )


# ── P3: contexto sem referências duplicadas ──────────────────────────────────

class TestContextoSemDuplicatas:
    def test_nodes_do_contexto_e_o_dict_vivo(self):
        definition = {
            "nodes": [_node("n1"), _node("n2")],
            "edges": [_edge("n1", "n2")],
        }
        executor = WorkflowExecutor(definition, task_id="fix-core-ctx-1", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={}))

        assert executor.expression_context["nodes"] is executor.all_node_outputs

    def test_alias_vive_apenas_em_named(self):
        definition = {"nodes": [_node("n1", alias="Alvo")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="fix-core-ctx-2", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={}))

        assert "Alvo" in executor.expression_context["named"]
        assert "Alvo" not in executor.expression_context, (
            "o alias no topo do contexto do run era referência morta e duplicada"
        )


# ── P3: cleanup do spill em caminho de falha ─────────────────────────────────

class TestCleanupEmFalha:
    def test_cleanup_roda_quando_no_falha(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr("flow.executor.core._cleanup_spill",
                            lambda task_id, is_nested=False: chamadas.append(task_id))

        definition = {"nodes": [_node("n1")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="fix-core-cleanup-1", publisher=_publisher())

        async def _explode(inputs):
            raise RuntimeError("boom")

        executor.node_mgr.nodes["n1"].execute = _explode

        with pytest.raises(RuntimeError):
            asyncio.run(executor.run(initial_inputs={}))

        assert chamadas == ["fix-core-cleanup-1"], (
            "o spill precisa ser limpo mesmo quando o workflow aborta"
        )
