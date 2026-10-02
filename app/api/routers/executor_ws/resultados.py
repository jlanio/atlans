# app/api/routers/executor_ws/resultados.py
"""
Resultados e eventos de run: autorização run→executor, gravação do
job_result, publicação de node_events e eventos de sync.
"""
import asyncio
import json
import time
from dataclasses import dataclass

from app.core.utils.logger import get_logger

from sqlalchemy import select

from app.core.executor_connections import executor_registry
from app.core.constants import REDIS_TTL_1H
from app.core.db import get_session_async
# Dono das chaves do histórico/canal, do pipeline que grava eventos e do JSON
# do `__workflow_complete__`. Pelo módulo, como em `fechamento_de_run`.
from app.services import run_events_service
from flow.utils.protocolo_ws import (
    STATS_CONTROLE_DESCARTADO,
    STATS_TAMANHO_ORIGINAL,
    STATS_TRUNCADO,
)
from flow.utils.publisher.reducao import (
    TETO_NODE_EVENT_BYTES,
    TETO_POR_CAMPO,
    reduzir_node_event,
)

logger = get_logger(__name__)

from .protocolo import (
    _JOB_RESULT_RATE_LIMIT,
    _MAX_SYNC_EVENT_BYTES,
    _RATE_WINDOW,
    _cap_job_result,
    _coerce_gauge,
    _rate_allowed,
)

def _desfecho(job_status: str, is_cancelled: bool, *, ok: str) -> str:
    """Traduz o desfecho de um job para o vocabulario de quem le.

    A queda (`cancelled` antes de `failed`) e a mesma nos dois consumidores e
    estava copiada em dois pontos deste arquivo; a diferenca real e so o nome do
    caso de sucesso — a linha de `WorkflowRun` diz "success", o evento de ciclo
    de vida do painel diz "completed" —, por isso ele e parametro explicito e
    nao um default.

    A ORDEM importa: um job cancelado chega com status != "ok", e testar
    `is_cancelled` depois de "ok" e antes de "failed" e o que impede um
    cancelamento de ser reportado como falha ao usuario.
    """
    if job_status == "ok":
        return ok
    return "cancelled" if is_cancelled else "failed"

# TTLs do memo de autorização run→executor (ver _run_belongs_to_agent).
# Positivo é longo porque o vínculo run→host é IMUTÁVEL depois do dispatch;
# negativo é curto para que um executor malicioso em loop não gere um SELECT
# por tentativa e, ao mesmo tempo, um vínculo criado logo depois seja visto.
_RUN_AUTH_TTL_OK = 3600.0

_RUN_AUTH_TTL_DENY = 5.0

_RUN_AUTH_CACHE_MAX = 2048

# Teto de espera da query de autorização. Esperar POOL_TIMEOUT (30s) por uma
# conexão do pool no caminho quente do WS nunca é a resposta certa: o loop de
# recepção fica parado, o heartbeat não é lido e o servidor derruba um executor
# saudável por timeout — e aí `_fail_orphan_runs` mata runs que estavam vivos.
_RUN_AUTH_QUERY_TIMEOUT = 3.0

# Circuit breaker de banco degradado. O veredito `None` (falha de DB) não é
# memorizado de propósito — é transitório —, mas sem nenhuma trava cada
# node_event de uma rajada abria sessão nova e podia esperar o pool inteiro.
# Durante o cooldown negamos na hora, custo zero: o mesmo veredito de hoje.
#
# Vale SÓ para node_event. O job_result ignora o cooldown (ver
# `_handle_job_result`): ele é dado de negócio, não é reenviado pelo executor e
# sua perda pendura o run — não pode ser vítima de uma trava criada para conter
# telemetria.
_RUN_AUTH_DB_COOLDOWN = 2.0

# Retentativas da leitura do run no caminho do job_result. Cobre o failover
# curto (pgbouncer reiniciando, réplica trocando) sem transformar a drenadora
# numa fila de esperas longas.
_JOB_RESULT_DB_RETRIES = 3

_JOB_RESULT_DB_RETRY_DELAY = 0.25

# Acima deste tamanho de frame, as serializações do job_result vão para uma
# thread: um `stats` de MB congelava o event loop do worker INTEIRO (outros
# executores paravam de ser lidos, requests HTTP em voo travavam) por dezenas de
# ms. Abaixo dele, o overhead do to_thread seria maior que o próprio dumps.
_JSON_OFFLOAD_THRESHOLD = 256 * 1024

async def _dumps(obj, *, offload: bool) -> str:
    """json.dumps que sai do event loop quando o payload é grande.

    Um `stats` de MB serializado inline parava TODO o worker — outros
    executores deixavam de ser lidos e requests HTTP em voo travavam junto. Para
    payload pequeno o custo do to_thread seria maior que o do próprio dumps, daí
    o interruptor explícito em vez de uma heurística interna.
    """
    if offload:
        return await asyncio.to_thread(json.dumps, obj)
    return json.dumps(obj)

