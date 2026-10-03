# tests/unit/test_redacao.py
"""Recursive redaction of the definition (app/core/utils/redacao.py) and `scrub_text`.

What is guaranteed: a secret at any level of `properties`/`parameters` does not
go out in the clear, the input is never mutated, the rest of the definition goes
out intact, and detection returns PATHS — the edge that rejects needs to say
where. The key list is the lint's, with no copy: a new key there applies here.
"""
from __future__ import annotations

import copy
import json
import time

import pytest

from app.core.utils.logger import _scrub, scrub_text
from app.core.utils.redacao import (
    CHAVES_REDIGIDAS,
    compactar_definition,
    definition_contem_segredo,
    redigir_definition,
)
from flow.utils.definition_lint import _CABECALHOS_SECRETOS, CHAVES_SECRETAS

# Secrets assembled at runtime, so the secret scanner does not flag the test.
PAT = "atl_pat_" + "Ab3dEf7gH1jK2lM4nO5pQ6rS8tU9vW0xY_Z-abcdefg"  # pragma: allowlist secret
SENHA = "s3nh" + "a-do-banco"
DSN = f"postgresql://usuario:{SENHA}@db.interno:5432/atlans"
CIFRADO = "gAAAA" + "Bfakecipher" * 4
BEARER = "Bearer " + "tok" * 12

# The four DSN formats the `scrub_text` pattern must cover:
# empty user (the canonical form of REDIS_URL/AMQP_URL), "@" inside the password
# and driver in the scheme (`postgresql+asyncpg`).
SENHA_REDIS = "supersegre" + "do"  # pragma: allowlist secret
SENHA_AMQP = "pa" + "ss"  # pragma: allowlist secret
SENHA_COM_ARROBA = "p@" + "ss"  # pragma: allowlist secret
SENHA_ASYNCPG = "s3n" + "h4"  # pragma: allowlist secret
DSN_REDIS = f"redis://:{SENHA_REDIS}@redis:6379/0"
DSN_AMQP = f"amqp://:{SENHA_AMQP}@rabbit/"
DSN_ARROBA = f"postgresql://user:{SENHA_COM_ARROBA}@host/db"
DSN_ASYNCPG = f"postgresql+asyncpg://u:{SENHA_ASYNCPG}@db:5432/x"

# A value NO `scrub_text` pattern recognizes: what erases it is the key
# (`token`), and only if the serialized string is read as a structure.
SEGREDO_OPACO = "abc" + "123def456"  # pragma: allowlist secret


def _definition(*nodes, **topo):
    return {
        "nodes": list(nodes),
        "edges": [{"source": "n0", "target": "n1"}],
        "viewport": {"x": 10, "y": 20, "zoom": 1.5},
        **topo,
    }


def _no(nid, props, container="properties", **extra):
    return {"id": nid, "name": "HttpRequest", "type": "action",
            "position": {"x": 1, "y": 2}, "measured": {"width": 200, "height": 80},
            "selected": True, "dragging": False, container: props, **extra}


# ── chaves ───────────────────────────────────────────────────────────────────

def test_chaves_redigidas_sao_a_uniao_das_listas_do_lint():
    assert CHAVES_REDIGIDAS == CHAVES_SECRETAS | _CABECALHOS_SECRETOS
    assert {"connectionstring", "authorization", "x-api-key", "password"} <= CHAVES_REDIGIDAS


# ── redigir_definition ───────────────────────────────────────────────────────

def test_redige_cabecalho_aninhado_em_headers():
    d = _definition(_no("n0", {
        "url": "https://api.exemplo.com/v1",
        "headers": {"Authorization": BEARER, "X-Api-Key": "k" * 30, "Accept": "application/json"},
    }))
    saida = redigir_definition(d)
    headers = saida["nodes"][0]["properties"]["headers"]
    assert headers["Authorization"] == "<REDACTED>"
    assert headers["X-Api-Key"] == "<REDACTED>"
    assert headers["Accept"] == "application/json"
    assert saida["nodes"][0]["properties"]["url"] == "https://api.exemplo.com/v1"


