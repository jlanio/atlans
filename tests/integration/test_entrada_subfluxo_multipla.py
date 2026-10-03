# tests/integration/test_entrada_subfluxo_multipla.py
"""
Several data items ENTERING a sub-workflow, and the trigger choosing what passes on.

Mirror of test_saida_subfluxo_multipla.py, on the INPUT side. Two defects that
showed up when passing more than one argument:

  1. Entering the SubWorkflow node (invoke) with 2+ values: without a `to_key`
     per port, two edges with the same key name collide in `inputs.update()`
     and the last one wins — then `inputsMapping` complains about a key that
     "did not arrive".
  2. Inside the sub-workflow, the SubWorkflowInput (trigger) could only spread
     the whole dict to each following node — there was no way to say, through
     the edge, "this one carries focos, that one carries bbox".

The fix makes the trigger and the invoke symmetric with SubWorkflowOutput
(which already worked): declared ports become named connection points, and
each edge carries a distinct key (`from_key` on the trigger's output, `to_key`
on the invoke's input). The EXECUTOR already routed by name — these tests
exercise the real graph and lock that contract in.
"""
import asyncio
from unittest.mock import MagicMock

import flow.nodes  # noqa: F401  (popula o registry)


def _script(node_id, code, saida="result"):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": code, "output_vars": saida, "timeout": 20}}


def _rodar_pai(filho, edges_pai_para_sub):
    """Parent that feeds the `sub` node with {focos: 'FOCOS', bbox: 'BBOX'} coming
    from two distinct nodes, through the edges in `edges_pai_para_sub`."""
    from flow.executor import WorkflowExecutor

    pai = {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
            _script("pf", "result = 'FOCOS'"),
            _script("pb", "result = 'BBOX'"),
            {"id": "sub", "type": "control", "name": "SubWorkflow",
             "properties": {"workflowHash": "FILHO", "inputsMapping": {},
                            "timeoutSeconds": 60}},
        ],
        "edges": [
            {"source": "t", "target": "pf"},
            {"source": "t", "target": "pb"},
            *edges_pai_para_sub,
        ],
    }
    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return asyncio.run(
        WorkflowExecutor(
            pai, task_id="t", publisher=publisher, workflow_hash="PAI",
            subworkflow_definitions={"FILHO": filho},
        ).run()
    )


# Each source lands on ITS OWN input port of the sub (distinct to_key).
PAI_PARA_SUB = [
    {"source": "pf", "target": "sub", "from_key": "result", "to_key": "focos"},
    {"source": "pb", "target": "sub", "from_key": "result", "to_key": "bbox"},
]


def _filho_passthrough():
    return {
        "nodes": [
            {"id": "in", "type": "trigger", "name": "SubWorkflowInput", "properties": {"ports": []}},
            {"id": "out", "type": "output", "name": "SubWorkflowOutput", "properties": {"ports": []}},
        ],
        "edges": [{"source": "in", "target": "out"}],
    }


def test_invoke_recebe_duas_entradas_cada_uma_na_sua_chave():
    """The reported bug: passing 2 values to the sub. With a `to_key` per port,
    each source lands on its own key — no 'last one wins' collision."""
    saida = _rodar_pai(_filho_passthrough(), PAI_PARA_SUB)["sub"]

    assert saida["subWorkflowResult"] == {"focos": "FOCOS", "bbox": "BBOX"}


def test_trigger_escolhe_o_que_passa_adiante_por_from_key():
    """The reported bug: in the sub-workflow, choosing through the edge what the
    trigger sends to each node. Each edge leaving the trigger carries
    `from_key` = the port, so the target receives ONLY that key (here, routed
    to named ports of the output)."""
    filho = {
        "nodes": [
            {"id": "in", "type": "trigger", "name": "SubWorkflowInput",
             "properties": {"ports": ["focos", "bbox"]}},
            {"id": "out", "type": "output", "name": "SubWorkflowOutput",
             "properties": {"ports": ["a", "b"]}},
        ],
        "edges": [
            {"source": "in", "target": "out", "from_key": "focos", "to_key": "a"},
            {"source": "in", "target": "out", "from_key": "bbox", "to_key": "b"},
        ],
    }
    saida = _rodar_pai(filho, PAI_PARA_SUB)["sub"]

    # `focos` went only to port `a`, `bbox` only to port `b`: if the trigger
    # had spread the whole dict, the rename by to_key would pick the 1st value
    # and both ports would end up equal.
    assert saida["a"] == "FOCOS"
    assert saida["b"] == "BBOX"


def test_passthrough_sem_portas_continua_espalhando():
    """NON-REGRESSION: a trigger without declared ports keeps spreading the whole
    dict (edge without `from_key`) — existing sub-workflows do not change."""
    saida = _rodar_pai(_filho_passthrough(), PAI_PARA_SUB)["sub"]

    assert saida["subWorkflowResult"] == {"focos": "FOCOS", "bbox": "BBOX"}


def test_o_defeito_que_a_regra_evita():
    """Without `to_key`, the two parent->sub edges use the `from_key` ('result')
    as the name and collide in inputs.update() — the last one wins. That is
    why the editor fills `to_key` per named port; the frontend fix avoids this
    state."""
    sem_to_key = [
        {"source": "pf", "target": "sub", "from_key": "result"},
        {"source": "pb", "target": "sub", "from_key": "result"},
    ]
    saida = _rodar_pai(_filho_passthrough(), sem_to_key)["sub"]

    publico = saida["subWorkflowResult"]
    assert list(publico) == ["result"]
    assert publico["result"] in ("FOCOS", "BBOX")


# ── The node contract ────────────────────────────────────────────────────────

def test_subworkflowinput_declara_saidas_por_ports():
    """`outputs_from_ports` is what makes the editor derive the trigger's OUTPUT
    connection points from the `ports` property — each port becomes an output
    handle, and the edge leaving it carries `from_key`. Without it the trigger
    goes back to a single anonymous handle: the executor does not change, but
    on the canvas there is no way to choose what to pass on. Symmetric with
    SubWorkflowOutput's `dynamic_inputs`."""
    from flow.registry import auto_discover_nodes, NODE_REGISTRY
    auto_discover_nodes()

    d = NODE_REGISTRY["SubWorkflowInput"].description()
    assert d.get("outputs_from_ports") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["default"] == [], "vazio por padrao — preserva os sub-fluxos existentes"
