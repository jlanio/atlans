# flow/nodes/action/attribute_filter.py

import operator
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)

# Operadores suportados para filtragem
_OP_FUNCS = {
    '==': operator.eq,
    '!=': operator.ne,
    '>':  operator.gt,
    '<':  operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
}

@register_node
class AttributeFilter(BaseNode):
    """
    Filtra um GeoDataFrame por uma condição em um atributo e retorna o resultado.

    Propriedades:
      - attributeName:  coluna a filtrar (string; obrigatório)
      - operator:       um de ['==','!=','>','<','>=','<='] (string; default '==')
      - compareTo:      valor para comparação (string no formulário; convertido em número se possível)
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'AttributeFilter',
            'alias': 'Filtro de Atributo',
            'description': 'Filtra um GeoDataFrame por uma condição em um atributo',
            'type': 'action',
            'properties': [
                {
                    'name': 'attributeName', 'required': True,
                    'label': 'Coluna',
                    'type': 'string',
                    # Nó de entrada única: '*' e a porta dariam no mesmo.
                    'suggest_columns': '*',
                    'default': '',
                    'description': 'Nome da coluna do GeoDataFrame para aplicar o filtro.'
                },
                {
                    'name': 'operator',
                    'label': 'Operador',
                    'type': 'select',
                    'default': '==',
                    'description': 'Operador de comparação.',
                    'options': [
                        {'value': '==', 'label': 'Igual (==)'},
                        {'value': '!=', 'label': 'Diferente (!=)'},
                        {'value': '>',  'label': 'Maior (>)'},
                        {'value': '<',  'label': 'Menor (<)'},
                        {'value': '>=', 'label': 'Maior ou igual (>=)'},
                        {'value': '<=', 'label': 'Menor ou igual (<=)'},
                    ],
                },
                {
                    'name': 'compareTo', 'required': True,
                    'label': 'Comparar com',
                    'type': 'string',
                    'default': '',
                    'description': 'Valor a ser comparado com a coluna (ex.: 42, 3.5 ou texto).'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame filtrado pelo atributo'},
            ],
        }

    # Máscara + `.copy()` sobre o GeoDataFrame inteiro são CPU-bound: rodando no
    # event loop do executor, um filtro sobre centenas de milhares de linhas
    # segurava heartbeat, node_events e o `cancel` do usuário.
    def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # ---------------------------------------------------
        # 1) Validação de parâmetros básicos + aplica defaults
        # ---------------------------------------------------
        self.validate()

        # ---------------------------------------------------
        # 2) Extrai parâmetros (já validados como strings)
        # ---------------------------------------------------
        attribute    = self.parameters.get('attributeName', '').strip()
        op_str       = self.parameters.get('operator', '==').strip()
        compare_str  = self.parameters.get('compareTo', '').strip()

        # ---------------------------------------------------
        # 3) Obtém o GeoDataFrame via helper da classe base
        # ---------------------------------------------------
        gdf = self.get_first_gdf(inputs)

        # ---------------------------------------------------
        # 4) Verifica se attributeName foi informado e existe no GeoDataFrame
        # ---------------------------------------------------
        if not attribute:
            raise ValueError("Parâmetro 'attributeName' é obrigatório.")

        if attribute not in gdf.columns:
            available = ", ".join(gdf.columns.tolist())
            raise ValueError(
                f"Atributo '{attribute}' não existe no GeoDataFrame. "
                f"Colunas disponíveis: [{available}]"
            )

        # ---------------------------------------------------
        # 5) Verifica se o operador é válido
        # ---------------------------------------------------
        # operator já validado contra as options pelo self.validate().
        op_func = _OP_FUNCS[op_str]

        # ---------------------------------------------------
        # 6) Tenta converter compareTo para número (float), se possível
        # ---------------------------------------------------
        if compare_str == "":
            raise ValueError("Parâmetro 'compareTo' é obrigatório e não pode ficar em branco.")

        cmp_val: Any = compare_str
        try:
            cmp_val = float(compare_str)
        except Exception:
            # Permanece como string — usará comparação literal
            pass

        # ---------------------------------------------------
        # 7) Aplica o filtro no GeoDataFrame
        # ---------------------------------------------------
        try:
            mask = op_func(gdf[attribute], cmp_val)
        except Exception as e:
            raise ValueError(f"Erro ao aplicar filtro na coluna '{attribute}': {e}") from e

        filtered = gdf[mask].copy()

        # ---------------------------------------------------
        # 8) Retorna o GeoDataFrame filtrado
        # ---------------------------------------------------
        return {"output": filtered}
