# app/core/fontes_catalogo.py
"""
Catálogo de fontes: a semente entra no arranque e os endpoints são verificados
por período.

Duas tarefas de fundo do lifespan da API (o lock e o laço são os de
`app/core/tarefas_periodicas.py`):

- `importar_catalogo_no_arranque()` roda UMA vez na subida: lê
  `FONTES_CATALOGO_DIR` (a cópia versionada do Vault, `catalogo/geoservicos`)
  e importa as camadas como fontes da plataforma. É idempotente por hash —
  com a pasta igual à da última subida custa uma consulta e zero escritas.
  Lock NX no Redis para que só um worker uvicorn importe; os outros só
  carregam os sinônimos (`_sinonimos.md`), que vivem na memória de cada
  processo. Depois, uma verificação inicial só do que está pendente (nunca
  verificado ou vencido), para a semente nascer com `estado` preenchido.
- `run_verificacao_loop()` repete a verificação a cada
  `FONTES_VERIFICACAO_INTERVAL` segundos. 0 desliga as duas — nenhuma
  sondagem parte do servidor por conta própria.

A verificação é POR ENDPOINT: um GetCapabilities por URL distinta marca todas
as camadas daquela URL (77 pedidos para 25 mil linhas na semente), no máximo
`_PARALELISMO` em paralelo e com uma pausa dispersa entre eles, para não parecer
varredura a quem hospeda o serviço. Falha de um endpoint não para a rodada.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import inspect

from app.core import tarefas_periodicas
from app.core.config import FONTES_CATALOGO_DIR, FONTES_VERIFICACAO_INTERVAL
from app.core.db import AsyncSessionLocal
from app.core.utils.logger import get_logger
from app.models.fonte_de_dados import FonteDeDados
from app.services import fontes_service, fontes_vault
from flow.utils.backoff import com_jitter

logger = get_logger(__name__)

# Redis fora: as duas rotinas prosseguem SEM lock — são idempotentes, então o
# pior caso é trabalho repetido, não dado errado.
_LOCK_IMPORTACAO = "fontes_catalogo:lock"
_LOCK_VERIFICACAO = "fontes_verificacao:lock"
_TTL_LOCK_IMPORTACAO_S = 600
# A API sobe com o banco vazio e o guia manda migrar DEPOIS (`alembic upgrade
# head`): a importação espera a tabela do catálogo aparecer, até este tanto.
_ESPERA_PELO_SCHEMA_S = 600
_INTERVALO_DA_ESPERA_S = 5
# Endpoints sondados ao mesmo tempo e a pausa (com jitter) antes de cada um.
_PARALELISMO = 2
_PAUSA_ENTRE_ENDPOINTS_S = 1.0


@dataclass
class ResumoDaRodada:
    endpoints: int = 0
    ok: int = 0         # camadas marcadas `ok`
    falhando: int = 0   # camadas marcadas `falhando`
    fora: int = 0       # endpoints que não responderam ao GetCapabilities
    erros: int = 0      # exceções inesperadas (banco, bug) — a rodada segue

    def como_texto(self) -> str:
        return (
            f"{self.endpoints} endpoint(s): {self.ok} camada(s) ok, {self.falhando} falhando, "
            f"{self.fora} endpoint(s) fora do ar, {self.erros} erro(s)"
        )


async def verificar_endpoints(*, apenas_pendentes: bool = False) -> ResumoDaRodada:
    """Uma rodada: um GetCapabilities por URL distinta, `_PARALELISMO` por vez.

    `apenas_pendentes`: só as URLs com alguma camada nunca verificada ou mais
    velha que o intervalo. Cada endpoint tem a própria sessão de banco — um
    que falhe (rede ou banco) não derruba os outros.
    """
    resumo = ResumoDaRodada()
    async with AsyncSessionLocal() as db:
        endpoints = await fontes_service.endpoints_para_verificar(
            db, desatualizados_ha=FONTES_VERIFICACAO_INTERVAL if apenas_pendentes else None
        )
    resumo.endpoints = len(endpoints)
    if not endpoints:
        return resumo
    semaforo = asyncio.Semaphore(_PARALELISMO)

    async def _um(url: str, version: str) -> None:
        async with semaforo:
            pausa = com_jitter(_PAUSA_ENTRE_ENDPOINTS_S)
            if pausa > 0:
                await asyncio.sleep(pausa)
            try:
                async with AsyncSessionLocal() as db:
                    parcial = await fontes_service.verificar_endpoint(db, url, version)
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
    logger.info("Fontes: verificação concluída — %s.", resumo.como_texto())
    return resumo


async def _schema_pronto() -> bool:
    """A tabela do catálogo já existe no banco? (Postgres ou o SQLite dos testes.)"""
    try:
        async with AsyncSessionLocal() as db:
            conexao = await db.connection()
            return bool(await conexao.run_sync(lambda c: inspect(c).has_table(FonteDeDados.__tablename__)))
    except Exception as exc:
        logger.debug("Fontes: não deu para consultar o schema: %s", exc)
        return False


async def importar_catalogo_no_arranque() -> "fontes_service.ResumoDaImportacao | None":
    """Importa a pasta do catálogo (se existir) e verifica o que está pendente.

    Devolve o resumo da importação, ou None quando não havia o que importar
    (flag vazia, pasta inexistente, outro worker com o lock) ou quando falhou —
    a API sobe do mesmo jeito; o catálogo é acessório, não pré-requisito.
    """
    caminho = (FONTES_CATALOGO_DIR or "").strip()
    if not caminho:
        logger.info("Fontes: FONTES_CATALOGO_DIR vazio — sem importação do catálogo.")
        return None
    raiz = Path(caminho)
    if not raiz.is_dir():
        logger.info("Fontes: pasta do catálogo não existe (%s) — sem importação.", raiz)
        return None

    # Os sinônimos moram na memória do processo: TODO worker carrega, tenha ou
    # não ficado com o lock da importação.
    try:
        fontes_service.definir_sinonimos(await asyncio.to_thread(fontes_vault.sinonimos_de, raiz))
    except Exception as exc:
        logger.warning("Fontes: não deu para ler %s/_sinonimos.md: %s", raiz, exc)

    # Sem a tabela, a importação falhava uma vez, o lock de 10 minutos ficava
    # preso e a recriação seguinte da API (a que o guia manda logo depois do
    # `alembic upgrade head`) pulava a importação: o catálogo nascia vazio, com
    # o smoke verde. Espera-se o schema; o lock só é tomado na hora de importar.
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

    if not await tarefas_periodicas.adquirir_lock(_LOCK_IMPORTACAO, _TTL_LOCK_IMPORTACAO_S):
        logger.debug("Fontes: outro worker está importando o catálogo — pulando.")
        return None
    try:
        async with AsyncSessionLocal() as db:
            resumo = await fontes_service.importar_pasta(db, raiz)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Fontes: importação do catálogo %s falhou: %s", raiz, exc, exc_info=True)
        # Quem falhou devolve o lock: a próxima subida tenta de novo, sem esperar o TTL.
        await tarefas_periodicas.soltar_lock(_LOCK_IMPORTACAO)
        return None
    logger.info("Fontes: catálogo %s importado — %s.", raiz, resumo.como_texto())
    for erro in resumo.erros[:10]:
        logger.warning("Fontes: %s", erro)

    if FONTES_VERIFICACAO_INTERVAL <= 0:
        return resumo
    try:
        await verificar_endpoints(apenas_pendentes=True)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Fontes: verificação inicial falhou: %s", exc, exc_info=True)
    return resumo


async def run_verificacao_loop() -> None:
    """Loop infinito: a cada FONTES_VERIFICACAO_INTERVAL segundos, uma rodada de
    `verificar_endpoints()` — só no worker que pegar o lock Redis do intervalo.
    Iniciado como background task no lifespan da API; 0 desliga."""
    intervalo = FONTES_VERIFICACAO_INTERVAL
    if intervalo <= 0:
        logger.info("Fontes: verificação periódica desligada (FONTES_VERIFICACAO_INTERVAL=0).")
        return
    await tarefas_periodicas.laco_periodico(
        "Fontes: verificação periódica", intervalo, verificar_endpoints, lock=_LOCK_VERIFICACAO
    )
