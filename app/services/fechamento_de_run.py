# app/services/fechamento_de_run.py
"""
Closing a run from the SERVER — without a job_result from the executor.

Nine paths close a run this way: dispatch (no executor accepted, the
isolation barrier, an exception midway), cancellation (run still in the
queue, or with the executor offline) and the watchers in `executor_ws/orfaos.py`
(executor that vanished, run stuck in 'pending' without delivery, job dropped in the
relay, run lost in the inventory reconciliation). Each had its own copy, and
they diverged: the dispatch ones assigned `run.status` and wrote by PK — the
"second writer" the others avoided — and did not publish the completion. The
rule lives here, the same for everyone:

1. Conditional UPDATE (compare-and-swap) on the status: only closes a run that is
   still in one of the `de` states (and, with `host`, on the given executor). An
   outcome another writer recorded first — the executor's job_result, the user's
   cancellation, another worker — is not overwritten, and the run is not counted
   twice.
2. Mirror onto the object without dirtying it (`set_committed_value`): a plain
   assignment would make the next flush re-emit the status by PK, which is exactly
   the second writer.
3. Accounting in usage_daily (`account_terminal_run`): these runs never
   go through the run_results queue.
4. `__workflow_complete__` (`publicar_conclusao`) for the open panel, once
   per run — only whoever won the UPDATE publishes. Best-effort: the run is already
   closed in the database, and the panel also finds out when it reopens.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core import run_result_consumer
from app.core.utils.logger import get_logger
from app.models.workflow_run import WorkflowRun
from app.services import run_events_service

logger = get_logger(__name__)

# The states of runs that have not finished yet.
ABERTOS = ("pending", "running")

# The completion event's `extra`, in the flow taxonomy, for runs that failed through
# no fault of the content (executor vanished, send never arrived, no executor accepted):
# repeating the execution is safe — the panel offers "tentar de novo" (try again).
REPETIVEL = {"error_category": "transient", "retryable": True}


async def fechar_runs(
    db: AsyncSession,
    runs: Iterable[WorkflowRun | str],
    *,
    de: tuple[str, ...],
    para: str,
    mensagem: str,
    categoria: str | None,
    host: str | None = None,
    duracao: bool = False,
    extra: dict | None = None,
) -> list[WorkflowRun]:
    """Closes as `para` the `runs` (session objects or task_ids) that are still
    in `de`; returns the ones THIS call closed, already mirrored.

    `categoria` goes to `error_category` (None on a cancellation — cancelling is not
    failing). `duracao` writes `duration_seconds` since `start_time`: it only makes
    sense for runs that actually ran. Commits the closing: the
    accounting and the publication only apply to what was written.
    """
    # Already terminal on the object: an outcome never goes back to pending/running, so
    # there is nothing to contend for — it is the run that dispatch just closed and that
    # then goes through the `except` safety net.
    runs = [run for run in runs if isinstance(run, str) or run.status in de]
    if not runs:
        return []
    agora = datetime.now(timezone.utc)
    valores = {"status": para, "error_message": mensagem, "error_category": categoria, "end_time": agora}

    fechados: list = []
    for run in runs:
        task_id = run if isinstance(run, str) else run.task_id
        deste = dict(valores)
        if duracao:
            deste["duration_seconds"] = _duracao(run, agora)
        condicao = [
            WorkflowRun.task_id == task_id,
            WorkflowRun.status == de[0] if len(de) == 1 else WorkflowRun.status.in_(de),
        ]
        if host is not None:
            condicao.append(WorkflowRun.host == host)
        resultado = await db.execute(
            update(WorkflowRun).where(*condicao).values(**deste)
            .execution_options(synchronize_session=False)
        )
        if resultado.rowcount:
            fechados.append((run, deste))
    await db.commit()
    if not fechados:
        return []

    objetos = await _objetos(db, fechados)
    task_ids = [run.task_id for run in objetos]
    # A failure in the accounting rolls back (see `account_terminal_run`), and the
    # rollback EXPIRES every object in the session: the next run would be counted
    # with expired attributes (and lost), and the caller would read `run.host` or
    # `run.task_id` on a stateless object — the cancel to the host and the panel's
    # completion did not go out. The closing is already written: reloading brings the same
    # outcome.
    for run in objetos:
        await _recarregar_se_expirou(db, run)
        await run_result_consumer.account_terminal_run(db, run)
    for run in objetos:
        await _recarregar_se_expirou(db, run)
    try:
        await run_events_service.publicar_conclusao(
            task_ids, status=para, mensagem=mensagem, extra=extra,
        )
    except Exception as exc:
        logger.warning(
            "Conclusão de %d run(s) fechado(s) no servidor não publicada: %s", len(objetos), exc,
        )
    return objetos


async def _recarregar_se_expirou(db: AsyncSession, run: WorkflowRun) -> None:
    estado = inspect(run)
    if estado.expired or estado.expired_attributes:
        await db.refresh(run)


async def _objetos(db: AsyncSession, fechados: list) -> list[WorkflowRun]:
    """The closed runs as objects, with what was written mirrored. Those that came
    by task_id are loaded in a single query."""
    por_id = [run for run, _ in fechados if isinstance(run, str)]
    carregados = {}
    if por_id:
        linhas = await db.execute(select(WorkflowRun).where(WorkflowRun.task_id.in_(por_id)))
        carregados = {r.task_id: r for r in linhas.scalars().all()}
    objetos = []
    for run, gravado in fechados:
        objeto = carregados.get(run) if isinstance(run, str) else run
        if objeto is None:
            continue
        for campo, valor in gravado.items():
            set_committed_value(objeto, campo, valor)
        objetos.append(objeto)
    return objetos


def _duracao(run, agora: datetime) -> float | None:
    inicio = getattr(run, "start_time", None)
    if inicio is None:
        return None
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    return round((agora - inicio).total_seconds(), 3)
