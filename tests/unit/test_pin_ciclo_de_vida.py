# tests/unit/test_pin_ciclo_de_vida.py
"""
Regressões do ciclo de vida do pin-cache (executor ⇄ servidor).

O bug de produção que motivou tudo: `_collect_stats` reportava o
`pinned_outputs` INTEIRO em `__updated_pinned_outputs__` — inclusive refs que
vieram do servidor e apenas passaram pela run. O consumer re-deriva a s3_key
com o task_id ATUAL, então cada run "corrompia" as refs que não regravou,
apontando-as para objetos que nunca foram enviados. Na run seguinte: 404,
re-execução do nó, e — como o auto-pin só dispara com a ref vazia — a quebra
nunca se resolvia sozinha.

Três defesas, três grupos de teste:
  F0: o executor só reporta o que GRAVOU nesta run (`updated_pin_refs`).
  F1: pin cujo objeto sumiu do storage é zerado na hora e regravado na
      própria run (auto-cura). Pin EXPIRADO não é regravado — a lacuna é
      deliberada até alguém re-pinar.
  (o guard do consumer contra passthrough de executor antigo está em
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
    """WorkflowExecutor sem __init__ — só o necessário para _resolve_pin_data."""
    ex = WorkflowExecutor.__new__(WorkflowExecutor)
    ex.pinned_outputs = pinned_outputs
    ex.pin_metadata = pin_metadata
    ex.updated_pin_refs = {}
    ex.logger = logging.getLogger("test-pin")
    if download is not None:
        # staticmethod na classe; atributo de instância tem precedência.
        ex._download_pin_artifact = download
    return ex


def _resolve(ex, node_id="n1"):
    return asyncio.run(ex._resolve_pin_data(node_id))


# ── F1: auto-cura de pin quebrado ────────────────────────────────────────────

class TestAutoCuraDoPin:

    def test_download_vazio_zera_a_ref_para_regravar(self):
        """Objeto sumiu do MinIO (404): a ref precisa ficar vazia para o
        auto-pin regravar nesta mesma run — senão o 404 se repete para sempre."""
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
        """Expiração é deliberada (TTL do usuário): executa normalmente, mas a
        ref fica — regravar aqui transformaria o pin num cache de última run."""
        vencido = (utc_now_naive() - timedelta(hours=1)).isoformat()
        ex = _executor_stub(
            {"n1": dict(_REF)},
            {"n1": {"pinned_at": "x", "expires_at": vencido}},
        )
        assert _resolve(ex) is None
        assert ex.pinned_outputs["n1"] == _REF          # intacta

    def test_pin_sem_metadata_nao_e_zerado(self):
        """Sem pin_metadata o auto-pin não dispararia de qualquer forma; zerar a
        ref só destruiria informação sem ganhar a regravação."""
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


# ── F0: só refs gravadas NESTA run voltam ao servidor ────────────────────────

class TestColetaDePinsAtualizados:

    def _stats(self, executor_stub) -> dict:
        from executor import job_executor
        # build_metrics falhando não pode derrubar a coleta de pins — e aqui
        # simplesmente não interessa: devolve dict vazio.
        executor_stub.metrics_collector = MagicMock()
        executor_stub.metrics_collector.build_metrics.return_value = {}
        executor_stub.node_stats = {}
        return job_executor._collect_stats(executor_stub, status="success")

    def test_ref_passthrough_NAO_e_reportada(self):
        """A regressão de produção: ref que veio do servidor e só passou pela
        run era reenviada e o consumer a repontava para o task_id atual —
        objeto inexistente, 404 em toda run seguinte."""
        ex = SimpleNamespace(
            pinned_outputs={"n1": dict(_REF)},   # veio do servidor, não regravada
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
        """flow/ e executor/ são implantados juntos, mas a coleta não pode
        explodir se um WorkflowExecutor antigo (sem updated_pin_refs) aparecer."""
        ex = SimpleNamespace(pinned_outputs={"n1": dict(_REF)})
        stats = self._stats(ex)
        assert "__updated_pinned_outputs__" not in stats
