# flow/nodes/control/conditional.py

import asyncio
import geopandas as gpd
import operator
import pandas as pd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import to_metric_crs
from flow.utils.logger import get_logger
logger = get_logger(__name__)

# ---------------------------
# Operator dictionary
# ---------------------------
_OP_FUNCS = {
    '==': operator.eq,
    '!=': operator.ne,
    '>':  operator.gt,
    '<':  operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
}


@register_node
class Conditional(BaseNode):
    """
    Control node that evaluates a condition on a value or GeoDataFrame
    and signals the branch (True/False) to the workflow.

    Available metrics:
      - count: size of the container (len) or scalar value
      - area:  sum of the geometries' areas (reprojects to UTM if the CRS is geographic)
      - field: value of a specific field of the GeoDataFrame or dict (requires fieldName)

    Type coercion:
      Tries numeric comparison first (float × float).
      If that fails, falls back to comparison as strings.
      This avoids false negatives when compareTo="10" and val=10.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Conditional',
            'alias': 'Bifurcação',
            'description': 'Avalia uma condição sobre um valor ou GeoDataFrame e sinaliza o branch (True/False).',
            'type': 'control',
            'properties': [
                {
                    'name': 'metric',
                    'label': 'Avaliar',
                    'type': 'select',
                    'default': 'count',
                    'description': "Como extrair o valor a comparar a partir do dado de entrada.",
                    'options': [
                        {'value': 'count', 'label': 'Tamanho (count)'},
                        {'value': 'area',  'label': 'Soma das áreas (apenas GeoDataFrame)'},
                        {'value': 'field', 'label': 'Valor de um campo'},
                    ],
                },
                {
                    'name': 'operator',
                    'label': 'Operador',
                    'type': 'select',
                    'default': '==',
                    'description': 'Operador usado na comparação.',
                    'options': [
                        {'value': '==', 'label': 'Igual a (==)'},
                        {'value': '!=', 'label': 'Diferente de (!=)'},
                        {'value': '>',  'label': 'Maior que (>)'},
                        {'value': '<',  'label': 'Menor que (<)'},
                        {'value': '>=', 'label': 'Maior ou igual (>=)'},
                        {'value': '<=', 'label': 'Menor ou igual (<=)'},
                    ],
                },
                {
                    # Defined as a string to appear in the UI; converted at runtime
                    'name': 'compareTo',
                    'label': 'Comparar com',
                    'type': 'string',
                    'default': '',
                    'description': 'Valor para comparar com a métrica. Numérico (ex: 10) ou texto (ex: "ativo").'
                },
                {
                    'name': 'fieldName',
                    'label': 'Campo (apenas para "Valor de um campo")',
                    'type': 'string',
                    'default': '',
                    'description': "Nome do campo do GeoDataFrame, DataFrame ou chave do dict a avaliar.",
                    # The editor offers the names seen in the last run of the
                    # previous node — same hint as AttributeFilter.
                    'suggest_columns': '*',
                    'visibleWhen': {'field': 'metric', 'in': ['field']},
                },
            ],
            'outputs': [
                {'name': 'result', 'type': 'any', 'description': 'Dado recebido na entrada, repassado adiante'},
                {'name': 'branch', 'type': 'boolean', 'description': 'Resultado da condição (True ou False)'},
                {'name': 'value', 'type': 'number', 'description': 'Valor calculado da métrica avaliada'},
            ],
            'branches': True,
            # The ORDER matters twice, and in both `result` needs to come
            # first. In the simulation, an edge WITHOUT `from_key` makes the executor
            # type the next node's input by the FIRST field of this list
            # (edge_resolver.resolve_edge_schema_inputs): with `branch` first, the
            # editor announced `<boolean>` to whoever received the layer. Today the UI
            # writes `from_key = candidateKeys[0]` (the first data output) when
            # connecting from a branch handle, so new edges no longer fall into this
            # case — but keeping `result` first covers legacy edges. And in
            # the edge's port selector, the first item is the most likely
            # guess — which is the data, not the decision.
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # ---------------------------------------
        # 1) Parameter validation (types + defaults)
        # ---------------------------------------
        self.validate()

        # ---------------------------------------
        # 2) Extracts parameters
        # ---------------------------------------
        # metric/operator already validated against the options by self.validate().
        metric       = self.parameters.get('metric', 'count')
        operator_str = self.parameters.get('operator', '==')
        compare_str  = self.parameters.get('compareTo', '').strip()
        field_name   = self.parameters.get('fieldName', '').strip()

        # ---------------------------------------
        # 3) Gets the input data (first available)
        # ---------------------------------------
        if not inputs:
            raise ValueError("Nenhum dado em inputs para avaliar condição.")
        data = next(iter(inputs.values()))

        # ---------------------------------------
        # 4) Computes the metric "val" on the data
        # ---------------------------------------
        if metric == 'count':
            # Size of the container or the scalar value directly
            if hasattr(data, '__len__') and not isinstance(data, (str, bytes)):
                val = len(data)
            else:
                try:
                    val = float(data)
                except Exception:
                    val = data

        elif metric == 'area':
            if not isinstance(data, gpd.GeoDataFrame):
                raise ValueError("Métrica 'area' requer um GeoDataFrame como entrada.")
            gdf: gpd.GeoDataFrame = data
            # If the CRS is geographic, reprojects to UTM before computing the area
            # (the estimate also goes to the thread: it walks total_bounds)
            if gdf.crs and gdf.crs.is_geographic:
                try:
                    (gdf,) = await asyncio.to_thread(to_metric_crs, gdf)
                except Exception as e:
                    raise RuntimeError(f"Falha ao reprojetar para UTM: {e}")
            val = gdf.geometry.area.sum()

        elif metric == 'field':
            # Evaluates the value of a specific field of the data
            if not field_name:
                raise ValueError(
                    "Bifurcação configurada para avaliar um campo, mas 'Campo' está vazio. "
                    "Preencha o nome da coluna ou chave a avaliar."
                )
            # GeoDataFrame eh subclasse de DataFrame; testar primeiro.
            if isinstance(data, gpd.GeoDataFrame):
                if field_name not in data.columns:
                    raise ValueError(
                        f"Campo '{field_name}' não encontrado no GeoDataFrame. "
                        f"Campos disponíveis: {list(data.columns)}"
                    )
                # Numeric sum of the field; for single-value comparisons, use count=1
                val = data[field_name].sum()
            else:
                # DataFrame puro
                if isinstance(data, pd.DataFrame):
                    if field_name not in data.columns:
                        raise ValueError(
                            f"Campo '{field_name}' não encontrado no DataFrame. "
                            f"Campos disponíveis: {list(data.columns)}"
                        )
                    val = data[field_name].sum()
                elif isinstance(data, dict):
                    if field_name not in data:
                        raise ValueError(
                            f"Campo '{field_name}' não encontrado no dado de entrada. "
                            f"Campos disponíveis: {list(data.keys())}"
                        )
                    val = data[field_name]
                else:
                    raise ValueError(
                        f"Avaliação por campo requer GeoDataFrame, DataFrame ou dict como entrada. "
                        f"Recebido: {type(data).__name__}."
                    )

        # ---------------------------------------
        # 5) Seleciona o operador
        # ---------------------------------------
        op_func = _OP_FUNCS[operator_str]

        # ---------------------------------------
        # 6) Compares with type coercion
        # ---------------------------------------
        # Tries numeric comparison (float × float) first.
        # If val or compareTo are not numeric, falls back to comparison as strings.
        try:
            cmp_num = float(compare_str)
            val_num = float(val)
            branch = bool(op_func(val_num, cmp_num))
        except (ValueError, TypeError):
            # Fallback: comparison as strings (supports "ativo" == "ativo", etc.)
            branch = bool(op_func(str(val), compare_str))

        logger.info(
            "Conditional: metric=%s, val=%s %s %s -> branch=%s",
            metric, val, operator_str, compare_str, branch,
        )

        # ---------------------------------------
        # 7) Returns the result to the workflow
        # ---------------------------------------
        # The ORDER here is the contract with the executor, not aesthetics.
        #
        # `**inputs` used to come LAST and overwrote the `branch`, `value` and
        # `result` this node had just computed. Chaining two
        # forks, the second received the first's keys, computed its
        # own decision and DISCARDED it on the way back: the executor routes by reading
        # `outputs["branch"]` (core.py:628), so the second fork
        # repeated the first's decision and the workflow went down a branch that
        # nobody chose. Spreading first and deciding afterwards makes this node's
        # decision prevail, which is the only correct reading.
        #
        # And `branch` cannot be the FIRST key. When connecting from a branch
        # handle, the UI today writes `from_key = candidateKeys[0]` — the first data
        # output, never the boolean (web/app/components/workflow/index.tsx), so
        # the new edge already resolves to the data. The spread here is the safety
        # net for legacy edges without `from_key` and for whoever reads
        # `next(iter(inputs.values()))` — ComputeBBox, Geocode, HttpRequest on
        # POST, ResponseNode and the control nodes themselves — which would get the
        # BOOLEAN instead of the data. With the spread first, the first
        # key is the data that came from the parent.
        #
        # `result` still exists: it's a selectable port in the edge's
        # selector (custom-edges/index.tsx), and removing it would break workflows
        # that already point to it.
        # `result` closes the dict, and that's not arbitrary: Merge with the
        # "último" strategy scans `reversed(inputs.values())` and would get `value` —
        # the metric's number — if it were the last key. With the data in the
        # first position (under the parent's key) AND in the last (in `result`), both
        # whoever reads `next(iter(...))` and whoever reads back to front receive the
        # layer. Both point to the SAME object, so there's no copy.
        # The control keys are REMOVED from the pass-through before being
        # rewritten, not just overwritten. Reassigning a key that already
        # exists in a Python dict keeps its original POSITION: chaining
        # JinjaBranch → Fork, the inherited `result` stayed in the middle and `value`
        # ended up as the last key — Merge with the "último" strategy went back
        # to getting the metric's number. By rebuilding, the order is always the same:
        # the parent's data, decision, metric, and the data again at the end.
        saida = {k: v for k, v in inputs.items()
                 if k not in ("branch", "value", "result")}
        saida["branch"] = branch
        saida["value"] = val
        saida["result"] = data
        return saida
