# app/core/agent_connections.py
"""
Registro global de conexões WebSocket ativas de executores.

ExecutorConnectionRegistry mantém dois planos de estado:
  - Em memória (por worker): mapa executor_id → ExecutorConnection com o WebSocket real.
    Usado exclusivamente para envio de jobs e leitura de capacity/connected_at.
  - Redis (compartilhado): chave executor:presence:{id} com TTL de 120s.
    Usado para determinar se o executor está online — funciona corretamente com
    múltiplos workers uvicorn (--workers N), pois é um estado global.
    Ao lado dela vive executor:conn_owner:{id}, com o token da conexão que detém
    a POSSE global do executor. Duas conexões com o mesmo executor_id em workers
    diferentes fariam o job ser executado duas vezes (o relay é PUBLISH, ou
    seja, broadcast); e o unregister de uma delas apagava a presença da outra.
    Com o owner: quem conecta por último assume, o perdedor fecha o seu socket
    e a remoção de presença é por CAS.

Relay via Redis pub/sub:
  Quando o HTTP request que despacha um job cai em um worker diferente do que
  tem o WebSocket, o job é publicado no canal 'executor:job_relay:{executor_id}'.
  O worker que tem o WS subscreve esse canal e encaminha o job ao executor.

Renovação de TTL: ocorre a cada heartbeat/capacity recebido (~30s).
O TTL de 120s serve de segurança para workers que criem sem chamar unregister().
"""
import asyncio
import collections
import hashlib
import hmac
import json
from flow.utils.backoff import com_jitter
from app.core.utils.logger import get_logger
import os
import time
import uuid
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as _aioredis
from redis.exceptions import TimeoutError as _RedisTimeoutError
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.config import REDIS_URL

logger = get_logger(__name__)

# TTL da chave de presença no Redis (segundos).
# Deve ser > HEARTBEAT_TIMEOUT do servidor (90s) para evitar falsos negativos.
_PRESENCE_TTL = 120

# Canal pub/sub para relay de jobs entre workers
_RELAY_CHANNEL_PREFIX = "executor:job_relay:"

# Cache local (TTL curto) para respostas de is_online — evita round-trip Redis
# em endpoints que listam todos os executores (GET /executores, list_agents).
_PRESENCE_CACHE_TTL = 5.0  # segundos

# Intervalo mínimo entre dois EVAL de renovação de presença da MESMA conexão.
# O executor manda capacity a cada 10s e heartbeat a cada 30s: sem throttle eram
# ~14 EVAL/min/executor (com 200 executores, ~47 EVAL/s de puro "ainda estou
# vivo") para manter uma chave cujo TTL é de 120s. Renovando a cada TTL/4 a
# margem continua enorme e a carga de fundo cai ~8x. A detecção de takeover por
# este caminho passa a demorar até 30s, mas ela é só a rede de segurança — o
# marker `__internal__.takeover` publicado no relay fecha o duplicado na hora.
#
# TTL/4 (e não TTL/3) de propósito: com TTL/3 havia UMA renovação de folga, então
# uma única renovação perdida já encostava no vencimento da chave. Com TTL/4
# sobram três tentativas antes de a presença sumir — e presença ausente com o WS
# vivo faz o `orphan_runs_watchdog` matar runs que estão executando.
_PRESENCE_RENEW_INTERVAL = _PRESENCE_TTL / 4

# Espera antes de RETENTAR uma renovação que não pôde ser feita (Redis fora).
# Sem isto, uma falha de Redis avançava o relógio do throttle como se a chave
# tivesse sido renovada e a próxima tentativa só viria um intervalo inteiro
# depois — um blip de ~45s bastava para a chave expirar com o executor vivo.
_PRESENCE_RENEW_RETRY_INTERVAL = 5.0


def _relay_secret() -> bytes:
    """Segredo HMAC para autenticar mensagens do relay entre workers.

    Reusa APP_SECRET (já obrigatório via config) — compartilhado por todos os
    workers uvicorn mas NÃO pelo Redis. Mesmo se o Redis for comprometido ou
    um container hostil conseguir publicar no canal, as mensagens sem HMAC
    válido são descartadas pelo listener.
    """
    from app.core.config import APP_SECRET
    return APP_SECRET.encode() if isinstance(APP_SECRET, str) else APP_SECRET


# ── Envelope assinado do relay ────────────────────────────────────────────────
# O HMAC cobria SÓ o payload cru — sem canal, destinatário, nonce ou timestamp.
# Consequência: um envelope capturado valia PARA SEMPRE e em QUALQUER canal.
# Bastava gravar um `control/revoked` legítimo e republicá-lo no canal de cada
# executor para derrubar a frota inteira. Agora o material assinado inclui o
# propósito (audience), o executor de destino, um nonce e o timestamp; o
# consumidor recusa envelope fora da janela de frescor ou com nonce já visto.
_AUDIENCE_RELAY = "relay"
_AUDIENCE_DRIVE = "drive_events"

# Curinga de destinatário. Só o fan-out de drive events usa: `emit_drive_event`
# assina UM envelope e publica para os N executores do workspace. O relay
# SEMPRE carrega o executor_id concreto — é essa amarra que impede reaproveitar
# o control message de um executor no canal de outro.
_ANY_EXECUTOR = "*"

# Janela de frescor do envelope. Produtor e consumidor são processos do mesmo
# host/stack, então relógio de parede é comparável entre eles.
_RELAY_FRESHNESS_WINDOW = 60.0
_RELAY_NONCE_TTL = 2 * _RELAY_FRESHNESS_WINDOW
_RELAY_NONCE_MAX = 20_000

# "nonce|destinatário" já consumidos → deadline monotonic. Cache EM PROCESSO de
# propósito: o adversário do modelo de ameaça é justamente quem fala com o
# Redis, então um seen-set lá seria apagável por ele. Cada worker só precisa
# deduplicar o que ELE recebe.
#
# O TTL é FIXO, então a ordem de inserção do dict é a ordem de vencimento — é o
# que permite purgar por prefixo em O(expirados) lá embaixo.
_seen_relay_nonces: dict[str, float] = {}

# Contador de nonces AINDA VÁLIDOS descartados por saturação do cache. Enquanto
# durar a saturação o anti-replay do relay está desligado de fato para essas
# entradas; o log é agregado para não virar um ERROR por envelope recebido.
_relay_nonce_evictions: dict[str, float] = {"total": 0.0, "since_log": 0.0, "last_log": 0.0}
_RELAY_NONCE_EVICTION_LOG_EVERY = 10.0  # segundos


def _relay_signing_material(
    *, payload: str, audience: str, executor_id: str, nonce: str, ts: str,
) -> bytes:
    """Serializa os campos assinados com prefixo de comprimento.

    O prefixo elimina ambiguidade de concatenação: sem ele, deslocar caracteres
    entre `audience` e `executor_id` produziria o mesmo material assinado.
    """
    parts = (payload, audience, executor_id, nonce, ts)
    return b"".join(f"{len(p)}:{p}".encode() for p in parts)


def _relay_mac(**fields: str) -> str:
    """HMAC-SHA256 hex do material assinado, usando APP_SECRET."""
    return hmac.new(
        _relay_secret(), _relay_signing_material(**fields), hashlib.sha256,
    ).hexdigest()


def _seal_envelope(payload: str, *, audience: str, executor_id: str) -> str:
    nonce = uuid.uuid4().hex
    ts = f"{time.time():.3f}"
    mac = _relay_mac(
        payload=payload, audience=audience, executor_id=executor_id,
        nonce=nonce, ts=ts,
    )
    return json.dumps({
        "payload":     payload,
        "aud":         audience,
        "executor_id": executor_id,
        "nonce":       nonce,
        "ts":          ts,
        "hmac":        mac,
    })


def build_signed_envelope(payload: str) -> str:
    """Envelope assinado para o canal de DRIVE EVENTS (fan-out).

    `emit_drive_event` assina uma vez e publica para todos os executores do
    workspace, então este envelope não pode se amarrar a um executor concreto —
    mas continua amarrado ao propósito 'drive_events', ao nonce e ao timestamp.
    Consequência aceita: dentro da janela de frescor um envelope de drive pode
    ser reapresentado a OUTRO executor. O listener de drive só aceita
    {"type":"drive_event"}, então o estrago se limita a uma notificação de
    arquivo fora de ordem — nada de control/job.
    """
    return _seal_envelope(payload, audience=_AUDIENCE_DRIVE, executor_id=_ANY_EXECUTOR)


def build_relay_envelope(payload: str, *, executor_id: str) -> str:
    """Envelope assinado para o relay de job/control de UM executor.

    Todo canal pub/sub que termina em `ws.send_text()` para o executor DEVE usar
    um envelope assinado — o listener valida antes de encaminhar. Quem não tiver
    APP_SECRET (container hostil, Redis comprometido) não consegue injetar
    mensagens no WebSocket do executor.
    """
    return _seal_envelope(payload, audience=_AUDIENCE_RELAY, executor_id=executor_id)


def _nonce_already_seen(nonce: str, executor_id: str) -> bool:
    """Registra o nonce para este destinatário; True se já tinha sido consumido."""
    now = time.monotonic()
    key = f"{nonce}|{executor_id}"
    deadline = _seen_relay_nonces.get(key)
    if deadline is not None and deadline > now:
        return True
    # PERF: TTL fixo ⇒ ordem de inserção == ordem de vencimento, logo os
    # expirados são sempre um PREFIXO. Purgar pelo início até achar o primeiro
    # vivo custa O(expirados). A versão anterior varria as 20k entradas e ainda
    # fazia `sorted()` sobre elas — no caminho quente de TODO envelope recebido.
    while _seen_relay_nonces:
        oldest_key, oldest_deadline = next(iter(_seen_relay_nonces.items()))
        if oldest_deadline > now:
            break
        _seen_relay_nonces.pop(oldest_key, None)

    # SEG: se o teto for atingido só com entradas AINDA VÁLIDAS, evictar reabre
    # a janela de replay do envelope correspondente. Descartar em SILÊNCIO — como
    # era feito antes — deixava o operador sem saber que o anti-replay do relay
    # estava desligado de fato. O cache irmão do executor
    # (executor/job_validator.py) grita nessa mesma situação; aqui o grito é
    # agregado porque, saturado, isso acontece a cada envelope.
    if len(_seen_relay_nonces) >= _RELAY_NONCE_MAX:
        evicted_key, evicted_deadline = next(iter(_seen_relay_nonces.items()))
        _seen_relay_nonces.pop(evicted_key, None)
        _relay_nonce_evictions["total"] += 1
        _relay_nonce_evictions["since_log"] += 1
        if (now - _relay_nonce_evictions["last_log"]) >= _RELAY_NONCE_EVICTION_LOG_EVERY:
            logger.error(
                "Cache anti-replay do relay cheio (%d entradas, TTL %.0fs): %d nonce(s) "
                "AINDA VÁLIDO(S) descartado(s) nos últimos %.0fs (%d no total desta "
                "instância; o mais recente ainda tinha %.1fs de vida). Enquanto durar a "
                "saturação, um replay dos envelopes correspondentes não seria detectado.",
                _RELAY_NONCE_MAX, _RELAY_NONCE_TTL,
                int(_relay_nonce_evictions["since_log"]), _RELAY_NONCE_EVICTION_LOG_EVERY,
                int(_relay_nonce_evictions["total"]),
                max(0.0, evicted_deadline - now),
            )
            _relay_nonce_evictions["since_log"] = 0.0
            _relay_nonce_evictions["last_log"] = now

    _seen_relay_nonces[key] = now + _RELAY_NONCE_TTL
    return False


