# flow/executor/rendering.py
"""Renderização de parâmetros de nós via Jinja2 com sistema de aliases."""
from typing import Any, Dict
from flow.utils.expression_service import ExpressionService
from flow.utils.logger import get_logger

logger = get_logger(__name__)

expr_svc = ExpressionService()

# Teto de aninhamento na descida por dict/list. Parâmetro de formulário não
# chega perto disso; o limite existe só para uma estrutura patológica não virar
# recursão infinita.
_PROFUNDIDADE_MAX = 12

# O que o SERVIDOR injeta a partir da credencial salva (ver
# app/services/credential_resolver.py): segredo, nunca template. Renderizar
# mudaria em silêncio uma senha com `{{`, `{%` ou `$Alias.campo` dentro — e a
# falha de renderização repetiria o segredo na mensagem de erro, que vai à
# tela, ao banco e ao log (o DEBUG daqui também o escreveria cru).
_INJETADOS_PELO_SERVIDOR = frozenset({"connectionString", "http_auth", "s3_auth"})


def _tem_expressao(raw: str, named: Dict[str, Any]) -> bool:
    """A string pede renderização?

    Statements `{% %}` contam como Jinja tanto quanto expressões `{{ }}`.
    Antes o gate exigia `{{` E `}}`, então um parâmetro contendo apenas
    `{% ... %}` não era renderizado aqui e seguia CRU até o nó — que podia
    avaliá-lo num ambiente próprio. Passando pelo expr_svc (sandboxed),
    statement e expressão recebem o mesmo tratamento.
    """
    has_jinja = ("{{" in raw and "}}" in raw) or ("{%" in raw and "%}" in raw)
    m_alias = expr_svc.find_alias(raw)
    has_valid_alias = bool(m_alias and m_alias.group("alias").split(".")[0] in named)
    return has_jinja or has_valid_alias


def _renderizar(
    valor: Any,
    *,
    node_id: str,
    caminho: str,
    named: Dict[str, Any],
    context: Dict[str, Any],
    profundidade: int = 0,
) -> Any:
    """Renderiza um valor de parâmetro, descendo por dicionários e listas.

    A versão anterior parava na primeira linha (`if not isinstance(raw, str):
    continue`) e só renderizava parâmetro string de topo. Quem sofria com isso
    eram justamente os campos que existem para receber valor dinâmico:

      - `queryParams` do DatabaseQuery/DatabaseSpatialQuery — os valores dos
        `:placeholders`, que é ONDE o valor variável do filtro deveria entrar.
        A UI ainda instrui, logo acima do campo, a usar `{{ $Alias }}`.
      - `headers` e `params` do HttpRequest.

    E o modo de falha era pior que "não funciona": o dicionário seguia cru até o
    nó, o template ia como TEXTO para o banco (`WHERE bairro = '{{ ... }}'`), a
    consulta rodava, voltava vazia e o fluxo continuava. Nenhum erro em lugar
    nenhum.

    A chave do dicionário não é renderizada — só o valor. Em `queryParams` a
    chave é o nome do `:placeholder` e precisa casar com o SQL; em `headers` é o
    nome do cabeçalho. Não há caso de uso, e um template que produzisse chave
    vazia ou repetida quebraria o dicionário em silêncio.
    """
    if isinstance(valor, str):
        if not _tem_expressao(valor, named):
            return valor
        logger.debug("[%s] Param raw (%s): %s", node_id, caminho, valor)
        try:
            # Dentro de dicionário/lista, o tipo é preservado quando o valor é
            # uma expressão só: `{{ $Filtro.limite }}` com 50 devolve o inteiro
            # 50, não `'50'`. É o que `queryParams` precisa — ali o valor vira
            # bind de SQL, e o tipo decide como o Postgres compara com a coluna.
            #
            # No topo (profundidade 0) segue `render`, que devolve texto. Ali já
            # existe comportamento de que os nós dependem há tempo, e mudá-lo
            # junto misturaria uma correção com uma quebra: um nó que faz
            # `.strip()` num parâmetro passaria a receber int. O tratamento
            # nativo entra só onde nada era renderizado antes.
            renderizado = (
                expr_svc.render_native(valor, context) if profundidade > 0
                else expr_svc.render(valor, context)
            )
        except Exception as e:
            msg = (
                f"[Node {node_id} | param '{caminho}']\n"
                f"  Falha ao renderizar a expressão: {valor!r}\n"
                f"  Erro: {e}\n"
                f"  Aliases disponíveis: {sorted(named.keys())}\n"
            )
            logger.error(msg)
            raise ValueError(msg) from e
        logger.debug("[%s] Param rendered (%s): %s", node_id, caminho, renderizado)
        return renderizado

    if profundidade >= _PROFUNDIDADE_MAX:
        return valor

    if isinstance(valor, dict):
        return {
            chave: _renderizar(
                item, node_id=node_id, caminho=f"{caminho}.{chave}",
                named=named, context=context, profundidade=profundidade + 1,
            )
            for chave, item in valor.items()
        }

    if isinstance(valor, list):
        return [
            _renderizar(
                item, node_id=node_id, caminho=f"{caminho}[{i}]",
                named=named, context=context, profundidade=profundidade + 1,
            )
            for i, item in enumerate(valor)
        ]

    # Número, booleano, None, GeoDataFrame fixado — nada a renderizar.
    return valor


def render_node_parameters(
    node,
    node_id: str,
    named: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Renderiza parâmetros do nó usando Jinja2.

    Retorna cópia dos parameters com expressões renderizadas.
    Não modifica node.parameters diretamente — o caller deve atribuir o resultado.
    """
    context.update(named)
    return {
        chave: valor if chave in _INJETADOS_PELO_SERVIDOR else _renderizar(
            valor, node_id=node_id, caminho=chave,
            named=named, context=context,
        )
        for chave, valor in node.parameters.items()
    }
