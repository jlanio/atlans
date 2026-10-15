from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.workflow_contract import _parse_ports
logger = get_logger(__name__)


@register_node
class MergeNode(BaseNode):
    """
    Control node that merges inputs from multiple branches into a single output.
    Used after Conditional or JinjaBranch to rejoin the diverging paths.

    Properties:
      - strategy: merge strategy: 'first', 'last' or 'all'
      - ports: declared input ports (optional)

    Every input arrives under the key its edge delivers (`to_key`, else
    `from_key`). Two parallel branches wired from nodes that both produce
    `output` wrote the SAME key: the second overwrote the first and 'all'
    returned one branch, with nothing failing. With two or more declared
    ports the editor gives each edge its own `to_key` (the port it lands on),
    'all' returns {port: value} and 'first'/'last' follow the port order.
    Without ports nothing changes.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Merge',
            'alias': 'Mesclagem',
            'description': (
                'Mescla entradas de múltiplos branches em uma única saída. '
                "Estratégias: 'first' (primeiro não-None), 'last' (último), "
                "'all' (todos como dicionário)."
            ),
            'type': 'control',
            'properties': [
                {
                    'name': 'strategy',
                    'label': 'Estratégia',
                    'type': 'select',
                    'default': 'first',
                    'description': 'Como mesclar os valores dos branches de entrada.',
                    'options': [
                        {'value': 'first', 'label': 'Primeiro valor não-nulo'},
                        {'value': 'last',  'label': 'Último valor não-nulo'},
                        {'value': 'all',   'label': 'Todos (como dicionário)'},
                    ],
                },
                {
                    'name': 'ports',
                    'label': 'Portas de entrada',
                    'type': 'ports',
                    'default': [],
                    'description': (
                        'Nome de cada entrada. Vazio: cada conexão chega com o nome da '
                        'saída do nó anterior, e duas com o mesmo nome se sobrescrevem '
                        "(só a última fica). Com DUAS ou mais, cada porta vira um ponto "
                        "de conexão próprio: 'all' devolve {porta: valor} e 'first'/'last' "
                        'seguem a ordem das portas.'
                    ),
                },
            ],
            # Inputs DECLARED BY THE USER, via `ports` — the same mechanism as
            # the Python Script: with two or more ports the editor writes each
            # edge's `to_key`. Empty by default, so existing Merges keep their
            # single anonymous input and run exactly as before.
            'dynamic_inputs': True,
            'outputs': [
                {'name': 'output', 'type': 'any', 'description': 'Valor mesclado dos branches de entrada'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # -------------------------------------------------------
        # 1) Parameter validation and extraction
        # -------------------------------------------------------
        self.validate()

        # strategy already validated against the options by self.validate().
        strategy = self.parameters.get('strategy', 'first')

        if not inputs:
            logger.warning("MergeNode recebeu inputs vazios.")
            return {'output': None}

        portas = _parse_ports(self.parameters.get('ports'))
        if portas:
            # Port order, not arrival order: 'first' is the first port with a
            # value. A key outside the ports (an edge with no `to_key`) is kept,
            # after them — dropping it would lose a branch with no sign.
            fora = [k for k in inputs if k not in portas]
            avisar = [str(k) for k in fora if not str(k).startswith("__")]
            if avisar:
                logger.warning(
                    "MergeNode: entrada(s) fora das portas declaradas: %s. Portas: %s. "
                    "Ligue cada conexão a uma porta.",
                    ", ".join(avisar), ", ".join(portas),
                )
            inputs = {
                **{p: inputs[p] for p in portas if p in inputs},
                **{k: inputs[k] for k in fora},
            }

        logger.info(
            f"MergeNode: estratégia='{strategy}', "
            f"chaves de entrada={list(inputs.keys())}"
        )

        # -------------------------------------------------------
        # 2) Applies the merge strategy
        # -------------------------------------------------------
        merged = None

        if strategy == 'first':
            for val in inputs.values():
                if val is not None:
                    merged = val
                    break

        elif strategy == 'last':
            for val in reversed(list(inputs.values())):
                if val is not None:
                    merged = val
                    break

        elif strategy == 'all':
            merged = dict(inputs)

        logger.info(
            f"MergeNode: mesclagem concluída com estratégia '{strategy}'. "
            f"Tipo do resultado: {type(merged).__name__}"
        )

        return {'output': merged}