async def _register_webhook_response_artifact(run_id: str, executor_id: str, body_ref: dict) -> None:
    """Cria linha Artifact para body de webhook guardado no MinIO, com expires_at
    baseado em artifact_retention_days (mesma política dos demais artefatos).

    O cleanup global (app/core/artifact_cleanup.py) remove o objeto do MinIO e
    a linha do DB quando expires_at é atingido. O webhook_router tenta apagar
    imediatamente após streaming; este registro é a rede de segurança para órfãos.
    """
    from datetime import timedelta
    from app.core.run_result_consumer import _get_retention_days
    from app.core.utils.datetime_utils import utc_now_naive
    from app.models.artifact import Artifact
    from app.models.models import WorkflowRun

    s3_key = body_ref.get("s3_key")
    if not s3_key:
        return

    async with get_session_async() as db:
        run_res = await db.execute(
            select(WorkflowRun).where(WorkflowRun.task_id == run_id)
        )
        run = run_res.scalar_one_or_none()
        workspace_id = run.workspace_id if run else None
        workflow_hash = run.workflow_hash if run else None

        if not workspace_id:
            logger.warning("Webhook response sem workspace_id (run=%s) — artifact não registrado.", run_id)
            return

        # A s3_key vem CRUA do executor, que é uma máquina sob controle do
        # usuário. Sem este guard, um executor respondia com
        # `body_ref.s3_key = "drive/<workspace_alheio>/<arquivo>"` e o servidor
        # criava um Artifact — sem credential_id, portanto de download PÚBLICO —
        # apontando para o objeto de outro tenant; o expires_at ainda fazia o
        # purge apagá-lo depois. Mesmo vetor que run_result_consumer já fecha
        # para pins e artefatos de nó; este caminho tinha ficado de fora.
        from fastapi import HTTPException
        from app.api.routers.executor_drive_router import _validate_agent_s3_key
        try:
            _validate_agent_s3_key(s3_key, [workspace_id])
        except HTTPException as exc:
            logger.warning(
                "Webhook response com s3_key rejeitada (%s) do executor %s no run %s: %s",
                exc.detail, executor_id, run_id, s3_key,
            )
            return

        retention_days = await _get_retention_days(db)
        expires_at = (
            utc_now_naive() + timedelta(days=retention_days)
            if retention_days else None
        )

        artifact = Artifact(
            workspace_id=workspace_id,
            workflow_hash=workflow_hash,
            run_id=run_id,
            node_id=None,
            output_key="__webhook_response__",
            filename=s3_key.rsplit("/", 1)[-1],
            format=None,
            size_bytes=body_ref.get("size"),
            s3_key=s3_key,
            executor_id=executor_id,
            expires_at=expires_at,
        )
        db.add(artifact)
        await db.commit()

async def _record_job_ack(executor_id: str, job_id: str | None, status: str) -> None:
    """Confirmação de recebimento: tira o job dos pendentes de ACK e promove o
    run de 'pending' para 'running'.

    Chamado quando o executor envia {type: "ack", job_id, status}. A ausência
    de ACK após send_job é rastreada via executor_registry.overdue_acks().

    A PROMOÇÃO é o que fecha o buraco do run preso em "Na fila": o dispatch só
    grava 'running' depois que `send_job` retorna, então um worker que morre
    nessa janela deixava 'pending' para sempre um job que o executor recebeu e
    está rodando. O ACK é a prova de entrega vinda do outro lado — e chega por
    qualquer worker, inclusive depois da morte de quem despachou. O UPDATE é
    condicional ('pending' e o host deste executor): não ressuscita run
    cancelado nem terminal, e um ACK de outro executor não promove nada.

    SEG: o ACK só limpa jobs despachados para ESTE executor. Sem o vínculo,
    qualquer executor podia confirmar o job de outro e cegar o monitor de
    jobs perdidos.
    """
    if not job_id:
        return
    who = await executor_registry.clear_pending_ack(job_id, expected_executor_id=executor_id)
    if who:
        logger.debug("ACK recebido: job=%s status=%s executor=%s", job_id, status, who)
    # A promoção é um UPDATE + COMMIT no Postgres por ACK: sem teto, um executor
    # com bug (ou hostil) prendia uma conexão do banco em loop. O teto é o do
    # job_result — um ACK por job, muito abaixo disso no tráfego honesto. Um ACK
    # acima dele só perde a promoção; o inventário a faz no minuto seguinte.
    if not _rate_allowed(executor_id, "ack", _JOB_RESULT_RATE_LIMIT):
        return
    try:
        await _promover_para_running(executor_id, job_id)
    except Exception as exc:
        # Best-effort: o dispatch vivo promove sozinho, e a varredura dos não
        # entregues fecha o que ficar para trás.
        logger.warning(
            "ACK do job '%s' (executor '%s'): falha ao promover para 'running': %s",
            job_id, executor_id, exc,
        )


async def _promover_para_running(executor_id: str, job_ids) -> int:
    """'pending' → 'running' para jobs que ESTE executor confirmou ter. Devolve
    quantos runs mudaram.

    Condicional em status e host: um run cancelado, terminal ou despachado para
    outro executor fica como está.
    """
    from sqlalchemy import update as sa_update

    from app.models.models import WorkflowRun

    ids = [job_ids] if isinstance(job_ids, str) else list(job_ids)
    if not ids:
        return 0
    async with get_session_async() as db:
        result = await db.execute(
            sa_update(WorkflowRun)
            .where(
                WorkflowRun.task_id.in_(ids),
                WorkflowRun.status == "pending",
                WorkflowRun.host == f"executor:{executor_id}",
            )
            .values(status="running")
            .execution_options(synchronize_session=False)
        )
        await db.commit()
    if result.rowcount:
        logger.info(
            "Executor '%s' confirmou %d job(s) ainda em 'pending' — promovidos para 'running'.",
            executor_id, result.rowcount,
        )
    return result.rowcount or 0

