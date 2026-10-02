# flow/core/expression_service.py

import re
import threading
from uuid import uuid4
from jinja2 import StrictUndefined
from flow.utils.datetime_utils import utc_now_naive
from flow.utils.jinja_seguro import criar_ambiente_sandbox
from flow.utils.safe_env import safe_env

# Captura $Alias ou $Alias.key.subkey (com dotted path opcional).
#
# `[^\W\d]` é "letra ou _" em Unicode — `\w` menos os dígitos. O padrão antigo
# abria com `[A-Za-z_]` e recusava alias começado por letra acentuada: o
# executor registra "Área" (str.isidentifier() aceita Unicode) e o modal deixa
# criá-lo, mas `$Área.total` não casava aqui, o `$` sobrevivia ao pré-processo e
# o Jinja estourava erro de sintaxe. Curiosamente "Bifurcação" funcionava — o
# `\w*` do resto já era Unicode; só a primeira letra era ASCII-only.
#
# Vale também para o dotted path: nome de coluna vinda de shapefile costuma ter
# acento, e `$Alias.população` caía no mesmo buraco.
_ALIAS_PATTERN = re.compile(r'\$(?P<alias>[^\W\d]\w*(?:\.[^\W\d]\w*)*)')

# Blocos Jinja: expressão, statement e comentário. Servem para separar o que já
# É Jinja do texto comum, porque `$Alias` recebe tratamento diferente nos dois.
_BLOCO_JINJA = re.compile(r"(\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})", re.DOTALL)


def _preprocessar_aliases(template: str) -> str:
    """Traduz `$Alias` para Jinja, respeitando onde ele está.

    FORA de um bloco Jinja, `$Alias.campo` vira `{{ Alias.campo }}` — que é o
    que quem escreveu quis dizer. DENTRO de um bloco, vira só `Alias.campo`,
    porque ali já se está numa expressão.

    A versão anterior fazia outra coisa: tirava o `$` do texto inteiro e, se
    não houvesse nenhum `{{`, embrulhava a STRING INTEIRA em `{{ }}`. Isso só
    funciona quando o template é um alias sozinho. Nos outros casos dava em
    três desfechos, e o pior deles era silencioso:

        $Pedido.id                          -> 42                    (ok)

        https://api.org/v1/$Pedido.id/dados -> TemplateSyntaxError:
                                               "expected token 'end of print
                                               statement', got ':'" — quem
                                               escreveu uma URL recebia um erro
                                               de parser de template.

        {"id": $Pedido.id,                  -> "{'id': 42,
         "n": "$Pedido.nome"}                  'n': 'Pedido.nome'}"
                                               A string inteira era avaliada
                                               como expressão Python: o corpo
                                               virava repr de dict (aspas
                                               simples, JSON inválido) e o alias
                                               entre aspas virava TEXTO literal.
                                               Sem erro nenhum.

        .../{{ Pedido.id }}/x/$Pedido.nome  -> ".../42/x/Pedido.nome"
                                               Misturando as duas sintaxes, o
                                               `$Alias` virava texto literal —
                                               também em silêncio.
    """
    partes = _BLOCO_JINJA.split(template)
    saida = []
    for i, parte in enumerate(partes):
        if i % 2:  # separador capturado: já é um bloco Jinja
            saida.append(_ALIAS_PATTERN.sub(lambda m: m.group("alias"), parte))
        else:
            saida.append(_ALIAS_PATTERN.sub(lambda m: "{{ " + m.group("alias") + " }}", parte))
    return "".join(saida)


# Teto do cache de templates compilados. Templates sao definidos no workflow
# (finitos por fluxo), mas o executor e long-lived e ve muitos fluxos — o cap
# evita crescimento ilimitado. 512 cobre fluxos grandes com folga.
_TEMPLATE_CACHE_MAX = 512


