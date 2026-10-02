# tests/unit/test_definition_lint.py
"""Lint estático da definition (flow/utils/definition_lint.py).

Puro: registry e descriptors falsos, sem executor. O que se garante aqui é o
CONTRATO — código por problema, severidade, e o que cada mensagem precisa
carregar para quem monta o fluxo por API conseguir corrigir sem adivinhar.
"""
from __future__ import annotations

import time

import pytest

from flow.utils.definition_lint import (
    CHAVES_SECRETAS,
    FATAIS,
    _CABECALHOS_SECRETOS,
    _TAMANHO_MAX_TEXTO,
    Diagnostico,
    _partes_jinja,
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

# Descriptor no molde do Switch: uma propriedade `object` e o `fallback_output`.
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


# ── Fatais: o que derrubaria o construtor do executor ────────────────────────

def test_nome_inexistente_e_fatal_com_a_mensagem_da_factory():
    rel = _lint([_n("n1", name="NaoExiste")])

    assert _codes(rel.errors) == ["unknown_node"]
    assert rel.fatal
    # A frase da factory à letra: é o que scripts/validar.py procura.
    assert "não encontrado para instância" in rel.errors[0].message
    assert "NaoExiste" in rel.errors[0].message and "n1" in rel.errors[0].message
    assert rel.errors[0].node_id == "n1"


def test_unknown_node_fora_da_ordem_de_execucao_nao_e_fatal():
    """O NodeManager só instancia os nós da ordem: um nome inexistente solto
    (ou fora do cone do trigger) continua ERRO, mas não derruba o construtor."""
    rel = _lint(
        [_n("t", name="T", ntype="trigger"), _n("m"), _n("x", name="NaoExiste")],
        [{"source": "t", "target": "m"}],
    )

    assert _codes(rel.errors) == ["unknown_node"]
    assert rel.errors[0].severity == "error"
    assert rel.fatal is False
    assert [d.node_id for d in rel.warnings if d.code == "unreachable_node"] == ["x"]
    assert rel.execution_order == ["t", "m"]


def test_unknown_node_ligado_no_fluxo_e_fatal():
    rel = _lint(
        [_n("t", name="T", ntype="trigger"), _n("x", name="NaoExiste")],
        [{"source": "t", "target": "x"}],
    )

    assert _codes(rel.errors) == ["unknown_node"]
    assert rel.fatal is True


def test_id_duplicado_e_fatal():
    rel = _lint([_n("x"), _n("x"), _n("y")])

    dup = [d for d in rel.errors if d.code == "duplicate_node_id"]
    assert len(dup) == 1 and dup[0].node_id == "x"
    assert "2 vezes" in dup[0].message
    assert rel.fatal


def test_ciclo_e_fatal():
    rel = _lint([_n("a"), _n("b")],
                [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}])

    assert _codes(rel.errors) == ["cycle"]
    assert "Ciclo detectado" in rel.errors[0].message
    assert rel.fatal
    assert rel.execution_order == []


def test_relatorio_sem_fatal_nao_e_fatal():
    rel = _lint([_n("a"), _n("b")], [{"source": "a", "target": "ghost"}])

    assert rel.errors == []
    assert not rel.fatal
    assert FATAIS == {
        "unknown_node", "duplicate_node_id", "cycle", "construction_error", "invalid_credential_id",
    }


def test_construction_error_registrado_pelo_chamador_e_fatal():
    rel = _lint([_n("a")])
    d = rel.erro("construction_error", "nó recusou o construtor")

    assert d.fatal is True and rel.fatal is True
    assert "fatal" not in d.as_dict()


# ── Grafo ────────────────────────────────────────────────────────────────────

def test_aresta_orfa_e_aviso_com_a_aresta_no_diagnostico():
    rel = _lint([_n("a"), _n("b")],
                [{"source": "a", "target": "b"}, {"source": "a", "target": "ghost"}])

    assert rel.errors == []
    orfas = [d for d in rel.warnings if d.code == "orphan_edge"]
    assert len(orfas) == 1
    assert orfas[0].edge == {"source": "a", "target": "ghost"}
    assert orfas[0].node_id is None
    assert "target 'ghost'" in orfas[0].message


def test_no_isolado_e_no_fora_do_cone_do_trigger_sao_avisos_distintos():
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


def test_sem_arestas_nenhum_no_e_inalcancavel():
    rel = _lint([_n("a"), _n("b")])

    assert rel.errors == [] and rel.warnings == []
    assert set(rel.execution_order) == {"a", "b"}