async def _query_run_belongs_to_agent(executor_id: str, run_id: str) -> bool | None:
    """SELECT que confere WorkflowRun.host == 'executor:{executor_id}'.

    Retorna True/False, ou None quando a consulta em si falhou (erro de DB) —
    o caller trata como negado, mas NÃO memoriza um resultado que veio de uma
    indisponibilidade transitória.

    FAIL-CLOSED: run inexistente ou com host NULL é rejeitado. A versão anterior
    retornava True nesses casos ("benefício da dúvida"), herdado de quando o
    INSERT do run era assíncrono via fila Redis. Como o dispatcher hoje persiste
    run + host de forma síncrona antes de enviar o job, aquele fail-open virou
    pura superfície de ataque: permitia a um executor qualquer reivindicar o run
    de outro tenant durante a janela em que host ainda era NULL.
    """
    from app.models.models import WorkflowRun
    try:
        async with get_session_async() as db:
            result = await db.execute(
                select(WorkflowRun.host).where(WorkflowRun.task_id == run_id)
            )
            host = result.scalar_one_or_none()
            if host is None:
                logger.warning(
                    "WS event auth: run=%s inexistente ou sem host atribuído — "
                    "evento do executor '%s' descartado (fail-closed).",
                    run_id, executor_id,
                )
                return False
            expected = f"executor:{executor_id}"
            ok = host == expected
            if not ok:
                logger.warning(
                    "WS event auth mismatch: run=%s expected_host=%s actual_host=%s "
                    "— node_event será descartado (causa comum de canvas sem feedback).",
                    run_id, expected, host,
                )
            return ok
    except Exception as exc:
        # Em falha de DB, fail-closed para proteger cross-tenant.
        logger.error("Erro ao validar propriedade de run '%s' pelo executor '%s': %s", run_id, executor_id, exc)
        return None

def _store_run_auth(cache: dict, run_id: str, authorized: bool, now: float) -> None:
    """Memoriza o veredito com TTL, mantendo o cache limitado."""
    if len(cache) >= _RUN_AUTH_CACHE_MAX:
        # Um executor malicioso pode inventar run_ids à vontade: purga expirados
        # e, se ainda estiver cheio, descarta as entradas mais próximas de vencer.
        for key, (_ok, deadline) in list(cache.items()):
            if deadline <= now:
                cache.pop(key, None)
        while len(cache) >= _RUN_AUTH_CACHE_MAX:
            cache.pop(min(cache, key=lambda k: cache[k][1]), None)
    ttl = _RUN_AUTH_TTL_OK if authorized else _RUN_AUTH_TTL_DENY
    cache[run_id] = (authorized, now + ttl)

async def _run_belongs_to_agent(executor_id: str, run_id: str) -> bool:
    """Valida que o WorkflowRun pertence ao executor_id que está reportando.

    Previne cross-tenant injection: um executor comprometido não pode manipular
    runs de outro tenant/workspace enviando job_result ou node_event com
    run_id arbitrário. O dispatcher seta WorkflowRun.host = f"executor:{executor_id}"
    ANTES do send_job, então a autoria é sempre verificável.

    PERF: o veredito é memorizado NA CONEXÃO do executor. Antes havia sessão +
    SELECT + teardown POR EVENTO para revalidar um vínculo run→host que é
    IMUTÁVEL depois do dispatch — com POOL_PRE_PING são ~2 round-trips por
    evento, então um workflow de 100 nós custava 400-600 round-trips e 200-300
    checkouts do pool, SERIALIZADOS no loop de recepção (job_result e heartbeat
    ficavam na fila atrás dos eventos).

    O memo NÃO é um bypass: ele só guarda o resultado de uma verificação já
    feita para AQUELE PAR (executor_id, run_id) — vive dentro do
    `ExecutorConnection`, portanto nunca cruza executores e desaparece no
    unregister. Vereditos NEGATIVOS também são memorizados (TTL curto) para que
    um executor malicioso em loop não gere um SELECT por tentativa.
    """
    conn = executor_registry.get(executor_id)
    cache = conn.run_auth_cache if conn is not None else None
    now = time.monotonic()

    if cache is not None:
        memo = cache.get(run_id)
        if memo is not None and memo[1] > now:
            return memo[0]

    # Banco degradado: nega sem abrir sessão. Ver `_RUN_AUTH_DB_COOLDOWN`.
    if conn is not None and conn.db_auth_cooldown_until > now:
        return False

    try:
        verdict = await asyncio.wait_for(
            _query_run_belongs_to_agent(executor_id, run_id), _RUN_AUTH_QUERY_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            "Autorização do run '%s' (executor '%s') não respondeu em %.1fs — "
            "evento descartado (fail-closed).",
            run_id, executor_id, _RUN_AUTH_QUERY_TIMEOUT,
        )
        verdict = None
    if verdict is None:
        # Erro/timeout de DB: nega agora e abre o cooldown para que a rajada
        # seguinte não vire N tentativas de checkout do pool.
        if conn is not None:
            conn.db_auth_cooldown_until = now + _RUN_AUTH_DB_COOLDOWN
        return False
    if cache is not None:
        _store_run_auth(cache, run_id, verdict, now)
    return verdict

def _forget_run_auth(executor_id: str, run_id: str) -> None:
    """Invalida o memo de um run — chamado quando o job_result dele chega."""
    conn = executor_registry.get(executor_id)
    if conn is not None:
        conn.run_auth_cache.pop(run_id, None)

async def _query_run_snapshot(run_id: str):
    """Lê host, status e start_time do WorkflowRun numa ÚNICA query.

    Os três vereditos do job_result (pertence a este executor? já é terminal?
    quanto durou?) vinham de três funções independentes, cada uma com sua
    própria sessão: 3 checkouts do pool + 3 pre-pings + 3 SELECTs para ler a
    MESMA linha — e o terceiro carregava o ORM inteiro, incluindo `node_stats`
    (JSON) e `error_message` (Text) da execução anterior, para usar só o
    `start_time`. Sob concorrência isso disputava o pool com o tráfego HTTP e
    atrasava visivelmente o "concluído" na UI.

    Devolve `(host, status, start_time)`, ou None quando a linha não existe.
    LEVANTA em falha de banco de propósito: o caller precisa distinguir "run
    inexistente" (rejeição memorizável) de "banco fora" (cooldown, sem memo).
    """
    from app.models.models import WorkflowRun
    async with get_session_async() as db:
        result = await db.execute(
            select(
                WorkflowRun.host, WorkflowRun.status, WorkflowRun.start_time,
            ).where(WorkflowRun.task_id == run_id)
        )
        return result.first()

