# app/mcp/cotas.py
"""
Cotas por token: o teto que impede um cliente em laço de derrubar a plataforma.

Um cliente MCP repete chamadas sozinho — reescreve a definição, valida de novo,
executa de novo — e um laço mal fechado do outro lado vira tempestade aqui. Os
baldes são chaveados pelo `token_id`, nunca pelo IP: clientes atrás do mesmo NAT
ou da mesma nuvem colapsariam num balde só, e o IP do cliente sequer é confiável.

Dois tipos de teto:
- contagem por minuto (`verificar`), com um balde geral e baldes extras para as
  operações caras (validar conecta em banco, executar despacha para um executor);
- esperas simultâneas (`espera`), porque cada `wait` de execução segura uma
  assinatura pub/sub e uma resposta SSE aberta — recurso que não se mede por
  requisições por minuto.

Sem Redis, tudo degrada ABERTO. É a mesma política do WebSocket de logs
(`dependencies.py`): a API nem sobe sem Redis, então "Redis fora" é um incidente
transitório de segundos — recusar toda chamada nesse intervalo transformaria uma
degradação em queda total, e o teto existe contra laço acidental, não contra
adversário. O aviso sai no máximo uma vez por minuto por processo para que o
incidente não afogue o log justamente quando ele é preciso.
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
# `probe` é I/O contra servidores de terceiros (GetCapabilities/DescribeFeatureType
# de um WFS): metade do balde de validação, que já é o mais apertado.
LIMITES_POR_COTA: dict[str, int] = {"validate": 20, "run": 20, "probe": 10}

MAX_ESPERAS_POR_TOKEN = 3
MAX_ESPERAS_GLOBAL = 40

# Cota do assistente da web. Aqui o teto não é sobre carga: é sobre DINHEIRO — a
# plataforma paga os tokens do modelo. Por isso a unidade é token acumulado numa
# janela de 24 h, e não chamada por minuto.
#
# O número saiu de uma medição (com 38 ferramentas; hoje são 42): as
# definições de ferramenta somam ~6,9 k
# tokens, e o que domina uma conversa são os RESULTADOS (o índice de nós tem
# ~10 KB, uma definição inteira outro tanto). Montar um fluxo de verdade custa
# na ordem de 150 k a 400 k tokens somando todos os turnos. 1,5 M dá uma margem
# folgada de alguns fluxos por dia por pessoa, e ainda assim põe um teto no que
# uma conta sozinha pode gastar.
#
# Revise com o número real: `docs/assistente-editor.md` registra o custo medido, e este
# valor deve sair de lá, não de estimativa. Cada instalação pode trocá-lo por
# ASSISTENTE_TETO_DE_TOKENS_POR_DIA (`app/core/config.py`).
JANELA_DO_ASSISTENTE_SEGUNDOS = 24 * 60 * 60
TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA = ASSISTENTE_TETO_DE_TOKENS_POR_DIA

# Um aviso por minuto por processo — ver a nota do módulo.
_INTERVALO_AVISO = 60.0
_ultimo_aviso = 0.0

# Sem Redis não há contador compartilhado entre workers; o teto de esperas cai
# para este semáforo, que vale só dentro do processo. É menos do que o desenho
# pede e mais do que nada: segura o laço de um único cliente.
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
    """Consome uma unidade do balde geral e, se houver, do balde da cota.

    Janela fixa de um minuto (`contar_na_janela`), o mesmo contador do rate
    limit do WebSocket: o prazo nasce na primeira chamada e não anda. Estourou:
    levanta `ToolError rate_limited` com `retry_after_seconds` lido do TTL, para
    o cliente saber esperar em vez de repetir.
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
        except Exception as exc:  # pragma: no cover - depende do Redis
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
    """Recusa a conversa quando o usuário já gastou a cota de tokens do dia.

    `teto` é injetado porque ele pode depender do PLANO de quem conversa
    (`teto_do_assistente.teto_de`), e resolvê-lo aqui obrigaria este módulo — que é
    só Redis — a conhecer banco e assinatura. O default preserva o
    comportamento de quem não passa nada: o teto da instalação.

    Por que TOKENS e não mensagens: uma mensagem que dispara dez chamadas de
    ferramenta custa dez vezes uma que não dispara nenhuma, e o que a plataforma
    paga é token, não mensagem. Contar mensagens mediria a coisa errada e daria
    a mesma cota para o "obrigado!" e para o fluxo de vinte nós.

    A conferência é ANTES da chamada e a cobrança é DEPOIS (`cobrar_tokens_do_
    assistente`), porque o custo só se conhece no `usage` da resposta. A
    consequência aceita é que a última conversa do dia pode passar do teto —
    nunca por mais de um turno, e o teto existe contra gasto acumulado, não
    contra o centavo.
    """
    if redis is None:
        _avisar_sem_redis("pool Redis indisponível")
        return
    try:
        gasto = await redis.get(chave_de_tokens(user_id))
    except Exception as exc:  # pragma: no cover - depende do Redis
        _avisar_sem_redis(f"falha ao ler a cota do assistente: {exc.__class__.__name__}")
        return
    if gasto is None:
        return
    try:
        acumulado = int(gasto)
    except (TypeError, ValueError):  # pragma: no cover - valor corrompido
        return
    if acumulado < teto:
        return
    # «assistente», e não «assistente»: este mesmo caminho serve a Home e o
    # editor, e quem não administra o sistema só alcança a Home — para essa
    # pessoa, «assistente» nomeia algo que ela nunca viu. Pelo mesmo motivo saiu
    # o «enquanto isso o editor continua inteiro»: era consolo sobre uma tela
    # que ela não pode abrir.
    #
    # «da SUA primeira conversa», e não «do dia»: o prazo nasce na primeira
    # cobrança (é ali que o EXPIRE é posto), então não há virada de meia-noite.
    raise erro(
        "rate_limited",
        "Você atingiu a cota diária do assistente.",
        "a cota reabre 24 horas depois da sua primeira conversa",
        retry_after_seconds=await _quanto_falta(redis, chave_de_tokens(user_id)),
    )


