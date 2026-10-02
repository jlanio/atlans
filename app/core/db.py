#/app/core/db.py
import asyncio
import re
import ssl
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import (
    DATABASE_URL,
    DB_COMMAND_TIMEOUT,
    DB_STATEMENT_TIMEOUT,
    ECHO_SQL,
    POOL_SIZE,
    MAX_OVERFLOW,
    POOL_TIMEOUT,
    POOL_RECYCLE,
    POOL_PRE_PING,
)
from app.core.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_url(url: str) -> tuple[str, dict]:
    """
    Extrai ssl/sslmode da DATABASE_URL e retorna (url_limpa, connect_args) para asyncpg.

    - Sem parâmetro SSL → desabilita SSL explicitamente (asyncpg tenta SSL por padrão,
      o que pode causar timeout em servidores que aceitam mas não completam o handshake).
    - ssl=disable / ssl=false → ssl=False
    - ssl=require / sslmode=require → SSLContext com ou sem CA cert.
    """
    match = re.search(r'[?&](ssl|sslmode)=([^&]+)', url)

    if not match:
        # asyncpg tenta SSL por padrão — desabilita explicitamente quando não solicitado
        return url, {"ssl": False}

    full_param = match.group(0)
    ssl_value  = match.group(2).lower()

    # Remove o parâmetro da URL e normaliza separadores
    clean = url.replace(full_param, "")
    clean = re.sub(r'\?&', '?', clean)
    clean = re.sub(r'[?&]$', '', clean)

    _SSL_OFF = {"disable", "false", "0", "no", "allow"}
    if ssl_value in _SSL_OFF:
        return clean, {"ssl": False}

    # Auditoria (SEG-25): honrar verify-ca / verify-full em vez de aceitar
    # QUALQUER certificado. Antes, todo valor "ligado" caía num contexto com
    # check_hostname=False e CERT_NONE — um MITM com certificado autoassinado
    # era aceito mesmo com o operador pedindo verify-full. Agora:
    #   require/prefer/true/1 → cifra sem verificar cadeia (semântica do libpq)
    #   verify-ca             → verifica a cadeia (CA de DATABASE_CA_CERT)
    #   verify-full           → verifica cadeia + hostname
    import os as _os
    _ssl_ctx = ssl.create_default_context()
    ca_cert = _os.getenv("DATABASE_CA_CERT", "").strip()
    if ca_cert and _os.path.isfile(ca_cert):
        try:
            _ssl_ctx.load_verify_locations(cafile=ca_cert)
        except OSError as e:
            logger.warning("DATABASE_CA_CERT não pôde ser carregado (%s): %s", ca_cert, e)

    if ssl_value == "verify-full":
        _ssl_ctx.check_hostname = True
        _ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    elif ssl_value == "verify-ca":
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    else:
        # require / prefer / true / 1: só cifra (não verifica a cadeia).
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = ssl.CERT_NONE

    return clean, {"ssl": _ssl_ctx}


def _prazos(statement_timeout_s: int, command_timeout_s: int) -> dict:
    """
    connect_args do asyncpg com os prazos de cada comando (ver config.py).

    - `statement_timeout` vai como parâmetro de sessão na abertura da conexão:
      vale para todo comando dela, e o Postgres cancela com `QueryCanceledError`
      e deixa a conexão pronta para o próximo.
    - `command_timeout` é o prazo do lado do asyncpg, para quando o Postgres
      nem responde.
    0 (ou negativo) desliga o prazo correspondente.
    """
    args: dict = {}
    if statement_timeout_s > 0:
        args["server_settings"] = {"statement_timeout": str(statement_timeout_s * 1000)}
    if command_timeout_s > 0:
        args["command_timeout"] = command_timeout_s
    if 0 < command_timeout_s <= statement_timeout_s:
        logger.warning(
            "DB_COMMAND_TIMEOUT (%ss) <= DB_STATEMENT_TIMEOUT (%ss): o asyncpg desiste antes "
            "de o Postgres cancelar, e o erro chega sem a causa do banco.",
            command_timeout_s, statement_timeout_s,
        )
    return args


_async_url, _connect_args = _parse_url(DATABASE_URL) if DATABASE_URL else (None, {})
_connect_args = {**_connect_args, **_prazos(DB_STATEMENT_TIMEOUT, DB_COMMAND_TIMEOUT)}

