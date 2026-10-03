# executor/dashboard/__init__.py
"""
Live statistics panel in the terminal.

Replaces the console's step-by-step log with a summary that updates itself.
The log is still complete — it goes to a rotating file, which becomes enabled
by default when the panel takes over (see `logging_setup.switch_to_dashboard_mode`).

This module does NOT import `rich`. The modules that do (`render`, `runtime`)
are only loaded inside `start()`, after the gate approves — so an
executor with the panel off pays nothing.
"""
from __future__ import annotations

import atexit
import importlib.util
import logging
import os
import shutil
import sys
from typing import Mapping

logger = logging.getLogger("executor.dashboard")

_LIGADO = {"off", "never", "0", "false", "no"}
_FORCADO = {"on", "always", "1", "true", "yes"}
_JSON = {"json", "ndjson", "ipc"}

# Possible modes. The gate returns one of these, and not a boolean: with the arrival of
# the desktop app there came to be TWO consumers of the statistics collector —
# the terminal and a supervisor — and "on/off" does not distinguish the two.
MODO_RICH = "rich"
MODO_JSON = "json"
MODO_OFF = "off"

# Below this the panel comes out clipped, which is worse than not existing.
_MIN_LARGURA = 60
_MIN_ALTURA = 12

_runtime = None


def rich_disponivel() -> bool:
    """`find_spec` instead of `import`: does not pay the cost of loading rich
    when the panel is off."""
    try:
        return importlib.util.find_spec("rich") is not None
    except (ImportError, ValueError):
        return False


def should_enable(
    *,
    env: Mapping[str, str],
    stdout_tty: bool,
    stderr_tty: bool,
    rich_ok: bool,
    largura: int,
    altura: int,
) -> tuple[str, str]:
    """Decides the collector mode. Pure function — no real TTY, no os.environ.

    Returns `(modo, motivo)`, with `modo` in {"rich", "json", "off"}. The reason is
    always filled in when the result is NOT the panel: a panel that does not
    show up with no explanation becomes a support ticket.

    `json` is always explicit, never inferred: writing NDJSON on the stdout of
    something that expected human logs breaks the consumer silently. Whoever wants the
    structured channel asks for it with `EXECUTOR_DASHBOARD=json` — which is what the desktop app does
    when it spawns the process.
    """
    modo = (env.get("EXECUTOR_DASHBOARD") or "auto").strip().lower()

    # Before anything else: does not depend on rich, on a TTY or on the terminal size.
    # The consumer is a program.
    if modo in _JSON:
        return MODO_JSON, "canal NDJSON por EXECUTOR_DASHBOARD"

    if modo in _LIGADO:
        return MODO_OFF, "desativado por EXECUTOR_DASHBOARD"

    if not rich_ok:
        return MODO_OFF, "biblioteca 'rich' nao instalada (pip install rich)"

    # Deliberate escape hatch: whoever passes `on` knows what they are doing.
    if modo in _FORCADO:
        return MODO_RICH, "forcado por EXECUTOR_DASHBOARD"

    # A partir daqui, modo == auto.
    if not stdout_tty or not stderr_tty:
        # Covers Docker without -it, systemd/journald, `| tee` and the desktop app, which
        # captures the process output through a pipe.
        return MODO_OFF, "stdout/stderr nao e um terminal interativo"

    if (env.get("LOG_COLOR") or "").strip().lower() == "never":
        # The operator already asked for unadorned output; it is what the executor's compose uses.
        return MODO_OFF, "LOG_COLOR=never"

    if env.get("NO_COLOR"):
        return MODO_OFF, "NO_COLOR definido"

    if os.name != "nt" and (env.get("TERM") or "").strip().lower() in ("", "dumb"):
        return MODO_OFF, "TERM ausente ou 'dumb'"

    if env.get("CI"):
        return MODO_OFF, "ambiente de CI"

    if largura < _MIN_LARGURA or altura < _MIN_ALTURA:
        return MODO_OFF, f"terminal pequeno demais ({largura}x{altura})"

    return MODO_RICH, "terminal interativo"


def should_enable_from_process() -> tuple[str, str]:
    """Le o ambiente real e delega para `should_enable`."""
    try:
        tamanho = shutil.get_terminal_size(fallback=(80, 24))
    except Exception:
        tamanho = os.terminal_size((80, 24))
    return should_enable(
        env=os.environ,
        stdout_tty=bool(getattr(sys.stdout, "isatty", lambda: False)()),
        stderr_tty=bool(getattr(sys.stderr, "isatty", lambda: False)()),
        rich_ok=rich_disponivel(),
        largura=tamanho.columns,
        altura=tamanho.lines,
    )


