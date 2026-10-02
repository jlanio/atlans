# tests/unit/test_redacao.py
"""Redação recursiva da definition (app/core/utils/redacao.py) e o `scrub_text`.

O que se garante: segredo em qualquer nível de `properties`/`parameters` não
sai em claro, a entrada nunca é mutada, o resto da definition sai intacto, e
a detecção devolve CAMINHOS — a borda que recusa precisa dizer onde. A lista
de chaves é a do lint, sem cópia: uma chave nova lá vale aqui.
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

# Segredos montados em runtime, para o scanner de segredos não acusar o teste.
PAT = "atl_pat_" + "Ab3dEf7gH1jK2lM4nO5pQ6rS8tU9vW0xY_Z-abcdefg"  # pragma: allowlist secret
SENHA = "s3nh" + "a-do-banco"
DSN = f"postgresql://usuario:{SENHA}@db.interno:5432/atlans"
CIFRADO = "gAAAA" + "Bfakecipher" * 4
BEARER = "Bearer " + "tok" * 12

# Os quatro formatos de DSN que o padrão do `scrub_text` precisa cobrir:
# usuário vazio (a forma canônica de REDIS_URL/AMQP_URL), "@" dentro da senha
# e driver no esquema (`postgresql+asyncpg`).
SENHA_REDIS = "supersegre" + "do"  # pragma: allowlist secret
SENHA_AMQP = "pa" + "ss"  # pragma: allowlist secret
SENHA_COM_ARROBA = "p@" + "ss"  # pragma: allowlist secret
SENHA_ASYNCPG = "s3n" + "h4"  # pragma: allowlist secret
DSN_REDIS = f"redis://:{SENHA_REDIS}@redis:6379/0"
DSN_AMQP = f"amqp://:{SENHA_AMQP}@rabbit/"
DSN_ARROBA = f"postgresql://user:{SENHA_COM_ARROBA}@host/db"
DSN_ASYNCPG = f"postgresql+asyncpg://u:{SENHA_ASYNCPG}@db:5432/x"

# Valor que NENHUM padrão do `scrub_text` reconhece: quem o apaga é a chave
# (`token`), e só se a string serializada for lida como estrutura.
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
    """O editor às vezes grava `headers` como string JSON; o segredo tem de
    sumir do mesmo jeito, e o valor continua sendo JSON válido."""
    d = _definition(_no("n0", {"headers": json.dumps({"x-api-key": "k" * 30, "Accept": "*/*"})}))
    headers = json.loads(redigir_definition(d)["nodes"][0]["properties"]["headers"])
    assert headers == {"x-api-key": "<REDACTED>", "Accept": "*/*"}


def test_redige_segredo_dentro_de_json_serializado_fora_de_headers():
    """`headers` não é a única propriedade que o editor grava serializada
    (`body`, `config`, `options` também). Um segredo dentro de uma string JSON
    não pode sair em claro só porque a propriedade tem outro nome."""
    assert scrub_text(SEGREDO_OPACO) == SEGREDO_OPACO  # o texto sozinho não o denuncia
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
    """A generalização não pode transformar em estrutura o que é texto: lista
    JSON, número e frase continuam string, e só passam pelo `scrub_text`."""
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
    """`parameters` é o formato do body de /validate — mesma regra."""
    d = _definition(_no("n0", {"password": "abc"}, container="parameters"))
    assert redigir_definition(d)["nodes"][0]["parameters"]["password"] == "<REDACTED>"


def test_redige_chave_sensivel_fora_de_properties_e_parameters():
    """A definition sai redigida INTEIRA, e não só os dois sacos de parâmetros.

    Um saco de configuração no topo, o `data` que o editor grava no nó e um
    `config` ao lado de `properties` saíam verbatim quando a descida começava
    nos contêineres: nem a chave sensível era trocada, nem o `scrub_text`
    chegava a correr sobre a string.
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
    # E o saco de parâmetros continua entregando o que não é segredo.
    assert saida["nodes"][0]["properties"]["url"] == "https://api.exemplo.com"
    inteiro = json.dumps(saida)
    assert SEGREDO_OPACO not in inteiro and SENHA not in inteiro


