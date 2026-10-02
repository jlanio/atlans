# executor/supervisor.py
"""
Watchdog do processo supervisor.

Quando o executor e iniciado por um supervisor externo — o app desktop —, o
supervisor passa o proprio PID em `EXECUTOR_SUPERVISOR_PID`. Se ele morrer sem
encerrar o filho (usuario matando o app pelo Gerenciador de Tarefas, crash do
Electron), o executor ficaria vivo, orfao e invisivel: sem janela, sem tray, e
ainda segurando a conexao WebSocket com o mesmo EXECUTOR_ID. Da proxima vez que
o app subisse, o servidor veria DUAS conexoes do mesmo executor.

A alternativa canonica no Windows seria um Job Object com
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, que mata o filho junto com o pai. Foi
descartada porque exige modulo nativo (`node-gyp`, rebuild a cada versao do
Electron, assinatura do `.node`) para resolver o que 60 linhas resolvem —
`psutil` ja e dependencia do executor, usada por `sysinfo.py`.

O encerramento e ORDENADO: dispara o mesmo `shutdown_event` de um SIGTERM, entao
jobs em andamento sao drenados e resultados confirmados. Matar na hora perderia
trabalho ja feito.
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger("executor.supervisor")

INTERVALO_S = 5.0
VAR_PID = "EXECUTOR_SUPERVISOR_PID"


def pid_configurado() -> int | None:
    """PID do supervisor, ou None se o executor nao foi iniciado por um.

    Rodar `python -m executor` na mao nao define a variavel, entao o watchdog
    simplesmente nao sobe — nao ha nada para vigiar.
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
    """Verifica periodicamente se o supervisor continua vivo.

    Compara PID **e** `create_time()`. So o PID nao basta: o sistema operacional
    reaproveita numeros de processo, e um PID reciclado por outro programa faria
    o watchdog concluir que o supervisor esta vivo quando ha muito morreu — o
    orfao que ele existe para evitar.
    """

    def __init__(self, pid: int, *, intervalo: float = INTERVALO_S) -> None:
        self._pid = pid
        self._intervalo = intervalo
        self._proc = None
        self._criado_em: float | None = None

    def vincular(self) -> bool:
        """Fixa a identidade do supervisor. False se ele ja nao existe."""
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
            # Zumbi ainda "roda" para o is_running(); nao serve de supervisor.
            import psutil
            if proc.status() == psutil.STATUS_ZOMBIE:
                return False
            return proc.create_time() == self._criado_em
        except Exception:
            # NoSuchProcess, AccessDenied num processo que virou de outro dono —
            # todos significam "o supervisor que eu conhecia se foi".
            return False

    async def vigiar(self, ao_morrer) -> None:
        """Loop ate o supervisor sumir; entao chama `ao_morrer` uma unica vez."""
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
        # O supervisor morreu entre o spawn e este ponto. Encerrar ja e o certo:
        # ninguem vai consumir o canal NDJSON nem parar este processo depois.
        ao_morrer()
        return None
    logger.info("Watchdog do supervisor ativo (PID %d, a cada %.0fs).", pid, intervalo)
    return asyncio.create_task(monitor.vigiar(ao_morrer), name="supervisor-watchdog")
