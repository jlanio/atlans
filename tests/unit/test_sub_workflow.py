"""
Testes do node SubWorkflow apos o hardening (loop detection, timeout,
mensagens especificas, cancelamento cascata).
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

try:
    from flow.nodes.control.sub_workflow import SubWorkflowNode
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

pytestmark = pytest.mark.skipif(not _AVAILABLE, reason="SubWorkflowNode indisponivel")


def _valid_child_definition() -> dict:
    """Minimal valid sub-workflow definition (with Input + Output)."""
    return {
        "nodes": [
            {"id": "in",  "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }


def _valid_child_final_outputs(public: dict | None = None) -> dict:
    """Simula final_outputs do filho contendo __subworkflow_output__."""
    return {"uuid-out": {"__subworkflow_output__": public if public is not None else {}}}


def _make_node(
    *,
    workflow_hash: str = "TARGET",
    inputs_mapping: dict | None = None,
    timeout_seconds: int = 300,
    workspace_id: str | None = "ws-1",
    context: dict | None = None,
    resolver=None,
) -> SubWorkflowNode:
    """Cria SubWorkflowNode pronto para chamar .execute()."""
    node = SubWorkflowNode(
        node_id="n1",
        parameters={
            "workflowHash": workflow_hash,
            "inputsMapping": inputs_mapping or {},
            "timeoutSeconds": timeout_seconds,
        },
    )
    node._workspace_id = workspace_id
    node._task_id = "task-test"
    # context default popula _subworkflow_definitions via resolver (se passado).
    ctx = dict(context) if context else {}
    if resolver is not None:
        # The resolver returns the definition OR raises ValueError. We populate the
        # envelope snapshot simulating what the server would do. If the resolver
        # raises, we store an empty snapshot — _fetch_definition_from_snapshot
        # will fail with "nao foi pre-resolvido pelo servidor" as expected.
        try:
            snapshot = {workflow_hash: resolver(workflow_hash, workspace_id)}
        except ValueError:
            snapshot = {}
        # Preserves _subworkflow_definitions already in the context (if some
        # test set them explicitly).
        existing = ctx.get("_subworkflow_definitions") or {}
        existing.update(snapshot)
        ctx["_subworkflow_definitions"] = existing
    node.context = ctx
    return node


# ── Loop detection ──────────────────────────────────────────────────────────

class TestLoopDetection:

    @pytest.mark.asyncio
    async def test_detects_direct_self_loop(self):
        """Workflow que tenta chamar a si mesmo (A -> A) falha."""
        node = _make_node(
            workflow_hash="A",
            context={"_subflow_ancestors": {"A"}},
        )
        with pytest.raises(ValueError, match="Loop detectado"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_detects_indirect_loop(self):
        """Cadeia A -> B -> C -> A detectada via set de ancestrais."""
        node = _make_node(
            workflow_hash="A",
            context={"_subflow_ancestors": {"B", "C", "A"}},
        )
        with pytest.raises(ValueError, match="Loop detectado"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_no_loop_when_target_is_new(self):
        """No loop -> tries to resolve the definition from the envelope snapshot."""
        # Empty snapshot: SubWorkflowNode will fail with the snapshot message.
        node = _make_node(
            workflow_hash="A",
            context={"_subflow_ancestors": {"B"}, "_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError, match="nao foi pre-resolvido"):
            await node.execute({})


def _async_run(returns=None, sleep=None, capture=None, capture_flag=False):
    """Double of `WorkflowExecutor.run` — a coroutine.

    The implementation now awaits `child.run(...)` on the SAME event loop
    (before: `asyncio.to_thread(run_sync)`, which created a new loop in a thread).
    With that, `wait_for` really cancels, so the double has to be
    cancellable — `asyncio.sleep`, not `time.sleep`.
    """
    async def _run(**kwargs):
        if capture is not None:
            capture.update({"ok": True} if capture_flag else kwargs)
        if sleep:
            await asyncio.sleep(sleep)
        return returns
    return _run


# ── Timeout ─────────────────────────────────────────────────────────────────

class TestTimeout:

    @pytest.mark.asyncio
    async def test_timeout_raises_runtime_error_quickly(self):
        """A sub-workflow that takes longer than the timeout fails in ~timeout seconds."""

        def slow_resolver(hash_, ws_id):
            # Returns a minimal (empty) definition — the WorkflowExecutor with
            # no nodes finishes quickly, but we make run() hang
            # via the patch below.
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="B",
            timeout_seconds=1,
            resolver=slow_resolver,
        )

        # Patch run() to sleep much longer than the timeout.
        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(sleep=3)  # > timeout=1s
            mock_executor_cls.return_value = mock_executor

            start = time.monotonic()
            with pytest.raises(RuntimeError, match="excedeu o timeout de 1s"):
                await node.execute({})
            elapsed = time.monotonic() - start

        # Deveria ter levantado em ~1s, nao em ~5s
        assert elapsed < 3.0, f"Timeout demorou demais: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_child_node_timeout_does_not_become_sub_workflow_timeout(self):
        """The child's PythonScript raises the built-in TimeoutError when the
        script exceeds ITS OWN deadline. From 3.11 on it is the same
        `asyncio.TimeoutError`, and the error became "excedeu o timeout de 300s,
        aumente timeoutSeconds" (exceeded the 300s timeout, increase
        timeoutSeconds) — the wrong advice. It has to come out as the child's
        error, with the cause."""
        node = _make_node(workflow_hash="B", timeout_seconds=300,
                          resolver=lambda h, w: _valid_child_definition())

        async def _run(**kwargs):
            raise TimeoutError("Execução do script excedeu o limite de 1 segundos.")

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _run
            mock_executor_cls.return_value = mock_executor

            with pytest.raises(RuntimeError) as capturado:
                await node.execute({})

        mensagem = str(capturado.value)
        assert "excedeu o timeout de" not in mensagem
        assert "Erro ao executar o sub-workflow 'B'" in mensagem
        assert "excedeu o limite de 1 segundos" in mensagem

    @pytest.mark.asyncio
    async def test_timeout_zero_or_negative_rejected(self):
        node = _make_node(workflow_hash="X", timeout_seconds=0)
        with pytest.raises(ValueError, match="timeoutSeconds"):
            await node.execute({})


# ── Mensagens especificas (fallback DB) ─────────────────────────────────────

class TestMessages:

    @pytest.mark.asyncio
    async def test_hash_not_in_snapshot_raises_helpful_message(self):
        """Hash not included in the envelope snapshot: the message guides the operator
        on the causes (does not exist / deactivated / other workspace) and suggests
        re-saving the calling workflow."""
        node = _make_node(
            workflow_hash="ghost",
            context={"_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError, match="nao foi pre-resolvido pelo servidor"):
            await node.execute({})


# ── Cancelamento cascata ────────────────────────────────────────────────────

class TestCancellation:

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self):
        """Cancelling the parent's task -> CancelledError does not become RuntimeError."""

        def slow_resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="C", timeout_seconds=30, resolver=slow_resolver)

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(sleep=3)
            mock_executor_cls.return_value = mock_executor

            task = asyncio.create_task(node.execute({}))
            await asyncio.sleep(0.05)  # gives to_thread a chance to start
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task