def test_redige_headers_serializado_como_json_pelo_editor():
    """The editor sometimes stores `headers` as a JSON string; the secret must
    vanish all the same, and the value is still valid JSON."""
    d = _definition(_no("n0", {"headers": json.dumps({"x-api-key": "k" * 30, "Accept": "*/*"})}))
    headers = json.loads(redigir_definition(d)["nodes"][0]["properties"]["headers"])
    assert headers == {"x-api-key": "<REDACTED>", "Accept": "*/*"}


def test_redige_segredo_dentro_de_json_serializado_fora_de_headers():
    """`headers` is not the only property the editor stores serialized
    (`body`, `config`, `options` too). A secret inside a JSON string must not
    go out in the clear just because the property has another name."""
    assert scrub_text(SEGREDO_OPACO) == SEGREDO_OPACO  # the text alone does not give it away
    d = _definition(
        _no("n0", {"config": json.dumps({"token": SEGREDO_OPACO, "url": DSN, "timeout": 30})})
    )
    config = redigir_definition(d)["nodes"][0]["properties"]["config"]
    assert SEGREDO_OPACO not in config and SENHA not in config
    assert json.loads(config) == {
        "token": "<REDACTED>",
        "url": "postgresql://usuario:<REDACTED>@db.interno:5432/atlans",
        "timeout": 30,
    }


def test_string_que_nao_e_json_de_dict_segue_pelo_scrub_text():
    """The generalization must not turn text into structure: a JSON list,
    a number and a sentence stay strings, and only go through `scrub_text`."""
    d = _definition(_no("n0", {"lista": "[1, 2]", "numero": "30", "frase": f"falhou com {PAT}"}))
    props = redigir_definition(d)["nodes"][0]["properties"]
    assert props["lista"] == "[1, 2]"
    assert props["numero"] == "30"
    assert PAT not in props["frase"] and "<REDACTED>" in props["frase"]


def test_redige_senha_de_dsn_em_url_mantendo_o_host():
    d = _definition(_no("n0", {"url": DSN, "metodo": "GET"}))
    url = redigir_definition(d)["nodes"][0]["properties"]["url"]
    assert SENHA not in url
    assert url == "postgresql://usuario:<REDACTED>@db.interno:5432/atlans"


@pytest.mark.parametrize("valor", [CIFRADO, DSN], ids=["cifrado", "em_claro"])
def test_redige_connection_string_cifrado_ou_em_claro(valor):
    d = _definition(_no("n0", {"connectionString": valor, "query": "select 1"}))
    props = redigir_definition(d)["nodes"][0]["properties"]
    assert props["connectionString"] == "<REDACTED>"
    assert props["query"] == "select 1"


def test_redige_dentro_de_listas_de_dicts():
    d = _definition(_no("n0", {
        "rules": [
            {"field": "a", "token": "abc123"},
            {"field": "b", "valor": PAT},
            "texto solto",
        ],
    }))
    rules = redigir_definition(d)["nodes"][0]["properties"]["rules"]
    assert rules[0] == {"field": "a", "token": "<REDACTED>"}
    assert rules[1]["field"] == "b"
    assert PAT not in rules[1]["valor"]
    assert rules[2] == "texto solto"


def test_redige_tambem_em_parameters():
    """`parameters` is the format of the /validate body — same rule."""
    d = _definition(_no("n0", {"password": "abc"}, container="parameters"))
    assert redigir_definition(d)["nodes"][0]["parameters"]["password"] == "<REDACTED>"


