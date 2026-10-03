import logging
from collections import defaultdict, deque
from graphlib import TopologicalSorter, CycleError
from typing import Dict, List

logger = logging.getLogger(__name__)


class WorkflowGraph:
    """
    Builds and analyzes the workflow execution graph.
    - Indexes incoming and outgoing edges for each node.
    - Computes the topological order, guaranteeing a DAG.
    - Optionally ignores isolated nodes (no edges).
    - Optionally restricts execution to the nodes reachable from the triggers AND
      to the dependencies (ancestors) of those nodes.
    """
    def __init__(
        self,
        node_defs: Dict[str, dict],  # mapping id -> node definition
        edges: List[dict],           # list of connections {'source', 'target'}
        filter_isolated: bool = True,
        filter_trigger_reachable: bool = True,
    ):
        self.node_defs = node_defs
        self.edges = edges
        self.filter_isolated = filter_isolated
        self.filter_trigger_reachable = filter_trigger_reachable
        self.incoming = defaultdict(list)
        self.outgoing = defaultdict(list)
        self._index_edges()

    def _index_edges(self) -> None:
        """
        Indexes edges by source and target in easy-to-search structures.

        ORPHAN edges — whose `source` and/or `target` does not exist in `node_defs` —
        are discarded (and logged), not indexed. They come from real cruft:
        a node deleted on the canvas leaving the edge dangling, sub-workflow
        expansion, manual JSON import/editing. If kept, they poison the run —
        `KeyError` while assembling inputs (the run reads `self.incoming`) and at
        instantiation. `compute_order` applies the same guard when ordering.
        """
        self.orphan_edges: List[dict] = []
        for edge in self.edges:
            src = edge['source']
            tgt = edge['target']
            if src not in self.node_defs or tgt not in self.node_defs:
                self.orphan_edges.append(edge)
                continue
            self.outgoing[src].append(edge)
            self.incoming[tgt].append(edge)
        if self.orphan_edges:
            logger.warning(
                "Ignorando %d aresta(s) órfã(s) (endpoint fora de node_defs): %s",
                len(self.orphan_edges),
                [f"{e.get('source')}->{e.get('target')}" for e in self.orphan_edges],
            )

    def compute_order(self) -> List[str]:
        """
        Returns the list of node IDs in execution (topological) order,
        removing isolated nodes if filter_isolated == True.
        """
        # Builds the predecessor map
        predecessors = {nid: set() for nid in self.node_defs}
        for edge in self.edges:
            src = edge['source']
            tgt = edge['target']
            # Guard against orphan edges (the same cruft handled in _index_edges):
            #  - target outside node_defs → predecessors[tgt] would raise a raw KeyError
            #    (plain dict), aborting the WHOLE run before any filter;
            #  - source outside node_defs → the phantom id would go in as a value in
            #    the predecessor set and TopologicalSorter would return it in
            #    static_order() as a node with no predecessors; the filters below only
            #    remove KEYS, so it would leak into instantiation (KeyError
            #    on node_defs[fantasma]).
            if src in self.node_defs and tgt in self.node_defs:
                predecessors[tgt].add(src)

        # If requested, removes nodes with no incoming or outgoing edges.
        # The filter only makes sense when the workflow has edges — if there are no
        # edges, every node is "isolated" by definition and must run.
        if self.filter_isolated and self.edges:
            involved = set(self.incoming.keys()) | set(self.outgoing.keys())
            for nid in list(predecessors.keys()):
                if nid not in involved:
                    predecessors.pop(nid)

        # If requested, restricts execution to the nodes reachable from the
        # triggers AND to the dependencies (ancestors) of those nodes.
        # Preserves legitimate parallel flows (e.g. two triggers converging on a Merge)
        # and eliminates disconnected trees with no path to a trigger.
        # When there are no triggers (e.g. isolated unit tests), the filter is not applied.
        if self.filter_trigger_reachable:
            trigger_ids = {
                nid for nid in predecessors
                if self.node_defs.get(nid, {}).get("type") == "trigger"
            }
            if trigger_ids:
                # Forward: the run "flows down" from the triggers following outgoing edges.
                reachable: set = set()
                queue: deque = deque(trigger_ids)
                while queue:
                    nid = queue.popleft()
                    if nid in reachable:
                        continue
                    reachable.add(nid)
                    for edge in self.outgoing.get(nid, []):
                        queue.append(edge["target"])
                # Backward: the DEPENDENCIES (ancestors) of each node that will run also
                # run. Without this, a "side" source feeding a reachable node
                # (e.g. WFS→Filter→Box, with the trigger connected only to the Box) was
                # left out, and the join HUNG: the executor counts parents per edge (Kahn),
                # and the parent that did not enter the run never decrements that counter —
                # the join and the whole branch never ran, only the trigger. (The direct
                # predecessor did even leak into the ORDER as a value, but the same parent
                # counter held it back, so not even it ran.) Closing the input cone
                # solves everything: every predecessor of a kept node is also kept —
                # no missing parent hanging Kahn and no dangling id in TopologicalSorter.
                manter: set = set(reachable)
                queue = deque(reachable)
                while queue:
                    nid = queue.popleft()
                    for src in predecessors.get(nid, ()):  # predecessors diretos
                        if src not in manter:
                            manter.add(src)
                            queue.append(src)
                for nid in list(predecessors.keys()):
                    if nid not in manter:
                        predecessors.pop(nid)

        # Topological sort
        sorter = TopologicalSorter(predecessors)
        try:
            order = list(sorter.static_order())
        except CycleError as e:
            raise ValueError(f"Ciclo detectado no grafo: {e}")

        return order

