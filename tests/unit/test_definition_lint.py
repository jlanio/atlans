# tests/unit/test_definition_lint.py
"""Static lint of the definition (flow/utils/definition_lint.py).

Pure: fake registry and descriptors, no executor. What is guaranteed here is the
CONTRACT — a code per problem, severity, and what each message needs to carry so
that whoever builds the workflow via API can fix it without guessing.
"""
from __future__ import annotations

import time

import pytest

from flow.utils.definition_lint import (
    SECRET_KEYS,
    FATAL_CODES,
    _SECRET_HEADERS,
    _MAX_TEXT_LENGTH,
    Diagnostic,
    _jinja_parts,
    lint_definition,
)

_REGISTRY = {"A", "T", "SubWorkflowInput"}

_DESCRIPTORS = {
    "A": {
        "name": "A", "type": "action",
        "properties": [
            {"name": "limite", "type": "integer", "default": 10},
            {"name": "url", "type": "string", "default": ""},
        ],
    },
    "T": {"name": "T", "type": "trigger", "properties": []},
    "SubWorkflowInput": {
        "name": "SubWorkflowInput", "type": "trigger",
        "properties": [{"name": "ports", "type": "object", "default": []}],
        "outputs_from_ports": True, "outputs": [],
    },
}

# Descriptor modeled on Switch: an `object` property and the `fallback_output`.
_DESC_SWITCH = {"A": {"name": "A", "properties": [
    {"name": "rules", "type": "object", "default": []},
    {"name": "fallback_output", "type": "string", "default": "output_0"},
]}}


def _n(nid, name="A", ntype="action", alias=None, **params):
    node = {"id": nid, "name": name, "type": ntype, "parameters": params}
    if alias is not None:
        node["alias"] = alias
    return node


def _lint(nodes, edges=(), **kw):
    kw.setdefault("registry_names", _REGISTRY)
    return lint_definition(list(nodes), list(edges), **kw)


def _codes(diags):
    return [d.code for d in diags]


# ── Fatal: what would bring down the executor's constructor ──────────────────

def test_unknown_name_is_fatal_with_the_factory_message():
    rel = _lint([_n("n1", name="NaoExiste")])

    assert _codes(rel.errors) == ["unknown_node"]
    assert rel.fatal
    # The factory's sentence verbatim: it is what scripts/validar.py looks for.
    assert "não encontrado para instância" in rel.errors[0].message
    assert "NaoExiste" in rel.errors[0].message and "n1" in rel.errors[0].message
    assert rel.errors[0].node_id == "n1"


def test_unknown_node_outside_execution_order_is_not_fatal():
    """NodeManager only instantiates the nodes in the order: a stray nonexistent
    name (or one outside the trigger's cone) is still an ERROR, but does not
    bring down the constructor."""
    rel = _lint(
        [_n("t", name="T", ntype="trigger"), _n("m"), _n("x", name="NaoExiste")],
        [{"source": "t", "target": "m"}],
    )

    assert _codes(rel.errors) == ["unknown_node"]
    assert rel.errors[0].severity == "error"
    assert rel.fatal is False
    assert [d.node_id for d in rel.warnings if d.code == "unreachable_node"] == ["x"]
    assert rel.execution_order == ["t", "m"]


def test_unknown_node_connected_in_the_workflow_is_fatal():
    rel = _lint(
        [_n("t", name="T", ntype="trigger"), _n("x", name="NaoExiste")],
        [{"source": "t", "target": "x"}],
    )

    assert _codes(rel.errors) == ["unknown_node"]
    assert rel.fatal is True


def test_duplicate_id_is_fatal():
    rel = _lint([_n("x"), _n("x"), _n("y")])

    dup = [d for d in rel.errors if d.code == "duplicate_node_id"]
    assert len(dup) == 1 and dup[0].node_id == "x"
    assert "2 vezes" in dup[0].message
    assert rel.fatal


def test_cycle_is_fatal():
    rel = _lint([_n("a"), _n("b")],
                [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}])

    assert _codes(rel.errors) == ["cycle"]
    assert "Ciclo detectado" in rel.errors[0].message
    assert rel.fatal
    assert rel.execution_order == []