def test_redige_chave_sensivel_fora_de_properties_e_parameters():
    """The WHOLE definition goes out redacted, not just the two parameter bags.

    A configuration bag at the top level, the `data` the editor stores on the node
    and a `config` next to `properties` went out verbatim when the descent started
    at the containers: neither was the sensitive key replaced, nor did
    `scrub_text` even run over the string.
    """
    d = _definition(
        _no(
            "n0", {"url": "https://api.exemplo.com"},
            data={"token": SEGREDO_OPACO},
            config={"headers": {"Authorization": BEARER}},
        ),
        settings={"connectionString": DSN, "timeout": 30},
        notas=f"falhou com {PAT}",
    )
    saida = redigir_definition(d)

    assert saida["settings"]["connectionString"] == "<REDACTED>"
    assert saida["settings"]["timeout"] == 30
    assert saida["nodes"][0]["data"]["token"] == "<REDACTED>"
    assert saida["nodes"][0]["config"]["headers"]["Authorization"] == "<REDACTED>"
    assert PAT not in saida["notas"] and "<REDACTED>" in saida["notas"]
    # And the parameter bag still delivers what is not secret.
    assert saida["nodes"][0]["properties"]["url"] == "https://api.exemplo.com"
    inteiro = json.dumps(saida)
    assert SEGREDO_OPACO not in inteiro and SENHA not in inteiro


def test_saco_de_parametros_mantem_orcamento_de_profundidade_proprio():
    """The definition's levels (`nodes` → node → `properties`) do not count toward
    the parameter bag's ceiling: subtracting them would erase a legitimate deep
    property just because it is inside a node. 30 levels fit; from the root it
    would be 33 and the whole subtree would become a marker."""
    valor = {"x": "valor-sem-padrao"}
    for _ in range(30):
        valor = {"nivel": valor}
    d = _definition(_no("n0", {"raiz": valor}))

    assert "valor-sem-padrao" in json.dumps(redigir_definition(d))


def test_chave_e_comparada_em_minusculas():
    d = _definition(_no("n0", {"ConnectionString": "x", "PASSWORD": "y", "Senha": "z"}))
    props = redigir_definition(d)["nodes"][0]["properties"]
    assert set(props.values()) == {"<REDACTED>"}


def test_profundidade_acima_do_teto_nao_estoura_nem_vaza():
    """The leaf is a NON-sensitive key, with a value matching no secret pattern: the
    only reason for it to vanish from the output is the ceiling. A version without
    a ceiling would descend all the way there and return the value in the clear —
    and would flag no path, because there is no secret to find."""
    valor = {"x": "valor-sem-padrao"}
    for _ in range(40):
        valor = {"nivel": [valor]}
    d = _definition(_no("n0", {"raiz": valor}))

    saida = json.dumps(redigir_definition(d))
    assert "valor-sem-padrao" not in saida  # the subtree beyond the ceiling is opaque
    assert "<REDACTED>" in saida  # and goes out as a marker, not as {} or None

    # Opaque = suspicious: the check flags the path it could not inspect.
    caminhos = definition_contem_segredo(d)
    assert len(caminhos) == 1
    assert caminhos[0].startswith("nodes[0].properties.raiz.nivel[0]")
    assert ".x" not in caminhos[0]  # stopped before the leaf, as expected


def test_nao_muta_a_entrada():
    d = _definition(_no("n0", {"connectionString": DSN, "headers": {"Authorization": BEARER},
                              "rules": [{"token": "abc"}]}))
    antes = copy.deepcopy(d)
    redigir_definition(d)
    compactar_definition(d)
    definition_contem_segredo(d)
    assert d == antes


def test_preserva_o_resto_e_tolera_definition_estranha():
    d = _definition(
        _no("n0", {"limite": 10, "ativo": True, "nada": None}),
        "nao-sou-dict",
        {"id": "n2", "name": "SemProps"},
        params_schema={"x": {"type": "string"}},
    )
    saida = redigir_definition(d)
    assert saida == d
    assert redigir_definition({"nodes": None}) == {"nodes": None}
    assert redigir_definition({}) == {}


# ── compactar_definition ─────────────────────────────────────────────────────

def test_compactar_tira_canvas_e_preserva_o_resto():
    d = _definition(_no("n0", {"connectionString": DSN}, alias="Banco"), "nao-sou-dict")
    saida = compactar_definition(d)
    assert "viewport" not in saida
    no = saida["nodes"][0]
    for chave in ("position", "measured", "selected", "dragging"):
        assert chave not in no
    assert no["id"] == "n0" and no["alias"] == "Banco"
    # does not redact: it is size, not security
    assert no["properties"]["connectionString"] == DSN
    assert saida["edges"] == d["edges"]
    assert saida["nodes"][1] == "nao-sou-dict"


