# app/api/routers/executor_ws/inbox.py
"""
Fila de despacho por conexão: enfileirar com back-pressure, drenar em
lote, resgatar job_results no teardown.
"""
import asyncio
import time

from app.core.utils.logger import get_logger



logger = get_logger(__name__)

from .protocolo import _e_telemetria
from .resultados import (
    _fechar_run_inconclusivo,
    _handle_job_result,
    _handle_sync_event,
    _posse_ja_provada,
    _publish_node_events,
    _record_job_ack,
)
from .orfaos import _reconciliar_inventario

# ── Fila de despacho por conexão (ver `_drenar_inbox`) ───────────────────────
# O loop de recepção processava cada mensagem INLINE: a próxima
# `ws.receive_text()` só acontecia depois que o Redis (e às vezes o Postgres)
# respondia. Heartbeat, capacity, ack e o job_result final ficavam presos atrás
# da rajada de telemetria do MESMO executor — o canvas recebia updates em
# rajadas engasgadas, o "concluído" chegava segundos depois do fim real e, em
# fan-out alto, o executor chegava perto do timeout de 90s.
#
# Agora o loop só faz parse + schema + rate limit + enfileirar; uma task
# drenadora fala com Redis/Postgres. TUDO vai na MESMA fila para preservar a
# ordem relativa entre node_event e job_result de um run.
#
# Fila cheia NÃO é simétrica: telemetria é descartada; ciclo de vida e
# job_result esperam vaga (back-pressure) e, no limite, são processados inline.
# Ver `_InboxQueue` e `_enfileirar_mensagem`.
_INBOX_MAXSIZE = 5000

# Máximo de node_events consecutivos fundidos num único pipeline. Não há timer:
# a drenadora só junta o que JÁ está na fila, então uma mensagem isolada sai na
# hora (latência zero) e a rajada se agrupa sozinha enquanto o Redis responde.
_INBOX_COALESCE_MAX = 64

# Teto de espera pelo flush da drenadora no teardown do WS. Sem o flush, os
# últimos eventos do run (inclusive o __workflow_complete__) se perderiam.
_INBOX_FLUSH_TIMEOUT = 10.0

# Intervalo mínimo entre dois WARNINGs de descarte por fila cheia.
_INBOX_DROP_LOG_EVERY = 5.0

# Carência dada ao job_result que já está sendo gravado quando o teardown
# desiste de esperar a drenagem. Ver `_drenar_inbox` e o `finally` do handler.
_INBOX_CANCEL_GRACE = 5.0

# Sentinela de encerramento da fila — ver `_drenar_inbox`.
_INBOX_STOP = object()

# Teto de espera por vaga quando a fila enche e a mensagem NÃO pode ser perdida.
# Existe só para o loop de recepção não ficar preso para sempre se a drenadora travar:
# esgotado o prazo, a mensagem é processada INLINE (que é lento, porém sem
# perda), nunca descartada. Bem abaixo do _HEARTBEAT_TIMEOUT de 90s para o
# executor não ser desconectado por causa da própria espera.
_INBOX_PUT_TIMEOUT = 30.0

class _InboxQueue(asyncio.Queue):
    """Fila da conexão com política de descarte SELETIVA quando enche.

    CONTRATO do que NUNCA cai (estado que nenhuma rede do cliente reconstrói):

      * `job_result` — é, por construção, a ÚLTIMA mensagem de um run, e o
        executor apaga a linha do outbox assim que o `send_text` retorna.
        Perdido, o WorkflowRun fica preso em 'running' para sempre (a presença
        do executor segue saudável, então nem `orphan_runs_watchdog` nem
        `_fail_orphan_runs_if_gone` reconciliam; o BRPOP do webhook estoura).
      * `sync_complete` — fecha a barra de progresso do GeoSync; perdê-lo a
        prende em 99% (ver `_SYNC_TERMINAL_EVENTS`).

    Todo o RESTO — telemetria (stdout/debug, sync_event de progresso) E os
    node_event de ciclo de vida — é descartável sob pressão. Perder um `completed`
    de nó deixa o nó em 'started' durante o run, mas no fim `completeExecution`
    o pinta como 'unknown' ("sem resposta"); e se o canal ao vivo morrer, o
    watchdog do cliente reconecta e reconcilia. É degradação honesta coberta pela
    rede — não vale o custo de back-pressure aqui. (Já foi: a Opção B mantinha o
    ciclo de vida sob back-pressure/inline, o que resolvia um sintoma cuja causa
    real era de transporte, hoje coberta por heartbeat+watchdog.)
    """

    # IP da conexão que recebeu as mensagens desta fila (a rota o define ao
    # criá-la). O job_result leva ESTE IP para o run_results, e não o de quem
    # estiver no registro quando for gravado: num takeover o listener tira a
    # conexão do registro antes de a fila terminar de esvaziar.
    ip_da_conexao: str | None = None

    def job_results_pendentes(self) -> list[tuple]:
        """job_result ainda enfileirados, na ordem de chegada.

        Usado no teardown para resgatar o que a drenadora cancelada não chegou a
        processar — telemetria residual pode sumir, resultado não.
        """
        return [
            item for item in self._queue
            if isinstance(item, tuple) and item[0] == "job_result"
        ]

