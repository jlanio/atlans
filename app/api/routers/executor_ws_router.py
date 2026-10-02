# app/api/routers/executor_ws_router.py
"""
WebSocket para conexão de Executores externos.

Endpoint: GET /ws/executores/{executor_id}?token=<JWT>

Protocolo de mensagens (JSON). Tipos por direção, versão e chaves reservadas
moram em flow/utils/protocolo_ws.py, que o executor também importa:

  Executor → Servidor:
    {"type": "handshake",  "protocol_version": str, "executor_version": str, "system_info": dict?}
    {"type": "heartbeat"}
    {"type": "capacity",   "queued": int, "running": int, "max_concurrent": int, "max_queue": int}
    {"type": "job_result", "job_id": str, "status": "ok"|"error", "output": any, "error": str?}
    {"type": "node_event", "run_id": str, "node": str, "status": str, "timestamp": float, ...}
    {"type": "sync_event", "event": str, "dataset": str, "progress": float, ...}
    {"type": "ack",        "job_id": str, "status": "enqueued"}
    {"type": "inventario", "ativos": [str], "resultados": [str], "truncado": bool}

  Servidor → Executor:
    {"type": "job",  ...job_message...}   ← build_job_message() do job_crypto.py
    {"type": "cancel", "job_id": str}         ← assinado (ver control_crypto)
    {"type": "control", "action": str, "reason": str}   ← assinado (idem)
    {"type": "drive_event", "action": str, "file": dict} ← app/core/drive_events.py
    {"type": "error", "reason": str, ...}     ← mensagem recusada (`_responder_erro`)
"""
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, NamedTuple

from app.core.utils.logger import get_logger

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.executor_connections import (
    encerrar_envios,
    encerrar_saida,
    enfileirar_ao_executor,
    executor_registry,
    fechar_ws_do_executor,
    ip_do_websocket,
)
from app.core.db import get_session_async
from app.models.executor import Executor
from app.services.executor_service import (
    motivo_da_revogacao, registrar_fim_da_sessao, update_agent_last_seen,
)
from flow.utils.protocolo_ws import (
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    TIPO_ERRO,
)

from .executor_ws.inbox import (
    _INBOX_CANCEL_GRACE,
    _INBOX_FLUSH_TIMEOUT,
    _INBOX_MAXSIZE,
    _InboxQueue,
    _drenar_inbox,
    _encerrar_drenagem,
    _enfileirar_mensagem,
    _novo_contador_de_descartes,
    _resgatar_job_results_pendentes,
)
from .executor_ws.orfaos import (
    _fail_orphan_runs_if_gone,
    _orphan_check_tasks,
)
from .executor_ws.protocolo import (
    _drop_rate_state,
    _missing_fields,
    _node_event_allowed,
    _sanitize_capacity,
    _sanitize_executor_version,
    _sanitize_system_info,
    _sync_event_allowed,
)

# ── Reexports ────────────────────────────────────────────────────────────────
# O main importa o watchdog (e o registro de tasks, já importado acima para o
# teardown) daqui. O resto do pacote é importado direto de
# app.api.routers.executor_ws.*.
from .executor_ws.orfaos import orphan_runs_watchdog  # noqa: F401

logger = get_logger(__name__)

router = APIRouter(tags=["executores-ws"])

# Intervalo máximo sem heartbeat antes de considerar o executor desconectado
_HEARTBEAT_TIMEOUT = 90  # segundos

# Referência forte para a task de purga de retenção disparada na reconexão
# (asyncio só guarda weakrefs). Perder essa task significa dado pessoal vencido
# que continua no disco do usuário até o próximo ciclo do loop de limpeza.
_purge_tasks_pendentes: set[asyncio.Task] = set()


