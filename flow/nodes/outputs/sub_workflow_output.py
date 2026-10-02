# flow/nodes/outputs/sub_workflow_output.py
"""
SubWorkflowOutput — declara a "API publica" de um workflow filho.

Quando um workflow B e usado como sub-fluxo (via SubWorkflowNode em A),
historicamente o pai recebia `final_outputs` indexado por UUIDs aleatorios
dos nodes do filho — totalmente nao-utilizavel no canvas.

Este node resolve isso: o operador de B conecta ao SubWorkflowOutput o que
quer expor, e o SubWorkflowNode em A detecta `__subworkflow_output__` e
retorna esse dict como outputs nomeados.

`ports` tem DOIS papeis, que sao o mesmo papel visto de dois lados:

  - com DUAS ou mais portas, cada uma vira um ponto de conexao proprio no
    canvas. O editor preenche o `to_key` da edge com o nome da porta, entao
    cada origem cai na SUA chave — varios nodes podem alimentar a saida ao
    mesmo tempo, um por chave;
  - a lista tambem e a allowlist do que sai para o pai.

Exemplo no canvas de B (duas portas declaradas: focos, mapa):
    WFS        ──────►  ( focos )  SubWorkflowOutput
    RenderMap  ──────►  ( mapa  )

Resultado no canvas de A apos SubWorkflowNode(B):
    outputs = {"subWorkflowResult": {...}, "focos": <gdf>, "mapa": <bytes>}

Com `ports` VAZIO o node volta ao modo passthrough: um unico ponto de conexao
anonimo, uma unica edge, e tudo que chega e devolvido. Duas edges nesse modo
espalhariam os dois dicts nas mesmas chaves e a ultima venceria — por isso o
editor so libera varias conexoes a partir de duas portas declaradas.
"""
from typing import Any, Dict

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.logger import get_logger
from flow.utils.workflow_contract import _parse_ports

logger = get_logger(__name__)


@register_node
class SubWorkflowOutput(BaseNode):
    """Define a saída publica de um workflow para uso como sub-fluxo."""

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
            # Entradas DECLARADAS PELO USUARIO, via a propriedade `ports` — o
            # mesmo mecanismo do PythonScript. E o que permite a mais de um node
            # alimentar a saida publica: com duas ou mais portas o editor
            # preenche o `to_key` de cada edge, e o executor entrega
            # `inputs[to_key]` em vez de sobrescrever tudo na mesma chave.
            "dynamic_inputs": True,
            "outputs": [
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Filtra metadados internos do executor (chaves comecando com __)
        # e tambem chaves nao declaradas em ports (se houver lista).
        declared_set = set(_parse_ports(self.parameters.get("ports")))

        raw = {k: v for k, v in (inputs or {}).items() if not k.startswith("__")}
        if declared_set:
            public = {k: v for k, v in raw.items() if k in declared_set}
            # Descarte com aviso: antes, conectar RenderMap -> Output com
            # to_key="mapa" e esquecer de declarar "mapa" fazia o dado sumir
            # sem erro, sem log e sem sinal no canvas.
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