def _novo_contador_de_descartes() -> dict:
    """Estado do WARNING agregado de descarte por conexão."""
    return {"total": 0, "desde_log": 0, "ultimo_log": 0.0}

def _contabilizar_descarte(
    executor_id: str, descartes: dict, quantidade: int = 1,
) -> None:
    """Contabiliza evento descartado por fila cheia, com WARNING agregado.

    Uma linha por mensagem afogaria o log justamente no incidente em que ele
    precisa ser lido. Cobre stdout/debug, sync_event de progresso E node_event de
    ciclo de vida — um `completed` perdido aqui aparece como "sem resposta" no
    painel, não como erro.
    """
    descartes["total"] += quantidade
    descartes["desde_log"] += quantidade
    agora = time.monotonic()
    if (agora - descartes["ultimo_log"]) >= _INBOX_DROP_LOG_EVERY:
        logger.warning(
            "Executor '%s': fila de processamento cheia (%d) — %d evento(s) "
            "descartado(s) nos últimos %.0fs (%d nesta conexão). node_event perdido "
            "vira 'sem resposta' no painel.",
            executor_id, _INBOX_MAXSIZE, descartes["desde_log"],
            _INBOX_DROP_LOG_EVERY, descartes["total"],
        )
        descartes["desde_log"] = 0
        descartes["ultimo_log"] = agora