# ── Inputs mapping ──────────────────────────────────────────────────────────

class TestInputsMapping:

    @pytest.mark.asyncio
    async def test_empty_mapping_passes_all_inputs(self):
        """Empty inputsMapping -> all of the parent's inputs go to the child."""
        captured: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="D", inputs_mapping={}, resolver=resolver)

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}), capture=captured)
            mock_executor_cls.return_value = mock_executor

            await node.execute({"layer": "data1", "filter": "data2"})

        assert captured["initial_inputs"] == {"layer": "data1", "filter": "data2"}

    @pytest.mark.asyncio
    async def test_mapping_translates_keys(self):
        """inputsMapping {'a': 'src_a'} -> the child receives 'a' with the value of 'src_a'."""
        captured: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="D",
            inputs_mapping={"sub_in": "parent_out"},
            resolver=resolver,
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}), capture=captured)
            mock_executor_cls.return_value = mock_executor

            await node.execute({"parent_out": "DATA", "other": "IGNORED"})

        assert captured["initial_inputs"] == {"sub_in": "DATA"}


# ── Disabled nodes (snapshot via envelope) ──────────────────────────────────

class TestDisabledNodes:

    @pytest.mark.asyncio
    async def test_child_with_disabled_node_is_blocked(self):
        """A sub-workflow whose definition contains a node disabled by the admin fails
        with a clear message, BEFORE instantiating the executor."""

        def resolver(hash_, ws_id):
            return {
                "nodes": [
                    {"id": "n1", "name": "WebhookTrigger"},
                    {"id": "n2", "name": "SendEmail"},  # desabilitado
                ],
                "edges": [],
            }

        node = _make_node(
            workflow_hash="CHILD",
            resolver=resolver,
            context={"_disabled_nodes": {"SendEmail"}},
        )

        with pytest.raises(ValueError, match="SendEmail"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_child_without_disabled_nodes_runs(self):
        """An empty snapshot blocks nothing."""

        captured: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="CHILD",
            resolver=resolver,
            context={"_disabled_nodes": set()},
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"r": 1}), capture=captured, capture_flag=True)
            mock_executor_cls.return_value = mock_executor

            result = await node.execute({})

        assert captured.get("ok") is True
        assert result["r"] == 1

    @pytest.mark.asyncio
    async def test_disabled_nodes_snapshot_propagates_to_grandchild(self):
        """Chain A→B→C: the server's envelope snapshot (in A) must reach B's
        executor, which in turn propagates it to C."""
        injected_context: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="B",
            resolver=resolver,
            context={
                "_disabled_nodes": {"SendEmail"},
                "_subflow_ancestors": {"A"},
            },
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = injected_context
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}))
            mock_executor_cls.return_value = mock_executor

            await node.execute({})

        # The sub-executor (B's) received the snapshot. When it instantiates
        # another SubWorkflow for C, that one will validate against this set.
        assert injected_context.get("_disabled_nodes") == {"SendEmail"}


