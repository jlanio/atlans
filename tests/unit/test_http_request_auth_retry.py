# tests/unit/test_http_request_auth_retry.py
"""
HTTP request — credential authentication, retry and redirection.

The three features share the same trait: when they go wrong, they go wrong
SILENTLY. A request goes out anonymous and comes back 401 (which the user reads as "the API
is down"), a repeated POST charges the customer twice, a redirect followed
without revalidation becomes SSRF. None of them fails loudly, so the
tests cover exactly the edges where the defect would go unnoticed:

  AUTH        the secret must come from the CREDENTIAL, never from the definition — and
              win over a hand-written `Authorization`, otherwise a header
              forgotten in the form overrides the chosen credential.

  RETRY       POST/PATCH NEVER retry: the response may have been lost on the
              way back, with the effect already applied on the server.

  4xx         no retry (except 429) — retrying gives exactly the same error and
              only wastes the run's time.

  REDIRECT    off by default; and when following, 303 (and 301/302 on POST)
              must become a GET WITHOUT A BODY, as every HTTP client does.
"""
import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import flow.nodes.action.http_request as http_mod
from flow.nodes.action.http_request import (
    HttpRequestNode,
    _aplicar_auth,
    _METODOS_REPETIVEIS,
    _STATUS_REPETIVEIS,
)


class RespostaFalsa:
    """The minimum of httpx.Response that the node consumes."""

    def __init__(self, status_code=200, headers=None, json_data=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._json = json_data
        self.text = text

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308) and "location" in self.headers

    def json(self):
        if self._json is None:
            raise ValueError("sem json")
        return self._json


def _no(**props):
    return HttpRequestNode(node_id="n1", parameters={"url": "https://api.exemplo.com/x", **props})


# ── Authentication ──────────────────────────────────────────────────────────

def test_bearer_monta_o_header():
    h = _aplicar_auth({}, {"type": "http_bearer", "token": "segredo"})
    assert h["Authorization"] == "Bearer segredo"


def test_basic_codifica_em_base64():
    h = _aplicar_auth({}, {"type": "http_basic", "username": "ana", "password": "senha"})
    # "ana:senha" em base64
    assert h["Authorization"] == "Basic YW5hOnNlbmhh"


def test_credencial_vence_authorization_escrito_a_mao():
    """A header forgotten in the form must not override the credential."""
    h = _aplicar_auth(
        {"Authorization": "Bearer antigo-e-errado"},
        {"type": "http_bearer", "token": "novo"},
    )
    assert h["Authorization"] == "Bearer novo"


def test_sem_credencial_preserva_os_headers():
    h = _aplicar_auth({"X-Custom": "v"}, None)
    assert h == {"X-Custom": "v"}


def test_credencial_incompleta_falha_alto():
    """An empty token would go out as 'Bearer ' and come back 401 — an error hard to read."""
    with pytest.raises(ValueError, match="token"):
        _aplicar_auth({}, {"type": "http_bearer", "token": "  "})


def test_credencial_de_outro_tipo_nao_sai_anonima():
    """The resolver injects `http_auth` for WFS credentials too; when chosen
    here, one of them was ignored and the request went out without authentication."""
    with pytest.raises(ValueError, match="não serve para requisição HTTP"):
        _aplicar_auth({}, {"type": "geoserver_authkey", "token": "k"})
    assert _aplicar_auth({"X": "1"}, {}) == {"X": "1"}  # without a credential, nothing changes


# ── Retry ───────────────────────────────────────────────────────────────────