def test_aresta_sem_as_duas_pontas_e_ignorada():
    rel = _lint([_n("a")], [{"source": "a"}])

    assert rel.errors == [] and rel.warnings == []


# ── Alias ────────────────────────────────────────────────────────────────────

def test_alias_invalido_reservado_e_duplicado_explicito():
    rel = _lint([
        _n("n1", alias="Caixa Delimitadora"),
        _n("n2", alias="inputs"),
        _n("n3", alias="Caixa"),
        _n("n4", alias="Caixa"),
    ])

    assert sorted(_codes(rel.errors)) == ["duplicate_alias", "invalid_alias", "reserved_alias"]
    por_codigo = {d.code: d for d in rel.errors}
    assert por_codigo["invalid_alias"].node_id == "n1"
    assert por_codigo["reserved_alias"].node_id == "n2"
    assert por_codigo["duplicate_alias"].node_id == "n3"
    assert "n3" in por_codigo["duplicate_alias"].message
    assert "n4" in por_codigo["duplicate_alias"].message
    assert not rel.fatal


def test_alias_em_properties_tambem_e_lido():
    node = {"id": "n1", "name": "A", "type": "action", "properties": {"alias": "now"}}

    rel = _lint([node])

    assert _codes(rel.errors) == ["reserved_alias"]


def test_dois_nos_do_mesmo_tipo_sem_alias_nao_acusam_nada():
    rel = _lint([_n("n1"), _n("n2")])

    assert rel.errors == [] and rel.warnings == []


@pytest.mark.parametrize("texto", [
    "{{ $A.x }}",
    "$A.x",
    "{{ A.x }}",
    "{% if A.x > 1 %}s{% endif %}",
    "{{ named.A.x }}",
    "{{ named['A'].x }}",
    # Sem `.` depois: o alias inteiro também é referência.
    "{{ A }}",
    "{{ A['x'] }}",
    "{{ A | tojson }}",
    "{% for r in A %}{{ r }}{% endfor %}",
])
def test_alias_derivado_do_name_avisa_so_quando_referenciado(texto):
    rel = _lint([_n("n1"), _n("n2", url=texto)])

    assert rel.errors == []
    assert _codes(rel.warnings) == ["duplicate_alias"]
    assert rel.warnings[0].node_id == "n1"
    assert "n1" in rel.warnings[0].message and "n2" in rel.warnings[0].message


@pytest.mark.parametrize("texto", [
    "{{ inputs.A.x }} $AB.x",   # `inputs.A` e `$AB` não são o alias `A`
    "{{ named.A2 }}",
    "A.x fora de bloco",         # sem `$` e fora de Jinja é texto comum
])
def test_referencia_a_outro_nome_nao_confunde_com_o_alias(texto):
    rel = _lint([_n("n1"), _n("n2", url=texto)])

    assert rel.warnings == []


# ── Segredos e credenciais ───────────────────────────────────────────────────

def test_segredo_na_definicao_e_erro_sem_ecoar_o_valor():
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


def test_expressao_pura_e_vazio_nao_sao_segredo():
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
def test_esquema_de_autenticacao_mais_expressao_nao_e_segredo(valor):
    """Só o esquema ("Bearer") fica gravado; o valor vem de expressão."""
    rel = _lint([_n("n1", headers={"Authorization": valor}, token=valor)])

    assert rel.errors == []


def test_http_auth_so_com_type_nao_e_segredo():
    # `type` é seletor do formulário, não segredo.
    assert _lint([_n("n1", http_auth={"type": "http_bearer"})]).errors == []


@pytest.mark.parametrize("valor", [
    "Bearer abc123",  # pragma: allowlist secret
    "Basic abc123",  # pragma: allowlist secret
    "abc {{ $Cred.x }} def",
    "Bearer {{ $Cred.token }} extra",
])
def test_literal_ao_lado_do_esquema_continua_segredo(valor):
    rel = _lint([_n("n1", headers={"Authorization": valor})])

    assert _codes(rel.errors) == ["secret_in_definition"]


def test_http_auth_com_token_continua_segredo():
    rel = _lint([_n("n1", http_auth={"type": "http_bearer", "token": "abc"})])  # pragma: allowlist secret

    assert _codes(rel.errors) == ["secret_in_definition"]


