# flow/nodes/control/conditional.py

import asyncio
import geopandas as gpd
import operator
import pandas as pd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import para_crs_metrico
from flow.utils.logger import get_logger
logger = get_logger(__name__)

# ---------------------------
# Dicionário de operadores
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
    Nó de controle que avalia uma condição sobre um valor ou GeoDataFrame
    e sinaliza o branch (True/False) para o fluxo.

    Métricas disponíveis:
      - count: tamanho do container (len) ou valor escalar
      - area:  soma das áreas das geometrias (reprojeta para UTM se CRS geográfico)
      - field: valor de um campo específico do GeoDataFrame ou dict (requer fieldName)

    Coerção de tipo:
      Tenta comparação numérica primeiro (float × float).
      Se falhar, faz fallback para comparação como string.
      Isso evita falsos negativos quando compareTo="10" e val=10.
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
                    # Definido como string para aparecer no UI; convertido em runtime
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
                    # O editor oferece os nomes vistos na última execução do nó
                    # anterior — mesma dica do AttributeFilter.
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
            # A ORDEM importa duas vezes, e nas duas o `result` precisa vir na
            # frente. Na simulação, uma aresta SEM `from_key` faz o executor tipar
            # a entrada do nó seguinte pelo PRIMEIRO campo desta lista
            # (edge_resolver.resolve_edge_schema_inputs): com `branch` na frente, o
            # editor anunciava `<boolean>` para quem recebia a camada. Hoje a UI
            # grava `from_key = candidateKeys[0]` (a primeira saída de dado) ao
            # conectar de um handle de ramo, então arestas novas já não caem nesse
            # caso — mas manter `result` na frente cobre as arestas legadas. E no
            # seletor de porta da aresta, o primeiro item é o palpite mais
            # provável — que é o dado, não a decisão.
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # ---------------------------------------
        # 1) Validação de parâmetros (tipos + defaults)
        # ---------------------------------------
        self.validate()

        # ---------------------------------------
        # 2) Extrai parâmetros
        # ---------------------------------------
        # metric/operator já validados contra as options pelo self.validate().
        metric       = self.parameters.get('metric', 'count')
        operator_str = self.parameters.get('operator', '==')
        compare_str  = self.parameters.get('compareTo', '').strip()
        field_name   = self.parameters.get('fieldName', '').strip()

        # ---------------------------------------
        # 3) Obtém o dado de entrada (primeiro disponível)
        # ---------------------------------------
        if not inputs:
            raise ValueError("Nenhum dado em inputs para avaliar condição.")
        data = next(iter(inputs.values()))

        # ---------------------------------------
        # 4) Calcula a métrica "val" sobre o dado
        # ---------------------------------------
        if metric == 'count':
            # Tamanho do container ou valor escalar direto
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
            # Se CRS for geográfico, reprojeta para UTM antes de calcular área
            # (a estimativa também vai para a thread: percorre total_bounds)
            if gdf.crs and gdf.crs.is_geographic:
                try:
                    (gdf,) = await asyncio.to_thread(para_crs_metrico, gdf)
                except Exception as e:
                    raise RuntimeError(f"Falha ao reprojetar para UTM: {e}")
            val = gdf.geometry.area.sum()

        elif metric == 'field':
            # Avalia o valor de um campo específico do dado
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
                # Soma numérica do campo; para comparações de valor único, usar count=1
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
        # 6) Compara com coerção de tipo
        # ---------------------------------------
        # Tenta comparação numérica (float × float) primeiro.
        # Se val ou compareTo não forem numéricos, faz fallback para comparação como string.
        try:
            cmp_num = float(compare_str)
            val_num = float(val)
            branch = bool(op_func(val_num, cmp_num))
        except (ValueError, TypeError):
            # Fallback: comparação como string (suporta "ativo" == "ativo", etc.)
            branch = bool(op_func(str(val), compare_str))

        logger.info(
            "Conditional: metric=%s, val=%s %s %s -> branch=%s",
            metric, val, operator_str, compare_str, branch,
        )

        # ---------------------------------------
        # 7) Retorna o resultado para o fluxo
        # ---------------------------------------
        # A ORDEM aqui é o contrato com o executor, e não estética.
        #
        # `**inputs` vinha por ÚLTIMO e sobrescrevia `branch`, `value` e
        # `result` que este nó acabou de calcular. Encadeando duas
        # bifurcações, a segunda recebia as chaves da primeira, computava a
        # própria decisão e a DESCARTAVA na volta: o executor roteia lendo
        # `outputs["branch"]` (core.py:628), então a segunda bifurcação
        # repetia a decisão da primeira e o fluxo seguia por um ramo que
        # ninguém escolheu. Espalhar primeiro e decidir depois faz a decisão
        # deste nó prevalecer, que é a única leitura correta.
        #
        # E `branch` não pode ser a PRIMEIRA chave. Ao conectar de um handle de
        # ramo, a UI hoje grava `from_key = candidateKeys[0]` — a primeira saída
        # de dado, nunca o booleano (web/app/components/workflow/index.tsx), então
        # a aresta nova já resolve para o dado. O espalhamento aqui é a rede de
        # segurança para arestas legadas sem `from_key` e para quem lê
        # `next(iter(inputs.values()))` — ComputeBBox, Geocode, HttpRequest no
        # POST, ResponseNode e os próprios nós de controle — que pegaria o
        # BOOLEANO em vez do dado. Com o espalhamento na frente, a primeira
        # chave é o dado que veio do pai.
        #
        # `result` continua existindo: é uma porta escolhível no seletor da
        # aresta (custom-edges/index.tsx), e sumir com ela quebraria fluxos
        # que já a apontam.
        # `result` fecha o dict, e não é arbitrário: o Merge com estratégia
        # "último" varre `reversed(inputs.values())` e pegaria o `value` — o
        # número da métrica — se ele fosse a última chave. Com o dado na
        # primeira posição (pela chave do pai) E na última (em `result`), tanto
        # quem lê `next(iter(...))` quanto quem lê de trás para frente recebe a
        # camada. Os dois apontam para o MESMO objeto, então não há cópia.
        # As chaves de controle são REMOVIDAS do repasse antes de serem
        # reescritas, e não apenas sobrescritas. Reatribuir uma chave que já
        # existe num dict Python mantém a POSIÇÃO original dela: encadeando
        # JinjaBranch → Bifurcação, o `result` herdado ficava no meio e `value`
        # terminava como última chave — o Merge com estratégia "último" voltava
        # a pegar o número da métrica. Reconstruindo, a ordem é sempre a mesma:
        # dados do pai, decisão, métrica, e o dado de novo no fim.
        saida = {k: v for k, v in inputs.items()
                 if k not in ("branch", "value", "result")}
        saida["branch"] = branch
        saida["value"] = val
        saida["result"] = data
        return saida