def test_post_e_patch_nunca_repetem():
    """Retrying a non-idempotent write duplicates the effect on the server."""
    assert "POST" not in _METODOS_REPETIVEIS
    assert "PATCH" not in _METODOS_REPETIVEIS
    assert {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"} <= _METODOS_REPETIVEIS


def test_repete_apenas_status_transitorios():
    assert 429 in _STATUS_REPETIVEIS          # sobrecarga: esperar ajuda
    assert 503 in _STATUS_REPETIVEIS
    assert 404 not in _STATUS_REPETIVEIS      # request error: retrying gives the same thing
    assert 401 not in _STATUS_REPETIVEIS


def test_get_repete_ate_obter_sucesso():
    respostas = [RespostaFalsa(503), RespostaFalsa(503), RespostaFalsa(200, json_data={"ok": True})]
    chamadas = []

    async def falsa(**kw):
        chamadas.append(kw["method"])
        return respostas[len(chamadas) - 1]

    no = _no(method="GET", retries=2)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa), \
         patch("flow.nodes.action.http_request.asyncio.sleep", new=AsyncMock()):
        r = asyncio.run(no.execute({}))

    assert len(chamadas) == 3
    assert r["status_code"] == 200


def test_post_nao_repete_mesmo_com_retries_configurado():
    """Configuration must not override the idempotency rule."""
    chamadas = []

    async def falsa(**kw):
        chamadas.append(kw["method"])
        return RespostaFalsa(503, text="indisponível")

    no = _no(method="POST", body='{"a":1}', retries=5)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa), \
         patch("flow.nodes.action.http_request.asyncio.sleep", new=AsyncMock()):
        r = asyncio.run(no.execute({}))

    assert len(chamadas) == 1
    assert r["status_code"] == 503


# ── Redirecionamento ────────────────────────────────────────────────────────

def test_nao_segue_redirect_por_padrao():
    """Safe default: the 3xx comes back as the response, without becoming a proxy."""
    async def falsa(**kw):
        return RespostaFalsa(301, headers={"location": "https://outro.exemplo.com/y"})

    no = _no(method="GET")
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        r = asyncio.run(no.execute({}))

    assert r["status_code"] == 301


def test_segue_redirect_quando_ligado_e_revalida_cada_salto():
    """Each hop goes through safe_httpx_request again — that is what keeps SSRF closed."""
    urls = []

    async def falsa(**kw):
        urls.append(kw["url"])
        if len(urls) == 1:
            return RespostaFalsa(302, headers={"location": "https://api.exemplo.com/final"})
        return RespostaFalsa(200, json_data={"ok": True})

    no = _no(method="GET", followRedirects=True)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        r = asyncio.run(no.execute({}))

    assert len(urls) == 2
    assert urls[1] == "https://api.exemplo.com/final"
    assert r["status_code"] == 200


def test_redirect_303_vira_get_sem_corpo():
    """Forwarding the body after a 303 breaks the API on the other side."""
    chamadas = []

    async def falsa(**kw):
        chamadas.append(kw)
        if len(chamadas) == 1:
            return RespostaFalsa(303, headers={"location": "/pronto"})
        return RespostaFalsa(200, json_data={"ok": True})

    no = _no(method="POST", body='{"a":1}', followRedirects=True)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        asyncio.run(no.execute({}))

    assert chamadas[0]["method"] == "POST"
    assert chamadas[1]["method"] == "GET"
    assert "json" not in chamadas[1] and "content" not in chamadas[1]


def test_estoura_limite_de_saltos():
    async def falsa(**kw):
        return RespostaFalsa(302, headers={"location": "https://api.exemplo.com/volta"})

    no = _no(method="GET", followRedirects=True, maxRedirects=2)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        with pytest.raises(RuntimeError, match="redirecionamentos"):
            asyncio.run(no.execute({}))


# ── Response limit ──────────────────────────────────────────────────────────

def test_limite_de_tamanho_chega_ao_transporte():
    recebido = {}

    async def falsa(**kw):
        recebido.update(kw)
        return RespostaFalsa(200, json_data={})

    no = _no(method="GET", maxResponseMb=8)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        asyncio.run(no.execute({}))

    assert recebido["max_response_bytes"] == 8 * 1024 * 1024


