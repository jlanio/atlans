# flow/nodes/actions/http_request.py

import asyncio
import base64
import json
import httpx
import geopandas as gpd
from urllib.parse import parse_qsl, urlparse
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import gdf_para_geojson, safe_httpx_request
from flow.utils.circuit_breaker import get_circuit_breaker, CircuitOpenError
from flow.utils.backoff import espera_exponencial
from flow.utils.logger import get_logger
from typing import Any, Dict, List, Tuple

logger = get_logger(__name__)

# Retrying a POST/PATCH that already reached the server duplicates the effect —
# the response may have been lost on the way back, not on the way out. The
# others are idempotent by the protocol's definition.
_METODOS_REPETIVEIS = frozenset({'GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE'})

# Failures where retrying makes sense: the server said "I'm overloaded" or
# "try again". 4xx (except 429) is a request error — retrying gives the same error.
_STATUS_REPETIVEIS = frozenset({429, 500, 502, 503, 504})
# Ceiling on the wait between retries. With the maximum attempts the node
# offers, the wait doesn't come close, but the shared policy requires a
# declared ceiling — and a high `tentativas` configured on the canvas must not
# be able to hold the workflow for minutes.
_TETO_DE_ESPERA_S = 30.0


def _inteiro(valor: Any, padrao: int) -> int:
    """Number coming from the form, which arrives as a string when typed."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _juntar_query(url: str, params: Any) -> List[Tuple[str, str]]:
    """Merges the query already in the URL with the one from the `Parametros de query` field.

    httpx treats `params` as the whole query: handing it a dictionary
    REPLACES what came in the URL. Since the natural way to use the node is to
    paste the ready-made address from the portal — and a WFS/OGC address is
    almost all query —, the useful behavior is to add, not replace.

    Returns a LIST OF PAIRS, not a dictionary, because an HTTP query allows the
    same key repeated, and that is common precisely here: `?bbox=..&bbox=..`,
    `?typeName=a&typeName=b`. A `dict(parse_qsl(...))` keeps only the last
    occurrence and silences the others — the URL leaves the node different from
    the one the user pasted. httpx accepts the list of pairs and preserves the
    repetition.

    The field wins on a repeated key: whoever typed the pair explicitly is
    correcting what came in the URL — so the occurrences of that key that came
    from the URL are dropped, instead of being added to the typed value.
    """
    do_campo = [(str(k), str(v)) for k, v in (params or {}).items()]
    sobrescritas = {chave for chave, _ in do_campo}
    da_url = [
        (chave, valor)
        for chave, valor in parse_qsl(urlparse(url).query, keep_blank_values=True)
        if chave not in sobrescritas
    ]
    return da_url + do_campo


# Headers that carry a credential and must not cross a change of origin.
# It's the same list curl and requests drop when following a 3xx.
_CABECALHOS_DE_CREDENCIAL = frozenset({'authorization', 'cookie', 'proxy-authorization'})


def _mesma_origem(a: str, b: str) -> bool:
    """Compares origin in the RFC 6454 sense: scheme, host and effective port."""
    _PADRAO = {'http': 80, 'https': 443}
    def origem(u: str):
        p = urlparse(u)
        esquema = (p.scheme or '').lower()
        return (esquema, (p.hostname or '').lower(), p.port or _PADRAO.get(esquema))
    return origem(a) == origem(b)


def _sem_credenciais(headers: Dict[str, str]) -> Dict[str, str]:
    """Copy of the headers without the ones that carry a secret."""
    return {k: v for k, v in headers.items() if k.lower() not in _CABECALHOS_DE_CREDENCIAL}


def _aplicar_auth(headers: Dict[str, str], auth: Any) -> Dict[str, str]:
    """Builds the `Authorization` header from the resolved credential.

    The credential wins over an `Authorization` written by hand in the headers:
    whoever selected a credential expressed the stronger intent, and the
    opposite would let a header forgotten in the form silently drop the secret
    the user just chose.
    """
    if not isinstance(auth, dict):
        return headers

    tipo = auth.get('type')
    if not tipo:
        return headers
    if tipo not in ('http_bearer', 'http_basic'):
        # The resolver injects `http_auth` for WFS credentials too; one of
        # them chosen here would be ignored and the request would go out ANONYMOUS.
        raise ValueError(
            f"A credencial escolhida (tipo '{tipo}') não serve para requisição HTTP: "
            "use uma do tipo HTTP Bearer ou HTTP Basic."
        )

    # HTTP headers are case-insensitive, but dictionaries are not:
    # writing to `Authorization` left a hand-typed `authorization` standing
    # beside it, and the node sent TWO authentication headers — it's up to the
    # server to decide which one counts, and neither outcome is what the user asked for.
    for existente in [k for k in headers if k.lower() == 'authorization']:
        headers.pop(existente)

    if tipo == 'http_bearer':
        token = str(auth.get('token') or '').strip()
        if not token:
            raise ValueError(
                "A credencial Bearer selecionada não tem token preenchido."
            )
        headers['Authorization'] = f'Bearer {token}'
    elif tipo == 'http_basic':
        usuario = str(auth.get('username') or '')
        senha   = str(auth.get('password') or '')
        if not usuario:
            raise ValueError(
                "A credencial Basic selecionada não tem usuário preenchido."
            )
        par = base64.b64encode(f'{usuario}:{senha}'.encode('utf-8')).decode('ascii')
        headers['Authorization'] = f'Basic {par}'

    return headers


@register_node
class HttpRequestNode(BaseNode):
    """
    Performs asynchronous HTTP requests (GET, POST, PUT, PATCH, DELETE, etc.).
    - Protected against SSRF via validate_url_ssrf.
    - Protected by a per-host Circuit Breaker (5 failures → opens for 60 s).
    - If the method is POST/PUT/PATCH and 'body' is empty, uses the payload from inputs.
      Received GeoDataFrames are automatically converted to GeoJSON.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'HttpRequest',
            'alias': 'Requisição HTTP',
            'description': 'Executa requisições HTTP assíncronas com circuit breaker e proteção SSRF.',
            'type': 'action',
            # Optional: without a credential the request goes out anonymous, which
            # is the case for any public API. `requires_credential` would force
            # choosing one just for the node to validate.
            'properties': [
                {
                    'name': 'credential_id',
                    'label': 'Credencial',
                    'type': 'credential',
                    'credential_types': ['http_bearer', 'http_basic'],
                    'default': '',
                    'description': 'Opcional. Autenticação Bearer ou Basic. Preferir isto a escrever '
                                   'o token em "Cabeçalhos": o que vai nas propriedades é gravado na '
                                   'definição do workflow e no histórico de versões.'
                },
                {
                    # INJECTED by the server from `credential_id`, and
                    # declared here for a reason that is not cosmetic:
                    # `BaseNode.validate()` REBUILDS `self.parameters` from
                    # this list, and discards every key not in it (see
                    # the validate_node_parameters docstring). Without this entry,
                    # `http_auth` was resolved by the server, injected, and thrown
                    # away on the first line of `execute()` — every request with a
                    # credential went out ANONYMOUS, with the runtime itself printing
                    # "parametro(s) ['http_auth'] ... descartados" in a warning that
                    # nobody read.
                    #
                    # It's the same treatment `connectionString` already got in the
                    # database nodes. The UI hides it by name (node-config-form).
                    'name': 'http_auth',
                    'label': 'Autenticacao resolvida',
                    'type': 'object',
                    'default': {},
                    'description': 'Preenchida automaticamente a partir da credencial escolhida. '
                                   'Nao editavel: o segredo nunca e gravado na definicao do workflow.'
                },
                {
                    'name': 'url', 'required': True, 'placeholder': 'https://api.exemplo.com/dados',
                    'label': 'URL',
                    'type': 'string',
                    'default': '',
                    'description': 'URL para onde a requisição será enviada.'
                },
                {
                    'name': 'method',
                    'label': 'Método',
                    'type': 'select',
                    'default': 'GET',
                    'description': 'Método HTTP da requisição.',
                    'options': [
                        {'value': 'GET',     'label': 'GET'},
                        {'value': 'POST',    'label': 'POST'},
                        {'value': 'PUT',     'label': 'PUT'},
                        {'value': 'PATCH',   'label': 'PATCH'},
                        {'value': 'DELETE',  'label': 'DELETE'},
                        {'value': 'HEAD',    'label': 'HEAD'},
                        {'value': 'OPTIONS', 'label': 'OPTIONS'},
                    ],
                },
                {
                    'name': 'headers',
                    'label': 'Cabeçalhos',
                    # `keyvalue`, not `object`: a header is a flat two-column
                    # list, and the JSON tree editor demanded navigation and
                    # type selection for data you type from memory.
                    'type': 'keyvalue',
                    'default': {},
                    'description': 'Dicionário de headers a serem enviados.'
                },
                {
                    'name': 'params',
                    'label': 'Parâmetros de query',
                    'type': 'keyvalue',
                    'default': {},
                    'description': 'Parâmetros de query string (usado em GET/DELETE etc).'
                },
                {
                    'name': 'body',
                    'label': 'Corpo da requisição',
                    'type': 'string',
                    'default': '',
                    'description': 'Conteúdo bruto a ser enviado no corpo (POST/PUT/PATCH). '
                                   'Se vazio e método for POST/PUT/PATCH, usa payload de inputs como JSON.'
                },
                {
                    'name': 'timeout',
                    'label': 'Tempo limite (s)',
                    'type': 'number',
                    'default': 30,
                    'description': 'Tempo máximo de espera pela resposta (segundos).'
                },
                {
                    'name': 'followRedirects',
                    'label': 'Seguir redirecionamentos',
                    'type': 'boolean',
                    'default': False,
                    'description': 'Desligado por padrão: um 3xx apontando para endereço interno '
                                   'transformaria a plataforma em proxy. Cada salto é revalidado '
                                   'contra SSRF. Ligue se a API responde 301/302 (ex.: http→https).'
                },
                {
                    'name': 'maxRedirects',
                    'label': 'Máximo de saltos',
                    'type': 'number',
                    'default': 3,
                    'description': 'Quantos redirecionamentos seguir antes de desistir.',
                    # `in`, not `equals`: it's the only operator that
                    # `isFieldVisible` knows (see node-config-form).
                    'visibleWhen': {'field': 'followRedirects', 'in': [True]},
                },
                {
                    'name': 'maxResponseMb',
                    'label': 'Tamanho máximo da resposta (MB)',
                    'type': 'number',
                    'default': 32,
                    'description': 'Corta a leitura acima deste tamanho, em vez de carregar a '
                                   'resposta inteira na memória do executor. 0 remove o limite.'
                },
                {
                    'name': 'retries',
                    'label': 'Tentativas extras',
                    'type': 'number',
                    'default': 0,
                    'description': 'Repete em falha transitória (timeout, erro de rede, 429 e 5xx) '
                                   'com espera crescente. Só para métodos idempotentes — POST e '
                                   'PATCH nunca são repetidos, para não duplicar efeito.'
                },
            ],
            'outputs': [
                {'name': 'status_code', 'type': 'number', 'description': 'Código de status HTTP da resposta', 'port': True},
                {'name': 'headers', 'type': 'object', 'description': 'Cabeçalhos da resposta HTTP', 'port': True},
                {'name': 'body', 'type': 'any', 'description': 'Corpo da resposta (objeto JSON ou texto)', 'port': True},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        url     = self.parameters.get('url', '').strip()
        method  = self.parameters.get('method', 'GET').strip().upper()
        headers = dict(self.parameters.get('headers') or {})
        params  = self.parameters.get('params') or {}
        body    = self.parameters.get('body', '').strip()
        timeout = self.parameters.get('timeout', 30)

        seguir_redirect = bool(self.parameters.get('followRedirects', False))
        max_redirects   = _inteiro(self.parameters.get('maxRedirects'), 3)
        max_mb          = _inteiro(self.parameters.get('maxResponseMb'), 32)
        tentativas      = max(0, _inteiro(self.parameters.get('retries'), 0))

        # `http_auth` is injected by the server from the chosen credential
        # (see credential_resolver). The secret does NOT travel in the workflow
        # definition — that's why authenticating here is better than writing
        # the header by hand, which is stored in plain text in the database and in the history.
        headers = _aplicar_auth(headers, self.parameters.get('http_auth'))

        if not url:
            raise ValueError("Parâmetro 'url' é obrigatório para HttpRequest.")

        # The server REMOVES `credential_id` from the properties when injecting the
        # resolved credential (see credential_resolver.inject_credentials).
        # Arriving here with the id STILL present and without `http_auth` means
        # the resolution didn't happen — credential deleted, outside the scope of
        # whoever triggered it, or orphaned. Before, this went through silently: the
        # request went out ANONYMOUS, and since the node doesn't treat 4xx as a failure,
        # a 401 became normal output and the workflow went on with the error response
        # in place of the data.
        if self.parameters.get('credential_id') and not self.parameters.get('http_auth'):
            raise ValueError(
                "A credencial escolhida para este nó não pôde ser resolvida — ela pode "
                "ter sido apagada, não estar acessível a quem disparou a execução, ou ser "
                "de um tipo que este nó não usa (Bearer ou Basic). "
                "A requisição NÃO foi enviada, para não sair sem autenticação."
            )

        # httpx's `params` replaces the URL's ENTIRE query, it doesn't add to
        # it. Passing the empty dictionary — the field's default — erased the query
        # of any ready-made pasted address, and a WFS without
        # `?service=WFS&request=GetFeature` is not a WFS. Filling the field when the
        # URL already had a query had the same effect, only partial.
        #
        # The merge happens here, and not in the transport, because `safe_httpx_request`
        # also serves WFS and the webhook, which build the query on their own.
        params = _juntar_query(url, params)

        host    = urlparse(url).netloc or url
        breaker = get_circuit_breaker(f"http:{host}")

        logger.info("Preparando requisição HTTP: %s %s [circuit=%s]", method, url, breaker.state)

        # ── Builds kwargs for safe_httpx_request ─────────────────────────────
        # SEC (SSRF): we used to call validate_url_ssrf and DISCARD the
        # return value, letting httpx re-resolve DNS (TOCTOU / DNS rebinding).
        # safe_httpx_request validates AND pins the resolved IP, closing the window.
        request_kwargs: Dict[str, Any] = {
            'method':  method,
            'url':     url,
            'headers': headers,
            'timeout': timeout,
        }
        if max_mb > 0:
            request_kwargs['max_response_bytes'] = max_mb * 1024 * 1024

        if method in ('GET', 'DELETE', 'HEAD', 'OPTIONS'):
            # `if params`, as the POST/PUT/PATCH branch below already did: without
            # the guard, the empty dictionary reached httpx and wiped the query.
            if params:
                request_kwargs['params'] = params

        elif method in ('POST', 'PUT', 'PATCH'):
            if body:
                # explicit body: tries JSON, falls back to raw content
                try:
                    request_kwargs['json'] = json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    request_kwargs['content'] = body
                if params:
                    request_kwargs['params'] = params
            elif inputs:
                first_payload = next(iter(inputs.values()))
                if isinstance(first_payload, gpd.GeoDataFrame):
                    try:
                        request_kwargs['json'] = json.loads(gdf_para_geojson(first_payload, nat_como_nulo=True))
                    except Exception as e:
                        raise ValueError(f"Falha ao converter GeoDataFrame para GeoJSON: {e}")
                else:
                    request_kwargs['json'] = first_payload
                if params:
                    request_kwargs['params'] = params
            else:
                raise ValueError(
                    "Método POST/PUT/PATCH selecionado mas 'body' está vazio "
                    "e não há payload em inputs para enviar."
                )
        else:
            if params:
                request_kwargs['params'] = params

        # ── Executa com circuit breaker (SSRF-safe, IP-pinned) ───────────────
        async def _do_request():
            return await safe_httpx_request(**request_kwargs)

        # ── Retry on transient failure ───────────────────────────────────
        # "Transient" is literal: only transport errors. The `except` used to be
        # bare and retried EVERYTHING — including the SSRF refusal, the size
        # limit overflow and the certificate validation failure, whose own message
        # says "this is not a temporary failure". Retrying what will give the same
        # error doesn't just cost the wait: each attempt goes through the circuit
        # breaker and counts a failure, so a malformed URL in one node opened the
        # host's circuit and knocked down, for 60 s, the legitimate requests of all
        # the other workflows that talk to it.
        # It stays OUTSIDE the per-call circuit breaker: each attempt goes through it,
        # so a host whose circuit is already open fails immediately instead of spending
        # the attempts waiting. The wait grows with each retry (ranges of
        # 0.25–0.5s, 0.5–1s, 1–2s…) so as not to retry in a burst against a server
        # that already said it's overloaded; the jitter within the range is what
        # keeps several workflows from hitting at once (see flow/utils/backoff.py).
        pode_repetir = method in _METODOS_REPETIVEIS and tentativas > 0
        total = tentativas + 1 if pode_repetir else 1
        response = None

        for tentativa in range(total):
            ultima = tentativa == total - 1
            try:
                response = await breaker.call(_do_request)
            except CircuitOpenError as e:
                raise RuntimeError(str(e))
            except httpx.TransportError as e:
                # Only what is transient enters the retry: timeout, connection
                # refused, drop in the middle of the read.
                if ultima:
                    logger.error("Erro na requisição HTTP para %s: %s", url, e)
                    raise RuntimeError(f"Erro na requisição HTTP: {e}")
                logger.warning(
                    "Tentativa %d/%d falhou para %s (%s) — repetindo.",
                    tentativa + 1, total, url, e,
                )
            else:
                if ultima or response.status_code not in _STATUS_REPETIVEIS:
                    break
                logger.warning(
                    "Tentativa %d/%d devolveu HTTP %s de %s — repetindo.",
                    tentativa + 1, total, response.status_code, url,
                )

            await asyncio.sleep(
                espera_exponencial(tentativa, inicial=0.5, teto=_TETO_DE_ESPERA_S)
            )

        logger.info("Recebido HTTP %s de %s", response.status_code, url)

        # ── Redirects ────────────────────────────────────────────────────────
        # `safe_httpx_request` refuses to follow on its own, and for good reason: a
        # 3xx pointing to an internal address would turn the platform into an SSRF
        # proxy. Following HERE keeps the defense, because each hop goes back
        # through the same function, which revalidates the URL and redoes the IP pinning.
        if seguir_redirect:
            saltos = 0
            while response.is_redirect and saltos < max_redirects:
                destino = response.headers.get('location')
                if not destino:
                    break
                destino = str(httpx.URL(url).join(destino))
                logger.info("Redirecionamento %d: %s → %s", saltos + 1, url, destino)

                # SEC: whoever chooses the destination of a 3xx is the remote server, not
                # the user. Forwarding `Authorization` would hand the credential's
                # token to a host the other side pointed to — a compromised
                # endpoint, or an open redirect, is all it takes for the
                # secret to leave the platform. On the SAME origin the header goes along:
                # it's the common case of `/api` → `/api/`, and dropping it there would
                # only make the request come back 401.
                if not _mesma_origem(url, destino):
                    request_kwargs['headers'] = _sem_credenciais(request_kwargs['headers'])

                # The `Location` is already the complete target, query included. Continuing
                # to pass `params` — which was built from the ORIGINAL URL —
                # would make httpx REPLACE the destination's query with that of the
                # address we came from, erasing exactly what usually comes in a
                # download redirect: the file's temporary signature. It's also
                # what every HTTP client does when following a 3xx.
                request_kwargs.pop('params', None)

                url = destino
                request_kwargs['url'] = destino
                # 303, and 301/302 on POST, become GET without a body — it's what every
                # HTTP client does, and forwarding the body would break the API on
                # the other side.
                if response.status_code == 303 or (
                    response.status_code in (301, 302) and method == 'POST'
                ):
                    request_kwargs['method'] = 'GET'
                    request_kwargs.pop('json', None)
                    request_kwargs.pop('content', None)

                # The circuit breaker is PER HOST, and after the hop the host is different:
                # continuing to use the original address's breaker counted the
                # destination's failures against the one that only redirected, and
                # stopped consulting the circuit of the host actually being called.
                salto_breaker = get_circuit_breaker(
                    f"http:{urlparse(destino).netloc or destino}"
                )
                try:
                    response = await salto_breaker.call(_do_request)
                except CircuitOpenError as e:
                    raise RuntimeError(str(e))
                saltos += 1

            if response.is_redirect:
                raise RuntimeError(
                    f"Limite de {max_redirects} redirecionamentos atingido sem chegar "
                    f"a uma resposta final."
                )

        try:
            data = response.json()
        except ValueError:
            data = response.text

        return {
            'status_code': response.status_code,
            'headers':     dict(response.headers),
            'body':        data,
        }
