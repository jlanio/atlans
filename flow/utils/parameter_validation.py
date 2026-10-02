# Em flow/utils/parameter_validation.py

import json
from typing import Any, Dict, List
from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _coerce_structured(key: str, value: Any) -> Any:
    """Normaliza parametros de tipo "object" vindos serializados do canvas.

    O editor de nodes so consegue gravar primitivos — `setNodeField` tem
    assinatura (field, value: string | number | boolean) — entao os helpers
    serializam estruturas com JSON.stringify. Chegavam aqui como str e a
    checagem `isinstance(value, dict)` rejeitava com
    "O parametro 'X' deve ser um objeto (dict)", quebrando em runtime algo que
    a UI tinha gravado corretamente (ex: inputsMapping do SubWorkflow).

    "object" no vocabulario do catalogo significa "estrutura JSON", nao
    estritamente dict: `ports` declara type "object" com default [] (lista).
    Por isso dict e list sao ambos aceitos.
    """
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        texto = value.strip()
        if not texto:
            return {}
        try:
            decodificado = json.loads(texto)
        except (ValueError, TypeError):
            raise ValueError(
                f"O parâmetro '{key}' deve ser um objeto (dict) ou JSON válido. "
                f"Recebido: {value[:80]!r}"
            )
        if isinstance(decodificado, (dict, list)):
            return decodificado
    raise ValueError(
        f"O parâmetro '{key}' deve ser um objeto (dict). "
        f"Tipo recebido: {type(value).__name__}"
    )


def colunas_pedidas(bruto: Any) -> List[str]:
    """Lista de colunas de um campo de fichas ("chips"), venha como lista,
    JSON, ou texto separado por vírgula.

    O campo de fichas grava JSON (`ChipsField` faz JSON.stringify), mas as
    definitions já salvas guardam lista de verdade (editor de objeto) ou o
    formato antigo — texto com vírgulas —, que continua sendo o jeito natural
    de COLAR várias colunas de uma vez no campo novo.

    Um parser tolerante aqui evita uma migration de dados sobre a definition
    de todo workflow que use um desses nós. Nasceu como `_colunas_pedidas` no
    AttributeJoin e subiu para cá quando outros nós ganharam o mesmo campo.

    Devolve list[str] sem vazios e sem espaços nas pontas.
    """
    if isinstance(bruto, (list, tuple)):
        return [str(c).strip() for c in bruto if str(c).strip()]

    texto = str(bruto or "").strip()
    if not texto:
        return []

    if texto.startswith("["):
        try:
            carregado = json.loads(texto)
        except json.JSONDecodeError:
            carregado = None
        if isinstance(carregado, list):
            return [str(c).strip() for c in carregado if str(c).strip()]

    return [c.strip() for c in texto.split(",") if c.strip()]

# Chaves que vivem em `properties` sem serem parametros do no, e que por isso
# nao devem gerar aviso de descarte: o rotulo gravado pelo modal de configuracao
# e os controles de retry que o executor le direto de `parameters` antes do
# execute (core.py::get_retry_params).
#
# Os prefixos legados outputKey*/inputKey* saíram desta lista: auto_map_edges foi
# aposentado (ver core.py e docs/specs/edge-data-contract.md §5), então esses
# params não têm mais efeito e DEVEM aparecer como descartados até serem
# corrigidos à mão.
_CHAVES_DE_PLATAFORMA = frozenset({"alias", "retry_count", "retry_delay_s"})


def _e_de_plataforma(chave: str) -> bool:
    return chave in _CHAVES_DE_PLATAFORMA