def test_report_without_fatal_is_not_fatal():
    rel = _lint([_n("a"), _n("b")], [{"source": "a", "target": "ghost"}])

    assert rel.errors == []
    assert not rel.fatal
    assert FATAL_CODES == {
        "unknown_node", "duplicate_node_id", "cycle", "construction_error", "invalid_credential_id",
    }


def test_construction_error_registered_by_caller_is_fatal():
    rel = _lint([_n("a")])
    d = rel.erro("construction_error", "nó recusou o construtor")

    assert d.fatal is True and rel.fatal is True
    assert "fatal" not in d.as_dict()


# ── Grafo ────────────────────────────────────────────────────────────────────

def test_orphan_edge_is_warning_with_the_edge_in_the_diagnostic():
    rel = _lint([_n("a"), _n("b")],
                [{"source": "a", "target": "b"}, {"source": "a", "target": "ghost"}])

    assert rel.errors == []
    orphans = [d for d in rel.warnings if d.code == "orphan_edge"]
    assert len(orphans) == 1
    assert orphans[0].edge == {"source": "a", "target": "ghost"}
    assert orphans[0].node_id is None
    assert "target 'ghost'" in orphans[0].message


def test_isolated_node_and_node_outside_trigger_cone_are_distinct_warnings():
    rel = _lint(
        [_n("t", name="T", ntype="trigger"), _n("a"), _n("x"), _n("y"), _n("z")],
        [{"source": "t", "target": "a"}, {"source": "y", "target": "z"}],
    )

    assert rel.errors == []
    fora = {d.node_id: d.message for d in rel.warnings if d.code == "unreachable_node"}
    assert set(fora) == {"x", "y", "z"}
    assert "isolado" in fora["x"]
    assert "sem caminho a partir de um trigger" in fora["y"]
    assert "sem caminho a partir de um trigger" in fora["z"]
    assert fora["x"] != fora["y"]
    assert rel.execution_order == ["t", "a"]


def test_without_edges_no_node_is_unreachable():
    rel = _lint([_n("a"), _n("b")])

    assert rel.errors == [] and rel.warnings == []
    assert set(rel.execution_order) == {"a", "b"}


def test_edge_without_both_ends_is_ignored():
    rel = _lint([_n("a")], [{"source": "a"}])

    assert rel.errors == [] and rel.warnings == []


# ── Alias ────────────────────────────────────────────────────────────────────

def test_alias_invalid_reserved_and_explicit_duplicate():
    rel = _lint([
        _n("n1", alias="Caixa Delimitadora"),
        _n("n2", alias="inputs"),
        _n("n3", alias="Caixa"),
        _n("n4", alias="Caixa"),
    ])

    assert sorted(_codes(rel.errors)) == ["duplicate_alias", "invalid_alias", "reserved_alias"]
    by_code = {d.code: d for d in rel.errors}
    assert by_code["invalid_alias"].node_id == "n1"
    assert by_code["reserved_alias"].node_id == "n2"
    assert by_code["duplicate_alias"].node_id == "n3"
    assert "n3" in by_code["duplicate_alias"].message
    assert "n4" in by_code["duplicate_alias"].message
    assert not rel.fatal


def test_alias_in_properties_is_also_read():
    node = {"id": "n1", "name": "A", "type": "action", "properties": {"alias": "now"}}

    rel = _lint([node])

    assert _codes(rel.errors) == ["reserved_alias"]


def test_two_nodes_of_the_same_type_without_alias_flag_nothing():
    rel = _lint([_n("n1"), _n("n2")])

    assert rel.errors == [] and rel.warnings == []


@pytest.mark.parametrize("texto", [
    "{{ $A.x }}",
    "$A.x",
    "{{ A.x }}",
    "{% if A.x > 1 %}s{% endif %}",
    "{{ named.A.x }}",
    "{{ named['A'].x }}",
    # No `.` after it: the whole alias is also a reference.
    "{{ A }}",
    "{{ A['x'] }}",
    "{{ A | tojson }}",
    "{% for r in A %}{{ r }}{% endfor %}",
])
def test_alias_derived_from_name_warns_only_when_referenced(texto):
    rel = _lint([_n("n1"), _n("n2", url=texto)])

    assert rel.errors == []
    assert _codes(rel.warnings) == ["duplicate_alias"]
    assert rel.warnings[0].node_id == "n1"
    assert "n1" in rel.warnings[0].message and "n2" in rel.warnings[0].message


