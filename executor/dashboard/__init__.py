# executor/dashboard/__init__.py
"""
Painel de estatisticas ao vivo no terminal.

Substitui o log passo-a-passo do console por um resumo que se atualiza sozinho.
O log continua inteiro — vai para um arquivo rotativo, que passa a ser ligado
por padrao quando o painel assume (ver `logging_setup.switch_to_dashboard_mode`).

Este modulo NAO importa `rich`. Os modulos que importam (`render`, `runtime`)
so sao carregados dentro de `start()`, depois de o gate aprovar — assim um
executor com o painel desligado nao paga nada.
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

# Modos possiveis. O gate devolve um destes, e nao um booleano: com a chegada do
# app desktop passaram a existir DOIS consumidores do coletor de estatisticas —
# o terminal e um supervisor — e "ligado/desligado" nao distingue os dois.
MODO_RICH = "rich"
MODO_JSON = "json"
MODO_OFF = "off"

# Abaixo disso o painel sai cortado, o que e pior que nao existir.
_MIN_LARGURA = 60
_MIN_ALTURA = 12

_runtime = None


def rich_disponivel() -> bool:
    """`find_spec` em vez de `import`: nao paga o custo de carregar o rich
    quando o painel esta desligado."""
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
    """Decide o modo do coletor. Funcao pura — sem TTY real, sem os.environ.

    Retorna `(modo, motivo)`, com `modo` em {"rich", "json", "off"}. O motivo e
    sempre preenchido quando o resultado NAO e o painel: um painel que nao
    aparece sem explicacao vira ticket de suporte.

    `json` e sempre explicito, nunca inferido: quem escreve NDJSON no stdout de
    quem esperava log humano quebra o consumidor em silencio. Quem quer o canal
    estruturado pede por `EXECUTOR_DASHBOARD=json` — e o que o app desktop faz
    ao dar spawn no processo.
    """
    modo = (env.get("EXECUTOR_DASHBOARD") or "auto").strip().lower()

    # Antes de tudo: nao depende de rich, de TTY nem de tamanho de terminal.
    # O consumidor e um programa.
    if modo in _JSON:
        return MODO_JSON, "canal NDJSON por EXECUTOR_DASHBOARD"

    if modo in _LIGADO:
        return MODO_OFF, "desativado por EXECUTOR_DASHBOARD"

    if not rich_ok:
        return MODO_OFF, "biblioteca 'rich' nao instalada (pip install rich)"

    # Escape hatch consciente: quem passa `on` sabe o que esta fazendo.
    if modo in _FORCADO:
        return MODO_RICH, "forcado por EXECUTOR_DASHBOARD"

    # A partir daqui, modo == auto.
    if not stdout_tty or not stderr_tty:
        # Cobre Docker sem -it, systemd/journald, `| tee` e o app desktop, que
        # captura a saida do processo por pipe.
        return MODO_OFF, "stdout/stderr nao e um terminal interativo"

    if (env.get("LOG_COLOR") or "").strip().lower() == "never":
        # O operador ja pediu saida sem enfeite; e o que o compose do executor usa.
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
    """Sobe o runtime do `modo` pedido e devolve o objeto (com `stop()`).

    `ao_sair` e chamado pela tecla 'q' ou pelo comando `shutdown` — deve
    disparar o mesmo shutdown ordenado de um SIGTERM. `ao_reconectar` responde
    ao 'r' / `reconnect` e deve interromper o backoff da conexao.

    Retorna `None` se nao foi possivel ligar. Nao levanta: qualquer falha aqui
    deixa o executor no modo de log normal, funcionando.
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
    """Painel `rich`: troca o console pelo arquivo e sobe o loop de refresh."""
    global _runtime

    from executor import logging_setup

    try:
        caminho = logging_setup.switch_to_dashboard_mode()
    except logging_setup.LoggingSetupError as exc:
        # A regra: o painel so liga se o arquivo abrir. Trocar o log do console
        # por um arquivo que nao existe seria apagar o log, nao move-lo.
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
        # O tail ja podia estar no root: deixa-lo la alimentaria para sempre um
        # coletor que ninguem le.
        if tail is not None:
            logging.getLogger().removeHandler(tail)
        logging_setup.restore_console_mode()
        _runtime = None
        return None


async def _start_json(stats, *, capacity_source, result_queue, intervalo,
                      ao_sair, ao_reconectar, ao_sincronizar):
    """Canal NDJSON no stdout.

    Nao mexe no logging do console: ele escreve em stderr, que continua sendo o
    log humano lido pelo supervisor. O arquivo rotativo e ligado se possivel,
    mas a falha dele NAO impede o canal — diferente do painel rich, aqui nao ha
    tela sendo tomada, entao nao ha log a ser perdido.
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

        # Sem esta linha o canal emite APENAS snapshots periodicos, e todo
        # evento imediato — job, sync, conn — simplesmente nunca sai. O sintoma
        # e um painel com metricas corretas e historico de execucoes
        # permanentemente vazio: `last_finished` do snapshot guarda um job so, e
        # o consumidor nao tem como reconstruir a lista a partir dele.
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
    """Fecha o painel e devolve o terminal. Sincrona, idempotente, sem event loop.

    Existe para os caminhos que nao passam pelo shutdown ordenado: excecao nao
    tratada, `SystemExit`, `KeyboardInterrupt` e o `os.execve` do auto-restart.
    Sem ela o processo morre (ou e substituido) deixando o terminal no buffer
    alternativo, sem cursor — o usuario ve a tela limpar e nada mais.
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
