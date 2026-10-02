# executor/sync/queue.py
"""
SyncQueue — fila resiliente com retry exponencial para operacoes de sync.
"""
import logging
import time
from typing import Callable, Awaitable

from flow.utils.backoff import espera_exponencial

from executor.sync.manifest import SyncManifest

logger = logging.getLogger("executor.sync")

_MAX_RETRIES = 10
_MAX_BACKOFF = 300  # 5 minutos


class SyncQueue:
    """Processa operacoes pendentes do manifesto com retry exponencial.

    O backoff e AGENDADO, nunca dormido: `process_pending()` roda no topo do
    ciclo, antes da deteccao de mudanca local, e um `asyncio.sleep(300)` aqui
    dentro congelava a pasta inteira — com 5 itens falhando, ela podia ficar
    ~25 minutos sem reagir a nenhum arquivo novo, mesmo com a rede ja de volta.
    O tick de `SYNC_INTERVAL` (30s) e a batida natural do retry: cada ciclo so
    PULA o que ainda nao venceu.
    """

    def __init__(self, manifest: SyncManifest, executor: Callable[[dict], Awaitable[bool]]):
        self.manifest = manifest
        self.executor = executor

    async def process_pending(self):
        """Processa os itens da fila cujo horario de tentativa ja venceu."""
        items = self.manifest.pending_items()
        if not items:
            return

        agora = time.time()

        for item in list(items):
            dataset_name = item["dataset"]
            retries = item.get("retries", 0)

            if retries >= _MAX_RETRIES:
                logger.error("Sync '%s': limite de retries (%d) atingido — desistindo.",
                             dataset_name, _MAX_RETRIES)
                self.manifest.dequeue(dataset_name)
                # Sair da fila nao basta para uma operacao de DELETE: o dataset
                # continuava no manifesto, o proximo `diff` o via de novo como
                # "removido localmente" (ele ja nao esta no disco), enfileirava
                # de novo — e o ciclo recomecava do zero a cada varredura, para
                # sempre. Desistir precisa significar parar de tentar.
                if item.get("action") == "delete":
                    self.manifest.remove_dataset(dataset_name)
                continue

            # Item sem `next_attempt_at` (fila gravada antes do agendamento)
            # conta como "tentar agora".
            proxima = item.get("next_attempt_at") or 0.0

            # O agendamento e epoch de RELOGIO DE PAREDE e sobrevive a reinicios
            # dentro do manifesto. Num notebook de campo que boota adiantado (CMOS
            # ruim) e depois e corrigido pelo NTP, o item ficava agendado para um
            # futuro que nunca chega — congelado para sempre. Para 'upload' e
            # 'delete' o diff acabava re-dirigindo a operacao; o 'discard' nao tem
            # outro motor, e o arquivo que o Drive mandou apagar ficava no disco do
            # tecnico sem nenhum erro no log. Nenhum agendamento legitimo passa de
            # `agora + _MAX_BACKOFF`: mais que isso so pode ser relogio bagunçado.
            if proxima > agora + _MAX_BACKOFF:
                logger.warning(
                    "Sync '%s': agendamento de retry no futuro impossivel (%.0fs a frente) — "
                    "relogio do sistema mudou; tentando agora.", dataset_name, proxima - agora)
                proxima = 0.0

            if proxima > agora:
                continue

            try:
                success = await self.executor(item)
                if success:
                    self.manifest.dequeue(dataset_name)
                    logger.info("Sync '%s': operacao concluida com sucesso.", dataset_name)
                else:
                    delay = espera_exponencial(retries, teto=_MAX_BACKOFF)
                    self.manifest.update_retry(item, agora + delay)
                    logger.warning("Sync '%s': falhou (tentativa %d) — proximo retry em %.1fs.",
                                   dataset_name, retries + 1, delay)
            except Exception as e:
                delay = espera_exponencial(retries, teto=_MAX_BACKOFF)
                self.manifest.update_retry(item, agora + delay)
                logger.error("Sync '%s': erro (%s) — proximo retry em %.1fs.",
                             dataset_name, e, delay)