async def _enfileirar_mensagem(
    executor_id: str,
    inbox: "_InboxQueue",
    descartes: dict,
    msg_type: str,
    msg: dict,
    frame_bytes: int,
) -> None:
    """Enfileira para a drenadora. Sob fila cheia, só job_result, ack e
    sync_complete escapam do descarte.

    Fila cheia significa que o executor produz mais rápido do que o Redis aceita.
    A resposta depende do que a mensagem CARREGA:

      * node_event (stdout/debug E ciclo de vida) e sync_event de progresso —
        DESCARTADOS, com WARNING agregado. A perda de um `completed` vira um nó
        'unknown' no fim do run (completeExecution), e o watchdog do cliente
        recupera se o canal ao vivo morrer: degradação honesta, coberta pela rede.
      * job_result, ack e sync_complete — NUNCA descartados. Carregam estado
        que nenhuma rede reconstrói (o run preso em 'running' no Postgres; o
        run entregue e preso em 'pending'; a barra do GeoSync em 99%).
        job_result e ack vão INLINE na hora; sync_complete espera vaga e, no
        limite, também vai inline.

    O `await` no caminho feliz não suspende (put_nowait não cede o loop), então o
    ganho de latência do enfileiramento continua intacto.
    """
    entrada = (msg_type, msg, frame_bytes)
    try:
        inbox.put_nowait(entrada)
        return
    except asyncio.QueueFull:
        pass

    # ── Fila cheia ────────────────────────────────────────────────────────────
    # node_event (qualquer kind) e sync_event de progresso são descartáveis: a
    # perda degrada honestamente (nó 'unknown', barra segue) e a rede do cliente
    # cobre. Só job_result e sync_complete seguem adiante.
    # O inventário também: é periódico, e o próximo chega em um minuto.
    if msg_type in ("node_event", "inventario") or _e_telemetria(msg_type, msg):
        _contabilizar_descarte(executor_id, descartes)
        return

    # O ACK promove o run de 'pending' para 'running'. Perdido, um job que o
    # executor recebeu ficaria em "Na fila" até a varredura dos não entregues
    # fechá-lo como falho — com o executor rodando. É um UPDATE curto por job:
    # inline, sem esperar vaga.
    if msg_type == "ack":
        try:
            await _record_job_ack(executor_id, msg.get("job_id"), msg.get("status") or "enqueued")
        except Exception as exc:
            logger.error(
                "Executor '%s': erro ao processar ACK inline do job '%s': %s",
                executor_id, msg.get("job_id"), exc,
            )
        return

    # job_result não espera nem tenta abrir vaga: é UMA mensagem por run e o
    # inline resolve na hora, sem perda. Bloquear o loop de recepção custa menos
    # que pendurar o run em 'running' para sempre.
    if msg_type == "job_result":
        logger.error(
            "Executor '%s': fila cheia — job_result do job '%s' processado INLINE "
            "(o loop de recepção vai bloquear).",
            executor_id, msg.get("job_id"),
        )
        try:
            await _handle_job_result(executor_id, msg, frame_bytes)
        except Exception as exc:
            logger.error(
                "Executor '%s': erro ao processar job_result inline do job '%s': %s",
                executor_id, msg.get("job_id"), exc,
            )
        return

    # Resta o sync_complete (terminal do GeoSync). Perdê-lo prende a barra em 99%
    # e nenhum watchdog recupera — então ESPERA vaga (back-pressure: o loop para
    # de ler, o TCP enche, o executor desacelera sozinho) e, esgotado o prazo,
    # vai INLINE. É o único evento que ainda paga o custo do back-pressure aqui.
    try:
        await asyncio.wait_for(inbox.put(entrada), timeout=_INBOX_PUT_TIMEOUT)
        return
    except asyncio.TimeoutError:
        # `asyncio.Queue.put` cancelado levanta ANTES do put_nowait interno,
        # então o item não entrou na fila e não há risco de duplicata aqui.
        pass

    logger.error(
        "Executor '%s': fila de processamento saturada por %.0fs — sync_event "
        "terminal processado INLINE. Investigar Redis/Postgres.",
        executor_id, _INBOX_PUT_TIMEOUT,
    )
    try:
        await _handle_sync_event(executor_id, msg)
    except Exception as exc:
        logger.error(
            "Executor '%s': erro ao processar sync_event inline: %s",
            executor_id, exc,
        )

async def _flush_node_events(executor_id: str, eventos: list[dict]) -> None:
    """Publica o lote acumulado. Não propaga: a drenadora não pode morrer."""
    if not eventos:
        return
    try:
        await _publish_node_events(executor_id, eventos)
    except Exception as exc:
        logger.error(
            "Executor '%s': falha ao drenar lote de %d node_event(s): %s",
            executor_id, len(eventos), exc,
        )

async def _processar_job_result_blindado(
    executor_id: str, msg: dict, frame_bytes: int, inflight: set | None,
    executor_ip: str | None = None,
) -> None:
    """Roda `_handle_job_result` numa task blindada contra cancelamento.

    PORQUÊ: a gravação do resultado é uma sequência NÃO atômica (setex do
    resultado → lpush em `run_results`, que vira o WorkflowRun para terminal no
    Postgres → webhook_response → publish do `__workflow_complete__`), com vários
    `await` de Redis no meio. Um `cancel()` da drenadora caindo entre eles deixa
    o run terminal no banco e o canvas SEM o evento de conclusão — o painel gira
    para sempre num run que já acabou. Com `shield`, o cancelamento chega a quem
    espera, nunca a quem grava; a task segue até o fim e o teardown lhe dá
    carência antes de encerrar (ver `_INBOX_CANCEL_GRACE`).
    """
    tarefa = asyncio.create_task(
        _handle_job_result(executor_id, msg, frame_bytes, executor_ip=executor_ip),
        name=f"job-result-{executor_id[:8]}",
    )
    # asyncio guarda só weakrefs para tasks — sem referência forte, uma task
    # blindada pode ser coletada no meio da gravação.
    if inflight is not None:
        inflight.add(tarefa)
        tarefa.add_done_callback(inflight.discard)
    await asyncio.shield(tarefa)

