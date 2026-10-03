# flow/executor/node_manager.py
"""Instantiation and configuration of the workflow's nodes."""
from typing import Dict, Any, List
from flow.factory import NodeFactory


class NodeManager:
    def __init__(self, node_defs: Dict[str, dict]):
        self.node_defs = node_defs
        self.factory = NodeFactory()
        self.nodes: Dict[str, Any] = {}

    def instantiate_nodes(self, execution_order: List[str]) -> None:
        for node_id in execution_order:
            self.nodes[node_id] = self.factory.create(self.node_defs[node_id])
