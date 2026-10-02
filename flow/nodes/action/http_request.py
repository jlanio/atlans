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

# Repetir um POST/PATCH que já chegou ao servidor duplica o efeito — a resposta
# pode ter se perdido no caminho de volta, não na ida. Os demais são
# idempotentes por definição do protocolo.
_METODOS_REPETIVEIS = frozenset({'GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE'})

# Falhas em que repetir faz sentido: o servidor disse "estou sobrecarregado" ou
# "tente de novo". 4xx (exceto 429) é erro do pedido — repetir dá o mesmo erro.
_STATUS_REPETIVEIS = frozenset({429, 500, 502, 503, 504})
# Teto da espera entre repeticoes. Com o maximo de tentativas que o no
# oferece a espera nao chega perto, mas a politica compartilhada exige um
# teto declarado — e um `tentativas` alto configurado no canvas nao deve
# poder prender o fluxo por minutos.
_TETO_DE_ESPERA_S = 30.0


def _inteiro(valor: Any, padrao: int) -> int:
    """Número vindo do formulário, que chega como string quando digitado."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _juntar_query(url: str, params: Any) -> List[Tuple[str, str]]:
    """Junta a query que ja esta na URL com a do campo `Parametros de query`.

    O httpx trata `params` como a query inteira: entregar um dicionario a ele
    SUBSTITUI o que veio na URL. Como a forma natural de usar o no e colar o
    endereco pronto do portal — e endereco de WFS/OGC e quase so query —, o
    comportamento util e somar, nao trocar.

    Devolve LISTA DE PARES, e nao dicionario, porque a query HTTP admite a mesma
    chave repetida e isso e comum justamente aqui: `?bbox=..&bbox=..`,
    `?typeName=a&typeName=b`. Um `dict(parse_qsl(...))` guarda so a ultima
    ocorrencia e emudece as demais — a URL sai do no diferente da que o usuario
    colou. O httpx aceita a lista de pares e preserva a repeticao.

    O campo vence em caso de chave repetida: quem digitou o par explicitamente
    esta corrigindo o que veio na URL — entao as ocorrencias daquela chave que
    vieram da URL saem, em vez de se somarem ao valor digitado.
    """
    do_campo = [(str(k), str(v)) for k, v in (params or {}).items()]
    sobrescritas = {chave for chave, _ in do_campo}
    da_url = [
        (chave, valor)
        for chave, valor in parse_qsl(urlparse(url).query, keep_blank_values=True)
        if chave not in sobrescritas
    ]
    return da_url + do_campo


# Cabecalhos que carregam credencial e nao podem atravessar uma mudanca de
# origem. E a mesma lista que curl e requests derrubam ao seguir um 3xx.
_CABECALHOS_DE_CREDENCIAL = frozenset({'authorization', 'cookie', 'proxy-authorization'})


def _mesma_origem(a: str, b: str) -> bool:
    """Compara origem no sentido do RFC 6454: esquema, host e porta efetiva."""
    _PADRAO = {'http': 80, 'https': 443}
    def origem(u: str):
        p = urlparse(u)
        esquema = (p.scheme or '').lower()
        return (esquema, (p.hostname or '').lower(), p.port or _PADRAO.get(esquema))
    return origem(a) == origem(b)


def _sem_credenciais(headers: Dict[str, str]) -> Dict[str, str]:
    """Copia dos cabecalhos sem os que carregam segredo."""
    return {k: v for k, v in headers.items() if k.lower() not in _CABECALHOS_DE_CREDENCIAL}


def _aplicar_auth(headers: Dict[str, str], auth: Any) -> Dict[str, str]:
    """Monta o header `Authorization` a partir da credencial resolvida.

    A credencial vence um `Authorization` escrito à mão nos cabeçalhos: quem
    selecionou uma credencial expressou a intenção mais forte, e o contrário
    faria um header esquecido no formulário silenciosamente derrubar o segredo
    que o usuário acabou de escolher.
    """
    if not isinstance(auth, dict):
        return headers

    tipo = auth.get('type')
    if not tipo:
        return headers
    if tipo not in ('http_bearer', 'http_basic'):
        # O resolver injeta `http_auth` também para as credenciais do WFS; uma
        # delas escolhida aqui sairia ignorada e a requisição, ANÔNIMA.
        raise ValueError(
            f"A credencial escolhida (tipo '{tipo}') não serve para requisição HTTP: "
            "use uma do tipo HTTP Bearer ou HTTP Basic."
        )

    # Header HTTP não distingue maiúscula de minúscula, mas dicionário sim:
    # gravar em `Authorization` deixava um `authorization` digitado à mão de pé
    # ao lado, e o nó enviava DOIS cabeçalhos de autenticação — cabe ao servidor
    # decidir qual vale, e nenhum dos dois desfechos é o que o usuário pediu.
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
    Executa requisições HTTP assíncronas (GET, POST, PUT, PATCH, DELETE, etc.).
    - Protegido contra SSRF via validate_url_ssrf.
    - Protegido por Circuit Breaker por host (5 falhas → abre por 60 s).
    - Se método for POST/PUT/PATCH e 'body' estiver vazio, usa payload de inputs.
      GeoDataFrames recebidos são automaticamente convertidos para GeoJSON.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'HttpRequest',
            'alias': 'Requisição HTTP',
            'description': 'Executa requisições HTTP assíncronas com circuit breaker e proteção SSRF.',
            'type': 'action',
            # Opcional: sem credencial a requisição sai anônima, que é o caso
            # de qualquer API pública. `requires_credential` obrigaria a
            # escolher uma para o nó sequer validar.
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
                    # INJETADA pelo servidor a partir de `credential_id`, e
                    # declarada aqui por um motivo que nao e cosmetico:
                    # `BaseNode.validate()` RECONSTROI `self.parameters` a partir
                    # desta lista, e descarta toda chave que nao esteja nela (ver
                    # a docstring de validate_node_parameters). Sem esta entrada,
                    # `http_auth` era resolvida pelo servidor, injetada, e jogada
                    # fora na primeira linha do `execute()` — toda requisicao com
                    # credencial saia ANONIMA, com o proprio runtime imprimindo
                    # "parametro(s) ['http_auth'] ... descartados" num aviso que
                    # ninguem lia.
                    #
                    # E o mesmo tratamento que `connectionString` ja recebia nos
                    # nos de banco. A UI a esconde pelo nome (node-config-form).
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
                    # `keyvalue`, e não `object`: cabeçalho é lista rasa de duas
                    # colunas, e o editor de árvore JSON cobrava navegação e
                    # escolha de tipo por um dado que se digita de cor.
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
                    # `in`, e não `equals`: é o único operador que
                    # `isFieldVisible` conhece (ver node-config-form).
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

        # `http_auth` é injetado pelo servidor a partir da credencial escolhida
        # (ver credential_resolver). O segredo NÃO trafega na definition do
        # workflow — é por isso que autenticar por aqui é melhor do que escrever
        # o header à mão, que fica gravado em claro no banco e no histórico.
        headers = _aplicar_auth(headers, self.parameters.get('http_auth'))

        if not url:
            raise ValueError("Parâmetro 'url' é obrigatório para HttpRequest.")

        # O servidor REMOVE `credential_id` das propriedades ao injetar a
        # credencial resolvida (ver credential_resolver.inject_credentials).
        # Chegar aqui com o id AINDA presente e sem `http_auth` significa que a
        # resolução não aconteceu — credencial apagada, fora do escopo de quem
        # disparou, ou órfã. Antes disso passar em silêncio: a requisição saía
        # ANÔNIMA, e como o nó não trata 4xx como falha, um 401 virava output
        # normal e o fluxo seguia com a resposta de erro no lugar do dado.
        if self.parameters.get('credential_id') and not self.parameters.get('http_auth'):
            raise ValueError(
                "A credencial escolhida para este nó não pôde ser resolvida — ela pode "
                "ter sido apagada, não estar acessível a quem disparou a execução, ou ser "
                "de um tipo que este nó não usa (Bearer ou Basic). "
                "A requisição NÃO foi enviada, para não sair sem autenticação."
            )

        # `params` do httpx substitui a query INTEIRA da URL, nao acrescenta a
        # ela. Passar o dicionario vazio — o padrao do campo — apagava a query de
        # qualquer endereco colado pronto, e um WFS sem
        # `?service=WFS&request=GetFeature` nao e um WFS. Preencher o campo com a
        # URL ja tendo query tinha o mesmo efeito, so que parcial.
        #
        # A juncao acontece aqui, e nao no transporte, porque `safe_httpx_request`
        # atende tambem o WFS e o webhook, que montam a query por conta propria.
        params = _juntar_query(url, params)

        host    = urlparse(url).netloc or url
        breaker = get_circuit_breaker(f"http:{host}")

        logger.info("Preparando requisição HTTP: %s %s [circuit=%s]", method, url, breaker.state)

        # ── Monta kwargs para safe_httpx_request ─────────────────────────────
        # SEG (SSRF): antes chamavamos validate_url_ssrf e DESCARTAVAMOS o
        # retorno, deixando o httpx re-resolver o DNS (TOCTOU / DNS-rebinding).
        # safe_httpx_request valida E fixa o IP resolvido, fechando a janela.
        request_kwargs: Dict[str, Any] = {
            'method':  method,
            'url':     url,
            'headers': headers,
            'timeout': timeout,
        }
        if max_mb > 0:
            request_kwargs['max_response_bytes'] = max_mb * 1024 * 1024

        if method in ('GET', 'DELETE', 'HEAD', 'OPTIONS'):
            # `if params`, como ja fazia o ramo de POST/PUT/PATCH abaixo: sem a
            # guarda, o dicionario vazio chegava ao httpx e zerava a query.
            if params:
                request_kwargs['params'] = params

        elif method in ('POST', 'PUT', 'PATCH'):
            if body:
                # body explícito: tenta JSON, cai para content bruto
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

        # ── Repetição em falha transitória ───────────────────────────────────
        # "Transitória" é literal: só erro de transporte. Antes o `except` era
        # cru e repetia TUDO — inclusive a recusa de SSRF, o estouro do limite de
        # tamanho e a falha de validação do certificado, cuja própria mensagem
        # diz "isso não é falha temporária". Repetir o que vai dar o mesmo erro
        # não custa só a espera: cada tentativa passa pelo disjuntor e conta uma
        # falha, então uma URL malformada num nó abria o circuito do host e
        # derrubava, por 60 s, os pedidos legítimos de todos os outros fluxos
        # que falam com ele.
        # Fica FORA do circuit breaker por chamada: cada tentativa passa por ele,
        # então um host que já abriu o circuito falha na hora em vez de gastar as
        # tentativas esperando. A espera cresce a cada repetição (faixas de
        # 0,25–0,5s, 0,5–1s, 1–2s…) para não repetir em rajada contra um servidor
        # que já disse estar sobrecarregado; a dispersão dentro da faixa é o que
        # impede vários fluxos de baterem juntos (ver flow/utils/backoff.py).
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
                # Só o que é transitório entra na repetição: timeout, conexão
                # recusada, queda no meio da leitura.
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

        # ── Redirecionamentos ────────────────────────────────────────────────
        # `safe_httpx_request` recusa seguir sozinho, e por um bom motivo: um
        # 3xx apontando para endereço interno faria a plataforma virar proxy de
        # SSRF. Seguir AQUI mantém a defesa, porque cada salto entra de novo
        # pela mesma função, que revalida a URL e refaz o IP pinning.
        if seguir_redirect:
            saltos = 0
            while response.is_redirect and saltos < max_redirects:
                destino = response.headers.get('location')
                if not destino:
                    break
                destino = str(httpx.URL(url).join(destino))
                logger.info("Redirecionamento %d: %s → %s", saltos + 1, url, destino)

                # SEG: quem escolhe o destino de um 3xx é o servidor remoto, não
                # o usuário. Mandar o `Authorization` adiante entregaria o token
                # da credencial a um host que o outro lado apontou — basta um
                # endpoint comprometido, ou um redirecionamento aberto, para o
                # segredo sair da plataforma. Na MESMA origem o cabeçalho segue:
                # é o caso comum de `/api` → `/api/`, e derrubá-lo ali só faria
                # o pedido voltar 401.
                if not _mesma_origem(url, destino):
                    request_kwargs['headers'] = _sem_credenciais(request_kwargs['headers'])

                # O `Location` já é o alvo completo, query inclusive. Continuar
                # entregando `params` — que foi montado a partir da URL ORIGINAL —
                # faria o httpx TROCAR a query do destino pela do endereço de
                # onde viemos, apagando exatamente o que costuma vir num
                # redirecionamento de download: a assinatura temporária do
                # arquivo. É também o que todo cliente HTTP faz ao seguir um 3xx.
                request_kwargs.pop('params', None)

                url = destino
                request_kwargs['url'] = destino
                # 303, e 301/302 sobre POST, viram GET sem corpo — é o que todo
                # cliente HTTP faz, e mandar o corpo adiante quebraria a API do
                # outro lado.
                if response.status_code == 303 or (
                    response.status_code in (301, 302) and method == 'POST'
                ):
                    request_kwargs['method'] = 'GET'
                    request_kwargs.pop('json', None)
                    request_kwargs.pop('content', None)

                # O disjuntor é POR HOST, e depois do salto o host é outro: seguir
                # usando o do endereço original contava as falhas do destino na
                # conta de quem só redirecionou, e deixava de consultar o circuito
                # do host que de fato vai ser chamado.
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