def _responder_erro(ws: WebSocket, executor_id: str, reason: str, **detalhe) -> None:
    """Resposta de erro ao executor: `{"type": "error", "reason": ..., **detalhe}`.
    Melhor-esforço, pela mesma fila dos outros envios ao socket (ver `_Saida`):
    escrever por fora disputava o drain de um envio em curso.

    O tipo é o do protocolo (TIPO_ERRO, em flow/utils/protocolo_ws.py), que o
    executor reconhece e registra em WARNING com o `reason`.

    Só enfileira, sem esperar a vez: quem chama é o loop de recebimento, o único
    que renova a presença — preso atrás de um frame lento, ele deixava a
    presença de um executor vivo vencer (e o watchdog fechava os runs dele).
    Um close logo depois descarta a resposta que ainda estiver na fila; o que
    conta para o executor nesses casos é o código do close."""
    corpo = {"type": TIPO_ERRO, "reason": reason, **detalhe}
    try:
        enfileirar_ao_executor(ws, json.dumps(corpo), executor_id)
    except Exception:
        pass  # socket pode ter fechado


# Prazo para gravar o fim da sessão no teardown — ver `_gravar_fim_da_sessao`.
_FIM_DA_SESSAO_TIMEOUT = 5.0


async def _gravar_fim_da_sessao(executor_id: str, ultimo_contato) -> None:
    """Grava o fim da sessão em `last_seen_at`. Sem isto ele parava no
    handshake, e a tela de executores mostrava um executor que passou três dias
    no ar e caiu há dez minutos como "visto há 3 dias".

    Grava o último contato da sessão (a última mensagem recebida), não o
    instante do teardown: depois de um heartbeat estourado, esse instante vem
    ~100 s depois do último sinal de vida. E só se for posterior ao que está no
    banco (ver `registrar_fim_da_sessao`)."""
    if not isinstance(ultimo_contato, datetime):
        ultimo_contato = datetime.now(timezone.utc)
    if ultimo_contato.tzinfo is None:
        ultimo_contato = ultimo_contato.replace(tzinfo=timezone.utc)
    visto_em = ultimo_contato.astimezone(timezone.utc).replace(tzinfo=None)   # coluna em UTC sem fuso
    async with get_session_async() as db:
        await registrar_fim_da_sessao(db, executor_id, visto_em)


# Intervalo da conferência de revogação com a sessão aberta — ver `_vigiar_revogacao`.
_REVOGACAO_INTERVALO = 60.0


async def _vigiar_revogacao(executor_id: str, ws: WebSocket) -> None:
    """Fecha com 4403 a sessão de um executor revogado enquanto ela está aberta.

    O mTLS só é conferido ao conectar. As revogações pedem o fechamento pelo
    relay, mas o aviso se perde com o Redis reiniciando, com o listener da
    sessão reconectando ou com uma sessão que nasce no meio da revogação — e a
    sessão revogada seguia viva (recebendo jobs) até reconectar. A cada
    `_REVOGACAO_INTERVALO` o banco diz se ela ainda vale
    (`motivo_da_revogacao`). Banco fora fica para a próxima volta: derrubar as
    sessões vivas da frota por um blip do banco seria pior."""
    while True:
        await asyncio.sleep(_REVOGACAO_INTERVALO)
        try:
            async with get_session_async() as db:
                motivo = await motivo_da_revogacao(db, executor_id)
        except Exception as exc:
            logger.warning(
                "Executor '%s': conferência de revogação falhou (%r) — tento de novo.", executor_id, exc,
            )
            continue
        if motivo:
            logger.warning("Executor '%s' revogado com a sessão aberta (%s) — fechando.", executor_id, motivo)
            try:
                await fechar_ws_do_executor(ws, code=4403, reason=motivo)
            except Exception as exc:
                logger.warning("Executor '%s': falha ao fechar a sessão revogada: %r", executor_id, exc)
            return


