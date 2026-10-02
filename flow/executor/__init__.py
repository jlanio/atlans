# flow/executor/__init__.py
"""
Package executor: orquestração de workflows.

Re-exporta WorkflowExecutor e NodeManager para compatibilidade com todos os
arquivos que fazem `from flow.executor import WorkflowExecutor`.

As constantes e funções de spill e de pin ficam só nos módulos reais
(flow.executor.spill, flow.executor.pin): é lá que elas são lidas, então é lá
que um teste precisa fazer o patch.
"""
from flow.executor.core import WorkflowExecutor
from flow.executor.node_manager import NodeManager

__all__ = [
    "WorkflowExecutor",
    "NodeManager",
]
