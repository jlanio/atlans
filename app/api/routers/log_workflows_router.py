import asyncio
from contextlib import aclosing

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.api.dependencies import check_ws_rate_limit, ws_authenticate
from app.core.utils.logger import get_logger
# The subscribe → LRANGE → dedup → pub/sub loop lives in `run_events_service`
# (MCP consumes it without a socket). Only what THIS handler calls comes in from
# there: the batch generator and the exception that decides the close code. The
# loop's details (buffer, markers, batch sizes) belong to the service and whoever
# needs them imports them from there — re-exporting them here made this module look
# like the owner of a loop it no longer has.
from app.services.run_events_service import RunEventsUnavailable, iter_run_events

logger = get_logger(__name__)
router = APIRouter()

# Short poll to tolerate light-replica read-after-write: the run is created
# SYNCHRONOUSLY in POST /execute, but the master may have committed before the
# replica replicated.
_WS_POLL_ATTEMPTS = 5
_WS_POLL_INTERVAL = 0.2

# Lifetime ceiling of an events socket. The old loop had no ceiling: the socket
# lived until `__workflow_complete__` or until the tab closed. `iter_run_events`
# requires a deadline (MCP needs it), so the WS passes a generous one — larger
# than any legitimate run — only so that an orphan subscriber of a run that
# never publishes the marker (dead consumer) is not stuck forever. When it
# expires, the socket closes with 1000 and the UI reopens as it does today.
_WS_MAX_S = 24 * 3600.0


def _batch_frame(events: list[str], dropped: int = 0) -> str:
    """Builds `{"type":"events","dropped":N,"events":[...]}` from the RAWs.

    SINGLE ENVELOPE: historical replay and live stream use exactly the same
    format. The old envelope said "replay" for live too, and the client
    decided by the envelope — the immediate-completion path (drain synchronously on
    seeing `__workflow_complete__`) only existed in the raw event format, so with
    the tab in the background the run got stuck on "Executando" (Running). Now the
    client decides by the batch CONTENT and there is no `{"type":"live"}` marker anymore.

    `dropped` is ALWAYS sent (0 included) so the client can add it up without checking
    `undefined`: silently truncating makes the "Bruto" (Raw) tab look complete.

    The items are already valid JSON: doing json.loads to look at a field and
    ws.send_json right after cost 2×N serializations and N frames. Here it is a
    string concatenation and a single frame.
    """
    return '{"type":"events","dropped":%d,"events":[%s]}' % (dropped, ",".join(events))


