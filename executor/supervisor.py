# executor/supervisor.py
"""
Supervisor process watchdog.

When the executor is started by an external supervisor — the desktop app —,
the supervisor passes its own PID in `EXECUTOR_SUPERVISOR_PID`. If it dies
without shutting down the child (user killing the app through Task Manager,
Electron crash), the executor would stay alive, orphaned and invisible: no
window, no tray, and still holding the WebSocket connection with the same
EXECUTOR_ID. The next time the app started, the server would see TWO
connections from the same executor.

The canonical alternative on Windows would be a Job Object with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, which kills the child along with the
parent. It was discarded because it requires a native module (`node-gyp`, a
rebuild for every Electron version, signing the `.node`) to solve what 60
lines solve — `psutil` is already an executor dependency, used by `sysinfo.py`.

The shutdown is ORDERLY: it fires the same `shutdown_event` as a SIGTERM, so
jobs in progress are drained and results confirmed. Killing on the spot would
lose work already done.
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger("executor.supervisor")

INTERVALO_S = 5.0
VAR_PID = "EXECUTOR_SUPERVISOR_PID"


def pid_configurado() -> int | None:
    """The supervisor's PID, or None if the executor was not started by one.

    Running `python -m executor` by hand doesn't set the variable, so the
    watchdog simply doesn't start — there is nothing to watch.
    """
    bruto = (os.getenv(VAR_PID) or "").strip()
    if not bruto:
        return None
    try:
        pid = int(bruto)
    except ValueError:
        logger.warning("%s=%r nao e um inteiro — watchdog do supervisor desativado.", VAR_PID, bruto)
        return None
    if pid <= 0:
        return None
    return pid


class MonitorSupervisor:
    """Periodically checks whether the supervisor is still alive.

    Compares the PID **and** `create_time()`. The PID alone is not enough: the
    operating system reuses process numbers, and a PID recycled by another
    program would make the watchdog conclude the supervisor is alive when it
    died long ago — the orphan it exists to prevent.
    """

    def __init__(self, pid: int, *, intervalo: float = INTERVALO_S) -> None:
        self._pid = pid
        self._intervalo = intervalo
        self._proc = None
        self._criado_em: float | None = None

    def vincular(self) -> bool:
        """Pins the supervisor's identity. False if it no longer exists."""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil ausente — watchdog do supervisor desativado.")
            return False
        try:
            self._proc = psutil.Process(self._pid)
            self._criado_em = self._proc.create_time()
            return True
        except Exception as exc:
            logger.warning(
                "Supervisor PID %d nao encontrado no start (%s) — encerrando: "
                "seguir sem ele deixaria este processo orfao.", self._pid, exc,
            )
            return False

    def vivo(self) -> bool:
        """True enquanto o MESMO processo do `vincular()` continuar rodando."""
        proc = self._proc
        if proc is None:
            return False
        try:
            if not proc.is_running():
                return False
            # A zombie still "runs" as far as is_running() is concerned; it doesn't count as a supervisor.
            import psutil
            if proc.status() == psutil.STATUS_ZOMBIE:
                return False
            return proc.create_time() == self._criado_em
        except Exception:
            # NoSuchProcess, AccessDenied on a process now owned by someone else —
            # all mean "the supervisor I knew is gone".
            return False

    async def vigiar(self, ao_morrer) -> None:
        """Loops until the supervisor disappears; then calls `ao_morrer` exactly once."""
        while True:
            await asyncio.sleep(self._intervalo)
            if not self.vivo():
                logger.warning(
                    "Supervisor (PID %d) encerrou — iniciando shutdown ordenado "
                    "para nao ficar orfao.", self._pid,
                )
                try:
                    ao_morrer()
                except Exception as exc:
                    logger.error("Falha ao sinalizar o shutdown pelo watchdog: %s", exc)
                return


def criar_task(ao_morrer, *, intervalo: float = INTERVALO_S) -> asyncio.Task | None:
    """Sobe o watchdog se houver supervisor configurado. None caso contrario."""
    pid = pid_configurado()
    if pid is None:
        return None
    monitor = MonitorSupervisor(pid, intervalo=intervalo)
    if not monitor.vincular():
        # The supervisor died between the spawn and this point. Shutting down now is
        # right: nobody will consume the NDJSON channel or stop this process later.
        ao_morrer()
        return None
    logger.info("Watchdog do supervisor ativo (PID %d, a cada %.0fs).", pid, intervalo)
    return asyncio.create_task(monitor.vigiar(ao_morrer), name="supervisor-watchdog")
