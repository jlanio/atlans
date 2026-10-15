# tests/unit/test_aresta_sem_dado.py
"""
An edge whose `from_key` the source did not produce delivers nothing.

The target still runs, without that input, and fails far from the cause
("Nenhum GeoDataFrame encontrado") or finishes with wrong data. It happens when
a Python Script's `output_vars` is renamed, a Switch rule is removed, a child
workflow's output port is renamed or a node's output changes name in a deploy:
the edge keeps the old key. Only a log line on the executor said why; the
target's completion event now carries the edges that delivered nothing, and the
run panel shows them.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from flow.executor.core import WorkflowExecutor
from flow.nodes.base import BaseNode
from flow.utils.publisher.events import LEVEL_INFO, LEVEL_WARN


class _Fonte(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteFonteAB", "type": "action", "properties": [],
                "outputs": [{"name": "a", "type": "any"}, {"name": "b", "type": "any"}]}

    async def execute(self, inputs):
        return {"a": 1, "b": 2}


class _Destino(BaseNode):
    recebido: dict = {}

    @classmethod
    def description(cls):
        return {"name": "TesteDestino", "type": "action", "properties": [],
                "outputs": [{"name": "output", "type": "any"}]}

    async def execute(self, inputs):
        _Destino.recebido = dict(inputs)
        return {"output": dict(inputs)}


@pytest.fixture(autouse=True)
def _registra_nos():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["TesteFonteAB"] = _Fonte
    NODE_REGISTRY["TesteDestino"] = _Destino
    try:
        yield
    finally:
        NODE_REGISTRY.pop("TesteFonteAB", None)
        NODE_REGISTRY.pop("TesteDestino", None)


def _rodar(edges):
    definition = {
        "nodes": [
            {"id": "T", "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}},
            {"id": "F", "type": "action", "name": "TesteFonteAB", "properties": {}},
            {"id": "D", "type": "action", "name": "TesteDestino", "properties": {}},
        ],
        "edges": [{"source": "T", "target": "F"}, *edges],
    }
    pub = MagicMock()
    ex = WorkflowExecutor(definition, task_id="sem-dado", publisher=pub)
    asyncio.run(ex.run(initial_inputs={"T": {"output": 1}}))
    eventos = [c for c in pub.publish_event.call_args_list if c.args[1] == "D" and c.args[2] == "completed"]
    assert len(eventos) == 1
    return eventos[0]


def test_from_key_que_a_origem_nao_produziu_vai_no_evento_do_destino():
    evento = _rodar([{"source": "F", "target": "D", "from_key": "c", "to_key": "entrada"}])
    extra = evento.args[6]
    assert extra["unresolved_edges"] == [{"source": "F", "from_key": "c", "keys": ["a", "b"]}]
    assert evento.kwargs["level"] == LEVEL_WARN
    # The run itself is unchanged: the edge still delivers nothing.
    assert "entrada" not in _Destino.recebido


def test_aresta_que_entrega_nao_gera_aviso():
    evento = _rodar([{"source": "F", "target": "D", "from_key": "b", "to_key": "entrada"}])
    assert "unresolved_edges" not in evento.args[6]
    assert evento.kwargs["level"] == LEVEL_INFO
    assert _Destino.recebido == {"entrada": 2}


def test_aresta_sem_from_key_espalha_e_nao_gera_aviso():
    evento = _rodar([{"source": "F", "target": "D"}])
    assert "unresolved_edges" not in evento.args[6]