def open_signed_envelope(
    raw: str, *, channel_label: str, executor_id: str, audience: str,
) -> str | None:
    """Valida o envelope assinado e devolve o payload, ou None se inválido.

    Além do HMAC, exige: propósito igual ao esperado, destinatário igual ao
    executor deste canal (ou curinga, só em drive events), timestamp dentro de
    `_RELAY_FRESHNESS_WINDOW` e nonce inédito.
    """
    try:
        envelope = json.loads(raw)
        payload = envelope.get("payload")
        mac     = envelope.get("hmac")
        aud     = envelope.get("aud")
        target  = envelope.get("executor_id")
        nonce   = envelope.get("nonce")
        ts      = envelope.get("ts")
        if not all(isinstance(v, str) for v in (payload, mac, aud, target, nonce, ts)):
            raise ValueError("envelope com campo ausente ou de tipo inesperado")
    except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        logger.warning(
            "%s: envelope malformado no canal do executor '%s': %s",
            channel_label, executor_id, exc,
        )
        return None

    # HMAC primeiro: aud/target/nonce/ts fazem parte do material assinado, logo
    # qualquer adulteração deles é detectada aqui antes de serem usados.
    expected = _relay_mac(
        payload=payload, audience=aud, executor_id=target, nonce=nonce, ts=ts,
    )
    if not hmac.compare_digest(expected, mac):
        logger.warning(
            "%s: mensagem com HMAC inválido no canal do executor '%s' — descartada.",
            channel_label, executor_id,
        )
        return None

    if aud != audience:
        logger.warning(
            "%s: envelope assinado para propósito '%s' apresentado no canal '%s' "
            "do executor '%s' — descartado.",
            channel_label, aud, audience, executor_id,
        )
        return None

    if target != executor_id and not (audience == _AUDIENCE_DRIVE and target == _ANY_EXECUTOR):
        logger.warning(
            "%s: envelope destinado a '%s' apresentado no canal do executor '%s' "
            "— descartado (replay cross-executor).",
            channel_label, target, executor_id,
        )
        return None

    try:
        age = abs(time.time() - float(ts))
    except ValueError:
        logger.warning(
            "%s: envelope com timestamp ilegível no canal do executor '%s'.",
            channel_label, executor_id,
        )
        return None
    if age > _RELAY_FRESHNESS_WINDOW:
        logger.warning(
            "%s: envelope fora da janela de frescor (%.1fs > %.0fs) no canal do "
            "executor '%s' — descartado (replay).",
            channel_label, age, _RELAY_FRESHNESS_WINDOW, executor_id,
        )
        return None

    if _nonce_already_seen(nonce, executor_id):
        logger.warning(
            "%s: nonce repetido no canal do executor '%s' — descartado (replay).",
            channel_label, executor_id,
        )
        return None

    return payload


def _presence_key(executor_id: str) -> str:
    return f"executor:presence:{executor_id}"


def _conn_owner_key(executor_id: str) -> str:
    """Chave do DONO GLOBAL da conexão WebSocket de um executor.

    O de-dup de `register()` é por processo, mas o deploy roda `--workers 4`:
    nada impedia dois workers de terem, cada um, um WS vivo para o mesmo
    executor_id. Como o relay usa PUBLISH (broadcast), o job era entregue duas
    vezes → INSERT e e-mail duplicados. Esta chave carrega o token da conexão
    que detém a posse; quem conecta por último assume e o perdedor fecha o seu
    socket.
    """
    return f"executor:conn_owner:{executor_id}"


def _relay_channel(executor_id: str) -> str:
    return f"{_RELAY_CHANNEL_PREFIX}{executor_id}"


def _drive_channel(executor_id: str) -> str:
    return f"executor:{executor_id}:drive_events"


# Renova presence + owner APENAS se o token ainda for o dono (ou se a posse
# expirou e ninguém assumiu). Retorna 1 se renovou, 0 se outro worker assumiu.
_LUA_RENEW_PRESENCE = """
local owner = redis.call('GET', KEYS[2])
if owner and owner ~= ARGV[1] then
  return 0
end
redis.call('SET', KEYS[2], ARGV[1], 'EX', tonumber(ARGV[2]))
redis.call('SET', KEYS[1], '1', 'EX', tonumber(ARGV[2]))
return 1
"""

# Libera presence + owner por CAS. O DELETE incondicional anterior era um bug de
# disponibilidade grave: o worker cuja conexão MORREU apagava a presença global
# de uma sessão que já pertencia a outro worker → "503 Nenhum executor
# disponível" com o executor online e ocioso.
_LUA_RELEASE_PRESENCE = """
local owner = redis.call('GET', KEYS[2])
if owner and owner ~= ARGV[1] then
  return 0
end
redis.call('DEL', KEYS[1])
redis.call('DEL', KEYS[2])
return 1
"""


# ── Prazo de envio pelo WebSocket do executor ────────────────────────────────
# Sem prazo, `send_text` para uma conexão parada (executor congelado, rede
# meio-aberta) esperava o drain até o ping timeout da API (`--ws-ping-timeout
# 600`): o despacho — e com ele o agendador daquele worker, que processa um
# agendamento por vez — ficava até ~10 min preso num único envio, com o run em
# "Na fila". O prazo cresce com o tamanho do frame para não cortar um envelope
# grande numa rede lenta: 30 s + 1 s a cada 512 KB (16 MB, o teto do frame,
# dá ~62 s).
#
# Estourar o prazo NÃO é recusa nem conexão morta. O frame inteiro já está no
# buffer do transporte (o websockets o escreve antes do drain; o prazo só
# cancela a espera) e continua saindo em segundo plano. Por isso:
#   - não se derruba a conexão: um executor vivo com link lento perdia a
#     presença, o watchdog fechava todos os runs dele como órfãos e, na volta,
#     o inventário mandava cancelar os jobs que ainda rodavam;
#   - o job conta como entregue sem confirmação (ACK pendente), sem failover —
#     mandá-lo a outro executor faria os dois rodarem o mesmo job. Se ele não
#     chegar, o inventário e a varredura dos 'pending' fecham o run;
#   - enquanto a escrita estiver atrasada (além do próprio prazo), a conexão
#     fica fora do despacho — no worker que a segura e, por uma marca no Redis,
#     nos que a alcançam pelo relay. Uma conexão morta de verdade cai pelo
#     timeout do heartbeat e pela presença.
_PRAZO_DE_ENVIO_BASE_S = 30.0
_PRAZO_DE_ENVIO_BYTES_POR_S = 512 * 1024
# A marca de parada no Redis vence sozinha se ninguém a renovar (worker morto
# no meio de uma escrita atrasada); o escritor a renova enquanto o atraso durar.
_TTL_DA_PARADA_S = 60
_RENOVA_PARADA_S = 30.0


def _prazo_de_envio(n_bytes: int) -> float:
    return _PRAZO_DE_ENVIO_BASE_S + n_bytes / _PRAZO_DE_ENVIO_BYTES_POR_S


def _chave_de_parada(executor_id: str) -> str:
    return f"executor:parada:{executor_id}"


async def _redis_parada(executor_id: str) -> bool:
    """O worker que segura o socket deste executor tem uma escrita atrasada
    (ver `_Saida._sinalizar_atraso`). Redis fora: False — a marca é otimização,
    não trava de segurança."""
    try:
        rc = await _get_redis()
        return bool(await rc.exists(_chave_de_parada(executor_id)))
    except Exception:
        return False


# ── Saída do WebSocket do executor: uma fila, um escritor ────────────────────
# O `--ws websockets` do uvicorn (fixado no compose) escreve o frame INTEIRO no
# transporte e só então espera o drain — e o drain não aceita dois esperando:
# com o socket em backpressure (um envelope de MBs num link lento), um segundo
# escritor levantava AssertionError com o frame dele JÁ no buffer, e quem
# chamava tratava como falha (failover: o job rodava em dois executores; ou
# unregister: presença apagada de um executor vivo).
#
# Por isso cada socket tem uma `_Saida`: uma fila e UMA tarefa que escreve, em
# ordem, sem prazo nenhum sobre o drain. Quem manda espera o próprio desfecho
# com um prazo que conta o que está na frente (o envio em curso e a fila):
#   ENVIADO   saiu inteiro;
#   ESCOANDO  a escrita começou (o frame está no buffer) e passou do prazo —
#             segue saindo; para quem mandou, entregue sem confirmação;
#   OCUPADO   o prazo acabou ainda na fila: quem mandou desiste e NADA é escrito;
#   FECHANDO  o socket está sendo fechado: nada é escrito.
# Erro do socket (conexão morta) sobe para quem espera. Quem espera nunca
# recebe o CancelledError do escritor: o desfecho é um Future próprio.
ENVIADO = "enviado"
ESCOANDO = "escoando"
OCUPADO = "ocupado"
FECHANDO = "fechando"

# ws → _Saida. Sai daqui no fim do handler da conexão (ver `encerrar_saida`).
_saidas: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
# Referências fortes a tarefas soltas (asyncio só guarda weakrefs).
_tarefas_soltas: set = set()


def _em_segundo_plano(coro, nome: str) -> "asyncio.Task":
    tarefa = asyncio.create_task(coro, name=nome)
    _tarefas_soltas.add(tarefa)

    def _fim(t: "asyncio.Task") -> None:
        _tarefas_soltas.discard(t)
        if not t.cancelled() and t.exception() is not None:
            logger.debug("Tarefa '%s' terminou com erro: %r", nome, t.exception())

    tarefa.add_done_callback(_fim)
    return tarefa


async def _redis_marcar_parada(executor_id: str) -> None:
    try:
        await (await _get_redis()).setex(_chave_de_parada(executor_id), _TTL_DA_PARADA_S, "1")
    except Exception as exc:
        logger.debug("Marca de parada de '%s' não gravada: %s", executor_id, exc)


async def _redis_limpar_parada(executor_id: str) -> None:
    try:
        await (await _get_redis()).delete(_chave_de_parada(executor_id))
    except Exception as exc:
        logger.debug("Marca de parada de '%s' não limpa: %s", executor_id, exc)


@dataclass(eq=False)
class _Envio:
    texto: str
    prazo: float
    feito: "asyncio.Future"
    estado: str = "na_fila"   # na_fila → escrevendo → fim | desistiu
    inicio: float = 0.0       # monotonic, quando a escrita começou


