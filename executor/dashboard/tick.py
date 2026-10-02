# executor/dashboard/tick.py
"""
Coleta de um `Snapshot` — o unico lugar que junta os numeros do tick.

Extraido de `runtime.DashboardRuntime._pintar` quando o modo JSON apareceu.
Duplicar a chamada nos dois runtimes garantiria divergencia: bastaria alguem
adicionar um argumento em `stats.snapshot()` e lembrar de um lado so, e o painel
do terminal e a GUI passariam a mostrar numeros diferentes do mesmo executor —
sem erro, sem log, sem jeito de perceber olhando um deles.

O cache do outbox mora aqui pelo mesmo motivo: e uma consulta SQLite sincrona, e
faze-la a cada tick seria I/O de disco a 1 Hz dentro do event loop, para um
numero que muda devagar.

O espaco em disco tinha exatamente o mesmo problema — e pior, porque a pasta de
artefatos pode estar numa unidade de rede — mas o cache dele mora dentro do
proprio `sysinfo` (`TTL_DISCO_S`), e nao aqui: `connection._capacity_loop` le as
mesmas metricas e precisa da mesma protecao sem passar por este modulo.
"""
from __future__ import annotations

import logging

from executor import sysinfo

logger = logging.getLogger("executor.dashboard")

# Intervalo entre consultas ao outbox. Ver o docstring do modulo.
INTERVALO_OUTBOX_S = 5.0


def contar_outbox() -> int:
    """Pendentes no outbox SQLite. Nunca levanta — 0 e melhor que derrubar o tick."""
    try:
        from executor import result_store
        return result_store.count_pending()
    except Exception:
        return 0


class CacheOutbox:
    """Guarda a ultima contagem e so reconsulta a cada `INTERVALO_OUTBOX_S`.

    Recebe o relogio por parametro (`loop.time`) em vez de chamar
    `asyncio.get_running_loop()` internamente: assim e testavel sem event loop.
    """

    def __init__(self, intervalo: float = INTERVALO_OUTBOX_S) -> None:
        self._intervalo = intervalo
        self._valor = 0
        self._proximo = 0.0

    def get(self, agora: float) -> int:
        if agora >= self._proximo:
            self._proximo = agora + self._intervalo
            self._valor = contar_outbox()
        return self._valor


def coletar_snapshot(stats, *, capacity_source, result_queue, outbox_pending: int):
    """Monta o `Snapshot` do tick.

    `capacity_source` e `result_queue` sao lidos "na hora" de proposito — e o
    contrato de `stats.snapshot()`, que nao guarda referencia a objeto vivo do
    executor. Os dois sao tolerantes a falha: uma fila que estourou no `qsize()`
    nao pode apagar o painel inteiro.
    """
    try:
        capacity = capacity_source() if capacity_source else None
    except Exception as exc:
        logger.debug("capacity_source falhou no tick: %s", exc)
        capacity = None

    try:
        result_queue_size = result_queue.qsize() if result_queue else 0
    except Exception:
        result_queue_size = 0

    return stats.snapshot(
        capacity=capacity,
        recursos=sysinfo._get_dynamic_metrics(),
        processo=sysinfo.process_metrics(),
        outbox_pending=outbox_pending,
        result_queue_size=result_queue_size,
    )
