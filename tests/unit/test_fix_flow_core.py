# tests/unit/test_fix_flow_core.py
"""
Regressions in flow/executor/core.py:

- P7: the per-node log must not materialize the inputs payload when the level
  is above DEBUG (an eager f-string cost CPU/RAM on every node). The "which node
  is running" stays at INFO — it is the only clue when the WS drops.
- P3: the LIGHT dict of spill references may only live in `all_node_outputs`,
  which is the path that rehydrates via `_load_from_disk`. `named[alias]` and
  `final_outputs` hold the real payload on purpose: nothing rehydrates the
  Jinja context, and the Parquet is deleted by `_free_node_outputs`.
- P3: the spill cleanup must run even when the workflow fails, otherwise
  _spill_cache (a module-level dict) leaks GeoDataFrames for the rest of the
  executor process's life.
- P3.1b: the spill threads must be drained BEFORE the cleanup's rmtree,
  otherwise a cancelled run leaves an orphan Parquet in /tmp forever.
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
    """Input node: `type == 'trigger'` makes the executor inject initial_inputs.

    The `name` stays 'Merge' because it is the factory lookup — with strategy 'first'
    it returns the first non-null value among the inputs, which is the shortest way
    to get a real GeoDataFrame out of a node's output.
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
    def test_str_summarizes_dict_without_materializing_payload(self):
        """__str__ returns the per-key summary, not the payload's repr."""
        payload = {"body": "x" * 10_000}
        resumo = str(_LazySummary(payload))
        assert "body" in resumo
        assert len(resumo) < 1_000, "resumo não pode carregar o payload inteiro"

    def test_non_dict_does_not_blow_up(self):
        assert str(_LazySummary(["a", "b"])) == "<list>"

    def test_logger_above_debug_does_not_call_str(self, caplog):
        """
        With the level above DEBUG, logging does not even touch the argument — that is
        what makes the per-node log free. If someone goes back to using an f-string,
        this contract disappears.
        """
        chamadas = []

        class _Spy(_LazySummary):
            def __str__(self):
                chamadas.append(1)
                return "!"

        logger = logging.getLogger("teste.lazy.summary")
        logger.setLevel(logging.WARNING)
        logger.debug("inputs %s", _Spy({"a": 1}))
        assert chamadas == [], "o resumo foi construído mesmo com nível acima de DEBUG"

    def test_run_node_does_not_log_inputs_at_info(self, caplog):
        """The inputs payload must not appear in INFO-level logs."""
        definition = {"nodes": [_node("n1")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="fix-core-log-1", publisher=_publisher())
        with caplog.at_level(logging.INFO, logger="flow.executor.core"):
            asyncio.run(executor.run(initial_inputs={"n1": {"segredo": "conteudo-gigante"}}))
        assert "conteudo-gigante" not in caplog.text


# ── P3: spill returns the light reference ────────────────────────────────────

class TestSpillReplacesPayload:
    def test_alias_and_final_outputs_receive_the_real_payload(self, tmp_path, monkeypatch):
        """The spill must NOT leak the light reference into `named`/`final_outputs`.

        Regression guard. Returning the spilled dict would lower peak RAM,
        but `named[alias]` feeds the Jinja context (`context.update(named)`) and
        rehydration via `_load_from_disk` only exists on the
        `parent_outputs` path. With the light reference in the alias, `{{ Alvo.output }}`
        would render `{'__spilled__': True, …}` instead of the data — silent
        corruption between nodes. `final_outputs` would also keep pointing at
        Parquets that `_free_node_outputs` has already deleted.

        `all_node_outputs` keeps receiving the light dict (it is consumed through
        `parent_outputs`, which rehydrates).
        """
        # The spill reference points to a REAL, readable Parquet — the production
        # invariant: a spill ref only exists because the file was written.
        # Since the fix for #164, `_load_from_disk` FAILS LOUDLY when it does
        # not restore (instead of letting the sentinel travel on); n2 consumes
        # n1's output through that path, so the Parquet must exist. What
        # this test proves is that the light ref does not leak into `named`/
        # `final_outputs`; the load failure path has its own test
        # (test_executor_correcao_auditoria::test_unrestored_spill_raises).
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

        # Graph with an edge: n2's Merge only produces output if it gets input from n1,
        # and without output there is no spill — the test would pass without exercising anything.
        definition = {
            "nodes": [_node("n1"), _node("n2", alias="Alvo")],
            "edges": [_edge("n1", "n2")],
        }
        executor = WorkflowExecutor(definition, task_id="fix-core-spill-1", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={"output": {"dado": "real"}}))
        # `_delete_spill_files` is stubbed out (above), so the normal cleanup does not
        # run: remove the re-read GDF from the module cache so it does not leak between tests.
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

    def test_without_spill_returns_the_same_dict(self, monkeypatch):
        """Without spill (identical return), nothing changes: returns the original dict."""
        monkeypatch.setattr("flow.executor.core._spill_to_disk",
                            lambda task_id, node_id, outputs: outputs)

        definition = {"nodes": [_node("n1")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="fix-core-spill-2", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={}))

        assert "output" in executor.final_outputs["n1"]


# ── P3/P3.1b: REAL spill, no fake of the mechanism ───────────────────────────

def _gdf(n=200):
    gpd = pytest.importorskip("geopandas")
    geom = pytest.importorskip("shapely.geometry")
    return gpd.GeoDataFrame(
        {"id": list(range(n)), "nome": [f"feicao-{i}" for i in range(n)]},
        geometry=[geom.Point(i, i) for i in range(n)],
        crs="EPSG:4326",
    )


