# executor/dashboard/runtime.py
"""
Loop de refresh do painel e os atalhos de teclado.

Dois modos, alternaveis a qualquer momento pela tecla `l`:

  PAINEL — o `Live` ocupa a tela com as estatisticas; o log passo-a-passo vai
           so para o arquivo.
  LOG    — o `Live` sai, o console volta a receber o log linha a linha (o
           comportamento historico do executor) e o arquivo continua gravando.

Alternar nao reconfigura nada pesado: o handler de arquivo e criado uma vez e
fica; so o StreamHandler do console entra e sai do root.
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

# Falhas consecutivas de render antes de o painel desistir e devolver o console.
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
        # Aceito para o painel de terminal ficar no mesmo contrato do JSON.
        # Sem isto, `_start_rich` quebrava com TypeError ao repassar o handler.
        self._ao_sincronizar = ao_sincronizar
        self._ao_sair = ao_sair
        self._ao_reconectar = ao_reconectar

        self._console = Console(stderr=False)
        # auto_refresh=False: o repaint e disparado pelo nosso tick, e nao por
        # uma thread do rich competindo com o event loop.
        # transient=False: o ultimo quadro fica na tela depois do stop, servindo
        # de resumo final da sessao.
        # vertical_overflow="crop": rede de seguranca. `render.build` ja monta o
        # painel dentro da altura do terminal, mas se algum bloco escapar do
        # calculo o rich corta em vez de rolar — o modo "ellipsis" (default)
        # empurra o quadro para cima a cada repaint e o painel vira lixo.
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

    # ── Ciclo de vida ────────────────────────────────────────────────────────

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
        """Para o `Live` e reanexa o console. Sincrona — usada tambem pelo
        `emergency_stop`, que roda fora do event loop (atexit, os.execve)."""
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
        """Tira o log do console e devolve a tela ao `Live`."""
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
                # O ultimo quadro fica na tela como resumo, mas nao termina em
                # newline: sem esta linha, a proxima mensagem gruda no rodape.
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
        """Roda NO event loop (o leitor entrega por call_soon_threadsafe)."""
        try:
            k = tecla.lower()
            repintar = True
            if k in ("l", "\t"):
                self._overlay = None
                self.alternar()
                repintar = False        # alternar ja cuida da tela
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

            # Repinta na hora em vez de esperar o proximo tick — sem isso, uma
            # tecla parece nao ter funcionado por ate um segundo inteiro.
            if repintar and self._modo == MODO_PAINEL and self._vivo:
                self._pintar()
        except Exception as exc:
            # Uma tecla nunca pode derrubar o executor.
            logger.debug("Falha ao tratar a tecla %r: %s", tecla, exc)

    def _alternar_debug(self) -> None:
        from executor import logging_setup
        ligado = logging_setup.alternar_debug()
        # Vai para o log (e para o rodape de alertas) porque muda o volume do
        # arquivo de forma drastica: quem achar o log gigante depois precisa
        # encontrar o momento em que foi ligado.
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
                    # O painel nunca pode derrubar nem cegar o executor: depois
                    # de N falhas seguidas ele se demite e o log volta ao console.
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
        # Coleta compartilhada com o modo JSON (dashboard/tick.py): os dois
        # runtimes precisam ler exatamente os mesmos numeros.
        snap = tick.coletar_snapshot(
            self._stats,
            capacity_source=self._capacity_source,
            result_queue=self._result_queue,
            outbox_pending=self._cache_outbox.get(loop.time()),
        )

        # A largura vem do Console, e nao de shutil.get_terminal_size(): e ela
        # que o rich usa para desenhar. Quando as duas divergem (sem TTY, ou com
        # COLUMNS defasado) o layout escolhe duas colunas para um espaco que so
        # comporta uma, e o rich corta o conteudo com reticencias.
        largura, altura = self._console.size
        self._live.update(
            render.build(
                snap,
                largura=largura,
                altura=altura or shutil.get_terminal_size(fallback=(100, 30)).lines,
                log_path=self._log_path,
                # conhost legado do Windows nao aguenta os blocos unicode e
                # repinta devagar — cai para ASCII nas barras.
                ascii_only=bool(getattr(self._console, "legacy_windows", False)),
                atalhos=self._com_teclado,
                pausado=self._pausado,
                overlay=self._overlay,
            ),
            refresh=True,
        )