def test_zero_remove_o_limite():
    recebido = {}

    async def falsa(**kw):
        recebido.update(kw)
        return RespostaFalsa(200, json_data={})

    no = _no(method="GET", maxResponseMb=0)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        asyncio.run(no.execute({}))

    assert "max_response_bytes" not in recebido


# ── Through execute(), not through the helper ───────────────────────────────
#
# The authentication tests above exercise `_aplicar_auth` as a pure function, and
# that is why they passed while NO authenticated request worked: the
# `validate()` on the first line of `execute()` rebuilds `self.parameters` from
# the DECLARED properties and discards the rest — and `http_auth`, which the
# server injects, was not declared. The token was thrown away before
# `_aplicar_auth` was even called.
#
# The lesson is not about HTTP: it is about where the test touches. A pure helper does
# not prove that the value reaches it. These tests go through the whole `execute()` and
# look at what comes out on the transport.

def _capturar(**props):
    """Runs the node with the transport replaced and returns the kwargs received."""
    recebido = {}

    async def falsa(**kw):
        recebido.update(kw)
        return RespostaFalsa(200, json_data={"ok": True})

    no = _no(**props)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        asyncio.run(no.execute({}))
    return recebido


def test_credencial_sobrevive_ao_validate_e_chega_ao_transporte():
    recebido = _capturar(
        method="GET",
        http_auth={"type": "http_bearer", "token": "SEGREDO"},
    )
    assert recebido["headers"].get("Authorization") == "Bearer SEGREDO"


def test_credencial_basic_pelo_execute():
    recebido = _capturar(
        method="GET",
        http_auth={"type": "http_basic", "username": "u", "password": "p"},
    )
    # dToA= is base64 of "u:p"
    assert recebido["headers"].get("Authorization") == "Basic dTpw"


def test_http_auth_e_declarado_no_schema():
    """Direct guard on the cause: if the property disappears, validate() goes back to
    discarding the secret and no other test in this suite notices."""
    nomes = [p["name"] for p in HttpRequestNode.description()["properties"]]
    assert "http_auth" in nomes


# ── Query string ────────────────────────────────────────────────────────────
#
# httpx's `params` REPLACES the URL's query instead of adding to it. Since the field
# defaults to `{}` and the node always passed it, any ready-made pasted address
# lost its query — and a WFS/OGC address is almost all query.

def test_query_da_url_sobrevive_quando_o_campo_esta_vazio():
    recebido = _capturar(method="GET")
    # With nothing to add, the node does not pass `params` to the transport, and the query
    # that came in the URL stays intact.
    assert not recebido.get("params")


def test_query_da_url_e_somada_a_do_campo():
    no = HttpRequestNode(
        node_id="n1",
        parameters={
            "url": "https://exemplo.org/wfs?service=WFS&request=GetFeature",
            "method": "GET",
            "params": {"typeName": "municipios"},
        },
    )
    recebido = {}

    async def falsa(**kw):
        recebido.update(kw)
        return RespostaFalsa(200, json_data={})

    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        asyncio.run(no.execute({}))

    assert recebido["params"] == [
        ("service", "WFS"),
        ("request", "GetFeature"),
        ("typeName", "municipios"),
    ]


def test_campo_vence_a_url_na_chave_repetida():
    no = HttpRequestNode(
        node_id="n1",
        parameters={
            "url": "https://exemplo.org/x?a=daurl",
            "method": "GET",
            "params": {"a": "docampo"},
        },
    )
    recebido = {}

    async def falsa(**kw):
        recebido.update(kw)
        return RespostaFalsa(200, json_data={})

    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        asyncio.run(no.execute({}))

    # The occurrence that came from the URL goes — it does not add to the typed value.
    assert recebido["params"] == [("a", "docampo")]