class TestSpillReal:
    """Exercises `_spill_to_disk`/`_load_from_disk` for real.

    The repo's other spill tests replace `_spill_to_disk` with a fake,
    which nullifies exactly what we want to prove: the Parquet write, the
    rehydration on consumption and the cleanup. Here the threshold goes to 1 KB and
    the directory to tmp_path, so the production code writes and re-reads the
    file. The only wrapper is a spy that CALLS the real function.
    """

    def _tmp_spill(self, tmp_path, monkeypatch):
        monkeypatch.setattr(spill_mod, "_SPILL_BASE_DIR", str(tmp_path / "spill"))
        monkeypatch.setattr(spill_mod, "_SPILL_THRESHOLD_MB", 0.001)

    def test_alias_delivers_real_data_and_parquet_is_cleaned(self, tmp_path, monkeypatch):
        gpd = pytest.importorskip("geopandas")
        self._tmp_spill(tmp_path, monkeypatch)

        real_spill = spill_mod._spill_to_disk
        paths: list[str] = []

        def _spy(task_id, node_id, outputs):
            resultado = real_spill(task_id, node_id, outputs)
            for valor in resultado.values():
                if isinstance(valor, dict) and valor.get("__spilled__"):
                    paths.append(valor["__spill_path__"])
                    assert os.path.isfile(valor["__spill_path__"]), (
                        "o spill devolveu uma referência sem ter escrito o Parquet"
                    )
            return resultado

        monkeypatch.setattr("flow.executor.core._spill_to_disk", _spy)

        origem = _gdf(200)
        definition = {
            "nodes": [_trigger("n1"), _node("n2", alias="Alvo")],
            "edges": [_edge("n1", "n2")],
        }
        executor = WorkflowExecutor(definition, task_id="spill-real-1", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={"gdf": origem}))

        assert paths, "nenhum spill real aconteceu — o teste não provaria nada"

        # n1 spilled; n2 only produces output because `_load_from_disk` rehydrated the
        # Parquet on the parent_outputs path.
        assert executor.node_stats["n2"]["input_features"] == 200, (
            "o filho não recebeu o GeoDataFrame de volta do disco"
        )

        # The alias and final_outputs hold the DATA, never the spill reference.
        alvo = executor.expression_context["named"]["Alvo"]["output"]
        assert isinstance(alvo, gpd.GeoDataFrame), f"alias virou {type(alvo).__name__}"
        assert len(alvo) == 200
        assert alvo.crs.to_epsg() == 4326
        assert list(alvo["nome"])[:2] == ["feicao-0", "feicao-1"]
        assert executor.final_outputs["n1"]["output"] is origem, (
            "o dict leve de spill vazou para final_outputs"
        )

        # Nothing was left on disk or in the module cache.
        assert list(tmp_path.rglob("*.parquet")) == [], "Parquet de spill não foi limpo"
        assert not os.path.isdir(str(tmp_path / "spill" / "spill-real-1"))
        assert [k for k in spill_mod._spill_cache if k in paths] == [], (
            "_spill_cache continua segurando os GeoDataFrames relidos"
        )

    def test_cancelled_run_leaves_no_orphan_parquet(self, tmp_path, monkeypatch):
        """P3.1b: the cleanup's rmtree must not run before the spill thread.

        `asyncio.to_thread` is not cancellable. Without the drain, the `finally` of
        `run()` deleted the directory while the thread was still writing — it
        recreated the dir in `os.makedirs` and left the Parquet orphaned forever
        (there is no janitor). Reproduces the production path: job_executor
        wraps `run()` in an `asyncio.wait_for(..., JOB_TIMEOUT)`.
        """
        import asyncio
        import time

        self._tmp_spill(tmp_path, monkeypatch)
        real_spill = spill_mod._spill_to_disk

        def _slow(task_id, node_id, outputs):
            # Ensures the thread is still alive when wait_for times out.
            time.sleep(0.4)
            return real_spill(task_id, node_id, outputs)

        monkeypatch.setattr("flow.executor.core._spill_to_disk", _slow)

        definition = {"nodes": [_trigger("n1")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="spill-cancel-1", publisher=_publisher())

        async def _runs():
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    executor.run(initial_inputs={"gdf": _gdf(200)}), timeout=0.1
                )

        asyncio.run(_runs())

        assert list(tmp_path.rglob("*.parquet")) == [], (
            "o cleanup correu antes da thread de spill terminar — Parquet órfão"
        )


# ── P3: context without duplicated references ────────────────────────────────

class TestContextWithoutDuplicates:
    def test_context_nodes_is_the_live_dict(self):
        definition = {
            "nodes": [_node("n1"), _node("n2")],
            "edges": [_edge("n1", "n2")],
        }
        executor = WorkflowExecutor(definition, task_id="fix-core-ctx-1", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={}))

        assert executor.expression_context["nodes"] is executor.all_node_outputs

    def test_alias_lives_only_in_named(self):
        definition = {"nodes": [_node("n1", alias="Alvo")], "edges": []}
        executor = WorkflowExecutor(definition, task_id="fix-core-ctx-2", publisher=_publisher())
        asyncio.run(executor.run(initial_inputs={}))

        assert "Alvo" in executor.expression_context["named"]
        assert "Alvo" not in executor.expression_context, (
            "o alias no topo do contexto do run era referência morta e duplicada"
        )


# ── P3: spill cleanup on the failure path ────────────────────────────────────

class TestCleanupOnFailure:
    def test_cleanup_runs_when_node_fails(self, monkeypatch):
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