# ── definition_contem_segredo ────────────────────────────────────────────────

def test_contem_segredo_devolve_caminhos():
    d = _definition(
        _no("n0", {"headers": {"Authorization": BEARER, "Accept": "*/*"}}),
        _no("n1", {"url": DSN}),
        _no("n2", {"connectionString": CIFRADO}),
        _no("n3", {"rules": [{"ok": 1}, {"token": "abc123"}]}),
    )
    assert definition_contem_segredo(d) == [
        "nodes[0].properties.headers.Authorization",
        "nodes[1].properties.url",
        "nodes[2].properties.connectionString",
        "nodes[3].properties.rules[1].token",
    ]


def test_contem_segredo_ignora_expressoes_vazios_e_esquema():
    d = _definition(_no("n0", {
        "headers": {"Authorization": "Bearer {{ inputs.tok }}"},
        "token": "{{ $Cred.token }}",
        "password": "",
        "connectionString": None,
        "url": "postgresql://{{ $Cred.user }}:{{ $Cred.senha }}@db/atlans",
        "http_auth": {"type": "http_bearer", "token": "$Cred.token"},
    }))
    assert definition_contem_segredo(d) == []


def test_contem_segredo_le_headers_serializado():
    d = _definition(_no("n0", {"headers": json.dumps({"Authorization": BEARER})}))
    assert definition_contem_segredo(d) == ["nodes[0].properties.headers.Authorization"]


def test_contem_segredo_desce_por_json_serializado_fora_de_headers():
    """Same readable path as a real dict: the property, then the key inside
    the string."""
    d = _definition(_no("n0", {"config": json.dumps({"token": SEGREDO_OPACO, "ok": 1})}))
    assert definition_contem_segredo(d) == ["nodes[0].properties.config.token"]


def test_contem_segredo_acusa_fora_de_properties_e_parameters():
    """Detection cannot be narrower than redaction: if the edge accepts a secret
    in `nodes[].data` or in a top-level bag, there is now a place where it gets
    in without anyone warning. The parameter bags come last, because they enter
    the scan separately (their own depth budget)."""
    d = _definition(
        _no("n0", {"connectionString": DSN}, data={"token": SEGREDO_OPACO}),
        settings={"url": DSN},
    )
    assert definition_contem_segredo(d) == [
        "nodes[0].data.token",
        "settings.url",
        "nodes[0].properties.connectionString",
    ]


def test_contem_segredo_com_definition_sem_nodes():
    assert definition_contem_segredo({}) == []
    assert definition_contem_segredo({"nodes": "x"}) == []


# ── scrub_text ───────────────────────────────────────────────────────────────

def test_scrub_text_e_publico_e_a_mesma_funcao_do_logger():
    assert scrub_text is _scrub
    saida = scrub_text(f"token novo {PAT} emitido")
    assert PAT not in saida and "<REDACTED>" in saida


@pytest.mark.parametrize("texto, esperado", [
    (DSN, "postgresql://usuario:<REDACTED>@db.interno:5432/atlans"),
    (f"falha ao conectar em {DSN}: timeout", "falha ao conectar em postgresql://usuario:<REDACTED>@db.interno:5432/atlans: timeout"),
    ("https://ana:seg" + "redo@api.exemplo.com/x", "https://ana:<REDACTED>@api.exemplo.com/x"),
    ("http://host:8080/caminho", "http://host:8080/caminho"),
    ("mailto:ana@exemplo.com", "mailto:ana@exemplo.com"),
    ("postgresql://usuario@db/atlans", "postgresql://usuario@db/atlans"),
])
def test_scrub_text_redige_credencial_de_url_e_deixa_url_comum(texto, esperado):
    assert scrub_text(texto) == esperado


# ── DSN pattern: cost and formats ────────────────────────────────────────────

