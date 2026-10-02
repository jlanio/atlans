import asyncio
from contextlib import aclosing

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.api.dependencies import check_ws_rate_limit, ws_authenticate
from app.core.utils.logger import get_logger
# O laço subscribe → LRANGE → dedup → pub/sub vive em `run_events_service`
# (o MCP o consome sem socket). Daqui entra só o que ESTE handler chama: o
# gerador de lotes e a exceção que decide o código de fechamento. Os detalhes
# do laço (buffer, marcadores, tamanhos de lote) são do service e quem precisa
# deles o importa de lá — re-exportá-los aqui fazia este módulo parecer dono de
# um laço que já não tem.
from app.services.run_events_service import RunEventsUnavailable, iter_run_events

logger = get_logger(__name__)
router = APIRouter()

# Poll curto para tolerar read-after-write de replica leve: o run é criado
# SINCRONAMENTE no POST /execute, mas o master pode ter commitado antes de a
# replica replicar.
_WS_POLL_ATTEMPTS = 5
_WS_POLL_INTERVAL = 0.2

# Teto de vida de um socket de eventos. O laço antigo não tinha teto: o socket
# vivia até o `__workflow_complete__` ou até a aba fechar. `iter_run_events`
# exige um prazo (o MCP precisa dele), então o WS passa um generoso — maior
# que qualquer run legítimo — só para que um assinante órfão de um run que
# nunca publica o marcador (consumer morto) não fique preso para sempre. Ao
# estourar, o socket fecha com 1000 e a UI reabre como faz hoje.
_WS_MAX_S = 24 * 3600.0


def _batch_frame(events: list[str], dropped: int = 0) -> str:
    """Monta `{"type":"events","dropped":N,"events":[...]}` a partir dos RAWs.

    ENVELOPE ÚNICO: replay histórico e stream ao vivo usam exatamente o mesmo
    formato. O envelope antigo dizia "replay" também para o ao vivo, e o cliente
    decidia pelo envelope — o caminho de conclusão imediata (drenar síncrono ao
    ver `__workflow_complete__`) só existia no formato de evento cru, então com
    a aba em segundo plano o run ficava preso em "Executando". Agora o cliente
    decide pelo CONTEÚDO do lote e não há mais marcador `{"type":"live"}`.

    `dropped` vai SEMPRE (0 inclusive) para o cliente poder somar sem checar
    `undefined`: truncar em silêncio faz a aba "Bruto" parecer completa.

    Os itens já são JSON válido: fazer json.loads para olhar um campo e
    ws.send_json logo depois custava 2×N serializações e N frames. Aqui é uma
    concatenação de strings e um frame só.
    """
    return '{"type":"events","dropped":%d,"events":[%s]}' % (dropped, ",".join(events))