async def cobrar_tokens_do_assistente(redis, user_id: str, tokens: int) -> int | None:
    """Soma o que este turno gastou. Nunca levanta — cobrar não pode perder o trabalho.

    Devolve o acumulado da janela DEPOIS desta cobrança (o que o INCRBY
    respondeu): é o que o stream manda à tela no quadro `cota`, para o donut
    subir durante o turno sem consultar `/estado`. `None` quando não houve
    cobrança — sem Redis, nada a cobrar, ou o Redis falhou.

    A janela de 24 h nasce na primeira cobrança e não anda (`contar_na_janela`,
    que arma o prazo na mesma transação do INCRBY — a chave não fica imortal).

    Se o Redis falhar aqui, o gasto some da contagem e o teto do dia fica mais
    frouxo. É o lado certo para errar: o outro seria descartar uma resposta que
    o modelo já produziu (e que a plataforma já pagou) por causa de um contador.
    """
    if redis is None or tokens <= 0:
        return None
    try:
        acumulado, _ = await contar_na_janela(
            chave_de_tokens(user_id), JANELA_DO_ASSISTENTE_SEGUNDOS, incremento=int(tokens), redis=redis
        )
        return acumulado
    except Exception as exc:  # pragma: no cover - depende do Redis
        _avisar_sem_redis(f"falha ao cobrar a cota do assistente: {exc.__class__.__name__}")
        return None


# A chave é a MESMA (`assistente:tokens:…`)
# tanto para o assistente do editor quanto para o assistente da Home — os dois
# compartilham o orçamento de tokens do modelo por pessoa, e é isso que o teto
# diário mede.
#
# O balde único é DELIBERADO (o modelo é o mesmo e o orçamento por pessoa é um
# só), mas desde que a Home virou a primeira tela após o login ele passou a ser
# consumido sem intenção: quem conversa no globo pela manhã pode achar o assistente
# do editor esgotado à tarde sem nunca o ter aberto. Separar as chaves aqui
# resolveria a surpresa e dobraria o gasto máximo por pessoa — decisão de
# produto, não de código. O medidor das duas superfícies (`uso-da-cota.tsx`, que
# lê `GET /assistente/estado` e `GET /assistente/estado`, ambos nesta mesma chave)
# mostra só gasto, teto e prazo: dizer ali que o orçamento é único foi tentado
# e retirado — é ruído para quem lê um medidor. O fato fica registrado em
# docs/assistente.md, "Limites conhecidos".
def chave_de_tokens(user_id: str) -> str:
    return f"assistente:tokens:{user_id}"


