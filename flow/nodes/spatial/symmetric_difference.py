from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.spatial.sobreposicao_binaria import SobreposicaoBinaria


@register_node
class SymmetricDifferenceNode(SobreposicaoBinaria):
    """
    Computes the symmetric difference between two vector layers (A △ B).
    """

    HOW = 'symmetric_difference'
    OPERACAO = 'diferença simétrica'
    ROTULO = 'diferença simétrica'
    DESCRICAO_LOG = 'diferença simétrica'

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SymmetricDifferenceNode',
            'alias': 'Diferença Simétrica',
            'description': 'Realiza a operação de diferença simétrica (A △ B).',
            'type': 'spatial',
            'properties': [],
            'inputs': [
                {'name': 'layerA', 'type': 'geodataframe', 'description': 'Primeira camada (GeoDataFrame).'},
                {'name': 'layerB', 'type': 'geodataframe', 'description': 'Segunda camada (GeoDataFrame).'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da diferença simétrica entre as camadas'},
            ],
        }