def _posse_ja_provada(executor_id: str, run_id: str) -> bool:
    """True quando o memo desta conexão já provou que o run é deste executor.

    Serve aos caminhos em que o job_result não pôde ser processado e precisamos
    fechar o run: sem uma prova de posse, um executor comprometido fecharia runs
    de outro tenant mandando job_result com run_id arbitrário justamente durante
    uma indisponibilidade do banco.
    """
    conn = executor_registry.get(executor_id)
    if conn is None:
        return False
    memo = conn.run_auth_cache.get(run_id)
    return memo is not None and memo[0] and memo[1] > time.monotonic()

async def _fechar_run_inconclusivo(executor_id: str, run_id: str, motivo: str) -> None:
    """Fecha como FALHO um run cujo job_result não pôde ser processado.

    PORQUÊ: o executor apaga a linha do outbox assim que o `send_text` retorna,
    então um job_result descartado aqui não volta nunca. Sem este fechamento o
    WorkflowRun fica em 'running' para sempre — a presença do executor continua
    saudável, então o `orphan_runs_watchdog` (que só age quando a presença some)
    jamais reconcilia —, o painel do usuário gira indefinidamente e o BRPOP do
    webhook síncrono estoura em timeout. Falho/inconclusivo é ruim; preso em
    'running' é pior.

    SEG: só chame com a posse do run por ESTE executor já provada
    (`_posse_ja_provada` ou snapshot lido).
    """
    from datetime import datetime as _dt, timezone as _tz

    from app.core.redis import get_redis_pool

    mensagem = f"Resultado do executor não pôde ser processado: {motivo}"
    agora = _dt.now(_tz.utc)
    try:
        resultado = json.dumps({
            "task_id":          run_id,
            "status":           "failed",
            "error_message":    mensagem,
            "error_category":   "internal",
            "retryable":        True,
            "end_time":         agora.isoformat(),
            "duration_seconds": None,
            # `stats` vazio de propósito: o consumer preserva os stats parciais
            # já acumulados no run em vez de apagá-los.
            "stats":            {},
        })
        # O evento carimba o MESMO instante do `end_time` acima.
        evento = run_events_service.evento_de_conclusao(
            run_id, "failed", erro=mensagem,
            extra={"error_category": "internal", "retryable": True},
            duration_ms=None, timestamp=agora.timestamp(),
        )
        webhook_key = f"webhook_response:{run_id}"
        rc = get_redis_pool()
        # Tudo num pipeline só: não pode existir estado intermediário em que o
        # banco fecha o run mas a UI nunca recebe o evento de conclusão.
        async with rc.pipeline(transaction=False) as pipe:
            pipe.lpush("run_results", resultado)
            run_events_service.anexar_eventos(pipe, run_id, [evento])
            # Desbloqueia o webhook síncrono, que senão espera o timeout inteiro.
            pipe.lpush(webhook_key, json.dumps({
                "job_status": "error", "error": mensagem, "response": None,
            }))
            pipe.expire(webhook_key, 300)
            await pipe.execute()
        logger.error(
            "Run '%s' (executor '%s') fechado como falho — %s.",
            run_id, executor_id, motivo,
        )
    except Exception as exc:
        logger.error(
            "Run '%s': não foi possível fechar o run após perder o job_result (%s): %s",
            run_id, motivo, exc,
        )

async def _ler_snapshot_com_retentativa(run_id: str):
    """Lê o snapshot do run insistindo um pouco antes de desistir.

    O caminho do job_result não tem segunda chance: perder o resultado por um
    reinício de pgbouncer de 200ms pendurava o run. Duas retentativas curtas
    cobrem o failover típico sem virar espera longa dentro da drenadora.
    """
    ultimo_erro: Exception | None = None
    for tentativa in range(_JOB_RESULT_DB_RETRIES):
        try:
            return await asyncio.wait_for(
                _query_run_snapshot(run_id), _RUN_AUTH_QUERY_TIMEOUT,
            )
        except Exception as exc:
            ultimo_erro = exc
            if tentativa + 1 < _JOB_RESULT_DB_RETRIES:
                await asyncio.sleep(_JOB_RESULT_DB_RETRY_DELAY)
    raise ultimo_erro  # type: ignore[misc]

async def _descartar_por_rate_limit(executor_id: str, job_id, msg: dict) -> None:
    """Descarta o job_result que passou do teto — sem pendurar o run.

    ERROR e não WARNING porque descartar um job_result legítimo pendura o run
    até o watchdog — se isto aparecer, o teto está errado ou há abuso.
    """
    logger.error(
        "Executor '%s': job_result do job '%s' descartado por rate limit (>%d/%.0fs).",
        executor_id, job_id, _JOB_RESULT_RATE_LIMIT, _RATE_WINDOW,
    )
    # Descartado é descartado, mas o run não pode ficar em 'running' para
    # sempre por causa disso — fecha como falho quando a posse já está provada.
    run_descartado = msg.get("run_id") or job_id
    if _posse_ja_provada(executor_id, run_descartado):
        await _fechar_run_inconclusivo(
            executor_id, run_descartado, "rate limit de job_result",
        )

