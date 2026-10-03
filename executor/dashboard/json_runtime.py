# executor/dashboard/json_runtime.py
"""
Structured event channel for a supervisor (the desktop app).

Replaces the `rich` panel for a consumer that is not human: instead of drawing
the `Snapshot`, it serializes and emits one JSON line per event on **stdout**.

Why stdout, and not a local socket: `logging_setup` sends the human log to
**stderr** (`logging.StreamHandler()` with no argument), so stdout is already free
and there is no logging refactor to do. An HTTP/WS server on 127.0.0.1 would require
a port, authentication and firewall, and would be readable by any process of the
user — carrying statistics and the log tail.

Why NOT read the log file: that is what the removed `agent-desktop` did,
deriving state with regexes over Portuguese messages. It is what the header of
`executor/stats.py` forbids, and the reason that app rotted.

## Format

One JSON line per event, terminated by `\\n`, ALWAYS starting with `{"v":1,`.
The prefix is framing: the reader drops any line that does not match, which covers
an accidental `print()` from a workflow node landing on the same stdout.

    {"v":1,"t":"hello",...}       once, at start
    {"v":1,"t":"state",...}       boot / shutdown phase
    {"v":1,"t":"snapshot",...}    periodic
    {"v":1,"t":"job"|"sync"|"conn",...}   immediate, via the stats observer
    {"v":1,"t":"log",...}         WARNING+
    {"v":1,"t":"ack",...}         reply to a command

## Commands (stdin)

One JSON line per command, mirroring the keys of the `rich` panel
(`runtime.py::_tecla`) — the GUI gets exactly the control surface the
terminal operator has, no more, no less.
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

# Format version, the `v` of the framing. Bumping it here requires updating the PROTOCOLO
# in desktop/src/shared/events.ts.
PROTOCOLO = 1
_PREFIXO = '{"v":%d,' % PROTOCOLO

# Events held back while the consumer is not reading. When full, the OLDEST is dropped
# (deque with maxlen). It is the right choice for snapshots, which supersede each other: the
# consumer wants the current state, not the one from 40 s ago.
_BUFFER_MAX = 256

# Ceiling on a serialized line. No event may become a multi-megabyte line
# that hangs the parser on the other side.
_LINHA_MAX = 512 * 1024

# `Snapshot` fields that exist for the `rich` panel to draw and that this
# runtime does NOT emit. `log_tail` is up to 200 log lines resent in full
# every second, while the supervisor has its own log channel, incremental and
# with `seq` (`log` events) — the tail would only repeat what it already received.
# `system` is hardware, which does not change from one tick to the next.
#
# Neither of the two is read on the other side, and both went through the pipe,
# `JSON.parse` and a structured clone per window, at 1 Hz, only to be discarded:
# tens of KB per second with the executor IDLE. `log_warn_count` and
# `log_error_count` stay — they are two integers and the GUI shows the counters.
#
# If some screen ever needs `system`, its place is `hello`, which goes out
# once, and not a periodic event.
_SO_DO_PAINEL = ("log_tail", "system")

# Mirror the rich panel's keys 1:1. `toggle_debug` is named that way, and not
# `set_debug`, because `logging_setup.alternar_debug()` toggles — promising an
# idempotent setter on top of a toggle would give a retry the opposite semantics.
COMANDOS = ("shutdown", "reconnect", "reset_stats", "toggle_debug", "ping", "sync_now")


class JsonRuntime:
    """Emits NDJSON on stdout and reads commands from stdin.

    Same lifecycle interface as `DashboardRuntime` (`start`, `stop`,
    `close_live`) so that `dashboard.start()` can return either one and
    `main.py` does not need to know which.
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

        # Buffer + writer thread. Writing must NOT happen on the event loop:
        # `sys.stdout.write` on a full pipe blocks, and the whole executor —
        # heartbeat, jobs, connection — would freeze because the supervisor stopped reading.
        self._buffer: deque[str] = deque(maxlen=_BUFFER_MAX)
        self._cond = threading.Condition()
        self._descartados = 0
        self._encerrando = False
        self._escritora: threading.Thread | None = None
        self._leitora: threading.Thread | None = None

    def vincular_fontes(
        self, *, capacity_source=None, result_queue=None, ao_sincronizar=None,
    ) -> None:
        """Hooks up the sources that only exist after boot.

        Unlike the rich panel, which only starts in phase 7 with everything ready, this
        runtime starts before phase 0 — so that a boot failure reaches the
        supervisor as an event, and not as an exit code. The job queue
        is born in phase 3 and the connection in phase 4, so until then the capacity
        fields go out zeroed, which is the truth: there is no queue yet.

        `ao_sincronizar` comes in for the same reason, and through the same door: GeoSync
        is only set up in phase 6. It could not be passed in the constructor, and since
        ONLY the rich panel received it there, the `sync_now` command — which comes from the
        desktop app, which runs in JSON mode — always answered
        `ok=false, "sem handler de sincronizacao"`. The "Sincronizar agora" (sync now) button
        never did anything in the only mode in which it exists.
        """
        if capacity_source is not None:
            self._capacity_source = capacity_source
        if result_queue is not None:
            self._result_queue = result_queue
        if ao_sincronizar is not None:
            self._ao_sincronizar = ao_sincronizar

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._escritora = threading.Thread(
            target=self._loop_escrita, name="ipc-stdout", daemon=True)
        self._escritora.start()

        # `hello` is queued BEFORE the reader starts. With the order reversed,
        # a command already in the pipe was processed first and its
        # `ack` went out before the handshake — the supervisor must not have to handle
        # a command reply before knowing who it is talking to.
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
        """Idempotent. Drains what is still in the buffer before leaving — the
        last `state` (`stopped`) is precisely what the supervisor needs to
        tell an orderly shutdown from a crash."""
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
        """Stops the writer and restores logging to normal. Synchronous — also used
        by `emergency_stop`, which runs outside the event loop."""
        # Turns off the observer before anything else: leaving it pointing at a runtime
        # that has already closed would make every subsequent job queue into a buffer that
        # nobody drains.
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
            # Short on purpose: the goal is to deliver what is already in the buffer,
            # not to wait for a consumer that may have died.
            t.join(timeout=2.0)
        self._escritora = None

        if self._tail_handler is not None:
            try:
                logging.getLogger().removeHandler(self._tail_handler)
            except Exception:
                pass
            self._tail_handler = None

        # Does NOT call `logging_setup.restore_console_mode()`: unlike the rich
        # panel, JSON mode never took the log off the console. The console handler
        # writes to **stderr** (logging_setup: `logging.StreamHandler()` with no
        # argument), and stderr is the channel through which the supervisor reads the
        # formatted human log. Silencing it would leave the GUI with only the WARNING+ events.

    # ── Emissao ──────────────────────────────────────────────────────────────

    def emitir(self, tipo: str, dados: dict | None = None, **extra) -> None:
        """Serializes and queues. Never raises, never blocks.

        Called from any thread, including from inside the stats `_lock`
        (it is the observer) — hence the cost being just a `json.dumps` and an `append`.
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
            # Serialization failed — there is nothing to emit, and insisting here
            # (logging, for example) would risk recursion through the JsonLogHandler.
            return

        with self._cond:
            if self._encerrando:
                return
            if len(self._buffer) == _BUFFER_MAX:
                self._descartados += 1
            self._buffer.append(linha)
            self._cond.notify()

    def _loop_escrita(self) -> None:
        """Thread: drains the buffer to stdout. The only place that writes there."""
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
                # stdout closed (the supervisor died). There is nowhere to report to;
                # the watchdog in executor/supervisor.py takes care of the shutdown.
                return

    # ── Tick ─────────────────────────────────────────────────────────────────

    async def _loop_tick(self) -> None:
        while not self._parar.is_set():
            try:
                self._emitir_snapshot()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Unlike the rich panel, here there is no "give up after N failures":
                # without this channel the desktop app is blind. Log at debug and try
                # again on the next tick.
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
        """Thread: reads commands from stdin line by line.

        Blocking thread + `call_soon_threadsafe`, and not `loop.connect_read_pipe`:
        it is the same pattern already proven by `dashboard/keys.py`, and the behavior of
        connect_read_pipe with inherited handles in Windows' ProactorEventLoop is
        erratic.
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
        """Runs ON the event loop. No command may raise."""
        nome = (cmd.get("cmd") or "").strip() if isinstance(cmd, dict) else ""
        ident = cmd.get("id") if isinstance(cmd, dict) else None
        ok, detalhe = True, None
        try:
            if nome == "shutdown":
                # Same path as the 'q' key and a SIGTERM: orderly shutdown,
                # no shortcut. Draining jobs and confirming results matters more than
                # exiting fast — on Windows this holds even more, because there is
                # no signal at all for the supervisor to send.
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
                # Wakes the GeoSync cycle without waiting for the interval. Whoever asks
                # knows something the executor has not seen yet — they just copied
                # a file into the folder, or published something to the Drive.
                if self._ao_sincronizar is None:
                    ok, detalhe = False, "sem handler de sincronizacao"
                else:
                    # `ok` says the command was valid and was executed, not that
                    # something changed — same convention as `reconnect`, which answers
                    # ok even when there was no backoff to interrupt. With no
                    # folder configured there is no failure at all: there is nothing to do.
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