@pytest.mark.parametrize("texto", [
    "{{ inputs.A.x }} $AB.x",   # `inputs.A` and `$AB` are not the alias `A`
    "{{ named.A2 }}",
    "A.x fora de bloco",         # without `$` and outside Jinja it is plain text
])
def test_reference_to_another_name_is_not_mistaken_for_the_alias(texto):
    rel = _lint([_n("n1"), _n("n2", url=texto)])

    assert rel.warnings == []


# ── Segredos e credenciais ───────────────────────────────────────────────────

def test_secret_in_definition_is_error_without_echoing_the_value():
    rel = _lint([_n(
        "n1",
        connectionString="postgres://u:senha@host/db",  # pragma: allowlist secret
        http_auth={"type": "http_bearer", "token": "abc"},  # pragma: allowlist secret
        headers={"Authorization": "Bearer x", "Accept": "json"},  # pragma: allowlist secret
    )])

    segredos = [d for d in rel.errors if d.code == "secret_in_definition"]
    assert len(segredos) == 3
    assert len(rel.errors) == 3
    chaves = sorted(d.message.split("'")[1] for d in segredos)
    assert chaves == ["connectionString", "headers.Authorization", "http_auth"]
    for d in segredos:
        assert "postgres://" not in d.message
        assert "abc" not in d.message
        assert "Bearer" not in d.message
        assert "credential_id" in d.message


def test_pure_expression_and_empty_are_not_secret():
    rel = _lint([_n(
        "n1",
        password="{{ $Cred.x }}",
        token="",
        secret=None,
        http_auth={},
        api_key="$Cred.chave",
        headers={"Authorization": "{{ inputs.tok }}", "X-Api-Key": ""},
    )])

    assert rel.errors == []


@pytest.mark.parametrize("valor", [
    "Bearer {{ $Cred.token }}",
    "Bearer $Cred.token",
    "Bearer {{ inputs.tok }}",
    "Basic {{ env.B64 }}",
    "Api-Key {{ $Cred.k }}",
    "bearer",
])
def test_auth_scheme_plus_expression_is_not_secret(valor):
    """Only the scheme ("Bearer") is stored; the value comes from an expression."""
    rel = _lint([_n("n1", headers={"Authorization": valor}, token=valor)])

    assert rel.errors == []


def test_http_auth_with_only_type_is_not_secret():
    # `type` is a form selector, not a secret.
    assert _lint([_n("n1", http_auth={"type": "http_bearer"})]).errors == []


@pytest.mark.parametrize("valor", [
    "Bearer abc123",  # pragma: allowlist secret
    "Basic abc123",  # pragma: allowlist secret
    "abc {{ $Cred.x }} def",
    "Bearer {{ $Cred.token }} extra",
])
def test_literal_next_to_the_scheme_stays_secret(valor):
    rel = _lint([_n("n1", headers={"Authorization": valor})])

    assert _codes(rel.errors) == ["secret_in_definition"]


def test_http_auth_with_token_stays_secret():
    rel = _lint([_n("n1", http_auth={"type": "http_bearer", "token": "abc"})])  # pragma: allowlist secret

    assert _codes(rel.errors) == ["secret_in_definition"]


@pytest.mark.parametrize("cabecalho", ["Cookie", "Proxy-Authorization"])
def test_stored_cookie_and_proxy_authorization_are_secret(cabecalho):
    """A session in `Cookie` authenticates just as well as an `Authorization`, and
    `Proxy-Authorization` carries the proxy's credential. Without both in the
    list the lint let them through and the definition went out with the value
    in the clear."""
    rel = _lint([_n("n1", headers={cabecalho: "sessao=abc123"})])  # pragma: allowlist secret

    assert _codes(rel.errors) == ["secret_in_definition"]
    assert f"headers.{cabecalho}" in rel.errors[0].message
    assert "abc123" not in rel.errors[0].message


def test_headers_as_serialized_json_are_also_read():
    rel = _lint([_n("n1", headers='{"x-api-key": "k"}')])  # pragma: allowlist secret

    assert _codes(rel.errors) == ["secret_in_definition"]
    assert "headers.x-api-key" in rel.errors[0].message


