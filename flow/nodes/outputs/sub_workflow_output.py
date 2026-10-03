# flow/nodes/outputs/sub_workflow_output.py
"""
SubWorkflowOutput — declares the "public API" of a child workflow.

When a workflow B is used as a sub-workflow (via SubWorkflowNode in A),
historically the parent received `final_outputs` keyed by the random UUIDs
of the child's nodes — completely unusable on the canvas.

This node solves that: B's operator connects to SubWorkflowOutput whatever
they want to expose, and the SubWorkflowNode in A detects `__subworkflow_output__`
and returns that dict as named outputs.

`ports` has TWO roles, which are the same role seen from two sides:

  - with TWO or more ports, each becomes its own connection point on the
    canvas. The editor fills the edge's `to_key` with the port name, so
    each source lands in ITS OWN key — several nodes can feed the output at
    the same time, one per key;
  - the list is also the allowlist of what goes out to the parent.

Example on B's canvas (two declared ports: focos, mapa):
    WFS        ──────►  ( focos )  SubWorkflowOutput
    RenderMap  ──────►  ( mapa  )

Result on A's canvas after SubWorkflowNode(B):
    outputs = {"subWorkflowResult": {...}, "focos": <gdf>, "mapa": <bytes>}

With `ports` EMPTY the node goes back to passthrough mode: a single anonymous
connection point, a single edge, and everything that arrives is returned. Two
edges in that mode would spread both dicts onto the same keys and the last
would win — that is why the editor only allows several connections from two
declared ports on.
"""
from typing import Any, Dict

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.logger import get_logger
from flow.utils.workflow_contract import _parse_ports

logger = get_logger(__name__)


@register_node
class SubWorkflowOutput(BaseNode):
    """Defines a workflow's public output for use as a sub-workflow."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name":        "SubWorkflowOutput",
            "alias":       "Saída do Sub-Workflow",
            "type":        "output",
            "description": (
                "Define a API publica de um workflow quando usado como sub-fluxo. "
                "Recebe (em conexao unica) um dict do node anterior e expoe as "
                "chaves declaradas em 'ports' como saida publica para o pai."
            ),
            "properties": [
                {
                    "name":        "ports",
                    "label":       "Chaves de saída",
                    "type":        "object",
                    "default":     [],
                    "description": (
                        "Lista de chaves de saida que o sub-fluxo expoe ao pai. "
                        "Ex: ['result_geometry']. Com duas ou mais, cada chave "
                        "vira um ponto de conexao proprio e recebe a sua origem. "
                        "Chaves nao listadas sao filtradas antes de retornar."
                    ),
                },
            ],
            # Inputs DECLARED BY THE USER, via the `ports` property — the
            # same mechanism as PythonScript. This is what lets more than one node
            # feed the public output: with two or more ports the editor
            # fills each edge's `to_key`, and the executor delivers
            # `inputs[to_key]` instead of overwriting everything on the same key.
            "dynamic_inputs": True,
            "outputs": [
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Filters out the executor's internal metadata (keys starting with __)
        # and also keys not declared in ports (if there is a list).
        declared_set = set(_parse_ports(self.parameters.get("ports")))

        raw = {k: v for k, v in (inputs or {}).items() if not k.startswith("__")}
        if declared_set:
            public = {k: v for k, v in raw.items() if k in declared_set}
            # Drop with a warning: before, connecting RenderMap -> Output with
            # to_key="mapa" and forgetting to declare "mapa" made the data vanish
            # with no error, no log and no sign on the canvas.
            dropped = sorted(set(raw) - set(public))
            if dropped:
                logger.warning(
                    "SubWorkflowOutput: %d chave(s) recebida(s) fora do contrato, "
                    "nao serao devolvidas ao pai: %s. Declaradas: %s.",
                    len(dropped), ", ".join(dropped), ", ".join(sorted(declared_set)),
                )
        else:
            # `ports` vazio = expoe tudo (modo passthrough).
            public = raw
        return {"__subworkflow_output__": public}