async def start(stats, *, modo: str = MODO_RICH, capacity_source, result_queue,
                intervalo: float = 1.0, ao_sair=None, ao_reconectar=None, ao_sincronizar=None):
    """Starts the runtime for the requested `modo` and returns the object (with `stop()`).

    `ao_sair` is called by the 'q' key or by the `shutdown` command — it must
    trigger the same orderly shutdown as a SIGTERM. `ao_reconectar` responds
    to 'r' / `reconnect` and must interrupt the connection backoff.

    Returns `None` if it could not be turned on. Does not raise: any failure here
    leaves the executor in normal log mode, working.
    """
    if modo == MODO_JSON:
        return await _start_json(stats, capacity_source=capacity_source,
                                 result_queue=result_queue, intervalo=intervalo,
                                 ao_sair=ao_sair, ao_reconectar=ao_reconectar,
                             ao_sincronizar=ao_sincronizar)
    return await _start_rich(stats, capacity_source=capacity_source,
                             result_queue=result_queue, intervalo=intervalo,
                             ao_sair=ao_sair, ao_reconectar=ao_reconectar,
                                 ao_sincronizar=ao_sincronizar)


async def _start_rich(stats, *, capacity_source, result_queue, intervalo,
                      ao_sair, ao_reconectar, ao_sincronizar):
    """`rich` panel: swaps the console for the file and starts the refresh loop."""
    global _runtime

    from executor import logging_setup

    try:
        caminho = logging_setup.switch_to_dashboard_mode()
    except logging_setup.LoggingSetupError as exc:
        # The rule: the panel only turns on if the file opens. Swapping the console log
        # for a file that does not exist would be deleting the log, not moving it.
        logger.warning("Painel nao ligado — %s", exc)
        return None

    tail = None
    try:
        from executor.dashboard.log_sink import LogTailHandler
        from executor.dashboard.runtime import DashboardRuntime

        tail = LogTailHandler(stats)
        logging.getLogger().addHandler(tail)

        _runtime = DashboardRuntime(
            stats,
            capacity_source=capacity_source,
            result_queue=result_queue,
            intervalo=intervalo,
            log_path=caminho,
            tail_handler=tail,
            ao_sair=ao_sair,
            ao_reconectar=ao_reconectar,
            ao_sincronizar=ao_sincronizar,
        )
        await _runtime.start()
        atexit.register(emergency_stop)
        return _runtime
    except Exception as exc:
        logger.error("Painel nao ligou — seguindo com log normal: %s", exc, exc_info=True)
        # The tail might already be on the root: leaving it there would forever feed a
        # collector nobody reads.
        if tail is not None:
            logging.getLogger().removeHandler(tail)
        logging_setup.restore_console_mode()
        _runtime = None
        return None


async def _start_json(stats, *, capacity_source, result_queue, intervalo,
                      ao_sair, ao_reconectar, ao_sincronizar):
    """NDJSON channel on stdout.

    Does not touch console logging: it writes to stderr, which is still the
    human log read by the supervisor. The rotating file is turned on if possible,
    but its failure does NOT prevent the channel — unlike the rich panel, here no
    screen is being taken over, so there is no log to be lost.
    """
    global _runtime

    try:
        from executor import logging_setup
        logging_setup.switch_to_dashboard_mode()
        logging_setup.restore_console_mode()   # devolve o stderr; mantem o arquivo
    except Exception as exc:
        logger.debug("Log em arquivo nao ligado no modo json: %s", exc)

    tail = None
    try:
        from executor.dashboard.json_runtime import JsonRuntime
        from executor.dashboard.log_sink import JsonLogHandler

        _runtime = JsonRuntime(
            stats,
            capacity_source=capacity_source,
            result_queue=result_queue,
            intervalo=intervalo,
            ao_sair=ao_sair,
            ao_reconectar=ao_reconectar,
            ao_sincronizar=ao_sincronizar,
        )
        tail = JsonLogHandler(stats, _runtime)
        logging.getLogger().addHandler(tail)
        _runtime._tail_handler = tail

        # Without this line the channel emits ONLY periodic snapshots, and every
        # immediate event — job, sync, conn — simply never goes out. The symptom
        # is a panel with correct metrics and a permanently empty execution
        # history: the snapshot's `last_finished` holds a single job, and
        # the consumer has no way to rebuild the list from it.
        stats.set_observer(_runtime.emitir)

        await _runtime.start()
        atexit.register(emergency_stop)
        return _runtime
    except Exception as exc:
        logger.error("Canal NDJSON nao ligou — seguindo com log normal: %s", exc, exc_info=True)
        if tail is not None:
            logging.getLogger().removeHandler(tail)
        _runtime = None
        return None


def emergency_stop() -> None:
    """Closes the panel and gives the terminal back. Synchronous, idempotent, no event loop.

    Exists for the paths that do not go through the orderly shutdown: unhandled
    exception, `SystemExit`, `KeyboardInterrupt` and the auto-restart's `os.execve`.
    Without it the process dies (or is replaced) leaving the terminal in the alternate
    buffer, with no cursor — the user sees the screen clear and nothing else.
    """
    global _runtime
    try:
        if _runtime is not None:
            _runtime.close_live()
            _runtime = None
    except Exception:
        pass
    try:
        from executor import logging_setup
        logging_setup.restore_console_mode()
    except Exception:
        pass
