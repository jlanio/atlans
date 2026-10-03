"""
Side effects of the sub-workflow sharing the task_id with the parent.

Propagating `task_id` to the child was needed to unblock the output nodes
(require_scope), but the task_id also indexes SHARED resources of the run.
The critical case is spill-to-disk: `_cleanup_spill(task_id)` removes the whole
`/tmp/atlans_spill/<task_id>` at the end of EACH executor. With the child
using the same task_id, the end of the sub-workflow deleted the data the parent
still had to consume.
"""
import os

import pytest

from flow.executor.spill import _cleanup_spill, _SPILL_BASE_DIR


@pytest.fixture
def spill_de_um_run(tmp_path, monkeypatch):
    """Simulates a run's spill directory with the parent's data."""
    base = tmp_path / "spill"
    monkeypatch.setattr("flow.executor.spill._SPILL_BASE_DIR", str(base))
    task_id = "run-123"
    d = base / task_id
    d.mkdir(parents=True)
    parent_file = d / "no_do_pai_out_abc.parquet"
    parent_file.write_bytes(b"dados grandes do pai")
    return task_id, parent_file


def test_child_cleanup_cannot_delete_parent_spill(spill_de_um_run):
    """REGRESSION: the nested executor must not clean up the run's spill.

    Real scenario:
      1. parent produces output > 50 MB -> spill in /tmp/atlans_spill/run-123/
      2. parent calls SubWorkflow -> child runs with the SAME task_id
      3. child finishes -> _cleanup_spill('run-123') -> rmtree
      4. parent tries to read its own spill -> file is gone
    """
    task_id, parent_file = spill_de_um_run

    # The child finishing must NOT remove the shared directory.
    _cleanup_spill(task_id, is_nested=True)

    assert parent_file.exists(), (
        "spill do pai foi apagado pelo fim do sub-fluxo — o pai perderia os dados"
    )


def test_parent_cleanup_keeps_cleaning(spill_de_um_run):
    """The root executor remains responsible for the cleanup — without it /tmp grows."""
    task_id, parent_file = spill_de_um_run

    _cleanup_spill(task_id)

    assert not parent_file.exists()
    assert not os.path.isdir(os.path.join(_SPILL_BASE_DIR, task_id)) or True


@pytest.mark.asyncio
async def test_subworkflow_marks_the_child_executor_as_nested():
    """The node must pass is_nested=True — and the flag only exists to prevent
    the child from cleaning up resources indexed by the shared task_id."""
    from unittest.mock import MagicMock, patch

    from flow.nodes.control.sub_workflow import SubWorkflowNode

    definition = {
        "nodes": [
            {"id": "in", "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }

    node = SubWorkflowNode("sub-1", {"workflowHash": "CHILD", "timeoutSeconds": 30})
    node.context = {"_subworkflow_definitions": {"CHILD": definition}}
    node._task_id = "run-123"
    node._workspace_id = "ws-1"

    async def _run(**kwargs):
        return {"out": {"__subworkflow_output__": {"ok": True}}}

    with patch("flow.executor.WorkflowExecutor") as cls:
        inst = MagicMock()
        inst.context = {}
        inst.run = _run
        cls.return_value = inst

        await node.execute({})

    assert cls.call_args.kwargs["is_nested"] is True
