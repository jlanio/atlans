import asyncio
import ctypes
import io
import os
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.code_sandbox import (
    build_safe_builtins,
    validate_code_ast,
    UnsafeCodeError,
)
from flow.utils.publisher.events import publish_stdout

# Safe builtins with a custom __import__ — generated only once
_SAFE_BUILTINS = build_safe_builtins()

# Pool DEDICATED to PythonScript, separate from the default ThreadPoolExecutor
# that `asyncio.to_thread` uses — and that EVERY CPU-bound node (spatial, to_json,
# DataFrame conversion) shares. `asyncio.to_thread`/the executor do NOT cancel the
# thread: a script in `while True: pass` blows the node's `wait_for` but leaves the
# THREAD alive. In the default pool, a few runs like that exhaust the workers and
# HANG the other nodes in the process — the executor already acknowledges this by
# isolating the control plane in its own pool (see executor/job_executor.py). Here
# the damage is contained: a stuck loop occupies at most the PythonScript workers,
# never those of the rest of the executor. The best-effort interrupt below still
# tries to return the worker; the complete defense (killable subprocess) is the
# recorded follow-up.
_MAX_PYTHONSCRIPT_WORKERS = min(8, (os.cpu_count() or 2) + 2)
_SCRIPT_POOL = ThreadPoolExecutor(
    max_workers=_MAX_PYTHONSCRIPT_WORKERS,
    thread_name_prefix="pythonscript",
)


class _ScriptInterrupted(BaseException):
    """Injected into the script's thread when the time limit expires.

    Subclass of BaseException — not of Exception — to survive an
    `except Exception` in the user's code and end even a loop that swallows
    common errors.
    """


def _interromper_thread(future: "Future", ident: Optional[int]) -> bool:
    """Best-effort: injects _ScriptInterrupted into the script's thread on timeout.

    `asyncio.wait_for` only cancels the WAIT; the exec() thread keeps running.
    For the common case of a pure-Python loop (`while True: x = 1`) this injection
    ends the thread at the next bytecode and returns the worker to the pool. It does
    NOT interrupt code stuck in a C extension (a giant numpy call) or waiting on
    I/O — for those, the worker only comes back when the executor restarts; the
    complete defense (killable subprocess) is the recorded follow-up.

    Target safety: `future.done()` and the injection call run with the GIL
    HELD (`ctypes.pythonapi` doesn't release it, and there is no await between them).
    If the future hasn't finished yet, the worker is PROVABLY inside our script
    — never in a next pool task, because the worker only dequeues the next one
    after `set_result`, which is what marks `done()`. So the interruption
    never lands on someone else's task.

    Returns True if the interruption was armed for exactly one thread.
    """
    if ident is None or future.done():
        return False
    armed = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(ident), ctypes.py_object(_ScriptInterrupted)
    )
    if armed > 1:
        # Should never happen (the ident is unique); if it does, undo it so as
        # not to leave the exception pending in the wrong thread.
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(ident), None)
        return False
    return armed == 1


def _discard_future(f: "Future") -> None:
    """Consumes the result/exception of an orphaned future (after the timeout).

    Without this, the _ScriptInterrupted that the injection puts in the future
    would become "Future exception was never retrieved" in the executor's log.
    """
    try:
        if not f.cancelled():
            f.exception()
    except BaseException:
        pass


# Stdout aggregation window. One node_event PER print() LINE filled the
# executor's 500-slot queue — shared by ALL jobs and by GeoSync — and
# blew the server's rate limit of 200 events/s: a
# `for i in range(50000): print(i)` took down the telemetry of the other workflows
# with it. With a batch of 200 ms / 200 lines the volume drops by 2 to 3 orders
# of magnitude and the perceived "real time" stays the same.
_STDOUT_FLUSH_SECONDS = 0.2
_STDOUT_FLUSH_LINES = 200
# The batch's BYTE budget — and it closes BEFORE the line ceiling.
# Counting only lines was not enough: a node_event above 64 KB
# (NODE_EVENT_BYTES_CEILING in flow/utils/publisher/reducao.py, the single rule for
# the executor and the server) is reduced, and of the lines only the prefix that
# fits remains — the panel lost the ENTIRE batch, silently, whenever lines were
# long (`for r in gdf.itertuples(): print(r)`, `print(json.dumps(feature))`).
# 24 KB leaves comfortable headroom for JSON overhead and escapes (a line with
# accents/quotes can nearly double in size when serialized).
_STDOUT_FLUSH_BYTES = 24 * 1024
# Ceiling for ONE line. Above it, the line alone would blow the frame and take
# down with it the legitimate lines of the same batch (a 70 KB `print(gdf.to_json())`
# killed the other 199). Truncated individually, with an explicit marker — never
# silently.
_STDOUT_MAX_LINE_CHARS = 8 * 1024
# Ceiling per node run. Past it, the script keeps running (and the local log
# stays complete), but the panel receives a single warning instead of a flood.
_STDOUT_MAX_LINES = 5_000