# ── Repeated key in the query ───────────────────────────────────────────────
#
# An HTTP query allows the same key more than once, and in geospatial addresses
# that is routine: `?bbox=..&bbox=..`, `?typeName=a&typeName=b`. The first version
# of this merge went through `dict(parse_qsl(...))`, which keeps only the last
# occurrence — the URL left the node different from the one the user pasted, without warning.

def test_chave_repetida_na_url_sobrevive():
    recebido = _capturar(
        url="https://exemplo.org/wfs?bbox=1&bbox=2&service=WFS",
        method="GET",
    )
    assert recebido["params"] == [("bbox", "1"), ("bbox", "2"), ("service", "WFS")]


def test_chave_repetida_chega_intacta_ao_endereco_final():
    """Proof via httpx, not via the structure: it is the assembled URL that matters."""
    recebido = _capturar(
        url="https://exemplo.org/wfs?bbox=1&bbox=2",
        method="GET",
    )
    montada = httpx.Request("GET", "https://exemplo.org/wfs", params=recebido["params"]).url
    assert str(montada) == "https://exemplo.org/wfs?bbox=1&bbox=2"


# ── Redirection ─────────────────────────────────────────────────────────────
#
# Whoever picks the destination of a 3xx is the remote server. Three things the node
# carried along and should not have.

def _seguir(url, location, **props):
    """Runs a GET that receives a 3xx and returns the kwargs of EACH hop."""
    saltos = []

    async def falsa(**kw):
        saltos.append({**kw, "headers": dict(kw.get("headers") or {})})
        if len(saltos) == 1:
            return RespostaFalsa(302, headers={"location": location})
        return RespostaFalsa(200, json_data={"ok": True})

    no = _no(url=url, method="GET", followRedirects=True, maxRedirects=3, **props)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        asyncio.run(no.execute({}))
    return saltos


def test_credencial_nao_atravessa_mudanca_de_origem():
    """SEC: the token must not go to a host the other side pointed to."""
    saltos = _seguir(
        "https://confiavel.org/v1",
        "https://outro.example/coleta",
        http_auth={"type": "http_bearer", "token": "SEGREDO"},
    )
    assert saltos[0]["headers"]["Authorization"] == "Bearer SEGREDO"
    assert "Authorization" not in saltos[1]["headers"]


def test_credencial_segue_na_mesma_origem():
    """The common case `/api` → `/api/` must not come back 401 for lack of a header."""
    saltos = _seguir(
        "https://confiavel.org/api",
        "https://confiavel.org/api/",
        http_auth={"type": "http_bearer", "token": "SEGREDO"},
    )
    assert saltos[1]["headers"]["Authorization"] == "Bearer SEGREDO"


def test_cookie_tambem_cai_na_troca_de_origem():
    saltos = _seguir(
        "https://confiavel.org/x",
        "https://outro.example/y",
        headers={"Cookie": "sessao=abc"},
    )
    assert saltos[0]["headers"]["Cookie"] == "sessao=abc"
    assert "Cookie" not in saltos[1]["headers"]


def test_query_do_destino_nao_e_trocada_pela_da_origem():
    """The signed-download case: the signature comes in the `Location` query."""
    saltos = _seguir(
        "https://portal.org/download?id=123",
        "https://cdn.portal.org/arq.zip?X-Amz-Signature=abc",
    )
    assert saltos[0]["params"] == [("id", "123")]
    # On the hop the node does not pass `params`, so the destination's query — which is already
    # in the URL — is the one that counts.
    assert not saltos[1].get("params")
    assert saltos[1]["url"] == "https://cdn.portal.org/arq.zip?X-Amz-Signature=abc"


def test_disjuntor_do_salto_e_o_do_host_de_destino():
    consultados = []
    real = http_mod.get_circuit_breaker

    def espia(nome):
        consultados.append(nome)
        return real(nome)

    with patch.object(http_mod, "get_circuit_breaker", side_effect=espia):
        _seguir("https://a.example/x", "https://b.example/y")

    assert consultados == ["http:a.example", "http:b.example"]


