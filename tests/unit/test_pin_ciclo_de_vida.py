# tests/unit/test_pin_ciclo_de_vida.py
"""
Regressions in the pin-cache lifecycle (executor ⇄ server).

The production bug that motivated all of this: `_collect_stats` reported the
WHOLE `pinned_outputs` in `__updated_pinned_outputs__` — including refs that
came from the server and merely passed through the run. The consumer re-derives
the s3_key with the CURRENT task_id, so each run "corrupted" the refs it did not
rewrite, pointing them at objects that were never uploaded. On the next run: 404,
re-execution of the node, and — since auto-pin only fires with an empty ref — the
breakage never resolved itself.

Three defenses, three test groups:
  F0: the executor only reports what it WROTE in this run (`updated_pin_refs`).
  F1: a pin whose object vanished from storage is cleared right away and rewritten
      in the same run (self-healing). An EXPIRED pin is not rewritten — the gap is
      deliberate until someone re-pins.
  (the consumer's guard against passthrough from an old executor is in
   test_fix_consumer_services.py::test_pin_passthrough_de_run_antiga_e_ignorado)
"""
import asyncio
import logging
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock


from flow.utils.datetime_utils import utc_now_naive
from flow.executor.core import WorkflowExecutor


# ── Helpers ──────────────────────────────────────────────────────────────────

_REF = {"__pin_s3_key__": "pin-cache/ws-1/task-antiga/n1_pin.parquet",
        "__pin_format__": "parquet"}


def _executor_stub(pinned_outputs, pin_metadata, download=None) -> WorkflowExecutor:
    """WorkflowExecutor without __init__ — only what _resolve_pin_data needs."""
    ex = WorkflowExecutor.__new__(WorkflowExecutor)
    ex.pinned_outputs = pinned_outputs
    ex.pin_metadata = pin_metadata
    ex.updated_pin_refs = {}
    ex.logger = logging.getLogger("test-pin")
    if download is not None:
        # staticmethod on the class; an instance attribute takes precedence.
        ex._download_pin_artifact = download
    return ex


def _resolve(ex, node_id="n1"):
    return asyncio.run(ex._resolve_pin_data(node_id))


# ── F1: auto-cura de pin quebrado ────────────────────────────────────────────

class TestAutoCuraDoPin:

    def test_download_vazio_zera_a_ref_para_regravar(self):
        """The object vanished from MinIO (404): the ref must become empty so
        auto-pin rewrites it in this same run — otherwise the 404 repeats forever."""
        ex = _executor_stub({"n1": dict(_REF)}, {"n1": {"pinned_at": "x"}},
                            download=lambda pinned: {})
        assert _resolve(ex) is None
        assert ex.pinned_outputs["n1"] == {}

    def test_excecao_no_download_zera_a_ref(self):
        def _boom(pinned):
            raise RuntimeError("storage fora do ar")
        ex = _executor_stub({"n1": dict(_REF)}, {"n1": {"pinned_at": "x"}},
                            download=_boom)
        assert _resolve(ex) is None
        assert ex.pinned_outputs["n1"] == {}

    def test_pin_expirado_NAO_e_regravado(self):
        """Expiration is deliberate (the user's TTL): it runs normally, but the
        ref stays — rewriting here would turn the pin into a last-run cache."""
        vencido = (utc_now_naive() - timedelta(hours=1)).isoformat()
        ex = _executor_stub(
            {"n1": dict(_REF)},
            {"n1": {"pinned_at": "x", "expires_at": vencido}},
        )
        assert _resolve(ex) is None
        assert ex.pinned_outputs["n1"] == _REF          # intacta

    def test_pin_sem_metadata_nao_e_zerado(self):
        """Without pin_metadata auto-pin would not fire anyway; clearing the
        ref would only destroy information without gaining the rewrite."""
        ex = _executor_stub({"n1": dict(_REF)}, {}, download=lambda pinned: {})
        assert _resolve(ex) is None
        assert ex.pinned_outputs["n1"] == _REF

    def test_download_ok_preserva_ref_e_nao_marca_regravacao(self):
        outputs = {"output": {"a": 1}}
        ex = _executor_stub({"n1": dict(_REF)}, {"n1": {"pinned_at": "x"}},
                            download=lambda pinned: outputs)
        assert _resolve(ex) == outputs
        assert ex.pinned_outputs["n1"] == _REF
        assert ex.updated_pin_refs == {}


# ── F0: only refs written in THIS run go back to the server ──────────────────

class TestColetaDePinsAtualizados:

    def _stats(self, executor_stub) -> dict:
        from executor import job_executor
        # A failing build_metrics must not bring down pin collection — and here
        # it simply does not matter: returns an empty dict.
        executor_stub.metrics_collector = MagicMock()
        executor_stub.metrics_collector.build_metrics.return_value = {}
        executor_stub.node_stats = {}
        return job_executor._collect_stats(executor_stub, status="success")

    def test_ref_passthrough_NAO_e_reportada(self):
        """The production regression: a ref that came from the server and only passed
        through the run was resent and the consumer re-pointed it to the current
        task_id — a nonexistent object, 404 on every following run."""
        ex = SimpleNamespace(
            pinned_outputs={"n1": dict(_REF)},   # came from the server, not rewritten
            updated_pin_refs={},
        )
        stats = self._stats(ex)
        assert "__updated_pinned_outputs__" not in stats

    def test_ref_gravada_nesta_run_e_reportada(self):
        ref_nova = {"__pin_s3_key__": "pin-cache/ws/task-atual/n2_pin.parquet",
                    "__pin_format__": "parquet"}
        ex = SimpleNamespace(
            pinned_outputs={"n1": dict(_REF), "n2": dict(ref_nova)},
            updated_pin_refs={"n2": dict(ref_nova)},
        )
        stats = self._stats(ex)
        assert stats["__updated_pinned_outputs__"] == {"n2": ref_nova}

    def test_executor_sem_o_atributo_nao_quebra_a_coleta(self):
        """flow/ and executor/ are deployed together, but collection must not
        blow up if an old WorkflowExecutor (without updated_pin_refs) shows up."""
        ex = SimpleNamespace(pinned_outputs={"n1": dict(_REF)})
        stats = self._stats(ex)
        assert "__updated_pinned_outputs__" not in stats