async def _ler_veredito(executor_id: str, job_id, run_id):
    """Posse e idempotência do job_result, numa ÚNICA leitura do WorkflowRun.

    Os três vereditos — pertence a este executor? já é terminal? quanto durou?
    — saem da mesma linha. Devolve essa linha, `(host, status, start_time)`,
    quando o resultado deve ser gravado; None quando ele é descartado: run de
    outro executor (recusa memorizada), banco fora (cooldown armado e o run
    fechado como falho se a posse já estava provada) ou run já terminal.
    """
    conn = executor_registry.get(executor_id)
    cache = conn.run_auth_cache if conn is not None else None
    agora = time.monotonic()

    # O memo só entra aqui como atalho de RECUSA: um veredito positivo não
    # dispensa a query (precisamos de status e start_time da mesma linha), mas o
    # negativo precisa continuar barato para que um executor em loop não gere um
    # SELECT por tentativa.
    memo = cache.get(run_id) if cache is not None else None
    if memo is not None and memo[1] > agora and not memo[0]:
        logger.warning(
            "Executor '%s' tentou reportar job_result para run '%s' que não lhe pertence — rejeitado.",
            executor_id, run_id,
        )
        return None
    # O cooldown de banco NÃO vale aqui de propósito. Ele existe para a
    # telemetria (node_event: alto volume, barata de perder); aplicá-lo ao
    # job_result transformava um erro transitório de 200ms (reinício de
    # pgbouncer, failover de réplica) na perda de TODOS os resultados dos 2s
    # seguintes daquela conexão — e cada perda pendura um run em 'running' para
    # sempre. Um job_result por job, com teto de _JOB_RESULT_RATE_LIMIT/s, é
    # custo desprezível em SELECTs.
    try:
        linha = await _ler_snapshot_com_retentativa(run_id)
    except Exception as exc:
        # Fail-closed na ESCRITA do resultado: sem provar a posse do run não há
        # como aceitá-lo. O cooldown segue sendo armado para conter a rajada de
        # node_event que vem atrás.
        logger.error(
            "Não foi possível ler o run '%s' para o job_result do executor '%s': %s "
            "— resultado descartado (fail-closed).", run_id, executor_id, exc,
        )
        if conn is not None:
            conn.db_auth_cooldown_until = time.monotonic() + _RUN_AUTH_DB_COOLDOWN
        # Se a posse já estava provada por eventos anteriores deste mesmo run,
        # fechamos como falho: o executor não reenvia job_result.
        if _posse_ja_provada(executor_id, run_id):
            await _fechar_run_inconclusivo(
                executor_id, run_id, f"banco indisponível ({exc})",
            )
        return None

    # FAIL-CLOSED: run inexistente ou com host NULL é rejeitado — durante a
    # janela em que host ainda era NULL, um executor qualquer podia reivindicar
    # o run de outro tenant.
    host = linha[0] if linha is not None else None
    if host != f"executor:{executor_id}":
        logger.warning(
            "Executor '%s' tentou reportar job_result para run '%s' que não lhe pertence "
            "(host=%s) — rejeitado.", executor_id, run_id, host,
        )
        if cache is not None:
            _store_run_auth(cache, run_id, False, agora)
        return None

    # O job_result é a última mensagem do run: o memo de autorização não serve
    # mais para nada e sai daqui em vez de esperar o TTL.
    _forget_run_auth(executor_id, run_id)

    # ── Idempotência: run terminal não aceita updates ────────────────────
    # Cenário: network partition > heartbeat_timeout → _fail_orphan_runs marca
    # o run como failed. Executor termina depois e faz replay pelo outbox; o
    # estado "failed" não deve virar "success" retroativamente.
    # `cancelled` entra pela mesma razão: uma vez que o usuário cancelou e o
    # estado terminal foi gravado, um job_result posterior (reentrega, ou um
    # executor comprometido) não pode ressuscitar o run como success/failed.
    if linha[1] in ("success", "failed", "cancelled"):
        logger.info(
            "Job '%s' (run '%s'): run já está em estado terminal — resultado ignorado (idempotência).",
            job_id, run_id,
        )
        return None
    return linha

@dataclass(frozen=True)
class _ResultadoDoJob:
    """O desfecho que o executor reportou, já na taxonomia do servidor.

    Lido UMA vez do job_result contido e usado por todos os destinos — a chave
    efêmera, a fila `run_results`, o webhook síncrono e o
    `__workflow_complete__`. Os três últimos recalculavam, cada um, o mesmo
    `msg.get("error") if job_status != "ok"`.
    """

    job_status: object    # o status cru do executor: "ok", "error", "cancelled"…
    cancelado: bool
    falhou: bool          # nem "ok" nem cancelado
    error_category: object
    retryable: bool
    erro: object          # o `error` do executor quando o job não terminou "ok"

def _ler_resultado(executor_id: str, job_id, msg: dict) -> _ResultadoDoJob:
    """Classifica o desfecho do job e registra o recebimento no log."""
    job_status = msg.get("status", "unknown")
    # Cancelamento não é falha: o usuário pediu para parar. Tem status próprio
    # para não poluir a taxa de erro nem aparecer como "falhou" no painel.
    cancelado = job_status == "cancelled"
    # Taxonomia de erro (flow.utils.error_taxonomy): categoria estável + retryable.
    falhou = job_status != "ok" and not cancelado
    resultado = _ResultadoDoJob(
        job_status=job_status,
        cancelado=cancelado,
        falhou=falhou,
        error_category=msg.get("error_category") if falhou else None,
        retryable=bool(msg.get("retryable", False)) if falhou else False,
        erro=msg.get("error") if job_status != "ok" else None,
    )
    if job_status == "ok":
        logger.info("Resultado do job '%s' recebido do executor '%s': status=ok.", job_id, executor_id)
    else:
        logger.info(
            "Resultado do job '%s' recebido do executor '%s': status=%s category=%s retryable=%s.",
            job_id, executor_id, job_status, resultado.error_category or "internal", resultado.retryable,
        )
    return resultado