class _LoggingStream(io.TextIOBase):
    """
    Stream that intercepts print() calls and redirects them to the node's
    logger and to the publisher, making them appear in the UI terminal.
    Processes line by line to respect print()'s default behavior.

    Lines are GROUPED before becoming an event: `publish_fn` receives a list
    of lines, not a line. The batch closes by BYTES (_STDOUT_FLUSH_BYTES), by
    count (_STDOUT_FLUSH_LINES) or by time (_STDOUT_FLUSH_SECONDS), whichever
    comes first — in that priority order, because only the byte criterion
    keeps the event from exceeding the 64 KB ceiling and being reduced to the
    control fields along the way (TOTAL loss of the batch, without warning). The
    time-based flush runs in a `threading.Timer` because the user's script owns
    the thread: without it, a script that prints and then computes for 10 s would
    only deliver the lines at the end of the node.
    """

    def __init__(
        self,
        log_fn: Callable[[str], None],
        publish_fn: Callable[[List[str]], None] | None = None,
    ) -> None:
        self._log_fn = log_fn
        self._publish_fn = publish_fn
        self._partial = ""
        # The buffer is touched by the script's thread AND by the timer's thread.
        self._lock = threading.Lock()
        self._buffer: List[str] = []
        # Bytes of text already accumulated in the current batch (see _STDOUT_FLUSH_BYTES).
        self._batch_bytes = 0
        self._timer: threading.Timer | None = None
        self._published = 0
        self._truncated = False

    # ── Buffer ───────────────────────────────────────────────────────────────

    @staticmethod
    def _truncate_line(line: str) -> str:
        """Truncates a single line too large to fit in a frame.

        Without this, a single `print()` of a GeoJSON takes the whole batch with it:
        the event exceeds 64 KB and reaches the panel with no `extra` at all. The
        marker is explicit because truncating silently would make the output look complete.
        """
        if len(line) <= _STDOUT_MAX_LINE_CHARS:
            return line
        return (
            line[:_STDOUT_MAX_LINE_CHARS]
            + f"…[linha truncada: {len(line)} caracteres; completa no log do executor]"
        )

    def _emit(self, line: str) -> None:
        self._log_fn(line)
        if self._publish_fn is None:
            return
        # The local log (above) receives the ENTIRE line; only what goes to the panel
        # is cut.
        linha = self._truncate_line(line)
        with self._lock:
            self._buffer.append(linha)
            self._batch_bytes += len(linha)
            # Bytes first: it's the criterion that prevents the total loss of the batch.
            cheio = (
                self._batch_bytes >= _STDOUT_FLUSH_BYTES
                or len(self._buffer) >= _STDOUT_FLUSH_LINES
            )
            if not cheio and self._timer is None:
                self._timer = threading.Timer(_STDOUT_FLUSH_SECONDS, self._flush_batch)
                self._timer.daemon = True
                self._timer.start()
        if cheio:
            self._flush_batch()

    def _flush_batch(self) -> None:
        """Closes the current batch and publishes it. Called by the script's thread or by the timer.

        Publishes INSIDE the lock: two threads produce batches (the script's,
        when it fills up, and the timer's, when the time closes it) and publishing
        outside it would let lines arrive out of order in the panel. The cost is
        irrelevant — publishing is a `call_soon_threadsafe`, not a network round trip.
        """
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if not self._buffer:
                return
            lote = self._buffer
            self._buffer = []
            self._batch_bytes = 0
            restante = _STDOUT_MAX_LINES - self._published
            if restante <= 0:
                if self._truncated:
                    return
                self._truncated = True
                lote = [self._truncation_notice()]
            elif len(lote) > restante:
                self._truncated = True
                lote = lote[:restante] + [self._truncation_notice()]
                self._published = _STDOUT_MAX_LINES
            else:
                self._published += len(lote)
            self._publish_fn(lote)  # type: ignore[misc]

    @staticmethod
    def _truncation_notice() -> str:
        return (
            f"[saída truncada: o nó passou de {_STDOUT_MAX_LINES} linhas impressas; "
            "o restante continua apenas no log do executor]"
        )

    # ── io.TextIOBase ────────────────────────────────────────────────────────

    def write(self, text: str) -> int:
        self._partial += text
        while "\n" in self._partial:
            line, self._partial = self._partial.split("\n", 1)
            if line:  # ignores empty lines generated by print()'s trailing \n
                self._emit(line)
        return len(text)

    def flush(self) -> None:
        # Emits partial content that did not end with \n
        if self._partial.strip():
            self._emit(self._partial)
        self._partial = ""
        self._flush_batch()