@router.websocket("/ws/executores/{executor_id}")
async def agent_websocket(executor_id: str, ws: WebSocket):
    """
    Conexão WebSocket autenticada por cert mTLS.

    Traefik valida o client cert contra a CA interna no handshake TLS e injeta
    X-Forwarded-Tls-Client-Cert-Info com CN e serial. Aqui:
      1. Parse do header → (cn, serial).
      2. CN deve ser `executor-{executor_id}` (do path da URL).
      3. Executor existe + status='active' + serial bate com cert_serial no DB.
      4. Cert serial não está na blacklist Redis.

    As fases da sessão moram abaixo, na ordem em que rodam:
    `_autenticar_ou_recusar` (antes do accept), `_abrir_sessao`,
    `_tratar_mensagem` a cada mensagem e `_encerrar_sessao` no teardown.
    """
    # ── 1. Valida cert mTLS antes de accept() ────────────────────────────────
    tetos = await _autenticar_ou_recusar(ws, executor_id)
    if tetos is None:
        return

    # ── 2. Aceita a conexão ───────────────────────────────────────────────────
    sessao = await _abrir_sessao(ws, executor_id, tetos)
    try:
        # Dentro do try DE PROPÓSITO: se o banco estiver fora, a exceção subia
        # antes do try e o `finally` com o unregister nunca rodava — a conexão
        # ficava registrada (e renovando presença) sem ninguém lendo o socket.
        async with get_session_async() as db:
            await update_agent_last_seen(db, executor_id)

        logger.info("Executor '%s' conectado via WebSocket.", executor_id)

        # ── 3. Loop de recebimento ────────────────────────────────────────────
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=_HEARTBEAT_TIMEOUT)
            except asyncio.TimeoutError:
                # Nenhuma mensagem dentro do timeout — fecha conexão
                logger.warning("Executor '%s' sem heartbeat por %ds — desconectando.", executor_id, _HEARTBEAT_TIMEOUT)
                await fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")
                break
            if not await _tratar_mensagem(sessao, raw):
                break

    except WebSocketDisconnect:
        logger.info("Executor '%s' desconectou (WebSocketDisconnect).", executor_id)
    except Exception as exc:
        logger.error("Erro no WebSocket do executor '%s': %s", executor_id, exc)
    finally:
        await _encerrar_sessao(sessao)


# ── 1. Autenticação ──────────────────────────────────────────────────────────


class _Tetos(NamedTuple):
    """Tetos do registro — clamp da capacidade auto-declarada (ver S3)."""

    max_concurrent: int | None
    max_queue: int | None


async def _autenticar_ou_recusar(ws: WebSocket, executor_id: str) -> _Tetos | None:
    """Valida o cert mTLS ANTES do accept() — pipeline único: ver
    dependencies.validate_executor_mtls, compartilhado com o HTTP.

    Devolve os tetos do registro do executor, ou None quando recusou: aí a
    conexão já foi aceita e fechada com o 44xx da razão, e nada mais roda."""
    from app.api.dependencies import (
        validate_executor_mtls, ExecutorMtlsError, _MTLS_WS_CODE,
    )
    try:
        async with get_session_async() as db:
            ag = await validate_executor_mtls(
                header_value=ws.headers.get("x-forwarded-tls-client-cert-info", ""),
                client_host=ws.client.host if ws.client else None,
                url_path=str(ws.url.path),
                db=db,
                expected_executor_id=executor_id,
                require_public_key=True,
            )
            # Extrai antes de fechar a sessão (evita DetachedInstanceError).
            # A versão NÃO vem daqui: o banco guarda a da sessão anterior, e a
            # desta chega no handshake.
            return _Tetos(max_concurrent=ag.max_concurrent_jobs, max_queue=ag.max_queue_size)
    except ExecutorMtlsError as exc:
        # DENY AUTORITATIVO: precisa chegar ao executor como CLOSE 44xx, nunca
        # como status HTTP. Levantar WebSocketException ANTES do accept() faz o
        # deny virar um status no handshake HTTP, e o cliente classifica status
        # HTTP como NÃO-terminal DE PROPÓSITO (durante deploy o Traefik responde
        # 404/502/503). O resultado era um executor revogado/removido
        # reconectando para sempre, com o ramo terminal do cliente virando
        # código morto. Aceitamos e fechamos na sequência: nada é processado e o
        # registry NÃO é populado.
        close_code = _MTLS_WS_CODE.get(exc.reason, 4401)
        # `reason` do close cabe em 123 bytes no frame — trunca com folga.
        close_reason = (exc.detail or "")[:100]
        logger.warning(
            "Executor '%s' recusado na autenticação mTLS (%s) — fechando com code=%d.",
            executor_id, exc.reason, close_code,
        )
        try:
            await ws.accept()
            await fechar_ws_do_executor(ws, code=close_code, reason=close_reason)
        except Exception as close_exc:
            logger.debug(
                "Falha ao notificar deny ao executor '%s': %s", executor_id, close_exc,
            )
        finally:
            encerrar_saida(ws)
        return None


