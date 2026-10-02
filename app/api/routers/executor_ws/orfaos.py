# app/api/routers/executor_ws/orfaos.py
"""
Runs órfãos: fechar como executor_lost quando o executor some e o
watchdog periódico que cobre janelas de queda do servidor.
"""
import asyncio
import time

from app.core.utils.logger import get_logger

from sqlalchemy import select

from app.core.executor_connections import executor_registry
from app.core.db import get_session_async

logger = get_logger(__name__)


# Carência antes de considerar que um executor que desconectou realmente sumiu.
# Ver `_fail_orphan_runs_if_gone`.
_DISCONNECT_GRACE_SECONDS = 20

# Referências fortes para as tasks de verificação pós-desconexão (asyncio só
# guarda weakrefs; sem isso a task pode sumir no meio do grace period).
_orphan_check_tasks: set[asyncio.Task] = set()

async def _fail_orphan_runs_if_gone(executor_id: str) -> None:
    """Falha os runs órfãos APENAS se o executor tiver realmente sumido.

    O `finally` do handler roda em TODA queda de socket, inclusive num blip de
    rede de 1 segundo. A fila local do executor é independente da conexão: ele
    continua executando os jobs e reconecta em seguida — mas os N runs já teriam
    sido marcados 'failed', e o `job_result` verdadeiro seria descartado depois
    pela checagem de idempotência do `_handle_job_result`. Um blip destruía 20
    workflows vivos de uma vez.

    Por isso esperamos um grace period e só falhamos se, passado ele, o executor
    não estiver registrado neste worker (reconexão local) NEM tiver presença no
    Redis (reconexão em outro worker uvicorn) — a mesma checagem que o
    `orphan_runs_watchdog` faz, e que continua sendo a rede de segurança para o
    caso de o próprio worker morrer sem rodar o `finally`.

    A consulta de presença é TRI-ESTADO. `_redis_check_presence` é fail-closed
    (erro de Redis = offline), o que está certo para dispatch mas é destrutivo
    aqui: um blip do pool no instante exato da checagem falharia justamente os
    runs que esta carência existe para salvar. "Não sei" não é "sumiu" — nesse
    caso não fazemos nada e o watchdog reavalia em ≤180s.
    """
    from app.core.executor_connections import _redis_presence_or_unknown

    # CancelledError (shutdown do worker) propaga de propósito: nesse cenário
    # não queremos falhar run nenhum — o watchdog resolve depois.
    await asyncio.sleep(_DISCONNECT_GRACE_SECONDS)

    if executor_registry.get(executor_id) is not None:
        logger.info(
            "Executor '%s' reconectou dentro da carência — runs em voo preservados.",
            executor_id,
        )
        return
    presence = await _redis_presence_or_unknown(executor_id)
    if presence is True:
        logger.info(
            "Executor '%s' com presença no Redis (reconectou em outro worker) — "
            "runs em voo preservados.",
            executor_id,
        )
        return
    if presence is None:
        logger.warning(
            "Executor '%s': não foi possível consultar a presença no Redis após a "
            "carência — runs em voo PRESERVADOS por precaução; o watchdog reavalia "
            "em até %ds.",
            executor_id, _ORPHAN_WATCHDOG_INTERVAL,
        )
        return

    try:
        await _fail_orphan_runs(executor_id)
    except Exception as exc:
        # A task é detached: sem este log a exceção só apareceria como
        # "Task exception was never retrieved" no shutdown.
        logger.error(
            "Falha ao limpar runs órfãos do executor '%s' pós-desconexão: %s",
            executor_id, exc,
        )