def _run_script(
    code: str,
    namespace: Dict[str, Any],
    log_fn: Callable[[str], None],
    publish_fn: Callable[[List[str]], None] | None = None,
) -> None:
    """
    Executes the Python script in the given namespace with restricted builtins.
    Redirects stdout so that print() appears in the UI terminal in real time.
    """
    stream = _LoggingStream(log_fn, publish_fn)
    old_stdout = sys.stdout
    try:
        sys.stdout = stream  # type: ignore[assignment]
        namespace["__builtins__"] = _SAFE_BUILTINS
        exec(compile(code, "<PythonScript>", "exec"), namespace)  # noqa: S102
    finally:
        # Restores stdout BEFORE the flush: if the timeout's asynchronous
        # interruption (_ScriptInterrupted) lands in this finally, the global
        # stdout is already back to normal — it never stays stuck on the node's
        # dead stream. The flush operates on `stream` itself, not on sys.stdout,
        # so the order doesn't change what is published; at most the last batch
        # is lost if the thread is killed midway, which is acceptable (the node
        # already failed).
        sys.stdout = old_stdout
        # The final flush is mandatory: without it the last batch (and the line without \n)
        # would die along with the script's thread.
        stream.flush()


@register_node
class PythonScript(BaseNode):
    """
    Executes a snippet of Python code to transform or process data.

    All connected inputs are available as variables in the script's scope
    (by the name of the input port, as defined on the edge).

    Libraries available by default: pd, gpd, np, shapely.

    The variables listed in `output_vars` are read from the namespace at the end
    of execution and returned as named outputs.

    Example script (assuming an input port named `camadas`):
        gdf = camadas.copy()
        gdf["area_ha"] = gdf.geometry.area / 10_000
        gdf = gdf[gdf["area_ha"] > 5]
        result = gdf
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "PythonScript",
            "alias": "Script Python",
            "description": (
                "Executa código Python para transformar tabelas ou GeoDataFrames. "
                "Inputs disponíveis como variáveis; defina as variáveis de saída em output_vars."
            ),
            "type": "action",
            "properties": [
                {
                    "name": "code",
                    "label": "Código Python",
                    "type": "code",
                    "default": "# Inputs disponíveis pelo nome da porta de entrada (ex: minha_camada, dados)\n# Bibliotecas: pd, gpd, np, shapely\n\n# result = minha_camada  # substitua pelo nome da sua porta de entrada\nresult = None\n",
                    "description": "Script Python a executar",
                },
                {
                    "name": "output_vars",
                    "label": "Variável de saída",
                    "type": "string",
                    "default": "result",
                    "description": "Variáveis de saída separadas por vírgula (ex: result_a, result_b)",
                },
                {
                    "name": "ports",
                    "label": "Portas de entrada",
                    "type": "ports",
                    "default": [],
                    "description": (
                        "Nome de cada entrada. Vazio: o nó aceita uma conexão e a "
                        "variável recebe o nome da saída do nó anterior. Com DUAS ou "
                        "mais, cada porta vira um ponto de conexão próprio e o nome "
                        "que você der é o nome da variável no script."
                    ),
                },
                {
                    "name": "timeout",
                    "label": "Tempo limite (s)",
                    "type": "integer",
                    "default": 30,
                    "description": "Tempo máximo de execução em segundos",
                },
            ],
            # Inputs DECLARED BY THE USER, via the `ports` property.
            #
            # Without this the node cannot receive two distinct inputs: the variable
            # name comes from the edge's `to_key`, the editor only fills `to_key`
            # when the target declares more than one port, and without it the executor
            # falls back to `from_key` — which is "output" in practically every node.
            # Both edges write to the same key and the second overwrites the first.
            #
            # Empty by default: existing nodes keep a single anonymous port and
            # today's edges keep working exactly as they do.
            "dynamic_inputs": True,
            # Outputs dinamicos — definidos pelo usuario via output_vars
            "dynamic_output": True,
            "outputs": [
                {"name": "result", "type": "any", "description": "Saída padrão do script (tipo depende do código executado)"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        code: str = self.parameters.get("code", "")
        output_vars_raw: str = self.parameters.get("output_vars", "result")
        timeout: int = self.get_param_int("timeout", 30)

        if not code.strip():
            raise ValueError("O campo 'code' não pode estar vazio.")

        # ── Security validation (AST) ────────────────────────────
        # Rejects disallowed imports and access to dangerous attributes
        # BEFORE compiling/executing any code.
        try:
            validate_code_ast(code)
        except UnsafeCodeError as exc:
            raise ValueError(f"Código bloqueado por segurança: {exc}") from exc

        # Names of the output variables
        output_var_names: List[str] = [
            v.strip() for v in output_vars_raw.split(",") if v.strip()
        ]
        if not output_var_names:
            raise ValueError("'output_vars' deve conter ao menos um nome de variável.")

        # Monta namespace com inputs nomeados + bibliotecas
        namespace: Dict[str, Any] = {
            "pd": pd,
            "gpd": gpd,
            "np": np,
            "shapely": shapely,
        }

        # Injects inputs by the real port name (to_key/from_key defined on the edge)
        for key, value in inputs.items():
            namespace[key] = value

        # Builds a callback that publishes print() to the UI terminal via Redis
        publisher = self._publisher
        task_id = self._task_id
        node_id = self.node_id

        def _publish_print(linhas: List[str]) -> None:
            """Publishes a BATCH of print() lines as a kind=stdout event."""
            publish_stdout(publisher, task_id, node_id, linhas)

        # Runs the script in PythonScript's DEDICATED pool, with a time limit.
        # self.log is passed as the callback for the Python logger;
        # _publish_print routes print() to the UI terminal via WebSocket.
        #
        # The script's thread is NOT cancelable: on timeout there's no way to stop it.
        # That's why (a) we run on _SCRIPT_POOL, which isolates the damage of a stuck
        # loop from the other nodes, and (b) we capture the thread's ident to inject
        # _ScriptInterrupted and try to return the worker to the pool.
        loop = asyncio.get_running_loop()
        thread_state: Dict[str, int] = {}

        def _executar_script() -> None:
            thread_state["ident"] = threading.get_ident()
            stdout_before = sys.stdout
            try:
                _run_script(code, namespace, self.log, _publish_print)
            finally:
                # Safety net: if _ScriptInterrupted lands in _run_script's finally
                # before stdout is restored, it is restored here. At this
                # point the asynchronous exception has already been consumed (it fires
                # only once), so this finally runs in full, with no risk of another
                # interruption — the global stdout never stays stuck on the node's stream.
                if sys.stdout is not stdout_before:
                    sys.stdout = stdout_before

        future = loop.run_in_executor(_SCRIPT_POOL, _executar_script)
        # Do NOT use asyncio.wait_for: on timeout it tries to CANCEL the future and,
        # since the executor's thread is already running (not cancelable), WAITS for
        # the thread to finish — which in a `while True` never happens, nullifying
        # the timeout itself. asyncio.wait only OBSERVES: at the deadline the future
        # stays in `pendentes` and we handle it without canceling.
        _, pendentes = await asyncio.wait({future}, timeout=float(timeout))
        if pendentes:
            # add_done_callback only here: only the orphan path (thread still
            # alive) needs to discard the exception — on the normal path the
            # future.exception() below already consumes it.
            future.add_done_callback(_discard_future)
            released = _interromper_thread(future, thread_state.get("ident"))
            self.log(
                "Tempo limite excedido. "
                + (
                    "Thread do script interrompida; worker devolvido ao pool."
                    if released
                    else "A thread pode seguir presa (codigo em extensao C ou I/O); "
                    "o worker so volta ao reiniciar o executor."
                )
            )
            raise TimeoutError(
                f"Execução do script excedeu o limite de {timeout} segundos."
            )

        # Finished within the deadline — propagates a script error as before.
        exc = future.exception()
        if exc is not None:
            _libs = {"pd", "gpd", "np", "shapely"}
            available = [k for k in namespace if not k.startswith("__") and k not in _libs]
            hint = f" Inputs disponíveis no namespace: {available}." if available else " Nenhum input foi conectado a este nó."
            raise RuntimeError(f"Erro ao executar script Python: {exc}.{hint}") from exc

        # Collects output variables from the namespace
        result: Dict[str, Any] = {}
        for var in output_var_names:
            if var not in namespace:
                _libs = {"pd", "gpd", "np", "shapely"}
                available = [k for k in namespace if not k.startswith("__") and k not in _libs]
                hint = f" Variáveis disponíveis: {available}." if available else ""
                raise KeyError(
                    f"Variável de saída '{var}' não foi definida no script.{hint}"
                )
            result[var] = namespace[var]

        return result