def test_saco_de_parametros_mantem_orcamento_de_profundidade_proprio():
    """Os níveis da definition (`nodes` → nó → `properties`) não entram no teto
    do saco de parâmetros: descontá-los apagaria propriedade legítima e funda
    só por ela estar dentro de um nó. 30 níveis cabem; a partir da raiz seriam
    33 e a subárvore inteira viraria marcador."""
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
    """A folha é uma chave NÃO sensível, com valor sem padrão de segredo: o
    único motivo para ela sumir da saída é o teto. Uma versão sem teto desceria
    até lá e devolveria o valor em claro — e não acusaria caminho nenhum,
    porque não há segredo a encontrar."""
    valor = {"x": "valor-sem-padrao"}
    for _ in range(40):
        valor = {"nivel": [valor]}
    d = _definition(_no("n0", {"raiz": valor}))

    saida = json.dumps(redigir_definition(d))
    assert "valor-sem-padrao" not in saida  # a subárvore além do teto é opaca
    assert "<REDACTED>" in saida  # e sai como marcador, não como {} ou None

    # Opaco = suspeito: a checagem acusa o caminho que não conseguiu inspecionar.
    caminhos = definition_contem_segredo(d)
    assert len(caminhos) == 1
    assert caminhos[0].startswith("nodes[0].properties.raiz.nivel[0]")
    assert ".x" not in caminhos[0]  # parou antes da folha, como se espera


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
    # não redige: é tamanho, não segurança
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
    """Mesmo caminho legível de um dict de verdade: a propriedade, depois a
    chave de dentro da string."""
    d = _definition(_no("n0", {"config": json.dumps({"token": SEGREDO_OPACO, "ok": 1})}))
    assert definition_contem_segredo(d) == ["nodes[0].properties.config.token"]


def test_contem_segredo_acusa_fora_de_properties_e_parameters():
    """A detecção não pode ser mais estreita que a redação: se a borda aceita
    um segredo em `nodes[].data` ou num saco no topo, passa a existir um lugar
    onde ele entra sem ninguém avisar. Os sacos de parâmetros vêm por último,
    porque entram na varredura por fora (orçamento de profundidade próprio)."""
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


# ── padrão de DSN: custo e formatos ──────────────────────────────────────────

