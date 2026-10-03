# app/core/async_scheduler.py
"""
AsyncScheduler — replacement for Celery Beat.

An asyncio loop that checks active schedules in the database every DB_RELOAD_INTERVAL
seconds and calls WorkflowService.start_analysis() directly, with no external workers.

Supported strategies:
  cron     — cron_expression "min hour day month dow" (via croniter)
  interval — interval + unit (seconds/minutes/hours/days)
  rrule    — rrule_expression RFC 5545 (via python-dateutil)

State persistence:
  next_run_at and last_run_at are saved to the schedules table on every trigger.
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

DB_RELOAD_INTERVAL = 30  # seconds between checks
# Ceiling on schedules processed per tick. Without it the tick loaded ALL the
# due ones at once; with the LIMIT + order_by(next_run_at) the backlog is drained
# in batches per cycle, and the SKIP LOCKED in _process_schedule already keeps two
# workers from colliding on the same batch.
TICK_MAX_SCHEDULES = 200


class AsyncScheduler:
    """
    Manages workflow schedules without Celery Beat.

    Usage (in the API lifespan):
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
        """Checks every active schedule and triggers the ones that are due."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with AsyncSessionLocal() as db:
            # PERF: the time cutoff happens in SQL, not in Python. Before, the tick
            # loaded ALL active schedules and discarded the ones not yet due
            # in `_process_schedule` — after having already opened a session and
            # issued a SELECT ... FOR UPDATE for each one of them.
            #
            # The supporting index already existed and had never been used:
            # `ix_schedules_active_nextrun` on (active, next_run_at ASC), created
            # in 20260324_1400_add_performance_indexes.py with the comment
            # "Scheduler poll a cada 30s: filtra active=true + next_run_at <= now()".
            #
            # `next_run_at IS NULL` has to be included: the column is nullable and
            # `_process_schedule` itself uses NULL as the signal for "new
            # schedule, compute the first run". Filtering only by `<= now`
            # would leave those schedules stuck forever.
            #
            # The JOIN with Workflow is the final lock against an orphan schedule: an
            # active Schedule pointing to a deactivated (or soft-deleted) workflow
            # made the tick take the lock, open a session and call start_analysis only
            # to reap WorkflowInactiveError — again on every cron occurrence,
            # forever. The paths that produced that state have been
            # closed (`sync_schedules_with_workflow_state`), but the scheduler
            # must not depend on that: here it simply does not see
            # schedules of workflows that cannot run.
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
                # Drains the backlog in batches: new schedules (next_run_at NULL) first
                # — so their first occurrence gets computed right away —, then the most
                # overdue. Without the LIMIT the tick loaded ALL the due ones at
                # once, opening a session and a lock for each.
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
            # SELECT FOR NO KEY UPDATE SKIP LOCKED — only one worker processes each
            # schedule. If another worker has already locked this row, scalar_one_or_none()
            # returns None and this instance simply skips it (no blocking and no
            # duplication).
            #
            # `key_share=True` (→ FOR NO KEY UPDATE, not FOR UPDATE) is what avoids
            # a SELF-DEADLOCK invisible to the Postgres detector: this SELECT opens
            # a transaction and keeps it open while `_fire_workflow` runs IN
            # ANOTHER session/connection. That trigger inserts a `WorkflowRun` with an FK
            # to `schedules.id` (schedule_id), and every INSERT with an FK requests a
            # `FOR KEY SHARE` on the referenced row. FOR UPDATE conflicts with
            # FOR KEY SHARE → the trigger's connection blocks waiting for the row that
            # THIS transaction holds, but this transaction is `await`-ing the
            # trigger to finish: mutual lock. Since the outer connection is
            # idle-in-transaction (it waits on no lock at the database level), the
            # PG deadlock detector never sees it and the tick hangs until the
            # timeout. FOR NO KEY UPDATE does NOT conflict with FOR KEY SHARE — it keeps the
            # "one worker per schedule" exclusivity (it only clashes with another
            # FOR/NO KEY/UPDATE) and lets the run's INSERT through.
            result = await db.execute(
                select(Schedule)
                .where(Schedule.id == sched.id)
                .with_for_update(skip_locked=True, key_share=True)
            )
            s = result.scalar_one_or_none()
            if s is None or not s.active:
                return

            # Initializes next_run_at if it is not set
            if s.next_run_at is None:
                s.next_run_at = self._compute_next(s, now)
                await db.commit()
                return

            # Not time yet
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
                # Updates timestamps and releases the lock (commit ends the FOR UPDATE transaction)
                s.last_run_at = now
                s.next_run_at = self._compute_next(s, now)
                await db.commit()

    # ── Workflow triggering ────────────────────────────────────────────────────

    async def _fire_workflow(self, workflow_hash: str, *, schedule_id: int | None = None) -> None:
        """Calls start_analysis in its own session.

        No executor available (spec §7.4): the occurrence does NOT vanish. A
        `failed` `WorkflowRun` stays in the history, with the policy's message, and the
        owner is notified on transitions (1st failure of the window, reminder every 6 h,
        recovery). Before, the exception was swallowed by the loop and only
        `next_run_at` advanced — a cron whose group (or pool) was down vanished.
        """
        from app.core.exceptions import NoExecutorAvailableError
        from app.services import execution_alert_service
        from app.services.workflow_service import WorkflowService

        async with AsyncSessionLocal() as db:
            service = WorkflowService(db)
            wf = await service.get_workflow_by_hash(workflow_hash)
            try:
                # There is no HTTP request at all in a scheduled trigger: requiring the
                # trigger token here would raise 401 ("Request HTTP é necessário")
                # in every workflow that combines a schedule with a webhook trigger.
                await service.start_analysis(
                    workflow_hash, inputs={}, autenticar_entrada=False, workflow=wf,
                    # Run label: before, the `schedule_id` only reached the database
                    # when the schedule FAILED; the happy path was
                    # indistinguishable from a manual trigger in the History.
                    trigger_source="schedule", schedule_id=schedule_id,
                )
            except NoExecutorAvailableError as exc:
                # If the dispatch already created (and closed) a run for this occurrence,
                # it is the record — a second one would make the history and
                # usage_daily count the same failure twice.
                if getattr(exc, "run_id", None) is None:
                    await self._record_scheduled_failure(
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
                    except Exception as alert_exc:  # best-effort
                        logger.warning("AsyncScheduler: falha ao alertar sobre '%s': %s", workflow_hash, alert_exc)
                raise
            except Exception as exc:
                # Any OTHER failure of the scheduled dispatch (validation, database
                # error, timeout, ...): before, it bubbled up to the loop, was only logged, and the
                # `finally` of `_process_schedule` advanced `next_run_at` — the
                # occurrence vanished with no run and no alert. Materializes the same visible
                # failure that the no-executor path records. `internal` is the
                # only legal category (≤16 chars) for a generic error. The
                # `getattr(run_id)` mirrors the no-executor guard: if the dispatch
                # already created the run, it does not duplicate it.
                if getattr(exc, "run_id", None) is None:
                    await self._record_scheduled_failure(
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
                    except Exception as alert_exc:  # best-effort
                        logger.warning("AsyncScheduler: falha ao alertar sobre '%s': %s", workflow_hash, alert_exc)
                raise
            if schedule_id is not None:
                try:
                    await execution_alert_service.record_success(db, schedule_id=schedule_id, workflow=wf)
                except Exception as alert_exc:  # best-effort
                    logger.warning("AsyncScheduler: falha ao registrar recuperação de '%s': %s", workflow_hash, alert_exc)

    async def _record_scheduled_failure(
        self, db, wf, schedule_id, *, category: str, message: str,
    ) -> None:
        """Materializes a missed scheduled occurrence as a visible `failed` run.

        Nobody sees the exception of a scheduled trigger (there is no HTTP request):
        without this row, the failure would exist nowhere — only a log line and
        `next_run_at` advancing. Covers the lack of an executor (`no_executor`) and
        any other `start_analysis` failure (`internal`). When
        `_dispatch_job` has already created the occurrence's run (`exc.run_id`), the caller
        does NOT come through here, so the same failure is not counted twice."""
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

    # ── Next run computation ───────────────────────────────────────────────────

    def _tz_of(self, sched: Schedule) -> tzinfo:
        """Timezone configured on the schedule, with a fallback to the product default.

        The fallback was **UTC**, and that was not a choice — it was the `datetime`
        default. But the rest of the product operates in `America/…` (the
        `ScheduleTrigger` node and the schema send UTC−4), so a schedule with a
        null column fired FOUR HOURS later than the screen said, with nothing to
        explain the difference. The most visible case: "0 9 * * *" on the screen, and the
        run at 5 a.m.

        This method answers a single question — "I don't know this
        schedule's timezone; which one do I use?" —, so both of its outcomes (empty column and
        unreadable value) lead to the same constant. The unreadable case still
        warns in the log, because there someone typed something and deserves to know it
        didn't take.

        Changing this **recreates no schedule at all**: the fallback does not take part in
        `_same_configuration` (`app/core/scheduling/hooks.py`), which compares the
        STORED value with what the node sends. Anyone with the column filled in
        feels nothing.
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
            # Interval is a sum of deltas — independent of timezone.
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
        """Naive UTC (the loop's internal convention) -> aware in the schedule's timezone."""
        return after.replace(tzinfo=timezone.utc).astimezone(tz)

    @staticmethod
    def _to_utc_naive(moment: datetime) -> datetime:
        """Aware -> UTC naive, formato gravado em Schedule.next_run_at."""
        return moment.astimezone(timezone.utc).replace(tzinfo=None)

    def _cron_next(self, expression: str, after: datetime, tz: tzinfo) -> datetime | None:
        """Next cron occurrence IN THE SCHEDULE'S TIMEZONE.

        The computation was done directly on `after` (naive UTC) and the
        `timezone` column was written but never read: "0 13 * * *" fired at 13:00 UTC,
        that is, 9:00 in America/Cuiaba. Anyone who configured the time via the UI never
        saw the workflow run at the chosen time.
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
        """Same timezone fix as cron — BYHOUR is also local time."""
        try:
            from dateutil.rrule import rrulestr
            after_local = self._to_local(after, tz)
            rule = rrulestr(expression, dtstart=after_local)
            proximo = rule.after(after_local)
            return self._to_utc_naive(proximo) if proximo else None
        except Exception as exc:
            logger.warning("AsyncScheduler: rrule inválida '%s': %s", expression, exc)
            return None


# Singleton — imported by the API lifespan
scheduler = AsyncScheduler()
