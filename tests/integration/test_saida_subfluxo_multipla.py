# tests/integration/test_saida_subfluxo_multipla.py
"""
Several sources feeding a sub-workflow's public output.

`SubWorkflowOutput` accepted ONE incoming edge. To return two values to the
parent you needed a funnel node (SetFields/PythonScript) just to build the
dict — a node that does nothing but exist because of the restriction.

The restriction had a real cause: with a single anonymous connection point,
two edges spread the two dicts onto the SAME keys and the last one wins. The
output depends on the order of the edges, and the contract announces one thing
while delivering another.

What changed: `ports` now also declares the connection points (the same
mechanism as PythonScript). From TWO ports on, the editor fills each edge's
`to_key` with the port name, and each source lands on its own key.

These tests exercise the real EXECUTOR: the defect and the fix are in
assembling the inputs between nodes, which only shows up when running the graph.
"""
import asyncio
from unittest.mock import MagicMock

import flow.nodes  # noqa: F401  (popula o registry)


def _script(node_id, code, saida="result"):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": code, "output_vars": saida, "timeout": 20}}


def _filho(portas, edges_para_saida):
    return {
        "nodes": [
            {"id": "in", "type": "trigger", "name": "SubWorkflowInput",
             "properties": {"ports": []}},
            _script("a", "result = 'FOCOS'"),
            _script("b", "result = 'MAPA'"),
            {"id": "out", "type": "output", "name": "SubWorkflowOutput",
             "properties": {"ports": portas}},
        ],
        "edges": [
            {"source": "in", "target": "a"},
            {"source": "in", "target": "b"},
            *edges_para_saida,
        ],
    }


def _rodar_pai(filho):
    from flow.executor import WorkflowExecutor

    pai = {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
            {"id": "sub", "type": "control", "name": "SubWorkflow",
             "properties": {"workflowHash": "FILHO", "inputsMapping": {},
                            "timeoutSeconds": 60}},
        ],
        "edges": [{"source": "t", "target": "sub"}],
    }
    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return asyncio.run(
        WorkflowExecutor(
            pai, task_id="t", publisher=publisher, workflow_hash="PAI",
            subworkflow_definitions={"FILHO": filho},
        ).run()
    )


COM_PORTAS = [
    {"source": "a", "target": "out", "from_key": "result", "to_key": "focos"},
    {"source": "b", "target": "out", "from_key": "result", "to_key": "mapa"},
]


def test_duas_origens_chegam_cada_uma_na_sua_chave():
    saida = _rodar_pai(_filho(["focos", "mapa"], COM_PORTAS))["sub"]

    assert saida["focos"] == "FOCOS"
    assert saida["mapa"] == "MAPA"
    # The wrapper carries the same set — it is through it that the parent
    # references everything at once in Jinja (`{{ Alias.subWorkflowResult }}`).
    assert saida["subWorkflowResult"] == {"focos": "FOCOS", "mapa": "MAPA"}


def test_o_defeito_que_a_regra_evita():
    """Without `to_key`, the two edges use the `from_key` as the name.

    It is not an executor bug to fix — it is the reason the editor only allows
    several connections when the node declares two or more ports.
    """
    sem_to_key = [
        {"source": "a", "target": "out", "from_key": "result"},
        {"source": "b", "target": "out", "from_key": "result"},
    ]
    saida = _rodar_pai(_filho([], sem_to_key))["sub"]

    # A single key, with the value of ONE of the two sources: the other vanished.
    publico = saida["subWorkflowResult"]
    assert list(publico) == ["result"]
    assert publico["result"] in ("FOCOS", "MAPA")


def test_a_allowlist_continua_valendo_sobre_as_portas():
    """`ports` is a connection point AND a contract: what is not in the list does
    not come back.

    Here the edge delivers `mapa`, which was not declared — the value is
    discarded (with a warning in the log) instead of leaking to the parent.
    """
    saida = _rodar_pai(_filho(["focos"], COM_PORTAS))["sub"]

    assert saida["subWorkflowResult"] == {"focos": "FOCOS"}
    assert "mapa" not in saida


def test_passthrough_sem_portas_continua_devolvendo_tudo():
    """Single-use sub-workflow: one edge, no declared port."""
    uma_aresta = [{"source": "a", "target": "out", "from_key": "result"}]
    saida = _rodar_pai(_filho([], uma_aresta))["sub"]

    assert saida["subWorkflowResult"] == {"result": "FOCOS"}


# ── The node contract ────────────────────────────────────────────────────────

def test_subworkflowoutput_declara_entradas_dinamicas():
    """`dynamic_inputs` is what makes the editor derive the connection points from
    the `ports` property. Without it the node goes back to one anonymous
    handle: the tests above keep passing (the executor does not change), but
    on the canvas there is no way to connect each source to its key — `to_key`
    stops being filled."""
    from flow.registry import auto_discover_nodes, NODE_REGISTRY
    auto_discover_nodes()

    d = NODE_REGISTRY["SubWorkflowOutput"].description()
    assert d.get("dynamic_inputs") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["default"] == [], "vazio por padrao — preserva os sub-fluxos existentes"
