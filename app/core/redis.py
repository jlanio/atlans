# app/core/redis.py
"""
Pool Redis centralizado para o Atlas Studio.

Uso:
    # No lifespan (main.py):
    from app.core.redis import init_redis, close_redis
    await init_redis()

    # Em qualquer serviço:
    from app.core.redis import get_redis_pool
    redis = get_redis_pool()
    await redis.get("chave")

    # Contador de rate limit / cota numa janela de tempo:
    from app.core.redis import contar_na_janela
    contagem, ttl = await contar_na_janela("ratelimit:x:chave", 60)

Nota: executor_connections.py e run_result_consumer.py mantêm conexões
próprias intencionalmente (pub/sub persistente e brpop bloqueante).
"""
import redis.asyncio as aioredis

from app.core.config import REDIS_URL

_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    """Retorna o pool Redis global. Deve ser inicializado via init_redis() no lifespan."""
    if _pool is None:
        raise RuntimeError(
            "Redis pool não inicializado. "
            "Certifique-se de que init_redis() foi chamado no lifespan da aplicação."
        )
    return _pool


async def init_redis() -> aioredis.Redis:
    """Inicializa o pool Redis global. Chamado uma vez no startup."""
    global _pool
    _pool = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _pool


def new_pubsub_client() -> aioredis.Redis:
    """Cliente Redis DEDICADO para uma assinatura pub/sub de longa duração.

    Um assinante segura a conexão enquanto o run inteiro dura. Vindo de um pool
    com teto (o WS de logs tinha um pool próprio de 20), o N-ésimo espectador
    recebia MaxConnectionsError e o painel fechava sem explicação nenhuma —
    intermitente, sumindo sozinho quando alguém fechava uma aba. Aqui cada
    assinante ganha a própria conexão, sem teto: o custo é um socket por painel
    aberto, que é o que o pub/sub exige de qualquer forma.

    Comandos pontuais (GET/LRANGE) continuam no pool global — este cliente é só
    para o subscribe. O chamador DEVE fechar com `await client.aclose()`.
    """
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def contar_na_janela(
    chave: str,
    janela_s: int,
    *,
    incremento: int = 1,
    deslizante: bool = False,
    redis: aioredis.Redis | None = None,
) -> tuple[int, int]:
    """Soma `incremento` ao contador `chave` e devolve (contagem, ttl em segundos).

    É o contador de todo rate limit e cota por janela da API. `INCRBY`, `EXPIRE`
    e `TTL` saem numa transação só (MULTI/EXEC): ou os três acontecem, ou
    nenhum. Com dois comandos soltos — `INCR` e, se o contador voltou a 1,
    `EXPIRE` —, perder o segundo (o processo cai entre os dois, a conexão
    quebra, o SSE é cancelado no meio) deixava a chave SEM PRAZO: o contador
    nunca zerava e, ao cruzar o teto, o IP, o executor, a família de refresh ou
    o usuário ficavam bloqueados para sempre.

    Janela fixa (o padrão): `EXPIRE ... NX` só arma o prazo de uma chave que não
    tem nenhum — na primeira contagem, ou numa chave que ficou sem prazo antes
    desta função existir —, e nunca empurra um prazo que já corre: senão a
    janela não fecharia enquanto houvesse tráfego. O `NX` exige Redis 7 (o
    compose usa `redis:7-alpine`).

    `deslizante=True` renova o prazo a cada contagem: a janela só fecha depois
    de `janela_s` segundos SEM contagem (o bloqueio de login por conta).

    `redis`: um cliente já em mãos; sem ele, o pool global. Erros do Redis
    sobem para o chamador, que decide se degrada aberto ou fechado.
    """
    rc = redis if redis is not None else get_redis_pool()
    async with rc.pipeline(transaction=True) as pipe:
        pipe.incrby(chave, incremento)
        pipe.expire(chave, janela_s, nx=not deslizante)
        pipe.ttl(chave)
        contagem, _, ttl = await pipe.execute()
    return int(contagem), int(ttl)


async def close_redis() -> None:
    """Fecha o pool Redis. Chamado no shutdown."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
