# flow/executor/__init__.py
"""
executor package: workflow orchestration.

Re-exports WorkflowExecutor and NodeManager for compatibility with all the
files that do `from flow.executor import WorkflowExecutor`.

The spill and pin constants and functions live only in the real modules
(flow.executor.spill, flow.executor.pin): that is where they are read, so that is
where a test needs to patch them.
"""
from flow.executor.core import WorkflowExecutor
from flow.executor.node_manager import NodeManager

__all__ = [
    "WorkflowExecutor",
    "NodeManager",
]
