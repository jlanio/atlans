"""
End-to-end sub-workflow, with a REAL WorkflowExecutor.

The sub-workflow unit tests mock `flow.executor.WorkflowExecutor`, so they
validate what the node ASKS of the executor — never what the executor DOES.
A signature mismatch (is_nested, the call to run) or a propagation mismatch
would go unnoticed by all of them.

Here the parent and the child are real definitions and the executor really runs.
"""
import asyncio

import pytest


def _merge(node_id, strategy="first"):
    return {"id": node_id, "type": "control", "name": "Merge",
            "properties": {"strategy": strategy}}


def _edge(source, target, from_key=None, to_key=None):
    e = {"source": source, "target": target}
    if from_key:
        e["from_key"] = from_key
    if to_key:
        e["to_key"] = to_key
    return e


def _child(ports_in=None, ports_out=None):
    """SubWorkflowInput -> Merge -> SubWorkflowOutput."""
    return {
        "nodes": [
            {"id": "c-in", "type": "trigger", "name": "SubWorkflowInput",
             "properties": {"ports": ports_in or []}},
            _merge("c-mid", strategy="all"),
            {"id": "c-out", "type": "output", "name": "SubWorkflowOutput",
             "properties": {"ports": ports_out or []}},
        ],
        "edges": [
            _edge("c-in", "c-mid"),
            _edge("c-mid", "c-out", from_key="output", to_key="resultado"),
        ],
    }


def _parent(child_hash="CHILD", inputs_mapping=None):
    props = {"workflowHash": child_hash, "timeoutSeconds": 30}
    if inputs_mapping is not None:
        props["inputsMapping"] = inputs_mapping
    return {
        "nodes": [
            _merge("p-src"),
            {"id": "p-sub", "type": "control", "name": "SubWorkflow", "properties": props},
        ],
        "edges": [_edge("p-src", "p-sub", from_key="output", to_key="valor")],
    }


def _run_parent(parent_def, child_def, **executor_kwargs):
    from flow.executor import WorkflowExecutor

    executor = WorkflowExecutor(
        parent_def,
        subworkflow_definitions={"CHILD": child_def},
        **executor_kwargs,
    )
    asyncio.run(executor.run(initial_inputs={}))
    return executor


# ── Cadeia completa ──────────────────────────────────────────────────────────

def test_pai_executa_filho_e_recebe_saida_publica():
    executor = _run_parent(_parent(), _child(), task_id="run-int-1", workspace_id="ws-1")

    saida = executor.final_outputs.get("p-sub", {})
    assert "subWorkflowResult" in saida, "o node deve expor o dict publico do filho"
    assert "resultado" in saida["subWorkflowResult"]


def test_escopo_chega_aos_nodes_do_filho():
    """The central fix: without task_id/workspace_id in the child, every output
    node (DataOutput, SaveToS3, SendEmail...) fails in require_scope()."""
    from flow.executor import WorkflowExecutor

    capturado = {}
    original = WorkflowExecutor.__init__

    def _spy(self, definition, **kwargs):
        # O segundo executor instanciado e o do filho.
        if any(n.get("name") == "SubWorkflowInput" for n in definition.get("nodes", [])):
            capturado.update(kwargs)
        original(self, definition, **kwargs)

    WorkflowExecutor.__init__ = _spy
    try:
        _run_parent(_parent(), _child(), task_id="run-int-2", workspace_id="ws-42")
    finally:
        WorkflowExecutor.__init__ = original

    assert capturado.get("task_id") == "run-int-2"
    assert capturado.get("workspace_id") == "ws-42"
    assert capturado.get("is_nested") is True
    assert capturado.get("workflow_hash") == "CHILD", "hash do filho, nao do pai"


def test_eventos_do_filho_chegam_com_namespace():
    """The sub-workflow is no longer a black box: internal events go up to the
    parent's publisher prefixed by the node that originated them."""
    from unittest.mock import MagicMock

    publisher = MagicMock()
    _run_parent(_parent(), _child(), task_id="run-int-3",
                workspace_id="ws-1", publisher=publisher)

    nodes = [c.kwargs.get("node") for c in publisher.publish_event.call_args_list]
    do_filho = [n for n in nodes if n and n.startswith("p-sub::")]

    assert do_filho, f"nenhum evento do filho publicado; recebidos: {nodes}"
    assert not any(n == "__workflow_complete__" for n in do_filho)


# ── Contrato aplicado em runtime ─────────────────────────────────────────────

def test_ports_de_entrada_filtram_de_verdade():
    """`ports` on the input now takes effect at runtime, not only on save."""
    child = _child(ports_in=["valor"])
    parent = _parent(inputs_mapping={})  # mapping vazio: repassaria tudo

    executor = _run_parent(parent, child, task_id="run-int-4", workspace_id="ws-1")

    entrada_do_filho = executor.final_outputs.get("p-sub", {})
    assert "subWorkflowResult" in entrada_do_filho