def validate_node_parameters(
    params: Dict[str, Any],
    props: List[Dict[str, Any]],
    node_name: str = "",
) -> Dict[str, Any]:
    """
    Nova versão que aceita:
      params:      O dicionário de parâmetros (por ex. self.parameters)
      props:       A lista de propriedades (por ex. description().get("properties"))
      node_name:   Nome do nó, só para identificar o aviso de parâmetro descartado

    Retorna os parâmetros validados (com defaults aplicados).

    ATENÇÃO: o retorno é montado a partir de `props`, então **toda chave de
    `params` que não estiver declarada é descartada**. Isso é o que mantém o nó
    imune a lixo na definition, mas também torna um executor defasado
    indistinguível de um bug de lógica: o servidor publica o catálogo de nós, a
    UI mostra o campo novo e grava o valor, e o executor — com um `flow/` mais
    antigo, cujo descriptor ainda não declara a propriedade — joga o valor fora
    sem erro nenhum. Foi assim que a opção "Sobrescrever se já existir" do
    DataOutput não surtiu efeito. O aviso abaixo existe para que isso apareça
    numa linha de log em vez de virar investigação.
    """
    final_params = {}
    for prop in props:
        key = prop["name"]
        expected_type = prop.get("type")
        default_value = prop.get("default")

        if key in params:
            value = params[key]
            # Campo numérico/booleano LIMPO na UI chega como "" (o input de
            # texto grava string vazia, não remove a chave). Para um parâmetro
            # com default declarado isso é "não preenchido", não um valor:
            # sem este desvio, limpar um campo opcional derrubava a run com
            # "deve ser inteiro. Recebido: ''".
            if value in ("", None) and expected_type in ("integer", "number", "boolean") \
                    and default_value is not None:
                value = default_value
        elif default_value is not None:
            value = default_value
            # opcional: se quiser logar default usado, pode adicionar verbose aqui
        else:
            raise ValueError(f"❌ Parâmetro obrigatório '{key}' ausente.")

        # validação de tipo
        if expected_type:
            if expected_type == "string" and not isinstance(value, str):
                raise ValueError(f"O parâmetro '{key}' deve ser uma string.")
            if expected_type == "object":
                value = _coerce_structured(key, value)
            if expected_type == "number":
                # Coage strings numéricas (a UI de campo texto gravava "5"); só
                # rejeita o que não for número de fato.
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(f"O parâmetro '{key}' deve ser numérico. Recebido: '{value}'.")
                elif isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"O parâmetro '{key}' deve ser numérico.")
            if expected_type == "integer":
                if isinstance(value, bool):
                    raise ValueError(f"O parâmetro '{key}' deve ser inteiro.")
                if isinstance(value, str):
                    try:
                        value = int(value)
                    except ValueError:
                        raise ValueError(f"O parâmetro '{key}' deve ser inteiro. Recebido: '{value}'.")
                elif not isinstance(value, int):
                    # aceita float inteiro (5.0 -> 5); rejeita 5.5
                    if isinstance(value, float) and value.is_integer():
                        value = int(value)
                    else:
                        raise ValueError(f"O parâmetro '{key}' deve ser inteiro.")
            if expected_type == "boolean" and not isinstance(value, bool):
                raise ValueError(f"O parâmetro '{key}' deve ser booleano.")
            if expected_type == "select":
                if not isinstance(value, str):
                    raise ValueError(f"O parâmetro '{key}' deve ser uma string (select).")
                options = prop.get("options", [])
                valid_values = [o["value"] if isinstance(o, dict) else o for o in options]
                if valid_values and value not in valid_values:
                    # Tolera espaços/caixa (como os nós faziam com .strip().lower()/.upper()
                    # antes de migrarem para select) e canonicaliza para o valor da option.
                    stripped = value.strip()
                    match = next((v for v in valid_values if v.lower() == stripped.lower()), None)
                    if match is None:
                        raise ValueError(
                            f"O parâmetro '{key}' deve ser um dos valores: {valid_values}. Recebido: '{value}'."
                        )
                    value = match

        final_params[key] = value

    descartados = sorted(
        k for k in params
        if k not in final_params and not _e_de_plataforma(k)
    )
    if descartados:
        logger.warning(
            "%sparâmetro(s) %s presentes na definição mas ausentes do schema do nó — "
            "descartados. Duas causas: parâmetro obsoleto de um workflow antigo "
            "(inofensivo), ou executor com `flow/` anterior ao que publicou o campo — "
            "aí a opção foi configurada na interface e não surte efeito. Declarados: %s",
            f"[{node_name}] " if node_name else "",
            descartados,
            sorted(p["name"] for p in props),
        )

    return final_params