# --- Async Engine & Session ---
#
# A CONEXÃO É DIRETA COM O POSTGRES. Não há pooler no caminho.
#
# Existia na raiz do repositório um `pgbouncer.ini` que não estava ligado a
# nada: nenhum serviço no docker-compose.yml nem no docker-compose.executor.yml,
# nenhuma referência à porta 6432 em lugar nenhum. Pior que inútil, ele mentia —
# prometia `pool_mode = transaction` (que não estava em vigor) e documentava um
# dimensionamento de "4 workers × 30 pool each" que não é o do código. Quem
# investigasse "too many clients already" ia conferir o pooler e concluir que
# estava tudo certo. O arquivo foi removido; esta nota é o que sobrou dele.
#
# O teto real de conexões é `n_workers × (POOL_SIZE + MAX_OVERFLOW)` — hoje
# 4 × (8 + 5) = 52 (ver o comentário do pool em app/core/config.py e o
# `--workers` do api-prod no docker-compose.yml). Isso tem de caber no
# `max_connections` do servidor com folga para migrations e psql.
#
# Se um dia o pgbouncer for de fato introduzido em `pool_mode = transaction`,
# `connect_args` PRECISA levar junto `statement_cache_size=0` e
# `prepared_statement_cache_size=0`: asyncpg com prepared statements sob
# transaction pooling produz "prepared statement already exists" intermitente,
# que só aparece sob concorrência. E o `statement_timeout` de `_prazos` vai como
# parâmetro de início de sessão, que o pgbouncer recusa: ou ele entra em
# `ignore_startup_parameters`, ou o prazo muda para `ALTER ROLE ... SET`.
#
# Permite importação sem DATABASE_URL (testes unitários, CI sem banco).
# O engine será None — qualquer uso real falhará com erro claro.
if _async_url:
    async_engine = create_async_engine(
        _async_url,
        connect_args=_connect_args,
        echo=ECHO_SQL,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        pool_pre_ping=POOL_PRE_PING,
        future=True,
    )
    engine = async_engine

    @event.listens_for(async_engine.sync_engine, "invalidate")
    def _abortar_conexao_presa(dbapi_conn, _registro, exc):
        """Conexão invalidada por prazo estourado ou tarefa cancelada: derruba o
        socket já.

        Nos dois casos o SQLAlchemy descarta a conexão e o asyncpg a fecha com
        cortesia — espera a confirmação do cancelamento da consulta, SEM
        prazo. Com a rede muda (NAT que esqueceu o fluxo, peer congelado) essa
        espera não acaba: o `command_timeout` nunca chegava a quem chamou, e um
        `asyncio.wait_for` em volta da escrita (o fim de sessão do WS de
        executores, 5 s) ficava preso — medido com um proxy que congela. O
        backend órfão morre no `statement_timeout`.
        """
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError, asyncio.CancelledError)):
            try:
                dbapi_conn.driver_connection.terminate()
            except Exception as erro:
                logger.debug("Abortar a conexão invalidada falhou: %s", erro)

    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
else:
    import logging as _log
    _log.getLogger(__name__).warning("DATABASE_URL não definida — engine de banco desabilitado.")
    async_engine = None
    engine = None
    AsyncSessionLocal = None

@asynccontextmanager
async def get_session_async() -> AsyncSession:
    """
    Fornece uma AsyncSession do SQLAlchemy para uso com FastAPI ou código async.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()

# --- Sync Engine & Session: REMOVIDOS ---
#
# Havia aqui um `sync_engine` + `SyncSessionLocal` + `get_session_sync()` que
# NENHUM código usava — zero referências em app/, flow/, executor/, alembic/ e
# tests/. O Alembic não dependia deles: `alembic/env.py` monta a própria URL
# psycopg2 em `_get_sync_url()` e usa `engine_from_config`.
#
# Não era só código morto, era armadilha. O engine síncrono era configurado com
# os MESMOS POOL_SIZE/MAX_OVERFLOW do assíncrono, então o teto real de conexões
# do processo era `2 × (POOL_SIZE + MAX_OVERFLOW)`, não `1 ×`. Pools do
# SQLAlchemy são lazy e o pool morto nunca abria conexão, então na prática nunca
# custou nada — mas o primeiro uso de `SyncSessionLocal` dobraria o teto
# silenciosamente, justo o número que precisa ficar abaixo do `max_connections`
# do servidor (ver o comentário do pool em app/core/config.py).
#
# Se algum dia for preciso código síncrono, criar um engine com pool próprio e
# explícito (provavelmente NullPool), não reaproveitar as constantes do async.
