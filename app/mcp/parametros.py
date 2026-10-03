# app/mcp/parametros.py
"""
Validation and coercion of `inputs` against the workflow's `params_schema`.

Until now nobody validated: the run screen merely COERCED in the browser
(`Number("")` becomes `0`, `Boolean("false")` becomes `True`, `object` went
raw) and the server accepted whatever arrived. With an MCP client in place of
the screen, that silence gets expensive: whoever builds the call does not see
the form, sends everything as text and discovers the error mid-run — after
spending an executor, writing to the database and producing a wrong artifact.
Hence the rule lives here, BEFORE dispatch, and is the same for everyone.

Three decisions that explain the shape:

- **Coercion only from strings.** JSON already distinguishes `1` from `"1"`; if
  the caller sent `1` where `boolean` was declared, that is the caller's
  mistake, not a loose format. What coercion solves is the legitimate text
  case — the command line, the form, the environment variable — all of which
  arrive as strings.
- **An empty string never becomes a value.** That was the screen's worst
  defect: a blank field became `0` and the workflow ran with a number nobody
  typed. Empty is absence, and absence of a required field is an error.
- **A malformed `params_schema` is not an error.** An old workflow (or one
  generated outside the screen) may have a `params_schema` that is null, a
  list, or values that do not describe a type. Refusing the run because of
  that would break workflows that work today; the right thing is to pass the
  inputs along and SAY, in a hint, that nobody checked them.

An undeclared key also passes through untouched: the webhook trigger has its
own `payload_schema`, validated at dispatch, and complaining here about a field
that the other contract requires would be refusing the right workflow.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from app.core.utils.logger import scrub_text
from app.mcp.erros import erro

# The types that the parameters screen emits and that the executor knows how to
# receive. A `type` outside this list signals a schema of other provenance — and
# a schema we do not recognize becomes "no contract", not an error.
TIPOS = ("string", "number", "boolean", "object")

# Pure integer: this is what decides between `int` and `float`. Without it, "3"
# would become `3.0` and a node that indexes a list or builds pagination would
# receive a float.
_INTEIRO = re.compile(r"^-?\d+$")

# Accepted spellings for a boolean in text. Includes `nao` without the accent
# because people writing on the command line rarely use accents, and refusing
# because of the tilde would be an error with no gain at all.
_VERDADEIRO = frozenset({"true", "1", "yes", "sim"})
_FALSO = frozenset({"false", "0", "no", "não", "nao"})

# Nesting ceiling for an `object`. A real workflow parameter stays far below
# it — a FeatureCollection of MultiPolygons reaches 8 levels. Up to Python 3.11
# the ceiling was implicit: `json.loads` raised `RecursionError` near 1000
# levels. From 3.12 on the decoder counts against the C recursion limit, and
# 2000 levels pass — the object went on and blew the stack in whoever traversed
# it later (validation, copying, the executor), far from this layer, which
# exists to return `validation`. Explicit, it holds the same in any version.
_PROFUNDIDADE_MAXIMA = 100

HINT_SEM_CONTRATO = "params_schema ausente ou malformado: inputs não validados"


def _schema_valido(params_schema: Any) -> bool:
    """Does the `params_schema` describe a contract? (run screen format)

    A non-empty dict whose values are all dicts with a known `type`. The EMPTY
    dict counts as absent on purpose: "no parameter declared" and "a schema I
    cannot read" lead to the same place — nothing to check.
    """
    if not isinstance(params_schema, dict) or not params_schema:
        return False
    return all(
        isinstance(decl, dict) and decl.get("type") in TIPOS
        for decl in params_schema.values()
    )


def _para_numero(valor: Any) -> tuple[Any, str | None]:
    # `bool` is a subclass of `int` in Python: without this line, `True` would
    # pass as the number 1 and the workflow would receive a boolean where it
    # expects a quantity.
    if isinstance(valor, bool):
        return None, "esperado number; booleano não é número"
    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and not math.isfinite(valor):
            return None, "esperado number finito"
        return valor, None
    if not isinstance(valor, str):
        return None, "esperado number"
    texto = valor.strip()
    if not texto:
        return None, "esperado number; string vazia não é zero"
    if _INTEIRO.match(texto):
        # The `try` is not superfluous: since 3.10.7 the interpreter imposes a
        # ceiling of 4300 digits (`sys.set_int_max_str_digits`) for converting
        # text to int, and above it `int()` raises `ValueError`. Letting it
        # bubble up raw would hand the client an "unexpected error" — the
        # `ferramenta` decorator only translates `ToolError`, `AtlasBaseError`
        # and `HTTPException` — in a case that is an input error like any
        # other and one the client fixes on its own.
        try:
            return int(texto), None
        except ValueError:
            return None, "esperado number; inteiro com dígitos demais"
    try:
        numero = float(texto)
    except ValueError:
        return None, "esperado number; o texto enviado não é numérico"
    if not math.isfinite(numero):
        return None, "esperado number finito"
    return numero, None


def _para_booleano(valor: Any) -> tuple[Any, str | None]:
    if isinstance(valor, bool):
        return valor, None
    if not isinstance(valor, str):
        # Including `1`/`0`: in JSON, a number is a number. Whoever wants a
        # boolean writes `true` or sends the string "1".
        return None, "esperado boolean"
    texto = valor.strip().lower()
    if texto in _VERDADEIRO:
        return True, None
    if texto in _FALSO:
        return False, None
    return None, "esperado boolean (true/false, 1/0, yes/no, sim/não)"


def _para_texto(valor: Any) -> tuple[Any, str | None]:
    if isinstance(valor, str):
        return valor, None
    if isinstance(valor, bool):
        # "true"/"false", not "True"/"False": the value came from JSON and goes
        # on to a workflow expression, where the lowercase spelling is the
        # recognized one.
        return ("true" if valor else "false"), None
    if isinstance(valor, (int, float)):
        return str(valor), None
    return None, "esperado string"


def _fundo_demais(valor: Any) -> bool:
    """Does the `object` exceed `_PROFUNDIDADE_MAXIMA` levels? (the root is level 1)

    Iterative on purpose — measuring recursively would blow the stack in the
    very case the measurement exists to refuse — and one level per pass, with
    the next level's containers collected in a comprehension: it runs on the
    event loop, and a 200-thousand-point GeoJSON passed as `object` cost
    hundreds of milliseconds in the item-by-item loop.
    """
    nivel = [valor]
    for _ in range(_PROFUNDIDADE_MAXIMA):
        nivel = [
            filho
            for conteiner in nivel
            for filho in (conteiner.values() if isinstance(conteiner, dict) else conteiner)
            if isinstance(filho, (dict, list))
        ]
        if not nivel:
            return False
    return True


def _para_objeto(valor: Any) -> tuple[Any, str | None]:
    if isinstance(valor, (dict, list)):
        decodificado = valor
    elif not isinstance(valor, str):
        return None, "esperado object (objeto ou lista JSON)"
    else:
        try:
            decodificado = json.loads(valor)
        except (ValueError, RecursionError):
            # `RecursionError` goes in alongside `ValueError` — and it is not a
            # cleanup to be done: the CPython decoder is recursive and, with
            # deep enough nesting (`"[[[[..."`), it blows the stack BEFORE
            # deciding whether the text is valid JSON. Since it inherits from
            # `RuntimeError`, it would escape the `ferramenta` decorator and
            # become an "unexpected error" for the client, instead of the
            # `validation` this layer exists to produce. From the caller's
            # point of view it is the same failure as the others: the text is
            # not JSON the server can read.
            return None, "esperado object; o texto enviado não é JSON válido"
        if not isinstance(decodificado, (dict, list)):
            return None, "esperado object; o JSON enviado não é objeto nem lista"
    if _fundo_demais(decodificado):
        return None, f"esperado object; aninhamento acima de {_PROFUNDIDADE_MAXIMA} níveis"
    return decodificado, None


_COERCOES = {
    "string": _para_texto,
    "number": _para_numero,
    "boolean": _para_booleano,
    "object": _para_objeto,
}


def validar_inputs(params_schema: Any, inputs: dict | None) -> tuple[dict, list[str]]:
    """Checks `inputs` against `params_schema` and returns `(inputs, hints)`.

    Errors are AGGREGATED into a single `validation` `ToolError` with
    `errors=[{path, message}]`: the caller fixes everything at once instead of
    discovering one problem per attempt. The message names the field and the
    expected type and never echoes the value received — a parameter may carry
    a password, and the error is a secret's easiest route into the log.

    `hints` is a warning, not a refusal: a schema without a contract and an
    undeclared key go there so the caller knows what was NOT checked.
    """
    hints: list[str] = []

    if inputs is None:
        recebidos: dict[str, Any] = {}
    elif isinstance(inputs, dict):
        recebidos = dict(inputs)
    else:
        raise erro(
            "validation",
            "inputs precisa ser um objeto com um campo por parâmetro.",
            "consulte params_schema em get_workflow(workflow_id)",
            errors=[{"path": "inputs", "message": "esperado object"}],
        )

    if not _schema_valido(params_schema):
        hints.append(HINT_SEM_CONTRATO)
        return recebidos, hints

    saida: dict[str, Any] = {}
    erros: list[dict[str, str]] = []

    for nome, decl in params_schema.items():
        caminho = f"inputs.{nome}"
        coagir = _COERCOES[decl["type"]]
        # An explicit `None` counts as absence: none of the four types accepts
        # null, so treating it as a value would only produce a worse error
        # ("expected string") in place of the right one ("required").
        presente = nome in recebidos and recebidos[nome] is not None

        if not presente:
            # `default: None` is the SAME rule as the null input, applied on the
            # other side of the contract: null is absence of a value, not a
            # value. It holds for the same reason — none of the four types
            # accepts null, so coercing it would only produce an error. Except
            # that here the error would be WORSE than the input one: it would
            # blame the workflow's `params_schema`, which the caller did not
            # write and cannot fix with any input, leaving the workflow
            # unrunnable through the MCP. And `null` for an optional field is
            # what an ordinary JSON serializer emits, including in workflows
            # created by `create_workflow`.
            padrao = decl.get("default")
            if padrao is not None:
                # The default is coerced too: a `"5"` written in the schema has to
                # reach the executor as 5, otherwise the omitted value behaves
                # differently from the typed value.
                valor, problema = coagir(padrao)
                if problema:
                    erros.append({"path": caminho, "message": f"default do params_schema inválido: {problema}"})
                else:
                    saida[nome] = valor
            elif decl.get("required"):
                erros.append({"path": caminho, "message": "obrigatório e sem default"})
            continue

        valor, problema = coagir(recebidos[nome])
        if problema:
            erros.append({"path": caminho, "message": problema})
        else:
            saida[nome] = valor

    nao_declaradas = [nome for nome in recebidos if nome not in params_schema]
    for nome in nao_declaradas:
        saida[nome] = recebidos[nome]
    if nao_declaradas:
        hints.append(
            "chaves fora do params_schema, enviadas sem conferência: "
            + ", ".join(sorted(nao_declaradas))
        )

    if erros:
        raise erro(
            "validation",
            "Alguns inputs não batem com o params_schema do workflow.",
            "veja errors, corrija e chame de novo; get_workflow mostra o params_schema",
            errors=[
                {"path": scrub_text(item["path"]), "message": scrub_text(item["message"])}
                for item in erros
            ],
        )

    return saida, hints
