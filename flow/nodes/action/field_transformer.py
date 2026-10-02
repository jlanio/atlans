from jinja2 import Undefined
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.jinja_seguro import criar_ambiente_sandbox
from flow.utils.safe_env import safe_env

_JINJA_ENV = criar_ambiente_sandbox(undefined=Undefined)


def _tem_expressao(v: Any) -> bool:
    """True se o valor é uma string com sintaxe Jinja ({{ }} ou {% %})."""
    return isinstance(v, str) and ("{{" in v or "{%" in v)


def _coerce_num(rendered: str) -> Any:
    """Converte o texto renderizado para int/float quando possível.

    Ex: "{{ row.area * 1.1 }}" → float; "ativo" → "ativo".
    """
    try:
        return int(rendered)
    except ValueError:
        pass
    try:
        return float(rendered)
    except ValueError:
        pass
    return rendered


@register_node
class SetFields(BaseNode):
    """
    Adiciona, atualiza, remove ou renomeia campos em um GeoDataFrame.

    Parâmetros:
      - setFields (dict): campos e valores a adicionar ou sobrescrever.
        Suporta expressões Jinja por campo usando {{ row.<coluna> }} e
        variáveis de contexto do workflow (ex: {{ env.NOME_VAR }}).
        Ex: {"area_km2": "{{ row.area / 1e6 }}", "status": "ativo"}

      - removeFields (dict): objeto com chave 'fields' contendo lista de colunas a remover.
        Ex: {"fields": ["temp", "flag"]}

      - renameFields (dict): mapeamento old_name → new_name.
        Ex: {"old_coluna": "nova_coluna"}
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SetFields',
            'alias': 'Definir Campos',
            'description': 'Adiciona, remove ou renomeia colunas de um GeoDataFrame. '
                           'Suporta expressões Jinja nos valores ({{ row.<campo> }}).',
            'type': 'action',
            'properties': [
                {
                    'name': 'setFields',
                    'label': 'Definir campos',
                    'type': 'object',
                    # O type continua "object" (um helper dedicado da web consome
                    # estes campos); o marcador só liga o bloco de sugestões.
                    'suggest_columns': '*',
                    'default': {},
                    'description': (
                        'Campos e valores a definir ou sobrescrever. '
                        'Aceita valores fixos ou expressões Jinja. '
                        'Ex: {"area_km2": "{{ row.area / 1e6 }}", "status": "ativo"}'
                    )
                },
                {
                    'name': 'removeFields',
                    'label': 'Remover campos',
                    'type': 'object',
                    'suggest_columns': '*',
                    'default': {},
                    'description': 'Objeto com lista de colunas a remover. Ex: {"fields": ["temp", "flag_aux"]}'
                },
                {
                    'name': 'renameFields',
                    'label': 'Renomear campos',
                    'type': 'object',
                    'suggest_columns': '*',
                    'default': {},
                    'description': 'Mapeamento de renomeação de colunas. Ex: {"antigo_nome": "novo_nome"}'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com os campos adicionados, removidos ou renomeados'},
            ],
        }

    # CPU-bound puro (Jinja linha a linha sobre o GeoDataFrame inteiro): roda
    # numa thread do pool, não no event loop que atende o WebSocket do executor.
    def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        gdf = self.get_first_gdf(inputs)

        # Contexto disponível nas expressões Jinja — apenas vars seguras
        jinja_context: dict = {"env": safe_env()}

        # SET FIELDS — suporta valores fixos e expressões Jinja por linha
        set_fields: Dict[str, Any] = self.parameters.get('setFields', {})
        if set_fields:
            # Verifica se algum valor usa Jinja para decidir se precisa iterar linha a linha
            has_expressions = any(_tem_expressao(v) for v in set_fields.values())

            if has_expressions:
                # `to_dict(orient='records')` materializa o GeoDataFrame INTEIRO
                # em dicts Python. Ficava dentro da list comprehension, ou seja,
                # era refeito uma vez POR CAMPO: com 5 campos sobre 100k linhas
                # eram 500k dicts construídos para renderizar 500k valores. Uma
                # vez só, fora do laço.
                registros = gdf.to_dict(orient="records")
                for field, raw_value in set_fields.items():
                    if not _tem_expressao(raw_value):
                        # Valor fixo no meio de campos com expressão. Escalar →
                        # broadcast do pandas. Container (lista/tupla/dict/set) →
                        # replicado por linha, preservando o comportamento antigo
                        # (_render_value devolvia o valor cru por linha); sem isto
                        # o pandas tentaria atribuir os elementos coluna a coluna.
                        if isinstance(raw_value, (list, tuple, dict, set)):
                            gdf[field] = [raw_value] * len(gdf)
                        else:
                            gdf[field] = raw_value
                        continue
                    # Compila o template UMA vez por campo — compilar
                    # (source→AST→bytecode) é ordens de magnitude mais caro que
                    # renderizar. Antes recompilava a cada linha × campo: 100k
                    # linhas × 3 campos = 300k compilações do MESMO template.
                    tpl = _JINJA_ENV.from_string(raw_value)
                    gdf[field] = [
                        _coerce_num(tpl.render(row=row, **jinja_context))
                        for row in registros
                    ]
            else:
                # Caminho rápido sem Jinja — atribuição vetorial direta
                for field, value in set_fields.items():
                    gdf[field] = value

        # REMOVE FIELDS
        remove_fields_obj = self.parameters.get("removeFields", {})
        fields_to_remove = (
            remove_fields_obj.get("fields", [])
            if isinstance(remove_fields_obj, dict)
            else []
        )
        if fields_to_remove:
            gdf = gdf.drop(columns=[col for col in fields_to_remove if col in gdf.columns], errors='ignore')

        # RENAME FIELDS
        rename_fields: Dict[str, str] = self.parameters.get('renameFields', {})
        if rename_fields:
            gdf = gdf.rename(columns=rename_fields)

        return {"output": gdf}