async def _persistir_resultado(
    executor_id: str, job_id, msg: dict, resultado: _ResultadoDoJob,
) -> None:
    """Chave efêmera `executor:{id}:results:{job}` (TTL 300 s) com o resumo.

    Vai ANTES da fila `run_results`: a reconciliação do inventário
    (`orfaos.py`) a lê para não dar como perdido o job cujo resultado acabou de
    chegar.
    """
    from app.core.redis import get_redis_pool

    try:
        rc = get_redis_pool()
        # Sanitiza dados antes de persistir — remove campos que podem conter credenciais
        sanitized_msg = {
            "job_id": msg.get("job_id"),
            "status": msg.get("status"),
            "run_id": msg.get("run_id"),
            "error": msg.get("error", "")[:500] if msg.get("error") else None,
            "error_category": resultado.error_category,
            "retryable": resultado.retryable,
        }
        key = f"executor:{executor_id}:results:{job_id}"
        await rc.setex(key, 300, json.dumps(sanitized_msg))
    except Exception as exc:
        logger.error("Erro ao persistir resultado do job '%s' no Redis: %s", job_id, exc)

def _medir_duracao(inicio) -> tuple[float | None, float | None]:
    """`(duration_seconds, duration_ms)` desde o `start_time` do run, ou `(None, None)`.

    O `start_time` já veio na leitura do veredito; naive é lido como UTC.
    """
    from datetime import datetime as _dt, timezone as _tz

    if inicio is None:
        return None, None
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=_tz.utc)
    decorrido = (_dt.now(_tz.utc) - inicio).total_seconds()
    return round(decorrido, 3), round(decorrido * 1000, 2)

async def _notificar_consumer(
    executor_id: str, run_id, resultado: _ResultadoDoJob, duration_seconds,
    stats_json: str, executor_ip: str | None,
) -> None:
    """Enfileira o resultado em `run_results`, de onde o consumer fecha o run no banco."""
    from datetime import datetime as _dt, timezone as _tz

    from app.core.redis import get_redis_pool

    try:
        # AWARE, com offset explicito. `utcnow().isoformat()` produzia uma
        # string SEM offset; o consumer fazia fromisoformat e entregava um
        # datetime naive para WorkflowRun.end_time, que e timestamptz. O
        # Postgres entao assumia o fuso da sessao (TZ=America/Cuiaba nos
        # containers) e convertia para UTC, gravando o fim 4h no futuro —
        # toda execucao aparecia com ~4h de duracao quando a UI subtraia
        # end_time - start_time. O duration_seconds sempre esteve certo, por
        # comparar dois datetimes aware (`_medir_duracao`).
        end_ts = _dt.now(_tz.utc).isoformat()
        # `stats` já foi serializado uma única vez em `_cap_job_result` (até
        # 4 MB): repetir o dumps aqui era a segunda das três serializações
        # que congelavam o event loop a cada workflow pesado que terminava.
        # Montamos o envelope só com as chaves leves e emendamos a string
        # pronta — o dict literal nunca é vazio, então o `[:-1]` sempre corta
        # a chave de fechamento.
        # O IP da conexão vai junto: só este worker o tem. O consumer de
        # run_results roda nos quatro workers e, procurando no registro
        # local, gravava `executor_ip` vazio em ~3 de cada 4 execuções.
        # É o servidor quem escreve a chave, fora do `stats` — o executor
        # não tem como declarar o próprio IP. `executor_ip` é o da conexão
        # que recebeu o frame (a fila da sessão o carrega); o registro só
        # entra para quem chama sem ele.
        _head = json.dumps({
            "task_id":          run_id,
            "status":           _desfecho(resultado.job_status, resultado.cancelado, ok="success"),
            "error_message":    resultado.erro,
            "error_category":   resultado.error_category,
            "retryable":        resultado.retryable,
            "end_time":         end_ts,
            "duration_seconds": duration_seconds,
            "executor_ip":      executor_ip or getattr(executor_registry.get(executor_id), "executor_ip", None),
        })
        await get_redis_pool().lpush(
            "run_results", f'{_head[:-1]},"stats":{stats_json}}}',
        )
    except Exception as exc:
        logger.error("Erro ao publicar run_results para run '%s': %s", run_id, exc)

async def _notificar_webhook(
    run_id, stats: dict, resposta, resultado: _ResultadoDoJob, *, offload: bool,
) -> None:
    """Destrava o webhook síncrono (ResponseNode ou falha).

    O webhook_router aguarda via BRPOP em `webhook_response:{run}` se o workflow
    tem ResponseNode. Também notificamos em caso de erro para evitar que o
    webhook fique preso no timeout.
    """
    from app.core.redis import get_redis_pool

    # Marcas da truncagem de `stats` — a do protocolo, que o executor aplica
    # antes de enviar e `_cap_job_result` reaplica na entrada.
    truncado = stats.get(STATS_TRUNCADO) is True
    controle_descartado = stats.get(STATS_CONTROLE_DESCARTADO) is True
    # Se o payload foi truncado e até as chaves de controle sumiram, o webhook
    # não tem como receber a resposta — publicamos erro explícito para
    # desbloquear o BRPOP em vez de deixar o caller em timeout.
    if truncado and resposta is None and controle_descartado:
        job_status = "error"
        erro = (
            f"Resposta do workflow excedeu o limite de {stats.get(STATS_TAMANHO_ORIGINAL, '?')} bytes "
            "no transporte executor→servidor. Reduza o tamanho do body (ex: compactar geometria, "
            "paginar resultados) ou consuma via runner assíncrono."
        )
    else:
        job_status = resultado.job_status
        erro = resultado.erro

    if resposta is not None or job_status != "ok":
        try:
            # O body inline do ResponseNode vai até 1 MB: acima do limiar
            # esta serialização também sai do event loop.
            payload = await _dumps(
                {
                    "job_status": job_status,
                    "error":      erro,
                    "response":   resposta,
                },
                offload=offload,
            )
            rc = get_redis_pool()
            await rc.lpush(f"webhook_response:{run_id}", payload)
            await rc.expire(f"webhook_response:{run_id}", 300)
        except Exception as exc:
            logger.error("Erro ao publicar webhook_response para run '%s': %s", run_id, exc)