async def _authorize_run(db, run_id: str, user_id_hash: str) -> tuple[bool, bool]:
    """(run_existe, tem_acesso) in ONE round-trip.

    Previously there were up to four DB sessions in series in the handshake — one per
    poll attempt, plus owner, plus member — all before the first event byte.

    SEC: the LEFT JOIN on Workspace carries `deleted_at IS NULL`, so a workspace
    in the trash does not match and `tem_acesso` comes out False for both the owner
    and the member (WorkspaceMember only goes away on purge).
    """
    from sqlalchemy import and_, case, or_, select
    from app.models.models import WorkflowRun
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    stmt = (
        select(
            WorkflowRun.workspace_id,
            case(
                (
                    and_(
                        Workspace.id.isnot(None),
                        or_(
                            Workspace.owner_id == user_id_hash,
                            WorkspaceMember.id.isnot(None),
                        ),
                    ),
                    True,
                ),
                else_=False,
            ).label("has_access"),
        )
        .select_from(WorkflowRun)
        .outerjoin(
            Workspace,
            and_(
                Workspace.id_hash == WorkflowRun.workspace_id,
                Workspace.deleted_at.is_(None),
            ),
        )
        .outerjoin(
            WorkspaceMember,
            and_(
                WorkspaceMember.workspace_id == WorkflowRun.workspace_id,
                WorkspaceMember.user_id == user_id_hash,
            ),
        )
        .where(WorkflowRun.task_id == run_id)
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return False, False
    return True, bool(row.has_access)


@router.websocket("/ws/workflow/{run_id}")
async def websocket_workflow(ws: WebSocket, run_id: str):
    # 1) Accept + authenticate via the first message (JWT in the body, not in the query).
    #    ws_authenticate does the accept() internally.
    user = await ws_authenticate(ws, scope="workflow")
    if user is None:
        return
    user_id_hash = user.id_hash

    # 2) Rate limit per USER, not per IP: behind Traefik the IP is the proxy's
    #    for everyone. Runs before the database so a burst does not cost
    #    queries. The ceiling is loose because the UI reopens the socket on every
    #    workflow switch (and StrictMode doubles the openings in dev).
    if not await check_ws_rate_limit(
        ws, scope="workflow", identity=user_id_hash, limit=120, period=60
    ):
        return

    # 3) Does the run belong to a workspace this user can reach?
    try:
        from app.core.db import get_session_async

        exists = has_access = False
        start = asyncio.get_running_loop().time()
        # A single session for all attempts: in READ COMMITTED each
        # statement takes a fresh snapshot, so the retry sees the late commit
        # without needing a connection checkout per attempt.
        async with get_session_async() as db:
            for attempt in range(_WS_POLL_ATTEMPTS):
                exists, has_access = await _authorize_run(db, run_id, user_id_hash)
                if exists:
                    break
                # Without this guard the last cycle slept 200 ms before giving up
                # — pure delay added to a 4404 that was already decided.
                if attempt < _WS_POLL_ATTEMPTS - 1:
                    # Return the connection to the pool BEFORE sleeping: the first
                    # execute opens a transaction and the AsyncSession stays "idle in
                    # transaction" during the sleeps. Several panels reopening
                    # together (slow consumer) held N connections for up to 800 ms
                    # without using any, competing with the rest of the API.
                    await db.rollback()
                    await asyncio.sleep(_WS_POLL_INTERVAL)

        if not exists:
            elapsed = asyncio.get_running_loop().time() - start
            # Explicit log for diagnosis: without it the backend only records a generic
            # "connection closed" — the operator cannot tell 4404 from a
            # normal close. Goes to WARN because it indicates a race between POST /execute
            # and run_result_consumer (slow or stopped).
            logger.warning(
                "WS /ws/workflow/%s: 4404 (Run nao encontrado apos %.1fs). "
                "Possivel atraso do run_result_consumer ou DB lento.",
                run_id, elapsed,
            )
            await ws.close(code=4404, reason="Run não encontrado.")
            return
        if not has_access:
            await ws.close(code=4403, reason="Acesso negado a este run.")
            return
    except Exception as exc:
        logger.error(
            "Erro na verificacao de acesso ao run '%s' (user=%s): %s",
            run_id, user_id_hash, exc,
        )
        await ws.close(code=4500, reason="Erro interno na verificação de acesso.")
        return

    # 4) Forwards the batches from `iter_run_events` (replay + live) to the socket.
    logger.info("WS /ws/workflow/%s: subscribed user=%s", run_id, user_id_hash)

    # Close code decided by the error branches. 1000 is a normal
    # shutdown and the client ignores it on purpose; a server failure must go out
    # as 4500, otherwise the panel stays on "Executando" forever with no toast.
    close_code = 1000
    close_reason = ""
    try:
        await _forward_events(ws, run_id)
    except WebSocketDisconnect as exc:
        # Tab closed in the middle of a send: normal path, not a server failure.
        logger.debug("WS /ws/workflow/%s encerrado pelo cliente: %s", run_id, exc)
    except RunEventsUnavailable as exc:
        # Redis down (or pool without lifespan) with the socket alive: server error.
        # Treating it as "tab closed" hid the failure in a DEBUG and the panel
        # opened empty, stuck on "Executando", without a single error in the log.
        logger.error("Erro no WebSocket do workflow %s: %s", run_id, exc, exc_info=True)
        close_code, close_reason = 4500, "Erro interno no stream de eventos."
    except RuntimeError as exc:
        # RuntimeError here is Starlette sending on an already closed socket (tab
        # closed — normal). If the socket is still alive on both sides, that is not
        # the case and the failure is the server's.
        if WebSocketState.DISCONNECTED in (ws.client_state, ws.application_state):
            logger.debug("WS /ws/workflow/%s encerrado pelo cliente: %s", run_id, exc)
        else:
            logger.error(
                "Erro no WebSocket do workflow %s: %s", run_id, exc, exc_info=True,
            )
            close_code, close_reason = 4500, "Erro interno no stream de eventos."
    except Exception as exc:
        logger.error("Erro no WebSocket do workflow %s: %s", run_id, exc, exc_info=True)
        close_code, close_reason = 4500, "Erro interno no stream de eventos."
    finally:
        if ws.client_state != WebSocketState.DISCONNECTED:
            try:
                await ws.close(code=close_code, reason=close_reason)
            except Exception as close_exc:
                logger.debug("Falha ao fechar WebSocket do workflow %s: %s", run_id, close_exc)


async def _forward_events(ws: WebSocket, run_id: str) -> None:
    """Batches → frames, plus a socket reader.

    Reading the socket is what makes the server notice the closed tab RIGHT AWAY:
    before, the handler never called `ws.receive()`, so the browser's close only
    showed up on the next send — in a long, quiet run, the task and the Redis
    connection stayed stuck until the run ended.
    """
    lotes = iter_run_events(run_id, timeout_s=_WS_MAX_S)

    async def encaminhar() -> None:
        async for lote in lotes:
            if lote.heartbeat:
                # Empty batch: a no-op on the client, which only renews the inactivity
                # watchdog; if the socket has already died, it is this send that fails.
                await ws.send_text(_batch_frame([], 0))
            else:
                await ws.send_text(_batch_frame(lote.eventos, lote.dropped))
            if lote.completo:
                return

    async def watch_close() -> None:
        try:
            while True:
                message = await ws.receive()
                if message.get("type") == "websocket.disconnect":
                    return
        except Exception:
            # Any failure in the read means the socket is gone — that is exactly the
            # signal this task exists to give.
            return

    tasks = [asyncio.create_task(encaminhar()), asyncio.create_task(watch_close())]
    # `aclosing`: if the socket reader finishes first, the generator stays
    # suspended at a `yield` and only the explicit `aclose()` runs its `finally`
    # (cancels the pub/sub producer and closes the subscriber's connection).
    async with aclosing(lotes):
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                # A real forwarder error has to bubble up to the handler's log,
                # not vanish inside the task.
                if not task.cancelled() and task.exception() is not None:
                    raise task.exception()
        finally:
            # Wait for the tasks to actually finish before `aclosing` runs:
            # `aclose()` on a generator that another task is still running raises
            # "asynchronous generator is already running".
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