# ── 2. Abertura ──────────────────────────────────────────────────────────────


@dataclass(eq=False)
class _Sessao:
    """O que uma conexão aceita carrega do accept ao teardown."""

    executor_id: str
    ws: WebSocket
    # A conexão DESTA sessão no registro: no fim, o último contato dela vira o
    # "visto há". None quando outra sessão registrou por cima antes da
    # conferência — aí o fim desta não é gravado (ver `_abrir_sessao`).
    minha_conexao: Any
    # Fila + drenadora desta conexão: o loop só valida e enfileira, nunca
    # espera Redis/Postgres. Ver `_drenar_inbox`.
    inbox: _InboxQueue
    drain_task: asyncio.Task
    # job_results em voo na drenadora. O teardown espera por eles antes de
    # cancelar: cortar um commit dividido no meio deixa o run terminal no banco
    # sem nunca publicar o `__workflow_complete__` (painel girando para sempre).
    inflight: set[asyncio.Task]
    descartes: dict
    # A conferência de revogação (`_vigiar_revogacao`). Referência forte (o
    # asyncio só guarda weakrefs); cancelada no teardown.
    vigia: asyncio.Task
    # Contador de JSON inválido em sequência — evita flapping de executor com
    # bug que envia payload corrompido repetidamente.
    invalid_json_streak: int = 0
    # A versão e o system_info são da conexão: valem os do PRIMEIRO handshake.
    # Os seguintes não gravam nada — cada um era um SELECT + UPDATE no banco,
    # sem limite, e um system_info diferente só na memória deste worker fazia a
    # tela mudar conforme o worker que respondia.
    identificacao_gravada: bool = False


async def _abrir_sessao(ws: WebSocket, executor_id: str, tetos: _Tetos) -> _Sessao:
    """Aceita a conexão, registra, agenda a purga de retenção e monta a fila,
    a drenadora e a vigia da sessão.

    Fora do `finally` do handler, como sempre esteve: o teardown só roda para
    a sessão que chegou a abrir inteira."""
    await ws.accept()

    await executor_registry.register(
        executor_id, ws,
        max_concurrent_limit=tetos.max_concurrent,
        max_queue_limit=tetos.max_queue,
    )

    # Em task separada de propósito: o handshake não pode esperar uma consulta
    # ao banco, e uma falha aqui não deve derrubar a conexão que acabou de subir.
    # Referência forte obrigatória: o asyncio guarda só weakrefs para tasks, e
    # sem isto a purga pode ser coletada no meio da consulta ao banco — o mesmo
    # cuidado de `_orphan_check_tasks` no teardown.
    _purge_tasks_pendentes.add(
        t := asyncio.create_task(_purgar_pendentes(executor_id), name=f"purge-{executor_id[:8]}")
    )
    t.add_done_callback(_purge_tasks_pendentes.discard)

    # A conexão DESTA sessão: no fim, o último contato dela vira o "visto há".
    # Guardada agora porque, até o teardown, o registro pode ter outra — e
    # conferida pelo socket, porque outra sessão pode ter registrado por cima
    # entre o register e aqui (aí o fim desta não é gravado).
    minha_conexao = executor_registry.get(executor_id)
    if getattr(minha_conexao, "websocket", None) is not ws:
        minha_conexao = None

    inbox = _InboxQueue(maxsize=_INBOX_MAXSIZE)
    # Do próprio websocket, não do registro: um takeover pode tirar esta
    # conexão de lá antes de a fila esvaziar (ver `_InboxQueue.ip_da_conexao`).
    inbox.ip_da_conexao = ip_do_websocket(ws)
    inflight: set[asyncio.Task] = set()
    drain_task = asyncio.create_task(
        _drenar_inbox(executor_id, inbox, inflight), name=f"inbox-{executor_id[:8]}",
    )
    descartes = _novo_contador_de_descartes()
    vigia = asyncio.create_task(_vigiar_revogacao(executor_id, ws), name=f"revogacao-{executor_id[:8]}")
    return _Sessao(
        executor_id=executor_id, ws=ws, minha_conexao=minha_conexao,
        inbox=inbox, drain_task=drain_task, inflight=inflight,
        descartes=descartes, vigia=vigia,
    )


