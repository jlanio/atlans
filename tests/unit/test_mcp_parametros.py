# tests/unit/test_mcp_parametros.py
"""
The `inputs` × `params_schema` rule — the one the server now enforces.

Before this module, the only place that looked at `params_schema` was the
screen's dialog, and it merely coerced: `Number("")` became `0`, `Boolean(qualquer
coisa)` (anything) became `True` and `required` was visual decoration. Whoever calls from outside
the screen has no form at all, sends everything as text and only discovers the
mistake mid-run — after spending an executor and writing to a database.

The cases here are, one by one, what the screen let through:

- empty is not zero, and required with no value is an error (not `0`, not `""`);
- `"false"`, `"0"` and `"não"` are false — naive coercion turned them into `True`;
- coercion ONLY from text: `1` is not `true`, `true` is not `1`;
- a schema that doesn't describe a contract refuses nothing, but warns;
- `null` is absence on both sides: in the input and in the schema's `default`;
- an absurd value (JSON nested too deep, an integer with thousands of digits)
  comes out as a validation error, never as a raw exception — raising the
  exception would hand "unexpected error" to someone who can fix the input alone;
- the errors all come out at once, with a path, and never echo the value — a
  parameter may carry a password.
"""
from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp.parametros import HINT_NO_CONTRACT, validate_inputs


def _response_body(exc: ToolError) -> dict:
    return json.loads(str(exc))


def _error(params_schema, inputs) -> dict:
    with pytest.raises(ToolError) as capturado:
        validate_inputs(params_schema, inputs)
    return _response_body(capturado.value)


# ── No contract: doesn't validate, but warns ──────────────────────────────────


@pytest.mark.parametrize(
    "schema",
    [
        None,
        {},
        [],
        "string",
        {"x": "number"},                       # value is not a dict
        {"x": {"type": "array"}},              # type outside the four
        {"x": {"type": "string"}, "y": {}},    # one of the fields has no type
    ],
)
def test_schema_without_contract_lets_the_inputs_through_with_hint(schema):
    """An old workflow keeps running: what's missing is checking, not permission."""
    inputs, hints = validate_inputs(schema, {"x": "3", "y": True})

    assert inputs == {"x": "3", "y": True}
    assert HINT_NO_CONTRACT in hints


def test_without_schema_and_inputs_returns_empty_dict():
    inputs, hints = validate_inputs(None, None)

    assert inputs == {}
    assert hints == [HINT_NO_CONTRACT]


def test_inputs_that_is_not_an_object_is_refused():
    corpo = _error({"x": {"type": "string"}}, ["x"])

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [{"path": "inputs", "message": "esperado object"}]


# ── Required, default, absence ────────────────────────────────────────────────


def test_missing_required_is_error():
    corpo = _error({"cidade": {"type": "string", "required": True}}, {})

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [{"path": "inputs.cidade", "message": "obrigatório e sem default"}]


def test_required_with_default_is_filled_without_error():
    inputs, hints = validate_inputs(
        {"limite": {"type": "number", "required": True, "default": 10}}, {}
    )

    assert inputs == {"limite": 10}
    assert hints == []


def test_text_default_arrives_coerced():
    """`"5"` written in the schema must become 5, otherwise omitting differs from typing."""
    inputs, _ = validate_inputs({"limite": {"type": "number", "default": "5"}}, {})

    assert inputs == {"limite": 5}


def test_invalid_default_is_reported_by_path():
    corpo = _error({"limite": {"type": "number", "default": "dez"}}, {})

    assert corpo["errors"][0]["path"] == "inputs.limite"
    assert "default do params_schema" in corpo["errors"][0]["message"]


def test_missing_optional_does_not_enter_as_null():
    """No `{"cidade": None}`: the node would see the key and treat the null as a value."""
    inputs, hints = validate_inputs({"cidade": {"type": "string"}}, {})

    assert inputs == {}
    assert hints == []


def test_explicit_null_counts_as_absence():
    corpo = _error({"cidade": {"type": "string", "required": True}}, {"cidade": None})

    assert corpo["errors"][0]["message"] == "obrigatório e sem default"


def test_null_default_on_optional_counts_as_absence_and_the_field_is_omitted():
    """`default: null` must not make the workflow unexecutable via MCP.

    It is the same rule as the null input, applied on the other side of the
    contract: null is the absence of a value. Coercing it always produced
    `problema` (none of the four types accepts null) and the error blamed the
    WORKFLOW's `params_schema` — which the caller didn't write and can't fix
    with any input. And `null` for a blank optional field is exactly what an
    ordinary JSON serializer emits.
    """
    inputs, hints = validate_inputs({"bairro": {"type": "string", "default": None}}, {})

    assert inputs == {}
    assert hints == []


def test_null_default_on_required_reports_the_required_not_the_default():
    """No value and no default is a missing input — that is the useful diagnosis."""
    corpo = _error({"bairro": {"type": "string", "default": None, "required": True}}, {})

    assert corpo["errors"] == [{"path": "inputs.bairro", "message": "obrigatório e sem default"}]