# ── Ancestor propagation ────────────────────────────────────────────────────

class TestAncestorPropagation:

    @pytest.mark.asyncio
    async def test_child_executor_inherits_ancestors_plus_self(self):
        """The child receives the set of ancestors with the current hash included."""
        injected_context: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="LEAF",
            resolver=resolver,
            context={"_subflow_ancestors": {"ROOT", "MID"}},
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = injected_context
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}))
            mock_executor_cls.return_value = mock_executor

            await node.execute({})

        ancestors = injected_context.get("_subflow_ancestors")
        assert ancestors == {"ROOT", "MID", "LEAF"}


# ── Validacoes basicas ──────────────────────────────────────────────────────

class TestBasicValidation:

    @pytest.mark.asyncio
    async def test_missing_workflow_hash_raises(self):
        node = _make_node(workflow_hash="")
        with pytest.raises(ValueError, match="workflowHash"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_non_dict_inputs_mapping_raises(self):
        """A list in inputsMapping is rejected (by BaseNode's validate() before the
        node's custom check — both result in a ValueError with 'inputsMapping')."""
        node = SubWorkflowNode(
            node_id="n1",
            parameters={
                "workflowHash": "A",
                "inputsMapping": ["not", "a", "dict"],
                "timeoutSeconds": 60,
            },
        )
        node.context = {}
        with pytest.raises((ValueError, TypeError), match="inputsMapping"):
            await node.execute({})


# ── Output contract via SubWorkflowOutput ───────────────────────────────────

class TestSubWorkflowOutputContract:
    """When the child workflow uses SubWorkflowOutput, the parent receives outputs
    with named keys (usable on the canvas) instead of the dict of UUIDs."""

    @pytest.mark.asyncio
    async def test_uses_subworkflow_output_when_present(self):
        """The child's final_outputs contain __subworkflow_output__: uses that dict."""

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="CHILD", resolver=resolver)

        # Simulates execution: child final_outputs with 2 nodes — one of them has
        # __subworkflow_output__.
        child_final_outputs = {
            "uuid-wfs": {"output": "<gdf>"},
            "uuid-output-node": {"__subworkflow_output__": {"focos": "<gdf>", "total": 26}},
        }

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=child_final_outputs)
            mock_executor_cls.return_value = mock_executor

            result = await node.execute({})

        # subWorkflowResult must be the PUBLIC dict (not the raw final_outputs)
        assert result["subWorkflowResult"] == {"focos": "<gdf>", "total": 26}
        # Chaves nomeadas spread
        assert result["focos"] == "<gdf>"
        assert result["total"] == 26
        # UUIDs from final_outputs must NOT leak
        assert "uuid-wfs" not in result
        assert "uuid-output-node" not in result

    @pytest.mark.asyncio
    async def test_raises_when_output_node_didnt_run(self):
        """The contract passes (definition has SubWorkflowOutput) but the node did not
        execute (a branch excluded it) — explanatory RuntimeError."""

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="NORUN", resolver=resolver)

        # Simulates final_outputs WITHOUT __subworkflow_output__ (the output node was left out)
        child_final_outputs = {"uuid-wfs": {"output": "<gdf>"}}

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=child_final_outputs)
            mock_executor_cls.return_value = mock_executor

            with pytest.raises(RuntimeError, match="SubWorkflowOutput nao foi executado"):
                await node.execute({})

    @pytest.mark.asyncio
    async def test_subworkflow_output_node_strips_internal_keys(self):
        """SubWorkflowOutput must not leak __artifact__ / __response__ keys
        to the caller — they are internal metadata of the previous node."""
        from flow.nodes.outputs.sub_workflow_output import SubWorkflowOutput

        node = SubWorkflowOutput(node_id="out", parameters={})
        result = await node.execute({
            "focos": "<gdf>",
            "__artifact__": {"s3_key": "x"},
            "__response__": {"status": 200},
            "outro": 42,
        })

        public = result["__subworkflow_output__"]
        assert public == {"focos": "<gdf>", "outro": 42}
        assert "__artifact__" not in public
        assert "__response__" not in public

    @pytest.mark.asyncio
    async def test_subworkflow_output_empty_inputs(self):
        """Node sem inputs conectados: retorna dict publico vazio."""
        from flow.nodes.outputs.sub_workflow_output import SubWorkflowOutput

        node = SubWorkflowOutput(node_id="out", parameters={})
        result = await node.execute({})
        assert result == {"__subworkflow_output__": {}}


