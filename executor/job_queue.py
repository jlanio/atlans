# executor/job_queue.py
"""
Fila local de jobs com controle de concorrência e back-pressure.

Arquitetura:
  - asyncio.PriorityQueue: buffer de jobs aguardando execução
  - asyncio.Semaphore: limita execuções paralelas do flow/
  - N worker coroutines: consumem a fila e executam jobs
  - Capacity reporting: informa o servidor do estado atual da fila
"""
import asyncio
import itertools
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Any

from executor import config

logger = logging.getLogger(__name__)


# Lápide de um job cancelado ANTES de chegar a este executor (ver `lapidar`).
# O job pode estar em trânsito — despachado por um worker da API cujo envio
# ainda não saiu — e, se chegar depois do cancelamento, é descartado em vez de
# rodar um run que o servidor já fechou. Dez minutos cobrem com folga o prazo de
# envio do servidor; o teto impede que um servidor com bug encha a memória.
_LAPIDE_TTL_S = 600.0
_LAPIDE_MAX = 1000


@dataclass(order=True)
class _QueueItem:
    """Item da fila de prioridade. Menor valor = maior prioridade; entre
    prioridades iguais, quem chegou antes (`seq`).

    Sem o `seq` o empate não tinha ordem: o heap da PriorityQueue não é estável,
    e como o servidor não manda prioridade, TODO job empata no 5. Com dez jobs
    na fila, o segundo a chegar era o nono a rodar.
    """
    priority:  int
    seq:       int
    message:   dict    = field(compare=False, default_factory=dict)