# ── number ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "enviado,esperado",
    [
        ("42", 42),
        ("-7", -7),
        (" 42 ", 42),
        ("3.5", 3.5),
        ("-0.5", -0.5),
        ("1e3", 1000.0),
        (42, 42),
        (3.5, 3.5),
    ],
)
def test_number_accepts_number_and_numeric_text(enviado, esperado):
    inputs, _ = validate_inputs({"n": {"type": "number"}}, {"n": enviado})

    assert inputs == {"n": esperado}
    assert type(inputs["n"]) is type(esperado)


def test_number_with_empty_string_is_error_never_zero():
    """O defeito original da tela: campo em branco virava `0` e o fluxo rodava."""
    corpo = _error({"n": {"type": "number"}}, {"n": ""})

    assert corpo["errors"] == [{"path": "inputs.n", "message": "esperado number; string vazia não é zero"}]


@pytest.mark.parametrize("enviado", ["  ", "dez", "1,5", "12abc", True, False, [], {}])
def test_number_refuses_what_is_not_a_number(enviado):
    corpo = _error({"n": {"type": "number"}}, {"n": enviado})

    assert corpo["errors"][0]["path"] == "inputs.n"
    assert corpo["errors"][0]["message"].startswith("esperado number")


@pytest.mark.parametrize("enviado", ["inf", "-inf", "nan", float("inf")])
def test_number_refuses_infinity_and_nan(enviado):
    """`json.dumps(float("inf"))` produces `Infinity`, which is not valid JSON."""
    corpo = _error({"n": {"type": "number"}}, {"n": enviado})

    assert corpo["errors"][0]["message"] == "esperado number finito"


def test_number_with_too_many_digit_integer_is_refused_without_breaking_the_call():
    """The interpreter has a 4300-digit ceiling for converting text to int.

    Above it `int()` raises `ValueError` — which is not `ToolError`,
    `AtlasBaseError` nor `HTTPException` and therefore escaped the `ferramenta`
    decorator: the client received "unexpected error" instead of `validation`
    with `errors[]`. The path is reachable because the value arrives as a JSON
    STRING; a raw JSON number with 5000 digits would already die in the SDK's
    parser.
    """
    corpo = _error({"n": {"type": "number", "required": True}}, {"n": "1" * 5000})

    assert corpo["code"] == "validation"
    assert corpo["errors"][0]["path"] == "inputs.n"
    assert corpo["errors"][0]["message"].startswith("esperado number")


def test_default_with_too_many_digit_integer_is_reported_as_default():
    """The default goes through the SAME coercion — and fell through the same raw exception."""
    corpo = _error({"n": {"type": "number", "default": "1" * 5000}}, {})

    assert corpo["code"] == "validation"
    assert corpo["errors"][0]["path"] == "inputs.n"
    assert "default do params_schema" in corpo["errors"][0]["message"]


# ── boolean ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "enviado,esperado",
    [
        ("true", True), ("TRUE", True), ("True", True),
        ("1", True), ("yes", True), ("sim", True), (" Sim ", True),
        ("false", False), ("FALSE", False),
        ("0", False), ("no", False), ("não", False), ("NÃO", False), ("nao", False),
        (True, True), (False, False),
    ],
)
def test_boolean_understands_the_text_spellings(enviado, esperado):
    inputs, _ = validate_inputs({"b": {"type": "boolean"}}, {"b": enviado})

    assert inputs == {"b": esperado}


@pytest.mark.parametrize("enviado", [1, 0, 2, "talvez", "", [], {}])
def test_boolean_refuses_number_and_unknown_text(enviado):
    """In JSON, a number is a number: whoever wants a boolean writes `true` or `"1"`."""
    corpo = _error({"b": {"type": "boolean"}}, {"b": enviado})

    assert corpo["errors"][0]["path"] == "inputs.b"
    assert corpo["errors"][0]["message"].startswith("esperado boolean")


# ── string ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "enviado,esperado",
    [("oi", "oi"), ("", ""), (42, "42"), (3.5, "3.5"), (True, "true"), (False, "false")],
)
def test_string_accepts_text_and_converts_scalars(enviado, esperado):
    inputs, _ = validate_inputs({"s": {"type": "string"}}, {"s": enviado})

    assert inputs == {"s": esperado}


@pytest.mark.parametrize("enviado", [{"a": 1}, [1, 2]])
def test_string_refuses_structure(enviado):
    corpo = _error({"s": {"type": "string"}}, {"s": enviado})

    assert corpo["errors"] == [{"path": "inputs.s", "message": "esperado string"}]


# ── object ────────────────────────────────────────────────────────────────────


def test_object_accepts_dict_and_list():
    inputs, _ = validate_inputs(
        {"o": {"type": "object"}, "l": {"type": "object"}},
        {"o": {"a": 1}, "l": [1, 2]},
    )

    assert inputs == {"o": {"a": 1}, "l": [1, 2]}


