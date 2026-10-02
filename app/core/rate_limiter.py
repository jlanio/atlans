# app/core/rate_limiter.py
"""Rate limiter global da aplicacao.

`get_remote_address` do slowapi devolve `request.client.host`, que atras do
Traefik e SEMPRE o IP do proxy — todos os limites (`10/hour` no enrollment,
`10/minute` no patch de executor, etc.) viravam um unico balde compartilhado
pela plataforma inteira. Qualquer cliente conseguia esgotar a cota de todos.

`_client_key` resolve o IP real via X-Forwarded-For, confiando no header apenas
quando o peer e um proxy listado em TRUSTED_PROXIES (ver app/core/trusted_proxy.py).

Storage dos contadores. Com `uvicorn --workers 4` (api-prod) e contadores
em memoria, cada worker tem o proprio balde e um `10/minute` vale, na pratica,
ate 4x isso — o Traefik espalha as conexoes entre os workers — e tudo zera a
cada deploy. Por isso, sem configuracao, os contadores vao para o Redis da
aplicacao (`REDIS_URL`) e valem para a API inteira. Ordem de escolha:

1. `RATE_LIMIT_STORAGE_URI`, se definida: `redis://...` ou `memory://` (a
   saida explicita para memoria por worker);
2. `REDIS_URL`, se definida e for `redis://` ou `rediss://`;
3. memoria do processo (testes, dev sem Redis).

O storage Redis do `limits` e sincrono: roda no event loop do worker, um
round-trip curto na rede do compose por request nas rotas com limite. Sem
prazo, um Redis travado (aceita a conexao e nao responde) prende o worker
inteiro sem fim — medido: o `hit` segue bloqueado depois de 5 s. Por isso o
prazo de 0,25 s em `_PRAZO_DO_REDIS` (a ida ao Redis no compose leva bem
menos de 1 ms; parametros na query da URI, como `?socket_timeout=2`, valem
mais). `in_memory_fallback_enabled` faz o slowapi cair para memoria na
primeira falha e voltar sozinho quando o Redis responder, em vez de derrubar
a API junto. Com o Redis travado, o custo e: a primeira falha para o loop
por duas idas (o `hit` e uma conferencia imediata) e, depois, o slowapi
confere o Redis de novo com 2, 4, 8, 16 e 32 s de intervalo, e recomeca —
cada conferencia para o loop por ate um prazo. A resolucao do nome `redis`
(DNS) nao entra no prazo: com o container fora do ar, o Docker repassa a
consulta ao DNS do host.

Uma URI que o `limits` recusa (esquema desconhecido, porta invalida, typo
como `memory` sem `://`) cai em memoria com erro no log, em vez de derrubar a
importacao — e com ela os quatro workers.
"""
import os
from urllib.parse import urlsplit

from slowapi import Limiter

from app.core.trusted_proxy import get_client_ip
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

# Prazo de cada ida ao Redis do limiter, em segundos (ver a docstring). O
# redis-py 7 nao repete um timeout.
_PRAZO_DO_REDIS = {"socket_timeout": 0.25, "socket_connect_timeout": 0.25}
# Esquemas do `limits` que abrem uma conexao redis-py direta e aceitam o prazo.
# Sentinel e cluster levam outros parametros: quem os usar passa o prazo na
# query da URI.
_ESQUEMAS_COM_PRAZO = ("redis", "rediss", "redis+unix", "valkey", "valkeys", "valkey+unix")
_ESQUEMAS_REDIS = ("redis", "rediss")


def _client_key(request) -> str:
    return get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
    )


def _storage_do_limiter() -> str:
    """URI do storage dos contadores (ver a ordem na docstring do modulo)."""
    explicita = (os.getenv("RATE_LIMIT_STORAGE_URI") or "").strip()
    if explicita:
        return explicita
    redis_da_aplicacao = (os.getenv("REDIS_URL") or "").strip()
    if not redis_da_aplicacao:
        return "memory://"
    if _esquema(redis_da_aplicacao) not in _ESQUEMAS_REDIS:
        # `unix://` e afins valem para o redis-py, mas o `limits` nao conhece o
        # esquema e recusaria na importacao — a API nem subiria. Aqui, que e
        # so o padrao, memoria com aviso; quem quiser o socket define
        # RATE_LIMIT_STORAGE_URI=redis+unix://...
        logger.warning(
            "Rate limit: REDIS_URL com esquema %r nao serve ao limiter; contadores em memoria de cada worker.",
            _esquema(redis_da_aplicacao),
        )
        return "memory://"
    return redis_da_aplicacao


def _esquema(uri: str) -> str:
    """Esquema da URI em minusculas; "" se ela nem se deixa analisar."""
    try:
        return urlsplit(uri).scheme.lower()
    except ValueError:
        return ""


def _onde_ficam_os_contadores(storage_uri: str) -> str:
    """Para o log de arranque: esquema, host, porta e banco — nunca a senha.

    O caminho da URI nao sai inteiro: uma senha com `/` faz o `urlsplit`
    empurrar o resto dela para o caminho.
    """
    if _esquema(storage_uri) == "memory":
        return "memoria de cada worker (cada limite vale por worker)"
    try:
        partes = urlsplit(storage_uri)
        host = partes.hostname or "?"
        porta = f":{partes.port}" if partes.port else ""
    except ValueError:
        return f"{_esquema(storage_uri) or '?'}://? (compartilhados; memoria se cair)"
    banco = partes.path if partes.path[1:].isdigit() else ""
    return f"{partes.scheme}://{host}{porta}{banco} (compartilhados; memoria se cair)"


def _novo_limiter(storage_uri: str) -> Limiter:
    esquema = _esquema(storage_uri)
    return Limiter(
        key_func=_client_key,
        storage_uri=storage_uri,
        storage_options=dict(_PRAZO_DO_REDIS) if esquema in _ESQUEMAS_COM_PRAZO else {},
        # So faz sentido com storage externo — em memoria nao ha o que "cair".
        in_memory_fallback_enabled=esquema != "memory",
    )


def criar_limiter() -> Limiter:
    """Redis (com fallback em memoria) por padrao; memoria sem Redis ou com `memory://`."""
    storage_uri = _storage_do_limiter()
    try:
        limiter = _novo_limiter(storage_uri)
    except Exception as exc:
        # Esquema que o `limits` nao conhece, porta invalida, maiusculas que o
        # redis-py recusa: derrubar a importacao derrubaria a API inteira. So o
        # TIPO da excecao vai para o log: a mensagem cita pedacos da URI, e com
        # eles a senha ("Port could not be cast to integer value as '<senha>'").
        logger.error(
            "Rate limit: storage %s recusado (%s); contadores em memoria de cada worker.",
            _onde_ficam_os_contadores(storage_uri), type(exc).__name__,
        )
        storage_uri = "memory://"
        limiter = _novo_limiter(storage_uri)
    logger.info("Rate limit: contadores em %s", _onde_ficam_os_contadores(storage_uri))
    return limiter


# instância única de rate-limiter para toda a aplicação
limiter = criar_limiter()
