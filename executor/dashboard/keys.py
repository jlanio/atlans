# executor/dashboard/keys.py
"""
Reading terminal keys without blocking the event loop.

A daemon thread stays blocked on the read and delivers each key to the loop through
`call_soon_threadsafe`. It could be `loop.add_reader(stdin)` on POSIX, but that
does not exist on Windows (the Proactor implementation only accepts sockets), and a single
thread covers both without branching the lifecycle.

The central concern is POSIX: reading key by key requires taking the terminal out of
canonical mode, and a terminal left in cbreak after the process dies stops
echoing what the user types — the shell looks frozen. That is why the restore
happens in three places (stop, the thread's `finally` and `atexit`) and is idempotent.
"""
from __future__ import annotations

import asyncio
import atexit
import logging
import os
import sys
import threading
from typing import Callable

logger = logging.getLogger("executor.dashboard")

_TERMINAL_STATE = None   # settings do termios a restaurar (POSIX)
_FD_TERMINAL = None


def _restore_terminal() -> None:
    """Devolve o terminal ao modo canonical. Idempotente e silenciosa."""
    global _TERMINAL_STATE, _FD_TERMINAL
    if _TERMINAL_STATE is None:
        return
    estado, fd, _TERMINAL_STATE, _FD_TERMINAL = _TERMINAL_STATE, _FD_TERMINAL, None, None
    try:
        import termios
        termios.tcsetattr(fd, termios.TCSADRAIN, estado)
    except Exception:
        pass


atexit.register(_restore_terminal)


def teclado_disponivel() -> bool:
    """Can keys be read from this process?

    The panel gate already requires stdout/stderr on a TTY, but stdin may be
    redirected (`< /dev/null`, a pipe, a supervisor). In that case the panel
    keeps working — just without shortcuts.
    """
    try:
        if not sys.stdin or not sys.stdin.isatty():
            return False
    except Exception:
        return False
    if os.name == "nt":
        try:
            import msvcrt  # noqa: F401
            return True
        except ImportError:
            return False
    try:
        import termios  # noqa: F401
        import tty  # noqa: F401
        return True
    except ImportError:
        return False


class KeyReader:
    """Delivers keys to the event loop through a callback.

    The callback runs ON THE LOOP (via call_soon_threadsafe), so it can touch the
    panel state without extra synchronization.
    """

    def __init__(self, on_receive: Callable[[str], None]):
        self._on_receive = on_receive
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """Starts the reader thread. Returns False if the keyboard is not
        available — the caller carries on without shortcuts, without treating it as an error."""
        if not teclado_disponivel():
            return False
        self._loop = asyncio.get_running_loop()
        try:
            self._preparar_terminal()
        except Exception as exc:
            logger.debug("Teclado indisponivel (%s) — painel segue sem atalhos.", exc)
            return False
        self._thread = threading.Thread(target=self._read_loop,
                                        name="dashboard-keys", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stops delivering keys and returns the terminal to canonical mode.

        The thread is not awaited: it is blocked on a read that only returns
        on the next key. Since it is a daemon and `_stop_event` makes it drop whatever
        arrives, leaving it hanging neither holds up shutdown nor delivers a key
        to a panel that has already died.
        """
        self._stop_event.set()
        _restore_terminal()

    # ── Plataforma ───────────────────────────────────────────────────────────

    def _preparar_terminal(self) -> None:
        global _TERMINAL_STATE, _FD_TERMINAL
        if os.name == "nt":
            return  # msvcrt.getwch() already reads without echo and without enter
        import termios
        import tty
        fd = sys.stdin.fileno()
        _TERMINAL_STATE = termios.tcgetattr(fd)
        _FD_TERMINAL = fd
        # cbreak, and not raw: keeps Ctrl+C as SIGINT, which is still
        # the shutdown path everybody knows.
        tty.setcbreak(fd)

    def _ler_uma(self) -> str | None:
        if os.name == "nt":
            import msvcrt
            ch = msvcrt.getwch()
            # Special keys (arrows, F1..) arrive as prefix + code; the
            # second byte must be consumed, otherwise it becomes a phantom key.
            if ch in ("\x00", "\xe0"):
                msvcrt.getwch()
                return None
            return ch
        return sys.stdin.read(1)

    def _read_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    tecla = self._ler_uma()
                except Exception:
                    return  # stdin fechado (shutdown) — nada a relatar
                if tecla is None or self._stop_event.is_set():
                    continue
                loop, cb = self._loop, self._on_receive
                if loop is None or loop.is_closed():
                    return
                try:
                    loop.call_soon_threadsafe(cb, tecla)
                except RuntimeError:
                    return  # loop encerrando
        finally:
            _restore_terminal()
