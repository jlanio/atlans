# tests/integration/test_portas_nomeadas.py
"""
Two distinct inputs arriving at the same node.

The name of the variable the script receives comes from the edge's `to_key`.
The editor only fills `to_key` when the target node DECLARES more than one
port; without it the executor falls back to `from_key` (core.py) — which is
"output" on practically every node. Two edges write to the same key and the
second overwrites the first.

The symptom does not reveal the cause: the script complains about an undefined
variable, with nothing saying that the other input was lost. That is how
`PythonScript` came to exist without being able to combine two sources.

These tests exercise the real EXECUTOR, not the isolated node: the defect was
in assembling the inputs between nodes, which only shows up when running the
graph.
"""
import asyncio
from unittest.mock import MagicMock

import pytest


def _script(node_id, code, saida="r"):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": code, "output_vars": saida, "timeout": 20}}


def _rodar(nodes, edges):
    from flow.executor import WorkflowExecutor

    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return asyncio.run(
        WorkflowExecutor({"nodes": nodes, "edges": edges},
                         task_id="t", publisher=publisher).run()
    )


# ── O defeito ────────────────────────────────────────────────────────────────

def test_sem_to_key_a_segunda_aresta_SOBRESCREVE_a_primeira():
    """Documents the inherited behavior: without `to_key`, the two edges use the
    `from_key` as the name and one of them is lost.

    It is not a bug to fix in the executor — it is the reason the node needs
    to DECLARE ports. If this ever starts accumulating instead of overwriting,
    this test warns that the contract changed.
    """
    with pytest.raises(Exception) as e:
        _rodar(
            [_script("a", "r = 'A'"), _script("b", "r = 'B'"),
             _script("c", "r = f'{A}+{B}'")],
            [{"source": "a", "target": "c", "from_key": "r"},
             {"source": "b", "target": "c", "from_key": "r"}],
        )
    msg = str(e.value)
    assert "not defined" in msg
    assert "['r']" in msg, "so uma entrada chegou, com o nome do from_key"


# ── O conserto ───────────────────────────────────────────────────────────────

def test_com_to_key_as_duas_entradas_chegam_pelo_nome():
    resultado = _rodar(
        [_script("a", "r = 'A'"), _script("b", "r = 'B'"),
         _script("c", "r = f'{entrada_1}+{entrada_2}'")],
        [{"source": "a", "target": "c", "from_key": "r", "to_key": "entrada_1"},
         {"source": "b", "target": "c", "from_key": "r", "to_key": "entrada_2"}],
    )
    assert resultado["c"]["r"] == "A+B"


def test_to_key_nomeia_mesmo_com_from_key_diferente():
    """`to_key` wins: it is the ARRIVAL name, regardless of what the parent called it."""
    resultado = _rodar(
        [_script("a", "saida_do_a = 'A'", saida="saida_do_a"),
         _script("c", "r = pontos")],
        [{"source": "a", "target": "c", "from_key": "saida_do_a", "to_key": "pontos"}],
    )
    assert resultado["c"]["r"] == "A"


def test_uma_entrada_sem_to_key_continua_funcionando():
    """Must not break existing workflows: without declared ports `ports` stays
    empty, the node keeps one anonymous connection point and the variable keeps
    coming through `from_key`."""
    resultado = _rodar(
        [_script("a", "r = 'A'"), _script("c", "r = r + '!'")],
        [{"source": "a", "target": "c", "from_key": "r"}],
    )
    assert resultado["c"]["r"] == "A!"


# ── The node contract ────────────────────────────────────────────────────────

def test_pythonscript_declara_entradas_dinamicas():
    """`dynamic_inputs` is what makes the editor derive the connection points from
    the `ports` property instead of the catalog's fixed list."""
    from flow.registry import auto_discover_nodes, NODE_REGISTRY
    auto_discover_nodes()

    d = NODE_REGISTRY["PythonScript"].description()
    assert d.get("dynamic_inputs") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["type"] == "ports"
    assert ports["default"] == [], "vazio por padrao — e o que preserva os fluxos existentes"
