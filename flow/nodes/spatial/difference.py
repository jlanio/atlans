from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.spatial.sobreposicao_binaria import BinaryOverlay


@register_node
class DifferenceNode(BinaryOverlay):
    """
    Computes the spatial difference (A - B) between two vector layers.
    """

    HOW = 'difference'
    OPERACAO = 'operação de diferença'
    ROTULO = 'diferença'
    DESCRICAO_LOG = 'diferença espacial A - B'

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'DifferenceNode',
            'alias': 'Diferença Espacial',
            'description': 'Realiza a operação de diferença espacial (A - B).',
            'type': 'spatial',
            'properties': [],
            'inputs': [
                {'name': 'layerA', 'type': 'geodataframe', 'description': 'Camada A (GeoDataFrame base).'},
                {'name': 'layerB', 'type': 'geodataframe', 'description': 'Camada B (GeoDataFrame a subtrair).'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da diferença espacial A - B'},
            ],
        }