# ── Credential that does not resolve ────────────────────────────────────────
#
# The server REMOVES `credential_id` when injecting the resolved credential. Reaching
# `execute()` with the id still present and without `http_auth` means resolution
# failed — credential deleted, orphaned, or outside the scope of whoever triggered. That
# went through silently and the request went out anonymous.

def test_credencial_que_nao_resolve_nao_sai_anonima():
    chamou = []

    async def falsa(**kw):
        chamou.append(kw)
        return RespostaFalsa(401, json_data={"erro": "sem token"})

    no = _no(method="GET", credential_id="abc-123")
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        with pytest.raises(ValueError, match="não pôde ser resolvida"):
            asyncio.run(no.execute({}))

    # And the request never went out — there is no point failing after the
    # unauthenticated request has already hit the server.
    assert chamou == []


def test_sem_credencial_escolhida_a_requisicao_anonima_e_legitima():
    """A public API is the normal case — the guard must not get in its way."""
    recebido = _capturar(method="GET")
    assert "Authorization" not in recebido["headers"]


def test_credencial_resolvida_passa_pela_guarda():
    """On the happy path the server has already removed `credential_id`."""
    recebido = _capturar(
        method="GET",
        http_auth={"type": "http_bearer", "token": "SEGREDO"},
    )
    assert recebido["headers"]["Authorization"] == "Bearer SEGREDO"


# ── What must NOT be retried ────────────────────────────────────────────────
#
# Retrying a deterministic error does not just cost the wait: every attempt goes
# through the circuit breaker and counts as a failure, so a URL refused in one node opened
# the host's circuit and brought down the legitimate requests of other workflows.

# The circuit breaker is a singleton PER HOST and survives between tests: whoever causes
# a failure needs their own host, otherwise it opens the circuit for the following tests.
# It is the same effect this fix exists to prevent in production.
@pytest.mark.parametrize("host,erro", [
    ("ssrf", ValueError("Requisições para endereços internos/privados não são permitidas.")),
    ("tamanho", ValueError("Resposta excedeu o limite de 1024 bytes.")),
    ("tls", RuntimeError("Não foi possível validar o certificado TLS de 'x'. Isso não é falha temporária")),
])
def test_erro_deterministico_nao_e_repetido(host, erro):
    tentativas = []

    async def falsa(**kw):
        tentativas.append(kw)
        raise erro

    no = _no(url=f"https://{host}.exemplo.com/x", method="GET", retries=3)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        with pytest.raises(Exception):
            asyncio.run(no.execute({}))

    assert len(tentativas) == 1


def test_erro_de_transporte_continua_sendo_repetido():
    tentativas = []

    async def falsa(**kw):
        tentativas.append(kw)
        if len(tentativas) < 3:
            raise httpx.ConnectError("conexão recusada")
        return RespostaFalsa(200, json_data={"ok": True})

    no = _no(url="https://transporte.exemplo.com/x", method="GET", retries=3)
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa), \
         patch("flow.nodes.action.http_request.asyncio.sleep", new=AsyncMock()):
        saida = asyncio.run(no.execute({}))

    assert len(tentativas) == 3
    assert saida["status_code"] == 200


# ── Header case ─────────────────────────────────────────────────────────────

def test_credencial_derruba_authorization_de_qualquer_caixa():
    """HTTP headers are case-insensitive; dictionaries are not. Without this the node sent
    TWO authentication headers and the server picked which one counted."""
    recebido = _capturar(
        url="https://caixa.exemplo.com/x",
        method="GET",
        headers={"authorization": "Bearer ESCRITO-A-MAO"},
        http_auth={"type": "http_bearer", "token": "DA-CREDENCIAL"},
    )
    autenticacao = [k for k in recebido["headers"] if k.lower() == "authorization"]
    assert autenticacao == ["Authorization"]
    assert recebido["headers"]["Authorization"] == "Bearer DA-CREDENCIAL"
