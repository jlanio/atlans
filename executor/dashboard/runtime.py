# executor/dashboard/runtime.py
"""
Dashboard refresh loop and keyboard shortcuts.

Two modes, switchable at any time with the `l` key:

  PAINEL — the `Live` takes over the screen with the statistics; the
           step-by-step log goes only to the file.
  LOG    — the `Live` exits, the console goes back to receiving the log line by
           line (the executor's historical behavior) and the file keeps writing.

Switching does not reconfigure anything heavy: the file handler is created once
and stays; only the console StreamHandler is added to and removed from the root.
"""
from __future__ import annotations

import asyncio
import logging
import shutil

from rich.console import Console
from rich.live import Live

from executor.dashboard import render, tick
from executor.dashboard.keys import LeitorDeTeclas

logger = logging.getLogger("executor.dashboard")

# Consecutive render failures before the dashboard gives up and hands back the console.
_MAX_FALHAS = 3

MODO_PAINEL = "painel"
MODO_LOG = "log"


class DashboardRuntime:
    def __init__(self, stats, *, capacity_source, result_queue, intervalo: float,
                 log_path: str, tail_handler: logging.Handler | None = None,
                 ao_sair=None, ao_reconectar=None, ao_sincronizar=None):
        self._stats = stats
        self._capacity_source = capacity_source
        self._result_queue = result_queue
        self._intervalo = intervalo
        self._log_path = log_path
        self._tail_handler = tail_handler
        # Accepted so the terminal dashboard follows the same contract as the JSON one.
        # Without this, `_start_rich` broke with TypeError when passing the handler on.
        self._ao_sincronizar = ao_sincronizar
        self._ao_sair = ao_sair
        self._ao_reconectar = ao_reconectar

        self._console = Console(stderr=False)
        # auto_refresh=False: the repaint is triggered by our tick, not by a
        # rich thread competing with the event loop.
        # transient=False: the last frame stays on screen after stop, serving
        # as a final summary of the session.
        # vertical_overflow="crop": safety net. `render.build` already builds the
        # dashboard within the terminal height, but if some block escapes the
        # calculation rich crops instead of scrolling — the "ellipsis" mode
        # (default) pushes the frame upward on every repaint and the dashboard
        # turns into garbage.
        self._live = Live(console=self._console, auto_refresh=False,
                          transient=False, screen=False,
                          vertical_overflow="crop")
        self._task: asyncio.Task | None = None
        self._parar = asyncio.Event()
        self._vivo = False
        self._cache_outbox = tick.CacheOutbox()

        self._modo = MODO_PAINEL
        self._pausado = False
        self._overlay: str | None = None   # None | "ajuda" | "alertas"
        self._teclas = LeitorDeTeclas(self._tecla)
        self._com_teclado = False

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._com_teclado = self._teclas.start()

        atalho = (
            "[dim]Atalhos:[/dim] [bold]l[/bold][dim] alterna painel/log · [/dim]"
            "[bold]?[/bold][dim] lista todos · [/dim][bold]q[/bold][dim] encerra[/dim]"
            if self._com_teclado else
            "[dim]Atalhos indisponiveis (stdin nao e um terminal). "
            "Desative o painel com EXECUTOR_DASHBOARD=off.[/dim]"
        )
        self._console.print(
            f"[dim]Painel ao vivo ativo. Log completo em[/dim] [cyan]{self._log_path}[/cyan]\n"
            f"{atalho}\n"
        )
        self._entrar_no_painel()
        self._task = asyncio.create_task(self._loop(), name="dashboard")

    async def stop(self) -> None:
        """Encerra o painel e devolve o console. Idempotente."""
        self._parar.set()
        self._teclas.stop()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        self.close_live()

    def close_live(self) -> None:
        """Stops the `Live` and reattaches the console. Synchronous — also used by
        `emergency_stop`, which runs outside the event loop (atexit, os.execve)."""
        self._teclas.stop()
        self._sair_do_painel()
        if self._tail_handler is not None:
            try:
                logging.getLogger().removeHandler(self._tail_handler)
            except Exception:
                pass
            self._tail_handler = None

    # ── Alternancia painel <-> log ───────────────────────────────────────────

    @property
    def modo(self) -> str:
        return self._modo

    def _entrar_no_painel(self) -> None:
        """Takes the log off the console and hands the screen back to the `Live`."""
        if self._vivo:
            return
        from executor import logging_setup
        logging_setup.switch_to_dashboard_mode()
        self._live.start(refresh=False)
        self._vivo = True
        self._modo = MODO_PAINEL

    def _sair_do_painel(self) -> None:
        """Fecha o `Live` e devolve o console. O arquivo continua gravando."""
        if self._vivo:
            self._vivo = False
            try:
                self._live.stop()
                # The last frame stays on screen as a summary, but it does not end in
                # a newline: without this line, the next message sticks to the footer.
                self._console.print()
            except Exception:
                pass
        from executor import logging_setup
        logging_setup.restore_console_mode()
        self._modo = MODO_LOG

    def alternar(self) -> None:
        if self._modo == MODO_PAINEL:
            self._sair_do_painel()
            self._console.print(
                "[dim]Modo log — o passo a passo volta para o terminal.[/dim] "
                "[bold]l[/bold][dim] devolve o painel · [/dim][bold]q[/bold][dim] encerra.[/dim]"
            )
        else:
            self._entrar_no_painel()

    # ── Teclas ───────────────────────────────────────────────────────────────

    def _tecla(self, tecla: str) -> None:
        """Runs ON the event loop (the reader delivers via call_soon_threadsafe)."""
        try:
            k = tecla.lower()
            repintar = True
            if k in ("l", "\t"):
                self._overlay = None
                self.alternar()
                repintar = False        # switching already takes care of the screen
            elif k == "p":
                self._pausado = not self._pausado
            elif k in ("?", "h"):
                self._overlay = None if self._overlay == "ajuda" else "ajuda"
            elif k == "a":
                self._overlay = None if self._overlay == "alertas" else "alertas"
            elif k == "d":
                self._alternar_debug()
            elif k == "r":
                self._reconectar()
            elif k == "z":
                self._zerar()
            elif k == "q":
                self._sair()
                repintar = False
            else:
                repintar = False        # tecla desconhecida: ignora em silencio

            # Repaints right away instead of waiting for the next tick — without this,
            # a key seems not to have worked for up to a whole second.
            if repintar and self._modo == MODO_PAINEL and self._vivo:
                self._pintar()
        except Exception as exc:
            # A key press must never bring down the executor.
            logger.debug("Falha ao tratar a tecla %r: %s", tecla, exc)

    def _alternar_debug(self) -> None:
        from executor import logging_setup
        ligado = logging_setup.alternar_debug()
        # Goes to the log (and to the alerts footer) because it changes the file's
        # volume drastically: whoever later finds the log huge needs to find the
        # moment it was turned on.
        logger.warning(
            "Nivel de log alterado para %s pela tecla 'd'.",
            "DEBUG" if ligado else "o valor de LOG_LEVEL",
        )

    def _reconectar(self) -> None:
        if self._ao_reconectar is None:
            return
        try:
            if self._ao_reconectar():
                logger.info("Tecla 'r' — backoff interrompido, reconectando agora.")
            else:
                logger.info("Tecla 'r' — nao ha espera de reconexao em curso.")
        except Exception as exc:
            logger.debug("Falha ao forcar a reconexao: %s", exc)

    def _zerar(self) -> None:
        try:
            self._stats.reset()
            logger.info("Tecla 'z' — contadores da sessao zerados.")
        except Exception as exc:
            logger.debug("Falha ao zerar os contadores: %s", exc)

    def _sair(self) -> None:
        if self._ao_sair is None:
            logger.info("Tecla 'q' — encerrando o executor...")
            return
        self._sair_do_painel()
        logger.info("Tecla 'q' — encerrando o executor...")
        try:
            self._ao_sair()
        except Exception as exc:
            logger.error("Falha ao solicitar o encerramento pela tecla 'q': %s", exc)

    # ── Loop ─────────────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        falhas = 0
        while not self._parar.is_set():
            try:
                if self._modo == MODO_PAINEL and not self._pausado:
                    self._pintar()
                falhas = 0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                falhas += 1
                logger.debug("Falha ao desenhar o painel (%d/%d): %s", falhas, _MAX_FALHAS, exc)
                if falhas >= _MAX_FALHAS:
                    # The dashboard must never bring down or blind the executor: after
                    # N consecutive failures it resigns and the log goes back to the console.
                    logger.error(
                        "Painel desligado apos %d falhas consecutivas de render — "
                        "o log volta para o console. Ultimo erro: %s",
                        falhas, exc, exc_info=True,
                    )
                    self.close_live()
                    return
            try:
                await asyncio.wait_for(self._parar.wait(), timeout=self._intervalo)
            except asyncio.TimeoutError:
                pass

    def _pintar(self) -> None:
        if not self._vivo:
            return
        loop = asyncio.get_running_loop()
        # Collection shared with the JSON mode (dashboard/tick.py): both
        # runtimes need to read exactly the same numbers.
        snap = tick.coletar_snapshot(
            self._stats,
            capacity_source=self._capacity_source,
            result_queue=self._result_queue,
            outbox_pending=self._cache_outbox.get(loop.time()),
        )

        # The width comes from the Console, not from shutil.get_terminal_size(): it is
        # what rich uses to draw. When the two diverge (no TTY, or a stale
        # COLUMNS) the layout picks two columns for a space that only fits one,
        # and rich truncates the content with ellipses.
        largura, altura = self._console.size
        self._live.update(
            render.build(
                snap,
                largura=largura,
                altura=altura or shutil.get_terminal_size(fallback=(100, 30)).lines,
                log_path=self._log_path,
                # the legacy Windows conhost cannot handle the unicode blocks and
                # repaints slowly — falls back to ASCII for the bars.
                ascii_only=bool(getattr(self._console, "legacy_windows", False)),
                atalhos=self._com_teclado,
                pausado=self._pausado,
                overlay=self._overlay,
            ),
            refresh=True,
        )