def test_credential_id_that_is_not_uuid_is_fatal():
    """Fatal by contract: the id never reaches the database, and whoever only looks
    at the HTTP status (the skill's `validar.py`) needs to fail it as it did
    with the 403."""
    rel = _lint([_n("n1", credential_id="nao-e-uuid")])

    assert _codes(rel.errors) == ["invalid_credential_id"]
    assert rel.errors[0].node_id == "n1"
    assert rel.fatal and rel.errors[0].fatal


def test_credential_id_uuid_or_empty_passes():
    rel = _lint([
        _n("n1", credential_id="3f1d4c2e-9a7b-4c1d-8e2f-1a2b3c4d5e6f"),
        _n("n2", credential_id=""),
    ])

    assert rel.errors == []


# ── Properties (only with descriptors) ───────────────────────────────────────

def test_undeclared_property_is_warning_and_platform_ones_are_ignored():
    rel = _lint(
        [_n("n1", foo=1, alias="Ok", retry_count=2, limite="{{ inputs.n }}")],
        descriptors=_DESCRIPTORS,
    )

    assert rel.errors == []
    assert _codes(rel.warnings) == ["undeclared_property"]
    msg = rel.warnings[0].message
    assert "['foo']" in msg
    assert "retry_count" not in msg.split("Declaradas")[0]
    assert rel.warnings[0].node_id == "n1"


def test_without_descriptors_there_is_no_property_check():
    rel = _lint([_n("n1", foo=1, rules="{nao e json", fallback_output="")])

    assert rel.errors == [] and rel.warnings == []


def test_missing_required_parameter_is_warning():
    descriptors = {"A": {"name": "A", "properties": [
        {"name": "query", "type": "string"},        # no default = required
        {"name": "limite", "type": "integer", "default": 10},
    ]}}

    rel = _lint([_n("n1", limite=5)], descriptors=descriptors)

    assert _codes(rel.warnings) == ["missing_required_parameter"]
    assert "['query']" in rel.warnings[0].message
    assert rel.warnings[0].node_id == "n1"


def test_required_present_with_expression_does_not_warn():
    descriptors = {"A": {"name": "A", "properties": [{"name": "query", "type": "string"}]}}

    rel = _lint([_n("n1", query="{{ inputs.q }}")], descriptors=descriptors)

    assert rel.warnings == []


@pytest.mark.parametrize("valor", ["{nao e json", '"texto"', "5", "null"])
def test_unreadable_object_property_is_error(valor):
    """The run decodes `object` in validate() and fails with this sentence."""
    rel = _lint([_n("n1", rules=valor)], descriptors=_DESC_SWITCH)

    assert _codes(rel.errors) == ["invalid_json_property"]
    assert "deve ser um objeto (dict) ou JSON válido" in rel.errors[0].message
    assert rel.errors[0].node_id == "n1"
    assert "nao e json" not in rel.errors[0].message  # the value is not echoed
    assert not rel.fatal


@pytest.mark.parametrize("valor", [
    '[{"field": "x", "operator": "==", "value": 1, "output": "output_1"}]',
    '{"a": 1}',
    "",
    "   ",
    "{{ inputs.regras }}",
    '{"limite": {{ inputs.n }}}',   # only becomes valid JSON after rendering
    "$Regras.lista",
    [{"field": "x"}],
    {"a": 1},
])
def test_valid_or_templated_object_property_is_not_flagged(valor):
    rel = _lint([_n("n1", rules=valor)], descriptors=_DESC_SWITCH)

    assert rel.errors == []


def test_empty_fallback_output_is_error():
    """An error, not a warning: no edge names the port '' (an empty `from_key` means
    "no key"), so the wiring out of it is dead and the edge diagnostics do not
    see it — as a warning, the report would say `ok: true`."""
    rel = _lint([_n("n1", fallback_output="")], descriptors=_DESC_SWITCH)

    assert _codes(rel.errors) == ["empty_fallback_output"]
    assert rel.warnings == []
    assert "porta ''" in rel.errors[0].message and "nenhuma aresta" in rel.errors[0].message
    assert rel.errors[0].node_id == "n1"
    assert not rel.fatal


def test_fallback_output_missing_or_filled_does_not_warn():
    assert _lint([_n("n1")], descriptors=_DESC_SWITCH).warnings == []
    assert _lint([_n("n1", fallback_output="resto")], descriptors=_DESC_SWITCH).warnings == []


