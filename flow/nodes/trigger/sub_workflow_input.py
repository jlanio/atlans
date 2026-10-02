# flow/nodes/trigger/sub_workflow_input.py
"""
SubWorkflowInput — entry point de um workflow chamado como sub-fluxo.

Espelho do SubWorkflowOutput: define a "API publica de entrada". Quando A
chama B via SubWorkflow, o `inputsMapping` de A mapeia chaves para o
initial_inputs do executor de B. O SubWorkflowInput recebe esses
initial_inputs e os expoe como outputs nomeados — utilizaveis nas edges
seguintes do canvas de B.

Diferenca do WebhookTrigger:
  - WebhookTrigger e para entrada HTTP externa (payload com schema, etc).
  - SubWorkflowInput e para entrada de outro workflow interno (chaves ja
    vem nomeadas via inputsMapping do caller).

Exemplo no canvas de B:
    SubWorkflowInput  ─[from_key="focos", to_key="data"]──► PythonScript
                      ─[from_key="bbox",  to_key="region"]──► ...

Workflow A chamando B:
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
    """Entry point para workflow usado como sub-fluxo."""

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
            # As SAIDAS deste trigger SAO as `ports` declaradas: cada porta vira
            # um ponto de conexao de saida no canvas, e a edge que sai dela leva
            # `from_key` = nome da porta, entao o proximo node recebe SO aquela
            # chave (ex: [from_key="focos"] -> {"focos": ...}). E o simetrico do
            # `dynamic_inputs` do SubWorkflowOutput, no lado da entrada.
            # Sem esta flag o trigger tinha um unico ponto de saida anonimo e cada
            # edge espalhava o dict inteiro — impossivel escolher o que passar.
            # `ports` vazio/1 porta mantem o ponto anonimo (modo passthrough).
            "outputs_from_ports": True,
            "outputs": [
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Filtra metadados internos do executor (chaves comecando com __)
        # — initial_inputs nao deveria carregar isso, mas defesa em profundidade.
        raw = {k: v for k, v in (inputs or {}).items() if not k.startswith("__")}

        # `ports` declarado = allowlist estrita, simetrica ao SubWorkflowOutput.
        # Antes o filtro so existia na saida: o contrato de entrada valia no save
        # e era ignorado em runtime, entao o filho recebia o namespace inteiro do
        # pai — inclusive chaves fora do contrato.
        # `ports` vazio mantem o passthrough (modo "aceita tudo").
        declared = _parse_ports(self.parameters.get("ports"))
        if not declared:
            return raw

        public = {k: v for k, v in raw.items() if k in declared}

        # Descarte nunca e silencioso: sem este aviso, o operador que mapeia uma
        # chave nao declarada ve o sub-fluxo rodar "com sucesso" e sem o dado.
        dropped = sorted(set(raw) - set(public))
        if dropped:
            logger.warning(
                "SubWorkflowInput: %d chave(s) recebida(s) do pai fora do contrato, "
                "descartada(s): %s. Declaradas: %s.",
                len(dropped), ", ".join(dropped), ", ".join(sorted(declared)) or "<nenhuma>",
            )
        return public
