# tests/unit/test_merge_portas.py
"""
Merge with declared input ports.

Every input arrives under the key its edge delivers (`to_key`, else
`from_key`). Two parallel branches wired from nodes that both produce `output`
wrote the same key: the second overwrote the first and 'all' returned one
branch, with nothing failing. With two or more declared ports the editor gives
each edge its own `to_key`, 'all' returns {port: value} and 'first'/'last'
follow the port order. A Merge without ports runs exactly as before.
"""
import asyncio
from unittest.mock import MagicMock

import pytest

from flow.executor.core import WorkflowExecutor
from flow.nodes.base import BaseNode
from flow.nodes.control.merge import MergeNode


def _merge(strategy, inputs, ports=None):
    params = {"strategy": strategy, **({"ports": ports} if ports is not None else {})}
    return asyncio.run(MergeNode(node_id="m", parameters=params).execute(inputs))["output"]


def test_descricao_declara_as_portas_de_entrada():
    desc = MergeNode.description()
    assert desc["dynamic_inputs"] is True
    portas = next(p for p in desc["properties"] if p["name"] == "ports")
    assert portas["type"] == "ports" and portas["default"] == []


@pytest.mark.parametrize("strategy, esperado", [
    ("all", {"quadras": 10, "lotes": 1}),
    ("first", 10),
    ("last", 1),
])
def test_sem_portas_nada_muda(strategy, esperado):
    # Arrival order, as always.
    assert _merge(strategy, {"quadras": 10, "lotes": 1}) == esperado


def test_all_devolve_porta_e_valor_na_ordem_das_portas():
    saida = _merge("all", {"quadras": 10, "lotes": 1}, ports=["lotes", "quadras"])
    assert saida == {"lotes": 1, "quadras": 10}
    assert list(saida) == ["lotes", "quadras"]


@pytest.mark.parametrize("strategy, esperado", [("first", 1), ("last", 10)])
def test_first_e_last_seguem_a_ordem_das_portas(strategy, esperado):
    assert _merge(strategy, {"quadras": 10, "lotes": 1}, ports=["lotes", "quadras"]) == esperado


def test_porta_sem_valor_fica_de_fora_e_first_pula_none():
    # A branch not taken does not deliver (its port is absent); None is skipped.
    assert _merge("all", {"quadras": 10}, ports=["lotes", "quadras"]) == {"quadras": 10}
    assert _merge("first", {"lotes": None, "quadras": 10}, ports=["lotes", "quadras"]) == 10


def test_portas_gravadas_como_json_pelo_editor():
    assert _merge("all", {"b": 2, "a": 1}, ports='["a", "b"]') == {"a": 1, "b": 2}


def test_entrada_fora_das_portas_nao_some(caplog):
    # An edge with no `to_key` delivers under the parent's key: dropping it would
    # lose a branch with no sign. It goes after the ports, with a warning.
    with caplog.at_level("WARNING"):
        saida = _merge("all", {"output": 5, "quadras": 10, "lotes": 1}, ports=["lotes", "quadras"])
    assert list(saida) == ["lotes", "quadras", "output"]
    assert "output" in caplog.text


# ── In a run: two branches that both produce the same key ─────────────────────

class _Lotes(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteLotes", "type": "action", "properties": [],
                "outputs": [{"name": "output", "type": "any"}]}

    async def execute(self, inputs):
        return {"output": "lotes"}


class _Quadras(_Lotes):
    @classmethod
    def description(cls):
        return {**_Lotes.description(), "name": "TesteQuadras"}

    async def execute(self, inputs):
        return {"output": "quadras"}


@pytest.fixture
def _nos():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["TesteLotes"] = _Lotes
    NODE_REGISTRY["TesteQuadras"] = _Quadras
    try:
        yield
    finally:
        NODE_REGISTRY.pop("TesteLotes", None)
        NODE_REGISTRY.pop("TesteQuadras", None)


def _rodar(merge_props, edges):
    definition = {
        "nodes": [
            {"id": "T", "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}},
            {"id": "L", "type": "action", "name": "TesteLotes", "properties": {}},
            {"id": "Q", "type": "action", "name": "TesteQuadras", "properties": {}},
            {"id": "M", "type": "control", "name": "Merge", "properties": merge_props},
        ],
        "edges": [{"source": "T", "target": "L"}, {"source": "T", "target": "Q"}, *edges],
    }
    pub = MagicMock()
    final = asyncio.run(WorkflowExecutor(definition, task_id="merge", publisher=pub).run(initial_inputs={"T": {"output": 1}}))
    concluido = [c for c in pub.publish_event.call_args_list if c.args[1] == "M" and c.args[2] == "completed"]
    return final["M"]["output"], concluido[0].args[6]


def test_merge_all_com_portas_devolve_os_dois_ramos(_nos):
    # What the editor writes once the Merge declares two ports: each edge lands
    # on one, so each carries its `to_key`.
    saida, extra = _rodar(
        {"strategy": "all", "ports": '["lotes", "quadras"]'},
        [{"source": "L", "target": "M", "from_key": "output", "to_key": "lotes"},
         {"source": "Q", "target": "M", "from_key": "output", "to_key": "quadras"}],
    )
    assert saida == {"lotes": "lotes", "quadras": "quadras"}
    assert "overwritten_inputs" not in extra


def test_merge_all_sem_portas_continua_sobrescrevendo_e_avisando(_nos):
    saida, extra = _rodar(
        {"strategy": "all"},
        [{"source": "L", "target": "M", "from_key": "output"},
         {"source": "Q", "target": "M", "from_key": "output"}],
    )
    assert saida == {"output": "quadras"}
    assert extra["overwritten_inputs"] == [{"key": "output", "source": "Q", "overwrote": "L"}]


# ── Static validation (what an agent iterates on) ─────────────────────────────

def _validar(merge_props, edges):
    nodes = [
        {"id": "a", "type": "action", "name": "Merge", "properties": {"strategy": "first"}},
        {"id": "m", "type": "control", "name": "Merge", "properties": merge_props},
    ]
    ex = WorkflowExecutor({"nodes": nodes, "edges": edges}, task_id="v", publisher=MagicMock())
    ex.simulated_outputs = {"a": {"status": "ok", "schema": [{"fields": [{"name": "output", "type": "any"}]}]}}
    return [(d["severity"], d.get("code")) for d in ex.validate_edges()]


def test_to_key_fora_das_portas_do_merge_vira_aviso():
    assert _validar({"strategy": "all", "ports": ["lotes", "quadras"]},
                    [{"source": "a", "target": "m", "from_key": "output", "to_key": "lote"}]) \
        == [("warning", "edge_to_key_unknown")]


def test_aresta_sem_to_key_num_merge_com_portas_vira_aviso():
    assert _validar({"strategy": "all", "ports": ["lotes", "quadras"]},
                    [{"source": "a", "target": "m", "from_key": "output"}]) \
        == [("warning", "edge_to_key_missing")]


@pytest.mark.parametrize("props, aresta", [
    ({"strategy": "all", "ports": ["lotes", "quadras"]}, {"from_key": "output", "to_key": "lotes"}),
    # Without ports, or with one (anonymous input): nothing to point at.
    ({"strategy": "all"}, {"from_key": "output"}),
    ({"strategy": "all", "ports": ["lotes"]}, {"from_key": "output"}),
])
def test_merge_ligado_como_o_editor_liga_nao_avisa(props, aresta):
    assert _validar(props, [{"source": "a", "target": "m", **aresta}]) == []