class ExecutorJobQueue:
    """
    Fila de jobs com controle de concorrência para o executor.

    Uso:
        queue = ExecutorJobQueue(on_execute=executor_coroutine)
        await queue.start()          # inicia workers em background
        accepted = await queue.enqueue(job_message)
        capacity = queue.get_capacity()
        await queue.shutdown()       # para de aceitar, aguarda jobs em execução
    """

    def __init__(
        self,
        on_execute: Callable[[dict], Coroutine[Any, Any, dict]],
        max_concurrent: int = config.MAX_CONCURRENT,
        max_queue_size: int = config.MAX_QUEUE_SIZE,
        on_cancelled: Callable[[dict], Coroutine[Any, Any, None]] | None = None,
    ):
        self._on_execute   = on_execute
        # Chamado quando um job é cancelado — quem cancela é o servidor, e sem
        # este aviso a execução simplesmente sumiria: o `on_execute` interrompido
        # nunca chega a produzir resultado, e o run ficaria "running" para sempre.
        self._on_cancelled = on_cancelled
        # Chamado na PRIMEIRA linha do shutdown, para o servidor saber da
        # drenagem sem esperar o tick de 10s do capacity_loop. Injetado depois da
        # construção (`set_on_draining`) porque a conexão só existe depois desta
        # fila — ela recebe a fila no próprio construtor.
        self._on_draining: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._max_concurrent = max_concurrent
        self._max_queue    = max_queue_size

        self._queue        = asyncio.PriorityQueue(maxsize=max_queue_size)
        # Ordem de chegada, desempate da prioridade — ver `_QueueItem`.
        self._seq          = itertools.count()
        self._semaphore    = asyncio.Semaphore(max_concurrent)
        self._running      = 0
        self._shutting_down = False
        self._workers: list[asyncio.Task] = []
        self._active_jobs: dict[str, dict] = {}  # job_id → message
        self._active_tasks: dict[str, asyncio.Task] = {}  # job_id → task em execução
        # Jobs cancelados enquanto ainda esperavam na fila. Não dá para remover
        # um item do meio de uma PriorityQueue, então o worker descarta ao pegar.
        self._cancelled: set[str] = set()
        # Jobs aceitos e ainda não finalizados (na fila, presos no semáforo ou em
        # execução). É o que permite ao `cancel()` responder "unknown" honestamente
        # em vez de marcar qualquer id desconhecido em `_cancelled` para sempre —
        # o set crescia sem limite e a UI dizia "cancelamento solicitado" para um
        # job que nem existia nesta instância.
        self._known: set[str] = set()
        # job_id → instante (monotonic) em que a lápide vence. Ver `lapidar`.
        self._lapides: dict[str, float] = {}
        # Sinaliza "nenhum job em execução". Substitui o polling de 0.5s do
        # shutdown — o `await` acorda no instante em que o último job termina.
        self._idle = asyncio.Event()
        self._idle.set()

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    async def start(self, n_workers: int | None = None):
        """Inicia N workers assíncronos consumindo a fila."""
        n = n_workers or self._max_concurrent
        self._workers = [
            asyncio.create_task(self._worker(i), name=f"executor-worker-{i}")
            for i in range(n)
        ]
        logger.info("ExecutorJobQueue iniciada com %d workers.", n)

    # Motivo enviado ao servidor para jobs que estavam na fila e nunca chegaram a
    # rodar. Distinto do cancelamento pedido pelo usuário — é o que impede a UI de
    # dizer "cancelada pelo usuário" para algo que ninguém cancelou.
    # ATENÇÃO: isto afirma um invariante LOCAL (nada foi executado, nenhum efeito
    # colateral aconteceu neste executor, logo redespachar é seguro). NÃO existe
    # redespacho automático: o servidor grava o run como 'cancelled' terminal e
    # ninguém o reenvia. Implementar re-dispatch exige mudança no servidor
    # (executor_ws_router._handle_job_result) — não presuma que já existe.
    NAO_INICIADO = "Job não iniciado — executor encerrando."

    async def shutdown(self, timeout: int = 120):
        """
        Graceful shutdown:
          1. Para de aceitar novos jobs
          2. Avisa o servidor NA HORA que entramos em drenagem
          3. Devolve (como cancelados) os jobs que ainda esperavam na fila
          4. Aguarda jobs em execução terminarem (máx timeout segundos)
          5. Cancela workers
        """
        self._shutting_down = True

        # Passo 2 ANTES de drenar a fila, e antes de qualquer espera: a partir da
        # linha acima `get_capacity()` anuncia saturação, mas quem envia é o
        # `_capacity_loop`, que dorme 10s ANTES de cada envio. Nessa janela o
        # `_resolve_candidates` do servidor ainda podia eleger este executor pelo
        # least-loaded, e o job voltava como "Executor em shutdown." — run FAILED
        # sem failover, que é exatamente o problema que o anúncio de saturação
        # existe para evitar. O empurrão imediato fecha a janela.
        await self._notify_draining()

        await self._drain_queued()
        logger.info("ExecutorJobQueue: aguardando jobs em execução (%ds timeout)...", timeout)

        try:
            await asyncio.wait_for(self._wait_for_running(), timeout=timeout)
        except asyncio.TimeoutError:
            abandoned = list(self._active_jobs.keys())
            logger.warning(
                "ExecutorJobQueue: timeout no shutdown — %d job(s) abandonado(s): %s",
                len(abandoned),
                abandoned,
            )

        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

        # Jobs que ainda restaram ativos após o cancelamento dos workers
        if self._active_jobs:
            logger.warning(
                "Executor encerrado com %d job(s) ainda em execução (serão marcados como falha pelo servidor): %s",
                len(self._active_jobs),
                list(self._active_jobs.keys()),
            )

        logger.info("ExecutorJobQueue encerrada.")

    async def _wait_for_running(self):
        await self._idle.wait()

    async def _drain_queued(self) -> None:
        """Esvazia a PriorityQueue avisando cada job que não vai rodar.

        `_wait_for_running` só enxerga `self._running`: os itens ainda na fila
        eram invisíveis e ninguém chamava `_notify_cancelled`. O servidor, que já
        marcou o run como 'running' ao despachar, acabava fechando tudo como
        "Executor desconectou durante a execucao" para jobs que nunca começaram.
        """
        pendentes: list[dict] = []
        while True:
            try:
                item: _QueueItem = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            # Balanceia o contador interno da fila — sem isto um `join()` futuro
            # nunca completaria.
            self._queue.task_done()
            pendentes.append(item.message)

        if not pendentes:
            return

        job_ids = [m.get("envelope", {}).get("job_id", "?") for m in pendentes]
        logger.warning(
            "ExecutorJobQueue: %d job(s) descartado(s) da fila no shutdown (nunca iniciaram): %s",
            len(job_ids), job_ids,
        )
        for message, job_id in zip(pendentes, job_ids):
            self._known.discard(job_id)
            self._cancelled.discard(job_id)
            await self._notify_cancelled(message, reason=self.NAO_INICIADO)

    # ── Enqueue ───────────────────────────────────────────────────────────────

    async def enqueue(self, message: dict) -> bool:
        """
        Coloca um job na fila.

        Retorna False (back-pressure) se:
          - Shutdown em andamento
          - Fila cheia (max_queue_size atingido)
        """
        if self._shutting_down:
            return False

        envelope = message.get("envelope", {})
        priority = envelope.get("priority", 5)
        item = _QueueItem(priority=priority, seq=next(self._seq), message=message)

        try:
            self._queue.put_nowait(item)
            self._known.add(envelope.get("job_id", "?"))
            return True
        except asyncio.QueueFull:
            logger.warning(
                "Fila do executor cheia (%d/%d) — back-pressure ativado.",
                self._queue.qsize(), self._max_queue,
            )
            return False

    # ── Worker ────────────────────────────────────────────────────────────────

    async def _worker(self, worker_id: int):
        logger.debug("Worker %d iniciado.", worker_id)
        while not self._shutting_down:
            try:
                item: _QueueItem = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            job_id = item.message.get("envelope", {}).get("job_id", "?")

            # Shutdown começou entre o `get()` e agora: o `_drain_queued()` já
            # passou e este item escapou da drenagem. Avisa em vez de executar —
            # senão o job rodaria com o executor encerrando e morreria no meio.
            if self._shutting_down:
                await self._discard_cancelled(item.message, job_id, reason=self.NAO_INICIADO)
                break

            # Cancelado enquanto esperava na fila — nem chega a executar.
            if self._take_cancelled(job_id):
                await self._discard_cancelled(item.message, job_id)
                continue

            async with self._semaphore:
                # Re-checa APÓS o semáforo: com o executor saturado um job fica
                # parado aqui por bastante tempo, e um cancelamento que chegasse
                # nessa janela se perdia — `cancel()` não encontrava task ativa,
                # marcava para descarte, e o worker já tinha passado da primeira
                # checagem. O job rodava até o fim enquanto a UI dizia
                # "cancelamento solicitado".
                if self._take_cancelled(job_id):
                    await self._discard_cancelled(item.message, job_id)
                    continue

                self._running += 1
                self._idle.clear()
                self._active_jobs[job_id] = item.message
                # Executa numa task própria para que `cancel()` tenha o que
                # cancelar — com `await self._on_execute(...)` direto não havia
                # handle e não existia forma de interromper um job em andamento.
                task = asyncio.create_task(self._on_execute(item.message), name=f"job-{job_id}")
                self._active_tasks[job_id] = task
                try:
                    await task
                except asyncio.CancelledError:
                    if task.cancelled():
                        # Cancelamento DESTE job (via cancel()). Não propaga:
                        # o worker segue vivo para o próximo item da fila.
                        logger.info("Job '%s' cancelado durante a execução.", job_id)
                        await self._notify_cancelled(item.message)
                    else:
                        # Quem está sendo cancelado é o WORKER (shutdown com
                        # timeout). Cancelar um `await task` NÃO cancela a task:
                        # sem este cancel explícito o job continuaria rodando
                        # órfão depois do encerramento — regressão em relação ao
                        # `await self._on_execute(...)` direto, que morria junto.
                        task.cancel()
                        raise
                except Exception as exc:
                    logger.error("Worker %d: erro ao executar job '%s': %s", worker_id, job_id, exc)
                finally:
                    self._running -= 1
                    if self._running == 0:
                        self._idle.set()
                    self._active_jobs.pop(job_id, None)
                    self._active_tasks.pop(job_id, None)
                    self._cancelled.discard(job_id)
                    self._known.discard(job_id)
                    self._queue.task_done()

        logger.debug("Worker %d encerrado.", worker_id)

    def _take_cancelled(self, job_id: str) -> bool:
        """Consome a marca de cancelamento do job, se existir."""
        if job_id in self._cancelled:
            self._cancelled.discard(job_id)
            return True
        return False

    async def _discard_cancelled(self, message: dict, job_id: str, reason: str | None = None) -> None:
        """Descarta um job cancelado antes de começar e fecha o item da fila."""
        logger.info("Job '%s' descartado (%s).", job_id, reason or "cancelado antes de iniciar")
        self._known.discard(job_id)
        await self._notify_cancelled(message, reason=reason)
        self._queue.task_done()

    def set_on_draining(self, callback: Callable[[], Coroutine[Any, Any, None]] | None) -> None:
        """Registra quem avisar quando a drenagem começar (ver `shutdown`)."""
        self._on_draining = callback

    async def _notify_draining(self) -> None:
        """Avisa o mundo externo que entramos em drenagem. Nunca levanta.

        Best-effort de propósito: se o WS já caiu, o servidor descobre pela
        ausência de heartbeat de qualquer jeito. Falhar aqui não pode impedir o
        shutdown de prosseguir — o aviso serve para economizar um job mal
        roteado, não é pré-requisito do encerramento.
        """
        if self._on_draining is None:
            return
        try:
            await self._on_draining()
        except Exception as exc:
            logger.warning("Falha ao anunciar drenagem ao servidor: %s", exc)

    async def _notify_cancelled(self, message: dict, reason: str | None = None) -> None:
        if self._on_cancelled is None:
            return
        if reason:
            # O motivo viaja dentro do próprio message porque a assinatura do
            # callback é pública (`on_cancelled(message)`) — mudá-la quebraria
            # todos os call sites. Cópia rasa: não mexemos no dict do caller.
            message = {**message, "cancel_reason": reason}
        try:
            await self._on_cancelled(message)
        except Exception as exc:
            logger.error("Falha ao notificar cancelamento do job: %s", exc)

    # ── Cancelamento ──────────────────────────────────────────────────────────

    def cancel(self, job_id: str) -> str:
        """Cancela um job em execução ou ainda enfileirado.

        Retorna "running" (task interrompida), "queued" (job conhecido, marcado
        para descarte quando um worker o pegar) ou "unknown" (não está nesta
        instância — nada foi marcado).
        """
        task = self._active_tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()
            logger.info("Cancelamento solicitado para job '%s' em execução.", job_id)
            return "running"

        # Não está executando. Só marca para descarte se o job for realmente
        # desta instância: pode estar na fila ou preso no semáforo (já saiu da
        # fila, ainda não virou task). Marcar ids desconhecidos fazia `_cancelled`
        # crescer para sempre e prometia um cancelamento que nunca aconteceria.
        if job_id in self._known:
            self._cancelled.add(job_id)
            logger.info("Job '%s' marcado para descarte na fila.", job_id)
            return "queued"

        logger.info("Cancelamento ignorado: job '%s' nao esta neste executor.", job_id)
        return "unknown"

    def job_ids_ativos(self) -> list[str]:
        """Jobs aceitos e ainda não finalizados: na fila, presos no semáforo ou
        em execução. É o inventário que o servidor confere — um run que ele acha
        que está aqui e não está nesta lista (nem com resultado pendente) se
        perdeu."""
        return sorted(self._known)

    async def encerrar_desconhecido(self, job_id: str, motivo: str) -> None:
        """Fecha um job que não está aqui: lápide + resultado 'cancelled' pelo
        mesmo caminho dos cancelamentos normais (`on_cancelled`)."""
        self.lapidar(job_id)
        await self._notify_cancelled({"envelope": {"job_id": job_id}}, reason=motivo)

    def lapidar(self, job_id: str) -> None:
        """Marca um job que foi cancelado sem estar aqui. Se ele chegar depois,
        `cancelado_antes_de_chegar` o descarta."""
        agora = time.monotonic()
        if len(self._lapides) >= _LAPIDE_MAX:
            for jid in [j for j, vence in self._lapides.items() if vence <= agora]:
                del self._lapides[jid]
            while len(self._lapides) >= _LAPIDE_MAX:
                # Dicionário mantém ordem de inserção: sai a lápide mais antiga.
                del self._lapides[next(iter(self._lapides))]
        self._lapides[job_id] = agora + _LAPIDE_TTL_S

    def cancelado_antes_de_chegar(self, job_id: str) -> bool:
        """True se o job foi cancelado (e fechado no servidor) antes de chegar.
        Consome a lápide."""
        vence = self._lapides.pop(job_id, None)
        return vence is not None and vence > time.monotonic()

    # ── Capacidade (para back-pressure e reporting) ───────────────────────────

    def get_capacity(self) -> dict:
        if self._shutting_down:
            # Drenando: o WS continua vivo por ate ~150s (jobs terminando +
            # resultados subindo) e o executor SEGUE no registry do servidor.
            # Reportar a carga real aqui era uma armadilha: `_drain_queued()`
            # esvazia a fila na hora e os jobs vao terminando, entao queued/running
            # DESPENCAM ate zero — e o `_resolve_candidates` de antes
            # (workflow_execution_service) ordenava o pool por running+queued.
            # O executor que esta morrendo virava o preferido do least-loaded e
            # todo job roteado para ele voltava como "Executor em shutdown."
            # (connection._handle_job), fechando o run como FAILED sem failover.
            #
            # Anunciamos saturacao: queued = teto da fila + teto de concorrencia.
            #   - cheio pela carga declarada -> o dispatch nos poe por ULTIMO
            #     (`_chave_de_ordem`, grupo dos cheios);
            #   - queued+running >= max_concurrent+max_queue -> `is_full()` do
            #     servidor (ExecutorConnection.is_full) da True e `send_job`
            #     recusa, fazendo o dispatch cair no proximo candidato.
            # Funciona mesmo com o clamp do servidor (`_sanitize_capacity` reduz
            # max_* para os limites do banco, nunca aumenta) — a soma clampada e
            # sempre <= o `queued` que declaramos.
            return {
                "queued":         self._max_queue + self._max_concurrent,
                "running":        self._running,
                "max_concurrent": self._max_concurrent,
                "max_queue":      self._max_queue,
            }
        return {
            "queued":        self._queue.qsize(),
            "running":       self._running,
            "max_concurrent": self._max_concurrent,
            "max_queue":     self._max_queue,
        }

    def is_full(self) -> bool:
        return self._queue.full()