async def gasto_e_prazo(redis, user_id: str) -> tuple[int, int | None]:
    """Quanto já foi gasto na janela e em quantos segundos ela reabre. Nunca levanta.

    É o que `GET /assistente/editor/estado` mostra sem recusar nada — e o que o
    `GET /assistente/estado` do assistente vai ler. Vive aqui, junto do resto da
    contabilidade de tokens, para as duas rotas lerem a MESMA fonte em vez de
    cada uma reimplementar a leitura da chave.
    """
    if redis is None:
        return (0, None)
    chave = chave_de_tokens(user_id)
    try:
        cru = await redis.get(chave)
        # Chave antiga sem prazo (a cobrança de antes de `contar_na_janela`
        # fazia INCRBY e EXPIRE em dois comandos, e o segundo podia se perder):
        # o NX dá a ela a janela e não mexe numa chave com prazo. Tem de ser
        # aqui, e não só na recusa: com a cota cheia, a interface lê este
        # estado e trava o envio, a recusa nunca roda, e a chave nunca expiraria.
        if cru is not None:
            await redis.expire(chave, JANELA_DO_ASSISTENTE_SEGUNDOS, nx=True)
        ttl = await redis.ttl(chave)
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao ler a cota do assistente: %s", exc.__class__.__name__)
        return (0, None)
    try:
        gasto = int(cru) if cru is not None else 0
    except (TypeError, ValueError):  # pragma: no cover - valor corrompido
        gasto = 0
    return (gasto, int(ttl) if isinstance(ttl, int) and ttl > 0 else None)


async def _quanto_falta(redis, chave: str) -> int:
    """TTL da janela, para a recusa dizer quando reabre. Nunca levanta.

    O `EXPIRE ... NX` antes de ler só age numa chave SEM prazo — uma que a
    cobrança de antes de `contar_na_janela` (INCRBY e EXPIRE em dois comandos)
    deixou imortal. É na recusa que isso importa: recusado, o turno não chega à
    cobrança, que é quem arma o prazo, e quem cruzou o teto com uma chave dessas
    nunca mais teria o assistente. Numa chave com prazo, o NX não mexe em nada.
    """
    try:
        await redis.expire(chave, JANELA_DO_ASSISTENTE_SEGUNDOS, nx=True)
        ttl = await redis.ttl(chave)
    except Exception:  # pragma: no cover - depende do Redis
        return JANELA_DO_ASSISTENTE_SEGUNDOS
    return int(ttl) if isinstance(ttl, int) and ttl > 0 else JANELA_DO_ASSISTENTE_SEGUNDOS


@asynccontextmanager
async def espera(redis, token_id: str, ttl_s: int) -> AsyncIterator[None]:
    """Reserva uma das esperas simultâneas — e devolve sempre, mesmo com erro.

    O TTL das chaves é `ttl_s + 60`: se um worker morrer no meio da espera, o
    contador se conserta sozinho um minuto depois do prazo máximo da execução,
    em vez de deixar o teto travado para o token até alguém perceber.

    A reserva são dois `INCR` em chaves diferentes, e uma falha entre eles não
    pode deixar a primeira pendurada: o que foi de fato incrementado é anotado
    e devolvido no tratamento do erro. Sem isso, um Redis que cai no meio da
    reserva consumiria uma vaga do token a cada tentativa até o TTL expirar.
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
    except Exception as exc:  # pragma: no cover - depende do Redis
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
    """Solta a reserva. Nunca levanta: falhar aqui só faria perder o resultado."""
    for chave in chaves:
        try:
            await redis.decr(chave)
        except Exception as exc:  # pragma: no cover - depende do Redis
            logger.warning("Falha ao devolver a espera de %s: %s", chave, exc.__class__.__name__)


@asynccontextmanager
async def _espera_local(token_id: str) -> AsyncIterator[None]:
    """Teto por processo, usado só quando não há Redis."""
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
