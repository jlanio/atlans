# executor/event_publisher.py
"""
Publisher de eventos de workflow para o executor externo.

Enfileira eventos numa asyncio.Queue para envio ao servidor via WebSocket
como mensagens do tipo 'node_event'. O servidor então os republica no
Redis pub/sub, conectando ao mesmo pipeline usado pelo Celery.
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any

from flow.utils.publisher.events import (
    WorkflowEventPublisher, KIND_DEBUG, KIND_LIFECYCLE, KIND_STDOUT, LEVEL_INFO,
)

logger = logging.getLogger(__name__)

# Ocupação a partir da qual a fila passa a aceitar SÓ ciclo de vida. A fila é
# compartilhada por todos os jobs e pelo GeoSync: sem prioridade, um nó barulhento
# (print em laço, debug mode) enchia os 500 slots e a vítima do descarte era o
# `completed` de um nó de OUTRO workflow — telemetria que a UI não recupera.
_LIMIAR_PRIORIDADE = 0.8
# Kinds descartáveis sob pressão: são log, não estado do grafo.
_KINDS_DESCARTAVEIS = frozenset({KIND_STDOUT, KIND_DEBUG})


class ColetorDeLifecycle:
    """Guarda o ÚLTIMO lifecycle por (run_id, nó) que não conseguiu ser enviado.

    Existe por causa de DOIS cenários, e o segundo é o mais comum:

      - janela de reconexão: no `ConnectionClosed` o sender para, ninguém drena a
        fila, os jobs seguem produzindo e o que chega é descartado. Como o
        backoff chega a dezenas de segundos, os nós que terminaram nesse
        intervalo ficavam com o spinner de "executando" para sempre — o usuário
        lê isso como "o workflow travou", com o run vivo e correndo bem;
      - PRESSÃO com o WebSocket vivo: um workflow de 300 nós em debug_mode
        produz mais rápido do que o sender envia, a fila de 500 slots enche e o
        `completed` de vários nós cai aqui. Se o coletor só fosse drenado na
        reconexão (que pode nunca acontecer), esses nós ficariam girando até o
        fim do run e as entradas ficariam retidas em memória. Por isso o sender
        também drena assim que a fila folga — ver `_ressincronizar_lifecycle`.

    Coalescer por nó limita a memória a O(nós) em vez de O(eventos), e os eventos
    guardados voltam para a fila como node_events normais. Reenviar um
    `completed` que o servidor já viu é inofensivo (ele ordena por timestamp);
    não reenviar deixa o canvas errado até o fim do run.
    """

    # Teto de segurança para o caso patológico (WS fora por muito tempo, milhares
    # de nós): melhor perder ressincronização do que crescer sem limite.
    _MAX_ENTRADAS = 2_000

    def __init__(self) -> None:
        self._por_no: Dict[tuple, Dict[str, Any]] = {}
        self._avisou_estouro = False

    def registrar(self, event: Dict[str, Any]) -> None:
        """Anota um evento descartado. Ignora tudo que não é ciclo de vida."""
        if not isinstance(event, dict) or event.get("kind") != KIND_LIFECYCLE:
            return
        chave = (event.get("run_id"), event.get("node"))
        anterior = self._por_no.get(chave)
        if anterior is not None:
            # Último status vence — mas só se for mesmo o mais recente: o requeue
            # pode devolver um evento antigo depois de um novo já ter passado.
            if (anterior.get("timestamp") or 0.0) > (event.get("timestamp") or 0.0):
                return
        elif len(self._por_no) >= self._MAX_ENTRADAS:
            if not self._avisou_estouro:
                self._avisou_estouro = True
                logger.error(
                    "Buffer de ressincronizacao cheio (%d nos) — o canvas pode ficar "
                    "desatualizado para os nos que terminarem enquanto o WebSocket "
                    "estiver fora.", self._MAX_ENTRADAS,
                )
            return
        self._por_no[chave] = event

    def drenar(self) -> list:
        """Devolve e esquece o snapshot acumulado.

        Chamado ao (re)conectar E sempre que a fila de eventos folga com a
        sessão viva — ver `ExecutorConnection._ressincronizar_lifecycle`.
        """
        pendentes = list(self._por_no.values())
        self._por_no.clear()
        self._avisou_estouro = False
        return pendentes

    def esquecer_run(self, run_id) -> None:
        """Descarta o lifecycle retido de um run que já terminou.

        Sem isto, um reenvio tardio (reconexão horas depois) ressuscitava as
        entradas por-run dos contadores da fila que `esquecer_run` acabara de
        expurgar — e nada mais as removia. Além de reenviar node_events de runs
        que o servidor já fechou como terminais, e que ele recusa.
        """
        for chave in [k for k in self._por_no if k[0] == run_id]:
            del self._por_no[chave]

    def __len__(self) -> int:
        """Quantos eventos aguardam reenvio. Barato — o sender consulta a cada volta."""
        return len(self._por_no)


class ExecutorEventPublisher(WorkflowEventPublisher):
    """
    Implementação de WorkflowEventPublisher para o executor externo.
    Coloca eventos numa asyncio.Queue — best-effort (descarta se fila cheia).

    Thread-safe: pode ser chamado de threads secundárias (asyncio.to_thread)
    via call_soon_threadsafe, que agenda o enqueue no event loop principal.
    """

    def __init__(self, event_queue: asyncio.Queue):
        self._queue = event_queue
        # Captura o event loop principal no momento da criação do publisher
        self._loop = asyncio.get_running_loop()
        self._descartados_por_pressao = 0

    def _safe_enqueue(self, event: Dict[str, Any]) -> None:
        """Enfileira o evento, com prioridade para o ciclo de vida.

        Duas regras, na ordem: (1) acima de _LIMIAR_PRIORIDADE de ocupação, só
        lifecycle entra — stdout/debug de um nó barulhento não pode custar o
        `completed` de outro job; (2) se ainda assim a fila estiver cheia, o
        lifecycle descartado vai para o coletor, que o reenvia na reconexão.
        """
        if self._e_descartavel_sob_pressao(event):
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._registrar_descarte(event)
            logger.warning(
                "Fila de eventos cheia — evento '%s' do nó '%s' (run=%s) descartado.",
                event.get("status"), event.get("node"), event.get("run_id"),
            )

    def _e_descartavel_sob_pressao(self, event: Dict[str, Any]) -> bool:
        """True quando o evento é log e a fila já está perto do limite."""
        if event.get("kind") not in _KINDS_DESCARTAVEIS:
            return False
        maxsize = getattr(self._queue, "maxsize", 0) or 0
        if not maxsize or self._queue.qsize() < maxsize * _LIMIAR_PRIORIDADE:
            return False
        self._descartados_por_pressao += 1
        if self._descartados_por_pressao % 500 == 1:
            logger.warning(
                "Fila de eventos a %d%% — descartando '%s' do nó '%s' para preservar "
                "o ciclo de vida dos jobs (%d descartado(s) até agora).",
                int(_LIMIAR_PRIORIDADE * 100), event.get("kind"), event.get("node"),
                self._descartados_por_pressao,
            )
        return True

    def _registrar_descarte(self, event: Dict[str, Any]) -> None:
        """Entrega o evento perdido ao coletor da fila, quando houver um."""
        coletor = getattr(self._queue, "coletor", None)
        if coletor is not None:
            coletor.registrar(event)

    def publish_event(
        self,
        run_id: str,
        node: str,
        status: str,
        timestamp: Optional[float] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        kind: str = KIND_LIFECYCLE,
        level: str = LEVEL_INFO,
    ) -> None:
        event: Dict[str, Any] = {
            "run_id": run_id,
            "node": node,
            "kind": kind,
            "level": level,
            "status": status,
            "timestamp": time.time() if timestamp is None else timestamp,
        }
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        if error is not None:
            event["error"] = error
        if extra is not None:
            event["extra"] = extra

        # call_soon_threadsafe é seguro de qualquer thread e também do próprio
        # event loop — agenda _safe_enqueue no loop principal sem bloquear.
        try:
            self._loop.call_soon_threadsafe(self._safe_enqueue, event)
        except RuntimeError:
            # Loop já encerrado (shutdown) — descarta o evento
            logger.debug("Evento descartado (loop encerrado): nó '%s'", event.get("node_id", "?"))