class _Saida:
    """Fila de saída de UM WebSocket de executor, com um único escritor."""

    def __init__(self, ws, executor_id: str | None = None):
        self.ws = ws
        self.executor_id = executor_id
        self.fila: "collections.deque[_Envio]" = collections.deque()
        self.atual: _Envio | None = None
        self.fechando = False
        # Fechada porque outra sessão assumiu o executor (takeover, posse
        # perdida): o que chegar agora é entregue por ela — ver
        # `_conexao_para_envio` e `_encaminhar`.
        self.substituida = False
        # Fechada pelo AVISO de takeover que este listener recebeu: o que
        # estava na fila foi publicado antes de a sessão nova subscrever (ver
        # `register`), então só existia aqui — ver `_fechar_nao_entregue`.
        self.avisada = False
        self.erro: BaseException | None = None
        self._tem_item = asyncio.Event()
        self._alarme: "asyncio.TimerHandle | None" = None
        self._marcou_parada = False
        self.escritor = asyncio.create_task(self._escrever(), name="saida-executor")

    # ── quem manda ────────────────────────────────────────────────────────────
    def enfileirar(self, texto: str) -> "_Envio | str":
        """Põe na fila e devolve o envio — ou FECHANDO. Síncrono de propósito:
        quem enfileira em sequência (o listener do relay) preserva a ordem."""
        if self.fechando:
            return FECHANDO
        if self.erro is not None:
            raise self.erro
        feito = asyncio.get_running_loop().create_future()
        # Um erro entregue a quem já desistiu não vira "exception never retrieved".
        feito.add_done_callback(lambda f: f.cancelled() or f.exception())
        envio = _Envio(texto=texto, prazo=_prazo_de_envio(len(texto)), feito=feito)
        self.fila.append(envio)
        self._tem_item.set()
        return envio

    def _espera(self, envio: _Envio) -> float:
        """O prazo próprio mais o que está na frente: o que falta do prazo do
        envio em curso e os BYTES da fila antes dele, no piso de projeto
        (512 KB/s). A base de 30 s entra uma vez só: somada por mensagem, uma
        fila de 40 eventos pequenos prendia quem manda por 20 minutos."""
        espera = envio.prazo
        atual = self.atual
        if atual is not None:
            espera += max(0.0, atual.prazo - (time.monotonic() - atual.inicio))
        for outro in self.fila:
            if outro is envio:
                break
            if outro.estado == "na_fila":
                espera += len(outro.texto) / _PRAZO_DE_ENVIO_BYTES_POR_S
        return espera

    async def aguardar(self, envio: _Envio) -> str:
        await asyncio.wait({envio.feito}, timeout=self._espera(envio))
        if envio.feito.done():
            return envio.feito.result()   # ENVIADO, ESCOANDO, FECHANDO — ou o erro do socket
        if envio.estado == "na_fila":
            envio.estado = "desistiu"     # o escritor pula: nada é escrito
            return OCUPADO
        return ESCOANDO                   # a escrita começou: o frame está no buffer

    async def enviar(self, texto: str) -> str:
        if self.atrasada() and not self.fechando:
            # O link está abaixo do piso: na fila, a mensagem esperaria atrás do
            # frame atrasado o prazo inteiro e sairia OCUPADO do mesmo jeito.
            return OCUPADO
        envio = self.enfileirar(texto)
        if isinstance(envio, str):
            return envio
        return await self.aguardar(envio)

    def atrasada(self) -> bool:
        """A escrita em curso passou do próprio prazo (link abaixo do piso)."""
        atual = self.atual
        return atual is not None and time.monotonic() - atual.inicio > atual.prazo

    def encerrar(self, *, substituida: bool = False, avisada: bool = False) -> None:
        """Nenhum envio novo; a ESPERA do escritor é cancelada — o que ele já pôs
        no buffer segue saindo antes do frame de close. A fila é resolvida aqui
        mesmo: um escritor cancelado antes do primeiro passo nunca chega ao
        próprio `except`, e quem esperava ficaria o prazo inteiro por um OCUPADO."""
        self.fechando = True
        self.substituida = self.substituida or substituida or avisada
        self.avisada = self.avisada or avisada
        if not self.escritor.done():
            self.escritor.cancel()
        self._resolver_fila(FECHANDO)

    # ── o escritor ────────────────────────────────────────────────────────────
    async def _escrever(self) -> None:
        envio: _Envio | None = None
        try:
            while True:
                while not self.fila:
                    self._tem_item.clear()
                    await self._tem_item.wait()
                envio = self.fila.popleft()
                if envio.estado != "na_fila":     # quem mandou desistiu
                    envio = None
                    continue
                envio.estado = "escrevendo"
                envio.inicio = time.monotonic()
                self.atual = envio
                self._armar_alarme(envio)
                try:
                    await self.ws.send_text(envio.texto)
                finally:
                    self._desarmar_alarme()
                    self.atual = None
                envio.estado = "fim"
                if not envio.feito.done():
                    envio.feito.set_result(ENVIADO)
                envio = None
        except asyncio.CancelledError:
            # Fechamento: o que estava sendo escrito já está no buffer.
            if envio is not None and envio.estado == "escrevendo" and not envio.feito.done():
                envio.feito.set_result(ESCOANDO)
            self._resolver_fila(FECHANDO)
            raise
        except Exception as exc:
            # Socket morto: quem esperava recebe o erro, e os próximos também.
            self.erro = exc
            if envio is not None and not envio.feito.done():
                envio.feito.set_exception(exc)
            self._resolver_fila(exc)

    def _resolver_fila(self, desfecho) -> None:
        while self.fila:
            envio = self.fila.popleft()
            if envio.feito.done():
                continue
            if isinstance(desfecho, BaseException):
                envio.feito.set_exception(desfecho)
            else:
                envio.feito.set_result(desfecho)

    # ── a marca de parada ─────────────────────────────────────────────────────
    # Liga quando a escrita em curso passa do próprio prazo e desliga quando ela
    # termina: os outros workers param de relayar SÓ enquanto o link está de
    # fato abaixo do piso — nem um minuto fixo depois de uma transferência
    # grande e saudável.
    def _armar_alarme(self, envio: _Envio) -> None:
        if self.executor_id:
            self._alarme = asyncio.get_running_loop().call_later(envio.prazo, self._sinalizar_atraso)

    def _sinalizar_atraso(self) -> None:
        self._marcou_parada = True
        _em_segundo_plano(_redis_marcar_parada(self.executor_id), "marca-parada")
        self._alarme = asyncio.get_running_loop().call_later(_RENOVA_PARADA_S, self._sinalizar_atraso)

    def _desarmar_alarme(self) -> None:
        if self._alarme is not None:
            self._alarme.cancel()
            self._alarme = None
        if self._marcou_parada:
            self._marcou_parada = False
            _em_segundo_plano(_redis_limpar_parada(self.executor_id), "limpa-parada")


def _ws_aberto(ws) -> bool:
    """O app ainda não pediu o close e o executor não se desconectou."""
    return (
        getattr(ws, "application_state", None) != WebSocketState.DISCONNECTED
        and getattr(ws, "client_state", None) != WebSocketState.DISCONNECTED
    )


def _saida_de(ws, executor_id: str | None = None) -> _Saida:
    saida = _saidas.get(ws)
    if saida is None:
        saida = _saidas[ws] = _Saida(ws, executor_id)
    elif executor_id and not saida.executor_id:
        saida.executor_id = executor_id
    return saida


async def enviar_ao_executor(ws, texto: str, executor_id: str | None = None) -> str:
    """Envia `texto` pela saída do socket — ver `_Saida`."""
    return await _saida_de(ws, executor_id).enviar(texto)


def enfileirar_ao_executor(ws, texto: str, executor_id: str | None = None) -> bool:
    """Põe `texto` na saída do socket e segue, sem esperar a vez (para o loop de
    recebimento, que não pode ficar preso atrás de um frame lento). Com o envio
    em curso atrasado, descarta e devolve False: só engrossaria a fila."""
    saida = _saida_de(ws, executor_id)
    if saida.atrasada():
        return False
    return not isinstance(saida.enfileirar(texto), str)


def encerrar_envios(ws) -> None:
    """O handler da conexão está terminando: nada mais sai por este socket. A
    saída fica no mapa — quem mandar recebe FECHANDO e o relay dá o job por não
    entregue, em vez de bater no socket morto — até `encerrar_saida`, no fim do
    mesmo handler."""
    _saida_de(ws).encerrar()


def encerrar_saida(ws) -> None:
    """Fim da vida do socket (o handler da conexão terminou): a saída dele sai
    do mapa. Ela segura o ws, então o WeakKeyDictionary sozinho não a soltaria."""
    saida = _saidas.pop(ws, None)
    if saida is not None:
        saida.encerrar()


async def _fechar_depois_do_escritor(ws, saida: "_Saida | None", code: int, reason: str) -> None:
    if saida is not None:
        await asyncio.gather(saida.escritor, return_exceptions=True)
    await ws.close(code=code, reason=reason)


async def fechar_ws_do_executor(
    ws, code: int = 1000, reason: str = "", *, substituida: bool = False, avisada: bool = False,
) -> None:
    """Fecha o WebSocket de um executor. Todo close de socket de executor passa
    por aqui.

    Com uma escrita escoando, o drain dela fica pendente — e com ele pendente o
    close do websockets legacy levantava AssertionError na hora, sem nunca chegar
    ao close_timeout → abort: o socket de um executor congelado ficava vivo com
    até 16 MB no buffer. Por isso a saída é encerrada primeiro (a espera do
    escritor é cancelada; o que ele já escreveu segue antes do frame de close).
    O close roda numa tarefa própria: um `wait_for` de quem chamou não o
    abandona no meio (ele chega ao abort mesmo que quem pediu desista de esperar).

    `substituida`: outra sessão assumiu o executor — o que vier para ele segue
    pelo relay até a sessão nova (ver `_conexao_para_envio`). `avisada`: foi o
    aviso de takeover que chegou (ver `_Saida.avisada`).
    """
    saida = _marcar_fechando(ws, substituida=substituida, avisada=avisada)
    fechamento = _em_segundo_plano(_fechar_depois_do_escritor(ws, saida, code, reason), "fecha-ws")
    await asyncio.shield(fechamento)


def _marcar_fechando(ws, *, substituida: bool, avisada: bool = False) -> "_Saida | None":
    """Encerra a saída do socket — criando-a, se nada saiu ainda por ele: quem
    mandar durante o close recebe FECHANDO. Sem ela, o relay criava uma saída
    nova, o escritor batia no socket fechado e o job relayado se perdia calado
    (o erro do socket não fecha o run). Quem a tira do mapa é o fim do handler
    (`encerrar_saida`); num socket já fechado não se cria nada."""
    saida = _saidas.get(ws)
    if saida is None and _ws_aberto(ws):
        saida = _saida_de(ws)
    if saida is not None:
        saida.encerrar(substituida=substituida, avisada=avisada)
    return saida


# ── Tracking de ACKs pendentes (compartilhado entre workers via Redis) ────────
# Cada job em voo vira: executor:pending_ack:{job_id} -> "{executor_id}|{sent_at_unix}"
# com TTL automático. O índice executor:pending_acks:set lista IDs vivos para o
# monitor poder enumerar sem SCAN. O lock garante que só um worker emite o
# warning por ciclo em deploys multi-worker.
_PENDING_ACK_TTL_SECONDS = 600
_PENDING_ACKS_INDEX_KEY = "executor:pending_acks:set"
_ACK_MONITOR_LOCK_KEY = "executor:ack_monitor:lock"


def _pending_ack_key(job_id: str) -> str:
    return f"executor:pending_ack:{job_id}"


# Compara-e-apaga o pending_ack em UM round-trip. Antes eram dois (GET para
# conferir o dono, depois pipeline GETDEL+SREM), com uma janela entre eles em que
# outra sessão podia trocar o valor.
#
# SEG: ARGV[1] é o executor que ENVIOU o ACK; só apagamos se o job tiver sido
# despachado para ele. ARGV[1] vazio é o modo curinga (caller sem vínculo a
# provar) — executor_id nunca é string vazia, então não há como um ACK forjar
# esse modo. Retornos: nil (job desconhecido), {0, dono} (impostor),
# {1, valor} (limpo).
_LUA_CLEAR_PENDING_ACK = """
local raw = redis.call('GET', KEYS[1])
if not raw then
  return nil
end
local sep = string.find(raw, '|', 1, true)
local owner = sep and string.sub(raw, 1, sep - 1) or raw
if ARGV[1] ~= '' and owner ~= ARGV[1] then
  return {0, owner}
end
redis.call('DEL', KEYS[1])
redis.call('SREM', KEYS[2], ARGV[2])
return {1, raw}
"""


# ── Pool Redis singleton ──────────────────────────────────────────────────────
# Reutiliza a mesma conexão em todas as operações do registry. Criar+fechar
# uma conexão a cada setex/exists/delete (como antes) é custoso: heartbeat
# (30s) + capacity (10s) × N executores viram pressão desnecessária em connect.
_redis_singleton: _aioredis.Redis | None = None
_redis_lock = asyncio.Lock()


async def _get_redis() -> _aioredis.Redis:
    """Retorna o cliente Redis singleton do registry.

    Inicialização lazy, thread-safe via Lock. NÃO chamar aclose() no retorno.
    """
    global _redis_singleton
    if _redis_singleton is not None:
        return _redis_singleton
    async with _redis_lock:
        if _redis_singleton is None:
            _redis_singleton = _aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_singleton


async def _reset_redis_singleton() -> None:
    """Invalida o singleton — próximo _get_redis() recria o client.

    Chamado quando uma operação falha com ConnectionError ou erro de protocolo,
    evitando que o singleton fique preso em estado ruim após um blip do Redis.
    """
    global _redis_singleton
    if _redis_singleton is None:
        return
    async with _redis_lock:
        old = _redis_singleton
        _redis_singleton = None
    try:
        await asyncio.wait_for(old.aclose(), timeout=1.0)
    except Exception:
        pass  # aclose em conn já ruim pode falhar; tudo bem