def test_padrao_de_dsn_em_texto_longo_sem_esquema_e_linear():
    """O padrão corre sobre texto que o cliente controla, síncrono no handler.
    Sem os tetos do esquema e da senha, cada letra de um texto sem "://" abria
    uma varredura até o fim e 100 mil caracteres custavam dezenas de segundos.
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
    # gulosa até o último "@" antes de "/": sem isso sobraria a cauda "ss@host".
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
    """A porta depois do host, o "@" de um e-mail e um link comum não são
    credencial: redigir qualquer um deles cegaria o diagnóstico."""
    assert scrub_text(url) == url
    d = _definition(_no("n0", {"url": url}))
    assert definition_contem_segredo(d) == []
    assert redigir_definition(d)["nodes"][0]["properties"]["url"] == url


def test_scrub_redige_o_authkey_do_geoserver_na_url():
    texto = scrub_text("GET https://geo.x/geoserver/ows?authkey=c0ffee-abc-123&service=WFS")
    assert "c0ffee-abc-123" not in texto and "service=WFS" in texto


def test_scrub_redige_o_authkey_ja_codificado_inteiro():
    # A regra genérica parava no primeiro `%` e deixava o resto da chave.
    texto = scrub_text("GET https://geo.x/ows?service=WFS&authkey=a%2Bb%2Fc%3Dd%26e&request=GetFeature")
    assert "2Fc" not in texto and "authkey=<REDACTED>&request=GetFeature" in texto


def test_a_borda_recusa_a_chave_authkey_gravada_na_url():
    # No nó WFS a chave mora em Credenciais (`geoserver_authkey`), nunca na url.
    def definicao(url):
        return {"nodes": [{"id": "n1", "name": "WFS", "properties": {"url": url, "typeName": "ns:c"}}]}

    assert definition_contem_segredo(definicao("https://geo.x/ows?authkey=0f3c-44aa-99")) == ["nodes[0].properties.url"]
    # Expressão não é segredo salvo; e URL sem a chave segue valendo.
    assert definition_contem_segredo(definicao("https://geo.x/ows?authkey={{ $Cred.chave }}")) == []
    assert definition_contem_segredo(definicao("https://geo.x/ows?authkey=$Cred.chave")) == []
    assert definition_contem_segredo(definicao("https://geo.x/ows?service=WFS&request=GetCapabilities")) == []


def test_authkey_na_url_so_e_segredo_no_no_que_usa_essa_credencial():
    # Num HttpRequest (ou num rótulo) `authkey` é só uma palavra: a borda
    # recusava a definição inteira por ela.
    http = {"nodes": [{"id": "n1", "name": "HttpRequest", "properties": {
        "url": "https://api.x/v1/itens?authkey=0f3c-44aa-99",
        "label": "veja ?authkey=abcdef no manual",
    }}]}
    assert definition_contem_segredo(http) == []
    # O nó WFS no formato do editor (nome e propriedades em `data`) segue recusado.
    wfs = {"nodes": [{"id": "n1", "data": {"name": "WFS", "properties": {"url": "https://geo.x/ows?authkey=0f3c-44aa-99"}}}]}
    assert definition_contem_segredo(wfs) == ["nodes[0].data.properties.url"]
    # E `user:senha@` continua segredo em qualquer nó.
    assert definition_contem_segredo({"nodes": [{"id": "n1", "name": "HttpRequest", "properties": {"url": DSN}}]}) == [
        "nodes[0].properties.url",
    ]


def test_chave_sensivel_sem_nada_literal_sai_como_entrou_e_a_definition_lida_volta_a_ser_gravavel():
    # `http_auth: {}` é o padrão que o nó WFS declara: redigi-lo para
    # "<REDACTED>" fazia a borda recusar, na volta, a definition que ela mesma
    # tinha entregado (um "<REDACTED>" é um segredo "preenchido"). O mesmo
    # vale para o que só REFERENCIA um valor de runtime.
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
    "{{ inputs.token | default('hunter2') }}",   # literal escondido na expressão
    "{% set p = 'hunter2' %}{{ p }}",
    {"type": "http_bearer", "token": "{{ 'hunter2' }}"},
    1234,                                          # número sob chave sensível é literal
    "Bearer " + SEGREDO_OPACO,
])
def test_qualquer_literal_sob_chave_sensivel_some_inteiro_mesmo_dentro_de_jinja(valor):
    saida = redigir_definition(_definition(_no("n0", {"token": valor})))
    assert saida["nodes"][0]["properties"]["token"] == "<REDACTED>"


def test_o_marcador_redacted_e_recusado_em_qualquer_lugar_da_definition():
    # O que a entrega redige e a borda NÃO recusa no original (uma `?authkey=`
    # num HttpRequest, um Bearer num texto) voltaria como "<REDACTED>" numa
    # gravação ler → editar → gravar, apagando a chave em silêncio. O marcador
    # é nosso: só existe numa leitura redigida, e a borda o recusa onde estiver.
    bearer = "Bearer " + "tok" * 12
    original = _definition(
        _no("n0", {"url": "https://geo.x/geoserver/rest/layers?authkey=0f3c44aa99bb", "label": f"use {bearer} aqui"}),
        _no("n1", {"config": json.dumps({"nota": bearer})}),
    )
    assert definition_contem_segredo(original) == []  # HttpRequest: `authkey` é só uma palavra
    entregue = redigir_definition(original)
    assert "0f3c44aa99bb" not in json.dumps(entregue) and "tok" * 12 not in json.dumps(entregue)
    assert definition_contem_segredo(entregue) == [
        "nodes[0].properties.url",
        "nodes[0].properties.label",
        "nodes[1].properties.config.nota",
    ]