async def _fail_orphan_runs(executor_id: str) -> None:
    """
    Ao desconectar, marca como 'failed' todos os WorkflowRun com status='running'
    atribuídos a este executor (host = 'executor:{executor_id}').

    O fechamento é o de todo run fechado pelo servidor (`fechar_runs`): UPDATE
    condicional por run — o consumer pode gravar o resultado verdadeiro entre o
    SELECT e o commit, e ele vence —, contabilização no usage_daily (este
    caminho nunca passa pela fila run_results) e `__workflow_complete__` com
    status=failed, para que o frontend feche o WebSocket de log e exiba o erro.
    """
    from app.models.models import WorkflowRun as _WFRun
    from app.services.fechamento_de_run import REPETIVEL, fechar_runs

    host_key = f"executor:{executor_id}"

    try:
        async with get_session_async() as db:
            result = await db.execute(
                select(_WFRun).where(
                    _WFRun.host == host_key,
                    _WFRun.status == "running",
                )
            )
            candidatos = result.scalars().all()

            if not candidatos:
                return

            # `executor_lost` vale para os dois caminhos que chegam aqui — o
            # finally do WS e o watchdog de presence. O evento publicado
            # continua "transient" (taxonomia do flow, para o painel de log
            # oferecer retry); a coluna guarda a causa vista pelo servidor.
            orphans = await fechar_runs(
                db, candidatos, de=("running",), para="failed",
                mensagem="Executor desconectou durante a execução.",
                categoria="executor_lost", host=host_key, duracao=True, extra=REPETIVEL,
            )
        if orphans:
            logger.warning(
                "Executor '%s' desconectou com %d run(s) em execução — marcados como failed.",
                executor_id, len(orphans),
            )

    except Exception as exc:
        logger.error("Erro ao limpar runs órfãos do executor '%s': %s", executor_id, exc)


# ── Runs em 'pending' que nenhum executor recebeu ────────────────────────────

# Idade a partir da qual um run em 'pending' não está mais sendo despachado. O
# despacho leva milissegundos, o envio ao executor tem prazo (ver
# `_prazo_de_envio` em executor_connections) e o ACK do executor promove o run
# para 'running' assim que o job chega. Um 'pending' desta idade é de um worker
# que morreu no meio do envio — e ninguém mais o fecharia: o watchdog de órfãos
# só olha 'running', e o run ficava "Na fila" para sempre (caso de 22/09).
_PENDING_SEM_ENTREGA_SECONDS = 600

# Teto por varredura: um incidente com milhares de runs presos é drenado em
# lotes, um a cada ciclo do watchdog, sem uma transação gigante.
_PENDING_LOTE = 200

_MSG_NAO_ENTREGUE = (
    "O servidor foi interrompido enquanto enviava esta execução ao executor, e "
    "nenhum executor confirmou o recebimento — ela não chegou a rodar."
)

# Executor anterior ao inventário não tem como promover um job cujo ACK se
# perdeu junto com o worker que o despachou (o worker morto derruba também a
# conexão direta dele). Para os runs de um executor ONLINE que não manda
# inventário, a varredura espera o teto de duração de um job (1 h por padrão,
# mais a fila) antes de concluir que o envio não chegou — senão fecharia, e
# mandaria cancelar, um job saudável.
_PENDING_SEM_INVENTARIO_SECONDS = 6 * 3600
# "Este executor manda inventário": renovada a cada inventário recebido.
_TTL_MARCA_DE_INVENTARIO_S = 180


def _chave_de_inventario(executor_id: str) -> str:
    return f"executor:{executor_id}:inventario"


async def _hosts_sem_inventario(hosts) -> set[str]:
    """Dos hosts dados (`executor:{id}`), os que podem ter o job sem ter como
    dizer: online — ou com presença desconhecida, porque a decisão é destrutiva
    — e sem inventário recente."""
    from app.core.executor_connections import _redis_presence_or_unknown
    from app.core.redis import get_redis_pool

    esperar: set[str] = set()
    for host in hosts:
        if not host or not host.startswith("executor:"):
            continue
        executor_id = host[len("executor:"):]
        if await _redis_presence_or_unknown(executor_id) is False:
            continue
        try:
            fala_inventario = bool(await get_redis_pool().exists(_chave_de_inventario(executor_id)))
        except Exception:
            fala_inventario = False
        if not fala_inventario:
            esperar.add(host)
    return esperar


