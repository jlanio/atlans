# flow/core/expression_service.py

import re
import threading
from uuid import uuid4
from jinja2 import StrictUndefined
from flow.utils.datetime_utils import utc_now_naive
from flow.utils.jinja_seguro import criar_ambiente_sandbox
from flow.utils.safe_env import safe_env

# Captures $Alias or $Alias.key.subkey (with an optional dotted path).
#
# `[^\W\d]` is "letter or _" in Unicode — `\w` minus digits. The old pattern
# started with `[A-Za-z_]` and rejected an alias starting with an accented
# letter: the executor registers "Área" (str.isidentifier() accepts Unicode) and
# the modal lets you create it, but `$Área.total` did not match here, the `$`
# survived preprocessing and Jinja blew up with a syntax error. Curiously
# "Bifurcação" worked — the `\w*` for the rest was already Unicode; only the
# first letter was ASCII-only.
#
# The same applies to the dotted path: column names coming from shapefiles often
# have accents, and `$Alias.população` fell into the same hole.
_ALIAS_PATTERN = re.compile(r'\$(?P<alias>[^\W\d]\w*(?:\.[^\W\d]\w*)*)')

# Jinja blocks: expression, statement and comment. Used to separate what already
# IS Jinja from plain text, because `$Alias` is treated differently in each.
_BLOCO_JINJA = re.compile(r"(\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})", re.DOTALL)


def _preprocessar_aliases(template: str) -> str:
    """Translates `$Alias` into Jinja, respecting where it is.

    OUTSIDE a Jinja block, `$Alias.campo` becomes `{{ Alias.campo }}` — which is
    what the author meant. INSIDE a block, it becomes just `Alias.campo`,
    because there you are already in an expression.

    The previous version did something else: it stripped the `$` from the whole
    text and, if there was no `{{`, wrapped the ENTIRE STRING in `{{ }}`. That
    only works when the template is a lone alias. In the other cases it had
    three outcomes, and the worst of them was silent:

        $Pedido.id                          -> 42                    (ok)

        https://api.org/v1/$Pedido.id/dados -> TemplateSyntaxError:
                                               "expected token 'end of print
                                               statement', got ':'" — whoever
                                               wrote a URL got a template
                                               parser error.

        {"id": $Pedido.id,                  -> "{'id': 42,
         "n": "$Pedido.nome"}                  'n': 'Pedido.nome'}"
                                               The whole string was evaluated
                                               as a Python expression: the body
                                               became a dict repr (single
                                               quotes, invalid JSON) and the
                                               quoted alias became literal TEXT.
                                               No error at all.

        .../{{ Pedido.id }}/x/$Pedido.nome  -> ".../42/x/Pedido.nome"
                                               Mixing the two syntaxes, the
                                               `$Alias` became literal text —
                                               also silently.
    """
    partes = _BLOCO_JINJA.split(template)
    saida = []
    for i, parte in enumerate(partes):
        if i % 2:  # captured separator: already a Jinja block
            saida.append(_ALIAS_PATTERN.sub(lambda m: m.group("alias"), parte))
        else:
            saida.append(_ALIAS_PATTERN.sub(lambda m: "{{ " + m.group("alias") + " }}", parte))
    return "".join(saida)


# Ceiling for the compiled-template cache. Templates are defined in the workflow
# (finite per workflow), but the executor is long-lived and sees many workflows —
# the cap prevents unbounded growth. 512 covers large workflows comfortably.
_TEMPLATE_CACHE_MAX = 512


class ExpressionService:
    """
    Service for rendering sandboxed Jinja2 templates for GISFlow.
    Exposes utilities such as now(), uuid() and environment variables.
    """
    def __init__(self):
        self.env = criar_ambiente_sandbox(undefined=StrictUndefined)
        self.env.globals.update({
            "now":      lambda fmt=None: utc_now_naive().strftime(fmt or "%Y-%m-%dT%H:%M:%SZ"),
            "uuid":     lambda: str(uuid4()),
            "env":      safe_env(),
        })
        # LRU cache of COMPILED templates. `env.from_string` compiles
        # source->AST->bytecode on every call; it used to run once per
        # templated parameter per node per run. The resulting Template is reusable
        # across renders (stateless — the context only enters in .render()).
        from collections import OrderedDict
        self._template_cache: "OrderedDict[str, object]" = OrderedDict()
        # `_compiled` runs inside the nodes' `asyncio.to_thread` (parameter
        # rendering goes to a thread), so several threads mutated this LRU at
        # the same time — `move_to_end`/`__setitem__`/`popitem` without a lock
        # corrupt the OrderedDict or raise. The lock protects only the O(1) dict
        # operations; the (expensive) compilation stays OUTSIDE it (double-checked
        # in `_compiled`).
        self._template_cache_lock = threading.Lock()

    def _compiled(self, source: str):
        with self._template_cache_lock:
            cached = self._template_cache.get(source)
            if cached is not None:
                self._template_cache.move_to_end(source)
                return cached
        # Compiles OUTSIDE the lock: two threads may compile the same raw source
        # concurrently (rare, only during warm-up), but the block below
        # reconciles — in exchange, `from_string` does not serialize across threads.
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

    # A template that is ONE single expression and nothing else: `{{ x }}`, with
    # surrounding whitespace allowed. This is the case where returning the native
    # value instead of the text makes sense — there is no prefix or suffix to
    # concatenate.
    _SO_UMA_EXPRESSAO = re.compile(r"^\{\{(?P<expr>(?:(?!\}\}).)*)\}\}$", re.DOTALL)

    def render_native(self, template: str, context: dict):
        """Like `render`, but preserves the TYPE when the template is a single expression.

        Jinja's `Template.render()` always returns text: `{{ x }}` with x=50 becomes
        `'50'`, and with x=None it becomes the string `'None'`. Where the result is
        concatenated that is right. Where it becomes an SQL bind value, it is not: the
        `queryParams` of a database node feed `$1`, and the value's type decides
        how Postgres compares it with the column.

        Only the unambiguous case gets native treatment — the whole template
        being a single expression. `ano-{{ x }}` stays a string, because text is
        exactly what it asks for. And the native value is returned only for a
        non-string scalar (number, boolean, null); anything else goes back through
        the text path, so a node is not handed a type it does not expect.
        """
        preprocessado = _preprocessar_aliases(template).strip()
        m = self._SO_UMA_EXPRESSAO.match(preprocessado)
        if m:
            # `compile_expression` evaluates in the SAME sandboxed environment and
            # returns the object, instead of passing it through str().
            #
            # `undefined_to_none=False` is essential: by default (True) a
            # nonexistent reference silently becomes None, and the environment's
            # StrictUndefined — which exists to turn a wrong alias into an
            # actionable error — would be bypassed right here. With False, the
            # Undefined comes back intact, matches no native type and falls into
            # the `render` below, which raises with the usual message.
            valor = self.env.compile_expression(
                m.group("expr").strip(), undefined_to_none=False,
            )(**context)
            if valor is None or isinstance(valor, (int, float, bool)):
                return valor

        return self.render(template, context)

    def find_alias(self, text: str) -> re.Match | None:
        """Returns the first alias match in the text, or None."""
        return _ALIAS_PATTERN.search(text)

    def render(self, template: str, context: dict) -> str:
        # 1) `$Alias` becomes Jinja where it stands (see _preprocessar_aliases)
        preprocessed = _preprocessar_aliases(template)

        # 2) Delegates rendering to Jinja2 (StrictUndefined). The compiled
        #    template is cached by source — only .render() runs per node.
        return self._compiled(preprocessed).render(**context)