async def _purgar_pendentes(executor_id: str) -> None:
    """Retenção pendente: artefatos locais deste executor que venceram enquanto
    a máquina estava desligada. O loop periódico só passaria daqui a até uma
    hora, e nesse intervalo há dado pessoal vencido no disco do usuário —
    reconectar é o primeiro instante em que a ordem pode ser entregue."""
    from app.core.artifact_cleanup import purgar_pendentes_do_executor
    try:
        n = await purgar_pendentes_do_executor(executor_id)
        if n:
            logger.info(
                "Executor '%s': %d artefato(s) local(is) vencido(s) purgado(s) na reconexão.",
                executor_id, n,
            )
    except Exception as exc:
        logger.warning(
            "Executor '%s': falha ao purgar artefatos pendentes na reconexão (%s). "
            "O ciclo periódico tenta de novo.", executor_id, exc,
        )


# ── 3. Cada mensagem ─────────────────────────────────────────────────────────

# JSONs inválidos seguidos que derrubam a sessão (close 1003).
_MAX_INVALID_JSON_STREAK = 5


async def _tratar_mensagem(sessao: _Sessao, raw: str) -> bool:
    """Uma mensagem do executor: parse, schema, portão do handshake e despacho
    pelo tipo (`_TRATADORES`).

    False quando a sessão acabou — o close já foi mandado (JSON inválido demais
    ou versão de protocolo não suportada)."""
    executor_id, ws = sessao.executor_id, sessao.ws
    try:
        msg = json.loads(raw)
        sessao.invalid_json_streak = 0  # resetou após parse válido
    except json.JSONDecodeError as exc:
        return await _json_invalido(sessao, raw, exc)

    msg_type = msg.get("type")

    # ── Schema validation: campos obrigatórios por tipo ─────────────────────
    missing = _missing_fields(msg_type, msg) if isinstance(msg_type, str) else []
    if missing:
        logger.warning(
            "Executor '%s' enviou '%s' com campos obrigatórios ausentes: %s",
            executor_id, msg_type, missing,
        )
        _responder_erro(
            ws, executor_id, "invalid_schema",
            missing_fields=missing, message_type=msg_type,
        )
        return True

    # SEG: handshake deve ser a PRIMEIRA mensagem — bloqueia qualquer
    # outro tipo até o executor se identificar. Isso vira barreira contra
    # mensagens espúrias de executores mal-implementados ou adversários
    # que conseguiram conectar mas não completaram o contrato.
    conn_state = executor_registry.get(executor_id)
    if conn_state and not getattr(conn_state, "handshake_received", False):
        if msg_type != "handshake":
            logger.warning(
                "Executor '%s' enviou '%s' antes de handshake — rejeitado.",
                executor_id, msg_type,
            )
            _responder_erro(ws, executor_id, "handshake_required")
            return True
        if not await _protocolo_aceito(sessao, msg):
            return False
        conn_state.handshake_received = True

    # Só texto é tipo: um `type` lista ou objeto não serve de chave, e cai no
    # "desconhecido" como qualquer outro.
    tratador = _TRATADORES.get(msg_type) if isinstance(msg_type, str) else None
    if tratador is None:
        logger.debug("Executor '%s' enviou tipo desconhecido: %s", executor_id, msg_type)
        return True
    await tratador(sessao, msg_type, msg, len(raw))
    return True