async def _authorize_run(db, run_id: str, user_id_hash: str) -> tuple[bool, bool]:
    """(run_existe, tem_acesso) em UM round-trip.

    Antes eram até quatro sessões DB em série no handshake — uma por tentativa
    do poll, mais dono, mais membro — todas antes do primeiro byte de evento.

    SEG: o LEFT JOIN em Workspace carrega `deleted_at IS NULL`, então workspace
    na lixeira não casa e `tem_acesso` sai False tanto para o dono quanto para o
    membro (WorkspaceMember só cai no purge).
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
    # 1) Aceita + autentica via primeira mensagem (JWT no corpo, não em query).
    #    ws_authenticate faz o accept() internamente.
    user = await ws_authenticate(ws, scope="workflow")
    if user is None:
        return
    user_id_hash = user.id_hash

    # 2) Rate limit por USUÁRIO, não por IP: atrás do Traefik o IP é o do proxy
    #    para todo mundo. Roda antes do banco para que uma rajada não custe
    #    consultas. O teto é folgado porque a UI reabre o socket a cada troca de
    #    workflow (e o StrictMode dobra as aberturas em dev).
    if not await check_ws_rate_limit(
        ws, scope="workflow", identity=user_id_hash, limit=120, period=60
    ):
        return

    # 3) O run pertence a um workspace que este usuário alcança?
    try:
        from app.core.db import get_session_async

        exists = has_access = False
        start = asyncio.get_running_loop().time()
        # Uma sessão só para todas as tentativas: em READ COMMITTED cada
        # statement pega snapshot novo, então o retry enxerga o commit tardio
        # sem precisar de um checkout de conexão por tentativa.
        async with get_session_async() as db:
            for attempt in range(_WS_POLL_ATTEMPTS):
                exists, has_access = await _authorize_run(db, run_id, user_id_hash)
                if exists:
                    break
                # Sem esta guarda o último ciclo dormia 200 ms antes de desistir
                # — atraso puro somado a um 4404 que já estava decidido.
                if attempt < _WS_POLL_ATTEMPTS - 1:
                    # Devolve a conexão ao pool ANTES de dormir: o primeiro
                    # execute abre transação e a AsyncSession fica "idle in
                    # transaction" durante os sleeps. Vários painéis reabrindo
                    # juntos (consumer lento) prendiam N conexões por até 800 ms
                    # sem usar nenhuma, competindo com o resto da API.
                    await db.rollback()
                    await asyncio.sleep(_WS_POLL_INTERVAL)

        if not exists:
            elapsed = asyncio.get_running_loop().time() - start
            # Log explicito para diagnostico: sem isso o backend so registra
            # "connection closed" generico — o operador nao distingue 4404 de
            # close normal. Vai para WARN porque indica race entre POST /execute
            # e run_result_consumer (lento ou parado).
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

    # 4) Encaminha os lotes de `iter_run_events` (replay + ao vivo) ao socket.
    logger.info("WS /ws/workflow/%s: subscribed user=%s", run_id, user_id_hash)

    # Código de fechamento decidido pelos ramos de erro. 1000 é encerramento
    # normal e o cliente o ignora de propósito; falha de servidor precisa sair
    # como 4500, senão o painel fica em "Executando" para sempre sem toast.
    close_code = 1000
    close_reason = ""
    try:
        await _encaminhar_eventos(ws, run_id)
    except WebSocketDisconnect as exc:
        # Aba fechada no meio de um envio: caminho normal, não é falha do server.
        logger.debug("WS /ws/workflow/%s encerrado pelo cliente: %s", run_id, exc)
    except RunEventsUnavailable as exc:
        # Redis fora (ou pool sem lifespan) com o socket vivo: erro do servidor.
        # Tratá-lo como "aba fechada" escondia a falha num DEBUG e o painel
        # abria vazio, preso em "Executando", sem um só erro no log.
        logger.error("Erro no WebSocket do workflow %s: %s", run_id, exc, exc_info=True)
        close_code, close_reason = 4500, "Erro interno no stream de eventos."
    except RuntimeError as exc:
        # RuntimeError aqui é o Starlette ao mandar num socket já fechado (aba
        # fechada — normal). Se o socket ainda está vivo dos dois lados, não é
        # esse o caso e a falha é do servidor.
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


async def _encaminhar_eventos(ws: WebSocket, run_id: str) -> None:
    """Lotes → frames, mais um leitor do socket.

    A leitura do socket é o que faz o servidor perceber a aba fechada NA HORA:
    antes o handler nunca chamava `ws.receive()`, então o close do browser só
    aparecia no próximo envio — num run longo e silencioso, a task e a conexão
    Redis ficavam presas até o run acabar.
    """
    lotes = iter_run_events(run_id, timeout_s=_WS_MAX_S)

    async def encaminhar() -> None:
        async for lote in lotes:
            if lote.heartbeat:
                # Lote vazio: no-op no cliente, que só renova o watchdog de
                # inatividade; se o socket já morreu, é este send que falha.
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
            # Qualquer falha na leitura significa socket ido — é exatamente o
            # sinal que esta task existe para dar.
            return

    tasks = [asyncio.create_task(encaminhar()), asyncio.create_task(watch_close())]
    # `aclosing`: se quem termina primeiro é o leitor do socket, o gerador fica
    # suspenso num `yield` e só o `aclose()` explícito roda o `finally` dele
    # (cancela o produtor do pub/sub e fecha a conexão do assinante).
    async with aclosing(lotes):
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                # Erro real do encaminhador tem que subir para o log do
                # handler, não sumir dentro da task.
                if not task.cancelled() and task.exception() is not None:
                    raise task.exception()
        finally:
            # Espera as tasks de fato encerrarem antes de o `aclosing` rodar:
            # `aclose()` num gerador que outra task ainda executa estoura
            # "asynchronous generator is already running".
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
