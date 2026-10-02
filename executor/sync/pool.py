# executor/sync/pool.py
"""
Pools de threads proprios do GeoSync.

Todo `asyncio.to_thread` cai no executor DEFAULT do loop — que o main.py
dimensiona a partir de MAX_CONCURRENT justamente para dar folga aos JOBS. O
sync mandava para la a varredura, o MD5 da pasta inteira, o `validate_dataset`
(geopandas/rasterio), o `extract_metadata` e o zip do shapefile: um `diff` de
pasta grande segurava uma thread por minutos e os nos de I/O dos workflows
ficavam esperando thread livre, sem que nada no painel explicasse a lentidao.

Com pools separados e pequenos, o sync nunca consome mais que
`SYNC_THREADS + SYNC_IO_THREADS` threads, aconteca o que acontecer. Eles sao
UNICOS no processo (nao por pasta): com uma pasta ou com cinco, o teto de
threads do GeoSync e o mesmo.

Sao DOIS pools porque as cargas nao se parecem:

  * `em_thread` — trabalho pesado e demorado: varredura, MD5, validacao,
    metadados, zip do bundle, gravacao do manifesto. Poucas threads.
  * `em_thread_io` — os chunks de 1 MB do PUT/GET das transferencias. Cada
    chamada e curtissima, mas precisa de vazao CONTINUA: com tudo no mesmo pool
    de 2 threads, bastavam dois `_write_zip`/`extract_metadata` pesados para
    parar todas as transferencias em voo por minutos. O socket ficava sem dados,
    o MinIO derrubava a conexao por ociosidade e o upload ia para a fila de
    retry — perda de vazao exatamente quando havia mais o que enviar.
"""
import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor

from executor.sync.sync_config import SYNC_IO_THREADS, SYNC_THREADS

logger = logging.getLogger("executor.sync")

_pool: ThreadPoolExecutor | None = None
_pool_io: ThreadPoolExecutor | None = None


def _obter_pool() -> ThreadPoolExecutor:
    """Cria o pool de trabalho pesado na primeira utilizacao.

    Preguicoso porque os SyncManagers sao construidos antes do event loop subir
    (e antes de qualquer varredura acontecer) — criar threads ali seria pagar
    por um GeoSync que talvez nem esteja configurado.
    """
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=SYNC_THREADS, thread_name_prefix="geosync")
        logger.debug("Pool do GeoSync criado com %d thread(s).", SYNC_THREADS)
    return _pool


def _obter_pool_io() -> ThreadPoolExecutor:
    """Cria o pool de I/O das transferencias na primeira utilizacao."""
    global _pool_io
    if _pool_io is None:
        _pool_io = ThreadPoolExecutor(max_workers=SYNC_IO_THREADS,
                                      thread_name_prefix="geosync-io")
        logger.debug("Pool de I/O do GeoSync criado com %d thread(s).", SYNC_IO_THREADS)
    return _pool_io


async def _executar(pool: ThreadPoolExecutor, func, *args, **kwargs):
    """`run_in_executor` nao aceita kwargs — por isso o `partial`."""
    loop = asyncio.get_running_loop()
    if kwargs:
        func = functools.partial(func, **kwargs)
    return await loop.run_in_executor(pool, func, *args)


async def em_thread(func, *args, **kwargs):
    """Trabalho pesado do sync (varredura, MD5, validacao, zip, manifesto)."""
    return await _executar(_obter_pool(), func, *args, **kwargs)


async def em_thread_io(func, *args, **kwargs):
    """Leitura/gravacao de bytes das transferencias — pool proprio, com vazao.

    Usar `em_thread` aqui acoplava o progresso de todo PUT/GET em voo a duracao
    do zip/validate que estivesse ocupando as 2 threads do pool pesado.
    """
    return await _executar(_obter_pool_io(), func, *args, **kwargs)