async def _fechar_runs_nao_entregues() -> int:
    """Fecha como 'failed' os runs presos em 'pending' além do prazo. Devolve
    quantos fechou.

    O fechamento é condicional (`status='pending'`, ver `fechar_runs`), então
    os 4 workers podem varrer ao mesmo tempo: cada run é fechado — e
    contabilizado — por um só. O host gravado recebe um 'cancel' mesmo assim: se
    o job tiver chegado sem ACK, o executor o interrompe; se não, responde que
    não o conhece.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import and_, or_

    from app.models.models import WorkflowRun as _WFRun
    from app.services.fechamento_de_run import REPETIVEL, fechar_runs

    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(seconds=_PENDING_SEM_ENTREGA_SECONDS)
    async with get_session_async() as db:
        # Os hosts antes dos runs: filtrar depois do LIMIT deixaria o lote
        # cheio de runs que esperam, e os outros nunca seriam varridos.
        hosts = (await db.execute(
            select(_WFRun.host)
            .where(_WFRun.status == "pending", _WFRun.start_time < corte)
            .distinct()
        )).scalars().all()
        esperar = await _hosts_sem_inventario(hosts)
        prazo = _WFRun.start_time < corte
        if esperar:
            corte_sem_inventario = agora - timedelta(seconds=_PENDING_SEM_INVENTARIO_SECONDS)
            prazo = or_(
                and_(prazo, or_(_WFRun.host.is_(None), _WFRun.host.notin_(sorted(esperar)))),
                _WFRun.start_time < corte_sem_inventario,
            )
        result = await db.execute(
            select(_WFRun)
            .where(_WFRun.status == "pending", prazo)
            .order_by(_WFRun.start_time)
            .limit(_PENDING_LOTE)
        )
        fechados = await fechar_runs(
            db, result.scalars().all(), de=("pending",), para="failed",
            mensagem=_MSG_NAO_ENTREGUE, categoria="dispatch", extra=REPETIVEL,
        )

    if not fechados:
        return 0
    logger.warning(
        "%d run(s) preso(s) em 'pending' há mais de %ds sem confirmação de entrega "
        "— fechados como failed: %s",
        len(fechados), _PENDING_SEM_ENTREGA_SECONDS,
        [run.task_id for run in fechados[:20]],
    )
    for run in fechados:
        host = run.host or ""
        if not host.startswith("executor:"):
            continue
        try:
            await executor_registry.send_json(
                host[len("executor:"):], {"type": "cancel", "job_id": run.task_id},
            )
        except Exception as exc:
            logger.debug("Cancel do run não entregue '%s' não enviado: %s", run.task_id, exc)
    return len(fechados)

_MSG_RELAY_NAO_ENTREGUE = (
    "O executor ainda estava recebendo um envio anterior e esta execução não "
    "chegou a ele — ela não rodou. Tente de novo."
)
_MSG_CONEXAO_FECHANDO = (
    "A conexão com o executor estava sendo encerrada e esta execução não "
    "chegou a ele — ela não rodou. Tente de novo."
)


async def fechar_run_nao_entregue(
    executor_id: str, task_id: str, *, conexao_fechando: bool = False,
) -> bool:
    """Fecha como failed/dispatch o run cujo job COMPROVADAMENTE não foi escrito
    no socket do executor — o relay o descartou sem a vez, ou (`conexao_fechando`)
    porque o socket estava fechando. Devolve se fechou.

    O worker que publicou no relay já tinha dado o job por entregue; sem este
    fechamento o run ficava "Em andamento" até o ACK pendente vencer (10 min) e
    só então falhava como perdido. Condicional em status e host, como os outros
    fechamentos do servidor (`fechar_runs`).
    """
    from app.services.fechamento_de_run import ABERTOS, REPETIVEL, fechar_runs

    mensagem = _MSG_CONEXAO_FECHANDO if conexao_fechando else _MSG_RELAY_NAO_ENTREGUE
    async with get_session_async() as db:
        fechados = await fechar_runs(
            db, [task_id], de=ABERTOS, para="failed", mensagem=mensagem,
            categoria="dispatch", host=f"executor:{executor_id}", extra=REPETIVEL,
        )
    if not fechados:
        return False
    try:
        await executor_registry.clear_pending_ack(task_id, expected_executor_id=executor_id)
    except Exception as exc:
        logger.debug("ACK pendente do run '%s' não limpo: %s", task_id, exc)
    logger.warning(
        "Run '%s' fechado: o job relayado ao executor '%s' não foi escrito (%s).",
        task_id, executor_id, "conexão fechando" if conexao_fechando else "sem a vez",
    )
    return True


# ── Watchdog periodico de runs orfaos ────────────────────────────────────────

# Intervalo entre varreduras. Alinha com _PRESENCE_TTL=120s do registry —
# pequenas latencias de rede podem levar um heartbeat legitimo a chegar
# no limite; 180s da folga confortavel sem deixar orfaos vivos por horas.
_ORPHAN_WATCHDOG_INTERVAL = 180

async def orphan_runs_watchdog() -> None:
    """Task de background que enumera runs 'running' cujo executor NAO tem
    presence no Redis. Chama `_fail_orphan_runs` para cada.

    Motivacao: o `_fail_orphan_runs` do handler WS so roda no `finally`
    do `agent_websocket`. Se o worker uvicorn morre (SIGKILL/OOM/crash),
    o finally nunca executa — runs ficam com status='running' para
    sempre, apesar de presence expirar em 120s.

    Este watchdog e a rede de seguranca.
    """
    import asyncio
    import re
    from app.models.models import WorkflowRun as _WFRun
    from app.core.executor_connections import _redis_presence_or_unknown

    # Aceita hash UUID-like (com hifens) e antigos (sem hifens) — evita
    # matchar valores garbage residuais.
    _HOST_RE = re.compile(r"^executor:([A-Fa-f0-9\-]{8,})$")

    logger.info("Watchdog de runs orfaos iniciado (intervalo %ds).", _ORPHAN_WATCHDOG_INTERVAL)

    while True:
        try:
            await asyncio.sleep(_ORPHAN_WATCHDOG_INTERVAL)

            # Antes dos órfãos em 'running': é independente de presença, e um
            # erro aqui não pode impedir a varredura de baixo.
            try:
                await _fechar_runs_nao_entregues()
            except Exception as exc:
                logger.error("Watchdog: falha ao fechar runs não entregues: %s", exc)

            async with get_session_async() as db:
                result = await db.execute(
                    select(_WFRun.host).where(
                        _WFRun.status == "running",
                        _WFRun.host.like("executor:%"),
                    ).distinct()
                )
                hosts = [row[0] for row in result.all() if row[0]]

            candidates: set[str] = set()
            for host in hosts:
                m = _HOST_RE.match(host)
                if m:
                    candidates.add(m.group(1))

            if not candidates:
                continue

            offline: list[str] = []
            for executor_id in candidates:
                # Tri-estado: se o worker morreu e nao renovou o TTL, a chave
                # sumiu de fato (False). None e "nao consegui perguntar" — nesse
                # caso NAO falhamos os runs; o proximo ciclo reavalia. Colapsar
                # os dois em "offline" faria um blip do Redis destruir runs vivos.
                presence = await _redis_presence_or_unknown(executor_id)
                if presence is False:
                    offline.append(executor_id)
                elif presence is None:
                    logger.warning(
                        "Watchdog: presence de '%s' indisponivel (Redis) — runs "
                        "preservados, reavalia no proximo ciclo.",
                        executor_id,
                    )

            if not offline:
                continue

            logger.warning(
                "Watchdog detectou %d executor(es) sem presence com runs 'running': %s. "
                "Marcando como failed.",
                len(offline), sorted(offline),
            )
            for executor_id in offline:
                try:
                    await _fail_orphan_runs(executor_id)
                except Exception as exc:
                    logger.error(
                        "Watchdog: falha ao limpar orfaos de '%s': %s",
                        executor_id, exc,
                    )
        except asyncio.CancelledError:
            logger.info("Watchdog de runs orfaos encerrado.")
            raise
        except Exception as exc:
            # Nao deixa loop morrer por erro pontual. Backoff curto.
            logger.error("Erro no watchdog de runs orfaos: %s", exc)
            await asyncio.sleep(30)


# ── Reconciliação pelo inventário do executor ────────────────────────────────
# O executor manda, ao conectar e a cada minuto, os jobs que TEM: `ativos` (na
# fila, no semáforo ou rodando) e `resultados` (terminaram, resultado ainda não
# confirmado). Antes o servidor só descobria um run perdido quando o executor
# DESCONECTAVA — em 22/09 o titan seguiu conectado com três runs que nunca
# recebeu, e eles ficaram "Em andamento" até 09:16, para então virarem um
# "Executor desconectou durante a execução" que culpava quem não tinha culpa.
#
# Três ações por inventário:
#   1. promove para 'running' os 'pending' que o executor tem (ACK perdido);
#   2. manda 'cancel' ao que ele segue rodando mas o servidor já fechou;
#   3. fecha os runs dele que ele NÃO tem, com mais de 3 min de idade e sem
#      resultado recém-chegado ao servidor.

# Idade mínima para um run ser julgado perdido por não estar no inventário.
# Acima do prazo máximo de envio (~62 s para um frame de 16 MB), com folga: um
# job ainda em trânsito quando o executor montou o inventário não é perda.
_RECONCILIACAO_IDADE_MIN_S = 180

# Intervalo mínimo entre duas reconciliações do mesmo executor. O executor
# honesto manda um inventário por minuto; um com bug (ou hostil) não transforma
# o inventário num SELECT por mensagem.
_RECONCILIACAO_INTERVALO_S = 30

# Carência depois de uma conexão nova antes de fechar algo por AUSÊNCIA. O
# inbox da conexão ANTERIOR pode ainda estar drenando (flush de 10 s + carência
# + resgate, ~20 s) um job_result que saiu antes da queda: o primeiro inventário
# da sessão nova não o lista, e fechar o run agora faria o resultado verdadeiro
# ser recusado logo depois. Promover e parar zumbis não esperam.
_RECONCILIACAO_CARENCIA_DA_CONEXAO_S = 45

_INVENTARIO_MAX_IDS = 2000
_JOB_ID_MAX_CHARS = 64

_MSG_PERDIDO = (
    "O executor não tinha mais esta execução quando o servidor conferiu com ele — "
    "ela se perdeu entre o servidor e o executor (queda da conexão, do servidor "
    "ou do próprio executor)."
)


def _ids_do_inventario(valor) -> set[str] | None:
    """Ids válidos de uma lista do inventário; None se a lista é malformada."""
    if valor is None:
        return set()
    if not isinstance(valor, list) or len(valor) > _INVENTARIO_MAX_IDS:
        return None
    return {v for v in valor if isinstance(v, str) and 0 < len(v) <= _JOB_ID_MAX_CHARS}


async def _reconciliar_inventario(executor_id: str, msg: dict) -> dict:
    """Confere os runs deste executor contra o que ele diz ter. Devolve as
    contagens (para log e teste); {} quando não reconciliou.

    SEG: tudo é restrito aos runs com `host` deste executor. Um inventário
    mentiroso só afeta runs do próprio executor — que já controla o desfecho
    deles pelo job_result de qualquer forma.
    """
    from app.core.redis import get_redis_pool

    from .resultados import _promover_para_running

    # Marca que este executor fala inventário — a varredura dos 'pending' trata
    # diferente quem não fala (ver `_PENDING_SEM_INVENTARIO_SECONDS`).
    try:
        await get_redis_pool().setex(
            _chave_de_inventario(executor_id), _TTL_MARCA_DE_INVENTARIO_S, "1",
        )
    except Exception as exc:
        logger.debug("Marca de inventário do executor '%s' não gravada: %s", executor_id, exc)

    conn = executor_registry.get(executor_id)
    if conn is not None:
        agora_mono = time.monotonic()
        if agora_mono - conn.ultima_reconciliacao < _RECONCILIACAO_INTERVALO_S:
            return {}
        conn.ultima_reconciliacao = agora_mono

    ativos = _ids_do_inventario(msg.get("ativos"))
    resultados = _ids_do_inventario(msg.get("resultados"))
    if ativos is None or resultados is None:
        logger.warning("Executor '%s' mandou inventário malformado — ignorado.", executor_id)
        return {}

    promovidos = await _promover_para_running(executor_id, ativos) if ativos else 0
    parados = await _parar_zumbis(executor_id, ativos) if ativos else 0
    # Truncado: não dá para saber o que ficou de fora, então nada é fechado por
    # ausência — promover e parar continuam valendo para o que veio. Idem logo
    # depois de conectar (ver `_RECONCILIACAO_CARENCIA_DA_CONEXAO_S`).
    if msg.get("truncado") or _conexao_recente(conn):
        fechados = 0
    else:
        fechados = await _fechar_perdidos(executor_id, ativos | resultados)
    return {"promovidos": promovidos, "parados": parados, "fechados": fechados}


def _conexao_recente(conn) -> bool:
    from datetime import datetime, timezone

    if conn is None:
        return False
    idade = (datetime.now(timezone.utc) - conn.connected_at).total_seconds()
    return idade < _RECONCILIACAO_CARENCIA_DA_CONEXAO_S


# Referências fortes aos cancels em segundo plano (asyncio só guarda weakrefs).
_cancels_em_curso: set[asyncio.Task] = set()


def _cancelar_em_segundo_plano(executor_id: str, task_ids: list[str], rotulo: str) -> None:
    """Manda `cancel` para cada job sem prender quem chamou: a reconciliação
    roda na drenadora da conexão, e com o socket congestionado cada envio pode
    esperar a vez por até o prazo inteiro — atrasando os job_results dela."""
    if not task_ids:
        return

    async def _mandar():
        for task_id in task_ids:
            try:
                await executor_registry.send_json(executor_id, {"type": "cancel", "job_id": task_id})
            except Exception as exc:
                logger.debug("Cancel do %s '%s' não enviado: %s", rotulo, task_id, exc)

    task = asyncio.create_task(_mandar(), name=f"cancel-{rotulo}-{executor_id[:8]}")
    _cancels_em_curso.add(task)
    task.add_done_callback(_cancels_em_curso.discard)


async def _parar_zumbis(executor_id: str, ativos: set[str]) -> int:
    """'cancel' para o que o executor segue rodando mas o servidor já fechou
    (cancelado com o executor fora do ar, falho por desconexão, não entregue).
    O resultado desses runs seria recusado de qualquer jeito — rodar até o fim
    só gastaria a máquina e produziria efeitos que ninguém espera."""
    from app.models.models import WorkflowRun as _WFRun

    async with get_session_async() as db:
        result = await db.execute(
            select(_WFRun.task_id).where(
                _WFRun.task_id.in_(sorted(ativos)),
                _WFRun.host == f"executor:{executor_id}",
                _WFRun.status.in_(("cancelled", "failed")),
            )
        )
        zumbis = [row[0] for row in result.all()]
    _cancelar_em_segundo_plano(executor_id, zumbis, "zumbi")
    if zumbis:
        logger.warning(
            "Executor '%s' ainda rodava %d job(s) que o servidor já fechou — cancel enviado: %s",
            executor_id, len(zumbis), zumbis[:20],
        )
    return len(zumbis)


async def _fechar_perdidos(executor_id: str, tem: set[str]) -> int:
    """Fecha os runs deste executor que ele não tem. Devolve quantos fechou."""
    from datetime import datetime, timedelta, timezone

    from app.core.redis import get_redis_pool
    from app.models.models import WorkflowRun as _WFRun
    from app.services.fechamento_de_run import REPETIVEL, fechar_runs

    host = f"executor:{executor_id}"
    corte = datetime.now(timezone.utc) - timedelta(seconds=_RECONCILIACAO_IDADE_MIN_S)
    async with get_session_async() as db:
        result = await db.execute(
            select(_WFRun.task_id, _WFRun.status).where(
                _WFRun.host == host,
                _WFRun.status.in_(("pending", "running")),
                _WFRun.start_time < corte,
            )
        )
        candidatos = [(tid, st) for tid, st in result.all() if tid not in tem]
    if not candidatos:
        return 0

    # Dois motivos para não estar no inventário sem estar perdido, ambos no
    # Redis: o resultado acabou de chegar (`_handle_job_result` grava a chave de
    # resultado, TTL 300 s, antes de mandá-lo ao consumer), ou o job ainda está
    # a caminho — um envio que estourou o prazo segue escoando pelo socket por
    # tempo indefinido, e o ACK pendente (TTL 600 s) é a marca disso. Sem Redis
    # não há como saber: não fecha nada.
    from app.core.executor_connections import _pending_ack_key

    try:
        chaves = [f"executor:{executor_id}:results:{tid}" for tid, _ in candidatos]
        chaves += [_pending_ack_key(tid) for tid, _ in candidatos]
        valores = await get_redis_pool().mget(chaves)
    except Exception as exc:
        logger.warning(
            "Reconciliação de '%s' adiada: Redis indisponível para conferir resultados (%s).",
            executor_id, exc,
        )
        return 0
    n = len(candidatos)
    candidatos = [
        c for c, chegou, a_caminho in zip(candidatos, valores[:n], valores[n:])
        if chegou is None and a_caminho is None
    ]
    if not candidatos:
        return 0

    async with get_session_async() as db:
        # 'pending' que o executor não tem nunca chegou a ele: é o mesmo caso da
        # varredura dos não entregues, só detectado mais cedo. Cada grupo fecha
        # só se ainda estiver no status em que foi lido.
        fechados = await fechar_runs(
            db, [tid for tid, st in candidatos if st == "pending"], de=("pending",),
            para="failed", mensagem=_MSG_NAO_ENTREGUE, categoria="dispatch", host=host,
            extra=REPETIVEL,
        )
        fechados += await fechar_runs(
            db, [tid for tid, st in candidatos if st == "running"], de=("running",),
            para="failed", mensagem=_MSG_PERDIDO, categoria="executor_lost", host=host,
            extra=REPETIVEL,
        )

    if not fechados:
        return 0
    logger.warning(
        "Executor '%s' não tinha %d run(s) que o servidor dava como em andamento — "
        "fechados como failed: %s",
        executor_id, len(fechados), [run.task_id for run in fechados[:20]],
    )
    # Se o job ainda chegar (um frame que escoava além do ACK pendente), o cancel
    # chega DEPOIS dele pelo mesmo socket e o interrompe — ou vira lápide, se o
    # job nunca vier. Sem isso ele rodaria, com efeitos, para um run já fechado.
    _cancelar_em_segundo_plano(executor_id, [run.task_id for run in fechados], "perdido")
    return len(fechados)

