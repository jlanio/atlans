from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class MergeNode(BaseNode):
    """
    Control node that merges inputs from multiple branches into a single output.
    Used after Conditional or JinjaBranch to rejoin the diverging paths.

    Properties:
      - strategy: merge strategy: 'first', 'last' or 'all'
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
            ],
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
