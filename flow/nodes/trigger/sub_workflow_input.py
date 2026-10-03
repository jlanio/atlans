# flow/nodes/trigger/sub_workflow_input.py
"""
SubWorkflowInput — entry point of a workflow called as a sub-workflow.

Mirror of SubWorkflowOutput: defines the "public input API". When A calls
B via SubWorkflow, A's `inputsMapping` maps keys to the initial_inputs of
B's executor. SubWorkflowInput receives those initial_inputs and exposes
them as named outputs — usable on the following edges of B's canvas.

Difference from WebhookTrigger:
  - WebhookTrigger is for external HTTP input (payload with a schema, etc).
  - SubWorkflowInput is for input from another internal workflow (keys
    already arrive named via the caller's inputsMapping).

Example on B's canvas:
    SubWorkflowInput  ─[from_key="focos", to_key="data"]──► PythonScript
                      ─[from_key="bbox",  to_key="region"]──► ...

Workflow A calling B:
    SubWorkflow(B, inputsMapping={"focos": "minha_camada", "bbox": "regiao"})
"""
from typing import Any, Dict

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.logger import get_logger
from flow.utils.workflow_contract import _parse_ports

logger = get_logger(__name__)


@register_node
class SubWorkflowInput(BaseNode):
    """Entry point for a workflow used as a sub-workflow."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name":        "SubWorkflowInput",
            "alias":       "Entrada do Sub-Workflow",
            "type":        "trigger",
            "description": (
                "Entry point quando este workflow e chamado como sub-fluxo. "
                "Recebe as chaves declaradas em 'ports' do node SubWorkflow "
                "no workflow chamador e as expoe em bloco para o proximo node "
                "(unica conexao permitida)."
            ),
            "properties": [
                {
                    "name":        "ports",
                    "label":       "Chaves de entrada",
                    "type":        "object",
                    "default":     [],
                    "description": (
                        "Lista de chaves de entrada esperadas pelo sub-fluxo. "
                        "Ex: ['geometry', 'buffer_distance']. O pai usa essa lista "
                        "para validar o inputsMapping."
                    ),
                },
            ],
            # This trigger's OUTPUTS ARE the declared `ports`: each port becomes
            # an output connection point on the canvas, and the edge leaving it carries
            # `from_key` = port name, so the next node receives ONLY that
            # key (e.g. [from_key="focos"] -> {"focos": ...}). It is the counterpart of
            # SubWorkflowOutput's `dynamic_inputs`, on the input side.
            # Without this flag the trigger had a single anonymous output point and each
            # edge spread the whole dict — impossible to choose what to pass.
            # Empty `ports`/1 port keeps the anonymous point (passthrough mode).
            "outputs_from_ports": True,
            "outputs": [
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Filters out the executor's internal metadata (keys starting with __)
        # — initial_inputs should not carry that, but defense in depth.
        raw = {k: v for k, v in (inputs or {}).items() if not k.startswith("__")}

        # Declared `ports` = strict allowlist, symmetric to SubWorkflowOutput.
        # Before, the filter only existed on the output: the input contract applied on
        # save and was ignored at runtime, so the child received the parent's whole
        # namespace — including keys outside the contract.
        # Empty `ports` keeps the passthrough ("accept everything" mode).
        declared = _parse_ports(self.parameters.get("ports"))
        if not declared:
            return raw

        public = {k: v for k, v in raw.items() if k in declared}

        # A drop is never silent: without this warning, the operator who maps an
        # undeclared key sees the sub-workflow run "successfully" and without the data.
        dropped = sorted(set(raw) - set(public))
        if dropped:
            logger.warning(
                "SubWorkflowInput: %d chave(s) recebida(s) do pai fora do contrato, "
                "descartada(s): %s. Declaradas: %s.",
                len(dropped), ", ".join(dropped), ", ".join(sorted(declared)) or "<nenhuma>",
            )
        return public
