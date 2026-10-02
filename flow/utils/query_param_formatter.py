#/flow/utils/query_param_formatter.py

import re
from typing import Any, Dict, List, Tuple

from flow.utils.sql_guard import strip_sql_literals

# Regex pré-compilado para encontrar placeholders :nome
_PLACEHOLDER_PATTERN = re.compile(r'(?<!:):(?P<key>[A-Za-z_]\w*)\b')

def prepare_query(query: str, params: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """
    Converte placeholders :chave em $1, $2, ... de forma estável (mesmo placeholder → mesmo índice),
    e retorna (query_preparada, valores_ordenados).
    
    Exemplo:
        query = "SELECT * FROM imoveis WHERE id = :id AND bairro = :bairro OR fk_id = :id"
        params = {"id": 5, "bairro": "Centro"}
    
    Retorna:
        (
            "SELECT * FROM imoveis WHERE id = $1 AND bairro = $2 OR fk_id = $1",
            [5, "Centro"]
        )

    Só conta como placeholder o que está em posição de CÓDIGO. Antes o regex
    varria o texto cru, e `:nome` dentro de literal ou comentário era tratado
    como parâmetro — com dois desfechos, ambos silenciosos para quem escreveu:

        WHERE obs = 'urgente:revisar'      -> "Parâmetro SQL 'revisar' não
                                              fornecido", e uma query
                                              perfeitamente válida era recusada.
        WHERE tag = 'nota:importante'      -> virava `'nota$1'` se existisse um
                                              parâmetro chamado `importante`: o
                                              conteúdo do literal era trocado por
                                              um bind, e a consulta passava a
                                              filtrar outra coisa.

    O mapa de posições vem de `strip_sql_literals`, que preserva o comprimento
    da query e apaga só o que é texto — o mesmo scanner que o `sql_guard` usa
    para não confundir português com comando.
    """
    # Mesmo comprimento da query: o índice de um match aqui vale lá.
    mapa = strip_sql_literals(query)
    if len(mapa) != len(query):  # pragma: no cover - invariante do scanner
        # Se o mascaramento deixar de preservar o comprimento, as posições
        # deslizam e os recortes abaixo montam uma query ERRADA em silêncio.
        # Falhar aqui é a única saída aceitável.
        raise RuntimeError(
            "strip_sql_literals não preservou o comprimento da query — "
            "as posições dos placeholders não são confiáveis."
        )

    index_map: Dict[str, int] = {}
    values: List[Any] = []
    pedacos: List[str] = []
    fim_anterior = 0

    for match in _PLACEHOLDER_PATTERN.finditer(mapa):
        key = match.group("key")
        if key not in params:
            raise ValueError(f"Parâmetro SQL '{key}' não fornecido.")
        if key not in index_map:
            index_map[key] = len(index_map) + 1
            values.append(params[key])
        pedacos.append(query[fim_anterior:match.start()])
        pedacos.append(f"${index_map[key]}")
        fim_anterior = match.end()

    pedacos.append(query[fim_anterior:])
    return "".join(pedacos), values


def resolver_query_params(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Decide entre o `queryParams` recebido do nó anterior e o configurado no nó.

    Vale PRESENÇA, e não veracidade. A forma anterior era
    `inputs.get('queryParams') or parameters.get('queryParams', {})`, e o `or`
    tratava `{}` como ausência — mas um dicionário vazio vindo de uma aresta é
    uma resposta, não um silêncio: significa "não há filtro nenhum". O nó
    ignorava essa resposta e caía no valor estático, então uma consulta que
    deveria rodar sem filtro rodava com os filtros antigos, gravados no
    formulário — e o resultado voltava plausível, só que errado.

    `inputs` é chaveado pelo `to_key` da aresta (ver executor/core.py), então a
    chave estar ali significa exatamente que alguém ligou uma aresta apontando
    para `queryParams`.
    """
    veio_da_aresta = 'queryParams' in inputs
    valor = inputs['queryParams'] if veio_da_aresta else parameters.get('queryParams', {})

    if valor is None:
        valor = {}

    if not isinstance(valor, dict):
        origem = (
            "recebido do nó anterior" if veio_da_aresta
            else "configurado no campo 'Parâmetros da consulta'"
        )
        raise ValueError(
            f"'queryParams' ({origem}) deve ser um objeto JSON. "
            f"Recebido: {type(valor).__name__}."
        )
    return valor
