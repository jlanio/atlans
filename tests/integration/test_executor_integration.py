# tests/integration/test_executor_integration.py
"""
Integration tests for flow/executor.py.
They cover the full execution flow: node chaining, parallelism, Jinja2
rendering, event publishing, errors and memory release (M5).

These tests document the current behavior and serve as a safety net for
refactoring the executor into multiple modules.
"""
import asyncio
from unittest.mock import MagicMock


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_node(node_id, alias=None, strategy="first", extra_props=None):
    """Creates a Merge node definition with the given parameters."""
    props = {"strategy": strategy}
    if alias:
        props["alias"] = alias
    if extra_props:
        props.update(extra_props)
    return {"id": node_id, "type": "control", "name": "Merge", "properties": props}


def make_edge(source, target, from_key=None, to_key=None):
    """Creates an edge definition."""
    edge = {"source": source, "target": target}
    if from_key:
        edge["from_key"] = from_key
    if to_key:
        edge["to_key"] = to_key
    return edge


def make_workflow(nodes, edges):
    """Creates a workflow definition."""
    return {"nodes": nodes, "edges": edges}


def make_publisher():
    """Creates a publisher mock that collects events."""
    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return publisher


def executar(definition, task_id, publisher):
    """Runs the workflow like the production executor (executor/job_executor.py):
    `run()` on the loop and, with or without failure, the node_stats of what
    got to run.

    Returns (status, erro, node_stats), with status "success" or "failed".
    """
    from flow.executor import WorkflowExecutor

    executor = WorkflowExecutor(definition, task_id=task_id, publisher=publisher)
    try:
        asyncio.run(executor.run(initial_inputs={}))
    except Exception as exc:
        return "failed", str(exc), executor.node_stats
    return "success", None, executor.node_stats


# ── Node chaining ─────────────────────────────────────────────────────────────

class TestChaining:
    """Execution of a workflow with linearly chained nodes."""

    def test_three_chained_nodes_all_run(self):
        """Workflow A→B→C must execute all 3 nodes with status 'completed'."""
        definition = make_workflow(
            nodes=[
                make_node("node-a", alias="NodeA"),
                make_node("node-b", alias="NodeB"),
                make_node("node-c", alias="NodeC"),
            ],
            edges=[
                make_edge("node-a", "node-b", from_key="output", to_key="output"),
                make_edge("node-b", "node-c", from_key="output", to_key="output"),
            ],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-chain-001",
            publisher=make_publisher(),
        )

        assert status == "success", f"Esperado 'success', obtido '{status}': {error}"
        for node_id in ["node-a", "node-b", "node-c"]:
            assert node_id in stats, f"{node_id} não está em node_stats"
            assert stats[node_id]["status"] == "completed"

    def test_chain_respects_topological_order(self):
        """In the chain A→B, the topological order must put A before B."""
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-order-001", publisher=make_publisher()
        )
        order = executor.execution_order

        assert order.index("node-a") < order.index("node-b"), (
            "node-a deve preceder node-b na ordem topológica"
        )

    def test_middle_node_output_flows_to_child(self):
        """A's output must arrive as B's input via the edge."""
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b", strategy="all")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="entrada")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-flow-001", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        # node-b receives 'entrada' from node-a; with strategy='all', the output is
        # {'output': {'entrada': <valor>}}, confirming that the input arrived
        b_output = executor.final_outputs.get("node-b", {})
        assert "output" in b_output, "node-b deve ter produzido um output"
        # The mapped value ('entrada') must be present in the dict returned by 'all'
        merged = b_output.get("output")
        if isinstance(merged, dict):
            assert "entrada" in merged, (
                "Com strategy='all', o output de node-b deve conter a chave 'entrada'"
            )


# ── Jinja2 rendering ──────────────────────────────────────────────────────────