def test_object_decodes_json_in_text():
    inputs, _ = validate_inputs({"o": {"type": "object"}}, {"o": '{"a": 1}'})

    assert inputs == {"o": {"a": 1}}


def test_object_accepts_json_that_yields_a_list():
    inputs, _ = validate_inputs({"o": {"type": "object"}}, {"o": "[1, 2]"})

    assert inputs == {"o": [1, 2]}


@pytest.mark.parametrize(
    "enviado,trecho",
    [
        ("{a: 1}", "não é JSON válido"),
        ("", "não é JSON válido"),
        ('"texto"', "não é objeto nem lista"),
        ("42", "não é objeto nem lista"),
        ("null", "não é objeto nem lista"),
        (42, "esperado object"),
    ],
)
def test_object_refuses_invalid_or_scalar_json(enviado, trecho):
    corpo = _error({"o": {"type": "object"}}, {"o": enviado})

    assert trecho in corpo["errors"][0]["message"]


def test_object_with_too_deeply_nested_json_becomes_validation_error():
    """Deep nesting blew the stack instead of becoming an input error.

    CPython's decoder is recursive and raises `RecursionError` BEFORE deciding
    whether the text is valid JSON. Since it inherits from `RuntimeError`, it
    escaped the `except ValueError` and the `ferramenta` decorator, and the
    client received "unexpected error" — in a case it can fix alone — with the
    stack at its limit inside the request handler. 100 thousand levels blow up
    on any version.
    """
    corpo = _error({"cfg": {"type": "object"}}, {"cfg": "[" * 100_000 + "]" * 100_000})

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [
        {"path": "inputs.cfg", "message": "esperado object; o texto enviado não é JSON válido"}
    ]


def _nested(tiers: int) -> list:
    """A list with `tiers` levels, built without recursion."""
    valor: list = []
    for _ in range(tiers - 1):
        valor = [valor]
    return valor


@pytest.mark.parametrize("como", ["texto", "nativo"])
def test_object_too_deep_is_refused_even_when_the_json_decodes(como):
    """From 3.12 onward `json.loads` accepts 2000 levels (the decoder counts
    against the C recursion limit): without the explicit ceiling, the object
    got past here and blew the stack of whoever traversed it later. Native too —
    the call body arrives already decoded. 150 levels decode on any version,
    and the result is the same on all of them."""
    fundo = _nested(150)
    enviado = json.dumps(fundo) if como == "texto" else fundo
    corpo = _error({"cfg": {"type": "object"}}, {"cfg": enviado})

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [
        {"path": "inputs.cfg", "message": "esperado object; aninhamento acima de 100 níveis"}
    ]


def test_object_at_the_nesting_ceiling_passes():
    at_ceiling = _nested(100)
    inputs, _ = validate_inputs({"cfg": {"type": "object"}}, {"cfg": json.dumps(at_ceiling)})
    assert inputs == {"cfg": at_ceiling}

    corpo = _error({"cfg": {"type": "object"}}, {"cfg": json.dumps(_nested(101))})
    assert corpo["errors"][0]["message"] == "esperado object; aninhamento acima de 100 níveis"


# ── Undeclared keys ───────────────────────────────────────────────────────────


def test_undeclared_key_passes_intact_and_becomes_hint():
    """The webhook trigger has its own `payload_schema`, checked later."""
    inputs, hints = validate_inputs(
        {"cidade": {"type": "string"}},
        {"cidade": "Recife", "payload": {"id": 9}, "extra": "1"},
    )

    assert inputs == {"cidade": "Recife", "payload": {"id": 9}, "extra": "1"}
    assert len(hints) == 1
    assert "extra" in hints[0] and "payload" in hints[0]


# ── Aggregation and message safety ────────────────────────────────────────────


def test_the_errors_come_out_all_at_once():
    """One problem per attempt would make the caller discover the schema by trial and error."""
    corpo = _error(
        {
            "n": {"type": "number"},
            "b": {"type": "boolean"},
            "s": {"type": "string", "required": True},
        },
        {"n": "", "b": "talvez"},
    )

    caminhos = [item["path"] for item in corpo["errors"]]
    assert caminhos == ["inputs.n", "inputs.b", "inputs.s"]
    assert corpo["code"] == "validation"
    assert corpo["hint"]


def test_the_error_message_does_not_echo_the_sent_value():
    """A parameter may carry a password; the error is the easiest route into the log."""
    corpo = _error(
        {"dsn": {"type": "number"}},
        {"dsn": "postgresql://ana:sup3rs3cr3t@db.local:5432/geo"},  # pragma: allowlist secret
    )

    texto = json.dumps(corpo, ensure_ascii=False)
    assert "sup3rs3cr3t" not in texto
    assert "db.local" not in texto


def test_the_input_dict_is_not_modified():
    """The caller still needs what it sent (audit, retry)."""
    originais = {"n": "42", "extra": 1}
    inputs, _ = validate_inputs({"n": {"type": "number"}}, originais)

    assert originais == {"n": "42", "extra": 1}
    assert inputs == {"n": 42, "extra": 1}