async def _json_invalido(sessao: _Sessao, raw: str, exc: json.JSONDecodeError) -> bool:
    """Responde `invalid_json` e conta a sequência. Na
    `_MAX_INVALID_JSON_STREAK`-ésima seguida, fecha com 1003 e devolve False."""
    sessao.invalid_json_streak += 1
    logger.warning(
        "Executor '%s' enviou JSON inválido (streak=%d): %s | raw=%r",
        sessao.executor_id, sessao.invalid_json_streak, exc, raw[:200],
    )
    # Feedback ao executor — evita loop onde ele aguarda ACK e re-tenta.
    _responder_erro(sessao.ws, sessao.executor_id, "invalid_json", detail=str(exc)[:200])
    if sessao.invalid_json_streak < _MAX_INVALID_JSON_STREAK:
        return True
    logger.error(
        "Executor '%s' enviou %d JSONs inválidos seguidos — desconectando.",
        sessao.executor_id, sessao.invalid_json_streak,
    )
    await fechar_ws_do_executor(sessao.ws, code=1003, reason="Too many invalid messages.")
    return False


async def _protocolo_aceito(sessao: _Sessao, msg: dict) -> bool:
    """Validação de protocolo do primeiro handshake: rejeita executores com
    versão incompatível — responde `unsupported_protocol_version`, fecha com
    4426 e devolve False."""
    claimed = str(msg.get("protocol_version") or "1.0")
    if claimed in SUPPORTED_PROTOCOL_VERSIONS:
        return True
    logger.warning(
        "Executor '%s' declarou protocol_version='%s' não suportado (aceitos: %s).",
        sessao.executor_id, claimed, sorted(SUPPORTED_PROTOCOL_VERSIONS),
    )
    _responder_erro(
        sessao.ws, sessao.executor_id, "unsupported_protocol_version",
        server_protocol_version=PROTOCOL_VERSION,
        supported=list(SUPPORTED_PROTOCOL_VERSIONS),
    )
    await fechar_ws_do_executor(sessao.ws, code=4426, reason="Unsupported protocol version.")
    return False


# Os tratadores por tipo têm todos a mesma assinatura:
# (sessão, tipo, mensagem, tamanho do frame em bytes).


async def _tratar_heartbeat(sessao: _Sessao, _tipo: str, _msg: dict, _frame_bytes: int) -> None:
    await executor_registry.update_last_seen(sessao.executor_id)


async def _tratar_capacity(sessao: _Sessao, _tipo: str, msg: dict, _frame_bytes: int) -> None:
    capacity, cap_errors = _sanitize_capacity(sessao.executor_id, msg)
    if capacity is None:
        logger.warning(
            "Executor '%s' enviou capacity inválida: %s", sessao.executor_id, cap_errors,
        )
        _responder_erro(sessao.ws, sessao.executor_id, "invalid_capacity", errors=cap_errors)
        return
    # `update_capacity` já atualiza last_seen_at e renova a
    # presença — o `update_last_seen` que vinha logo aqui dobrava o
    # EVAL Lua de renovação a cada 10 segundos, por executor.
    await executor_registry.update_capacity(sessao.executor_id, capacity)


async def _tratar_handshake(sessao: _Sessao, _tipo: str, msg: dict, _frame_bytes: int) -> None:
    """O primeiro handshake grava a identificação da conexão (versão e
    system_info); os seguintes só renovam a presença."""
    executor_id = sessao.executor_id
    if sessao.identificacao_gravada:
        await executor_registry.update_last_seen(executor_id)
        return

    sessao.identificacao_gravada = True
    conn = executor_registry.get(executor_id)
    ver = _sanitize_executor_version(executor_id, msg.get("executor_version"))
    raw_sys_info = msg.get("system_info")
    sys_info = (
        _sanitize_system_info(executor_id, raw_sys_info)
        if raw_sys_info is not None else None
    )
    if conn:
        if ver:
            conn.executor_version = ver
        if sys_info:
            conn.system_info = sys_info
    if sys_info or ver:
        await _persistir_identificacao(executor_id, ver, sys_info)
    await executor_registry.update_last_seen(executor_id)