class TestJinja2Rendering:
    """Parameter rendering via Jinja2 during a real execution."""

    def test_jinja2_expression_rendered_in_parameter(self):
        """A parameter with a Jinja2 expression must be resolved before the node executes."""
        # strategy renders to 'last' via Jinja2
        # If rendering does NOT happen, the node receives "{{ 'la' + 'st' }}"
        # (invalid), raises ValueError and the workflow fails.
        definition = make_workflow(
            nodes=[make_node("node-jinja", strategy="{{ 'la' + 'st' }}")],
            edges=[],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-jinja-001",
            publisher=make_publisher(),
        )

        assert status == "success", (
            f"Expressão Jinja2 não foi renderizada corretamente: {error}"
        )

    def test_jinja2_acessa_inputs_do_no(self):
        """node-b's parameter can reference 'inputs' (data arriving via the edge)."""
        # node-b receives 'output' from node-a via the edge.
        # The strategy is: if inputs.output is None → 'last', otherwise use the value.
        # Since node-a returns {'output': None}, strategy must render to 'last'.
        definition = make_workflow(
            nodes=[
                make_node("node-a", alias="NodeA"),
                make_node("node-b", strategy="{{ inputs.output or 'last' }}"),
            ],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-jinja-inputs-001",
            publisher=make_publisher(),
        )

        assert status == "success", (
            f"Renderização de 'inputs' via Jinja2 falhou: {error}"
        )
        assert stats["node-b"]["status"] == "completed"

    def test_m5_releases_named_before_rendering(self):
        """
        M5 releases outputs (and removes them from 'named') while preparing
        inputs, BEFORE asyncio.gather starts the coroutines. Therefore
        'named.NodeA' is NOT available when node-b renders its parameters.
        This test documents that current behavior.
        """
        # If named.NodeA were available, strategy would render to 'all'
        # (valid). Since it is not, the expression fails with UndefinedError and
        # the executor returns status 'failed'.
        definition = make_workflow(
            nodes=[
                make_node("node-a", alias="NodeA"),
                make_node(
                    "node-b",
                    strategy="{{ named.NodeA.output }}",
                ),
            ],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-m5-named-001",
            publisher=make_publisher(),
        )

        # M5 releases 'NodeA' before the render → expression fails
        assert status == "failed", (
            "M5 deve liberar named.NodeA antes da renderização — "
            "expressão deve falhar com UndefinedError"
        )


# ── Event publishing ─────────────────────────────────────────────────────────

class TestEventPublishing:
    """Checks that the correct events are published during execution."""

    def test_started_and_completed_published_per_node(self):
        """Each node must generate at least one 'started' and one 'completed' event."""
        publisher = make_publisher()
        eventos = []

        def capture(run_id, node, status, *args, **kwargs):
            eventos.append({"node": node, "status": status})

        publisher.publish_event.side_effect = capture

        status, _, _ = executar(
            definition=make_workflow(
                nodes=[make_node("no-x"), make_node("no-y")],
                edges=[make_edge("no-x", "no-y", from_key="output", to_key="output")],
            ),
            task_id="test-eventos-001",
            publisher=publisher,
        )

        assert status == "success"
        for node_id in ["no-x", "no-y"]:
            statuses = {e["status"] for e in eventos if e["node"] == node_id}
            assert "started" in statuses, f"Evento 'started' ausente para {node_id}"
            assert "completed" in statuses, f"Evento 'completed' ausente para {node_id}"

    def test_started_precedes_completed_for_each_node(self):
        """For each node, 'started' must be published before 'completed'."""
        publisher = make_publisher()
        eventos = []

        def capture(run_id, node, status, *args, **kwargs):
            eventos.append({"node": node, "status": status})

        publisher.publish_event.side_effect = capture

        executar(
            definition=make_workflow(nodes=[make_node("no-seq")], edges=[]),
            task_id="test-seq-001",
            publisher=publisher,
        )

        node_events = [e for e in eventos if e["node"] == "no-seq"]
        statuses = [e["status"] for e in node_events]

        assert "started" in statuses and "completed" in statuses
        assert statuses.index("started") < statuses.index("completed"), (
            "'started' deve anteceder 'completed'"
        )

    def test_publisher_called_at_least_once_per_node(self):
        """The number of calls to the publisher must be >= the number of nodes."""
        publisher = make_publisher()
        n_nodes = 3

        executar(
            definition=make_workflow(
                nodes=[make_node(f"no-{i}") for i in range(n_nodes)],
                edges=[],
            ),
            task_id="test-calls-001",
            publisher=publisher,
        )

        assert publisher.publish_event.call_count >= n_nodes, (
            "Publisher deve ser chamado ao menos uma vez por nó"
        )


# ── Parallel execution ───────────────────────────────────────────────────────

