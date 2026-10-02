# executor/connection.py
"""
Cliente WebSocket do executor com:
  - Autenticação via cert mTLS (sem JWT intermediário)
  - Reconnect com backoff exponencial
  - Envio periódico de heartbeat e capacity
  - Recebimento e enfileiramento de jobs
"""
import asyncio
import json
import logging
import time
from datetime import datetime, date

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from websockets.frames import Close

from flow.utils.backoff import com_jitter
from flow.utils.protocolo_ws import (
    PROTOCOL_VERSION,
    TIPO_ERRO,
    TIPOS_DO_SERVIDOR,
    reduzir_stats,
)
from flow.utils.publisher.reducao import (
    CAMPOS_DE_CONTROLE,
    TETO_NODE_EVENT_BYTES,
    reduzir_node_event,
)
from executor import config
from executor.job_queue import ExecutorJobQueue
from executor.job_validator import JobValidationError, validate_control_message

logger = logging.getLogger(__name__)


def _json_default(obj):
    """Serializa tipos que o json padrão não suporta (Timestamp, datetime, date, etc.)."""
    # pandas.Timestamp e datetime.datetime
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # numpy int/float
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    # pandas.Timestamp (caso não seja subclasse de datetime no ambiente)
    try:
        import pandas as pd
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, pd.NA.__class__):
            return None
        # GeoDataFrame/DataFrame — nunca serializar inteiro, retorna apenas resumo
        if isinstance(obj, pd.DataFrame):
            return f"<DataFrame {obj.shape[0]}x{obj.shape[1]}>"
    except ImportError:
        pass
    # Limita strings muito longas para evitar payload gigante
    s = str(obj)
    if len(s) > 500:
        return s[:500] + "...[truncated]"
    return s


# Limite de payload WebSocket (16 MB) — casa com ws_max_size do uvicorn em app/main.py.
# Protege contra crash por mensagem grande e define o limite de auto-truncagem em
# _dumps_result.
_MAX_WS_PAYLOAD = 16 * 1024 * 1024


def _dumps_result(obj: dict) -> str:
    """Serializa um job_result; trunca por 'stats' se exceder o limite do WS.

    EXCLUSIVO do job_result. A truncagem aqui sabe mexer numa unica chave —
    'stats' —, que so existe neste tipo de mensagem. Reaproveitar esta funcao
    para node_event nao reduzia nada (o peso do evento esta em extra/error),
    injetava uma chave 'stats' espuria no evento e logava "job_result
    descartado" para algo que nao era job_result nem foi descartado. node_event
    tem o seu proprio _dumps_event.
    """
    result = json.dumps(obj, default=_json_default)
    if len(result) > _MAX_WS_PAYLOAD:
        # Truncagem de `stats` do protocolo (flow/utils/protocolo_ws.py), a mesma
        # que o servidor reaplica: descarta os stats por-nó, que são pesados, e
        # preserva as chaves de controle (resposta HTTP, artefatos, métricas).
        # __response__ é obrigatório para o padrão de webhook síncrono — sem
        # ele, o BRPOP do webhook_router fica preso. A régua daqui é a mensagem
        # inteira contra o frame do WS.
        _stats, result, preservou = reduzir_stats(
            obj.get("stats") or {}, len(result), _MAX_WS_PAYLOAD,
            lambda stats: json.dumps({**obj, "stats": stats}, default=_json_default),
        )
        if preservou:
            logger.warning(
                "job_result excedeu %d bytes; stats por-nó removidos, chaves de controle preservadas.",
                _MAX_WS_PAYLOAD,
            )
        else:
            # Nem com só as chaves de controle coube: saem também — o caller
            # vai receber timeout ou erro claro.
            logger.warning(
                "job_result excede %d bytes mesmo após preservar chaves de controle — descartado.",
                _MAX_WS_PAYLOAD,
            )
    return result


def _dumps_event(obj: dict) -> str:
    """Serializa um node_event; acima do teto, reduz pela regra do protocolo.

    O `default=_json_default` continua obrigatorio: um objeto nao-serializavel
    em `extra` levantava TypeError, caia no ramo generico do sender e reciclava
    o mesmo evento em laco. O teto e a reducao sao os de
    flow/utils/publisher/reducao.py — a mesma regra que o servidor reaplica
    antes do Redis: corta o peso do evento (traceback, debug, stdout que nao
    cabe) e mantem o que o painel usa, `output_columns` e `duration_ms`
    inclusive.
    """
    result = json.dumps(obj, default=_json_default)
    if len(result) <= TETO_NODE_EVENT_BYTES:
        return result
    logger.warning(
        "node_event node=%s status=%s de %d bytes excede %d — reduzido.",
        obj.get("node"), obj.get("status"), len(result), TETO_NODE_EVENT_BYTES,
    )
    return reduzir_node_event(obj, result, default=_json_default)


# A allowlist de tipos servidor → executor e TIPOS_DO_SERVIDOR, do vocabulario
# do protocolo em flow/utils/protocolo_ws.py (ver `_receive_loop`).
#
# `purge_artifacts` apaga arquivo do disco do usuario. Ja esta coberto por
# _SIGNED_SERVER_MESSAGES abaixo (todo `control` exige assinatura Ed25519) — sem
# isso, quem vencesse a conexao teria um canal de destruicao de dados.
_CONTROL_ACTIONS = frozenset({"revoked", "shutdown", "config_changed", "purge_artifacts"})

# Tipos que exigem assinatura Ed25519 do servidor antes de qualquer efeito.
# Mantenha em sincronia com SIGNED_MESSAGE_TYPES em app/core/control_crypto.py.
_SIGNED_SERVER_MESSAGES = frozenset({"control", "cancel"})

# Intervalo de heartbeat enviado ao servidor
_HEARTBEAT_INTERVAL = 30  # segundos
# Intervalo de envio de capacity report
_CAPACITY_INTERVAL = 10  # segundos
# Intervalo do inventário de jobs (ver `_inventario_loop`). O primeiro sai logo
# depois do handshake; daí em diante, um por minuto basta — o servidor só
# fecha runs perdidos com mais de 3 min de idade.
_INVENTARIO_INTERVAL = 60  # segundos
# Teto de ids por inventário. Acima disso ele vai marcado `truncado` e o
# servidor não fecha nada por ausência (não dá para saber o que ficou de fora).
_INVENTARIO_MAX = 1000
# Por quanto tempo um resultado ENVIADO ainda conta como "a caminho" — ver
# `_lembrar_enviado`. Folga sobre o que o servidor leva para processá-lo
# (drenagem do inbox de uma conexão que caiu: ~20 s); depois disso a chave de
# resultado do próprio servidor (TTL 300 s) já o protege. Curto de propósito:
# num executor movimentado os enviados não podem ocupar o inventário inteiro.
_ENVIADOS_TTL_S = 90.0
_ENVIADOS_MAX = 2000
# Motivo do resultado 'cancelled' de um job que o executor não tinha quando o
# cancelamento chegou (ver `_encerrar_cancelamento_desconhecido`).
_MOTIVO_CANCELAMENTO_DESCONHECIDO = (
    "Cancelada. O executor não tinha esta execução quando o pedido chegou — "
    "ela já tinha se perdido antes de rodar ou de o resultado sair."
)
# Amostras consecutivas de pool cheio antes de anunciar capacidade zero — ver
# `_pool_saturado`. Com o tick de 10s do capacity, sao ~10s de fila de threads
# ininterrupta: pico de despacho nao passa, thread orfa passa.
_POOL_SATURADO_TICKS = 2

# Duracao minima de uma sessao WS para considera-la "estavel" e zerar o backoff.
# Sem essa guarda, qualquer close pos-accept (4408 heartbeat timeout, 4426
# protocolo, 1003 JSON invalido, 1011, queda de rede) resetava delay=1 e o
# executor refazia handshake TLS+mTLS em laco apertado, martelando o servidor.
_SESSION_STABLE_SECONDS = 60
# Duracao DA SESSAO (contada do handshake aceito em diante) a partir da qual ela
# ao menos PROGREDIU e o backoff acumulado recua — ver
# `_apply_session_backoff_reset`. Tempo gasto em connect/TLS/upgrade nao conta:
# um upgrade pendurado por 10s nao e progresso, e trata-lo como tal desfazia o
# backoff exponencial exatamente na falha mais cara para o servidor.
_SESSION_PROGRESS_SECONDS = 5

