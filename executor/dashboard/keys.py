# executor/dashboard/keys.py
"""
Leitura de teclas do terminal sem bloquear o event loop.

Uma thread daemon fica bloqueada na leitura e entrega cada tecla ao loop por
`call_soon_threadsafe`. Poderia ser `loop.add_reader(stdin)` em POSIX, mas isso
nao existe no Windows (a implementacao Proactor so aceita sockets), e uma unica
thread cobre os dois sem ramificar o ciclo de vida.

O cuidado central e POSIX: ler tecla a tecla exige tirar o terminal do modo
canonico, e um terminal que fica em cbreak depois do processo morrer para de
ecoar o que o usuario digita — o shell parece travado. Por isso a restauracao
acontece em tres lugares (stop, `finally` da thread e `atexit`) e e idempotente.
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

_ESTADO_TERMINAL = None   # settings do termios a restaurar (POSIX)
_FD_TERMINAL = None


def _restaurar_terminal() -> None:
    """Devolve o terminal ao modo canonico. Idempotente e silenciosa."""
    global _ESTADO_TERMINAL, _FD_TERMINAL
    if _ESTADO_TERMINAL is None:
        return
    estado, fd, _ESTADO_TERMINAL, _FD_TERMINAL = _ESTADO_TERMINAL, _FD_TERMINAL, None, None
    try:
        import termios
        termios.tcsetattr(fd, termios.TCSADRAIN, estado)
    except Exception:
        pass


atexit.register(_restaurar_terminal)


def teclado_disponivel() -> bool:
    """Da para ler teclas deste processo?

    O gate do painel ja exige stdout/stderr em TTY, mas stdin pode estar
    redirecionado (`< /dev/null`, um pipe, um supervisor). Nesse caso o painel
    continua funcionando — so sem atalhos.
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


class LeitorDeTeclas:
    """Entrega teclas ao event loop por callback.

    O callback roda NO LOOP (via call_soon_threadsafe), entao pode mexer no
    estado do painel sem sincronizacao extra.
    """

    def __init__(self, ao_receber: Callable[[str], None]):
        self._ao_receber = ao_receber
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()

    def start(self) -> bool:
        """Sobe a thread de leitura. Retorna False se o teclado nao estiver
        disponivel — o caller segue sem atalhos, sem tratar isso como erro."""
        if not teclado_disponivel():
            return False
        self._loop = asyncio.get_running_loop()
        try:
            self._preparar_terminal()
        except Exception as exc:
            logger.debug("Teclado indisponivel (%s) — painel segue sem atalhos.", exc)
            return False
        self._thread = threading.Thread(target=self._loop_leitura,
                                        name="dashboard-keys", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Para de entregar teclas e devolve o terminal ao modo canonico.

        A thread nao e aguardada: ela esta bloqueada numa leitura que so retorna
        na proxima tecla. Como e daemon e o `_parar` a faz descartar o que
        chegar, deixa-la pendurada nao segura o encerramento nem entrega tecla
        a um painel que ja morreu.
        """
        self._parar.set()
        _restaurar_terminal()

    # ── Plataforma ───────────────────────────────────────────────────────────

    def _preparar_terminal(self) -> None:
        global _ESTADO_TERMINAL, _FD_TERMINAL
        if os.name == "nt":
            return  # msvcrt.getwch() ja le sem eco e sem enter
        import termios
        import tty
        fd = sys.stdin.fileno()
        _ESTADO_TERMINAL = termios.tcgetattr(fd)
        _FD_TERMINAL = fd
        # cbreak, e nao raw: preserva o Ctrl+C como SIGINT, que continua sendo
        # o caminho de encerramento que todo mundo conhece.
        tty.setcbreak(fd)

    def _ler_uma(self) -> str | None:
        if os.name == "nt":
            import msvcrt
            ch = msvcrt.getwch()
            # Teclas especiais (setas, F1..) chegam como prefixo + codigo; o
            # segundo byte precisa ser consumido, senao vira uma tecla fantasma.
            if ch in ("\x00", "\xe0"):
                msvcrt.getwch()
                return None
            return ch
        return sys.stdin.read(1)

    def _loop_leitura(self) -> None:
        try:
            while not self._parar.is_set():
                try:
                    tecla = self._ler_uma()
                except Exception:
                    return  # stdin fechado (shutdown) — nada a relatar
                if tecla is None or self._parar.is_set():
                    continue
                loop, cb = self._loop, self._ao_receber
                if loop is None or loop.is_closed():
                    return
                try:
                    loop.call_soon_threadsafe(cb, tecla)
                except RuntimeError:
                    return  # loop encerrando
        finally:
            _restaurar_terminal()