@pytest.mark.parametrize("cabecalho", ["Cookie", "Proxy-Authorization"])
def test_cookie_e_proxy_authorization_gravados_sao_segredo(cabecalho):
    """Uma sessão em `Cookie` autentica tão bem quanto um `Authorization`, e
    `Proxy-Authorization` carrega a credencial do proxy. Sem os dois na lista o
    lint deixava passar e a definition saía com o valor em claro."""
    rel = _lint([_n("n1", headers={cabecalho: "sessao=abc123"})])  # pragma: allowlist secret

    assert _codes(rel.errors) == ["secret_in_definition"]
    assert f"headers.{cabecalho}" in rel.errors[0].message
    assert "abc123" not in rel.errors[0].message


def test_headers_como_json_serializado_tambem_e_lido():
    rel = _lint([_n("n1", headers='{"x-api-key": "k"}')])  # pragma: allowlist secret

    assert _codes(rel.errors) == ["secret_in_definition"]
    assert "headers.x-api-key" in rel.errors[0].message


def test_credential_id_que_nao_e_uuid_e_fatal():
    """Fatal por contrato: o id nunca chega ao banco, e quem só olha o status
    HTTP (o `validar.py` da skill) precisa reprovar como reprovava com o 403."""
    rel = _lint([_n("n1", credential_id="nao-e-uuid")])

    assert _codes(rel.errors) == ["invalid_credential_id"]
    assert rel.errors[0].node_id == "n1"
    assert rel.fatal and rel.errors[0].fatal


def test_credential_id_uuid_ou_vazio_passa():
    rel = _lint([
        _n("n1", credential_id="3f1d4c2e-9a7b-4c1d-8e2f-1a2b3c4d5e6f"),
        _n("n2", credential_id=""),
    ])

    assert rel.errors == []


# ── Propriedades (só com descriptors) ────────────────────────────────────────

def test_propriedade_nao_declarada_e_aviso_e_ignora_as_de_plataforma():
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


def test_sem_descriptors_nao_ha_check_de_propriedade():
    rel = _lint([_n("n1", foo=1, rules="{nao e json", fallback_output="")])

    assert rel.errors == [] and rel.warnings == []


def test_parametro_obrigatorio_ausente_e_aviso():
    descriptors = {"A": {"name": "A", "properties": [
        {"name": "query", "type": "string"},        # sem default = obrigatório
        {"name": "limite", "type": "integer", "default": 10},
    ]}}

    rel = _lint([_n("n1", limite=5)], descriptors=descriptors)

    assert _codes(rel.warnings) == ["missing_required_parameter"]
    assert "['query']" in rel.warnings[0].message
    assert rel.warnings[0].node_id == "n1"


def test_obrigatorio_presente_com_expressao_nao_avisa():
    descriptors = {"A": {"name": "A", "properties": [{"name": "query", "type": "string"}]}}

    rel = _lint([_n("n1", query="{{ inputs.q }}")], descriptors=descriptors)

    assert rel.warnings == []


@pytest.mark.parametrize("valor", ["{nao e json", '"texto"', "5", "null"])
def test_propriedade_object_ilegivel_e_erro(valor):
    """O run decodifica `object` em validate() e falha com esta frase."""
    rel = _lint([_n("n1", rules=valor)], descriptors=_DESC_SWITCH)

    assert _codes(rel.errors) == ["invalid_json_property"]
    assert "deve ser um objeto (dict) ou JSON válido" in rel.errors[0].message
    assert rel.errors[0].node_id == "n1"
    assert "nao e json" not in rel.errors[0].message  # valor não é ecoado
    assert not rel.fatal


@pytest.mark.parametrize("valor", [
    '[{"field": "x", "operator": "==", "value": 1, "output": "output_1"}]',
    '{"a": 1}',
    "",
    "   ",
    "{{ inputs.regras }}",
    '{"limite": {{ inputs.n }}}',   # só vira JSON válido depois de renderizar
    "$Regras.lista",
    [{"field": "x"}],
    {"a": 1},
])
def test_propriedade_object_valida_ou_com_template_nao_acusa(valor):
    rel = _lint([_n("n1", rules=valor)], descriptors=_DESC_SWITCH)

    assert rel.errors == []


