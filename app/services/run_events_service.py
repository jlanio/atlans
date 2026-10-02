"""Eventos de um run, sem WebSocket.

O laço subscribe → LRANGE → dedup → pub/sub ao vivo nasceu dentro do handler
`/ws/workflow/{run_id}` e só o painel de execução o consumia. O servidor MCP
(docs/specs/mcp-server.md §6.4) precisa da MESMA sequência para o
`run_workflow(wait=true)` — mas sem socket, sem frame e sem browser do outro
lado. Extrair o laço para um gerador de `Lote`s deixa o WS como um cliente
entre outros: ele empacota cada lote no envelope de sempre e o MCP parseia só o
que lhe interessa.

Dois contratos vivem aqui:

- `iter_run_events(run_id)`: replay do histórico + stream ao vivo, em lotes de
  strings JSON CRUAS como saíram do Redis (re-serializar N eventos para que o
  WS os concatene de novo era custo puro); termina no `__workflow_complete__`
  ou no teto de tempo.
- `esperar_run(run_id)`: espera o run ficar terminal combinando os eventos
  (progresso por nó) com um poll de `WorkflowRun.status` — porque nem todo fim
  de run publica `__workflow_complete__` (cancel de run `pending`, despacho
  órfão, "todos recusaram"), e o consumer grava a linha DEPOIS de publicar o
  evento.

E o lado de quem ESCREVE mora aqui também: as chaves do histórico e do canal
(`chave_do_historico`, `canal_do_run`), o pipeline que grava um lote de eventos
(`anexar_eventos`) e o JSON do `__workflow_complete__` (`evento_de_conclusao`)
— usados pelos publicadores do WS do executor e por `publicar_conclusao`.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import Counter, deque
from contextlib import aclosing
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.constants import (
    MAX_EVENTOS_NO_HISTORICO,
    REDIS_TTL_1H,
    WORKFLOW_COMPLETE_NODE,
)
from app.core.db import get_session_async
from app.core.redis import get_redis_pool, new_pubsub_client
from app.core.utils.logger import get_logger
from app.models.workflow_run import WorkflowRun

logger = get_logger(__name__)

# Eventos por LOTE de replay. O ganho que importa é este: um frame WS (ou uma
# iteração do consumidor) por lote em vez de um por evento — a rajada mais densa
# do canal era justamente o instante em que o painel precisa aparecer. A
# LEITURA, porém, é uma só (ver `_ler_historico`): paginar o LRANGE por índice
# absoluto perdia eventos, porque o publicador faz LTRIM(-5000,-1) a cada lote e
# a lista desliza entre as páginas.
_REPLAY_CHUNK = 500

# Quantos RAWs do fim do replay ficam memorizados para deduplicar contra o
# stream ao vivo. A janela real de duplicação é o intervalo entre o SUBSCRIBE e
# o LRANGE (um round-trip), então este teto é folgado de sobra; ele existe só
# para o consumo de memória não depender do tamanho do histórico.
_DEDUP_TAIL = 500

# Buffer entre o pub/sub e o consumidor (socket do browser, tool do MCP). Sem
# ele, um consumidor lento bloqueia o laço que drena o pub/sub; o buffer de
# saída do assinante cresce até o `client-output-buffer-limit pubsub` e o Redis
# DESCONECTA o assinante — o painel para de receber no meio do run, sem erro e
# sem toast.
_QUEUE_MAXSIZE = 500

# Intervalo do heartbeat do stream ao vivo. Se o canal fica quieto por este
# tempo (um nó pesado e demorado, sem stdout), o gerador entrega um lote VAZIO
# só para o consumidor manter tráfego na conexão. Um WebSocket ocioso é
# derrubado em silêncio pelo Safari (e por proxies/LB com idle timeout) SEM
# disparar `onclose` no cliente — então um nó longo matava a conexão e o painel
# girava para sempre. O valor fica confortavelmente abaixo dos idle timeouts
# típicos (30-60s), e a perda de dados do MR de desempenho (stdout coalescido/
# descartável) foi o que passou a deixar o canal mudo tempo bastante para isso
# acontecer.
_HEARTBEAT_S = 20.0

# Marcadores de evento descartável quando a fila enche. `json.dumps` do
# publicador usa separadores com espaço, mas aceitamos as duas grafias para não
# depender disso. Qualquer evento que NÃO case aqui conta como ciclo de vida e
# é preservado — errar para o lado de guardar é o certo.
_DROPPABLE_MARKERS = (
    '"kind": "stdout"', '"kind":"stdout"',
    '"kind": "debug"',  '"kind":"debug"',
)

# Depois do `__workflow_complete__` ao vivo a linha de `workflow_runs` ainda
# pode estar não-terminal: o consumer publica o evento e só então grava o
# status. Este é o teto (e o passo) do poll curto que fecha essa janela; passar
# dele significa consumer parado, e devolvemos o que a linha diz.
_POLL_POS_COMPLETE_MAX_S = 10.0
_POLL_POS_COMPLETE_S = 0.5

# Falhas CONSECUTIVAS toleradas no poll de `WorkflowRun.status` antes de a
# espera desistir. Um checkout de conexão que estourou o timeout do pool, um
# `SQLAlchemyError` de conexão reciclada ou um blip de rede são transitórios: a
# próxima tentativa, `poll_s` depois, costuma passar. Derrubar a espera inteira
# na primeira delas — com o canal de eventos intacto, entregando progresso —
# trocava um soluço do banco por um erro na cara de quem chamou. O contador
# zera a cada leitura bem-sucedida, então só uma indisponibilidade real (três
# seguidas) propaga.
_POLL_FALHAS_CONSECUTIVAS_MAX = 3

# O que conta como falha TRANSITÓRIA do poll. `asyncio.TimeoutError` cobre o
# checkout do pool que estourou (até o 3.10 era uma classe à parte de
# `TimeoutError`; do 3.11 em diante é o mesmo, e os dois ficam por clareza);
# `OSError` é o socket do banco caindo.
# `CancelledError` NÃO entra: herda de `BaseException` e precisa continuar
# subindo para cancelar a task.
_ERROS_POLL_TRANSITORIOS = (SQLAlchemyError, OSError, asyncio.TimeoutError, TimeoutError)

# Vocabulário TERMINAL de `WorkflowRun.status` — o mesmo que
# `executor_ws_router` usa para não regredir um run já fechado.
_STATUS_TERMINAIS = frozenset({"success", "failed", "cancelled"})


# ── Onde vivem os eventos de um run ──────────────────────────────────────────
#
# As duas chaves eram montadas à mão em seis pontos (quatro publicadores, dois
# leitores) e o pipeline de escrita estava copiado em quatro: uma cópia que
# divergisse na grafia, no teto ou no TTL não quebrava nada na hora — o painel
# só deixava de ver o evento.


def chave_do_historico(run_id: str) -> str:
    """LIST com os eventos do run: o replay de quem abre o painel depois."""
    return f"workflow:{run_id}:history"


def canal_do_run(run_id: str) -> str:
    """Canal pub/sub dos eventos do run, ao vivo."""
    return f"workflow:{run_id}:events"


def anexar_eventos(pipe, run_id: str, payloads: list[str]) -> None:
    """Enfileira no `pipe` a gravação de `payloads` (JSON prontos) no run.

    Histórico ANTES do canal e no mesmo pipeline: é o que faz os duplicados da
    fronteira replay↔ao vivo serem um prefixo do stream (ver
    `_stream_ao_vivo`). O `ltrim` segura o teto de `MAX_EVENTOS_NO_HISTORICO` e
    o `expire` renova o TTL a cada escrita.

    O pipeline é de quem chama, que também o executa: é assim que o run
    inconclusivo grava o evento no MESMO round-trip em que fecha o run, e que
    um lote de node_events de vários runs sai de uma vez.
    """
    historico = chave_do_historico(run_id)
    pipe.rpush(historico, *payloads)
    pipe.ltrim(historico, -MAX_EVENTOS_NO_HISTORICO, -1)
    pipe.expire(historico, REDIS_TTL_1H)
    canal = canal_do_run(run_id)
    for payload in payloads:
        pipe.publish(canal, payload)


# `duration_ms` AUSENTE não é o mesmo que `None`. O fechamento pelo servidor
# (`publicar_conclusao`) não mede duração e nunca publicou a chave; o
# job_result e o run inconclusivo sempre a publicaram, nula quando não há
# início conhecido. Quem lê trata as duas formas igual (`?? null` no painel),
# então cada caminho segue publicando o que publicava.
_SEM_DURACAO = object()


def evento_de_conclusao(
    run_id: str,
    status: str,
    *,
    erro: str | None = None,
    extra: dict | None = None,
    duration_ms=_SEM_DURACAO,
    timestamp: float | None = None,
) -> str:
    """O JSON do `__workflow_complete__`, pronto para `anexar_eventos`.

    `status` é o que o painel mostra (`completed`, `failed`, `cancelled`); o
    nível sai dele — `error` só na falha, porque cancelar não é erro. `extra`
    leva a taxonomia de uma falha. `timestamp` é agora, a não ser que quem
    chama já tenha carimbado o fim em outro lugar e precise do MESMO instante.
    """
    evento = {
        "run_id":    run_id,
        "node":      WORKFLOW_COMPLETE_NODE,
        "kind":      "lifecycle",
        "level":     "error" if status == "failed" else "info",
        "status":    status,
        "timestamp": time.time() if timestamp is None else timestamp,
    }
    if duration_ms is not _SEM_DURACAO:
        evento["duration_ms"] = duration_ms
    evento["error"] = erro
    evento["extra"] = extra
    return json.dumps(evento)


class RunEventsUnavailable(Exception):
    """O Redis não respondeu ao subscribe/LRANGE: não há como acompanhar eventos.

    É uma exceção própria (e não o `RuntimeError`/`RedisError` de origem) para
    que cada consumidor decida o seu fallback: o WS fecha com 4500, o
    `esperar_run` cai para o poll de banco.
    """


@dataclass(frozen=True)
class Lote:
    """Um lote de eventos como o consumidor os recebe.

    `eventos` são as strings JSON CRUAS do Redis, na ordem de publicação.
    `dropped` é quantos eventos foram descartados do buffer desde o lote
    anterior (vai sempre, 0 inclusive, para quem soma não checar `None`).
    `heartbeat=True` marca um lote vazio emitido só porque o canal ficou quieto.
    `completo=True` marca o ÚLTIMO lote: o `__workflow_complete__` está nele
    (ou num lote anterior do mesmo replay) e o gerador encerra em seguida.
    """

    eventos: list[str]
    dropped: int
    heartbeat: bool
    completo: bool


def _is_droppable(raw: str) -> bool:
    return any(marker in raw for marker in _DROPPABLE_MARKERS)


def _is_complete_event(raw: str) -> bool:
    """True se o RAW é o evento `__workflow_complete__`.

    O teste de substring é o caminho rápido (evita um json.loads por evento);
    o parse só roda no candidato, porque um print() do usuário contendo a
    string do marcador truncaria o replay de um run que ainda está rodando.
    """
    if WORKFLOW_COMPLETE_NODE not in raw:
        return False
    try:
        return json.loads(raw).get("node") == WORKFLOW_COMPLETE_NODE
    except (ValueError, AttributeError):
        return False


class _EventBuffer:
    """Fila entre o produtor (pub/sub) e o consumidor (socket, tool).

    O produtor nunca bloqueia: quando enche, descarta o stdout/debug MAIS ANTIGO
    e preserva o ciclo de vida — é o ciclo de vida que pinta o canvas. O
    `__workflow_complete__` nunca é descartado.
    """

    def __init__(self, maxsize: int):
        self._items: deque[tuple[bool, str]] = deque()
        self._maxsize = maxsize
        self._ready = asyncio.Event()
        self._dropped = 0
        # Contado À PARTE do descarte de telemetria: são falhas de gravidade
        # completamente diferente, e somá-las escondia a grave dentro da banal.
        self._dropped_lifecycle = 0
        self.closed = False  # o produtor já viu o __workflow_complete__

    def push(self, raw: str, *, droppable: bool) -> None:
        if len(self._items) >= self._maxsize:
            self._evict()
        self._items.append((droppable, raw))
        self._ready.set()

    def _evict(self) -> None:
        for index, (droppable, _) in enumerate(self._items):
            if droppable:
                del self._items[index]
                self._dropped += 1
                return
        # Fila inteira de ciclo de vida: derruba o mais antigo que não seja o
        # marcador de fim. Perder um evento é ruim; parar de drenar o pub/sub
        # faz o Redis derrubar o assinante e perde TODOS os seguintes.
        #
        # ESTE é o único ponto do canal servidor→consumidor que ainda perde
        # estado do grafo, e cada ocorrência deixa um nó girando para sempre no
        # canvas do usuário. Por isso é contado separado e sai como ERROR: se
        # aparecer no log, está provado que a fila entre o pub/sub e o socket
        # precisa deixar de ser a última linha de defesa (back-pressure com
        # replay).
        for index, (_, raw) in enumerate(self._items):
            if not _is_complete_event(raw):
                del self._items[index]
                self._dropped += 1
                self._dropped_lifecycle += 1
                return

    def take_dropped_lifecycle(self) -> int:
        perdidos, self._dropped_lifecycle = self._dropped_lifecycle, 0
        return perdidos

    def close(self) -> None:
        self.closed = True
        self._ready.set()

    def take_dropped(self) -> int:
        dropped, self._dropped = self._dropped, 0
        return dropped

    @property
    def empty(self) -> bool:
        return not self._items

    async def drain(self) -> list[str]:
        """Espera haver evento (ou o fim do run) e devolve TUDO acumulado.

        Agregar antes de cada entrega é o coalescing: consumidor lento passa a
        receber menos lotes, maiores, em vez de travar o assinante do Redis.
        """
        while not self._items and not self.closed:
            self._ready.clear()
            await self._ready.wait()
        events = [raw for _, raw in self._items]
        self._items.clear()
        return events


async def _ler_historico(run_id: str, history_key: str) -> tuple[list[str], bool]:
    """Snapshot do histórico, cortado no 1º `__workflow_complete__`.

    Devolve (historico, run_ja_terminou).

    UMA leitura. O publicador roda `rpush + ltrim(-5000,-1)` a cada lote, então
    a lista desliza pela CABEÇA enquanto o replay acontece: paginar por índice
    absoluto (`lrange 0..499`, depois `500..999`) fazia os eventos que
    escorregaram para dentro da página já lida nunca serem lidos por página
    nenhuma — e, por serem anteriores ao subscribe, o pub/sub também não os
    reentregava. Um `completed` perdido assim deixa o nó rodando no canvas para
    sempre. O `LRANGE 0..-1` é um snapshot atômico e imune a isso; o ganho de
    menos lotes fica de pé porque a PAGINAÇÃO DA ENTREGA continua.
    """
    rc = get_redis_pool()
    history = await rc.lrange(history_key, 0, -1)
    for index, raw in enumerate(history):
        if _is_complete_event(raw):
            # Corta no marcador: o que vier depois é de outro ciclo e não deve
            # reanimar um run encerrado.
            return history[: index + 1], True
    return history, False


async def iter_run_events(
    run_id: str,
    *,
    timeout_s: float,
    heartbeat_s: float = _HEARTBEAT_S,
    chunk: int = _REPLAY_CHUNK,
) -> AsyncIterator[Lote]:
    """Replay do histórico e depois o stream ao vivo, em `Lote`s.

    Ordem obrigatória: SUBSCRIBE antes do LRANGE, para não perder o que é
    publicado enquanto o histórico é lido; o que cair nas duas fontes é
    deduplicado pela cauda do replay (ver `pendentes`).

    Encerra (1) ao fim do replay, se o histórico já contém o
    `__workflow_complete__` (último lote com `completo=True`); (2) no
    `__workflow_complete__` ao vivo (idem); (3) quando `timeout_s` passa, sem
    lote de conclusão — é o consumidor que decide o que um run ainda aberto
    significa. Levanta `RunEventsUnavailable` se o Redis falha no subscribe ou
    no LRANGE; a conexão dedicada do assinante é fechada em qualquer saída.
    """
    channel = canal_do_run(run_id)
    history_key = chave_do_historico(run_id)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s

    # Conexão dedicada para o subscribe (ver `new_pubsub_client`): ela fica presa
    # o run inteiro, e vir de um pool com teto era o que fazia o N-ésimo painel
    # aberto morrer com MaxConnectionsError.
    sub_client = new_pubsub_client()
    try:
        async with sub_client.pubsub() as pubsub:
            try:
                # Inscreve ANTES de ler o histórico para não perder eventos que
                # chegam enquanto o replay acontece.
                await pubsub.subscribe(channel)
                history, already_complete = await _ler_historico(run_id, history_key)
            except (RuntimeError, RedisError, OSError) as exc:
                # RuntimeError é o `get_redis_pool()` sem pool (shutdown/rolling
                # deploy, lifespan que não rodou); os outros dois são o Redis
                # fora do ar. Para o consumidor é tudo a mesma coisa: sem
                # eventos.
                raise RunEventsUnavailable(
                    f"Redis indisponível para os eventos do run {run_id}: {exc}"
                ) from exc

            logger.info(
                "Eventos do run %s: replay history=%d eventos", run_id, len(history),
            )
            for start in range(0, len(history), chunk):
                ultimo = start + chunk >= len(history)
                yield Lote(
                    eventos=history[start:start + chunk],
                    dropped=0,
                    heartbeat=False,
                    completo=already_complete and ultimo,
                )
            if already_complete:
                return

            # Cauda do snapshot: tudo publicado entre o SUBSCRIBE e o LRANGE
            # chega também pelo pub/sub e o painel mostraria a mesma linha de
            # print() duas vezes (o cliente reatribui `seq`, então não deduplica
            # sozinho). Contador (e não conjunto) para que N cópias idênticas
            # dentro da janela descartem exatamente N.
            pendentes: Counter | None = Counter(history[-_DEDUP_TAIL:]) if history else None

            # `aclosing`: quem consome pode parar no meio (o WS ao ver a aba
            # fechada, o `esperar_run` no lote de conclusão) e um `break` num
            # `async for` NÃO finaliza o gerador — sem isto, o produtor do
            # pub/sub só seria cancelado quando o coletor de lixo passasse.
            async with aclosing(_stream_ao_vivo(
                pubsub, run_id, pendentes, deadline=deadline, heartbeat_s=heartbeat_s,
            )) as ao_vivo:
                async for lote in ao_vivo:
                    yield lote
            # O unsubscribe/reset fica com o `async with` do pubsub — chamá-lo à
            # mão depois de um cancelamento só arrisca falar numa conexão já
            # derrubada.
    finally:
        await sub_client.aclose()


async def _stream_ao_vivo(
    pubsub,
    run_id: str,
    pendentes: Counter | None,
    *,
    deadline: float,
    heartbeat_s: float,
) -> AsyncIterator[Lote]:
    """Laço ao vivo: produtor pub/sub → fila → lotes para o consumidor.

    Duplicados da fronteira replay↔ao vivo (`pendentes`) são necessariamente um
    PREFIXO do stream (o publicador grava no histórico antes de publicar, na
    mesma pipeline), então na primeira mensagem que não casa desligamos o dedup
    — assim um print() repetido no meio do run, que é legítimo, não é engolido.
    """
    buf = _EventBuffer(_QUEUE_MAXSIZE)
    loop = asyncio.get_running_loop()

    # `completo` só é verdade quando o `__workflow_complete__` passou pelo
    # buffer: o produtor também fecha o buffer quando o pub/sub cai, e nesse
    # caso o gerador termina SEM marcar conclusão — o run pode estar vivo.
    viu_complete = False

    async def produce() -> None:
        nonlocal pendentes, viu_complete
        # O `finally` fecha o buffer em QUALQUER saída (fim do run, erro, Redis
        # derrubando o assinante). Sem ele, uma falha aqui deixaria o consumidor
        # esperando para sempre por um evento que não vem mais.
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message["data"]
                if _is_complete_event(raw):
                    viu_complete = True
                    buf.push(raw, droppable=False)
                    return
                if pendentes is not None:
                    if pendentes.get(raw):
                        pendentes[raw] -= 1
                        continue
                    pendentes = None
                buf.push(raw, droppable=_is_droppable(raw))
        finally:
            buf.close()

    producer = asyncio.create_task(produce())
    try:
        while True:
            restante = deadline - loop.time()
            if restante <= 0:
                return
            try:
                events = await asyncio.wait_for(
                    buf.drain(), timeout=min(heartbeat_s, restante),
                )
            except asyncio.TimeoutError:
                if buf.closed and buf.empty:
                    return
                if deadline - loop.time() <= 0:
                    return
                # Canal quieto além do intervalo: entrega um lote VAZIO. O WS o
                # manda como está para manter tráfego na conexão (o Safari e
                # proxies derrubam WebSocket ocioso sem avisar) e, se o socket
                # já morreu, o próprio send falha e o handler encerra — antes,
                # sem nenhuma escrita durante um nó longo, nem o servidor
                # percebia a queda. `drain()` é seguro de cancelar: nada foi
                # consumido, e o próximo laço recomeça a espera.
                yield Lote(eventos=[], dropped=0, heartbeat=True, completo=False)
                continue
            if events:
                dropped = buf.take_dropped()
                perdidos_lifecycle = buf.take_dropped_lifecycle()
                if perdidos_lifecycle:
                    # ERROR, e separado do aviso de telemetria: cada um destes é
                    # um nó que vai ficar girando para sempre no canvas. A linha
                    # anterior dizia "stdout descartados" para os dois casos, o
                    # que fazia a falha grave passar por ruído de log.
                    logger.error(
                        "Eventos do run %s: %d evento(s) de CICLO DE VIDA descartados "
                        "por saturação do buffer (%d slots) — o canvas do usuário vai "
                        "ficar com nó(s) sem conclusão. Consumidor não acompanha o "
                        "ritmo do run.",
                        run_id, perdidos_lifecycle, _QUEUE_MAXSIZE,
                    )
                if dropped > perdidos_lifecycle:
                    logger.warning(
                        "Eventos do run %s: %d evento(s) de stdout descartados — "
                        "consumidor nao acompanha o ritmo do run.",
                        run_id, dropped - perdidos_lifecycle,
                    )
                # O produtor fecha o buffer no mesmo passo em que empurra o
                # complete, então o lote que o contém já sai marcado.
                completo = viu_complete and buf.closed and buf.empty
                yield Lote(eventos=events, dropped=dropped, heartbeat=False, completo=completo)
            if buf.closed and buf.empty:
                return
    finally:
        # O produtor NÃO participa da espera: ele termina ao ver o
        # `__workflow_complete__`, e o consumidor drena o buffer até o fim antes
        # de chegar aqui — cancelá-lo antes engoliria justamente o último
        # evento, que decide o estado final do painel.
        producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)
        if (
            producer.done()
            and not producer.cancelled()
            and producer.exception() is not None
        ):
            # Erro real do pub/sub tem que subir para o consumidor, não sumir
            # dentro da task.
            raise producer.exception()


# ── Espera pelo fim do run ────────────────────────────────────────────────────


async def ler_status_do_run(db, run_id: str) -> tuple[str | None, WorkflowRun | None]:
    """(status, linha) do run pelo `task_id` — `(None, None)` se não existe."""
    stmt = select(WorkflowRun).where(WorkflowRun.task_id == run_id).limit(1)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        return None, None
    return run.status, run


@dataclass
class ResultadoEspera:
    """O que `esperar_run` devolve.

    `status`/`run` são o que a linha de `workflow_runs` dizia na última leitura
    (podem ser não-terminais em `timed_out`). `concluidos` são nós distintos
    com `completed`/`failed` vistos nos eventos; `eventos_descartados` soma o
    `dropped` dos lotes. `redis_indisponivel=True` diz que só o poll funcionou.

    `concluidos` NÃO é comparável com `total_nos` como "x de N terminaram": nó
    pulado por branch (`run.node_stats[no]["status"] == "skipped"`) e nó que
    nunca chegou a rodar depois de uma falha não publicam evento nenhum, então
    `concluidos < total_nos` ao final é o caso NORMAL de um grafo com desvios.
    O retrato real de quem rodou está em `run.node_stats`; `concluidos` serve
    para progresso incremental, não para conferir completude.

    `viu_complete=True` diz que o `__workflow_complete__` passou pelos eventos,
    isto é, o executor terminou o grafo. Combinado com `status` NÃO terminal
    significa uma coisa só: o run acabou, mas a linha de `workflow_runs` não
    tinha sido gravada nem depois do poll curto de `_POLL_POS_COMPLETE_MAX_S`
    — `run_result_consumer` parado ou muito atrasado. Quem chama deve tratar
    como "terminou, desfecho ainda desconhecido" (e reconsultar depois), nunca
    como "ainda executando".
    """

    status: str | None
    run: WorkflowRun | None
    concluidos: int
    eventos_descartados: int
    timed_out: bool
    redis_indisponivel: bool
    viu_complete: bool = False


ProgressoCallback = Callable[[int, int, str], Awaitable[None]]


def _formatar_duracao(duration_ms) -> str | None:
    try:
        ms = float(duration_ms)
    except (TypeError, ValueError):
        return None
    if ms < 1000:
        return f"{int(ms)} ms"
    return f"{ms / 1000:.1f} s".replace(".", ",")


async def esperar_run(
    run_id: str,
    *,
    timeout_s: float,
    total_nos: int,
    on_progress: ProgressoCallback | None = None,
    poll_s: float = 2.0,
) -> ResultadoEspera:
    """Espera o run terminar, com progresso por nó e o banco como verdade.

    Duas tasks: A consome `iter_run_events` (progresso + fim rápido pelo
    `__workflow_complete__`); B faz poll de `WorkflowRun.status` a cada
    `poll_s` numa sessão própria. Quem terminar primeiro decide:

    - A viu o complete → cancela B e faz um poll CURTO até a linha ficar
      terminal (o consumer grava depois de publicar);
    - B viu status terminal → cancela A. É o único caminho para os fins que
      não publicam evento (cancel de run `pending`, despacho órfão, "todos
      recusaram");
    - A morreu sem complete (Redis fora, assinante derrubado) → só B segue;
    - nenhum dos dois até `timeout_s` → `timed_out=True` com o que a linha diz.

    `total_nos` é só o denominador do progresso entregue a `on_progress` (o
    número de nós da definição). Não espere que o numerador o alcance: nó
    pulado por branch (`node_stats[no]["status"] == "skipped"`) e nó que nunca
    rodou depois de uma falha NÃO publicam evento, então terminar com
    `concluidos < total_nos` é o normal num grafo com desvios — o total real de
    quem rodou vem de `run.node_stats`.

    Falha transitória do poll (checkout do pool estourado, `SQLAlchemyError`,
    `OSError`) não derruba a espera: são toleradas até
    `_POLL_FALHAS_CONSECUTIVAS_MAX` seguidas, com warning; a partir daí (ou ao
    fim do prazo) o erro propaga.

    `on_progress` roda dentro do consumo de eventos: se ele levantar, a exceção
    é logada UMA vez e as notificações param, mas a contagem e a espera seguem
    — um callback quebrado do chamador não pode custar o desfecho do run.

    `ResultadoEspera.viu_complete` distingue os dois "não terminais": sem
    complete o run pode mesmo estar rodando; COM complete e status não terminal
    o run acabou e é a gravação da linha que está atrasada (ver a docstring de
    `ResultadoEspera`).

    O estado da espera e as duas tasks vivem em `_Espera`; aqui fica a ordem.
    """
    espera = _Espera(
        run_id, timeout_s=timeout_s, total_nos=total_nos,
        on_progress=on_progress, poll_s=poll_s,
    )
    status, run = await espera.disputar()
    if espera.viu_complete and status not in _STATUS_TERMINAIS:
        # O consumer publica o evento e SÓ DEPOIS grava a linha: poll curto para
        # não devolver "running" de um run que acabou de terminar.
        status, run = await espera.poll_pos_complete(status, run)
    return espera.resultado(status, run)


class _Espera:
    """Uma chamada de `esperar_run`: o que as duas tasks compartilham.

    A task A (`consumir_eventos`) conta o progresso e vê o fim rápido pelo
    `__workflow_complete__`; a B (`poll_ate_terminal`) lê `WorkflowRun.status`
    até o terminal ou o prazo. `disputar` corre as duas e fica com o desfecho
    de quem vale; `poll_pos_complete` e `resultado` fecham a espera.
    """

    def __init__(
        self,
        run_id: str,
        *,
        timeout_s: float,
        total_nos: int,
        on_progress: ProgressoCallback | None,
        poll_s: float,
    ):
        self.run_id = run_id
        self.total_nos = total_nos
        self.on_progress = on_progress
        self.poll_s = poll_s
        self.loop = asyncio.get_running_loop()
        self.deadline = self.loop.time() + timeout_s
        self.concluidos: set[str] = set()
        self.descartados = 0
        # Desligado na primeira exceção do callback do chamador (ver `absorver_lote`).
        self.notificar = on_progress is not None
        # Última leitura do banco que chegou ao fim, mesmo que a task do poll tenha
        # sido cancelada logo depois (ver `ler_status_inteiro`).
        self.ultima_leitura: tuple[str | None, WorkflowRun | None] | None = None
        self.redis_indisponivel = False
        self.viu_complete = False

    def restante(self) -> float:
        return self.deadline - self.loop.time()

    # ── A: eventos ────────────────────────────────────────────────────────────

    async def absorver_lote(self, lote: Lote) -> None:
        """Conta os nós que terminaram e avisa o chamador de cada um.

        Só ciclo de vida conta: stdout/debug, JSON inválido, evento sem nó, o
        próprio `__workflow_complete__` e status que não é de fim ficam de fora,
        e um nó conta uma vez só.
        """
        self.descartados += lote.dropped
        for raw in lote.eventos:
            # stdout/debug não carregam ciclo de vida: nem parse merecem.
            if _is_droppable(raw):
                continue
            try:
                ev = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(ev, dict) or ev.get("kind", "lifecycle") != "lifecycle":
                continue
            node, status = ev.get("node"), ev.get("status")
            if node == WORKFLOW_COMPLETE_NODE or not node:
                continue
            if status not in ("completed", "failed") or node in self.concluidos:
                continue
            self.concluidos.add(node)
            if self.notificar:
                msg = f"{node}: {status}"
                duracao = _formatar_duracao(ev.get("duration_ms"))
                if duracao:
                    msg = f"{msg} ({duracao})"
                try:
                    await self.on_progress(len(self.concluidos), self.total_nos, msg)
                except Exception as exc:
                    # O callback é do CHAMADOR (uma notificação de progresso do
                    # MCP, um send num socket que já morreu): quebrar aqui
                    # matava o consumo dos eventos, e com ele a contagem e o
                    # fim rápido pelo `__workflow_complete__` — a espera inteira
                    # passava a depender do poll. Avisa uma vez, para de
                    # notificar e continua absorvendo.
                    self.notificar = False
                    logger.warning(
                        "Progresso do run %s: callback falhou (%s); seguindo sem "
                        "notificar.", self.run_id, exc, exc_info=exc,
                    )

    async def consumir_eventos(self) -> bool:
        """True se o `__workflow_complete__` passou pelos eventos."""
        eventos = iter_run_events(self.run_id, timeout_s=max(self.restante(), 0.0))
        # `aclosing`: sair do laço no lote de conclusão não finaliza o gerador
        # sozinho, e é o `finally` dele que fecha a conexão do assinante.
        async with aclosing(eventos):
            async for lote in eventos:
                await self.absorver_lote(lote)
                if lote.completo:
                    return True
        return False

    # ── B: poll do banco ──────────────────────────────────────────────────────

    async def ler_status(self) -> tuple[str | None, WorkflowRun | None]:
        async with get_session_async() as db:
            status, run = await ler_status_do_run(db, self.run_id)
            if run is not None:
                # `get_session_async` faz rollback ao sair, e o rollback EXPIRA
                # tudo que a sessão carregou: quem lesse `run.node_stats` depois
                # levaria DetachedInstanceError. Desprendida antes, a linha fica
                # com os atributos já carregados e sem sessão para refrescar.
                db.expunge(run)
            return status, run

    async def ler_status_inteiro(self) -> tuple[str | None, WorkflowRun | None]:
        """`ler_status` que um cancelamento não interrompe no meio.

        A task do poll é cancelada assim que os eventos veem o complete — e o
        cancelamento cai onde ela estiver, inclusive no meio de um statement.
        Um driver interrompido ali fica com a conexão em estado indefinido
        (o pool a invalida, no melhor caso). O `shield` deixa a leitura em
        curso terminar e fechar a sessão; o cancelamento sobe logo depois.

        A leitura que sobrevive ao cancelamento é GUARDADA em `ultima_leitura`:
        ela custou um round-trip ao banco e é, por definição, a mais recente
        que existe. Descartá-la para logo em seguida abrir outra sessão e
        perguntar a mesma coisa dobrava a latência do caminho mais comum (os
        eventos veem o complete enquanto o poll já está lendo).
        """
        leitura = asyncio.ensure_future(self.ler_status())
        try:
            self.ultima_leitura = await asyncio.shield(leitura)
            return self.ultima_leitura
        except asyncio.CancelledError:
            await asyncio.gather(leitura, return_exceptions=True)
            if leitura.done() and not leitura.cancelled() and leitura.exception() is None:
                self.ultima_leitura = leitura.result()
            raise

    async def poll_ate_terminal(self) -> tuple[str | None, WorkflowRun | None]:
        """Poll até status terminal ou até o prazo; devolve a última leitura.

        Falha do banco aqui é quase sempre transitória (pool sem conexão livre
        no pico, conexão reciclada, blip de rede) e o canal de eventos segue
        entregando progresso: derrubar a espera na primeira delas trocava um
        soluço por um erro. Tolera até `_POLL_FALHAS_CONSECUTIVAS_MAX` seguidas
        — o contador zera em toda leitura boa — e só propaga ao estourar esse
        teto ou o prazo.
        """
        falhas = 0
        while True:
            try:
                status, run = await self.ler_status_inteiro()
            except _ERROS_POLL_TRANSITORIOS as exc:
                falhas += 1
                restante = self.restante()
                if falhas >= _POLL_FALHAS_CONSECUTIVAS_MAX or restante <= 0:
                    raise
                logger.warning(
                    "Poll do run %s falhou (%d/%d): %s",
                    self.run_id, falhas, _POLL_FALHAS_CONSECUTIVAS_MAX, exc,
                )
                await asyncio.sleep(min(self.poll_s, restante))
                continue
            falhas = 0
            if status in _STATUS_TERMINAIS:
                return status, run
            restante = self.restante()
            if restante <= 0:
                return status, run
            await asyncio.sleep(min(self.poll_s, restante))

    # ── A disputa e o fim ─────────────────────────────────────────────────────

    async def disputar(self) -> tuple[str | None, WorkflowRun | None]:
        """Corre A e B e devolve o `(status, linha)` de quem decide.

        Quem termina primeiro cancela a outra; A sem complete (Redis fora,
        assinante derrubado) deixa B seguir sozinha até o terminal ou o prazo.
        """
        tarefa_eventos = asyncio.create_task(self.consumir_eventos())
        tarefa_poll = asyncio.create_task(self.poll_ate_terminal())
        pendentes = {tarefa_eventos, tarefa_poll}
        try:
            while pendentes:
                done, pendentes = await asyncio.wait(pendentes, return_when=asyncio.FIRST_COMPLETED)
                if tarefa_eventos not in done:
                    # Só B terminou (status terminal ou prazo): o desfecho é dele.
                    break
                # A terminou — sozinha ou no MESMO passo que B. Ler o resultado dela
                # aqui, ANTES de qualquer `break`, é o que garante `viu_complete`
                # fiel: com as duas no mesmo `done`, sair direto pelo poll perdia a
                # informação de que o grafo tinha terminado.
                self.anotar_fim_dos_eventos(tarefa_eventos)
                if self.viu_complete or tarefa_poll in done:
                    break
                # Sem complete: o poll continua sozinho até o terminal ou o prazo.
        finally:
            for tarefa in (tarefa_eventos, tarefa_poll):
                tarefa.cancel()
            await asyncio.gather(tarefa_eventos, tarefa_poll, return_exceptions=True)

        if tarefa_poll.done() and not tarefa_poll.cancelled():
            # `.result()` repropaga a desistência do poll (falhas consecutivas além
            # do teto): sem banco não há desfecho para devolver.
            return tarefa_poll.result()
        if self.ultima_leitura is not None:
            # O poll foi cancelado (os eventos viram o complete), mas a leitura que
            # ele tinha em curso chegou ao fim — é a mais fresca que existe. Abrir
            # outra sessão para perguntar o mesmo custava um round-trip inteiro no
            # caminho MAIS comum. Se ela ainda não for terminal, o poll curto
            # (`poll_pos_complete`) continua de onde ela parou.
            return self.ultima_leitura
        return await self.ler_status()

    def anotar_fim_dos_eventos(self, tarefa: asyncio.Task) -> None:
        """Como A terminou: com o complete, sem Redis ou com erro."""
        exc = tarefa.exception()
        if exc is None:
            self.viu_complete = tarefa.result()
        elif isinstance(exc, RunEventsUnavailable):
            self.redis_indisponivel = True
            logger.warning(
                "Eventos do run %s indisponíveis; seguindo só pelo poll: %s", self.run_id, exc,
            )
        else:
            # O poll é a fonte de verdade; um erro no canal de eventos não
            # pode derrubar a espera inteira.
            logger.error(
                "Erro ao acompanhar eventos do run %s; seguindo só pelo poll: %s",
                self.run_id, exc, exc_info=exc,
            )

    async def poll_pos_complete(
        self, status: str | None, run: WorkflowRun | None,
    ) -> tuple[str | None, WorkflowRun | None]:
        """Poll curto, até `_POLL_POS_COMPLETE_MAX_S`, pela linha terminal.

        Passar do teto significa consumer parado: fica o que a linha diz, e
        `viu_complete` conta a quem chamou que o grafo terminou.
        """
        fim = self.loop.time() + _POLL_POS_COMPLETE_MAX_S
        falhas = 0
        while status not in _STATUS_TERMINAIS and self.loop.time() < fim:
            await asyncio.sleep(_POLL_POS_COMPLETE_S)
            try:
                status, run = await self.ler_status()
            except _ERROS_POLL_TRANSITORIOS as exc:
                # Mesmo raciocínio do poll longo, e aqui a aposta é ainda
                # melhor: o grafo comprovadamente terminou, só falta a linha.
                # Desistir por um soluço do banco seria jogar fora a única
                # informação que a espera já tem.
                falhas += 1
                if falhas >= _POLL_FALHAS_CONSECUTIVAS_MAX:
                    raise
                logger.warning(
                    "Poll pós-complete do run %s falhou (%d/%d): %s",
                    self.run_id, falhas, _POLL_FALHAS_CONSECUTIVAS_MAX, exc,
                )
                continue
            falhas = 0
        return status, run

    def resultado(self, status: str | None, run: WorkflowRun | None) -> ResultadoEspera:
        return ResultadoEspera(
            status=status,
            run=run,
            concluidos=len(self.concluidos),
            eventos_descartados=self.descartados,
            timed_out=status not in _STATUS_TERMINAIS and self.loop.time() >= self.deadline,
            redis_indisponivel=self.redis_indisponivel,
            viu_complete=self.viu_complete,
        )


# ── Conclusão publicada pelo servidor ────────────────────────────────────────

# Runs por pipeline. O bloco limita o buffer de comandos quando um incidente
# fecha centenas de runs de uma vez.
_BLOCO_DE_PUBLICACAO = 200


async def publicar_conclusao(
    run_ids: list[str], *, status: str, mensagem: str | None, extra: dict | None = None,
) -> None:
    """Publica o `__workflow_complete__` de runs que o SERVIDOR fechou.

    Quem fecha um run sem passar pelo job_result — órfão, não entregue, perdido
    na reconciliação, cancelado antes de chegar ao executor ou com o executor
    fora do ar — não publicava a conclusão: o painel aberto seguia girando e o
    botão de cancelar ficava em "aguardando o executor" para sempre. O evento é
    o mesmo `evento_de_conclusao` do job_result, sem `duration_ms` (o servidor
    não mede a duração de quem ele fecha) e com UM instante para o bloco todo.

    Um pipeline por bloco em vez de 4 round-trips POR RUN: quando um executor
    com 50 runs cai, eram 200 idas ao Redis em série e os painéis abertos
    fechavam em cascata lenta, um a um.
    """
    if not run_ids:
        return
    rc = get_redis_pool()
    ts = time.time()
    for inicio in range(0, len(run_ids), _BLOCO_DE_PUBLICACAO):
        bloco = run_ids[inicio:inicio + _BLOCO_DE_PUBLICACAO]
        async with rc.pipeline(transaction=False) as pipe:
            for run_id in bloco:
                evento = evento_de_conclusao(
                    run_id, status, erro=mensagem, extra=extra, timestamp=ts,
                )
                anexar_eventos(pipe, run_id, [evento])
            await pipe.execute()