# Teto de tentativas de reenvio de um mesmo node_event. node_event e telemetria
# de UI: perder um update do grafo e ruim, mas re-enfileirar para sempre um
# evento que falha de forma deterministica (payload nao serializavel) prende o
# unico consumidor da fila em laco e trava o _event_queue.join() de main.py.
_MAX_EVENT_SEND_ATTEMPTS = 3
# Teto equivalente para job_result. Simetria obrigatoria: o result loop tem a
# MESMA topologia (consumidor unico, requeue na cauda), entao um resultado que
# falha de forma deterministica (referencia circular em stats, objeto cujo
# __str__ levanta dentro de _json_default) girava para sempre a 1 tentativa/s,
# segurava o _result_queue.join() do shutdown nos 30s de timeout inteiros e
# nunca deixava passar a fila. O teto e mais alto que o de node_event porque
# resultado e dado de negocio, nao telemetria — e ao desistir NAO chamamos
# mark_sent(): a copia do outbox (sanitizada, sem stats — justamente o campo
# que costuma ser o veneno) e reenviada no proximo start.
_MAX_RESULT_SEND_ATTEMPTS = 5
# Chave interna de contagem de tentativas. Removida do payload antes do send —
# nunca trafega para o servidor.
_ATTEMPTS_KEY = "__send_attempts__"
# Backoff apos falha generica de envio. E por RAJADA, nao por item: a pausa so
# entra depois de _SEND_FAIL_STREAK_LIMIT falhas CONSECUTIVAS e o contador zera
# a cada envio bem-sucedido.
#
# Antes era 1,0s por ITEM, e como estes loops tem um unico consumidor a fila
# virava um funil de 1 evento/s: um erro de transporte transitorio com algumas
# centenas de eventos na fila congelava o canvas por minutos e ainda enchia a
# fila, que passava a descartar tudo que chegava. O teto continua sendo o mesmo
# 1,0s — o que muda e nao pagar nada por uma falha isolada.
_SEND_RETRY_PAUSE = 1.0
_SEND_RETRY_PAUSE_MIN = 0.05
_SEND_FAIL_STREAK_LIMIT = 3


def _pausa_por_rajada(falhas_consecutivas: int) -> float:
    """Quanto dormir apos N falhas seguidas de envio. 0 ate o limite da rajada."""
    if falhas_consecutivas < _SEND_FAIL_STREAK_LIMIT:
        return 0.0
    crescimento = _SEND_RETRY_PAUSE_MIN * (2 ** (falhas_consecutivas - _SEND_FAIL_STREAK_LIMIT))
    return min(_SEND_RETRY_PAUSE, crescimento)

# Close codes que o servidor emite no accept() pos-handshake (executor_ws_router)
# para negar autoritativamente: 4401 nao autenticado, 4403 revogado/proibido,
# 4404 executor inexistente. Reconectar nesses casos so gera ruido.
_TERMINAL_CLOSE_CODES = frozenset({4401, 4403, 4404})


# Metricas de sistema moram em executor/sysinfo.py desde que o painel local
# passou a le-las tambem — antes o unico consumidor era o payload de capacity.
from executor.sysinfo import _collect_system_info, _get_dynamic_metrics  # noqa: E402


def _classify_connection_error(exc: Exception) -> tuple[str, bool, bool]:
    """Traduz excecoes de conexao WS em mensagem amigavel para o operador.

    Retorna `(mensagem, include_traceback, terminal)`:
      - `mensagem` — texto explicativo em portugues, sem stack trace.
      - `include_traceback` — True para erros genuinamente inesperados
        (bugs, bindings C exoticos). False para erros bem categorizados
        (poluiriam log a cada backoff).
      - `terminal` — True quando o servidor autoritativamente nega. IMPORTANTE:
        o app NUNCA nega via status HTTP no handshake — todo deny autoritativo
        (cert revogado, executor removido/nao encontrado, status invalido) chega
        como WS close code 4401/4403/4404 (ver executor_ws_router.py). Logo, um
        status HTTP 4xx/5xx no handshake so pode vir da BORDA (Traefik/Cloudflare)
        e, durante um deploy, e transitorio (proxy ainda sem rota para o backend
        recem-recriado retorna 404/502/503). Por isso NENHUM status HTTP e tratado
        como terminal aqui — apenas os close codes 44xx (mais abaixo) sao.
    """
    from websockets.exceptions import InvalidStatus, InvalidURI, ConnectionClosed

    if isinstance(exc, InvalidStatus):
        status = getattr(exc.response, "status_code", None)
        # HTTP 4xx/5xx no handshake = resposta do proxy reverso, NAO do app.
        # Durante deploy/restart o Traefik responde 404 (sem rota ainda) ou
        # 502/503 (backend subindo). Tudo transitorio → reconectar com backoff.
        # O deny real do app (executor removido/revogado) vem como close 4404/4403,
        # tratado como terminal na secao ConnectionClosed. Tratar 404 HTTP como
        # terminal derrubava o executor a cada deploy (exit 0, container nao
        # reiniciava com restart: on-failure).
        return (
            f"Handshake recusado pelo proxy (HTTP {status or '???'}) — provavel "
            "servidor em deploy/reinicio (sem rota ou backend subindo).",
            False, False,
        )

    if isinstance(exc, InvalidURI):
        return (f"URL do servidor invalida: {exc}", False, True)

    # SSL errors especificos — cert expirado, cadeia invalida, etc.
    # `ssl.SSLError` cai em `OSError` (herda) — precisa vir ANTES do OSError.
    import ssl as _ssl
    if isinstance(exc, _ssl.SSLError):
        reason = getattr(exc, "reason", "") or ""
        msg = str(exc)
        # Padroes conhecidos da libssl:
        if "CERTIFICATE_VERIFY_FAILED" in msg or "CERTIFICATE_VERIFY_FAILED" in reason:
            if "expired" in msg.lower():
                return (
                    "Cert mTLS local expirado. O renewal automatico falhou — "
                    "refaca enrollment com novo OTP OU verifique renewal.py "
                    "logs para diagnostico.",
                    False, True,
                )
            return (
                "Falha na verificacao do cert TLS do servidor. Verifique se "
                "atlans-root.crt esta atualizado (delete o arquivo em "
                "EXECUTOR_CERT_DIR e reinicie para forcar re-download).",
                False, False,
            )
        if "SSLV3_ALERT_CERTIFICATE_EXPIRED" in msg or "certificate has expired" in msg.lower():
            return (
                "Cert mTLS do cliente expirado. Refaca enrollment com novo OTP.",
                False, True,
            )
        if "SSLV3_ALERT_HANDSHAKE_FAILURE" in msg or "handshake_failure" in reason.lower():
            return (
                "TLS handshake rejeitado pelo servidor. Cert mTLS local pode "
                "estar corrompido ou nao pertencer mais a esta CA. "
                "Refaca enrollment.",
                False, True,
            )
        return (f"Erro TLS: {reason or msg}", False, False)

    if isinstance(exc, ConnectionClosed):
        code = getattr(exc, "code", None)
        reason = getattr(exc, "reason", None) or ""
        # Codigos 4401/4403/4404 sao os que o servidor emite no accept()
        # pos-handshake (executor_ws_router). Semantica alinhada com HTTP.
        terminal = code in _TERMINAL_CLOSE_CODES
        return (f"Conexao fechada pelo servidor (code={code} reason={reason!r}).", False, terminal)

    if isinstance(exc, OSError):
        return (
            f"Falha de rede: {type(exc).__name__}: {exc}. "
            "Verifique DNS, firewall e conectividade com o servidor.",
            False, False,
        )

    # Categoria desconhecida — inclui traceback para diagnostico
    return (f"Erro inesperado na conexao: {type(exc).__name__}: {exc}.", True, False)