def test_padrao_de_dsn_em_texto_longo_sem_esquema_e_linear():
    """The pattern runs over client-controlled text, synchronously in the handler.
    Without the scheme and password ceilings, each letter of a text without "://"
    opened a scan to the end and 100 thousand characters cost tens of seconds.
    """
    texto = "a-" * 50_000

    inicio = time.perf_counter()
    scrub_text(texto)
    assert time.perf_counter() - inicio < 0.5

    d = {"nodes": [{"id": "n", "properties": {"url": texto}}]}
    inicio = time.perf_counter()
    definition_contem_segredo(d)
    assert time.perf_counter() - inicio < 0.5


@pytest.mark.parametrize("texto, esperado", [
    (DSN_REDIS, "redis://:<REDACTED>@redis:6379/0"),
    (DSN_AMQP, "amqp://:<REDACTED>@rabbit/"),
    # greedy up to the last "@" before "/": without that the tail "ss@host" would be left.
    (DSN_ARROBA, "postgresql://user:<REDACTED>@host/db"),
    (DSN_ASYNCPG, "postgresql+asyncpg://u:<REDACTED>@db:5432/x"),
], ids=["redis_sem_usuario", "amqp_sem_usuario", "arroba_na_senha", "driver_no_esquema"])
def test_scrub_text_redige_dsn_em_todos_os_formatos(texto, esperado):
    assert scrub_text(texto) == esperado


@pytest.mark.parametrize("dsn, senha", [
    (DSN_REDIS, SENHA_REDIS),
    (DSN_AMQP, SENHA_AMQP),
    (DSN_ARROBA, SENHA_COM_ARROBA),
    (DSN_ASYNCPG, SENHA_ASYNCPG),
], ids=["redis_sem_usuario", "amqp_sem_usuario", "arroba_na_senha", "driver_no_esquema"])
def test_dsn_de_qualquer_formato_e_acusado_e_redigido_na_definition(dsn, senha):
    d = _definition(_no("n0", {"url": dsn}))
    assert definition_contem_segredo(d) == ["nodes[0].properties.url"]
    assert senha not in json.dumps(redigir_definition(d))


@pytest.mark.parametrize("url", [
    "https://host:8080/path?email=user@x.com",
    "mailto:user@exemplo.com",
    "https://atlans.example.org/share/abc",
], ids=["porta_e_email_no_query", "mailto", "link_de_compartilhamento"])
def test_url_sem_credencial_fica_intacta_e_nao_e_acusada(url):
    """The port after the host, the "@" of an e-mail and an ordinary link are not
    credentials: redacting any of them would blind the diagnosis."""
    assert scrub_text(url) == url
    d = _definition(_no("n0", {"url": url}))
    assert definition_contem_segredo(d) == []
    assert redigir_definition(d)["nodes"][0]["properties"]["url"] == url


def test_scrub_redige_o_authkey_do_geoserver_na_url():
    texto = scrub_text("GET https://geo.x/geoserver/ows?authkey=c0ffee-abc-123&service=WFS")
    assert "c0ffee-abc-123" not in texto and "service=WFS" in texto


def test_scrub_redige_o_authkey_ja_codificado_inteiro():
    # The generic rule stopped at the first `%` and left the rest of the key.
    texto = scrub_text("GET https://geo.x/ows?service=WFS&authkey=a%2Bb%2Fc%3Dd%26e&request=GetFeature")
    assert "2Fc" not in texto and "authkey=<REDACTED>&request=GetFeature" in texto


def test_a_borda_recusa_a_chave_authkey_gravada_na_url():
    # In the WFS node the key lives in Credentials (`geoserver_authkey`), never in the url.
    def definicao(url):
        return {"nodes": [{"id": "n1", "name": "WFS", "properties": {"url": url, "typeName": "ns:c"}}]}

    assert definition_contem_segredo(definicao("https://geo.x/ows?authkey=0f3c-44aa-99")) == ["nodes[0].properties.url"]
    # An expression is not a stored secret; and a URL without the key still holds.
    assert definition_contem_segredo(definicao("https://geo.x/ows?authkey={{ $Cred.chave }}")) == []
    assert definition_contem_segredo(definicao("https://geo.x/ows?authkey=$Cred.chave")) == []
    assert definition_contem_segredo(definicao("https://geo.x/ows?service=WFS&request=GetCapabilities")) == []


