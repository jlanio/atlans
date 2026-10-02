# executor/dashboard/json_runtime.py
"""
Canal de eventos estruturados para um supervisor (o app desktop).

Substitui, para consumidor que nao e humano, o painel `rich`: em vez de desenhar
o `Snapshot`, serializa e emite uma linha JSON por evento no **stdout**.

Por que stdout, e nao um socket local: `logging_setup` manda o log humano para
**stderr** (`logging.StreamHandler()` sem argumento), entao stdout ja esta livre
e nao ha refactor de logging a fazer. Um servidor HTTP/WS em 127.0.0.1 exigiria
porta, autenticacao e firewall, e ficaria legivel por qualquer processo do
usuario — carregando estatisticas e tail de log.

Por que NAO ler o arquivo de log: era o que o `agent-desktop` removido fazia,
derivando estado com regex sobre mensagem em portugues. E o que o cabecalho de
`executor/stats.py` proibe, e o motivo pelo qual aquele app apodreceu.

## Formato

Uma linha JSON por evento, terminada em `\\n`, SEMPRE comecando por `{"v":1,`.
O prefixo e framing: o leitor descarta qualquer linha que nao case, o que cobre
um `print()` acidental de um no de workflow caindo no mesmo stdout.

    {"v":1,"t":"hello",...}       uma vez, no start
    {"v":1,"t":"state",...}       fase do boot / shutdown
    {"v":1,"t":"snapshot",...}    periodico
    {"v":1,"t":"job"|"sync"|"conn",...}   imediatos, via observer do stats
    {"v":1,"t":"log",...}         WARNING+
    {"v":1,"t":"ack",...}         resposta a comando

## Comandos (stdin)

Uma linha JSON por comando, espelhando as teclas do painel `rich`
(`runtime.py::_tecla`) — a GUI ganha exatamente a superficie de controle que o
operador do terminal tem, nem mais nem menos.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from collections import deque

from executor.dashboard import tick

logger = logging.getLogger("executor.dashboard")

# Versao do formato, o `v` do framing. Subir aqui exige atualizar o PROTOCOLO
# de desktop/src/shared/events.ts.
PROTOCOLO = 1
_PREFIXO = '{"v":%d,' % PROTOCOLO

# Eventos represados enquanto o consumidor nao le. Ao encher, o mais ANTIGO cai
# (deque com maxlen). E a escolha certa para snapshots, que se substituem: o
# consumidor quer o estado atual, nao o de 40 s atras.
_BUFFER_MAX = 256

# Teto de uma linha serializada. Nenhum evento pode virar uma linha de megabytes
# que trava o parser do outro lado.
_LINHA_MAX = 512 * 1024

# Campos do `Snapshot` que existem para o painel `rich` desenhar e que este
# runtime NAO emite. `log_tail` sao ate 200 linhas de log reenviadas inteiras a
# cada segundo, sendo que o supervisor tem canal de log proprio, incremental e
# com `seq` (eventos `log`) — o tail so repetiria o que ele ja recebeu.
# `system` e hardware, que nao muda entre um tick e o seguinte.
#
# Nenhum dos dois e lido do outro lado, e ambos atravessavam o pipe, o
# `JSON.parse` e um structured clone por janela, a 1 Hz, para serem descartados:
# dezenas de KB por segundo com o executor OCIOSO. `log_warn_count` e
# `log_error_count` ficam — sao dois inteiros e a GUI mostra os contadores.
#
# Se alguma tela precisar de `system` um dia, o lugar dele e o `hello`, que sai
# uma vez, e nao um evento periodico.
_SO_DO_PAINEL = ("log_tail", "system")

# Espelham 1:1 as teclas do painel rich. `toggle_debug` se chama assim, e nao
# `set_debug`, porque `logging_setup.alternar_debug()` alterna — prometer um
# setter idempotente sobre um toggle daria a um retry a semantica oposta.
COMANDOS = ("shutdown", "reconnect", "reset_stats", "toggle_debug", "ping", "sync_now")


class JsonRuntime:
    """Emite NDJSON no stdout e le comandos do stdin.

    Mesma interface de ciclo de vida do `DashboardRuntime` (`start`, `stop`,
    `close_live`) para que `dashboard.start()` possa devolver um ou outro e o
    `main.py` nao precise saber qual.
    """

    def __init__(self, stats, *, capacity_source, result_queue, intervalo: float,
                 tail_handler: logging.Handler | None = None,
                 ao_sair=None, ao_reconectar=None, ao_sincronizar=None):
        self._stats = stats
        self._capacity_source = capacity_source
        self._result_queue = result_queue
        self._intervalo = intervalo
        self._tail_handler = tail_handler
        self._ao_sair = ao_sair
        self._ao_reconectar = ao_reconectar
        self._ao_sincronizar = ao_sincronizar

        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._parar = asyncio.Event()
        self._cache_outbox = tick.CacheOutbox()

        # Buffer + thread escritora. A escrita NAO pode acontecer no event loop:
        # `sys.stdout.write` num pipe cheio bloqueia, e o executor inteiro —
        # heartbeat, jobs, conexao — congelaria porque o supervisor parou de ler.
        self._buffer: deque[str] = deque(maxlen=_BUFFER_MAX)
        self._cond = threading.Condition()
        self._descartados = 0
        self._encerrando = False
        self._escritora: threading.Thread | None = None
        self._leitora: threading.Thread | None = None

    def vincular_fontes(
        self, *, capacity_source=None, result_queue=None, ao_sincronizar=None,
    ) -> None:
        """Liga as fontes que so existem depois do boot.

        Diferente do painel rich, que so sobe na fase 7 com tudo pronto, este
        runtime sobe antes da fase 0 — para que uma falha de boot chegue ao
        supervisor como evento, e nao como codigo de saida. A fila de jobs
        nasce na fase 3 e a conexao na fase 4, entao ate la os campos de
        capacidade saem zerados, o que e a verdade: nao ha fila ainda.

        `ao_sincronizar` entra pelo mesmo motivo, e pela mesma porta: o GeoSync
        so e montado na fase 6. Ele nao podia ser passado no construtor, e como
        SO o painel rich o recebia la, o comando `sync_now` — que vem do app
        desktop, que roda no modo JSON — respondia sempre
        `ok=false, "sem handler de sincronizacao"`. O botao "Sincronizar agora"
        nunca fez nada no unico modo em que ele existe.
        """
        if capacity_source is not None:
            self._capacity_source = capacity_source
        if result_queue is not None:
            self._result_queue = result_queue
        if ao_sincronizar is not None:
            self._ao_sincronizar = ao_sincronizar

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._escritora = threading.Thread(
            target=self._loop_escrita, name="ipc-stdout", daemon=True)
        self._escritora.start()

        # `hello` e enfileirado ANTES de a leitora subir. Com a ordem invertida,
        # um comando que ja estivesse no pipe era processado primeiro e seu
        # `ack` saia antes do handshake — o supervisor nao pode ter de tratar
        # resposta de comando antes de saber com quem esta falando.
        self.emitir("hello", {
            "pid": os.getpid(),
            "executor_id": self._stats.executor_id,
            "python": sys.version.split()[0],
            "comandos": list(COMANDOS),
        })

        self._leitora = threading.Thread(
            target=self._loop_leitura, name="ipc-stdin", daemon=True)
        self._leitora.start()
        self._task = asyncio.create_task(self._loop_tick(), name="ipc-snapshot")

    async def stop(self) -> None:
        """Idempotente. Drena o que ainda esta no buffer antes de sair — o
        ultimo `state` (`stopped`) e justamente o que o supervisor precisa para
        distinguir encerramento ordenado de crash."""
        self._parar.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        self.close_live()

    def close_live(self) -> None:
        """Encerra a escritora e devolve o logging ao normal. Sincrona — usada
        tambem pelo `emergency_stop`, que roda fora do event loop."""
        # Desliga o observer antes de tudo: deixa-lo apontando para um runtime
        # que ja fechou faria cada job subsequente enfileirar num buffer que
        # ninguem drena.
        try:
            self._stats.set_observer(None)
        except Exception:
            pass

        with self._cond:
            if self._encerrando:
                return
            self._encerrando = True
            self._cond.notify_all()
        t = self._escritora
        if t is not None and t.is_alive():
            # Curto de proposito: o objetivo e entregar o que ja esta no buffer,
            # nao esperar por um consumidor que talvez tenha morrido.
            t.join(timeout=2.0)
        self._escritora = None

        if self._tail_handler is not None:
            try:
                logging.getLogger().removeHandler(self._tail_handler)
            except Exception:
                pass
            self._tail_handler = None

        # NAO chama `logging_setup.restore_console_mode()`: diferente do painel
        # rich, o modo JSON nunca tirou o log do console. O handler de console
        # escreve em **stderr** (logging_setup: `logging.StreamHandler()` sem
        # argumento), e stderr e o canal por onde o supervisor le o log humano
        # formatado. Silencia-lo deixaria a GUI so com os eventos WARNING+.

    # ── Emissao ──────────────────────────────────────────────────────────────

    def emitir(self, tipo: str, dados: dict | None = None, **extra) -> None:
        """Serializa e enfileira. Nunca levanta, nunca bloqueia.

        Chamada de qualquer thread, inclusive de dentro do `_lock` do stats
        (e o observer) — dai o custo ser so um `json.dumps` e um `append`.
        """
        try:
            msg = {"v": PROTOCOLO, "t": tipo, "ts": round(time.time(), 3), **extra}
            if dados is not None:
                msg["data"] = dados
            linha = json.dumps(msg, ensure_ascii=False, separators=(",", ":"))
            if len(linha) > _LINHA_MAX:
                linha = json.dumps({
                    "v": PROTOCOLO, "t": "warn", "ts": round(time.time(), 3),
                    "data": {"motivo": "linha descartada por tamanho",
                             "tipo": tipo, "bytes": len(linha)},
                }, separators=(",", ":"))
        except Exception:
            # Serializacao falhou — nao ha o que emitir, e insistir aqui
            # (logging, por exemplo) arriscaria recursao pelo JsonLogHandler.
            return

        with self._cond:
            if self._encerrando:
                return
            if len(self._buffer) == _BUFFER_MAX:
                self._descartados += 1
            self._buffer.append(linha)
            self._cond.notify()

    def _loop_escrita(self) -> None:
        """Thread: drena o buffer para o stdout. Unico ponto que escreve la."""
        while True:
            with self._cond:
                while not self._buffer and not self._encerrando:
                    self._cond.wait()
                if not self._buffer and self._encerrando:
                    return
                lote = list(self._buffer)
                self._buffer.clear()
            try:
                sys.stdout.write("".join(l + "\n" for l in lote))
                sys.stdout.flush()
            except Exception:
                # stdout fechou (supervisor morreu). Nao ha para onde reportar;
                # o watchdog de executor/supervisor.py cuida do encerramento.
                return

    # ── Tick ─────────────────────────────────────────────────────────────────

    async def _loop_tick(self) -> None:
        while not self._parar.is_set():
            try:
                self._emitir_snapshot()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Diferente do painel rich, aqui nao ha "desistir apos N falhas":
                # sem este canal o app desktop fica cego. Loga em debug e tenta
                # de novo no proximo tick.
                logger.debug("Falha ao emitir snapshot: %s", exc)
            try:
                await asyncio.wait_for(self._parar.wait(), timeout=self._intervalo)
            except asyncio.TimeoutError:
                pass

    def _emitir_snapshot(self) -> None:
        from executor.stats import snapshot_to_dict

        loop = asyncio.get_running_loop()
        snap = tick.coletar_snapshot(
            self._stats,
            capacity_source=self._capacity_source,
            result_queue=self._result_queue,
            outbox_pending=self._cache_outbox.get(loop.time()),
        )
        if snap is None:      # NullStats
            return

        dados = snapshot_to_dict(snap)
        for campo in _SO_DO_PAINEL:
            dados.pop(campo, None)

        with self._cond:
            descartados, self._descartados = self._descartados, 0
        self.emitir("snapshot", dados, descartados=descartados)

    # ── Comandos ─────────────────────────────────────────────────────────────

    def _loop_leitura(self) -> None:
        """Thread: le comandos do stdin linha a linha.

        Thread bloqueante + `call_soon_threadsafe`, e nao `loop.connect_read_pipe`:
        e o mesmo padrao ja provado por `dashboard/keys.py`, e o comportamento do
        connect_read_pipe com handles herdados no ProactorEventLoop do Windows e
        irregular.
        """
        while True:
            try:
                linha = sys.stdin.readline()
            except Exception:
                return
            if not linha:
                return          # EOF: o supervisor fechou o stdin
            linha = linha.strip()
            if not linha:
                continue
            try:
                cmd = json.loads(linha)
            except Exception:
                self.emitir("ack", None, cmd=None, ok=False, detail="json invalido")
                continue
            loop = self._loop
            if loop is None or loop.is_closed():
                return
            try:
                loop.call_soon_threadsafe(self._executar_comando, cmd)
            except RuntimeError:
                return          # loop encerrando

    def _executar_comando(self, cmd: dict) -> None:
        """Roda NO event loop. Nenhum comando pode levantar."""
        nome = (cmd.get("cmd") or "").strip() if isinstance(cmd, dict) else ""
        ident = cmd.get("id") if isinstance(cmd, dict) else None
        ok, detalhe = True, None
        try:
            if nome == "shutdown":
                # Mesmo caminho da tecla 'q' e de um SIGTERM: shutdown ordenado,
                # sem atalho. Drenar jobs e confirmar resultados importa mais que
                # sair rapido — no Windows isso vale ainda mais, porque la nao ha
                # sinal nenhum para o supervisor mandar.
                if self._ao_sair is None:
                    ok, detalhe = False, "sem handler de shutdown"
                else:
                    self._ao_sair()
            elif nome == "reconnect":
                if self._ao_reconectar is None:
                    ok, detalhe = False, "sem handler de reconexao"
                else:
                    detalhe = "backoff interrompido" if self._ao_reconectar() \
                        else "nao ha espera de reconexao em curso"
            elif nome == "sync_now":
                # Acorda o ciclo do GeoSync sem esperar o intervalo. Quem pede
                # sabe de algo que o executor ainda nao viu — acabou de copiar
                # um arquivo para a pasta, ou publicou algo no Drive.
                if self._ao_sincronizar is None:
                    ok, detalhe = False, "sem handler de sincronizacao"
                else:
                    # `ok` diz que o comando era valido e foi executado, nao que
                    # algo mudou — mesma convencao de `reconnect`, que responde
                    # ok mesmo quando nao havia backoff para interromper. Sem
                    # pasta configurada nao ha falha nenhuma: nao ha o que fazer.
                    n = self._ao_sincronizar()
                    detalhe = (f"{n} pasta(s) acordada(s)" if n
                               else "nenhuma pasta do GeoSync configurada")
            elif nome == "reset_stats":
                self._stats.reset()
            elif nome == "toggle_debug":
                from executor import logging_setup
                ligado = logging_setup.alternar_debug()
                detalhe = "DEBUG" if ligado else "LOG_LEVEL"
            elif nome == "ping":
                pass
            else:
                ok, detalhe = False, f"comando desconhecido: {nome!r}"
        except Exception as exc:
            ok, detalhe = False, str(exc)
        self.emitir("ack", None, cmd=nome or None, id=ident, ok=ok, detail=detalhe)
