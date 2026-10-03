# tests/test_workflow_happy_paths.py
"""
Happy path tests for workflow execution via the executor directly.
No dependency on a database, Redis or Celery.
"""
import asyncio
from unittest.mock import MagicMock


def test_execute_workflow_via_executor():
    """
    Happy path: direct execution of a minimal workflow via WorkflowExecutor.
    Uses a Merge node that returns simple data — no dependency on a database or Celery.
    Note: SYNCHRONOUS test — runs `run()` with asyncio.run, as the executor does on the loop.
    """
    from flow.executor import WorkflowExecutor

    definition = {
        "nodes": [
            {
                "id": "merge-1",
                "type": "control",
                "name": "Merge",
                "properties": {
                    "strategy": "first",
                },
            }
        ],
        "edges": [],
    }

    publisher = MagicMock()
    publisher.publish_event = MagicMock()

    executor = WorkflowExecutor(definition, task_id="unit-test-task-001", publisher=publisher)
    asyncio.run(executor.run(initial_inputs={}))

    # There must be statistics for the executed node
    assert executor.node_stats["merge-1"]["status"] == "completed"
    # The publisher must have been called at least once (start or end event)
    assert publisher.publish_event.called