# ── Contrato: SubWorkflowOutput obrigatorio, SubWorkflowInput opcional ──────

class TestSubWorkflowContract:
    """Only the OUTPUT is mandatory.

    SubWorkflowOutput defines the return value — without it the parent has
    nothing to consume, and we did not adopt n8n's "last executed node"
    (implicit and ambiguous with branches). SubWorkflowInput, on the other hand, is
    optional: a sub-workflow may receive nothing (fixed source, internal
    parameters), and requiring it was red tape.
    """

    @pytest.mark.asyncio
    async def test_missing_input_is_allowed(self):
        """A sub-workflow without an entry point runs — it just receives no data from the parent."""
        def resolver(hash_, ws_id):
            return {
                "nodes": [{"id": "out", "name": "SubWorkflowOutput"}],
                "edges": [],
            }

        node = _make_node(workflow_hash="X", resolver=resolver)

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}))
            mock_executor_cls.return_value = mock_executor

            result = await node.execute({})

        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_multiple_outputs_raises(self):
        """Two SubWorkflowOutputs make the return ambiguous: extract_contract merges
        the ports of all of them, but collect_subworkflow_output returns the first."""
        def resolver(hash_, ws_id):
            return {
                "nodes": [
                    {"id": "in", "name": "SubWorkflowInput"},
                    {"id": "out1", "name": "SubWorkflowOutput"},
                    {"id": "out2", "name": "SubWorkflowOutput"},
                ],
                "edges": [],
            }

        node = _make_node(workflow_hash="X", resolver=resolver)
        with pytest.raises(ValueError, match="Apenas um e permitido"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_missing_output_raises(self):
        def resolver(hash_, ws_id):
            return {
                "nodes": [{"id": "in", "name": "SubWorkflowInput"}],
                "edges": [],
            }

        node = _make_node(workflow_hash="X", resolver=resolver)
        with pytest.raises(ValueError, match="SubWorkflowOutput"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_missing_both_reports_only_output(self):
        """With neither of the two, the error cites only what is actually missing: the output."""
        def resolver(hash_, ws_id):
            return {"nodes": [{"id": "wfs", "name": "WFS"}], "edges": []}

        node = _make_node(workflow_hash="X", resolver=resolver)
        with pytest.raises(ValueError) as exc_info:
            await node.execute({})
        assert "SubWorkflowOutput" in str(exc_info.value)
        assert "SubWorkflowInput" not in str(exc_info.value)


# ── SubWorkflowInput (trigger) ──────────────────────────────────────────────

class TestSubWorkflowInputNode:

    @pytest.mark.asyncio
    async def test_exposes_inputs_as_outputs(self):
        from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

        node = SubWorkflowInput(node_id="in", parameters={})
        result = await node.execute({"focos": "<gdf>", "bbox": "BBOX"})
        assert result == {"focos": "<gdf>", "bbox": "BBOX"}

    @pytest.mark.asyncio
    async def test_strips_internal_keys(self):
        from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

        node = SubWorkflowInput(node_id="in", parameters={})
        result = await node.execute({
            "focos": "<gdf>",
            "__artifact__": {"x": 1},
        })
        assert result == {"focos": "<gdf>"}

    @pytest.mark.asyncio
    async def test_empty_inputs_returns_empty(self):
        from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

        node = SubWorkflowInput(node_id="in", parameters={})
        assert await node.execute({}) == {}