# ── suggested_params_schema ──────────────────────────────────────────────────

def test_inputs_in_trigger_become_suggested_parameters():
    rel = _lint([_n("t", name="T", ntype="trigger", url="{{ inputs.bbox }}")])

    assert rel.suggested_params_schema == {"bbox": {"type": "string", "required": True}}


def test_inputs_outside_trigger_are_not_parameters():
    # In a regular node `inputs` are the edges (core.py), not user parameters.
    rel = _lint([_n("a", url="{{ inputs.bbox }}")])

    assert rel.suggested_params_schema == {}


def test_forms_of_reference_to_inputs():
    rel = _lint([_n(
        "t", name="T", ntype="trigger",
        a="{{ inputs.um }}",
        b="{{ inputs['dois'].x }}",
        c='{% if inputs["tres"] %}s{% endif %}',
        d="$inputs.quatro/x",          # outside a block: the run does not render
        e="{{ $inputs.cinco }}",
        f={"aninhado": ["{{ inputs.seis }}"]},
        g="{{ nodes.inputs.nao }}",
    )])

    assert list(rel.suggested_params_schema) == ["um", "dois", "tres", "cinco", "seis"]


def test_dollar_inputs_outside_block_is_not_parameter():
    """`rendering._has_expression` only triggers on `$X` when X is a node alias:
    a stray `$inputs.x` reaches the node raw, so it is not a workflow parameter."""
    rel = _lint([_n("t", name="T", ntype="trigger", url="https://api/$inputs.id")])

    assert rel.suggested_params_schema == {}


def test_subworkflowinput_ports_become_suggested_parameters():
    rel = _lint([_n("in", name="SubWorkflowInput", ntype="trigger", ports=["geometry"])])

    assert rel.suggested_params_schema == {"geometry": {"type": "string", "required": True}}


# ── Linear cost: hostile text must not freeze the event loop ─────────────────

def test_pathological_text_is_not_quadratic():
    """`re.split` with `(\\{\\{.*?\\}\\}|...)` took 40 s on 100 KB of `{{`."""
    inicio = time.perf_counter()

    rel = lint_definition(
        [{"id": "a", "name": "T", "type": "trigger", "parameters": {"x": "{{" * 50000}}],
        [], registry_names={"T"},
    )

    assert time.perf_counter() - inicio < 2
    assert rel.suggested_params_schema == {}


def test_many_nodes_with_repeated_name_is_not_quadratic():
    """The duplicate-alias check re-tokenized ALL strings for each group of
    repeated names: 100 nodes of 8 KB cost seconds of synchronous CPU."""
    # 50 names, each in 2 nodes without their own alias; only N7 is referenced.
    nodes = [_n(f"n{i}", name=f"N{i % 50}", x="{{ a }}" * 1000) for i in range(100)]
    nodes[0]["parameters"]["ref"] = "{{ N7 | tojson }}"
    inicio = time.perf_counter()

    rel = _lint(nodes, registry_names={f"N{i}" for i in range(50)})

    assert time.perf_counter() - inicio < 2
    assert _codes(rel.warnings) == ["duplicate_alias"]
    assert "'N7'" in rel.warnings[0].message


@pytest.mark.parametrize("texto", [
    "$A", "$A.x", "named.A", "named['A']", 'named["A"]',
    "{{ A }}", "{{ A.x }}", "{{ A['x'] }}", "{{ A | tojson }}", "{% for r in A %}",
    "{{ $A.x }}", "{{ named.A }}",
])
def test_reference_to_derived_alias_in_the_forms_the_runtime_resolves(texto):
    rel = _lint([_n("n1", url=texto), _n("n2")])

    assert _codes(rel.warnings) == ["duplicate_alias"]


@pytest.mark.parametrize("texto", [
    "$Ab", "{{ Ab }}", "{{ inputs.A }}", "{{ x.A }}", "A solto fora de jinja", "named.Ab",
])
def test_text_not_referencing_the_alias_does_not_warn(texto):
    rel = _lint([_n("n1", url=texto), _n("n2")])

    assert rel.warnings == []


