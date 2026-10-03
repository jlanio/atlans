"""
What the sub-workflow TELLS when something goes wrong.

The six defects covered here had the same shape: execution went on (or stopped)
without saying what actually happened, and the operator went to investigate the
wrong thing. None was a crash — all were silence, or a message that pointed to
the wrong place.
"""
from __future__ import annotations

import pytest

from flow.executor.core import WorkflowExecutor
from flow.nodes.control.sub_workflow import (
    RESULT_KEY,
    SubWorkflowNode,
    _where_failed,
    _SubWorkflowEventPublisher,
)
from flow.utils.workflow_contract import MAX_DEPTH


def _valid_child() -> dict:
    """Minimal definition that passes the contract — Input + Output declared."""
    return {
        "nodes": [
            {"id": "in", "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }


def _no(*, workflow_hash="ALVO", inputs_mapping=None, context=None) -> SubWorkflowNode:
    node = SubWorkflowNode(
        node_id="n1",
        parameters={
            "workflowHash": workflow_hash,
            "inputsMapping": inputs_mapping or {},
            "timeoutSeconds": 300,
        },
    )
    node._workspace_id = "ws-1"
    node._task_id = "task-test"
    node.context = dict(context or {})
    return node


# ── 1. mapping pointing to a key that does not arrive ───────────────────────

class TestOrphanMapping:
    """Before: the child's dict received `None` under the key and the run finished green."""

    @pytest.mark.asyncio
    async def test_fails_naming_the_missing_key_and_those_that_arrived(self):
        node = _no(
            inputs_mapping={"area": "buffer_out"},
            context={"_subworkflow_definitions": {"ALVO": _valid_child()}},
        )
        with pytest.raises(ValueError) as exc:
            await node.execute({"output": {"x": 1}, "gdf": 2})

        msg = str(exc.value)
        assert "buffer_out" in msg, "não diz qual chave de origem faltou"
        assert "area" in msg, "não diz para qual porta do filho ela ia"
        # Without the list of what arrived, the operator has no way to fix the
        # mapping without guessing names.
        assert "gdf" in msg and "output" in msg

    @pytest.mark.asyncio
    async def test_says_when_nothing_arrived(self):
        node = _no(
            inputs_mapping={"area": "buffer_out"},
            context={"_subworkflow_definitions": {"ALVO": _valid_child()}},
        )
        with pytest.raises(ValueError, match="<nenhuma>"):
            await node.execute({})


# ── 2. fluxo que chama a si mesmo ───────────────────────────────────────────

class TestRootSelfReference:
    """Before: the root was not among the ancestors, so A→A was only caught at the
    SECOND level — after the first had already run the side effects (e-mail
    sent, file published) one extra time."""

    def test_the_root_is_among_the_ancestors(self):
        ex = WorkflowExecutor(
            {"nodes": [], "edges": []},
            task_id="t1",
            workflow_hash="RAIZ",
        )
        assert ex.context["_subflow_ancestors"] == {"RAIZ"}

    def test_without_hash_the_set_stays_empty(self):
        # An ad hoc execution (no saved workflow) has nothing to seed, and seeding
        # `None` would make any sub-workflow without a hash hit a false positive.
        ex = WorkflowExecutor({"nodes": [], "edges": []}, task_id="t1")
        assert ex.context["_subflow_ancestors"] == set()

    @pytest.mark.asyncio
    async def test_the_node_blocks_the_call_to_the_root(self):
        node = _no(workflow_hash="RAIZ", context={"_subflow_ancestors": {"RAIZ"}})
        with pytest.raises(ValueError, match="Loop detectado"):
            await node.execute({})


# ── 3. output port with the reserved name ───────────────────────────────────

class TestReservedPort:
    """Before: the node returned `{RESULT_KEY: tudo, **tudo}` — a port named
    `subWorkflowResult` overwrote the envelope and whoever read the key got the
    value of that port, with no error."""

    def _definition(self, portas):
        return {
            "nodes": [
                {"id": "in", "name": "SubWorkflowInput"},
                {"id": "out", "name": "SubWorkflowOutput",
                 "properties": {"ports": portas}},
            ],
            "edges": [],
        }

    def test_rejects_the_reserved_port(self):
        node = _no()
        with pytest.raises(ValueError, match=RESULT_KEY):
            node._check_subworkflow_contract("ALVO", self._definition([RESULT_KEY]))

    def test_accepts_normal_ports(self):
        node = _no()
        node._check_subworkflow_contract("ALVO", self._definition(["area", "total"]))



# ── 4. chain deeper than the limit ──────────────────────────────────────────

class TestDepth:
    """Before: the server stopped pre-resolving at MAX_DEPTH and the node
    said "não existe, está desativado, ou é de outro workspace" (does not exist,
    is deactivated, or belongs to another workspace) — all three false. The
    advice ("re-salve o workflow", re-save the workflow) did not solve it either."""

    @pytest.mark.asyncio
    async def test_says_the_chain_overflowed(self):
        ancestrais = {f"N{i}" for i in range(MAX_DEPTH)}
        node = _no(
            workflow_hash="FUNDO",
            context={"_subflow_ancestors": ancestrais, "_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError) as exc:
            await node.execute({})

        msg = str(exc.value)
        assert str(MAX_DEPTH) in msg and "níveis" in msg
        assert "não foi pré-resolvido" not in msg
        assert "outro workspace" not in msg, "mantém a causa falsa que enganava"

    @pytest.mark.asyncio
    async def test_within_the_limit_the_message_stays_the_snapshot_one(self):
        # A short chain with an empty snapshot is a DIFFERENT problem, and the
        # old message is the right one for it.
        node = _no(
            workflow_hash="ALVO",
            context={"_subflow_ancestors": {"A", "B"}, "_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError, match="pre-resolvido|pré-resolvido"):
            await node.execute({})


# ── 5. which node of the child failed ───────────────────────────────────────

class _FakeChild:
    def __init__(self, stats):
        self.node_stats = stats


class TestWhereItFailed:
    """Before: "Erro ao executar o sub-workflow 'F': division by zero" — in a
    fifteen-node sub-workflow that pinpoints nothing."""

    def test_names_the_node_that_failed(self):
        child = _FakeChild({
            "a": {"status": "completed", "node_name": "Ler"},
            "b": {"status": "failed", "node_name": "PythonScript"},
        })
        onde = _where_failed(child)
        assert "PythonScript" in onde and "b" in onde

    def test_empty_when_no_node_failed(self):
        # Timeout/cancellation do not mark a node as failed; inventing a node there
        # would be worse than saying nothing.
        assert _where_failed(_FakeChild({"a": {"status": "completed"}})) == ""

    def test_tolerates_child_without_stats(self):
        assert _where_failed(object()) == ""

    def test_falls_back_to_id_when_the_node_has_no_name(self):
        assert "b" in _where_failed(_FakeChild({"b": {"status": "failed"}}))


# ── 6. the child's events in the parent's panel ─────────────────────────────

class _SpyPublisher:
    def __init__(self):
        self.eventos = []

    def publish_event(self, **kwargs):
        self.eventos.append(kwargs)


class TestEventRepublishing:

    def test_marks_the_parent_node_for_the_panel_to_find_on_canvas(self):
        espiao = _SpyPublisher()
        pub = _SubWorkflowEventPublisher(espiao, "no-pai")
        pub.publish_event("run-1", "filho-3", "started", extra={"node_name": "Buffer"})

        ev = espiao.eventos[0]
        assert ev["node"] == "no-pai::filho-3"
        # It is what the panel row uses to know which canvas node to attach to
        # — without it the row was orphaned and clicking it did nothing.
        assert ev["extra"]["subworkflow_parent_node"] == "no-pai"

    def test_drops_the_child_progress_denominator(self):
        espiao = _SpyPublisher()
        pub = _SubWorkflowEventPublisher(espiao, "no-pai")
        pub.publish_event("run-1", "filho-3", "started", extra={"nodes_total": 3})
        assert "nodes_total" not in espiao.eventos[0]["extra"]

    def test_does_not_forward_the_child_run_end(self):
        espiao = _SpyPublisher()
        pub = _SubWorkflowEventPublisher(espiao, "no-pai")
        pub.publish_event("run-1", "__workflow_complete__", "completed")
        assert espiao.eventos == [], "encerraria o run do pai no painel"