class TestParallelism:
    """Nodes with no dependencies between them must be able to execute in parallel."""

    def test_diamond_all_nodes_run(self):
        """Workflow A→[B,C]→D must execute all 4 nodes successfully."""
        definition = make_workflow(
            nodes=[
                make_node("node-a"),
                make_node("node-b"),
                make_node("node-c"),
                make_node("node-d", strategy="all"),
            ],
            edges=[
                make_edge("node-a", "node-b", from_key="output", to_key="b_in"),
                make_edge("node-a", "node-c", from_key="output", to_key="c_in"),
                make_edge("node-b", "node-d", from_key="output", to_key="b_out"),
                make_edge("node-c", "node-d", from_key="output", to_key="c_out"),
            ],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-diamond-001",
            publisher=make_publisher(),
        )

        assert status == "success", f"Falha no workflow em diamante: {error}"
        for node_id in ["node-a", "node-b", "node-c", "node-d"]:
            assert node_id in stats, f"{node_id} não foi executado"
            assert stats[node_id]["status"] == "completed"

    def test_diamond_correct_topological_order(self):
        """D must appear after B and C in the diamond's topological order."""
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node(n) for n in ["node-a", "node-b", "node-c", "node-d"]],
            edges=[
                make_edge("node-a", "node-b"),
                make_edge("node-a", "node-c"),
                make_edge("node-b", "node-d"),
                make_edge("node-c", "node-d"),
            ],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-diamond-order", publisher=make_publisher()
        )
        idx = {n: executor.execution_order.index(n) for n in ["node-a", "node-b", "node-c", "node-d"]}

        assert idx["node-a"] < idx["node-b"], "A deve preceder B"
        assert idx["node-a"] < idx["node-c"], "A deve preceder C"
        assert idx["node-b"] < idx["node-d"], "B deve preceder D"
        assert idx["node-c"] < idx["node-d"], "C deve preceder D"


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Executor behavior when a node fails."""

    def test_invalid_node_returns_status_failed(self):
        """A node with an invalid strategy must fail and return status 'failed'."""
        definition = make_workflow(
            nodes=[make_node("node-ruim", strategy="invalida")],
            edges=[],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-error-001",
            publisher=make_publisher(),
        )

        assert status == "failed", "Esperado status 'failed' para nó com erro"
        assert error is not None
        assert stats["node-ruim"]["status"] == "failed"
        assert stats["node-ruim"]["error"] is not None

    def test_error_in_middle_node_keeps_predecessor_stats(self):
        """When B fails (A→B), the stats of A (which completed) must be present."""
        definition = make_workflow(
            nodes=[
                make_node("node-ok"),
                make_node("node-fail", strategy="invalida"),
            ],
            edges=[make_edge("node-ok", "node-fail", from_key="output", to_key="output")],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-partial-001",
            publisher=make_publisher(),
        )

        assert status == "failed"
        assert "node-ok" in stats
        assert stats["node-ok"]["status"] == "completed", (
            "node-ok completou antes da falha — stats devem ser preservados"
        )
        assert stats["node-fail"]["status"] == "failed"

    def test_error_publishes_completed_event_with_status_failed(self):
        """When a node fails, a 'completed' event with the failure must be published."""
        publisher = make_publisher()
        eventos = []

        def capture(run_id, node, status, *args, **kwargs):
            eventos.append({"node": node, "status": status})

        publisher.publish_event.side_effect = capture

        executar(
            definition=make_workflow(
                nodes=[make_node("node-ruim", strategy="invalida")],
                edges=[],
            ),
            task_id="test-error-events-001",
            publisher=publisher,
        )

        node_events = [e for e in eventos if e["node"] == "node-ruim"]
        statuses = [e["status"] for e in node_events]
        assert "started" in statuses, "Evento 'started' ausente mesmo em nó que falha"
        assert "failed" in statuses, "Evento 'failed'/'completed' ausente para nó que falha"


# ── Memory release (M5) ──────────────────────────────────────────────────────

class TestMemoryRelease:
    """M5 optimization: node outputs are released after the children consume them."""

    def test_intermediate_outputs_released_from_all_node_outputs(self):
        """
        After executing A→B, A's all_node_outputs must be released
        (B consumed A's data, triggering _free_node_outputs).
        """
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-m5-001", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        assert executor.all_node_outputs["node-a"]["outputs"] == {}, (
            "M5: outputs de node-a devem ser liberados após node-b consumir"
        )

    def test_final_outputs_preserved_after_m5_release(self):
        """
        final_outputs must contain the original values even after
        all_node_outputs is cleared by M5.
        """
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-m5-002", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        # final_outputs is not affected by releasing all_node_outputs
        assert "output" in executor.final_outputs["node-a"], (
            "final_outputs deve preservar output de node-a mesmo após M5"
        )
        assert "output" in executor.final_outputs["node-b"], (
            "final_outputs deve preservar output de node-b mesmo após M5"
        )

    def test_leaf_node_without_children_is_also_released(self):
        """
        A leaf node (no children) must also have its outputs released after execution
        (remaining_consumers == 0 → _free_node_outputs called).
        """
        from flow.executor import WorkflowExecutor

        definition = make_workflow(nodes=[make_node("node-isolado")], edges=[])

        executor = WorkflowExecutor(
            definition, task_id="test-m5-leaf-001", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        assert executor.all_node_outputs["node-isolado"]["outputs"] == {}, (
            "M5: nó folha deve ter outputs liberados ao final da execução"
        )