def test_ports_de_saida_filtram_de_verdade():
    child = _child(ports_out=["resultado"])
    executor = _run_parent(_parent(), child, task_id="run-int-5", workspace_id="ws-1")

    publico = executor.final_outputs["p-sub"]["subWorkflowResult"]
    assert set(publico) == {"resultado"}


def test_saida_declarada_inexistente_devolve_vazio():
    """A declared port that nobody feeds does not make up data."""
    child = _child(ports_out=["nao_existe"])
    executor = _run_parent(_parent(), child, task_id="run-int-6", workspace_id="ws-1")

    assert executor.final_outputs["p-sub"]["subWorkflowResult"] == {}


def test_sem_entry_point_ainda_executa():
    """SubWorkflowInput virou opcional (contrato opt-in)."""
    child = {
        "nodes": [
            _merge("c-only"),
            {"id": "c-out", "type": "output", "name": "SubWorkflowOutput",
             "properties": {"ports": []}},
        ],
        "edges": [_edge("c-only", "c-out", from_key="output", to_key="r")],
    }
    executor = _run_parent(_parent(), child, task_id="run-int-7", workspace_id="ws-1")

    assert "subWorkflowResult" in executor.final_outputs.get("p-sub", {})


def test_sem_saida_declarada_falha_com_mensagem_util():
    child = {"nodes": [_merge("c-only")], "edges": []}
    parent = _parent()

    with pytest.raises(Exception) as exc:
        _run_parent(parent, child, task_id="run-int-8", workspace_id="ws-1")

    assert "SubWorkflowOutput" in str(exc.value)


# ── Spill isolation (regression from task_id propagation) ───────────────────

def test_filho_nao_apaga_spill_do_pai(tmp_path, monkeypatch):
    """The child inherits the task_id, and the spill lives in /tmp/atlans_spill/<task_id>.
    Without is_nested, the end of the sub-workflow took the parent's data with it.

    We check DURING execution: at the end of the parent the removal is correct
    and expected, so checking the file after everything would prove nothing —
    that is how the first version of this test failed by its own mistake.
    """
    import flow.executor.core as core

    base = tmp_path / "spill"
    monkeypatch.setattr("flow.executor.spill._SPILL_BASE_DIR", str(base))

    task_id = "run-int-9"
    d = base / task_id
    d.mkdir(parents=True)
    do_pai = d / "output_do_pai.parquet"
    do_pai.write_bytes(b"x" * 32)

    chamadas = []
    real_cleanup = core._cleanup_spill

    def _spy(tid, is_nested=False):
        # At the moment the CHILD finishes, the parent's data must be there.
        chamadas.append({"is_nested": is_nested, "pai_intacto": do_pai.exists()})
        return real_cleanup(tid, is_nested=is_nested)

    monkeypatch.setattr(core, "_cleanup_spill", _spy)
    _run_parent(_parent(), _child(), task_id=task_id, workspace_id="ws-1")

    aninhadas = [c for c in chamadas if c["is_nested"]]
    raiz = [c for c in chamadas if not c["is_nested"]]

    assert aninhadas, "o executor do sub-fluxo deveria ter sido marcado is_nested"
    assert all(c["pai_intacto"] for c in aninhadas), (
        "sub-fluxo apagou o spill que o pai ainda usaria"
    )
    assert raiz, "o executor raiz continua responsavel por limpar no fim"


# ── The sub-workflow input can feed SEVERAL nodes ────────────────────────────

def test_entrada_alimenta_varios_ramos():
    """The editor blocked more than one edge leaving SubWorkflowInput, by
    symmetry with Output. The engine never needed that: each edge spreads the
    input dict onto its own target, with no contention.

    The effect of the restriction was to force a funnel node at the input of
    every sub-workflow that wanted to branch.
    """
    filho = {
        "nodes": [
            {"id": "c-in", "type": "trigger", "name": "SubWorkflowInput",
             "properties": {"ports": ["valor"]}},
            _merge("ramo-a", strategy="all"),
            _merge("ramo-b", strategy="all"),
            _merge("junta", strategy="all"),
            {"id": "c-out", "type": "output", "name": "SubWorkflowOutput",
             "properties": {"ports": ["resultado"]}},
        ],
        "edges": [
            _edge("c-in", "ramo-a"),          # leque 1
            _edge("c-in", "ramo-b"),          # leque 2
            _edge("ramo-a", "junta", from_key="output", to_key="de_a"),
            _edge("ramo-b", "junta", from_key="output", to_key="de_b"),
            _edge("junta", "c-out", from_key="output", to_key="resultado"),
        ],
    }
    executor = _run_parent(_parent(), filho, task_id="run-leque", workspace_id="ws-1")

    publico = executor.final_outputs.get("p-sub", {}).get("subWorkflowResult", {})
    assert "resultado" in publico, "o sub-fluxo com leque na entrada precisa devolver"
    # BOTH branches received it — if only one had arrived, one of the keys would be missing.
    assert set(publico["resultado"]) == {"de_a", "de_b"}