async def _registrar_body(run_id, executor_id: str, resposta) -> None:
    """Artifact para o body que o ResponseNode subiu direto ao MinIO.

    Garante uma linha com expires_at para o cleanup global remover o objeto
    caso o delete imediato pós-streaming do webhook_router falhe (órfão).
    """
    body_ref = (resposta or {}).get("body_ref") if isinstance(resposta, dict) else None
    # Fora do formato (executor defeituoso ou comprometido), o `.get` levantava
    # aqui, fora do try, e o `__workflow_complete__` não saía: o run fechava no
    # banco e o painel aberto nunca sabia.
    if isinstance(body_ref, dict) and body_ref.get("s3_key"):
        try:
            await _register_webhook_response_artifact(run_id, executor_id, body_ref)
        except Exception as exc:
            logger.error("Falha ao registrar Artifact de webhook response (run=%s): %s", run_id, exc)

async def _publicar_conclusao(run_id, resultado: _ResultadoDoJob, duration_ms) -> None:
    """Publica o `__workflow_complete__` do job no histórico e no canal do run.

    É o fim que o painel vê. Os runs que o SERVIDOR fecha, sem job_result,
    publicam pelo `run_events_service.publicar_conclusao`, com o evento montado
    no mesmo lugar (`evento_de_conclusao`), só que sem `duration_ms`: o servidor
    não mede a duração do que ele fecha.
    """
    from app.core.redis import get_redis_pool

    try:
        # O nível sai do status: "failed" ⇔ falha (`resultado.falhou`).
        evento = run_events_service.evento_de_conclusao(
            run_id,
            _desfecho(resultado.job_status, resultado.cancelado, ok="completed"),
            erro=resultado.erro,
            # Taxonomia do job inteiro — o painel usa para dizer se vale
            # repetir a execução ou se o usuário precisa corrigir a entrada.
            extra={
                "error_category": resultado.error_category,
                "retryable":      resultado.retryable,
            } if resultado.falhou else None,
            duration_ms=duration_ms,
        )
        rc = get_redis_pool()
        async with rc.pipeline(transaction=False) as pipe:
            run_events_service.anexar_eventos(pipe, run_id, [evento])
            await pipe.execute()
    except Exception as exc:
        logger.error("Erro ao publicar __workflow_complete__ para run '%s': %s", run_id, exc)

async def _handle_job_result(
    executor_id: str, msg: dict, frame_bytes: int = 0, executor_ip: str | None = None,
):
    """
    Processa o resultado de um job reportado pelo executor.

    Confere o run no banco e leva o desfecho a cada destino, na ordem abaixo. A
    chave efêmera do resultado vive 300 s; quem grava o run no banco é o
    consumer da fila `run_results`.

    LIMITES: rate limit e teto de bytes, iguais em espírito aos do node_event.
    Sem eles, `error` e `stats` iam crus para a fila `run_results` (sem TTL), o
    histórico do run e o Postgres — e o loop custava só 3 SELECTs por iteração.

    ORDEM dos efeitos, que é contrato: leitura do run (`_ler_veredito`) →
    chave efêmera do resultado (`_persistir_resultado`) → fila `run_results`
    (`_notificar_consumer`) → `webhook_response` (`_notificar_webhook`) →
    Artifact do body (`_registrar_body`) → `__workflow_complete__`
    (`_publicar_conclusao`). Cada destino tem o seu try: a falha de um não
    impede os seguintes.

    `frame_bytes` é o tamanho do frame que trouxe esta mensagem. Serve só para
    decidir se as serializações grandes vão para uma thread — ver
    `_JSON_OFFLOAD_THRESHOLD`.
    """
    job_id = msg.get("job_id")
    if not job_id:
        logger.warning("Executor '%s' enviou job_result sem job_id.", executor_id)
        return

    # Antes da autorização de propósito: é o custo em SELECTs que o flood explora.
    if not _rate_allowed(executor_id, "job_result", _JOB_RESULT_RATE_LIMIT):
        await _descartar_por_rate_limit(executor_id, job_id, msg)
        return

    # `stats` pode ter MB: acima do limiar, a medição do teto (que serializa)
    # sai do event loop para não congelar o worker inteiro.
    offload = frame_bytes > _JSON_OFFLOAD_THRESHOLD
    if offload:
        msg, stats_json = await asyncio.to_thread(_cap_job_result, executor_id, msg)
    else:
        msg, stats_json = _cap_job_result(executor_id, msg)

    # Fallback para job_id: o servidor define run_id == job_id ao despachar ao
    # executor; se a falha ocorreu antes da descriptografia (ex: assinatura
    # inválida), run_id não estará presente no resultado, mas job_id é
    # suficiente para localizar o WorkflowRun.
    run_id = msg.get("run_id") or job_id

    linha = await _ler_veredito(executor_id, job_id, run_id)
    if linha is None:
        return

    resultado = _ler_resultado(executor_id, job_id, msg)
    await _persistir_resultado(executor_id, job_id, msg, resultado)
    duration_seconds, duration_ms = _medir_duracao(linha[2])
    await _notificar_consumer(
        executor_id, run_id, resultado, duration_seconds, stats_json, executor_ip,
    )
    # O ResponseNode devolve o body do webhook síncrono dentro de `stats`.
    stats = msg.get("stats") or {}
    resposta = stats.get("__response__")
    await _notificar_webhook(run_id, stats, resposta, resultado, offload=offload)
    await _registrar_body(run_id, executor_id, resposta)
    await _publicar_conclusao(run_id, resultado, duration_ms)