def test_authkey_na_url_so_e_segredo_no_no_que_usa_essa_credencial():
    # In an HttpRequest (or a label) `authkey` is just a word: the edge
    # rejected the whole definition because of it.
    http = {"nodes": [{"id": "n1", "name": "HttpRequest", "properties": {
        "url": "https://api.x/v1/itens?authkey=0f3c-44aa-99",
        "label": "veja ?authkey=abcdef no manual",
    }}]}
    assert definition_contem_segredo(http) == []
    # The WFS node in the editor's format (name and properties in `data`) is still rejected.
    wfs = {"nodes": [{"id": "n1", "data": {"name": "WFS", "properties": {"url": "https://geo.x/ows?authkey=0f3c-44aa-99"}}}]}
    assert definition_contem_segredo(wfs) == ["nodes[0].data.properties.url"]
    # And `user:senha@` is still a secret in any node.
    assert definition_contem_segredo({"nodes": [{"id": "n1", "name": "HttpRequest", "properties": {"url": DSN}}]}) == [
        "nodes[0].properties.url",
    ]


def test_chave_sensivel_sem_nada_literal_sai_como_entrou_e_a_definition_lida_volta_a_ser_gravavel():
    # `http_auth: {}` is the default the WFS node declares: redacting it to
    # "<REDACTED>" made the edge reject, on the way back, the definition it had
    # itself delivered (a "<REDACTED>" is a "filled-in" secret). The same goes
    # for anything that only REFERENCES a runtime value.
    props = {
        "http_auth": {}, "password": "", "token": None, "secret": "{{ inputs.segredo }}",
        "api_key": "$Cred.chave", "headers": {"Authorization": "Bearer {{ inputs.tok }}"},
        "url": "https://geo.x/ows",
    }
    saida = redigir_definition(_definition(_no("n0", props)))
    assert saida["nodes"][0]["properties"] == props
    assert definition_contem_segredo(saida) == []


@pytest.mark.parametrize("valor", [
    {"type": "geoserver_authkey", "token": SEGREDO_OPACO},
    "{{ inputs.token | default('hunter2') }}",   # literal hidden in the expression
    "{% set p = 'hunter2' %}{{ p }}",
    {"type": "http_bearer", "token": "{{ 'hunter2' }}"},
    1234,                                          # a number under a sensitive key is a literal
    "Bearer " + SEGREDO_OPACO,
])
def test_qualquer_literal_sob_chave_sensivel_some_inteiro_mesmo_dentro_de_jinja(valor):
    saida = redigir_definition(_definition(_no("n0", {"token": valor})))
    assert saida["nodes"][0]["properties"]["token"] == "<REDACTED>"


def test_o_marcador_redacted_e_recusado_em_qualquer_lugar_da_definition():
    # What the delivery redacts and the edge does NOT reject in the original (a
    # `?authkey=` in an HttpRequest, a Bearer in a text) would come back as
    # "<REDACTED>" in a read → edit → write round trip, silently erasing the key.
    # The marker is ours: it only exists in a redacted read, and the edge rejects
    # it wherever it is.
    bearer = "Bearer " + "tok" * 12
    original = _definition(
        _no("n0", {"url": "https://geo.x/geoserver/rest/layers?authkey=0f3c44aa99bb", "label": f"use {bearer} aqui"}),
        _no("n1", {"config": json.dumps({"nota": bearer})}),
    )
    assert definition_contem_segredo(original) == []  # HttpRequest: `authkey` is just a word
    entregue = redigir_definition(original)
    assert "0f3c44aa99bb" not in json.dumps(entregue) and "tok" * 12 not in json.dumps(entregue)
    assert definition_contem_segredo(entregue) == [
        "nodes[0].properties.url",
        "nodes[0].properties.label",
        "nodes[1].properties.config.nota",
    ]