class ExpressionService:
    """
    Serviço para renderizar templates Jinja2 em sandbox para o GISFlow.
    Expõe utilitários como now(), uuid() e variáveis de ambiente.
    """
    def __init__(self):
        self.env = criar_ambiente_sandbox(undefined=StrictUndefined)
        self.env.globals.update({
            "now":      lambda fmt=None: utc_now_naive().strftime(fmt or "%Y-%m-%dT%H:%M:%SZ"),
            "uuid":     lambda: str(uuid4()),
            "env":      safe_env(),
        })
        # Cache LRU de templates COMPILADOS. `env.from_string` compila
        # source->AST->bytecode a cada chamada; era feito uma vez por parametro
        # templatizado por node por run. O Template resultante e reutilizavel
        # entre renders (stateless — o contexto entra so no .render()).
        from collections import OrderedDict
        self._template_cache: "OrderedDict[str, object]" = OrderedDict()
        # `_compiled` roda dentro dos `asyncio.to_thread` dos nos (o render de
        # parametros vai para thread), entao varias threads mutavam este LRU ao
        # mesmo tempo — `move_to_end`/`__setitem__`/`popitem` sem lock corrompem
        # o OrderedDict ou levantam. O lock protege so as operacoes O(1) do dict;
        # a compilacao (cara) fica FORA dele (dupla checagem em `_compiled`).
        self._template_cache_lock = threading.Lock()

    def _compiled(self, source: str):
        with self._template_cache_lock:
            cached = self._template_cache.get(source)
            if cached is not None:
                self._template_cache.move_to_end(source)
                return cached
        # Compila FORA do lock: duas threads podem compilar o mesmo source cru
        # concorrentemente (raro, so no aquecimento), mas o bloco abaixo
        # reconcilia — em troca, `from_string` nao serializa entre threads.
        tmpl = self.env.from_string(source)
        with self._template_cache_lock:
            existente = self._template_cache.get(source)
            if existente is not None:
                self._template_cache.move_to_end(source)
                return existente
            self._template_cache[source] = tmpl
            if len(self._template_cache) > _TEMPLATE_CACHE_MAX:
                self._template_cache.popitem(last=False)
            return tmpl

    # Um template que é UMA expressão só, e nada além dela: `{{ x }}`, com
    # espaço em volta permitido. É o caso em que faz sentido devolver o valor
    # nativo em vez do texto — não há prefixo nem sufixo para concatenar.
    _SO_UMA_EXPRESSAO = re.compile(r"^\{\{(?P<expr>(?:(?!\}\}).)*)\}\}$", re.DOTALL)

    def render_native(self, template: str, context: dict):
        """Como `render`, mas preserva o TIPO quando o template é uma expressão só.

        `Template.render()` do Jinja devolve texto sempre: `{{ x }}` com x=50 vira
        `'50'`, e com x=None vira a string `'None'`. Onde o resultado é
        concatenado isso é o certo. Onde ele vira valor de bind de SQL, não é: o
        `queryParams` de um nó de banco alimenta `$1`, e o tipo do valor decide
        como o Postgres o compara com a coluna.

        Só o caso sem ambiguidade recebe tratamento nativo — o template inteiro
        sendo uma única expressão. `ano-{{ x }}` continua string, porque texto é
        exatamente o que ele pede. E o valor nativo só é devolvido para escalar
        não-string (número, booleano, nulo); qualquer outra coisa volta pelo
        caminho de texto, para não entregar a um nó um tipo que ele não espera.
        """
        preprocessado = _preprocessar_aliases(template).strip()
        m = self._SO_UMA_EXPRESSAO.match(preprocessado)
        if m:
            # `compile_expression` avalia no MESMO ambiente sandboxado e devolve
            # o objeto, em vez de passá-lo por str().
            #
            # `undefined_to_none=False` é essencial: no padrão (True) uma
            # referência inexistente vira None em silêncio, e o StrictUndefined
            # do ambiente — que existe para transformar alias errado em erro
            # acionável — seria contornado justo aqui. Com False, o Undefined
            # volta intacto, não casa com nenhum tipo nativo e cai no `render`
            # abaixo, que levanta com a mensagem de sempre.
            valor = self.env.compile_expression(
                m.group("expr").strip(), undefined_to_none=False,
            )(**context)
            if valor is None or isinstance(valor, (int, float, bool)):
                return valor

        return self.render(template, context)

    def find_alias(self, text: str) -> re.Match | None:
        """Retorna o primeiro match de alias no texto, ou None."""
        return _ALIAS_PATTERN.search(text)

    def render(self, template: str, context: dict) -> str:
        # 1) `$Alias` vira Jinja no lugar onde está (ver _preprocessar_aliases)
        preprocessed = _preprocessar_aliases(template)

        # 2) Delega ao Jinja2 (StrictUndefined) para renderizar. O template
        #    compilado e cacheado por source — so o .render() roda por node.
        return self._compiled(preprocessed).render(**context)