def test_fallback_output_vazio_e_erro():
    """Erro, não aviso: nenhuma aresta nomeia a porta '' (`from_key` vazio é "sem
    chave"), então a fiação a partir dela está morta e o diagnóstico de aresta
    não a enxerga — como aviso, o relatório diria `ok: true`."""
    rel = _lint([_n("n1", fallback_output="")], descriptors=_DESC_SWITCH)

    assert _codes(rel.errors) == ["empty_fallback_output"]
    assert rel.warnings == []
    assert "porta ''" in rel.errors[0].message and "nenhuma aresta" in rel.errors[0].message
    assert rel.errors[0].node_id == "n1"
    assert not rel.fatal


def test_fallback_output_ausente_ou_preenchido_nao_avisa():
    assert _lint([_n("n1")], descriptors=_DESC_SWITCH).warnings == []
    assert _lint([_n("n1", fallback_output="resto")], descriptors=_DESC_SWITCH).warnings == []


# ── suggested_params_schema ──────────────────────────────────────────────────

def test_inputs_em_trigger_viram_parametros_sugeridos():
    rel = _lint([_n("t", name="T", ntype="trigger", url="{{ inputs.bbox }}")])

    assert rel.suggested_params_schema == {"bbox": {"type": "string", "required": True}}


def test_inputs_fora_de_trigger_nao_sao_parametros():
    # Em nó comum `inputs` são as arestas (core.py), não parâmetros do usuário.
    rel = _lint([_n("a", url="{{ inputs.bbox }}")])

    assert rel.suggested_params_schema == {}


def test_formas_de_referencia_a_inputs():
    rel = _lint([_n(
        "t", name="T", ntype="trigger",
        a="{{ inputs.um }}",
        b="{{ inputs['dois'].x }}",
        c='{% if inputs["tres"] %}s{% endif %}',
        d="$inputs.quatro/x",          # fora de bloco: o run não renderiza
        e="{{ $inputs.cinco }}",
        f={"aninhado": ["{{ inputs.seis }}"]},
        g="{{ nodes.inputs.nao }}",
    )])

    assert list(rel.suggested_params_schema) == ["um", "dois", "tres", "cinco", "seis"]


def test_cifrao_inputs_fora_de_bloco_nao_e_parametro():
    """`rendering._tem_expressao` só dispara `$X` quando X é alias de nó:
    `$inputs.x` solto chega cru ao nó, então não é parâmetro do fluxo."""
    rel = _lint([_n("t", name="T", ntype="trigger", url="https://api/$inputs.id")])

    assert rel.suggested_params_schema == {}


def test_ports_do_subworkflowinput_viram_parametros_sugeridos():
    rel = _lint([_n("in", name="SubWorkflowInput", ntype="trigger", ports=["geometry"])])

    assert rel.suggested_params_schema == {"geometry": {"type": "string", "required": True}}


# ── Custo linear: texto hostil não pode travar o event loop ──────────────────

def test_texto_patologico_nao_e_quadratico():
    """`re.split` com `(\\{\\{.*?\\}\\}|...)` levava 40 s em 100 KB de `{{`."""
    inicio = time.perf_counter()

    rel = lint_definition(
        [{"id": "a", "name": "T", "type": "trigger", "parameters": {"x": "{{" * 50000}}],
        [], registry_names={"T"},
    )

    assert time.perf_counter() - inicio < 2
    assert rel.suggested_params_schema == {}


def test_muitos_nos_com_nome_repetido_nao_e_quadratico():
    """A checagem de alias duplicado re-tokenizava TODAS as strings a cada grupo
    de nomes repetidos: 100 nós de 8 KB custavam segundos de CPU síncrona."""
    # 50 nomes, cada um em 2 nós sem alias próprio; só N7 é referenciado.
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
def test_referencia_ao_alias_derivado_nas_formas_que_o_runtime_resolve(texto):
    rel = _lint([_n("n1", url=texto), _n("n2")])

    assert _codes(rel.warnings) == ["duplicate_alias"]


@pytest.mark.parametrize("texto", [
    "$Ab", "{{ Ab }}", "{{ inputs.A }}", "{{ x.A }}", "A solto fora de jinja", "named.Ab",
])
def test_texto_que_nao_referencia_o_alias_nao_avisa(texto):
    rel = _lint([_n("n1", url=texto), _n("n2")])

    assert rel.warnings == []


def test_checagem_de_segredo_nao_tem_teto_e_continua_linear():
    inicio = time.perf_counter()

    rel = _lint([_n("n1", password="{{" * 50000)])

    assert time.perf_counter() - inicio < 2
    assert _codes(rel.errors) == ["secret_in_definition"]


