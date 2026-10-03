# flow/nodes/action/attribute_filter.py

import operator
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)

# Operators supported for filtering
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
    Filters a GeoDataFrame by a condition on an attribute and returns the result.

    Properties:
      - attributeName:  column to filter (string; required)
      - operator:       one of ['==','!=','>','<','>=','<='] (string; default '==')
      - compareTo:      value to compare against (string in the form; converted to a number if possible)
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
                    # Single-input node: '*' and the port would amount to the same thing.
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

    # Mask + `.copy()` over the whole GeoDataFrame are CPU-bound: running on the
    # executor's event loop, a filter over hundreds of thousands of rows
    # held up the heartbeat, node_events and the user's `cancel`.
    def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # ---------------------------------------------------
        # 1) Validation of basic parameters + applies defaults
        # ---------------------------------------------------
        self.validate()

        # ---------------------------------------------------
        # 2) Extracts parameters (already validated as strings)
        # ---------------------------------------------------
        attribute    = self.parameters.get('attributeName', '').strip()
        op_str       = self.parameters.get('operator', '==').strip()
        compare_str  = self.parameters.get('compareTo', '').strip()

        # ---------------------------------------------------
        # 3) Gets the GeoDataFrame via the base class helper
        # ---------------------------------------------------
        gdf = self.get_first_gdf(inputs)

        # ---------------------------------------------------
        # 4) Checks that attributeName was provided and exists in the GeoDataFrame
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
        # 5) Checks that the operator is valid
        # ---------------------------------------------------
        # operator already validated against the options by self.validate().
        op_func = _OP_FUNCS[op_str]

        # ---------------------------------------------------
        # 6) Tries to convert compareTo to a number (float), if possible
        # ---------------------------------------------------
        if compare_str == "":
            raise ValueError("Parâmetro 'compareTo' é obrigatório e não pode ficar em branco.")

        cmp_val: Any = compare_str
        try:
            cmp_val = float(compare_str)
        except Exception:
            # Stays a string — will use literal comparison
            pass

        # ---------------------------------------------------
        # 7) Applies the filter to the GeoDataFrame
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