async def _persistir_identificacao(executor_id: str, ver: str | None, sys_info: dict | None) -> None:
    """Persiste versão e system_info no banco (1x por conexão, ver
    `identificacao_gravada`): a tela de executores lê os dois do
    banco — a conexão só existe no worker do WebSocket. A versão
    ficava só na memória, e a coluna "versão" da tela mostrava
    "—" para todo executor."""
    async with get_session_async() as db:
        result = await db.execute(
            select(Executor).where(Executor.id_hash == executor_id)
        )
        ag = result.scalar_one_or_none()
        if ag:
            if sys_info:
                ag.system_info = sys_info
            if ver:
                ag.executor_version = ver
            await db.commit()


async def _enfileirar(sessao: _Sessao, msg_type: str, msg: dict, frame_bytes: int) -> None:
    """Para a drenadora da conexão (ver `_drenar_inbox`)."""
    await _enfileirar_mensagem(
        sessao.executor_id, sessao.inbox, sessao.descartes, msg_type, msg, frame_bytes,
    )


async def _tratar_node_event(sessao: _Sessao, msg_type: str, msg: dict, frame_bytes: int) -> None:
    if _node_event_allowed(sessao.executor_id, msg):
        await _enfileirar(sessao, msg_type, msg, frame_bytes)


async def _tratar_sync_event(sessao: _Sessao, msg_type: str, msg: dict, frame_bytes: int) -> None:
    if _sync_event_allowed(sessao.executor_id, msg):
        await _enfileirar(sessao, msg_type, msg, frame_bytes)


# O despacho: as chaves são os TIPOS_DO_EXECUTOR do protocolo
# (flow/utils/protocolo_ws.py). Tipo fora daqui só vai ao debug.
_TRATADORES: dict[str, Callable[[_Sessao, str, dict, int], Awaitable[None]]] = {
    "handshake": _tratar_handshake,
    "heartbeat": _tratar_heartbeat,
    "capacity": _tratar_capacity,
    # Os três abaixo custam Redis (e o job_result, Postgres):
    # validam-se aqui e são processados pela drenadora, para que o
    # próximo receive_text() não espere por I/O.
    "job_result": _enfileirar,
    "node_event": _tratar_node_event,
    "sync_event": _tratar_sync_event,
    # ACK de recebimento de job: limpa o pendente de ACK e promove o
    # run de 'pending' para 'running' (ver `_record_job_ack`). A
    # promoção é um UPDATE no Postgres, então vai pela drenadora —
    # na mesma fila do job_result, que chega depois dele.
    "ack": _enfileirar,
    # Jobs que o executor TEM. A reconciliação fecha os runs que ele
    # não tem (ver `_reconciliar_inventario`) e vai pela drenadora
    # DE PROPÓSITO: na mesma fila, um job_result enviado antes do
    # inventário é gravado antes de o inventário ser conferido — senão
    # o run recém-terminado pareceria perdido.
    "inventario": _enfileirar,
}


# ── 4. Teardown ──────────────────────────────────────────────────────────────