def test_tokenizador_alterna_texto_e_bloco():
    assert _partes_jinja("a {{ b }} c {% d %} e") == ["a ", "{{ b }}", " c ", "{% d %}", " e"]
    assert _partes_jinja("sem jinja") == ["sem jinja"]
    assert _partes_jinja("") == [""]
    assert _partes_jinja("{{ a }}{{ b }}") == ["", "{{ a }}", "", "{{ b }}", ""]
    # Abertura sem fechamento: o resto é texto comum.
    assert _partes_jinja("{{ sem fim") == ["{{ sem fim"]
    assert _partes_jinja("{% a {{ b }}") == ["{% a {{ b }}"]
    assert _partes_jinja("x {{ a }} {{ sem fim") == ["x ", "{{ a }}", " {{ sem fim"]


def test_heuristicas_ignoram_strings_acima_do_teto():
    bloco = "{{ inputs.x }}"
    abaixo = bloco * (_TAMANHO_MAX_TEXTO // len(bloco) - 1)
    acima = bloco * (_TAMANHO_MAX_TEXTO // len(bloco) + 2)
    assert len(abaixo) <= _TAMANHO_MAX_TEXTO < len(acima)

    assert "x" in _lint([_n("t", name="T", ntype="trigger", a=abaixo)]).suggested_params_schema
    assert _lint([_n("t", name="T", ntype="trigger", a=acima)]).suggested_params_schema == {}

    # Alias derivado referenciado só dentro de uma string gigante: sem aviso.
    grande = "{{ $A.x }}" + " " * _TAMANHO_MAX_TEXTO
    assert _lint([_n("n1"), _n("n2", url=grande)]).warnings == []


# ── Contrato de saída ────────────────────────────────────────────────────────

def test_as_dict_tem_exatamente_as_cinco_chaves():
    d = Diagnostico("cycle", "error", "msg")

    assert d.as_dict() == {
        "code": "cycle", "severity": "error", "node_id": None, "edge": None, "message": "msg",
    }
    assert set(Diagnostico("x", "warning", "m", node_id="n", edge={"source": "a", "target": "b"})
               .as_dict()) == {"code", "severity", "node_id", "edge", "message"}


def test_nos_sem_id_ou_name_nao_estouram():
    rel = _lint([{"parameters": {"x": 1}}, {"id": "b"}], [{"source": "b", "target": "c"}])

    assert "unknown_node" in _codes(rel.errors)


def test_lint_nao_exige_descriptor_de_todo_no():
    # Descriptor só de "A": "T" fica sem checks de propriedade, sem estourar.
    rel = _lint([_n("t", name="T", ntype="trigger", foo=1), _n("a", foo=1)],
                [{"source": "t", "target": "a"}], descriptors=_DESCRIPTORS)

    assert [d.node_id for d in rel.warnings if d.code == "undeclared_property"] == ["t", "a"]


def test_cabecalhos_secretos_cobrem_os_de_credencial_do_http_request():
    """`_CABECALHOS_DE_CREDENCIAL` (flow/nodes/action/http_request.py) é a lista
    que o nó derruba ao seguir um 3xx para outra origem — a definição de
    "cabeçalho que carrega credencial" que já existe no repositório. O lint tem
    de cobri-la inteira: um cabeçalho que não pode atravessar um
    redirecionamento também não pode ficar GRAVADO na definição, e a redação
    (app/core/utils/redacao.py) importa esta lista. `cookie` e
    `proxy-authorization` faltavam, e `headers.Cookie` saía em claro.
    """
    from flow.nodes.action.http_request import _CABECALHOS_DE_CREDENCIAL

    assert _CABECALHOS_DE_CREDENCIAL <= _CABECALHOS_SECRETOS
    assert {"cookie", "proxy-authorization"} <= _CABECALHOS_SECRETOS
    # `x-api-key` só existe no lint: é chave gravada, não cabeçalho a derrubar.
    assert _CABECALHOS_SECRETOS - _CABECALHOS_DE_CREDENCIAL == {"x-api-key"}


def test_chaves_secretas_em_sincronia_com_a_factory():
    """A lista é copiada (importar a factory puxaria o registry inteiro para
    dentro de um módulo puro). Se alguém acrescentar uma chave lá, tem de
    acrescentar aqui — senão o lint deixa passar o que o log já redige."""
    from flow.factory import _PROPRIEDADES_SECRETAS

    assert CHAVES_SECRETAS == _PROPRIEDADES_SECRETAS