class ExecutorConnection:
    """
    Gerencia a conexão WebSocket do executor com o servidor.

    Uso:
        conn = ExecutorConnection(job_queue, result_queue)
        await conn.run()  # loop infinito com reconnect automático
    """

    def __init__(self, job_queue: ExecutorJobQueue, result_queue: asyncio.Queue,
                 event_queue: asyncio.Queue | None = None,
                 drive_event_queue: asyncio.Queue | None = None,
                 stats=None, thread_pool=None):
        self._queue      = job_queue
        # Pool onde os nos rodam (main.py o instala como default do loop). Fica
        # aqui so para o capacity poder ser HONESTO: threads presas por um
        # PythonScript em laco infinito nao aparecem em queued/running, que
        # contam jobs — o executor continuava anunciando capacidade livre com o
        # pipeline inteiro parado, e o servidor seguia despachando para ele.
        self._thread_pool = thread_pool
        self._pool_saturado_seguidas = 0
        self._results    = result_queue
        self._events     = event_queue
        self._drive_events = drive_event_queue
        self._should_reconnect = True
        self.restart_requested: bool = False
        # Mensagem do deny autoritativo do servidor (close 4401/4403/4404), ou
        # None. Diferente de `restart_requested`, isto NAO se resolve sozinho:
        # so um enrollment novo devolve o executor ao ar. Quem supervisiona o
        # processo precisa saber a diferenca — religar um executor revogado e
        # um loop infinito contra um servidor que ja disse nao.
        self.terminal_deny: str | None = None
        # Sinaliza "nao espere o backoff, tente agora" — ver _esperar_retry.
        self._retry_agora = asyncio.Event()
        # Null object em vez de None: os call sites chamam self._stats.on_X()
        # direto, sem um `if` espalhado por cada ponto de estado da conexao.
        if stats is None:
            from executor.stats import NullStats
            stats = NullStats()
        self._stats = stats
        # Socket da sessao ATUAL, ou None durante o backoff de reconexao.
        # Existe só para `push_capacity()` — o resto do código recebe o `ws`
        # por parâmetro, que é mais difícil de usar errado.
        self._ws = None
        # Instante em que o handshake WS foi ACEITO (nao o inicio da tentativa),
        # ou None quando a tentativa nem chegou a abrir sessao. E o unico marco
        # honesto para o backoff: ver `_apply_session_backoff_reset`.
        self._sessao_iniciada_em: float | None = None
        # job_id -> instante do envio do resultado; ver `_lembrar_enviado`.
        self._enviados: dict[str, float] = {}

    async def push_capacity(self) -> None:
        """Envia um capacity report AGORA, fora do tick do `_capacity_loop`.

        O laço periódico dorme ANTES de enviar, então uma mudança de estado só
        chegava ao servidor até 10s depois. Isso importa num caso específico: ao
        entrar em drenagem o `get_capacity()` passa a anunciar saturação para
        sair do ranking least-loaded, e durante esses 10s o dispatch ainda podia
        escolher este executor — o job voltava como "Executor em shutdown." e o
        run fechava como FAILED sem failover. Empurrar na hora fecha a janela.

        Nunca levanta: é chamada de dentro do caminho de shutdown, e falhar em
        avisar o servidor não pode impedir o executor de encerrar.
        """
        ws = self._ws
        if ws is None:
            logger.debug("push_capacity: sem sessão WS ativa — nada a enviar.")
            return
        try:
            cap = self._montar_capacity()
            await ws.send(json.dumps({"type": "capacity", **cap}))
            logger.info(
                "Capacity enviado imediatamente (queued=%s running=%s).",
                cap.get("queued"), cap.get("running"),
            )
        except Exception as exc:
            logger.warning("Não foi possível enviar capacity imediato: %s", exc)

    # ── Loop principal (reconnect automático) ─────────────────────────────────

    async def run(self):
        """Loop infinito: conecta, recebe jobs, reconecta com backoff em caso de falha."""
        delay = 1
        while True:
            # `t0` serve SO ao log ("conexao encerrada apos X"): ele mede a
            # tentativa inteira, TCP + TLS/mTLS + upgrade incluidos. Quem decide
            # o backoff e `self._sessao_iniciada_em`, marcado depois do
            # handshake aceito — ver `_apply_session_backoff_reset`.
            t0 = time.monotonic()
            # Zerado a cada tentativa: sem isso a sessao boa da rodada anterior
            # faria o backoff de uma tentativa que nem abriu socket parecer
            # "sessao saudavel" e recuar.
            self._sessao_iniciada_em = None
            self._stats.on_connecting()
            try:
                await self._connect_and_run()
                if not self._should_reconnect:
                    logger.info("Executor encerrado pelo servidor.")
                    self._stats.on_disconnected(terminal=True)
                    break
                # Retorno limpo = servidor fechou a conexao sem erro (close 1000/1001)
                # ou o receive_loop terminou. Ainda assim e uma desconexao: precisa
                # do mesmo sleep do caminho de excecao, senao reconecta em spin.
                delay = self._apply_session_backoff_reset(delay)
                actual = com_jitter(delay)
                logger.warning(
                    "Conexão encerrada pelo servidor após %.1fs. Reconectando em %.1fs.",
                    time.monotonic() - t0, actual,
                )
                self._stats.on_disconnected(proximo_retry_s=actual)
                reagendado = await self._esperar_retry(actual)
                delay = 1 if reagendado else min(delay * 2, config.RECONNECT_MAX_DELAY)
            except asyncio.CancelledError:
                logger.info("Conexão cancelada — encerrando.")
                self._stats.on_disconnected(terminal=True)
                break
            except Exception as exc:
                if not self._should_reconnect:
                    logger.info("Reconnect desabilitado — encerrando executor.")
                    self._stats.on_disconnected(terminal=True)
                    break

                msg, include_tb, terminal = _classify_connection_error(exc)

                if terminal:
                    # 401/403/404 do servidor = authoritative deny (cert revogado,
                    # executor removido, id nao encontrado). Reconectar em loop
                    # so gera ruido; para o processo e o operador ve a mensagem
                    # clara nos logs. Volta a rodar so apos re-enrollment.
                    logger.error("%s Encerrando executor — refaça enrollment se necessario.", msg)
                    self._should_reconnect = False
                    self.terminal_deny = msg
                    self._stats.on_disconnected(terminal=True)
                    break

                delay = self._apply_session_backoff_reset(delay)
                # Jitter de 50-100% evita thundering herd quando N executores
                # reconectam sincronamente após queda do servidor. A fórmula
                # nasceu aqui e hoje mora em `flow/utils/backoff.py`, de onde os
                # outros laços da plataforma passaram a lê-la.
                actual = com_jitter(delay)
                logger.error("%s Reconectando em %.1fs.", msg, actual, exc_info=include_tb)
                self._stats.on_disconnected(proximo_retry_s=actual)
                reagendado = await self._esperar_retry(actual)
                delay = 1 if reagendado else min(delay * 2, config.RECONNECT_MAX_DELAY)

    async def _esperar_retry(self, segundos: float) -> bool:
        """Dorme ate a proxima tentativa, mas acorda se alguem pedir agora.

        Retorna True se a espera foi encurtada por `reconectar_agora()` — o
        caller entao zera o backoff, porque quem pediu sabe de algo que o
        processo nao sabia (a rede voltou, o servidor subiu). Sem isso, um
        operador que acabou de consertar a rede esperaria o backoff inteiro,
        que chega a RECONNECT_MAX_DELAY (15s por padrao).
        """
        self._retry_agora.clear()
        try:
            await asyncio.wait_for(self._retry_agora.wait(), timeout=segundos)
            return True
        except asyncio.TimeoutError:
            return False

    def reconectar_agora(self) -> bool:
        """Interrompe o backoff em curso. Retorna False se nao havia espera.

        Seguro de chamar a qualquer momento: com o WS vivo, o evento so fica
        marcado e e limpo na proxima espera.
        """
        if self._retry_agora.is_set():
            return False
        self._retry_agora.set()
        return True

    def _apply_session_backoff_reset(self, delay: int | float) -> int | float:
        """Ajusta o backoff conforme a SESSAO WS que acabou de terminar.

        O relogio comeca em `self._sessao_iniciada_em`, marcado depois que o
        handshake foi ACEITO — nunca no inicio da tentativa. Medir a tentativa
        inteira quebrava a defesa anti-spin no cenario mais caro: servidor em
        deploy/sobrecarga aceita o TCP e nunca completa o upgrade, o
        `websockets.connect` estoura o open_timeout (10s) e essa espera contava
        como "sessao que progrediu". O delay entao caia pela metade e o `run()`
        logo o dobrava — halve-then-double e neutro —, entao ele oscilava 1<->2
        para sempre e a frota refazia handshake mTLS a cada ~1s por horas.

        Tres faixas, e nao duas:
          - sessao saudavel (> _SESSION_STABLE_SECONDS): zera;
          - sessao que ao menos FUNCIONOU por um tempo
            (>= _SESSION_PROGRESS_SECONDS): recua para um QUARTO. Tem que ser
            menos que a metade justamente porque o caller dobra logo depois: com
            /2 o saldo era zero e a faixa nao recuava nada. Sem esta faixa, uma
            sessao de 59s que caia repetidamente (rede instavel, proxy
            reciclando conexao) nunca reduzia o delay: ele so crescia, e o
            executor sumia do painel por dezenas de segundos a cada queda de
            poucos segundos de indisponibilidade real;
          - sessao que morre logo apos o handshake — ou que nunca chegou a
            existir (`_sessao_iniciada_em is None`: DNS, TCP recusado, TLS
            reprovado, upgrade pendurado): mantem o acumulado, que e o que
            garante o crescimento exponencial contra um erro repetido.
        """
        inicio = self._sessao_iniciada_em
        if inicio is None:
            return delay
        duracao = time.monotonic() - inicio
        if duracao > _SESSION_STABLE_SECONDS:
            return 1
        if duracao >= _SESSION_PROGRESS_SECONDS:
            return max(1, delay / 4)
        return delay

    async def _connect_and_run(self):
        ws_url = f"{config.SERVER_URL}/ws/executores/{config.EXECUTOR_ID}"

        logger.info("Conectando a %s ...", config.SERVER_URL)
        from executor.utils import is_local_server, build_mtls_ssl_context
        if is_local_server(config.SERVER_URL):
            ssl_ctx = None  # ws:// local nao precisa de SSL
        else:
            # wss:// producao com mTLS — cert + chave + CA pinada do enrollment.
            # Identidade do executor vem do cert; backend valida CN/serial e
            # checa blacklist Redis. Sem JWT intermediario.
            ssl_ctx = build_mtls_ssl_context()
        async with websockets.connect(
            ws_url,
            # Heartbeat aplicativo (30s) é a fonte de verdade. Ping WS nativo
            # estava forçando close em 10s quando atrás de proxy/Traefik com
            # latência — desativado para manter comportamento pré-mudança.
            ping_interval=None,
            close_timeout=10,
            ssl=ssl_ctx,
            max_size=_MAX_WS_PAYLOAD,  # casa com ws_max_size do uvicorn
        ) as ws:
            logger.info("Conectado a %s (executor v%s).", config.SERVER_URL, config.EXECUTOR_VERSION)
            # Marco do backoff: a partir DAQUI existe sessao. Tudo que veio
            # antes (TCP, TLS/mTLS, upgrade) e custo de tentativa, nao tempo de
            # servico — ver `_apply_session_backoff_reset`.
            self._sessao_iniciada_em = time.monotonic()
            self._stats.on_connected()
            # Handle da sessao viva, para `push_capacity()` poder enviar fora do
            # tick de 10s do _capacity_loop. Limpo no `finally` abaixo: durante o
            # backoff de reconexao NAO ha socket, e mandar para um ws morto so
            # geraria excecao no caminho de shutdown.
            self._ws = ws

            # Envia handshake com versão do executor e info de hardware.
            # protocol_version declara compatibilidade — server rejeita se
            # não estiver em SUPPORTED_PROTOCOL_VERSIONS (flow/utils/protocolo_ws.py).
            sys_info = _collect_system_info()
            await ws.send(json.dumps({
                "type":             "handshake",
                "protocol_version": PROTOCOL_VERSION,
                "executor_version":    config.EXECUTOR_VERSION,
                **({"system_info": sys_info} if sys_info else {}),
            }))

            # Inicia tarefas paralelas como Tasks para permitir cancelamento
            tasks: list[asyncio.Task] = [
                asyncio.create_task(self._heartbeat_loop(ws),     name="heartbeat"),
                asyncio.create_task(self._capacity_loop(ws),      name="capacity"),
                asyncio.create_task(self._inventario_loop(ws),    name="inventario"),
                asyncio.create_task(self._receive_loop(ws),       name="receive"),
                asyncio.create_task(self._result_sender_loop(ws), name="results"),
            ]
            if self._events is not None:
                tasks.append(asyncio.create_task(self._event_sender_loop(ws), name="events"))

            # Aguarda a PRIMEIRA task concluir — normalmente é _receive_loop quando o
            # servidor fecha a conexão. Cancelar as demais imediatamente permite que o
            # loop externo reconecte sem esperar o heartbeat dormir 30 segundos.
            try:
                done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                # try/finally OBRIGATORIO: `asyncio.wait` NAO cancela o que
                # aguarda. Quando o main cancela o conn_task (SIGTERM), o
                # CancelledError sobe de dentro do wait e, sem este finally, os
                # 5 loops filhos sobreviviam ao gather do shutdown — ficavam ate
                # 5s bloqueados no `wait_for(get(), 5.0)` consumindo das MESMAS
                # filas que o main ja deu por drenadas, e o que chegasse nessa
                # janela era retirado e descartado (ws fechado). Cancelar aqui e
                # o que faz o rotulo "shutdown ORDENADO" de main.py valer para
                # os filhos da conexao.
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                # Sessao acabou: sem socket ate a proxima conexao.
                self._ws = None

            # A excecao que derrubou a sessao PRECISA subir para run(): o
            # `async with websockets.connect` nao re-levanta no __aexit__, entao
            # engolir aqui fazia _connect_and_run retornar como se fosse encerramento
            # limpo — o motivo real (close 4408/4426/1003/1011, queda de rede) sumia
            # do log em LOG_LEVEL=INFO e o backoff era pulado. Propagar tambem e o
            # que leva um ConnectionClosed com code 4401/4403/4404 ate o
            # _classify_connection_error, que o marca como terminal.
            #
            # `done` e um SET: iterar direto escolhia uma excecao ARBITRARIA
            # quando mais de uma task terminava no mesmo batch. O _receive_loop
            # e a fonte autoritativa do motivo (e ele que carrega o
            # ConnectionClosed com o close code do servidor); os demais loops so
            # refletem o mesmo close. Dai a prioridade explicita.
            first_exc: Exception | None = None
            for task in sorted(done, key=lambda t: 0 if t.get_name() == "receive" else 1):
                exc = task.exception() if not task.cancelled() else None
                if exc is None or isinstance(exc, asyncio.CancelledError):
                    continue
                if first_exc is None:
                    first_exc = exc
                else:
                    logger.debug("Task '%s' encerrada com exceção: %s", task.get_name(), exc)

            if first_exc is None:
                # Nenhuma excecao em `done` — mas os loops auxiliares tratam
                # ConnectionClosed com `break` e terminam LIMPOS. Se um deles
                # vencer a corrida com o _receive_loop, o receive vai para
                # `pending` e e cancelado antes de levantar: um deny
                # autoritativo (4401 revogado / 4403 / 4404) virava "conexao
                # encerrada, reconecte em backoff" e o operador nunca via
                # "refaca enrollment". O ws ja registrou o code no handshake de
                # close — ele e a fonte de verdade que sobrevive ao cancelamento.
                code = getattr(ws, "close_code", None)
                if code in _TERMINAL_CLOSE_CODES:
                    first_exc = ConnectionClosedError(
                        Close(code, getattr(ws, "close_reason", "") or ""), None
                    )

            if first_exc is not None:
                raise first_exc

    # ── Loops paralelos ───────────────────────────────────────────────────────

    async def _receive_loop(self, ws):
        """Recebe mensagens do servidor e enfileira jobs."""
        # Contador de JSONs invalidos consecutivos. Serve como backoff
        # cliente-side: N erros seguidos -> pequeno sleep antes de continuar,
        # evitando spin apertado se o servidor bugar enviando payload
        # corrompido em loop. Sem isso, o server desconectava em 5 msgs
        # invalidas (code 1003) e o cliente reconectava imediato, mesmo
        # bug se repetia em ciclo.
        _CLIENT_JSON_BACKOFF_THRESHOLD = 3
        _CLIENT_JSON_BACKOFF_SLEEP = 2.0
        invalid_streak = 0

        async for raw in ws:
            try:
                msg = json.loads(raw)
                invalid_streak = 0
            except json.JSONDecodeError:
                invalid_streak += 1
                logger.warning(
                    "Mensagem inválida recebida (streak=%d): %r",
                    invalid_streak, raw[:200],
                )
                if invalid_streak >= _CLIENT_JSON_BACKOFF_THRESHOLD:
                    # Backoff para evitar spin apertado — permite o
                    # servidor ou o operador intervir antes de acumular
                    # ate o server disparar close 1003.
                    await asyncio.sleep(_CLIENT_JSON_BACKOFF_SLEEP)
                continue

            msg_type = msg.get("type")
            # Allowlist do protocolo servidor → executor. Tudo fora dela e
            # descartado antes de qualquer processamento. Defesa em profundidade
            # junto do HMAC nos canais de relay: se algum dia uma mensagem nao
            # autenticada chegar ao WS, ela nao encontra handler
            # novo/experimental exposto por acidente.
            if msg_type not in TIPOS_DO_SERVIDOR:
                logger.debug("Mensagem desconhecida do servidor: %s", msg_type)
                continue

            # SEG (S7): comandos que MUDAM O ESTADO do executor (derrubar,
            # reiniciar, interromper job) exigem assinatura Ed25519 do servidor,
            # igual ao `job`. Antes bastava a allowlist de tipos acima: quem
            # conseguisse escrever no WS ou publicar no relay Redis derrubava a
            # frota com um "control/shutdown" sem forjar nada. `job` tem
            # validação própria em job_executor; `drive_event` não muda estado e
            # segue sem assinatura.
            if msg_type in _SIGNED_SERVER_MESSAGES:
                try:
                    validate_control_message(msg)
                except JobValidationError as exc:
                    logger.error(
                        "Comando '%s' REJEITADO pela validação de segurança: %s",
                        msg_type, exc,
                    )
                    continue

            if msg_type == "job":
                await self._handle_job(ws, msg)
            elif msg_type == "drive_event":
                await self._handle_drive_event(msg)
            elif msg_type == "control":
                action = msg.get("action", "")
                reason = msg.get("reason", "")
                if action not in _CONTROL_ACTIONS:
                    logger.warning("Acao de control desconhecida ignorada: %r", action)
                    continue
                if action == "revoked":
                    logger.warning("Servidor: executor revogado — %s", reason)
                    self._should_reconnect = False
                    # Mesma classe do close 4404: so um enrollment novo resolve.
                    self.terminal_deny = f"Executor revogado pelo servidor. {reason}".strip()
                    return  # Sai do loop, connection.run() vai encerrar
                elif action == "shutdown":
                    logger.warning("Servidor: shutdown solicitado — %s", reason)
                    self._should_reconnect = False
                    # NAO e deny: o servidor pediu para parar, o enrollment
                    # continua valido e o executor volta ao ar quando religado.
                    return
                elif action == "purge_artifacts":
                    # Retencao expirada: o servidor manda apagar artefatos que
                    # moram so neste disco. Nao encerra a conexao — e limpeza,
                    # nao deny.
                    from executor.artifact_purge import purgar
                    # `purgar` faz stat/unlink/rmdir por artefato — I/O de disco
                    # sincrono no laco de recepcao do WS. Vai para thread para
                    # nao segurar heartbeat/entrega de jobs numa ordem de
                    # retencao com muitos artefatos.
                    n = await asyncio.to_thread(purgar, msg.get("artifacts") or [])
                    logger.info(
                        "Servidor: remocao de artefatos locais — %d apagado(s). %s",
                        n, reason,
                    )
                    continue
                elif action == "config_changed":
                    logger.info("Servidor: configuração alterada — %s. Reiniciando executor...", reason)
                    self._should_reconnect = False
                    self.restart_requested = True
                    # Sai pelo caminho asyncio normal: _receive_loop ->
                    # _connect_and_run -> run() -> main(), que observa o fim
                    # do conn_task e faz o shutdown ordeiro antes do
                    # sys.exit(1) (Docker restart: on-failure reinicia).
                    #
                    # Nao auto-enviamos SIGTERM: em POSIX era redundante e no
                    # Windows nao havia handler registrado (add_signal_handler
                    # levanta NotImplementedError), deixando o processo
                    # pendurado sem reiniciar.
                    return
            elif msg_type == "cancel":
                job_id = msg.get("job_id")
                if not job_id:
                    logger.warning("Mensagem 'cancel' sem job_id — ignorada.")
                    continue
                outcome = self._queue.cancel(job_id)
                if outcome == "unknown":
                    outcome = await self._encerrar_cancelamento_desconhecido(job_id)
                logger.info("Cancelamento do job '%.8s': %s", job_id, outcome)
            elif msg_type == TIPO_ERRO:
                # O servidor recusou (e descartou) uma mensagem deste executor:
                # JSON invalido, campo obrigatorio ausente, capacity invalida,
                # mensagem antes do handshake, versao nao suportada. Nao ha o
                # que refazer, mas o motivo tem de aparecer AQUI: antes `error`
                # ficava fora da allowlist e caia em "Mensagem desconhecida", em
                # DEBUG — a recusa so existia no log do servidor, que o operador
                # do executor nao ve. So registro, sem efeito: a mensagem nao e
                # assinada.
                detalhe = {k: v for k, v in msg.items() if k not in ("type", "reason")}
                logger.warning(
                    "Servidor recusou uma mensagem deste executor: reason=%r %s",
                    str(msg.get("reason"))[:100],
                    json.dumps(detalhe, ensure_ascii=False)[:500] if detalhe else "",
                )

    async def _handle_job(self, ws, message: dict):
        """Valida back-pressure e enfileira o job para execução."""
        job_id   = message.get("envelope", {}).get("job_id", "?")
        job_type = message.get("envelope", {}).get("job_type", "?")
        logger.info("Job recebido  id=%.8s  type=%s", job_id, job_type)

        # Cancelado enquanto viajava: o servidor já fechou o run como cancelado
        # (ver `_encerrar_cancelamento_desconhecido`). Rodá-lo agora seria
        # executar — com efeitos colaterais — algo que o usuário mandou parar.
        if self._queue.cancelado_antes_de_chegar(job_id):
            logger.info("Job '%.8s' descartado: foi cancelado antes de chegar.", job_id)
            return

        if self._queue.is_full():
            # Informa o servidor que não pode aceitar
            await ws.send(json.dumps({
                "type":   "job_result",
                "job_id": job_id,
                "status": "error",
                "error":  "Fila do executor cheia — back-pressure.",
            }))
            logger.warning("Job '%s' rejeitado por back-pressure.", job_id)
            return

        accepted = await self._queue.enqueue(message)
        if accepted:
            logger.info("Job '%s' enfileirado.", job_id)
            # Diário em disco: se o processo morrer antes de o job produzir
            # resultado, o próximo boot o reporta como interrompido em vez de o
            # run ficar "Em andamento" no servidor (ver result_store).
            from executor import result_store
            result_store.registrar_em_voo(job_id)
            # ACK de recepção — server usa para detectar jobs perdidos entre
            # "send_text retornou OK" e "executor de fato enfileirou".
            try:
                await ws.send(json.dumps({
                    "type":   "ack",
                    "job_id": job_id,
                    "status": "enqueued",
                }))
            except Exception as exc:
                logger.warning("Falha ao enviar ACK do job '%s': %s", job_id, exc)
        else:
            await ws.send(json.dumps({
                "type":   "job_result",
                "job_id": job_id,
                "status": "error",
                "error":  "Executor em shutdown.",
            }))

    async def _handle_drive_event(self, msg: dict):
        """Encaminha evento Drive para a fila do SyncManager."""
        if self._drive_events is not None:
            try:
                self._drive_events.put_nowait(msg)
                action = msg.get("action", "?")
                fname = msg.get("file", {}).get("original_name", "?")
                logger.info("Drive event recebido: %s → %s", action, fname)
            except asyncio.QueueFull:
                logger.warning("Fila de drive_events cheia — evento descartado.")

    async def _result_sender_loop(self, ws):
        """Lê resultados da fila de saída e os envia ao servidor como job_result."""
        from executor import result_store

        falhas_seguidas = 0
        while True:
            try:
                result: dict = await asyncio.wait_for(self._results.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            sent_ok = False
            closed = False
            # Contador interno de tentativas (mesma chave do event loop): sai do
            # dict antes do send para nunca trafegar no protocolo. Lido fora do
            # try porque os handlers de excecao dependem dele.
            attempts = result.pop(_ATTEMPTS_KEY, 0) if isinstance(result, dict) else 0
            try:
                # O 'output' ja foi descartado na origem (executor/main.py, on_execute):
                # nunca entra na _result_queue. O servidor so usa job_id, run_id,
                # status, error e stats para atualizar o WorkflowRun.
                # _dumps_result continua obrigatorio: 'stats' ainda pode carregar
                # Timestamp/numpy e estourar o limite de payload do WS.
                await ws.send(_dumps_result({"type": "job_result", **result}))
                logger.info("Job %.8s → %s", result.get("job_id", "?"), (result.get("status") or "?").upper())
                sent_ok = True
                falhas_seguidas = 0
                # Marca d'agua de ENVIO (nao de consumo): o `task_done()` abaixo
                # e incondicional e nao distingue enviado de re-enfileirado.
                self._marcar_enviado(self._results, result)
            except ConnectionClosed:
                # Devolve o resultado para a fila — será reenviado após reconexão.
                # O result_store ainda mantém uma cópia persistente, então reinício
                # do processo também preserva o resultado.
                self._requeue_result(result, attempts)
                closed = True
            except asyncio.CancelledError:
                # CancelledError NAO e Exception: sem este ramo, um cancelamento
                # durante o `ws.send` (acontece em TODA queda de sessao — o
                # _connect_and_run cancela os loops) deixava o resultado fora da
                # fila, o `finally` fazia task_done() e o
                # `_result_queue.join()` do shutdown reportava "drenado" para
                # algo que nunca foi enviado. Perda silenciosa, sem nem o log de
                # ERROR dos outros caminhos: o run so voltava a andar no proximo
                # start do processo, pelo outbox.
                self._requeue_result(result, attempts)
                raise
            except Exception as exc:
                # Qualquer outro erro (json dump, encoding, RuntimeError) —
                # devolve para a fila. Sem isso, o resultado sumiria da
                # queue in-memory e o executor precisava restart para
                # que result_store.load_pending() drenasse. Mas com TETO: ver
                # _MAX_RESULT_SEND_ATTEMPTS.
                attempts += 1
                # DELETE/UPDATE por chave em SQLite WAL custa microssegundos e o
                # store inteiro ja e serializado por RLock com os `put()` deste
                # mesmo event loop — chamar sincrono e correto. A versao com
                # `asyncio.to_thread` piorava o que dizia consertar: caia no pool
                # DEFAULT (main.py instala o _thread_pool nele), o mesmo dos
                # `to_thread` dos nos GIS, e um batch de nos pesados segurava a
                # entrega de TODOS os resultados por minutos.
                result_store.increment_attempts(str(result.get("job_id") or ""))
                falhas_seguidas += 1
                if attempts >= _MAX_RESULT_SEND_ATTEMPTS:
                    # Fora da fila para sempre — fecha a conta da marca d'agua,
                    # senao o `_aguardar_confirmacao` do shutdown espera por um
                    # resultado que so voltara pelo outbox no proximo start.
                    self._marcar_resolvido(self._results, result)
                    logger.error(
                        "Resultado do job '%s' descartado da fila apos %d tentativas (%s) — "
                        "permanece no outbox e sera reenviado no proximo start.",
                        result.get("job_id"), attempts, exc,
                    )
                else:
                    logger.error(
                        "Erro ao enviar resultado do job '%s' (tentativa %d) — re-enfileirando: %s",
                        result.get("job_id"), attempts, exc,
                    )
                    self._requeue_result(result, attempts)
                    # Pausa por RAJADA: falha isolada nao custa nada; so um erro
                    # que se repete vira sleep (este e o unico consumidor da
                    # fila, entao um spin apertado a travaria).
                    pausa = _pausa_por_rajada(falhas_seguidas)
                    if pausa:
                        await asyncio.sleep(pausa)
            finally:
                # task_done() INCONDICIONAL. O re-enqueue conta como item novo
                # (put() incrementa _unfinished_tasks), entao o saldo fecha:
                # get() -> put() (+1) -> task_done() (-1) = 0. O 'if not requeued'
                # anterior deslocava o contador +1 PERMANENTEMENTE e travava
                # qualquer join() nesta fila.
                self._results.task_done()

            if closed:
                break

            # Fora do try/except para não rodar se ConnectionClosed (retentativa)
            if sent_ok:
                enviado = str(result.get("job_id") or "")
                self._lembrar_enviado(enviado)
                result_store.mark_sent(enviado)

    def _requeue_result(self, result: dict, attempts: int = 0) -> None:
        """Devolve um resultado nao enviado para a fila sem nunca bloquear.

        put_nowait em vez de await put(): este loop e o UNICO consumidor da fila,
        entao aguardar espaco numa fila cheia seria deadlock garantido — e a
        _result_queue TEM limite (main.py dimensiona em MAX_QUEUE_SIZE +
        MAX_CONCURRENT + 32). Fila cheia significa desistir do envio in-memory;
        o result_store mantem a copia persistente para o replay no restart.
        """
        # Encerra a conta da entrada ANTERIOR antes do put, que abre uma nova.
        self._marcar_resolvido(self._results, result)
        if attempts:
            result[_ATTEMPTS_KEY] = attempts
        try:
            self._results.put_nowait(result)
        except asyncio.QueueFull:
            logger.error(
                "Fila de resultados cheia — job '%s' sera reenviado apenas no "
                "proximo restart (result_store.load_pending).",
                result.get("job_id"),
            )
        except Exception:
            logger.exception("Falha ao re-enfileirar resultado do job '%s'", result.get("job_id"))

    async def _event_sender_loop(self, ws):
        """Drena a fila de eventos de nós e os envia ao servidor como node_event."""
        # Sessao nova: devolve para a fila o ciclo de vida que se perdeu enquanto
        # nao havia socket (ver ColetorDeLifecycle).
        self._ressincronizar_lifecycle()
        falhas_seguidas = 0
        try:
            while True:
                # A fila folgou: devolve para ela o lifecycle que a PRESSAO fez
                # cair no coletor. Sem isto, so a reconexao drenava — e a fila
                # enche por producao (workflow de 300 nos em debug_mode) muito
                # mais vezes do que a sessao cai. Os nos ficavam com spinner ate
                # o fim do run e os eventos presos em memoria; e o reenvio, se
                # viesse, vinha horas depois, num run que o servidor ja fechou.
                self._ressincronizar_lifecycle(so_com_folga=True)
                try:
                    event: dict = await asyncio.wait_for(self._events.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

                closed = False
                # O contador de tentativas e interno: sai do dict antes do send
                # para nunca trafegar no protocolo. Lido fora do try porque os
                # handlers de excecao dependem dele.
                attempts = event.pop(_ATTEMPTS_KEY, 0) if isinstance(event, dict) else 0
                try:
                    # _dumps_event (e nao json.dumps cru): um node_event com
                    # objeto nao-serializavel levantava TypeError, caia no ramo
                    # generico, re-enfileirava o MESMO evento e repetia para
                    # sempre em laco apertado. E aplica o teto de tamanho
                    # PROPRIO do evento — a truncagem por 'stats' do job_result
                    # nao servia aqui (evento nao tem 'stats').
                    await ws.send(_dumps_event({"type": "node_event", **event}))
                    falhas_seguidas = 0
                    # Ver o comentario equivalente no _result_sender_loop: a
                    # barreira de fim de job so pode contar o que SAIU pelo WS.
                    self._marcar_enviado(self._events, event)
                except ConnectionClosed:
                    logger.warning(
                        "Node event descartado por ConnectionClosed — re-enfileirando node=%s status=%s",
                        event.get("node"), event.get("status"),
                    )
                    self._requeue_event(event, attempts)
                    closed = True
                except asyncio.CancelledError:
                    # Ver o ramo equivalente no _result_sender_loop: sem ele o
                    # evento saia da fila no cancelamento e o
                    # `_event_queue.join()` de on_execute dava a fila por
                    # drenada com um update de UI perdido.
                    self._requeue_event(event, attempts)
                    raise
                except Exception as exc:
                    # Qualquer outro erro (serializacao, WS state invalido) —
                    # re-enfileira em vez de descartar. Sem isso a UI perde
                    # updates do grafo e mostra o workflow congelado. Mas com
                    # teto: apos _MAX_EVENT_SEND_ATTEMPTS o evento e descartado,
                    # porque a falha e provavelmente deterministica e um evento
                    # imortal prende o unico consumidor da fila.
                    attempts += 1
                    falhas_seguidas += 1
                    if attempts >= _MAX_EVENT_SEND_ATTEMPTS:
                        # Desistiu deste evento — mas se ele era ciclo de vida, o
                        # canvas ficaria com o no eternamente "executando". Guarda
                        # o ultimo status para a ressincronizacao da proxima sessao.
                        # Só os campos de controle: a falha aqui é
                        # DETERMINISTICA (payload nao serializavel), e reenviar o
                        # evento inteiro so repetiria as 3 tentativas a cada
                        # reconexao.
                        self._registrar_perda(event, minimo=True)
                        # Nao volta para a fila: fecha a conta para a barreira de
                        # fim de job nao ficar esperando um evento que nunca vira.
                        self._marcar_resolvido(self._events, event)
                        logger.error(
                            "Node event node=%s status=%s descartado apos %d tentativas: %s",
                            event.get("node"), event.get("status"), attempts, exc,
                        )
                    else:
                        logger.warning(
                            "Erro ao enviar node_event node=%s status=%s (tentativa %d) — re-enfileirando: %s",
                            event.get("node"), event.get("status"), attempts, exc,
                        )
                        self._requeue_event(event, attempts)
                        # Pausa por RAJADA (ver _pausa_por_rajada): o 1s por item
                        # transformava a fila num funil de 1 evento/s.
                        pausa = _pausa_por_rajada(falhas_seguidas)
                        if pausa:
                            await asyncio.sleep(pausa)
                finally:
                    # task_done() INCONDICIONAL — ver comentario no
                    # _result_sender_loop. Aqui o efeito do bug era pior: o
                    # _event_queue.join() de main.py (on_execute) nunca mais
                    # resolvia e TODO job subsequente pagava 30s de timeout
                    # ("Timeout ao drenar fila de eventos — 0 evento(s) pendente(s)").
                    self._events.task_done()

                if closed:
                    break
        except Exception:
            logger.exception("Erro fatal no event_sender_loop")

    def _requeue_event(self, event: dict, attempts: int) -> None:
        """Devolve um node_event nao enviado para a fila sem nunca bloquear.

        `await put()` numa fila com maxsize=500 cheia era DEADLOCK: este loop e o
        unico consumidor da _event_queue, entao ele ficaria bloqueado no proprio
        put esperando a si mesmo consumir. Com put_nowait, fila cheia significa
        descartar o evento — node_event e telemetria de UI, nao dado de negocio.
        """
        # Encerra a conta da entrada ANTERIOR antes do put, que abre uma nova.
        # Vale tambem quando o put falha por fila cheia: ali o evento se perde de
        # vez e a marca d'agua precisa igualmente ser fechada.
        self._marcar_resolvido(self._events, event)
        if attempts:
            event[_ATTEMPTS_KEY] = attempts
        try:
            self._events.put_nowait(event)
        except asyncio.QueueFull:
            self._registrar_perda(event)
            logger.warning(
                "Fila de node_events cheia — evento node=%s status=%s descartado.",
                event.get("node"), event.get("status"),
            )
        except Exception:
            logger.exception("Falha ao re-enfileirar node_event")

    # ── Ressincronizacao do ciclo de vida apos queda ──────────────────────────

    @staticmethod
    def _marcar_enviado(fila, item: dict) -> None:
        """Avisa a fila contada que o item saiu de fato pelo WebSocket.

        Duck typing de proposito: em teste (e em qualquer uso avulso) as filas
        sao `asyncio.Queue` cruas, que nao contam nada — e nao precisam.
        """
        marcar = getattr(fila, "confirmar_envio", None)
        if marcar is not None:
            marcar(item)

    @staticmethod
    def _marcar_resolvido(fila, item: dict) -> None:
        """Fecha a conta de um item que saiu da fila SEM ter sido enviado.

        Obrigatorio em TODO caminho de re-enfileiramento e de descarte
        definitivo: o `_put` conta cada entrada na fila, entao sem este
        contrapeso um unico retry deixava a marca d'agua daquele run devendo 1
        para sempre — e a barreira de fim de job, que espera
        `confirmados >= alvo`, so saia pelo timeout de estagnacao (3s de atraso
        no `__workflow_complete__` de todo job que tivesse uma falha de envio).
        """
        marcar = getattr(fila, "resolver_sem_envio", None)
        if marcar is not None:
            marcar(item)

    def _registrar_perda(self, event: dict, minimo: bool = False) -> None:
        """Guarda o ultimo lifecycle de um evento perdido, para reenviar depois."""
        coletor = getattr(self._events, "coletor", None)
        if coletor is None:
            return
        if minimo:
            guardado = {k: event[k] for k in CAMPOS_DE_CONTROLE if k in event}
        else:
            # Sem a chave interna de tentativas: ela nao pode voltar junto e
            # fazer o evento ressincronizado nascer ja no teto de retentativas.
            guardado = {k: v for k, v in event.items() if k != _ATTEMPTS_KEY}
        coletor.registrar(guardado)

    def _ressincronizar_lifecycle(self, so_com_folga: bool = False) -> None:
        """Reenfileira o ciclo de vida que se perdeu (queda de sessao OU pressao).

        Sem isto, uma queda de rede de 30-60s no meio de um workflow longo
        deixava o canvas permanentemente errado: os nos que terminaram na janela
        continuavam com o spinner ate o run inteiro fechar. Sao node_events
        normais — o servidor ja sabe reconstruir o canvas a partir deles e ordena
        por timestamp, entao reenviar um `completed` ja visto e inofensivo.

        Com `so_com_folga=True` (a chamada de cada volta do sender, com a sessao
        VIVA) o reenvio so acontece quando a fila esta abaixo da metade. E o que
        impede o remedio de virar a doenca: devolver os eventos numa fila ainda
        cheia dispararia o descarte por pressao de novo, num laco entre coletor e
        fila que nao deixaria o sender drenar o backlog que abriria a folga.
        """
        coletor = getattr(self._events, "coletor", None)
        if coletor is None:
            return
        if so_com_folga:
            if not len(coletor):
                return
            maxsize = getattr(self._events, "maxsize", 0) or 0
            if maxsize and self._events.qsize() >= maxsize // 2:
                return
        pendentes = coletor.drenar()
        if not pendentes:
            return
        logger.info(
            "Reenviando %d evento(s) de ciclo de vida que nao couberam antes "
            "(%s).", len(pendentes),
            "fila folgou" if so_com_folga else "sessao restabelecida",
        )
        for i, evento in enumerate(pendentes):
            try:
                self._events.put_nowait(evento)
            except asyncio.QueueFull:
                # Fila ja cheia com producao nova: devolve o que sobrou ao
                # coletor e tenta de novo na proxima sessao. Insistir aqui so
                # geraria log em laco.
                for restante in pendentes[i:]:
                    coletor.registrar(restante)
                logger.warning(
                    "Fila de node_events cheia na ressincronizacao — %d evento(s) "
                    "adiados para a proxima sessao.", len(pendentes) - i,
                )
                return

    async def _heartbeat_loop(self, ws):
        """Envia heartbeat periódico ao servidor."""
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            try:
                await ws.send(json.dumps({"type": "heartbeat"}))
                # Marcado APOS o send: a idade do heartbeat so significa algo
                # se contar desde o ultimo que realmente saiu pela conexao.
                self._stats.on_heartbeat()
            except ConnectionClosed:
                break

    async def _capacity_loop(self, ws):
        """Reporta capacidade da fila ao servidor periodicamente."""
        while True:
            await asyncio.sleep(_CAPACITY_INTERVAL)
            try:
                cap = self._montar_capacity()
                await ws.send(json.dumps({"type": "capacity", **cap}))
            except ConnectionClosed:
                break

    async def _inventario_loop(self, ws):
        """Manda ao servidor, logo após o handshake e a cada minuto, os jobs que
        este executor TEM: ativos (fila, semáforo, execução) e com resultado
        ainda não confirmado.

        É o que fecha o buraco do run "Em andamento" para sempre: um job que se
        perdeu no caminho (worker da API morto, relay sem destino, reinício do
        executor) não está aqui, e o servidor fecha o run em minutos em vez de
        esperar uma desconexão que pode nunca vir — em 22/09 o titan ficou
        conectado com três runs perdidos até 09:16.
        """
        while True:
            # Laço auxiliar: um erro ao MONTAR o inventário (outbox ilegível, por
            # exemplo) pula esta volta, não derruba a sessão — o `wait` do
            # _connect_and_run encerraria a conexão inteira com a primeira task
            # que terminasse.
            try:
                inventario = self._montar_inventario()
            except Exception as exc:
                logger.warning("Inventário de jobs não montado nesta volta: %s", exc)
                inventario = None
            if inventario is not None:
                try:
                    await ws.send(json.dumps(inventario))
                except ConnectionClosed:
                    break
            await asyncio.sleep(_INVENTARIO_INTERVAL)

    def _lembrar_enviado(self, job_id: str) -> None:
        """Guarda por alguns minutos o id de um resultado que acabou de sair.

        `mark_sent` apaga o resultado do outbox assim que o `ws.send` retorna,
        mas o servidor pode ainda não o ter processado: a conexão caiu logo
        depois e o inbox dela segue drenando noutro worker, ou o consumer está
        atrasado. Nesse intervalo o job não estava em lugar nenhum daqui, e:
          - o inventário da sessão nova dizia "não tenho" — o servidor fechava
            o run como perdido e depois recusava o resultado verdadeiro;
          - um cancel virava um 'cancelled' sintético por cima de um sucesso.
        """
        if not job_id:
            return
        self._enviados.pop(job_id, None)
        self._enviados[job_id] = time.monotonic()
        while len(self._enviados) > _ENVIADOS_MAX:
            self._enviados.pop(next(iter(self._enviados)))

    def _resultados_pendentes(self) -> set[str] | None:
        """Resultados que ainda não saíram: no outbox ou na fila em memória.
        None quando o outbox não pôde ser lido."""
        from executor import result_store

        pendentes = result_store.job_ids_pendentes()
        if pendentes is None:
            return None
        a_caminho = set(pendentes)
        # A fila em memória também conta: com o outbox desabilitado (disco sem
        # permissão, SQLite corrompido) ela é o único registro de um resultado
        # que ainda não saiu.
        for item in list(getattr(self._results, "_queue", ()) or ()):
            if isinstance(item, dict) and item.get("job_id"):
                a_caminho.add(str(item["job_id"]))
        return a_caminho

    def _enviados_recentes(self) -> list[str]:
        """Resultados enviados há menos de `_ENVIADOS_TTL_S`, do mais recente ao
        mais antigo."""
        vence = time.monotonic() - _ENVIADOS_TTL_S
        for job_id in [j for j, quando in self._enviados.items() if quando < vence]:
            del self._enviados[job_id]
        return list(reversed(self._enviados))

    def _resultados_a_caminho(self) -> set[str] | None:
        """Jobs que TERMINARAM aqui e cujo resultado o servidor pode ainda não
        ter processado. None quando o outbox não pôde ser lido — aí não dá para
        afirmar que um job NÃO terminou aqui."""
        pendentes = self._resultados_pendentes()
        if pendentes is None:
            return None
        return pendentes | set(self._enviados_recentes())

    def _montar_inventario(self) -> dict:
        ativos = self._queue.job_ids_ativos() if self._queue is not None else []
        pendentes = self._resultados_pendentes()
        # Outbox ilegível: o inventário sai marcado `truncado` — o servidor
        # promove e para zumbis, mas não fecha nada por ausência (uma lista vazia
        # afirmaria "nada pendente"). Não mandar nada deixaria a marca de
        # inventário vencer, e a varredura trataria este executor como antigo.
        truncado = pendentes is None
        pendentes = sorted((pendentes or set()) - set(ativos))
        truncado = truncado or len(ativos) + len(pendentes) > _INVENTARIO_MAX
        resultados = pendentes[:max(0, _INVENTARIO_MAX - len(ativos))]
        # Os enviados há pouco só ocupam o espaço que sobra, mais recentes
        # primeiro, e não marcam `truncado`: num executor movimentado eles
        # desligariam a reconciliação dele para sempre. O que ficar de fora já
        # está protegido pela chave de resultado do servidor.
        vaga = _INVENTARIO_MAX - len(ativos) - len(resultados)
        if vaga > 0:
            ja = set(ativos) | set(resultados)
            resultados += [j for j in self._enviados_recentes() if j not in ja][:vaga]
        return {
            "type":       "inventario",
            "ativos":     ativos[:_INVENTARIO_MAX],
            "resultados": resultados,
            "truncado":   truncado,
        }

    async def _encerrar_cancelamento_desconhecido(self, job_id: str) -> str:
        """Cancelamento de um job que não está nesta instância.

        Antes o executor respondia "unknown" só no log e ficava em silêncio: o run
        seguia "Em andamento" no servidor para sempre, e cancelar não servia
        para limpá-lo. Agora ele devolve um resultado 'cancelled' — o servidor
        fecha o run, a menos que ele já seja terminal — e deixa uma lápide para
        descartar o job se ele chegar atrasado.

        Com o resultado a caminho (outbox, fila em memória ou enviado há pouco)
        o job TERMINOU aqui: o resultado verdadeiro está chegando, e um
        'cancelled' por cima dele seria mentira — e, se o consumer do servidor
        ainda não o tivesse gravado, podia até vencê-lo. Com o outbox ilegível
        não dá para saber: não responde nada, e o inventário resolve depois.
        """
        a_caminho = self._resultados_a_caminho()
        if a_caminho is None:
            return "outbox_ilegivel"
        if job_id in a_caminho:
            return "resultado_pendente"
        await self._queue.encerrar_desconhecido(job_id, _MOTIVO_CANCELAMENTO_DESCONHECIDO)
        return "encerrado"

    def _montar_capacity(self) -> dict:
        """Payload de capacity, com o pool de threads levado em conta.

        `get_capacity()` conta JOBS. Isso deixou de descrever o executor desde
        que todo no passou a rodar no pool de threads: um PythonScript com laco
        infinito estoura o timeout do no, devolve o slot do job e deixa a thread
        viva para sempre (`asyncio.to_thread` nao cancela). Poucas execucoes
        assim ocupam o pool inteiro; dai em diante queued/running mostram um
        executor ocioso enquanto NENHUM no consegue rodar, e o servidor continua
        despachando jobs que morrem pendurados em "running" ate virarem orfaos.

        Quando o pool esta saturado anunciamos saturacao pelo mesmo meio que a
        drenagem usa (queued = teto da fila + teto de concorrencia): o
        despacho do servidor nos poe por ultimo (grupo dos cheios) e o
        `is_full` recusa o envio, que entao cai no proximo candidato em vez de
        falhar o run.
        """
        cap = {**self._queue.get_capacity(), **_get_dynamic_metrics()}
        if not self._pool_saturado():
            return cap
        return {
            **cap,
            "queued": cap.get("max_queue", 0) + cap.get("max_concurrent", 0),
        }

    def _pool_saturado(self) -> bool:
        """True quando o pool dos nos esta cheio E com trabalho esperando.

        Exige `_POOL_SATURADO_TICKS` amostras CONSECUTIVAS: um pico normal (N
        nos despachados no mesmo instante) satura o pool por milissegundos, e
        anunciar executor cheio por causa disso tiraria a maquina do ranking a
        toa. Threads orfas nao se resolvem sozinhas — a condicao persiste.
        """
        pool = self._thread_pool
        if pool is None:
            return False
        try:
            # Atributos privados de proposito: o ThreadPoolExecutor nao expoe
            # ocupacao publicamente e a alternativa seria embrulhar cada submit.
            # Qualquer surpresa cai no except e vira "nao saturado", que e o
            # comportamento anterior.
            cheio = len(pool._threads) >= pool._max_workers and pool._work_queue.qsize() > 0
        except Exception:
            return False
        if not cheio:
            self._pool_saturado_seguidas = 0
            return False
        self._pool_saturado_seguidas += 1
        if self._pool_saturado_seguidas == _POOL_SATURADO_TICKS:
            logger.error(
                "Pool de threads dos nos saturado (%d workers ocupados, %d tarefa(s) na "
                "espera) — anunciando capacidade zero. Suspeite de no travado "
                "(PythonScript em laco infinito nao e cancelavel pelo timeout).",
                pool._max_workers, pool._work_queue.qsize(),
            )
        return self._pool_saturado_seguidas >= _POOL_SATURADO_TICKS

