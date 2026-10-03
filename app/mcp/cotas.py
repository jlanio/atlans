# app/mcp/cotas.py
"""
Per-token quotas: the ceiling that keeps a client in a loop from taking the platform down.

An MCP client repeats calls on its own — rewrites the definition, validates
again, executes again — and a poorly closed loop on the other side becomes a
storm here. The buckets are keyed by `token_id`, never by IP: clients behind the
same NAT or the same cloud would collapse into a single bucket, and the client's
IP is not even trustworthy.

Two kinds of ceiling:
- count per minute (`verificar`), with a general bucket and extra buckets for
  the expensive operations (validating connects to a database, executing
  dispatches to an executor);
- simultaneous waits (`espera`), because each run `wait` holds a pub/sub
  subscription and an open SSE response — a resource that is not measured in
  requests per minute.

Without Redis, everything degrades OPEN. It is the same policy as the logs
WebSocket (`dependencies.py`): the API does not even start without Redis, so
"Redis down" is a transient incident lasting seconds — refusing every call in
that interval would turn a degradation into a total outage, and the ceiling
exists against accidental loops, not against an adversary. The warning goes out
at most once per minute per process so the incident does not flood the log
precisely when it is needed.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.core.config import ASSISTENTE_TETO_DE_TOKENS_POR_DIA
from app.core.redis import contar_na_janela
from app.core.utils.logger import get_logger
from app.mcp.erros import erro

logger = get_logger("app.mcp.cotas")

JANELA_SEGUNDOS = 60

LIMITE_GERAL = 120
# `probe` is I/O against third-party servers (GetCapabilities/DescribeFeatureType
# of a WFS): half of the validation bucket, which is already the tightest.
LIMITES_POR_COTA: dict[str, int] = {"validate": 20, "run": 20, "probe": 10}

MAX_ESPERAS_POR_TOKEN = 3
MAX_ESPERAS_GLOBAL = 40

# The web assistant's quota. Here the ceiling is not about load: it is about MONEY
# — the platform pays for the model's tokens. That is why the unit is tokens
# accumulated over a 24 h window, and not calls per minute.
#
# The number came from a measurement (with 38 tools; today there are 42): the
# tool definitions add up to ~6.9 k
# tokens, and what dominates a conversation is the RESULTS (the node index is
# ~10 KB, a whole definition about as much). Building a real workflow costs
# on the order of 150 k to 400 k tokens summing all turns. 1.5 M gives a
# comfortable margin of a few workflows per day per person, and still puts a
# ceiling on what a single account can spend.
#
# Revise with the real number: `docs/editor-assistant.md` records the measured
# cost, and this value should come from there, not from an estimate. Each
# installation can change it via ASSISTENTE_TETO_DE_TOKENS_POR_DIA (`app/core/config.py`).
JANELA_DO_ASSISTENTE_SEGUNDOS = 24 * 60 * 60
TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA = ASSISTENTE_TETO_DE_TOKENS_POR_DIA

# One warning per minute per process — see the module note.
_INTERVALO_AVISO = 60.0
_ultimo_aviso = 0.0

# Without Redis there is no counter shared across workers; the wait ceiling falls
# back to this semaphore, which only holds within the process. It is less than the
# design asks for and more than nothing: it holds back a single client's loop.
_esperas_locais: dict[str, int] = {}
_esperas_locais_total = 0


def _avisar_sem_redis(motivo: str) -> None:
    global _ultimo_aviso
    agora = time.monotonic()
    if agora - _ultimo_aviso < _INTERVALO_AVISO:
        return
    _ultimo_aviso = agora
    logger.warning("Cotas do MCP degradando abertas (%s).", motivo)


def _limite_da_cota(cota: str) -> int:
    return LIMITES_POR_COTA.get(cota, LIMITE_GERAL)


async def verificar(redis, token_id: str, cota: str | None = None) -> None:
    """Consumes one unit from the general bucket and, if there is one, from the quota's bucket.

    Fixed one-minute window (`contar_na_janela`), the same counter as the
    WebSocket rate limit: the deadline starts at the first call and does not
    move. Exceeded: raises `ToolError rate_limited` with `retry_after_seconds`
    read from the TTL, so the client knows to wait instead of retrying.
    """
    if redis is None:
        _avisar_sem_redis("pool Redis indisponível")
        return

    baldes: list[tuple[str, int]] = [(f"ratelimit:mcp:{token_id}:geral", LIMITE_GERAL)]
    if cota:
        baldes.append((f"ratelimit:mcp:{token_id}:{cota}", _limite_da_cota(cota)))

    for chave, limite in baldes:
        try:
            contador, ttl = await contar_na_janela(chave, JANELA_SEGUNDOS, redis=redis)
        except Exception as exc:  # pragma: no cover - depends on Redis
            _avisar_sem_redis(f"falha ao contar: {exc.__class__.__name__}")
            return
        if contador <= limite:
            continue
        raise erro(
            "rate_limited",
            f"Limite de {limite} chamadas por minuto atingido para este token.",
            "aguarde a janela reabrir antes de tentar de novo",
            retry_after_seconds=ttl if ttl > 0 else JANELA_SEGUNDOS,
        )


async def verificar_tokens_do_assistente(
    redis, user_id: str, *, teto: int = TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
) -> None:
    """Refuses the conversation when the user has already spent the day's token quota.

    `teto` is injected because it may depend on the PLAN of whoever is chatting
    (`teto_do_assistente.teto_de`), and resolving it here would force this
    module — which is Redis only — to know about the database and subscriptions.
    The default preserves the behavior for callers that pass nothing: the
    installation's ceiling.

    Why TOKENS and not messages: a message that fires ten tool calls costs ten
    times one that fires none, and what the platform pays for is tokens, not
    messages. Counting messages would measure the wrong thing and give the same
    quota to "obrigado!" (thanks!) and to the twenty-node workflow.

    The check is BEFORE the call and the charge is AFTER (`cobrar_tokens_do_
    assistente`), because the cost is only known in the response's `usage`. The
    accepted consequence is that the day's last conversation can go over the
    ceiling — never by more than one turn, and the ceiling exists against
    accumulated spending, not against the last cent.
    """
    if redis is None:
        _avisar_sem_redis("pool Redis indisponível")
        return
    try:
        gasto = await redis.get(chave_de_tokens(user_id))
    except Exception as exc:  # pragma: no cover - depends on Redis
        _avisar_sem_redis(f"falha ao ler a cota do assistente: {exc.__class__.__name__}")
        return
    if gasto is None:
        return
    try:
        acumulado = int(gasto)
    except (TypeError, ValueError):  # pragma: no cover - corrupted value
        return
    if acumulado < teto:
        return
    # "assistente", and not "assistente": this same path serves Home and the
    # editor, and whoever does not administer the system only reaches Home — for
    # that person, "assistente" names something they have never seen. For the
    # same reason "enquanto isso o editor continua inteiro" (meanwhile the editor
    # remains intact) was removed: it was consolation about a screen they cannot
    # open.
    #
    # "da SUA primeira conversa" (of YOUR first conversation), and not "do dia"
    # (of the day): the deadline starts at the first charge (that is where the
    # EXPIRE is set), so there is no midnight rollover.
    raise erro(
        "rate_limited",
        "Você atingiu a cota diária do assistente.",
        "a cota reabre 24 horas depois da sua primeira conversa",
        retry_after_seconds=await _quanto_falta(redis, chave_de_tokens(user_id)),
    )


async def cobrar_tokens_do_assistente(redis, user_id: str, tokens: int) -> int | None:
    """Adds up what this turn spent. Never raises — charging must not lose the work.

    Returns the window's running total AFTER this charge (what INCRBY
    answered): it is what the stream sends to the screen in the `cota` frame,
    so the donut goes up during the turn without querying `/estado`. `None`
    when there was no charge — no Redis, nothing to charge, or Redis failed.

    The 24 h window starts at the first charge and does not move
    (`contar_na_janela`, which sets the deadline in the same transaction as the
    INCRBY — the key does not become immortal).

    If Redis fails here, the spending drops out of the count and the day's
    ceiling gets looser. It is the right side to err on: the other would be
    discarding a response the model has already produced (and the platform has
    already paid for) because of a counter.
    """
    if redis is None or tokens <= 0:
        return None
    try:
        acumulado, _ = await contar_na_janela(
            chave_de_tokens(user_id), JANELA_DO_ASSISTENTE_SEGUNDOS, incremento=int(tokens), redis=redis
        )
        return acumulado
    except Exception as exc:  # pragma: no cover - depends on Redis
        _avisar_sem_redis(f"falha ao cobrar a cota do assistente: {exc.__class__.__name__}")
        return None


# The key is the SAME (`assistente:tokens:…`)
# for both the editor assistant and the Home assistant — the two share the
# per-person model token budget, and that is what the daily ceiling measures.
#
# The single bucket is DELIBERATE (the model is the same and the per-person
# budget is a single one), but since Home became the first screen after login it
# started being consumed unintentionally: someone who chats on the globe in the
# morning may find the editor assistant exhausted in the afternoon without ever
# having opened it. Separating the keys here would resolve the surprise and
# double the maximum spending per person — a product decision, not a code one.
# The meter on both surfaces (`uso-da-cota.tsx`, which reads
# `GET /assistente/estado` and `GET /assistente/estado`, both on this same key)
# shows only spending, ceiling and deadline: saying there that the budget is
# shared was tried and removed — it is noise for someone reading a meter. The
# fact is recorded in docs/assistant.md, "Known limits".
def chave_de_tokens(user_id: str) -> str:
    return f"assistente:tokens:{user_id}"


async def gasto_e_prazo(redis, user_id: str) -> tuple[int, int | None]:
    """How much has been spent in the window and in how many seconds it reopens. Never raises.

    It is what `GET /assistente/editor/estado` shows without refusing anything
    — and what the assistant's `GET /assistente/estado` will read. It lives
    here, next to the rest of the token accounting, so both routes read the
    SAME source instead of each one reimplementing the key read.
    """
    if redis is None:
        return (0, None)
    chave = chave_de_tokens(user_id)
    try:
        cru = await redis.get(chave)
        # An old key with no deadline (the charge from before `contar_na_janela`
        # did INCRBY and EXPIRE in two commands, and the second could get lost):
        # NX gives it the window and does not touch a key that has a deadline.
        # It has to be here, and not only in the refusal: with the quota full,
        # the interface reads this state and locks sending, the refusal never
        # runs, and the key would never expire.
        if cru is not None:
            await redis.expire(chave, JANELA_DO_ASSISTENTE_SEGUNDOS, nx=True)
        ttl = await redis.ttl(chave)
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao ler a cota do assistente: %s", exc.__class__.__name__)
        return (0, None)
    try:
        gasto = int(cru) if cru is not None else 0
    except (TypeError, ValueError):  # pragma: no cover - corrupted value
        gasto = 0
    return (gasto, int(ttl) if isinstance(ttl, int) and ttl > 0 else None)


async def _quanto_falta(redis, chave: str) -> int:
    """The window's TTL, so the refusal can say when it reopens. Never raises.

    The `EXPIRE ... NX` before reading only acts on a key WITHOUT a deadline —
    one that the charge from before `contar_na_janela` (INCRBY and EXPIRE in two
    commands) left immortal. It is in the refusal that this matters: once
    refused, the turn never reaches the charge, which is what sets the
    deadline, and whoever crossed the ceiling with such a key would never have
    the assistant again. On a key with a deadline, NX touches nothing.
    """
    try:
        await redis.expire(chave, JANELA_DO_ASSISTENTE_SEGUNDOS, nx=True)
        ttl = await redis.ttl(chave)
    except Exception:  # pragma: no cover - depends on Redis
        return JANELA_DO_ASSISTENTE_SEGUNDOS
    return int(ttl) if isinstance(ttl, int) and ttl > 0 else JANELA_DO_ASSISTENTE_SEGUNDOS


@asynccontextmanager
async def espera(redis, token_id: str, ttl_s: int) -> AsyncIterator[None]:
    """Reserves one of the simultaneous waits — and always gives it back, even on error.

    The keys' TTL is `ttl_s + 60`: if a worker dies in the middle of the wait,
    the counter fixes itself one minute after the run's maximum deadline,
    instead of leaving the ceiling stuck for the token until someone notices.

    The reservation is two `INCR`s on different keys, and a failure between
    them must not leave the first one dangling: what was actually incremented
    is noted and given back in the error handling. Without that, a Redis that
    goes down in the middle of the reservation would consume one of the
    token's slots on every attempt until the TTL expired.
    """
    if redis is None:
        _avisar_sem_redis("pool Redis indisponível")
        async with _espera_local(token_id):
            yield
        return

    chave_token = f"mcp:wait:token:{token_id}"
    chave_global = "mcp:wait:global"
    expiracao = max(int(ttl_s), 0) + 60
    incrementadas: list[str] = []
    try:
        do_token = await redis.incr(chave_token)
        incrementadas.append(chave_token)
        await redis.expire(chave_token, expiracao)
        do_global = await redis.incr(chave_global)
        incrementadas.append(chave_global)
        await redis.expire(chave_global, expiracao)
    except Exception as exc:  # pragma: no cover - depends on Redis
        _avisar_sem_redis(f"falha ao reservar espera: {exc.__class__.__name__}")
        await _devolver(redis, *incrementadas)
        async with _espera_local(token_id):
            yield
        return

    if do_token > MAX_ESPERAS_POR_TOKEN or do_global > MAX_ESPERAS_GLOBAL:
        await _devolver(redis, chave_token, chave_global)
        excedido_no_token = do_token > MAX_ESPERAS_POR_TOKEN
        raise erro(
            "wait_limit",
            (
                f"Limite de {MAX_ESPERAS_POR_TOKEN} execuções aguardando em paralelo "
                "atingido para este token."
                if excedido_no_token
                else "A plataforma está no limite de execuções aguardando em paralelo."
            ),
            "execute com wait=false e acompanhe por get_run(run_id)",
        )

    try:
        yield
    finally:
        await _devolver(redis, chave_token, chave_global)


async def _devolver(redis, *chaves: str) -> None:
    """Releases the reservation. Never raises: failing here would only lose the result."""
    for chave in chaves:
        try:
            await redis.decr(chave)
        except Exception as exc:  # pragma: no cover - depends on Redis
            logger.warning("Falha ao devolver a espera de %s: %s", chave, exc.__class__.__name__)


@asynccontextmanager
async def _espera_local(token_id: str) -> AsyncIterator[None]:
    """Per-process ceiling, used only when there is no Redis."""
    global _esperas_locais_total
    do_token = _esperas_locais.get(token_id, 0) + 1
    if do_token > MAX_ESPERAS_POR_TOKEN or _esperas_locais_total + 1 > MAX_ESPERAS_GLOBAL:
        raise erro(
            "wait_limit",
            f"Limite de {MAX_ESPERAS_POR_TOKEN} execuções aguardando em paralelo atingido.",
            "execute com wait=false e acompanhe por get_run(run_id)",
        )
    _esperas_locais[token_id] = do_token
    _esperas_locais_total += 1
    try:
        yield
    finally:
        restante = _esperas_locais.get(token_id, 1) - 1
        if restante > 0:
            _esperas_locais[token_id] = restante
        else:
            _esperas_locais.pop(token_id, None)
        _esperas_locais_total -= 1