async def _drenar_inbox(
    executor_id: str, inbox: asyncio.Queue, inflight: set | None = None,
) -> None:
    """Consome a fila da conexão e faz o trabalho pesado (Redis/Postgres).

    Separar recepção de processamento é o que tira o head-of-line blocking: o
    loop de recepção nunca mais espera por I/O, então heartbeat, capacity e ack
    deixam de ficar presos atrás de uma rajada de telemetria.

    COALESCÊNCIA SEM TIMER: cada volta pega o que JÁ está enfileirado (até
    `_INBOX_COALESCE_MAX`). Numa rajada a fila enche enquanto esta task espera o
    Redis, e a volta seguinte leva dezenas de eventos num pipeline só; com
    tráfego baixo, a mensagem isolada sai imediatamente. Um timer de janela fixa
    faria o oposto — adiaria justamente o evento único, que é o que o usuário vê.

    ORDEM: tudo vem da MESMA fila e um job_result/sync_event fecha o lote de
    node_events acumulado antes de ser processado, então a ordem relativa dentro
    de um run é a de chegada.
    """
    try:
        while True:
            item = await inbox.get()
            lote = [item]
            while len(lote) < _INBOX_COALESCE_MAX:
                try:
                    lote.append(inbox.get_nowait())
                except asyncio.QueueEmpty:
                    break

            eventos: list[dict] = []
            for entrada in lote:
                if entrada is _INBOX_STOP:
                    await _flush_node_events(executor_id, eventos)
                    return
                msg_type, msg, frame_bytes = entrada
                if msg_type == "node_event":
                    eventos.append(msg)
                    continue
                await _flush_node_events(executor_id, eventos)
                eventos = []
                try:
                    if msg_type == "job_result":
                        await _processar_job_result_blindado(
                            executor_id, msg, frame_bytes, inflight,
                            executor_ip=getattr(inbox, "ip_da_conexao", None),
                        )
                    elif msg_type == "ack":
                        await _record_job_ack(
                            executor_id, msg.get("job_id"), msg.get("status") or "enqueued",
                        )
                    elif msg_type == "inventario":
                        await _reconciliar_inventario(executor_id, msg)
                    else:
                        await _handle_sync_event(executor_id, msg)
                except Exception as exc:
                    logger.error(
                        "Executor '%s': erro ao processar '%s': %s",
                        executor_id, msg_type, exc,
                    )
            await _flush_node_events(executor_id, eventos)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Drenagem da conexão do executor '%s' abortada: %s", executor_id, exc)

async def _resgatar_job_results_pendentes(executor_id: str, inbox: "_InboxQueue") -> None:
    """Última chance para os job_result que sobraram na fila cancelada.

    O `cancel()` do teardown para a drenadora com a fila ainda cheia. Telemetria
    residual pode sumir; job_result não — sem ele o WorkflowRun fica em 'running'
    para sempre. Tentamos gravar cada um aqui e, se nem isso der certo, fechamos
    o run como falho em vez de deixá-lo pendurado.
    """
    pendentes = inbox.job_results_pendentes()
    if not pendentes:
        return
    logger.warning(
        "Executor '%s': %d job_result(s) na fila após o cancelamento da drenagem — "
        "processando no teardown.", executor_id, len(pendentes),
    )
    for _tipo, msg, frame_bytes in pendentes:
        run_id = msg.get("run_id") or msg.get("job_id")
        try:
            await _handle_job_result(
                executor_id, msg, frame_bytes,
                executor_ip=getattr(inbox, "ip_da_conexao", None),
            )
        except Exception as exc:
            logger.error(
                "Executor '%s': job_result do job '%s' perdido no teardown: %s",
                executor_id, msg.get("job_id"), exc,
            )
            if run_id and _posse_ja_provada(executor_id, run_id):
                await _fechar_run_inconclusivo(
                    executor_id, run_id, f"teardown da conexão ({exc})",
                )

async def _encerrar_drenagem(inbox: asyncio.Queue, drain_task: asyncio.Task) -> None:
    """Enfileira a sentinela e espera a drenadora terminar o que já recebeu.

    `put` (e não `put_nowait`) de propósito: se a fila estiver cheia no momento
    da queda, a sentinela espera a vaga que a própria drenadora abre — com
    `put_nowait` ela seria descartada e a task ficaria pendurada.
    """
    await inbox.put(_INBOX_STOP)
    await drain_task
