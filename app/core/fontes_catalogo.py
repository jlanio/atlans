# app/core/fontes_catalogo.py
"""
Source catalog: the seed is loaded at startup and the endpoints are verified
periodically.

Two background tasks of the API lifespan (the lock and the loop are those of
`app/core/tarefas_periodicas.py`):

- `importar_catalogo_no_arranque()` runs ONCE at startup: reads
  `FONTES_CATALOGO_DIR` (the versioned copy of the Vault, `catalogo/geoservicos`)
  and imports the layers as platform sources. It is idempotent by hash —
  with the folder unchanged since the last startup it costs one query and zero
  writes. NX lock in Redis so that only one uvicorn worker imports; the others
  only load the synonyms (`_sinonimos.md`), which live in each process's
  memory. Then, an initial verification of only what is pending (never
  verified or stale), so the seed is born with `estado` filled in.
- `run_verificacao_loop()` repeats the verification every
  `FONTES_VERIFICACAO_INTERVAL` seconds. 0 turns both off — no probing
  leaves the server on its own.

Verification is PER ENDPOINT: one GetCapabilities per distinct URL marks all
the layers of that URL (77 requests for 25 thousand rows in the seed), at most
`_PARALLELISM` in parallel and with a jittered pause between them, so as not to
look like a scan to whoever hosts the service. One endpoint's failure does not
stop the round.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import inspect

from app.core import tarefas_periodicas
from app.core.config import FONTES_CATALOGO_DIR, FONTES_VERIFICACAO_INTERVAL
from app.core.db import AsyncSessionLocal
from app.core.utils.logger import get_logger
from app.models.fonte_de_dados import DataSource
from app.services import fontes_service, fontes_vault
from flow.utils.backoff import with_jitter

logger = get_logger(__name__)

# Redis down: both routines proceed WITHOUT a lock — they are idempotent, so the
# worst case is repeated work, not wrong data.
_IMPORT_LOCK = "fontes_catalogo:lock"
_VERIFICATION_LOCK = "fontes_verificacao:lock"
_IMPORT_LOCK_TTL_S = 600
# The API starts with an empty database and the guide says to migrate AFTERWARDS
# (`alembic upgrade head`): the import waits for the catalog table to appear, up to this long.
_ESPERA_PELO_SCHEMA_S = 600
_INTERVALO_DA_ESPERA_S = 5
# Endpoints probed at the same time and the pause (with jitter) before each one.
_PARALLELISM = 2
_PAUSA_ENTRE_ENDPOINTS_S = 1.0


@dataclass
class RoundSummary:
    endpoints: int = 0
    ok: int = 0         # camadas marked `ok`
    falhando: int = 0   # camadas marked `falhando`
    fora: int = 0       # endpoints that did not answer GetCapabilities
    erros: int = 0      # unexpected exceptions (database, bug) — the round goes on

    def as_text(self) -> str:
        return (
            f"{self.endpoints} endpoint(s): {self.ok} camada(s) ok, {self.falhando} falhando, "
            f"{self.fora} endpoint(s) fora do ar, {self.erros} erro(s)"
        )


async def verificar_endpoints(*, only_pending: bool = False) -> RoundSummary:
    """One round: one GetCapabilities per distinct URL, `_PARALLELISM` at a time.

    `only_pending`: only the URLs with some layer never verified or older
    than the interval. Each endpoint has its own database session — one that
    fails (network or database) does not bring down the others.
    """
    resumo = RoundSummary()
    async with AsyncSessionLocal() as db:
        endpoints = await fontes_service.endpoints_to_verify(
            db, stale_for=FONTES_VERIFICACAO_INTERVAL if only_pending else None
        )
    resumo.endpoints = len(endpoints)
    if not endpoints:
        return resumo
    semaforo = asyncio.Semaphore(_PARALLELISM)

    async def _um(url: str, version: str) -> None:
        async with semaforo:
            pausa = with_jitter(_PAUSA_ENTRE_ENDPOINTS_S)
            if pausa > 0:
                await asyncio.sleep(pausa)
            try:
                async with AsyncSessionLocal() as db:
                    parcial = await fontes_service.verify_endpoint(db, url, version)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                resumo.erros += 1
                logger.warning("Fontes: verificação de %s falhou: %s", url, exc)
                return
            resumo.ok += parcial.ok
            resumo.falhando += parcial.falhando
            if parcial.erro:
                resumo.fora += 1

    await asyncio.gather(*(_um(url, version) for url, version in endpoints))
    logger.info("Fontes: verificação concluída — %s.", resumo.as_text())
    return resumo


async def _schema_pronto() -> bool:
    """Does the catalog table already exist in the database? (Postgres or the tests' SQLite.)"""
    try:
        async with AsyncSessionLocal() as db:
            conexao = await db.connection()
            return bool(await conexao.run_sync(lambda c: inspect(c).has_table(DataSource.__tablename__)))
    except Exception as exc:
        logger.debug("Fontes: não deu para consultar o schema: %s", exc)
        return False


async def importar_catalogo_no_arranque() -> "fontes_service.ResumoDaImportacao | None":
    """Import the catalog folder (if it exists) and verify what is pending.

    Returns the import summary, or None when there was nothing to import
    (empty flag, missing folder, another worker holding the lock) or when it
    failed — the API starts all the same; the catalog is an extra, not a
    prerequisite.
    """
    caminho = (FONTES_CATALOGO_DIR or "").strip()
    if not caminho:
        logger.info("Fontes: FONTES_CATALOGO_DIR vazio — sem importação do catálogo.")
        return None
    raiz = Path(caminho)
    if not raiz.is_dir():
        logger.info("Fontes: pasta do catálogo não existe (%s) — sem importação.", raiz)
        return None

    # The synonyms live in the process memory: EVERY worker loads them, whether
    # or not it got the import lock.
    try:
        fontes_service.set_synonyms(await asyncio.to_thread(fontes_vault.synonyms_of, raiz))
    except Exception as exc:
        logger.warning("Fontes: não deu para ler %s/_sinonimos.md: %s", raiz, exc)

    # Without the table, the import failed once, the 10-minute lock stayed
    # held and the next recreation of the API (the one the guide calls for right
    # after `alembic upgrade head`) skipped the import: the catalog was born
    # empty, with the smoke test green. We wait for the schema; the lock is only
    # taken at import time.
    esperou = 0.0
    while not await _schema_pronto():
        if esperou == 0:
            logger.info("Fontes: a tabela do catálogo ainda não existe (alembic upgrade head pendente?) — a importação espera.")
        if esperou >= _ESPERA_PELO_SCHEMA_S:
            logger.warning(
                "Fontes: o schema não apareceu em %d s — a importação do catálogo fica para a próxima subida.",
                _ESPERA_PELO_SCHEMA_S,
            )
            return None
        await asyncio.sleep(_INTERVALO_DA_ESPERA_S)
        esperou += _INTERVALO_DA_ESPERA_S

    if not await tarefas_periodicas.adquirir_lock(_IMPORT_LOCK, _IMPORT_LOCK_TTL_S):
        logger.debug("Fontes: outro worker está importando o catálogo — pulando.")
        return None
    try:
        async with AsyncSessionLocal() as db:
            resumo = await fontes_service.importar_pasta(db, raiz)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Fontes: importação do catálogo %s falhou: %s", raiz, exc, exc_info=True)
        # Whoever failed releases the lock: the next startup tries again, without waiting for the TTL.
        await tarefas_periodicas.soltar_lock(_IMPORT_LOCK)
        return None
    logger.info("Fontes: catálogo %s importado — %s.", raiz, resumo.as_text())
    for erro in resumo.erros[:10]:
        logger.warning("Fontes: %s", erro)

    if FONTES_VERIFICACAO_INTERVAL <= 0:
        return resumo
    try:
        await verificar_endpoints(only_pending=True)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Fontes: verificação inicial falhou: %s", exc, exc_info=True)
    return resumo


async def run_verificacao_loop() -> None:
    """Infinite loop: every FONTES_VERIFICACAO_INTERVAL seconds, one round of
    `verificar_endpoints()` — only on the worker that takes the interval's Redis lock.
    Started as a background task in the API lifespan; 0 turns it off."""
    intervalo = FONTES_VERIFICACAO_INTERVAL
    if intervalo <= 0:
        logger.info("Fontes: verificação periódica desligada (FONTES_VERIFICACAO_INTERVAL=0).")
        return
    await tarefas_periodicas.periodic_loop(
        "Fontes: verificação periódica", intervalo, verificar_endpoints, lock=_VERIFICATION_LOCK
    )