async def _redis_claim_presence(executor_id: str, owner_token: str) -> str | None:
    """Assume a posse global da conexão e marca presença. Devolve o token do
    dono anterior (None se não havia dono, ou em falha de Redis).

    Quem conecta por último vence: o executor só abre um WS novo depois de o
    antigo ter caído do ponto de vista DELE, então a sessão mais recente é a
    boa. O aviso ao worker perdedor sai sempre, com ou sem dono anterior (ver
    `register`): a posse de uma sessão que ainda está fechando pode ter vencido.
    """
    try:
        rc = await _get_redis()
        owner_key = _conn_owner_key(executor_id)
        async with rc.pipeline(transaction=True) as p:
            p.getset(owner_key, owner_token)
            p.expire(owner_key, _PRESENCE_TTL)
            p.setex(_presence_key(executor_id), _PRESENCE_TTL, "1")
            previous, _, _ = await p.execute()
        return previous
    except Exception as exc:
        logger.warning("Redis: falha ao assumir posse do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_renew_presence(executor_id: str, owner_token: str) -> bool | None:
    """Renova presence + owner em TRI-ESTADO.

    True  = renovei, a chave está gravada com TTL cheio.
    False = OUTRO worker é o dono — este WS é o duplicado e deve cair.
    None  = não consegui perguntar (Redis fora).

    O `None` existe porque "renovei" e "não consegui tentar" tinham o mesmo
    retorno: quem chama marcava a renovação como FEITA e só voltava a tentar um
    intervalo inteiro depois, enquanto a chave real seguia envelhecendo até
    expirar com o executor vivo — e presença ausente faz o watchdog de órfãos
    matar runs em execução. Continua fail-open no que importa (o WS não cai por
    blip de Redis): quem trata o None só reagenda a tentativa.
    """
    try:
        rc = await _get_redis()
        kept = await rc.eval(
            _LUA_RENEW_PRESENCE, 2,
            _presence_key(executor_id), _conn_owner_key(executor_id),
            owner_token, str(_PRESENCE_TTL),
        )
        return bool(kept)
    except Exception as exc:
        logger.warning("Redis: falha ao renovar presença do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_release_presence(executor_id: str, owner_token: str) -> bool | None:
    """Remove presença + posse por CAS — só se `owner_token` ainda for o dono.
    Devolve se liberou; False quando a posse já é de outra sessão; None em erro."""
    try:
        rc = await _get_redis()
        released = await rc.eval(
            _LUA_RELEASE_PRESENCE, 2,
            _presence_key(executor_id), _conn_owner_key(executor_id),
            owner_token,
        )
        if not released:
            logger.info(
                "Presença do executor '%s' preservada: a posse já é de outra sessão.",
                executor_id,
            )
        return bool(released)
    except Exception as exc:
        logger.warning("Redis: falha ao remover presença do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_presence_or_unknown(executor_id: str) -> bool | None:
    """Presença no Redis em TRI-ESTADO: True (online), False (offline), None (não sei).

    O `None` existe porque "a consulta falhou" e "o executor sumiu" são fatos
    diferentes com custos opostos. Quem decide DISPATCH pode colapsar os dois em
    offline sem prejuízo (não despachar é o lado seguro) — é o que
    `_redis_check_presence` faz. Já quem decide DESTRUIR estado (falhar runs
    órfãos) não pode: um blip do pool no instante exato da checagem mataria runs
    de 40 minutos que estão vivos e progredindo em outro worker. Esse caller
    trata None como "reavalio depois".
    """
    try:
        rc = await _get_redis()
        exists = await rc.exists(_presence_key(executor_id))
        return bool(exists)
    except Exception as exc:
        logger.warning("Redis: falha ao verificar presença do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_check_presence(executor_id: str) -> bool:
    """Presença como booleano, FAIL-CLOSED: "não sei" vira offline.

    Use apenas onde negar é o lado seguro (dispatch, relay, is_online). Para
    decisões destrutivas use `_redis_presence_or_unknown` e trate o None.
    """
    return (await _redis_presence_or_unknown(executor_id)) is True


# Carência de DISPATCH após uma desconexão limpa (spec §5.1). A presença é
# apagada na hora no `finally` do handler; sem carência, um executor que está
# reconectando (blip de rede, restart) sumia da lista de candidatos e o job ia
# para o próximo — ou falhava, sob terminal `fail`. Dentro desta janela a
# presença ausente vira "não sei" e o candidato é TENTADO: o `send_job` real
# decide (falha rápido se ele não voltou). Mesma ordem de grandeza do grace de
# órfãos do WS router.
_DISPATCH_GRACE_SECONDS = 20.0

# Capacidade no Redis (`executor:capacity:{id}`), para o caminho RELAY do
# `send_job` recusar um executor cheio como o caminho direto faz. Regravada só
# quando muda ou a cada intervalo — o capacity chega a cada ~10s por executor.
_CAPACITY_STORE_INTERVAL = 30.0


def _capacity_key(executor_id: str) -> str:
    return f"executor:capacity:{executor_id}"


def _capacity_is_full(c: dict | None) -> bool:
    """Fila local cheia (back-pressure) — a MESMA conta nos dois caminhos."""
    if not c:
        return False
    return (c.get("queued", 0) + c.get("running", 0)) >= (
        c.get("max_concurrent", 4) + c.get("max_queue", 50)
    )


async def _redis_store_capacity(executor_id: str, capacity: dict) -> None:
    try:
        rc = await _get_redis()
        await rc.set(_capacity_key(executor_id), json.dumps(capacity), ex=_PRESENCE_TTL)
    except Exception as exc:
        logger.warning("Redis: falha ao gravar capacidade do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()


async def _redis_delete_capacity(executor_id: str) -> None:
    """Apaga a capacidade publicada quando o WS cai: sem isto, um executor
    saturado que reconecta em OUTRO worker fica "cheio" para o relay por até
    um TTL — e num workspace isolado de executor único isso é um run falhado."""
    try:
        rc = await _get_redis()
        await rc.delete(_capacity_key(executor_id))
    except Exception as exc:
        logger.warning("Redis: falha ao apagar capacidade do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()


def _capacidade_de(raw) -> dict | None:
    """O valor de `executor:capacity:{id}` como dict; None se ausente ou ilegível."""
    if not raw:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode()
        cap = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return None
    return cap if isinstance(cap, dict) else None


async def _redis_read_capacity(executor_id: str) -> dict | None:
    """Capacidade publicada pelo worker que tem o WS; None = desconhecida."""
    try:
        rc = await _get_redis()
        return _capacidade_de(await rc.get(_capacity_key(executor_id)))
    except Exception as exc:
        logger.warning("Redis: falha ao ler capacidade do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_read_capacities(executor_ids: list[str]) -> dict[str, dict | None]:
    """`_redis_read_capacity` de vários executores numa ida só (MGET)."""
    try:
        rc = await _get_redis()
        valores = await rc.mget(*[_capacity_key(i) for i in executor_ids])
    except Exception as exc:
        logger.warning("Redis: falha ao ler a capacidade de %d executores: %s", len(executor_ids), exc)
        await _reset_redis_singleton()
        return dict.fromkeys(executor_ids)
    return {i: _capacidade_de(v) for i, v in zip(executor_ids, valores)}


# Capacidade padrão reportada antes do primeiro heartbeat de capacidade do executor
_DEFAULT_CAPACITY = {
    "queued": 0,
    "running": 0,
    "max_concurrent": 4,
    "max_queue": 50,
}


@dataclass
class ExecutorConnection:
    executor_id:    str
    websocket:   WebSocket
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executor_version: Optional[str] = None
    executor_ip:    Optional[str] = None
    capacity:    dict = field(default_factory=lambda: dict(_DEFAULT_CAPACITY))
    system_info: Optional[dict] = None
    # Define quando o executor enviou o handshake — mensagens anteriores são
    # rejeitadas. Ver SEG/R3 no WS router.
    handshake_received: bool = False
    # Token único desta conexão. É ele que aparece em `executor:conn_owner:{id}`
    # enquanto esta sessão for a dona — ver `_conn_owner_key`.
    owner_token: str = field(default_factory=lambda: uuid.uuid4().hex)
    # Tetos vindos do registro do Executor no banco (max_concurrent_jobs /
    # max_queue_size). A `capacity` é AUTO-DECLARADA pelo executor: sem clamp,
    # anunciar max_queue=10**9 atraía todos os jobs do pool para ele.
    max_concurrent_limit: int = _DEFAULT_CAPACITY["max_concurrent"]
    max_queue_limit:      int = _DEFAULT_CAPACITY["max_queue"]
    # Memo de autorização run_id → (autorizado, deadline monotonic). Evita um
    # SELECT no Postgres por node_event (o vínculo run→host é imutável depois do
    # dispatch). Vive NA CONEXÃO: nunca cruza executores e some no unregister.
    run_auth_cache: dict[str, tuple[bool, float]] = field(default_factory=dict)
    # Instante (monotonic) da última renovação de presença no Redis. O register
    # já grava a chave com TTL cheio, então a conexão nasce "renovada" — ver
    # `_PRESENCE_RENEW_INTERVAL`.
    last_presence_renew: float = field(default_factory=time.monotonic)
    # Circuit breaker curto de autorização: enquanto valer, o veredito é negado
    # SEM tocar no banco. Ver `_run_belongs_to_agent` no WS router.
    db_auth_cooldown_until: float = 0.0

    # Throttle da publicação de capacidade no Redis (ver _CAPACITY_STORE_INTERVAL).
    last_capacity_store: float = 0.0
    last_capacity_stored: tuple | None = None
    # Instante (monotonic) da última reconciliação pelo inventário do executor.
    # Zero de propósito: a primeira, logo depois da conexão, nunca espera. Ver
    # `_reconciliar_inventario` no WS router.
    ultima_reconciliacao: float = 0.0

    def is_full(self) -> bool:
        """Retorna True se a fila local do executor está cheia (back-pressure)."""
        return _capacity_is_full(self.capacity)


async def _redis_outra_sessao(executor_id: str, owner_token: str | None) -> bool | None:
    """Outra sessão detém a posse deste executor? None: não deu para saber."""
    try:
        dono = await (await _get_redis()).get(_conn_owner_key(executor_id))
    except Exception as exc:
        logger.debug("Posse do executor '%s' não conferida: %s", executor_id, exc)
        return None
    return dono is not None and dono != owner_token


async def _fechar_nao_entregue(
    executor_id: str, job_id: str, motivo: str, dono: str | None, *, so_aqui: bool = False,
) -> None:
    """Quem publicou no relay já deu o job por entregue (o run vai a 'running'):
    sem isto ele ficava "Em andamento" até o ACK pendente vencer (10 min).

    Só fecha se nenhuma outra sessão pode tê-lo recebido. `so_aqui`: ele estava
    na fila quando chegou o aviso de takeover — publicado antes de a sessão nova
    subscrever. Fora isso, a posse no Redis decide: ainda desta sessão (ou de
    ninguém) quer dizer que nenhuma sessão nova subscreveu antes deste instante,
    logo nenhuma o recebeu. Com a posse de outra (um executor que reconectou sem
    o aviso chegar aqui) ela pode tê-lo entregue, e fechar o run faria o
    inventário mandar parar o job em execução: fica para a reconciliação.
    """
    if not so_aqui:
        outra = await _redis_outra_sessao(executor_id, dono)
        if outra is not False:
            logger.warning(
                "Job '%s' não saiu pelo socket do executor '%s' (%s), mas %s — a reconciliação decide o run.",
                job_id, executor_id, motivo,
                "outra sessão já assumiu o executor" if outra else "a posse não pôde ser conferida",
            )
            return
    from app.api.routers.executor_ws.orfaos import fechar_run_nao_entregue
    try:
        await fechar_run_nao_entregue(executor_id, job_id, conexao_fechando=motivo != OCUPADO)
    except Exception as exc:
        logger.error("Run '%s' não entregue pelo relay não pôde ser fechado: %s", job_id, exc)


async def _acompanhar_encaminhamento(
    executor_id: str, saida: _Saida, envio: _Envio, canal: str, tipo: str | None,
    job_id: str | None, dono: str | None,
) -> None:
    """Espera o desfecho de uma mensagem que o listener enfileirou — sem prender
    o listener, que atende TODAS as mensagens do executor (inclusive o marker de
    close) e não pode deixá-las envelhecer atrás de um frame grande."""
    try:
        resultado = await saida.aguardar(envio)
    except Exception as exc:
        # Socket morto: nada saiu por ele (um frame cortado no meio não chega a
        # ser lido pelo executor).
        logger.debug("%s: mensagem ao executor '%s' não saiu: %s", canal, executor_id, exc)
        if job_id:
            await _fechar_nao_entregue(executor_id, job_id, "erro do socket", dono)
        return
    if resultado == ENVIADO:
        return
    if resultado == ESCOANDO:
        logger.warning("%s: envio ao executor '%s' passou do prazo — link lento; o frame segue saindo.",
                       canal, executor_id)
        return
    logger.warning("%s: mensagem '%s' ao executor '%s' não saiu (%s).", canal, tipo or "?", executor_id, resultado)
    if job_id:
        # FECHANDO aqui é de uma mensagem que já estava na fila quando o socket
        # começou a fechar.
        await _fechar_nao_entregue(
            executor_id, job_id, resultado, dono, so_aqui=resultado == FECHANDO and saida.avisada,
        )


def _encaminhar(
    executor_id: str, ws, payload: str, canal: str, tipo: str | None, job_id: str | None, dono: str | None,
) -> None:
    saida = _saida_de(ws, executor_id)
    try:
        envio = saida.enfileirar(payload)
    except Exception:
        # Socket morto: o erro sobe (o listener encerra), mas quem publicou
        # contou com este listener.
        if job_id:
            _em_segundo_plano(
                _fechar_nao_entregue(executor_id, job_id, "erro do socket", dono), f"nao-entregue-{job_id[:8]}",
            )
        raise
    if not isinstance(envio, str):
        _em_segundo_plano(
            _acompanhar_encaminhamento(executor_id, saida, envio, canal, tipo, job_id, dono),
            f"encaminha-{executor_id[:8]}",
        )
        return
    if saida.substituida:
        # Chegou depois do takeover: o listener da sessão nova também a recebe.
        # Janela rara: publicada entre o aviso e a inscrição dele (uma ida e
        # volta ao Redis, mais se a inscrição falhar), ninguém a entrega — a
        # reconciliação fecha o run quando o ACK pendente vence.
        logger.debug("%s: socket do executor '%s' substituído — '%s' fica com a sessão nova.",
                     canal, executor_id, tipo or "?")
        return
    # O executor está indo embora (heartbeat, erro de protocolo, disconnect):
    # este listener pode ser o único destinatário, e quem publicou contou com ele.
    if not job_id:
        logger.debug("%s: socket do executor '%s' fechando — '%s' descartado.", canal, executor_id, tipo or "?")
        return
    logger.warning("%s: socket do executor '%s' fechando — job '%s' não encaminhado.", canal, executor_id, job_id)
    _em_segundo_plano(_fechar_nao_entregue(executor_id, job_id, FECHANDO, dono), f"nao-entregue-{job_id[:8]}")


async def _handle_relay_message(
    executor_id: str, ws: "WebSocket", owner_token: str, raw: str,
) -> bool:
    """Trata uma mensagem do canal de relay. Devolve False para encerrar o listener.

    Extraída do laço para que relay e drive events possam dividir UM único
    pubsub — ver `_executor_pubsub_listener`.
    """
    # ── Verifica HMAC do envelope ─────────────────────────────────────────────
    # Qualquer publisher que não tenha APP_SECRET (ex: container externo
    # acessando Redis) produz mensagens sem assinatura válida e é descartado aqui.
    payload = open_signed_envelope(
        raw, channel_label="Relay",
        executor_id=executor_id, audience=_AUDIENCE_RELAY,
    )
    if payload is None:
        return True

    # Parse do payload uma vez — usado pra detectar marker interno de close
    # (nao encaminha). Backpressure fica com o CLIENTE
    # (executor/connection.py:_handle_job), que ja emite `job_result` com erro
    # "fila cheia" para que o server marque o run como failed. Filtrar aqui era
    # duplicata e causava run "running" para sempre.
    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError:
        parsed_payload = None

    # ── Marker interno de close (disconnect_executor) ─────────────────────────
    # Payload publicado por `disconnect_executor` para forcar fechamento remoto
    # do WS. Nao encaminhado ao cliente — so causa close local, cleanup e
    # finaliza o listener.
    if isinstance(parsed_payload, dict):
        internal = parsed_payload.get("__internal__")

        # ── Marker de takeover (outra sessão assumiu a posse) ──
        # Só chega aqui via envelope assinado com APP_SECRET e amarrado a ESTE
        # executor, então não é forjável de fora.
        if isinstance(internal, dict) and "takeover" in internal:
            new_owner = (internal.get("takeover") or {}).get("owner")
            if new_owner == owner_token:
                return True  # eco do meu próprio register
            logger.warning(
                "Executor '%s': outra sessão assumiu a conexão — "
                "fechando este WS duplicado (evita execução dupla de job).",
                executor_id,
            )
            try:
                # 4409 (conflito) NÃO é terminal no cliente: se este socket ainda
                # estiver vivo do lado dele, reconectar é o comportamento correto.
                await fechar_ws_do_executor(
                    ws, code=4409, reason="Conexao assumida por outra sessao.", avisada=True,
                )
            except Exception as exc:
                logger.debug(
                    "Relay: falha ao fechar WS duplicado de '%s': %s", executor_id, exc,
                )
            try:
                await executor_registry.unregister(executor_id, expected_ws=ws)
            except Exception as exc:
                logger.debug(
                    "Relay: falha no unregister pos-takeover de '%s': %s", executor_id, exc,
                )
            return False

        if isinstance(internal, dict) and "close" in internal:
            close_cfg = internal.get("close") or {}
            close_code = int(close_cfg.get("code", 1000))
            close_reason = str(close_cfg.get("reason", ""))
            try:
                await fechar_ws_do_executor(ws, code=close_code, reason=close_reason)
            except Exception as exc:
                logger.debug(
                    "Relay: falha ao fechar WS do executor '%s' via marker: %s",
                    executor_id, exc,
                )
            # Cleanup imediato — sem esperar 90s do heartbeat timeout. Remove
            # presence + entrada local + cancela o listener. O handler do WS caira
            # no finally logo em seguida e sera no-op via expected_ws guard.
            try:
                await executor_registry.unregister(executor_id, expected_ws=ws)
            except Exception as exc:
                logger.debug(
                    "Relay: falha no unregister pos-close remoto de '%s': %s",
                    executor_id, exc,
                )
            logger.info(
                "Relay: WS do executor '%s' fechado remotamente (code=%d reason=%r).",
                executor_id, close_code, close_reason,
            )
            return False

    # Encaminha payload ao cliente. Se for job e a fila do cliente estiver cheia,
    # ele responde com `job_result` error "back-pressure" e o server marca o run
    # failed via `_handle_job_result` (executor_ws_router.py). Enfileira e segue:
    # o desfecho é acompanhado fora do listener (ver `_acompanhar_encaminhamento`).
    tipo = parsed_payload.get("type") if isinstance(parsed_payload, dict) else None
    job_id = ((parsed_payload or {}).get("envelope") or {}).get("job_id") if tipo == "job" else None
    try:
        _encaminhar(executor_id, ws, payload, "Relay", tipo, str(job_id) if job_id else None, owner_token)
    except Exception as exc:
        logger.warning(
            "Relay: falha ao encaminhar mensagem ao executor '%s': %s", executor_id, exc,
        )
        return False
    return True


async def _handle_drive_message(executor_id: str, ws: "WebSocket", raw: str) -> bool:
    """Trata uma mensagem do canal de drive events. False encerra o listener."""
    # SEG: mesma verificação HMAC do relay de jobs. Antes este canal repassava o
    # payload cru do Redis direto ao WS — quem conseguisse publicar nele injetava
    # qualquer mensagem no executor, inclusive
    # {"type":"control","action":"shutdown"} (DoS) e
    # {"type":"control","action":"config_changed"} (SIGTERM em loop), além de
    # drive_events forjados.
    payload = open_signed_envelope(
        raw, channel_label="Drive event",
        executor_id=executor_id, audience=_AUDIENCE_DRIVE,
    )
    if payload is None:
        return True
    # Só drive_event trafega neste canal — control/job têm rota própria.
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict) or parsed.get("type") != "drive_event":
        logger.warning(
            "Drive event: tipo inesperado no canal do executor '%s' — descartado.",
            executor_id,
        )
        return True
    saida = _saidas.get(ws)
    if saida is not None and saida.atrasada():
        # Link abaixo do piso: o evento só engrossaria a fila atrás do frame
        # atrasado. Drive event é melhor-esforço — o GeoSync ressincroniza.
        logger.debug("Drive event ao executor '%s' descartado: envio anterior atrasado.", executor_id)
        return True
    try:
        # O mesmo listener do relay de jobs: enfileira e segue.
        _encaminhar(executor_id, ws, payload, "Drive event", "drive_event", None, None)
    except Exception as exc:
        logger.warning("Drive event: falha ao encaminhar ao executor '%s': %s", executor_id, exc)
        return False
    return True


async def _executor_pubsub_listener(executor_id: str, ws: "WebSocket", owner_token: str) -> None:
    """
    Subscreve os canais 'executor:job_relay:{id}' e 'executor:{id}:drive_events'
    num ÚNICO pubsub e encaminha cada mensagem ao WebSocket do executor. Roda
    como task enquanto o executor está conectado.

    Permite que workers uvicorn que não têm o WS em memória enviem jobs via Redis pub/sub.

    PERF: eram DUAS conexões Redis dedicadas por executor conectado por worker
    (uma por listener), cada uma com pool próprio — numa frota de 200 executores
    e 4 workers isso somava ~1600 sockets só de pubsub, e uma reconexão em
    rajada (deploy, blip de rede) subia todos ao mesmo tempo, pressionando o
    `maxclients` justamente quando o dispatch mais precisa do Redis. Um pubsub
    subscreve os dois canais e o despacho é por `message["channel"]`, cada um com
    a validação de envelope do SEU propósito (audience RELAY vs DRIVE) — a amarra
    anti-replay cross-canal continua exatamente onde estava.

    ROBUSTEZ:
      - Valida backpressure antes de encaminhar (o publisher em outro worker não
        conhece o capacity local).
      - Auto-restart com backoff exponencial se a conexão Redis cair (timeout/
        connection refused). Sem isso, um único erro transiente deixa o executor
        inalcançável via relay até que ele reconecte — o que causou o cenário
        "online no Redis mas sem relay listener ativo" em produção.
      - Backoff só zera após ficar saudável por _HEALTHY_THRESHOLD segundos —
        evita churn de TCP em loop apertado quando o problema é persistente
        (ex.: socket_timeout misconfig fazendo o read estourar a cada 5s).
      - TimeoutError de leitura no pubsub é demovido para DEBUG (causa
        rotineira); a cada _NOISY_WARN_EVERY reconexões loga 1 WARNING
        agregado pra operação. Outros erros continuam WARNING imediato.
      - Contador de restarts por executor (increment_listener_restart) alimenta
        o WARNING agregado acima.
      - Saída limpa em CancelledError (registry cancelou) via try/finally
        (CancelledError herda de BaseException, não cai no except Exception).

    `owner_token` identifica ESTA sessão. O canal também transporta o marker
    interno `__internal__.takeover`, publicado por quem assume a posse global da
    conexão: um listener que receba um takeover com token diferente do seu sabe
    que virou duplicata e fecha o próprio WS na hora (sem esperar o heartbeat).
    """
    relay_ch = _relay_channel(executor_id)
    drive_ch = _drive_channel(executor_id)
    channels = (relay_ch, drive_ch)
    backoff = 1.0
    _MAX_BACKOFF = 30.0
    _HEALTHY_THRESHOLD = 60.0    # segundos saudável antes de zerar o backoff
    _NOISY_WARN_EVERY = 50       # logs agregados a cada N reconexões consecutivas
    iteration = 0

    while True:
        iteration += 1
        rc: _aioredis.Redis | None = None
        pubsub = None
        ws_closed = False
        subscribed_at: float | None = None
        try:
            # PubSub usa conexão dedicada (não o singleton) — listen() é bloqueante
            # e acomodamos uma conexão por listener ativo.
            # Override explícito: produção mostrou socket_timeout efetivo de ~5s
            # vindo de algum lugar opaco (provavelmente REDIS_URL com query).
            # socket_timeout=None garante que pubsub.listen() bloqueia idle.
            # socket_keepalive=True + health_check_interval=30 cobrem detecção
            # de conexão morta no nível do SO e do protocolo redis.
            rc = _aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=None,
                socket_connect_timeout=10,
                socket_keepalive=True,
                health_check_interval=30,
            )
            pubsub = rc.pubsub()
            await pubsub.subscribe(*channels)
            subscribed_at = time.monotonic()
            if iteration == 1:
                logger.debug("Pubsub listener iniciado para executor '%s'.", executor_id)
            else:
                restart_count = executor_registry.increment_listener_restart(executor_id, "pubsub")
                if restart_count % _NOISY_WARN_EVERY == 0:
                    logger.warning(
                        "Pubsub listener para executor '%s' acumulou %d reconexões — "
                        "investigar saúde do Redis pubsub.",
                        executor_id, restart_count,
                    )
                else:
                    logger.debug(
                        "Pubsub listener reconectado para executor '%s' (tentativa %d).",
                        executor_id, restart_count,
                    )
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                # O canal decide a validação: um envelope de drive apresentado no
                # canal de relay (ou vice-versa) continua sendo recusado pelo
                # `audience` do envelope.
                if message["channel"] == relay_ch:
                    alive = await _handle_relay_message(
                        executor_id, ws, owner_token, message["data"],
                    )
                else:
                    alive = await _handle_drive_message(executor_id, ws, message["data"])
                if not alive:
                    ws_closed = True
                    break
        except _RedisTimeoutError as exc:
            # Causa rotineira (read pubsub estourando socket_timeout). Mantém
            # como DEBUG por padrão; o WARNING agregado já avisa a operação.
            logger.debug(
                "Pubsub listener: timeout no read (executor '%s'): %s", executor_id, exc,
            )
        except Exception as exc:
            logger.warning(
                "Pubsub listener erro (executor '%s'): %s — reiniciando em %.1fs.",
                executor_id, exc, backoff,
            )
        finally:
            # CancelledError herda de BaseException e cai aqui também.
            # _cleanup_pubsub é best-effort e idempotente.
            await _cleanup_pubsub(pubsub, rc, channels, "pubsub", executor_id)

        # Não reinicia se o WS já caiu — quem cuidar do unregister cancelará.
        if ws_closed or ws.client_state == WebSocketState.DISCONNECTED:
            break

        # Reset do backoff só se ficou saudável tempo suficiente.
        # Em loop apertado (timeout recorrente), backoff cresce até MAX_BACKOFF.
        elapsed = (time.monotonic() - subscribed_at) if subscribed_at else 0.0
        if elapsed >= _HEALTHY_THRESHOLD:
            backoff = 1.0
        else:
            backoff = min(backoff * 2, _MAX_BACKOFF)

        # Dispersa a espera (50–100%) — ver flow/utils/backoff.py. Todos os
        # listeners de uma API que perdeu o Redis reiniciam juntos; sem jitter
        # eles voltam a bater nele no mesmo instante.
        await asyncio.sleep(com_jitter(backoff))

    logger.debug("Pubsub listener encerrado para executor '%s'.", executor_id)


async def _cleanup_pubsub(
    pubsub, rc: "_aioredis.Redis | None", channels, label: str, executor_id: str,
) -> None:
    """Fecha pubsub/conexão Redis de um listener — best-effort, não levanta."""
    if isinstance(channels, str):
        channels = (channels,)
    if pubsub is not None:
        try:
            await asyncio.wait_for(pubsub.unsubscribe(*channels), timeout=2.0)
            await asyncio.wait_for(pubsub.aclose(), timeout=2.0)
        except Exception as exc:
            logger.debug("Falha ao fechar pubsub do %s (executor '%s'): %s", label, executor_id, exc)
    if rc is not None:
        try:
            await asyncio.wait_for(rc.aclose(), timeout=2.0)
        except Exception as exc:
            logger.debug("Falha ao fechar conexão Redis do %s (executor '%s'): %s", label, executor_id, exc)




class ExecutorConnectionRegistry:
    """
    Mantém um mapa executor_id → ExecutorConnection para conexões WebSocket ativas.

    Thread-safety: asyncio é single-threaded por worker; usamos asyncio.Lock
    em update_capacity para garantir atomicidade lógica quando múltiplos
    await points ocorrem em sequência.
    """

    def __init__(self):
        self._connections: dict[str, ExecutorConnection] = {}
        # UMA task de pubsub por executor: relay e drive events dividem o mesmo
        # cliente Redis (ver `_executor_pubsub_listener`).
        self._listener_tasks: dict[str, asyncio.Task] = {}
        # Cache local de presença (executor_id → (online, timestamp)) com TTL curto.
        self._presence_cache: dict[str, tuple[bool, float]] = {}
        # executor_id → monotonic da última desconexão limpa (carência de dispatch).
        self._recent_disconnects: dict[str, float] = {}
        # Contadores de restart do listener (executor_id → {"pubsub": N}): a cada
        # _NOISY_WARN_EVERY reconexões o listener loga um WARNING agregado.
        # Resetam no unregister.
        self._listener_restarts: dict[str, dict[str, int]] = {}
        # Lock por operação de registro para evitar register+unregister concorrente.
        self._register_lock = asyncio.Lock()
        self._capacity_lock = asyncio.Lock()

    def increment_listener_restart(self, executor_id: str, label: str) -> int:
        """Incrementa atomicamente o contador de restarts de um listener e devolve o novo valor."""
        counters = self._listener_restarts.setdefault(executor_id, {})
        counters[label] = counters.get(label, 0) + 1
        return counters[label]

    # ── Gerenciamento de conexões ─────────────────────────────────────────────

    async def register(
        self,
        executor_id: str,
        ws: WebSocket,
        executor_version: str | None = None,
        *,
        max_concurrent_limit: int | None = None,
        max_queue_limit: int | None = None,
    ):
        """Registra a conexão e assume a POSSE GLOBAL dela.

        `max_concurrent_limit`/`max_queue_limit` vêm do registro do Executor no
        banco (lido pelo router durante a validação mTLS, sem query extra) e
        servem de teto para a capacidade auto-declarada — ver S3 no WS router.
        """
        # Idempotência: se já existe conexão para este executor_id, derruba a antiga
        # antes de registrar a nova (evita dois workers disputando o mesmo slot).
        async with self._register_lock:
            if executor_id in self._connections:
                logger.warning("Executor '%s' já registrado — substituindo conexão anterior.", executor_id)
                await self._unregister_locked(executor_id)

            executor_ip = ip_do_websocket(ws)
            conn = ExecutorConnection(
                executor_id=executor_id,
                websocket=ws,
                executor_version=executor_version,
                executor_ip=executor_ip,
            )
            if max_concurrent_limit is not None:
                conn.max_concurrent_limit = max_concurrent_limit
            if max_queue_limit is not None:
                conn.max_queue_limit = max_queue_limit
            # Até o primeiro `capacity`, assume o executor vazio com os limites
            # do banco — o dispatch não deve enxergar mais folga do que existe.
            conn.capacity = {
                "queued":         0,
                "running":        0,
                "max_concurrent": conn.max_concurrent_limit,
                "max_queue":      conn.max_queue_limit,
            }
            self._connections[executor_id] = conn

            await _redis_claim_presence(executor_id, conn.owner_token)
            # Socket novo, nada escoando: uma marca de parada da sessão anterior
            # recusaria o relay para um executor saudável por até 60 s.
            try:
                await (await _get_redis()).delete(_chave_de_parada(executor_id))
            except Exception as exc:
                logger.debug("Marca de parada de '%s' não limpa no registro: %s", executor_id, exc)
            # Publica a capacidade inicial (vazia): o relay de outros workers
            # não pode herdar um "cheio" antigo até o primeiro heartbeat.
            await _redis_store_capacity(executor_id, conn.capacity)
            conn.last_capacity_store = time.monotonic()
            # Invalida cache local — executor está online agora.
            self._presence_cache[executor_id] = (True, time.monotonic())

            # Avisa pelo relay qualquer sessão anterior (possivelmente em OUTRO
            # worker uvicorn, com o WS ainda vivo) para fechar na hora — sem
            # isso, as duas receberiam o mesmo job pelo PUBLISH e o workflow
            # rodaria duas vezes. Mesmo sem dono anterior no Redis: a posse de
            # uma sessão que ainda está fechando (heartbeat estourado) vence no
            # meio do close, e o listener dela precisa saber que foi substituído.
            #
            # O aviso sai ANTES de o listener desta sessão existir: o que foi
            # publicado antes dele fica só com a sessão antiga, que ao fechar o
            # dá por não entregue (ver `_Saida.avisada`) — nunca com as duas.
            await self._announce_takeover(executor_id, conn.owner_token)

            # Um único listener cobre relay (jobs despachados por outros
            # workers) E drive events — os dois canais chegam pelo mesmo pubsub.
            task = asyncio.create_task(
                _executor_pubsub_listener(executor_id, ws, conn.owner_token),
                name=f"pubsub-{executor_id[:8]}",
            )
            self._listener_tasks[executor_id] = task

            logger.info("Executor '%s' conectado (versão=%s).", executor_id, executor_version)

    async def _unregister_locked(
        self, executor_id: str, expected_ws: "WebSocket | None" = None,
    ) -> None:
        """Implementação interna — assume que o caller já tem self._register_lock.

        Se `expected_ws` for passado, a remocao so acontece quando o WS
        atualmente registrado eh identicamente esse (`is`). Evita o race
        classico: handler A cai no finally e chama unregister DEPOIS que
        o executor ja reconectou e handler B registrou WS_B — sem essa
        checagem, A removia o WS_B legitimo e o executor entrava em
        flapping.
        """
        current = self._connections.get(executor_id)
        if expected_ws is not None and current is not None and current.websocket is not expected_ws:
            # WS atual pertence a outra sessao (reconexao recente). Nao mexer.
            logger.debug(
                "unregister ignorado para '%s': WS atual pertence a sessao diferente.",
                executor_id,
            )
            return

        conn = self._connections.pop(executor_id, None)
        # Liberação por CAS: só apaga presence/owner se ESTA sessão ainda for a
        # dona. Sem conexão local não há token, logo não há o que provar — e o
        # DELETE incondicional que existia aqui invalidava a sessão viva de
        # outro worker uvicorn ("503 Nenhum executor disponível" com o executor
        # online). O TTL de 120s cobre o caso do worker que morre sem unregister.
        if conn is not None:
            # A capacidade só sai com a posse: depois de um takeover a chave já é
            # da sessão nova, e apagá-la zerava a capacidade que ela publicou.
            if await _redis_release_presence(executor_id, conn.owner_token) is not False:
                await _redis_delete_capacity(executor_id)
            self._recent_disconnects[executor_id] = time.monotonic()
        self._presence_cache[executor_id] = (False, time.monotonic())
        # Reseta o contador de restarts — a próxima register é um ciclo novo.
        self._listener_restarts.pop(executor_id, None)

        task = self._listener_tasks.pop(executor_id, None)
        if task and not task.done():
            task.cancel()

        if conn:
            # Timeout defensivo — ws.close() normalmente retorna rápido (só envia
            # frame), mas queremos garantia absoluta de não travar o register lock.
            try:
                await asyncio.wait_for(fechar_ws_do_executor(conn.websocket), timeout=2.0)
            except Exception:
                pass
            logger.info("Executor '%s' desconectado.", executor_id)

    async def _announce_takeover(self, executor_id: str, owner_token: str) -> None:
        """Publica no relay o marker que manda a sessão antiga se fechar."""
        try:
            payload = json.dumps({"__internal__": {"takeover": {"owner": owner_token}}})
            envelope = build_relay_envelope(payload, executor_id=executor_id)
            rc = await _get_redis()
            await rc.publish(_relay_channel(executor_id), envelope)
        except Exception as exc:
            # Não é fatal: o perdedor também descobre na próxima renovação de
            # presença (`_redis_renew_presence` devolve False) — só demora mais.
            logger.warning(
                "Falha ao anunciar takeover da conexão do executor '%s': %s",
                executor_id, exc,
            )

    async def _renew_presence_or_drop(self, conn: ExecutorConnection) -> None:
        """Renova a presença; se a posse global mudou, fecha este WS duplicado.

        THROTTLE: a chave vale 120s e as mensagens que chamam aqui chegam a cada
        10s — renovar em todas era um EVAL Lua por mensagem, dentro do loop de
        recepção, atrasando o node_event/job_result que viesse logo atrás. Só
        renovamos a cada `_PRESENCE_RENEW_INTERVAL`; nos demais casos a conexão
        local é prova suficiente de que o executor está vivo para o cache.

        O carimbo do throttle só avança quando a renovação REALMENTE aconteceu.
        Avançá-lo antes da tentativa (com `_redis_renew_presence` devolvendo
        "sucesso" em erro de Redis) transformava um blip em "renovei" por um
        intervalo inteiro: a chave expirava com o WebSocket vivo e o
        `orphan_runs_watchdog` marcava como failed runs que estavam progredindo.
        """
        now = time.monotonic()
        if (now - conn.last_presence_renew) < _PRESENCE_RENEW_INTERVAL:
            self._presence_cache[conn.executor_id] = (True, now)
            return
        resultado = await _redis_renew_presence(conn.executor_id, conn.owner_token)
        if resultado is None:
            # Não deu para falar com o Redis: NÃO carimba renovação. Reagenda a
            # próxima tentativa para daqui a pouco em vez de um intervalo cheio,
            # para que a recuperação do Redis regrave a chave antes do TTL.
            conn.last_presence_renew = (
                now - _PRESENCE_RENEW_INTERVAL + _PRESENCE_RENEW_RETRY_INTERVAL
            )
            return
        conn.last_presence_renew = time.monotonic()
        if resultado:
            self._presence_cache[conn.executor_id] = (True, conn.last_presence_renew)
            return
        logger.warning(
            "Executor '%s': posse da conexão pertence a outra sessão — "
            "encerrando este WS duplicado.",
            conn.executor_id,
        )
        # Já na hora, antes de esperar a trava do unregister: o que for mandado
        # a este executor daqui em diante segue pelo relay até a sessão nova.
        # (O que já estava na fila é dado por não entregue ao fechar; sem o
        # aviso de takeover, a sessão nova pode tê-lo recebido também — caso
        # raro: exige o aviso perdido e a fila cheia neste instante.)
        _marcar_fechando(conn.websocket, substituida=True)
        await self.unregister(conn.executor_id, expected_ws=conn.websocket)

    async def unregister(
        self, executor_id: str, expected_ws: "WebSocket | None" = None,
    ):
        """Remove o executor do registry. Se `expected_ws` for passado,
        so remove quando o WS registrado for identicamente esse — protege
        contra race quando um handler finaliza depois de o executor ja
        ter reconectado noutra sessao."""
        async with self._register_lock:
            await self._unregister_locked(executor_id, expected_ws=expected_ws)

    def _conexao_para_envio(self, executor_id: str) -> "ExecutorConnection | str | None":
        """A conexão local, se ela ainda serve para enviar; None para ir pelo
        relay (o executor não está neste worker); FECHANDO se ele está indo
        embora — quem manda devolve False e o dispatch tenta o próximo.

        Uma conexão sendo fechada não serve. Se ela foi SUBSTITUÍDA (outra
        sessão assumiu o executor), quem manda cai no relay e o listener da
        sessão nova entrega. Nos outros fechamentos (heartbeat, erro de
        protocolo, disconnect, revogação) não há sessão nova: o único ouvinte
        do relay seria o listener deste mesmo socket, que descartaria a
        mensagem depois de o publish contar um destinatário — o job ia a
        'running' sem nunca sair."""
        conn = self._connections.get(executor_id)
        if conn is None:
            return None
        saida = _saidas.get(conn.websocket)
        if saida is None or not saida.fechando:
            return conn
        return None if saida.substituida else FECHANDO

    async def presence_or_unknown(self, executor_id: str) -> bool | None:
        """Presença em TRI-ESTADO para o DISPATCH (spec §5.1).

        True  = há prova de vida (WS neste worker, cache positivo ou chave viva).
        None  = não sei: Redis fora, ou desconexão limpa há menos de
                `_DISPATCH_GRACE_SECONDS` (pode estar reconectando). Quem monta
                candidatos TENTA o executor — o `send_job` real decide.
        False = presença ausente e fora da carência: excluído.

        `is_online` continua fail-closed para quem precisa de um booleano.
        """
        if executor_id in self._connections:
            return True
        now = time.monotonic()
        cached = self._presence_cache.get(executor_id)
        if cached is not None and cached[0] and (now - cached[1]) < _PRESENCE_CACHE_TTL:
            return True
        presenca = await _redis_presence_or_unknown(executor_id)
        if presenca is True:
            self._presence_cache[executor_id] = (True, now)
            self._recent_disconnects.pop(executor_id, None)
            return True
        if presenca is None:
            return None
        desconectou_em = self._recent_disconnects.get(executor_id)
        if desconectou_em is not None and (now - desconectou_em) < _DISPATCH_GRACE_SECONDS:
            return None
        self._recent_disconnects.pop(executor_id, None)
        return False

    async def read_capacity(self, executor_id: str) -> dict | None:
        """Capacidade conhecida: a local (WS neste worker) ou a publicada no Redis."""
        conn = self._connections.get(executor_id)
        if conn is not None:
            return dict(conn.capacity)
        return await _redis_read_capacity(executor_id)

    async def read_capacities(self, executor_ids: list[str]) -> dict[str, dict | None]:
        """`read_capacity` de vários executores: os locais da memória, os demais
        numa ida só ao Redis. O despacho lê todos os candidatos de um nível a
        cada job — um GET por candidato abria uma conexão Redis por executor."""
        capacidades: dict[str, dict | None] = {}
        remotos: list[str] = []
        for eid in executor_ids:
            conn = self._connections.get(eid)
            if conn is not None:
                capacidades[eid] = dict(conn.capacity)
            else:
                remotos.append(eid)
        if remotos:
            capacidades.update(await _redis_read_capacities(remotos))
        return capacidades

    async def read_presence_and_capacities(
        self, executor_ids: list[str],
    ) -> tuple[dict[str, bool], dict[str, dict | None]]:
        """Presença e capacidade publicada de vários executores numa ida só ao
        Redis (um MGET das duas chaves de cada um): o mesmo retrato em qualquer
        worker. É a leitura das telas, e por isso:

        - sem o cache positivo do `is_online`, que num worker ainda dava
          "online" até `_PRESENCE_CACHE_TTL` depois da queda;
        - com a cópia publicada da capacidade mesmo para o WebSocket deste
          worker. Ela só é regravada quando a carga muda ou a cada
          `_CAPACITY_STORE_INTERVAL`, então disco e RAM livres nela podem ter
          até esse tempo — mas são os mesmos em todos os workers;
        - offline não tem capacidade: a cópia pode sobreviver à presença por
          até um TTL (a remoção no unregister falhou, ou as chaves vencem em
          momentos diferentes).

        Redis fora: todos offline, como no `is_online`."""
        if not executor_ids:
            return {}, {}
        chaves = [chave for eid in executor_ids for chave in (_presence_key(eid), _capacity_key(eid))]
        try:
            rc = await _get_redis()
            valores = await rc.mget(*chaves)
        except Exception as exc:
            logger.warning(
                "Redis: falha ao ler presença e capacidade de %d executores: %s", len(executor_ids), exc,
            )
            await _reset_redis_singleton()
            return dict.fromkeys(executor_ids, False), dict.fromkeys(executor_ids)
        online: dict[str, bool] = {}
        capacidades: dict[str, dict | None] = {}
        for n, eid in enumerate(executor_ids):
            presenca, capacidade = valores[2 * n], valores[2 * n + 1]
            online[eid] = presenca is not None
            capacidades[eid] = _capacidade_de(capacidade) if online[eid] else None
        return online, capacidades

    async def is_online(self, executor_id: str) -> bool:
        """Verifica presença no Redis com cache POSITIVO de curta duração.

        Negative caching foi removido: um blip momentâneo do Redis ou uma
        reconexão em progresso não deve prender o executor como "offline" por
        5s no cache — isso causava "Nenhum executor disponível" logo após uma
        reconexão normal. Apenas respostas positivas são cacheadas; qualquer
        miss vai sempre ao Redis.
        """
        cached = self._presence_cache.get(executor_id)
        now = time.monotonic()
        if cached is not None and cached[0] and (now - cached[1]) < _PRESENCE_CACHE_TTL:
            return True
        online = await _redis_check_presence(executor_id)
        if online:
            self._presence_cache[executor_id] = (True, now)
        else:
            # Não cacheia False: força re-check no próximo is_online.
            self._presence_cache.pop(executor_id, None)
        return online

    def get(self, executor_id: str) -> ExecutorConnection | None:
        return self._connections.get(executor_id)

    # ── Atualização de metadados ──────────────────────────────────────────────

    async def update_capacity(self, executor_id: str, capacity: dict):
        # Lock evita que duas capacity updates concorrentes alternem leitores
        # (is_full) para um estado intermediário. O rebind do dict é atômico
        # pelo GIL, mas o pareamento com last_seen_at se beneficia do lock.
        async with self._capacity_lock:
            conn = self._connections.get(executor_id)
            if conn:
                conn.capacity = dict(capacity)  # cópia defensiva
                conn.last_seen_at = datetime.now(timezone.utc)
        # Renova o TTL de presença no Redis a cada mensagem de capacidade.
        # Sem conexão local não há como provar a posse — quem renovaria seria um
        # worker que não tem o WS, ressuscitando presença de sessão morta.
        if conn:
            await self._renew_presence_or_drop(conn)
            # A renovação pode ter descoberto que outra sessão é a dona e
            # derrubado esta: publicar agora sobrescreveria a capacidade da
            # sessão nova — no despacho e na tela — até ela regravar (30 s).
            if self._connections.get(executor_id) is not conn:
                return
            await self._store_capacity(conn)

    async def _store_capacity(self, conn: ExecutorConnection) -> None:
        """Publica a capacidade para o relay; só quando muda ou por intervalo."""
        c = conn.capacity
        assinatura = (c.get("queued", 0), c.get("running", 0),
                      c.get("max_concurrent", 4), c.get("max_queue", 50))
        now = time.monotonic()
        if assinatura == conn.last_capacity_stored and (now - conn.last_capacity_store) < _CAPACITY_STORE_INTERVAL:
            return
        conn.last_capacity_stored = assinatura
        conn.last_capacity_store = now
        await _redis_store_capacity(conn.executor_id, c)

    async def update_last_seen(self, executor_id: str):
        conn = self._connections.get(executor_id)
        if not conn:
            return
        conn.last_seen_at = datetime.now(timezone.utc)
        # Renova o TTL de presença no Redis a cada heartbeat
        await self._renew_presence_or_drop(conn)

    # ── Envio de jobs ─────────────────────────────────────────────────────────

    # Janela (segundos) após a qual um job enviado sem ACK é considerado perdido.
    JOB_ACK_WARN_SECONDS = 15.0

    async def record_pending_ack(self, job_id: str, executor_id: str) -> None:
        """Registra um job em voo aguardando ACK do executor (compartilhado via Redis).

        Chave principal carrega o executor_id e o timestamp de envio; o set de
        índice permite enumerar IDs vivos sem SCAN no banco inteiro.
        """
        if not job_id or job_id == "?":
            return
        try:
            rc = await _get_redis()
            value = f"{executor_id}|{time.time()}"
            async with rc.pipeline(transaction=True) as p:
                p.set(_pending_ack_key(job_id), value, ex=_PENDING_ACK_TTL_SECONDS)
                p.sadd(_PENDING_ACKS_INDEX_KEY, job_id)
                await p.execute()
        except Exception as exc:
            logger.warning("Redis: falha ao registrar pending_ack '%s': %s", job_id, exc)
            await _reset_redis_singleton()

    async def clear_pending_ack(
        self, job_id: str, *, expected_executor_id: str | None = None,
    ) -> str | None:
        """Remove o job da lista de pendentes — chamado ao receber ACK.

        Retorna o executor_id que tinha sido registrado, ou None se o ACK
        chegou para um job_id desconhecido (TTL expirou, limpeza de outro
        worker, ou vindo de outra instalação).

        SEG: com `expected_executor_id`, o ACK só é aceito se o job tiver sido
        despachado para aquele executor. Sem esse vínculo, um executor podia
        confirmar jobs de outro (job_id é global), apagando a evidência de job
        perdido usada por overdue_acks(). A conferência de dono e a remoção são
        UM script Lua: além de cortar um round-trip do caminho quente de cada
        ACK, fecham a janela que existia entre o GET e o GETDEL.
        """
        if not job_id:
            return None
        try:
            rc = await _get_redis()
            result = await rc.eval(
                _LUA_CLEAR_PENDING_ACK, 2,
                _pending_ack_key(job_id), _PENDING_ACKS_INDEX_KEY,
                expected_executor_id or "", job_id,
            )
            if not result:
                return None
            cleared, value = result[0], result[1]
            if not cleared:
                logger.warning(
                    "ACK do job '%s' recusado: enviado por '%s' mas despachado para '%s'.",
                    job_id, expected_executor_id, value,
                )
                return None
            return value.split("|", 1)[0]
        except Exception as exc:
            logger.warning("Redis: falha ao limpar pending_ack '%s': %s", job_id, exc)
            await _reset_redis_singleton()
            return None

    async def overdue_acks(self) -> list[tuple[str, str, float]]:
        """Retorna tuplas (job_id, executor_id, elapsed) para jobs sem ACK há mais
        que JOB_ACK_WARN_SECONDS. Background task pode consumir para alertas.

        Faz cleanup oportunista do índice: IDs cujo TTL expirou são removidos
        do set para não acumular fantasmas.
        """
        try:
            rc = await _get_redis()
            ids = await rc.smembers(_PENDING_ACKS_INDEX_KEY)
            if not ids:
                return []
            keys = [_pending_ack_key(jid) for jid in ids]
            values = await rc.mget(*keys)
            now = time.time()
            overdue: list[tuple[str, str, float]] = []
            ghosts: list[str] = []
            for jid, raw in zip(ids, values):
                if raw is None:
                    ghosts.append(jid)
                    continue
                try:
                    executor_id, sent_at_str = raw.split("|", 1)
                    elapsed = now - float(sent_at_str)
                except (ValueError, TypeError):
                    ghosts.append(jid)
                    continue
                if elapsed >= self.JOB_ACK_WARN_SECONDS:
                    overdue.append((jid, executor_id, elapsed))
            if ghosts:
                await rc.srem(_PENDING_ACKS_INDEX_KEY, *ghosts)
            return overdue
        except Exception as exc:
            logger.warning("Redis: falha ao listar overdue_acks: %s", exc)
            await _reset_redis_singleton()
            return []

    async def list_pending_acks(self) -> list[dict]:
        """Lista todos os pending_acks com elapsed (para endpoint admin)."""
        try:
            rc = await _get_redis()
            ids = await rc.smembers(_PENDING_ACKS_INDEX_KEY)
            if not ids:
                return []
            keys = [_pending_ack_key(jid) for jid in ids]
            values = await rc.mget(*keys)
            now = time.time()
            items: list[dict] = []
            for jid, raw in zip(ids, values):
                if raw is None:
                    continue
                try:
                    executor_id, sent_at_str = raw.split("|", 1)
                    elapsed = round(now - float(sent_at_str), 2)
                except (ValueError, TypeError):
                    continue
                items.append({"job_id": jid, "executor_id": executor_id, "elapsed_seconds": elapsed})
            return items
        except Exception as exc:
            logger.warning("Redis: falha ao listar pending_acks: %s", exc)
            await _reset_redis_singleton()
            return []

    async def send_job(self, executor_id: str, job_message: dict) -> bool:
        """
        Envia um job ao executor via WebSocket.

        Se o WebSocket estiver neste worker: envia diretamente.
        Se estiver em outro worker: publica no canal Redis de relay.

        Retorna True se o envio/relay foi bem-sucedido.
        Retorna False se o executor não está online ou a fila está cheia.
        """
        wire_message = {"type": "job", **job_message}
        wire_text    = json.dumps(wire_message)
        job_id       = job_message.get("envelope", {}).get("job_id", "?")

        conn = self._conexao_para_envio(executor_id)
        if conn is FECHANDO:
            logger.warning(
                "Executor '%s' desconectando — job '%s' vai ao próximo candidato.", executor_id, job_id,
            )
            return False

        # ── Caminho direto: WS está neste worker ─────────────────────────────
        if conn is not None:
            saida = _saida_de(conn.websocket, executor_id)
            if saida.atrasada():
                # O link está abaixo do piso: o próximo candidato recebe este job
                # em vez de ele entrar na fila atrás do frame atrasado.
                logger.warning(
                    "Executor '%s' com envio anterior atrasado — tentando o próximo candidato.",
                    executor_id,
                )
                return False
            if conn.is_full():
                logger.warning(
                    "Executor '%s' com fila cheia (queued=%d, running=%d) — back-pressure.",
                    executor_id,
                    conn.capacity.get("queued", 0),
                    conn.capacity.get("running", 0),
                )
                return False
            try:
                resultado = await saida.enviar(wire_text)
            except Exception as exc:
                logger.error("Erro ao enviar job ao executor '%s': %s", executor_id, exc)
                # `expected_ws`: o executor pode já ter reconectado NESTE worker
                # enquanto o envio falhava — derrubar a conexão nova só geraria
                # outra reconexão.
                await self.unregister(executor_id, expected_ws=conn.websocket)
                return False
            if resultado in (OCUPADO, FECHANDO):
                # Nada foi escrito: o próximo candidato recebe o job.
                logger.warning(
                    "Job '%s' não saiu para o executor '%s' (%s) — vai ao próximo candidato.",
                    job_id, executor_id, resultado,
                )
                return False
            if resultado == ESCOANDO:
                # Entregue sem confirmação — ver `_PRAZO_DE_ENVIO_BASE_S`.
                logger.warning(
                    "Job '%s': envio ao executor '%s' passou do prazo — link lento. O frame "
                    "segue saindo; o ACK, o inventário ou a varredura confirmam ou fecham o run.",
                    job_id, executor_id,
                )
            else:
                logger.info("Job '%s' enviado ao executor '%s' via WebSocket.", job_id, executor_id)
            await self.record_pending_ack(job_id, executor_id)
            return True

        # ── Caminho relay: WS está em outro worker uvicorn ───────────────────
        # Verifica presença no Redis antes de tentar o relay
        if not await _redis_check_presence(executor_id):
            logger.debug("Executor '%s' offline — job não enviado.", executor_id)
            return False

        # A MESMA regra do caminho direto: cheio ⇒ recusa ⇒ o dispatch tenta o
        # próximo candidato. Antes o relay publicava sem olhar capacidade, o
        # executor rejeitava por fila cheia e o run FALHAVA — o mesmo estado
        # produzia desfechos opostos conforme o worker que atendia a request.
        capacidade = await _redis_read_capacity(executor_id)
        if _capacity_is_full(capacidade):
            logger.warning(
                "Executor '%s' com fila cheia (relay; queued=%d, running=%d) — back-pressure.",
                executor_id,
                capacidade.get("queued", 0), capacidade.get("running", 0),
            )
            return False
        if await _redis_parada(executor_id):
            # O worker que segura o socket está preso atrás de um frame parado:
            # o job publicado agora esperaria a vez e seria descartado por idade.
            logger.warning(
                "Executor '%s' com envio parado noutro worker — job '%s' vai ao próximo candidato.",
                executor_id, job_id,
            )
            return False

        try:
            # Envelope assinado — listener valida HMAC antes de encaminhar ao WS.
            # Protege contra publisher não-autorizado no canal Redis.
            envelope = build_relay_envelope(wire_text, executor_id=executor_id)
            rc = await _get_redis()
            recipients = await rc.publish(_relay_channel(executor_id), envelope)
            if recipients == 0:
                # Executor aparece no Redis mas nenhum worker subscreveu o canal ainda
                # (race condition na inicialização — improvável mas possível)
                logger.warning(
                    "Executor '%s' online no Redis mas sem relay listener ativo — job não enviado.",
                    executor_id,
                )
                return False
            logger.info("Job '%s' encaminhado via relay Redis ao executor '%s'.", job_id, executor_id)
            # Tracking compartilhado via Redis: registrar aqui é seguro mesmo
            # com WS em outro worker — o ACK será limpo lá.
            await self.record_pending_ack(job_id, executor_id)
            return True
        except Exception as exc:
            logger.error("Erro no relay Redis para executor '%s': %s", executor_id, exc)
            return False

    async def send_json(self, executor_id: str, data: dict) -> bool:
        """Envia um payload JSON arbitrário ao executor (ex: cancel, control).

        Multi-worker uvicorn: se o WS estiver em outro worker, publica no
        canal Redis 'executor:job_relay:{id}' (mesmo canal do send_job) —
        o listener que tem o WS entrega. Sem esse relay, control messages
        (ex: 'action:revoked') morriam silenciosamente quando o admin caia
        num worker sem o WS, deixando o executor conectado indefinidamente
        apesar de o DB estar 'revoked'.

        SEG (S7): `control` e `cancel` são assinados AQUI, no ponto único de
        saída, em vez de em cada router que os emite — são 6 call sites hoje e
        um esquecido seria um comando descartado pelo executor. O HMAC do relay
        protege apenas o salto Redis→worker; a assinatura Ed25519 protege o
        comando fim-a-fim até o executor e o amarra a um destinatário, a um
        prazo curto e a um nonce.
        """
        from app.core.control_crypto import sign_if_needed

        try:
            data = sign_if_needed(data, executor_id)
        except RuntimeError as exc:
            # Sem chave de assinatura o executor descartaria a mensagem de
            # qualquer forma. Falhar aqui deixa o motivo no log do servidor em
            # vez de virar "comando sumiu" do lado do executor.
            logger.error(
                "Não foi possível assinar '%s' para o executor '%s': %s",
                data.get("type"), executor_id, exc,
            )
            return False

        conn = self._conexao_para_envio(executor_id)
        if conn is FECHANDO:
            logger.warning(
                "Mensagem '%s' ao executor '%s' não enviada: conexão fechando.", data.get("type"), executor_id,
            )
            return False

        # Caminho direto: WS neste worker.
        if conn is not None:
            try:
                resultado = await enviar_ao_executor(conn.websocket, json.dumps(data), executor_id)
            except Exception as exc:
                logger.warning("Falha ao enviar mensagem direta ao executor '%s': %r", executor_id, exc)
                await self.unregister(executor_id, expected_ws=conn.websocket)
                return False
            if resultado == ENVIADO:
                return True
            logger.warning(
                "Mensagem '%s' ao executor '%s': %s.", data.get("type"), executor_id,
                "link lento; o frame segue saindo" if resultado == ESCOANDO else f"não saiu ({resultado})",
            )
            # ESCOANDO: para quem chama — um cancel, por exemplo — a mensagem foi
            # entregue. OCUPADO (inclusive de cara, com um envio anterior
            # atrasado) e FECHANDO: nada saiu.
            return resultado == ESCOANDO

        # Caminho relay: WS em outro worker uvicorn.
        if not await _redis_check_presence(executor_id):
            return False
        if await _redis_parada(executor_id):
            # Publicada agora, esperaria a vez atrás do frame parado e seria
            # descartada por idade — quem chama (cancel_run) precisa saber.
            return False
        try:
            payload = json.dumps(data)
            envelope = build_relay_envelope(payload, executor_id=executor_id)
            rc = await _get_redis()
            recipients = await rc.publish(_relay_channel(executor_id), envelope)
            if recipients == 0:
                logger.warning(
                    "Executor '%s' online no Redis mas sem relay listener ativo — send_json ignorado.",
                    executor_id,
                )
                return False
            return True
        except Exception as exc:
            logger.error("Erro no relay Redis (send_json) para executor '%s': %s", executor_id, exc)
            return False

    async def disconnect_executor(
        self, executor_id: str, *, code: int = 1000, reason: str = "",
    ) -> bool:
        """Forca o fechamento do WebSocket do executor.

        Se o WS estiver neste worker: fecha direto + unregister local.
        Se estiver em outro worker: publica marker '__internal__.close' no
        relay Redis; o listener detecta o marker (nao encaminha ao cliente)
        e fecha o WS local.

        Diferente do send_json com control message (que confia no cliente
        para sair sozinho), este metodo garante o kick mesmo se o cliente
        estiver com bug ou versao antiga que ignora control.
        """
        conn = self._connections.get(executor_id)

        # Caminho direto.
        if conn is not None:
            try:
                await fechar_ws_do_executor(conn.websocket, code=code, reason=reason)
            except Exception as exc:
                logger.warning("Falha ao fechar WS local do executor '%s': %s", executor_id, exc)
            await self.unregister(executor_id)
            return True

        # Caminho relay.
        if not await _redis_check_presence(executor_id):
            return False
        try:
            # Marker '__internal__' e removido pelo listener antes de
            # qualquer send_text — cliente jamais ve esse payload.
            payload = json.dumps({
                "__internal__": {"close": {"code": code, "reason": reason}},
            })
            envelope = build_relay_envelope(payload, executor_id=executor_id)
            rc = await _get_redis()
            recipients = await rc.publish(_relay_channel(executor_id), envelope)
            if recipients == 0:
                logger.warning(
                    "Executor '%s' online no Redis mas sem relay listener ativo — disconnect ignorado.",
                    executor_id,
                )
                return False
            return True
        except Exception as exc:
            logger.error("Erro no relay Redis (disconnect) para executor '%s': %s", executor_id, exc)
            return False


# Instância singleton — importada pelos routers e services
executor_registry = ExecutorConnectionRegistry()


def ip_do_websocket(ws) -> Optional[str]:
    """IP real do executor na ponta deste WebSocket.

    Atras do Traefik, `ws.client.host` e o IP do proxy para TODOS os
    executores — `RunMetrics.executor_ip` registrava o mesmo endereco para a
    frota inteira. `get_client_ip` so confia no X-Forwarded-For quando o peer e
    um proxy listado em TRUSTED_PROXIES.

    Sem peer, None: preserva o NULL da coluna — "unknown" seria pior que
    ausente porque parece um valor.
    """
    from app.core.trusted_proxy import get_client_ip
    return get_client_ip(ws.client.host, ws.headers.get("x-forwarded-for")) if ws.client else None


# ── Monitor de ACKs atrasados ─────────────────────────────────────────────────
# Loga warnings periódicos para operador. Lançado no lifespan do app
# (app/main.py). Em deploys multi-worker, todos os workers entram aqui mas
# apenas o que adquirir o lock distribuído por ciclo emite o log — evita
# multiplicar warnings em N workers. TTL automático no Redis cuida do GC.

_ACK_MONITOR_INTERVAL = 30.0    # segundos entre varreduras


async def overdue_acks_monitor() -> None:
    """Varre periodicamente jobs sem ACK e alerta no log. Cancele no shutdown."""
    worker_token = f"{os.getpid()}-{id(executor_registry)}"
    try:
        while True:
            await asyncio.sleep(_ACK_MONITOR_INTERVAL)
            # Lock distribuído: só um worker loga por ciclo. TTL pouco menor
            # que o intervalo evita janelas em que ninguém pega o lock.
            try:
                rc = await _get_redis()
                got_lock = await rc.set(
                    _ACK_MONITOR_LOCK_KEY,
                    worker_token,
                    nx=True,
                    ex=int(_ACK_MONITOR_INTERVAL) - 5,
                )
            except Exception as exc:
                logger.warning("Redis: falha ao adquirir lock do ACK monitor: %s", exc)
                await _reset_redis_singleton()
                continue
            if not got_lock:
                continue
            items = await executor_registry.overdue_acks()
            if items:
                sample = [(jid[:8], aid[:8], round(e, 1)) for jid, aid, e in items[:5]]
                logger.warning(
                    "ACK overdue: %d job(s) sem confirmação do executor (amostra: %s)",
                    len(items), sample,
                )
    except asyncio.CancelledError:
        pass