def _serialize_node_event(executor_id: str, msg: dict) -> str:
    """Serializa o node_event já contido pelo teto de bytes.

    LIMITE: sem ele, um executor com bug (ou comprometido) empurra 16 MB por
    frame direto para o Redis, que no compose não tem maxmemory — cresce até o
    OOM-kill e leva junto dispatch, auth e o consumer de resultados.

    A redução é a do protocolo (flow/utils/publisher/reducao.py), a mesma que o
    executor já aplica antes de enviar: aqui ela é defesa, e um evento que o
    executor reduziu passa intacto.
    """
    # Remove o campo "type" — o canal Redis espera o evento sem ele
    event = {k: v for k, v in msg.items() if k != "type"}
    payload = json.dumps(event)

    # `json.dumps` usa ensure_ascii, logo len(str) == tamanho em bytes.
    if len(payload) > TETO_NODE_EVENT_BYTES:
        logger.warning(
            "Executor '%s': node_event de %d bytes (run=%s node=%s) excede o teto de %d — truncado.",
            executor_id, len(payload), msg.get("run_id"), msg.get("node"), TETO_NODE_EVENT_BYTES,
        )
        payload = reduzir_node_event(event, payload)
    return payload

async def _publish_node_events(executor_id: str, msgs: list[dict]) -> None:
    """
    Republica um LOTE de eventos de nós no Redis pub/sub, no mesmo canal que o
    log_workflows_router.py escuta. É assim que o frontend recebe atualizações
    visuais em tempo real quando o workflow roda num executor externo.

    PERF: o lote inteiro sai num ÚNICO pipeline — os eventos são agrupados por
    run e cada run gasta um `rpush` variádico + um `ltrim` + um `expire` + os
    `publish`. Antes era 1 round-trip Redis POR EVENTO, emitido de dentro do
    loop de recepção: numa rajada de fan-out alto o job_result final e o
    heartbeat ficavam presos atrás de centenas de idas ao Redis. Com o lote de
    até `_INBOX_COALESCE_MAX`, a mesma rajada custa um round-trip.

    SEG: run_id é validado contra executor_id — executor não pode injetar
    eventos em runs que não lhe pertencem (cross-tenant). A validação é por run
    (memorizada na conexão), não por evento, então agrupar não a afrouxa.
    """
    from app.core.redis import get_redis_pool

    por_run: dict[str, list[str]] = {}
    negados: set[str] = set()
    for msg in msgs:
        run_id = msg.get("run_id")
        if not run_id or run_id in negados:
            continue
        if run_id not in por_run:
            if not await _run_belongs_to_agent(executor_id, run_id):
                logger.warning(
                    "Executor '%s' tentou publicar node_event em run '%s' que não lhe "
                    "pertence — rejeitado.", executor_id, run_id,
                )
                negados.add(run_id)
                continue
            por_run[run_id] = []
        por_run[run_id].append(_serialize_node_event(executor_id, msg))

    if not por_run:
        return

    try:
        rc = get_redis_pool()
        async with rc.pipeline(transaction=False) as pipe:
            for run_id, payloads in por_run.items():
                run_events_service.anexar_eventos(pipe, run_id, payloads)
            await pipe.execute()
    except Exception as exc:
        logger.warning(
            "Erro ao publicar %d node_event(s) no Redis (runs=%s): %s",
            sum(len(p) for p in por_run.values()), list(por_run), exc,
        )

async def _handle_sync_event(executor_id: str, msg: dict):
    """
    Publica eventos de sync do executor no Redis para consumo pelo frontend.
    Canal: executor:{executor_id}:sync_events

    PERF: publish + hset + expire saem num único pipeline — eram três `await`
    soltos, e o emissor manda um evento por transição de ARQUIVO. Num GeoSync de
    milhares de arquivos isso gastava 3 round-trips por arquivo, em série, junto
    com os node_events dos workflows que rodavam no mesmo executor.

    LIMITE: o dicionário do evento copia qualquer `**kwargs` que o emissor tenha
    colocado, sem teto. Acima de `_MAX_SYNC_EVENT_BYTES` o evento é reduzido aos
    campos que a UI realmente usa.
    """
    from app.core.redis import get_redis_pool

    event = {k: v for k, v in msg.items() if k != "type"}
    event["executor_id"] = executor_id
    payload = json.dumps(event)

    if len(payload) > _MAX_SYNC_EVENT_BYTES:
        logger.warning(
            "Executor '%s': sync_event de %d bytes (event=%s) excede o teto de %d — reduzido.",
            executor_id, len(payload), msg.get("event"), _MAX_SYNC_EVENT_BYTES,
        )
        payload = json.dumps({
            "executor_id":   executor_id,
            "event":         str(msg.get("event", ""))[:TETO_POR_CAMPO],
            "dataset":       str(msg.get("dataset", ""))[:TETO_POR_CAMPO],
            "progress":      _coerce_gauge(msg.get("progress")) or 0,
            "timestamp":     _coerce_gauge(msg.get("timestamp")),
            "__truncated__": True,
        })

    channel = f"executor:{executor_id}:sync_events"
    status_key = f"executor:{executor_id}:sync_status"

    try:
        rc = get_redis_pool()
        async with rc.pipeline(transaction=False) as pipe:
            pipe.publish(channel, payload)
            # Salva estado atual para consulta
            pipe.hset(status_key, mapping={
                "last_event": str(msg.get("event", ""))[:TETO_POR_CAMPO],
                "dataset": str(msg.get("dataset", ""))[:TETO_POR_CAMPO],
                "progress": str(msg.get("progress", 0))[:64],
                "timestamp": str(msg.get("timestamp", ""))[:64],
            })
            pipe.expire(status_key, REDIS_TTL_1H)
            await pipe.execute()
    except Exception as exc:
        logger.warning("Erro ao publicar sync_event no Redis (executor=%s): %s", executor_id, exc)
