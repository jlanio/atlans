# tests/unit/test_core_amostra.py
"""
`data_preview` in the engine: each completed (or pinned) node publishes a
`sample` event with its outputs, only when the run asked for it, never for a
failed node or inside a sub-workflow (docs/specs/node-data-panels.md §5.5).
"""
import asyncio
from unittest.mock import MagicMock

import pandas as pd
import pytest

from flow.executor.core import WorkflowExecutor
from flow.nodes.base import BaseNode
from flow.utils.publisher.events import KIND_DEBUG


class _Tabela(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteTabelaAmostra", "type": "action", "properties": [],
                "outputs": [{"name": "output", "type": "any"}]}

    async def execute(self, inputs):
        return {"output": pd.DataFrame({"a": range(50)})}


class _Falha(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteFalhaAmostra", "type": "action", "properties": [],
                "outputs": [{"name": "output", "type": "any"}]}

    async def execute(self, inputs):
        raise ValueError("dado inválido")


@pytest.fixture(autouse=True)
def _registra_nos():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["TesteTabelaAmostra"] = _Tabela
    NODE_REGISTRY["TesteFalhaAmostra"] = _Falha
    try:
        yield
    finally:
        NODE_REGISTRY.pop("TesteTabelaAmostra", None)
        NODE_REGISTRY.pop("TesteFalhaAmostra", None)


def _definicao(segundo="TesteTabelaAmostra"):
    return {
        "nodes": [
            {"id": "T", "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}},
            {"id": "A", "type": "action", "name": "TesteTabelaAmostra", "properties": {}},
            {"id": "B", "type": "action", "name": segundo, "properties": {}},
        ],
        "edges": [{"source": "T", "target": "A"}, {"source": "A", "target": "B"}],
    }


def _amostras(pub):
    return [c for c in pub.publish_event.call_args_list if c.kwargs.get("status") == "sample"]


def _rodar(definition, **kw):
    pub = MagicMock()
    ex = WorkflowExecutor(definition, task_id="amostra", publisher=pub, **kw)
    try:
        asyncio.run(ex.run(initial_inputs={"T": {"output": 1}}))
    except Exception:
        pass
    return pub


def test_sem_data_preview_nao_publica_amostra():
    assert _amostras(_rodar(_definicao())) == []


def test_com_data_preview_cada_no_concluido_publica_sua_amostra():
    eventos = _amostras(_rodar(_definicao(), data_preview=True))
    assert {e.kwargs["node"] for e in eventos} == {"T", "A", "B"}
    evento = next(e for e in eventos if e.kwargs["node"] == "A")
    assert evento.kwargs["kind"] == KIND_DEBUG
    sample = evento.kwargs["extra"]["output_sample"]
    assert sample["outputs"]["output"]["rows_total"] == 50
    assert len(sample["outputs"]["output"]["rows"]) == 20
    assert evento.kwargs["extra"]["node_name"] == "TesteTabelaAmostra"


def test_no_que_falhou_nao_publica_amostra():
    eventos = _amostras(_rodar(_definicao("TesteFalhaAmostra"), data_preview=True))
    assert "B" not in {e.kwargs["node"] for e in eventos}
    assert "A" in {e.kwargs["node"] for e in eventos}


def test_execucao_aninhada_nunca_publica_amostra():
    ex = WorkflowExecutor(_definicao(), task_id="x", publisher=MagicMock(), data_preview=True, is_nested=True)
    assert ex.data_preview is False


def test_no_fixado_publica_a_amostra_do_pin(monkeypatch):
    pub = MagicMock()
    ex = WorkflowExecutor(
        _definicao(), task_id="amostra", publisher=pub, data_preview=True,
        pinned_outputs={"A": {"output": {"fixo": True}}}, pin_metadata={"A": {}},
    )
    asyncio.run(ex.run(initial_inputs={"T": {"output": 1}}))
    evento = next(e for e in _amostras(pub) if e.kwargs["node"] == "A")
    assert evento.kwargs["extra"]["output_sample"]["outputs"]["output"]["value"] == {"fixo": True}


def test_amostra_que_falha_nao_derruba_o_no(monkeypatch):
    import flow.executor.core as core

    def explode(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(core, "build_output_sample", explode)
    pub = _rodar(_definicao(), data_preview=True)
    assert _amostras(pub) == []
    concluidos = [c for c in pub.publish_event.call_args_list if len(c.args) > 2 and c.args[2] == "completed"]
    assert {c.args[1] for c in concluidos} >= {"A", "B"}