def test_secret_check_has_no_ceiling_and_stays_linear():
    inicio = time.perf_counter()

    rel = _lint([_n("n1", password="{{" * 50000)])

    assert time.perf_counter() - inicio < 2
    assert _codes(rel.errors) == ["secret_in_definition"]


def test_tokenizer_alternates_text_and_block():
    assert _jinja_parts("a {{ b }} c {% d %} e") == ["a ", "{{ b }}", " c ", "{% d %}", " e"]
    assert _jinja_parts("sem jinja") == ["sem jinja"]
    assert _jinja_parts("") == [""]
    assert _jinja_parts("{{ a }}{{ b }}") == ["", "{{ a }}", "", "{{ b }}", ""]
    # An opening without a closing: the rest is plain text.
    assert _jinja_parts("{{ sem fim") == ["{{ sem fim"]
    assert _jinja_parts("{% a {{ b }}") == ["{% a {{ b }}"]
    assert _jinja_parts("x {{ a }} {{ sem fim") == ["x ", "{{ a }}", " {{ sem fim"]


def test_heuristics_ignore_strings_above_the_ceiling():
    bloco = "{{ inputs.x }}"
    abaixo = bloco * (_MAX_TEXT_LENGTH // len(bloco) - 1)
    acima = bloco * (_MAX_TEXT_LENGTH // len(bloco) + 2)
    assert len(abaixo) <= _MAX_TEXT_LENGTH < len(acima)

    assert "x" in _lint([_n("t", name="T", ntype="trigger", a=abaixo)]).suggested_params_schema
    assert _lint([_n("t", name="T", ntype="trigger", a=acima)]).suggested_params_schema == {}

    # Derived alias referenced only inside a giant string: no warning.
    grande = "{{ $A.x }}" + " " * _MAX_TEXT_LENGTH
    assert _lint([_n("n1"), _n("n2", url=grande)]).warnings == []


# ── Output contract ──────────────────────────────────────────────────────────

def test_as_dict_has_exactly_the_five_keys():
    d = Diagnostic("cycle", "error", "msg")

    assert d.as_dict() == {
        "code": "cycle", "severity": "error", "node_id": None, "edge": None, "message": "msg",
    }
    assert set(Diagnostic("x", "warning", "m", node_id="n", edge={"source": "a", "target": "b"})
               .as_dict()) == {"code", "severity", "node_id", "edge", "message"}


def test_nodes_without_id_or_name_do_not_crash():
    rel = _lint([{"parameters": {"x": 1}}, {"id": "b"}], [{"source": "b", "target": "c"}])

    assert "unknown_node" in _codes(rel.errors)


def test_lint_does_not_require_a_descriptor_for_every_node():
    # Descriptor only for "A": "T" gets no property checks, without blowing up.
    rel = _lint([_n("t", name="T", ntype="trigger", foo=1), _n("a", foo=1)],
                [{"source": "t", "target": "a"}], descriptors=_DESCRIPTORS)

    assert [d.node_id for d in rel.warnings if d.code == "undeclared_property"] == ["t", "a"]


def test_secret_headers_cover_the_http_request_credential_ones():
    """`_CREDENTIAL_HEADERS` (flow/nodes/action/http_request.py) is the list
    the node drops when following a 3xx to another origin — the definition of
    "header that carries a credential" that already exists in the repository.
    The lint has to cover all of it: a header that cannot cross a redirect
    cannot stay STORED in the definition either, and the redaction
    (app/core/utils/redacao.py) imports this list. `cookie` and
    `proxy-authorization` were missing, and `headers.Cookie` went out in the clear.
    """
    from flow.nodes.action.http_request import _CREDENTIAL_HEADERS

    assert _CREDENTIAL_HEADERS <= _SECRET_HEADERS
    assert {"cookie", "proxy-authorization"} <= _SECRET_HEADERS
    # `x-api-key` only exists in the lint: it is a stored key, not a header to drop.
    assert _SECRET_HEADERS - _CREDENTIAL_HEADERS == {"x-api-key"}


def test_secret_keys_in_sync_with_the_factory():
    """The list is copied (importing the factory would pull the whole registry
    into a pure module). If someone adds a key there, they have to add it here
    too — otherwise the lint lets through what the log already redacts."""
    from flow.factory import _SECRET_PROPERTIES

    assert SECRET_KEYS == _SECRET_PROPERTIES
