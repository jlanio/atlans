# tests/unit/test_http_request_auth_retry.py
"""
Requisição HTTP — autenticação por credencial, repetição e redirecionamento.

Os três recursos compartilham a mesma característica: quando erram, erram EM
SILÊNCIO. Uma requisição sai anônima e volta 401 (que o usuário lê como "a API
está fora"), um POST repetido cobra o cliente duas vezes, um redirect seguido
sem revalidação vira SSRF. Nenhum deles falha de forma barulhenta, então os
testes cobrem exatamente as bordas onde o defeito passaria despercebido:

  AUTH        o segredo tem de sair da CREDENCIAL, nunca da definition — e
              vencer um `Authorization` escrito à mão, senão um header
              esquecido no formulário derruba a credencial escolhida.

  REPETIÇÃO   POST/PATCH JAMAIS repetem: a resposta pode ter se perdido na
              volta, com o efeito já aplicado no servidor.

  4xx         não repete (exceto 429) — repetir dá exatamente o mesmo erro e
              só gasta o tempo do run.

  REDIRECT    desligado por padrão; e ao seguir, 303 (e 301/302 sobre POST)
              tem de virar GET SEM CORPO, como faz todo cliente HTTP.
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
    """Mínimo de httpx.Response que o nó consome."""

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


# ── Autenticação ────────────────────────────────────────────────────────────

def test_bearer_monta_o_header():
    h = _aplicar_auth({}, {"type": "http_bearer", "token": "segredo"})
    assert h["Authorization"] == "Bearer segredo"


def test_basic_codifica_em_base64():
    h = _aplicar_auth({}, {"type": "http_basic", "username": "ana", "password": "senha"})
    # "ana:senha" em base64
    assert h["Authorization"] == "Basic YW5hOnNlbmhh"


def test_credencial_vence_authorization_escrito_a_mao():
    """Um header esquecido no formulário não pode derrubar a credencial."""
    h = _aplicar_auth(
        {"Authorization": "Bearer antigo-e-errado"},
        {"type": "http_bearer", "token": "novo"},
    )
    assert h["Authorization"] == "Bearer novo"


def test_sem_credencial_preserva_os_headers():
    h = _aplicar_auth({"X-Custom": "v"}, None)
    assert h == {"X-Custom": "v"}


def test_credencial_incompleta_falha_alto():
    """Token vazio sairia como 'Bearer ' e voltaria 401 — erro difícil de ler."""
    with pytest.raises(ValueError, match="token"):
        _aplicar_auth({}, {"type": "http_bearer", "token": "  "})


def test_credencial_de_outro_tipo_nao_sai_anonima():
    """O resolver injeta `http_auth` também para as credenciais do WFS; escolhida
    aqui, uma delas era ignorada e a requisição saía sem autenticação."""
    with pytest.raises(ValueError, match="não serve para requisição HTTP"):
        _aplicar_auth({}, {"type": "geoserver_authkey", "token": "k"})
    assert _aplicar_auth({"X": "1"}, {}) == {"X": "1"}  # sem credencial, nada muda


# ── Repetição ───────────────────────────────────────────────────────────────

def test_post_e_patch_nunca_repetem():
    """Repetir escrita não idempotente duplica o efeito no servidor."""
    assert "POST" not in _METODOS_REPETIVEIS
    assert "PATCH" not in _METODOS_REPETIVEIS
    assert {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"} <= _METODOS_REPETIVEIS


def test_repete_apenas_status_transitorios():
    assert 429 in _STATUS_REPETIVEIS          # sobrecarga: esperar ajuda
    assert 503 in _STATUS_REPETIVEIS
    assert 404 not in _STATUS_REPETIVEIS      # erro do pedido: repetir dá o mesmo
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
    """A configuração não pode vencer a regra de idempotência."""
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
    """Padrão seguro: o 3xx volta como resposta, sem virar proxy."""
    async def falsa(**kw):
        return RespostaFalsa(301, headers={"location": "https://outro.exemplo.com/y"})

    no = _no(method="GET")
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        r = asyncio.run(no.execute({}))

    assert r["status_code"] == 301


def test_segue_redirect_quando_ligado_e_revalida_cada_salto():
    """Cada salto passa de novo por safe_httpx_request — é o que mantém o SSRF fechado."""
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
    """Mandar o corpo adiante depois de um 303 quebra a API do outro lado."""
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


# ── Limite de resposta ──────────────────────────────────────────────────────

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


# ── Pelo execute(), e não pelo helper ───────────────────────────────────────
#
# Os testes de autenticação acima exercitam `_aplicar_auth` como função pura, e
# por isso passavam enquanto NENHUMA requisição autenticada funcionava: o
# `validate()` da primeira linha do `execute()` reconstrói `self.parameters` a
# partir das propriedades DECLARADAS e descarta o resto — e `http_auth`, que o
# servidor injeta, não estava declarada. O token era jogado fora antes de
# `_aplicar_auth` sequer ser chamado.
#
# A lição não é sobre HTTP: é sobre onde o teste toca. Um helper puro não prova
# que o valor chega até ele. Estes testes atravessam o `execute()` inteiro e
# olham o que sai no transporte.

def _capturar(**props):
    """Roda o nó com o transporte substituído e devolve os kwargs recebidos."""
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
    # dToA= é base64 de "u:p"
    assert recebido["headers"].get("Authorization") == "Basic dTpw"


def test_http_auth_e_declarado_no_schema():
    """Guarda direta da causa: se a propriedade sumir, o validate() volta a
    descartar o segredo e nenhum outro teste desta suíte percebe."""
    nomes = [p["name"] for p in HttpRequestNode.description()["properties"]]
    assert "http_auth" in nomes


# ── Query string ────────────────────────────────────────────────────────────
#
# `params` do httpx SUBSTITUI a query da URL em vez de somar a ela. Como o campo
# tem `{}` por padrão e o nó o entregava sempre, qualquer endereço colado pronto
# perdia a query — e endereço de WFS/OGC é quase só query.

def test_query_da_url_sobrevive_quando_o_campo_esta_vazio():
    recebido = _capturar(method="GET")
    # Sem nada a acrescentar, o nó não entrega `params` ao transporte, e a query
    # que veio na URL segue intacta.
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

    # A ocorrência que veio da URL sai — não se soma ao valor digitado.
    assert recebido["params"] == [("a", "docampo")]


# ── Chave repetida na query ─────────────────────────────────────────────────
#
# A query HTTP admite a mesma chave mais de uma vez, e em endereço geoespacial
# isso é rotina: `?bbox=..&bbox=..`, `?typeName=a&typeName=b`. A primeira versão
# desta junção passava por `dict(parse_qsl(...))`, que guarda só a última
# ocorrência — a URL saía do nó diferente da que o usuário colou, sem aviso.

def test_chave_repetida_na_url_sobrevive():
    recebido = _capturar(
        url="https://exemplo.org/wfs?bbox=1&bbox=2&service=WFS",
        method="GET",
    )
    assert recebido["params"] == [("bbox", "1"), ("bbox", "2"), ("service", "WFS")]


def test_chave_repetida_chega_intacta_ao_endereco_final():
    """Prova pelo httpx, não pela estrutura: é a URL montada que importa."""
    recebido = _capturar(
        url="https://exemplo.org/wfs?bbox=1&bbox=2",
        method="GET",
    )
    montada = httpx.Request("GET", "https://exemplo.org/wfs", params=recebido["params"]).url
    assert str(montada) == "https://exemplo.org/wfs?bbox=1&bbox=2"


# ── Redirecionamento ────────────────────────────────────────────────────────
#
# Quem escolhe o destino de um 3xx é o servidor remoto. Três coisas que o nó
# levava adiante e não devia.

def _seguir(url, location, **props):
    """Roda um GET que recebe um 3xx e devolve os kwargs de CADA salto."""
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
    """SEG: o token não pode ir para um host que o outro lado apontou."""
    saltos = _seguir(
        "https://confiavel.org/v1",
        "https://outro.example/coleta",
        http_auth={"type": "http_bearer", "token": "SEGREDO"},
    )
    assert saltos[0]["headers"]["Authorization"] == "Bearer SEGREDO"
    assert "Authorization" not in saltos[1]["headers"]


def test_credencial_segue_na_mesma_origem():
    """O caso comum `/api` → `/api/` não pode voltar 401 por falta de header."""
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
    """O caso do download assinado: a assinatura vem na query do `Location`."""
    saltos = _seguir(
        "https://portal.org/download?id=123",
        "https://cdn.portal.org/arq.zip?X-Amz-Signature=abc",
    )
    assert saltos[0]["params"] == [("id", "123")]
    # No salto o nó não entrega `params`, então a query do destino — que já está
    # na URL — é a que vale.
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


# ── Credencial que não resolve ──────────────────────────────────────────────
#
# O servidor REMOVE `credential_id` ao injetar a credencial resolvida. Chegar ao
# `execute()` com o id ainda presente e sem `http_auth` significa que a resolução
# falhou — credencial apagada, órfã, ou fora do escopo de quem disparou. Isso
# passava em silêncio e a requisição saía anônima.

def test_credencial_que_nao_resolve_nao_sai_anonima():
    chamou = []

    async def falsa(**kw):
        chamou.append(kw)
        return RespostaFalsa(401, json_data={"erro": "sem token"})

    no = _no(method="GET", credential_id="abc-123")
    with patch("flow.nodes.action.http_request.safe_httpx_request", side_effect=falsa):
        with pytest.raises(ValueError, match="não pôde ser resolvida"):
            asyncio.run(no.execute({}))

    # E a requisição não chegou a sair — não adianta falhar depois de o pedido
    # sem autenticação já ter batido no servidor.
    assert chamou == []


def test_sem_credencial_escolhida_a_requisicao_anonima_e_legitima():
    """API pública é o caso normal — a guarda não pode atrapalhá-lo."""
    recebido = _capturar(method="GET")
    assert "Authorization" not in recebido["headers"]


def test_credencial_resolvida_passa_pela_guarda():
    """No caminho feliz o servidor já removeu o `credential_id`."""
    recebido = _capturar(
        method="GET",
        http_auth={"type": "http_bearer", "token": "SEGREDO"},
    )
    assert recebido["headers"]["Authorization"] == "Bearer SEGREDO"


# ── O que NÃO deve ser repetido ─────────────────────────────────────────────
#
# Repetir um erro determinístico não custa só a espera: cada tentativa passa
# pelo disjuntor e conta uma falha, então uma URL recusada num nó abria o
# circuito do host e derrubava os pedidos legítimos dos outros fluxos.

# O disjuntor é um singleton POR HOST e sobrevive entre testes: quem provoca
# falha precisa de host próprio, senão abre o circuito para os testes seguintes.
# É o mesmo efeito que este conserto existe para evitar em produção.
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


# ── Caixa do cabeçalho ──────────────────────────────────────────────────────

def test_credencial_derruba_authorization_de_qualquer_caixa():
    """Header HTTP não distingue caixa; dicionário sim. Sem isso o nó enviava
    DOIS cabeçalhos de autenticação e o servidor escolhia qual valia."""
    recebido = _capturar(
        url="https://caixa.exemplo.com/x",
        method="GET",
        headers={"authorization": "Bearer ESCRITO-A-MAO"},
        http_auth={"type": "http_bearer", "token": "DA-CREDENCIAL"},
    )
    autenticacao = [k for k in recebido["headers"] if k.lower() == "authorization"]
    assert autenticacao == ["Authorization"]
    assert recebido["headers"]["Authorization"] == "Bearer DA-CREDENCIAL"