async def _encerrar_sessao(sessao: _Sessao) -> None:
    """O fim da sessão, nesta ordem: a vigia e os envios param, a fila esvazia
    (antes do unregister), a presença sai, a verificação de órfãos é agendada
    e, por último, o fim da sessão é carimbado."""
    executor_id, ws = sessao.executor_id, sessao.ws
    sessao.vigia.cancel()
    # Nada mais sai por este socket: durante o flush abaixo (até 10 s) a
    # conexão segue registrada e o listener do relay vivo, e um job relayado
    # agora batia no socket morto sem ninguém fechar o run.
    encerrar_envios(ws)
    await _esvaziar_a_fila(sessao)
    if sessao.descartes["total"]:
        logger.warning(
            "Executor '%s': %d mensagem(ns) descartada(s) por fila cheia nesta conexão.",
            executor_id, sessao.descartes["total"],
        )
    # expected_ws=ws garante que so removemos se o WS registrado ainda
    # e este — evita matar reconexao rapida que registrou WS_novo.
    await executor_registry.unregister(executor_id, expected_ws=ws)
    _drop_rate_state(executor_id)
    # Fim da vida deste socket: a fila de saída dele sai do mapa (ver
    # `encerrar_saida`) — vale também quando o unregister não o fechou
    # porque o executor já reconectou noutra sessão.
    encerrar_saida(ws)
    _agendar_verificacao_de_orfaos(executor_id)
    # Por último de propósito: um cancelamento aqui (shutdown) só perde este
    # carimbo, nunca a verificação de órfãos acima. Melhor-esforço e com
    # prazo — o teardown não espera um banco fora do ar; o próximo handshake
    # grava de novo.
    if sessao.minha_conexao is not None:
        try:
            await asyncio.wait_for(
                _gravar_fim_da_sessao(executor_id, sessao.minha_conexao.last_seen_at),
                timeout=_FIM_DA_SESSAO_TIMEOUT,
            )
        except Exception as exc:
            logger.warning("Executor '%s': fim da sessão não gravado (%r).", executor_id, exc)


async def _esvaziar_a_fila(sessao: _Sessao) -> None:
    """FLUSH ANTES do unregister: o que ainda estiver na fila são os ÚLTIMOS
    eventos do run (inclusive o job_result e o __workflow_complete__).
    Cancelar a drenadora aqui deixaria o painel do usuário girando para
    sempre num run que na verdade terminou."""
    executor_id, inbox, drain_task, inflight = (
        sessao.executor_id, sessao.inbox, sessao.drain_task, sessao.inflight,
    )
    try:
        await asyncio.wait_for(
            _encerrar_drenagem(inbox, drain_task), timeout=_INBOX_FLUSH_TIMEOUT,
        )
    except Exception as exc:
        logger.warning(
            "Executor '%s': drenagem final não concluiu em %.0fs (%s) — "
            "eventos residuais podem ter sido perdidos.",
            executor_id, _INBOX_FLUSH_TIMEOUT, exc,
        )
        # Parada graciosa antes do cancelamento: o `cancel()` seco podia cair
        # no meio da gravação de um job_result (banco terminal, canvas sem o
        # `__workflow_complete__`). A gravação roda blindada numa task
        # própria; aqui damos a ela a carência para terminar.
        drain_task.cancel()
        if inflight:
            pendentes = set(inflight)
            _, faltando = await asyncio.wait(
                pendentes, timeout=_INBOX_CANCEL_GRACE,
            )
            if faltando:
                logger.error(
                    "Executor '%s': %d gravação(ões) de job_result ainda em voo "
                    "após %.0fs de carência — run pode ficar sem conclusão.",
                    executor_id, len(faltando), _INBOX_CANCEL_GRACE,
                )
        # O que a drenadora cancelada não chegou a consumir: telemetria pode
        # sumir, job_result não.
        try:
            await asyncio.wait_for(
                _resgatar_job_results_pendentes(executor_id, inbox),
                timeout=_INBOX_CANCEL_GRACE,
            )
        except Exception as resgate_exc:
            logger.error(
                "Executor '%s': resgate dos job_result pendentes não concluiu: %s",
                executor_id, resgate_exc,
            )


def _agendar_verificacao_de_orfaos(executor_id: str) -> None:
    """Verificação de órfãos em task separada: ela espera um grace period
    (ver `_fail_orphan_runs_if_gone`) e não deve segurar o teardown do WS."""
    try:
        check = asyncio.create_task(
            _fail_orphan_runs_if_gone(executor_id),
            name=f"orphan-check-{executor_id[:8]}",
        )
        # asyncio guarda só weakrefs para tasks — sem esta referência forte
        # a task pode ser coletada no meio do sleep.
        _orphan_check_tasks.add(check)
        check.add_done_callback(_orphan_check_tasks.discard)
    except RuntimeError:
        # Loop já em shutdown: o orphan_runs_watchdog cuida na volta.
        logger.debug(
            "Sem loop para agendar verificação de órfãos de '%s' — watchdog assume.",
            executor_id,
        )
