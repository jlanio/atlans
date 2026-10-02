# app/core/async_scheduler.py
"""
AsyncScheduler — substituto do Celery Beat.

Loop asyncio que verifica schedules ativos no banco a cada DB_RELOAD_INTERVAL
segundos e dispara WorkflowService.start_analysis() diretamente, sem workers externos.

Estratégias suportadas:
  cron     — cron_expression "min hour day month dow" (via croniter)
  interval — interval + unit (seconds/minutes/hours/days)
  rrule    — rrule_expression RFC 5545 (via python-dateutil)

Persistência de estado:
  next_run_at e last_run_at são salvos na tabela schedules a cada disparo.
"""

import asyncio
from app.core.utils.logger import get_logger
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select

from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.core.db import AsyncSessionLocal
from app.models.models import Schedule, Workflow

logger = get_logger(__name__)

DB_RELOAD_INTERVAL = 30  # segundos entre verificações
# Teto de schedules processados por tick. Sem ele o tick carregava TODOS os
# vencidos de uma vez; com o LIMIT + order_by(next_run_at) o backlog é drenado
# em lotes por ciclo, e o SKIP LOCKED do _process_schedule já impede que dois
# workers colidam no mesmo lote.
TICK_MAX_SCHEDULES = 200


class AsyncScheduler:
    """
    Gerencia agendamentos de workflows sem Celery Beat.

    Uso (no lifespan da API):
        scheduler = AsyncScheduler()
        await scheduler.start()
        ...
        await scheduler.stop()
    """

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="async-scheduler")
        logger.info("AsyncScheduler iniciado (intervalo=%ds).", DB_RELOAD_INTERVAL)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AsyncScheduler encerrado.")

    # ── Loop principal ─────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("AsyncScheduler: erro no tick: %s", exc, exc_info=True)
            await asyncio.sleep(DB_RELOAD_INTERVAL)

    async def _tick(self) -> None:
        """Verifica todos os schedules ativos e dispara os que estão devidos."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with AsyncSessionLocal() as db:
            # PERF: o corte por horário vai no SQL, não em Python. Antes o tick
            # carregava TODOS os schedules ativos e descartava os não-vencidos
            # em `_process_schedule` — depois de já ter aberto uma sessão e
            # emitido um SELECT ... FOR UPDATE para cada um deles.
            #
            # O índice de apoio já existia sem nunca ter sido usado:
            # `ix_schedules_active_nextrun` em (active, next_run_at ASC), criado
            # em 20260324_1400_add_performance_indexes.py com o comentário
            # "Scheduler poll a cada 30s: filtra active=true + next_run_at <= now()".
            #
            # `next_run_at IS NULL` precisa entrar: a coluna é nullable e o
            # próprio `_process_schedule` usa o NULL como sinal de "schedule
            # novo, calcular a primeira execução". Filtrar só por `<= now`
            # deixaria esses schedules parados para sempre.
            #
            # O JOIN com Workflow é a trava final contra schedule órfão: um
            # Schedule ativo apontando para workflow desativado (ou soft-deletado)
            # fazia o tick pegar o lock, abrir sessão e chamar start_analysis só
            # para colher WorkflowInactiveError — de novo a cada ocorrência do
            # cron, para sempre. Os caminhos que produziam esse estado foram
            # fechados (`sync_schedules_with_workflow_state`), mas o scheduler
            # não deve depender disso: aqui ele simplesmente não enxerga
            # agendamento de workflow que não pode executar.
            result = await db.execute(
                select(Schedule)
                .join(Workflow, Workflow.id_hash == Schedule.workflow_hash)
                .where(
                    Schedule.active.is_(True),
                    Workflow.flag_ative.is_(True),
                    Workflow.deleted_at.is_(None),
                    or_(
                        Schedule.next_run_at.is_(None),
                        Schedule.next_run_at <= now,
                    ),
                )
                # Drena o backlog em lotes: schedule novo (next_run_at NULL) primeiro
                # — para ter a primeira ocorrência calculada logo —, depois os mais
                # atrasados. Sem o LIMIT o tick carregava TODOS os vencidos de uma
                # vez, abrindo sessão e lock por cada um.
                .order_by(Schedule.next_run_at.asc().nulls_first())
                .limit(TICK_MAX_SCHEDULES)
            )
            schedules = result.scalars().all()

        for sched in schedules:
            try:
                await self._process_schedule(sched, now)
            except Exception as exc:
                logger.error(
                    "AsyncScheduler: erro ao processar schedule '%s': %s",
                    sched.job_id, exc, exc_info=True,
                )

    async def _process_schedule(self, sched: Schedule, now: datetime) -> None:
        async with AsyncSessionLocal() as db:
            # SELECT FOR NO KEY UPDATE SKIP LOCKED — apenas um worker processa cada
            # schedule. Se outro worker já travou esta linha, scalar_one_or_none()
            # retorna None e esta instância simplesmente ignora (sem bloqueio nem
            # duplicação).
            #
            # `key_share=True` (→ FOR NO KEY UPDATE, não FOR UPDATE) é o que evita
            # um AUTO-DEADLOCK invisível ao detector do Postgres: este SELECT abre
            # uma transação e a mantém aberta enquanto `_fire_workflow` roda EM
            # OUTRA sessão/conexão. Esse disparo insere um `WorkflowRun` com FK
            # para `schedules.id` (schedule_id), e todo INSERT com FK pede um
            # `FOR KEY SHARE` na linha referenciada. FOR UPDATE conflita com
            # FOR KEY SHARE → a conexão do disparo bloqueia esperando a linha que
            # ESTA transação segura, mas esta transação está `await`-ando o
            # disparo terminar: trava mútua. Como a conexão de fora fica
            # idle-in-transaction (não espera lock nenhum no nível do banco), o
            # detector de deadlock do PG nunca a vê e o tick fica pendurado até o
            # timeout. FOR NO KEY UPDATE NÃO conflita com FOR KEY SHARE — mantém a
            # exclusividade de "um worker por schedule" (só bate em outro
            # FOR/NO KEY/UPDATE) e deixa o INSERT do run passar.
            result = await db.execute(
                select(Schedule)
                .where(Schedule.id == sched.id)
                .with_for_update(skip_locked=True, key_share=True)
            )
            s = result.scalar_one_or_none()
            if s is None or not s.active:
                return

            # Inicializa next_run_at se não estiver definido
            if s.next_run_at is None:
                s.next_run_at = self._compute_next(s, now)
                await db.commit()
                return

            # Ainda não é hora
            if now < s.next_run_at:
                return

            # ── Disparo ───────────────────────────────────────────────────────
            logger.info(
                "AsyncScheduler: disparando workflow '%s' (schedule '%s').",
                s.workflow_hash, s.job_id,
            )
            try:
                await self._fire_workflow(s.workflow_hash, schedule_id=s.id)
                logger.info("AsyncScheduler: workflow '%s' despachado.", s.workflow_hash)
            except Exception as exc:
                logger.error(
                    "AsyncScheduler: falha ao disparar workflow '%s': %s",
                    s.workflow_hash, exc,
                )
            finally:
                # Atualiza timestamps e libera o lock (commit encerra a transação FOR UPDATE)
                s.last_run_at = now
                s.next_run_at = self._compute_next(s, now)
                await db.commit()

    # ── Disparo de workflow ────────────────────────────────────────────────────

    async def _fire_workflow(self, workflow_hash: str, *, schedule_id: int | None = None) -> None:
        """Dispara start_analysis em sessão própria.

        Sem executor disponível (spec §7.4): a ocorrência NÃO some. Fica um
        `WorkflowRun` `failed` no histórico, com a mensagem da política, e o
        dono é avisado por transição (1ª falha da janela, lembrete a cada 6 h,
        recuperação). Antes, a exceção era engolida pelo laço e só o
        `next_run_at` avançava — um cron com o grupo (ou o pool) fora sumia.
        """
        from app.core.exceptions import NoExecutorAvailableError
        from app.services import execution_alert_service
        from app.services.workflow_service import WorkflowService

        async with AsyncSessionLocal() as db:
            service = WorkflowService(db)
            wf = await service.get_workflow_by_hash(workflow_hash)
            try:
                # Não há requisição HTTP nenhuma num disparo agendado: exigir o
                # token do gatilho aqui levantaria 401 ("Request HTTP é necessário")
                # em todo fluxo que combine agendamento com gatilho de webhook.
                await service.start_analysis(
                    workflow_hash, inputs={}, autenticar_entrada=False, workflow=wf,
                    # Rótulo do run: antes o `schedule_id` só chegava ao banco
                    # quando o agendamento FALHAVA; o caminho feliz ficava
                    # indistinguível de um disparo manual no Histórico.
                    trigger_source="schedule", schedule_id=schedule_id,
                )
            except NoExecutorAvailableError as exc:
                # Se o dispatch já criou (e fechou) um run para esta ocorrência,
                # ele é o registro — um segundo faria o histórico e o
                # usage_daily contarem a mesma falha duas vezes.
                if getattr(exc, "run_id", None) is None:
                    await self._registrar_falha_agendada(
                        db, wf, schedule_id,
                        category="no_executor",
                        message=f"Execução agendada não despachada: {exc.detail}",
                    )
                if schedule_id is not None:
                    try:
                        await execution_alert_service.record_failure(
                            db, schedule_id=schedule_id, workflow=wf,
                            reason=exc.detail, category=exc.category,
                        )
                    except Exception as alerta_exc:  # best-effort
                        logger.warning("AsyncScheduler: falha ao alertar sobre '%s': %s", workflow_hash, alerta_exc)
                raise
            except Exception as exc:
                # Qualquer OUTRA falha do dispatch agendado (validação, erro de
                # banco, timeout, ...): antes subia ao laço, só era logada, e o
                # `finally` de `_process_schedule` avançava `next_run_at` — a
                # ocorrência sumia sem run nem alerta. Materializa a mesma falha
                # visível que o caminho sem-executor registra. `internal` é a
                # única categoria legal (≤16 chars) para um erro genérico. O
                # `getattr(run_id)` espelha o guard do sem-executor: se o dispatch
                # já criou o run, não duplica.
                if getattr(exc, "run_id", None) is None:
                    await self._registrar_falha_agendada(
                        db, wf, schedule_id,
                        category="internal",
                        message=f"Execução agendada falhou: {exc}",
                    )
                if schedule_id is not None:
                    try:
                        await execution_alert_service.record_failure(
                            db, schedule_id=schedule_id, workflow=wf,
                            reason=str(exc), category="internal",
                        )
                    except Exception as alerta_exc:  # best-effort
                        logger.warning("AsyncScheduler: falha ao alertar sobre '%s': %s", workflow_hash, alerta_exc)
                raise
            if schedule_id is not None:
                try:
                    await execution_alert_service.record_success(db, schedule_id=schedule_id, workflow=wf)
                except Exception as alerta_exc:  # best-effort
                    logger.warning("AsyncScheduler: falha ao registrar recuperação de '%s': %s", workflow_hash, alerta_exc)

    async def _registrar_falha_agendada(
        self, db, wf, schedule_id, *, category: str, message: str,
    ) -> None:
        """Materializa uma ocorrência agendada perdida como run `failed` visível.

        Um disparo agendado não tem quem veja a exceção (não há requisição HTTP):
        sem esta linha, a falha não existiria em lugar nenhum — só um log e o
        `next_run_at` avançando. Cobre a falta de executor (`no_executor`) e
        qualquer outra falha do `start_analysis` (`internal`). Quando o
        `_dispatch_job` já criou o run da ocorrência (`exc.run_id`), o chamador
        NÃO passa por aqui, para não contar a mesma falha duas vezes."""
        import uuid
        from datetime import datetime, timezone

        from app.core.run_result_consumer import account_terminal_run
        from app.models.workflow_run import WorkflowRun

        try:
            agora = datetime.now(timezone.utc)
            run = WorkflowRun(
                task_id=str(uuid.uuid4()),
                workflow_hash=wf.id_hash,
                workspace_id=wf.workspace_id,
                schedule_id=schedule_id,
                status="failed",
                host=None,
                dispatch_tier=None,
                trigger_source="schedule",
                error_category=category,
                node_stats={},
                error_message=message,
                end_time=agora,
                duration_seconds=0.0,
            )
            db.add(run)
            await db.commit()
            await account_terminal_run(db, run)
        except Exception as reg_exc:
            logger.error(
                "AsyncScheduler: não foi possível registrar a falha agendada de '%s': %s",
                getattr(wf, "id_hash", "?"), reg_exc,
            )

    # ── Cálculo de próxima execução ────────────────────────────────────────────

    def _tz_of(self, sched: Schedule) -> tzinfo:
        """Fuso configurado no schedule, com fallback para o padrão do produto.

        O fallback era **UTC**, e isso não era uma escolha — era o default do
        `datetime`. Só que todo o resto do produto opera em `America/…` (o nó
        `ScheduleTrigger` e o schema mandam UTC−4), então um schedule de coluna
        nula disparava QUATRO HORAS depois do que a tela dizia, sem nada que
        explicasse a diferença. O caso mais visível: "0 9 * * *" na tela, e a
        execução às 5h da manhã.

        A pergunta que este método responde é uma só — "não sei o fuso deste
        agendamento; qual uso?" —, então as duas saídas dela (coluna vazia e
        valor ilegível) dão na mesma constante. O caso ilegível continua
        avisando no log, porque ali alguém digitou algo e merece saber que não
        pegou.

        Mudar isto **não recria schedule nenhum**: o fallback não participa do
        `_mesma_configuracao` (`app/core/scheduling/hooks.py`), que compara o
        valor GRAVADO com o que o nó envia. Quem tem a coluna preenchida não
        sente nada.
        """
        name = (sched.timezone or "").strip()
        if not name:
            return ZoneInfo(FUSO_PADRAO_DO_AGENDAMENTO)
        try:
            return ZoneInfo(name)
        except Exception as exc:
            logger.warning(
                "AsyncScheduler: timezone inválido '%s' no schedule '%s' (%s) — usando %s.",
                name, sched.job_id, exc, FUSO_PADRAO_DO_AGENDAMENTO,
            )
            return ZoneInfo(FUSO_PADRAO_DO_AGENDAMENTO)

    def _compute_next(self, sched: Schedule, after: datetime) -> datetime | None:
        if sched.strategy == "cron" and sched.cron_expression:
            return self._cron_next(sched.cron_expression, after, self._tz_of(sched))
        elif sched.strategy == "interval" and sched.interval and sched.unit:
            # Intervalo e uma soma de delta — independe de fuso.
            return self._interval_next(sched.interval, sched.unit, after)
        elif sched.strategy == "rrule" and sched.rrule_expression:
            return self._rrule_next(sched.rrule_expression, after, self._tz_of(sched))
        logger.warning(
            "AsyncScheduler: schedule '%s' sem estratégia válida (strategy=%s).",
            sched.job_id, sched.strategy,
        )
        return None

    @staticmethod
    def _to_local(after: datetime, tz: tzinfo) -> datetime:
        """UTC naive (convencao interna do loop) -> aware no fuso do schedule."""
        return after.replace(tzinfo=timezone.utc).astimezone(tz)

    @staticmethod
    def _to_utc_naive(moment: datetime) -> datetime:
        """Aware -> UTC naive, formato gravado em Schedule.next_run_at."""
        return moment.astimezone(timezone.utc).replace(tzinfo=None)

    def _cron_next(self, expression: str, after: datetime, tz: tzinfo) -> datetime | None:
        """Proxima ocorrencia do cron NO FUSO DO SCHEDULE.

        O calculo era feito direto sobre `after` (UTC naive) e a coluna
        `timezone` era gravada mas nunca lida: "0 13 * * *" disparava as 13h UTC,
        ou seja, 9h em America/Cuiaba. Quem configurava o horario via UI nunca
        via o workflow rodar na hora escolhida.
        """
        try:
            from croniter import croniter
            itr = croniter(expression, self._to_local(after, tz))
            return self._to_utc_naive(itr.get_next(datetime))
        except Exception as exc:
            logger.warning("AsyncScheduler: cron inválido '%s': %s", expression, exc)
            return None

    def _interval_next(self, interval: int, unit: str, after: datetime) -> datetime | None:
        seconds_map = {
            "seconds": interval,
            "minutes": interval * 60,
            "hours":   interval * 3600,
            "days":    interval * 86400,
        }
        seconds = seconds_map.get(unit)
        if not seconds:
            logger.warning("AsyncScheduler: unidade inválida '%s'.", unit)
            return None
        return after + timedelta(seconds=seconds)

    def _rrule_next(self, expression: str, after: datetime, tz: tzinfo) -> datetime | None:
        """Mesma correção de fuso do cron — BYHOUR também é hora local."""
        try:
            from dateutil.rrule import rrulestr
            after_local = self._to_local(after, tz)
            rule = rrulestr(expression, dtstart=after_local)
            proximo = rule.after(after_local)
            return self._to_utc_naive(proximo) if proximo else None
        except Exception as exc:
            logger.warning("AsyncScheduler: rrule inválida '%s': %s", expression, exc)
            return None


# Singleton — importado pelo lifespan da API
scheduler = AsyncScheduler()
