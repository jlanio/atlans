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
    Extracts ssl/sslmode from DATABASE_URL and returns (url_limpa, connect_args) for asyncpg.

    - No SSL parameter → disables SSL explicitly (asyncpg tries SSL by default,
      which can cause a timeout on servers that accept but never complete the handshake).
    - ssl=disable / ssl=false → ssl=False
    - ssl=require / sslmode=require → SSLContext with or without a CA cert.
    """
    match = re.search(r'[?&](ssl|sslmode)=([^&]+)', url)

    if not match:
        # asyncpg tries SSL by default — disable it explicitly when not requested
        return url, {"ssl": False}

    full_param = match.group(0)
    ssl_value  = match.group(2).lower()

    # Removes the parameter from the URL and normalizes separators
    clean = url.replace(full_param, "")
    clean = re.sub(r'\?&', '?', clean)
    clean = re.sub(r'[?&]$', '', clean)

    _SSL_OFF = {"disable", "false", "0", "no", "allow"}
    if ssl_value in _SSL_OFF:
        return clean, {"ssl": False}

    # Audit (SEG-25): honor verify-ca / verify-full instead of accepting
    # ANY certificate. Before, every "on" value fell into a context with
    # check_hostname=False and CERT_NONE — a MITM with a self-signed certificate
    # was accepted even when the operator asked for verify-full. Now:
    #   require/prefer/true/1 → encrypts without verifying the chain (libpq semantics)
    #   verify-ca             → verifies the chain (CA from DATABASE_CA_CERT)
    #   verify-full           → verifies chain + hostname
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
        # require / prefer / true / 1: encrypt only (does not verify the chain).
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = ssl.CERT_NONE

    return clean, {"ssl": _ssl_ctx}


def _timeouts(statement_timeout_s: int, command_timeout_s: int) -> dict:
    """
    asyncpg connect_args with the per-command deadlines (see config.py).

    - `statement_timeout` goes as a session parameter when the connection is opened:
      it applies to every command on it, and Postgres cancels with `QueryCanceledError`
      and leaves the connection ready for the next one.
    - `command_timeout` is the deadline on the asyncpg side, for when Postgres
      doesn't even respond.
    0 (or negative) disables the corresponding deadline.
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
_connect_args = {**_connect_args, **_timeouts(DB_STATEMENT_TIMEOUT, DB_COMMAND_TIMEOUT)}

# --- Async Engine & Session ---
#
# THE CONNECTION GOES DIRECTLY TO POSTGRES. There is no pooler in the path.
#
# There used to be a `pgbouncer.ini` at the repository root that was wired to
# nothing: no service in docker-compose.yml nor in docker-compose.executor.yml,
# no reference to port 6432 anywhere. Worse than useless, it lied —
# it promised `pool_mode = transaction` (which was not in effect) and documented a
# sizing of "4 workers × 30 pool each" that is not the code's. Anyone
# investigating "too many clients already" would check the pooler and conclude that
# everything was fine. The file was removed; this note is what is left of it.
#
# The real connection ceiling is `n_workers × (POOL_SIZE + MAX_OVERFLOW)` — today
# 4 × (8 + 5) = 52 (see the pool comment in app/core/config.py and the
# api-prod `--workers` in docker-compose.yml). That has to fit within the
# server's `max_connections` with headroom for migrations and psql.
#
# If pgbouncer is ever actually introduced in `pool_mode = transaction`,
# `connect_args` MUST also carry `statement_cache_size=0` and
# `prepared_statement_cache_size=0`: asyncpg with prepared statements under
# transaction pooling produces intermittent "prepared statement already exists",
# which only shows up under concurrency. And the `statement_timeout` from `_timeouts` goes as a
# session startup parameter, which pgbouncer refuses: either it goes into
# `ignore_startup_parameters`, or the deadline moves to `ALTER ROLE ... SET`.
#
# Allows importing without DATABASE_URL (unit tests, CI without a database).
# The engine will be None — any real use will fail with a clear error.
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
        """Connection invalidated by an exceeded deadline or a cancelled task: drops the
        socket right away.

        In both cases SQLAlchemy discards the connection and asyncpg closes it
        politely — it waits for confirmation of the query cancellation, WITHOUT a
        deadline. With a silent network (a NAT that forgot the flow, a frozen peer) that
        wait never ends: the `command_timeout` never reached the caller, and an
        `asyncio.wait_for` around the write (the executors WS session teardown,
        5 s) got stuck — measured with a freezing proxy. The
        orphaned backend dies at `statement_timeout`.
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
    Provides a SQLAlchemy AsyncSession for use with FastAPI or async code.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()

# --- Sync Engine & Session: REMOVED ---
#
# There used to be a `sync_engine` + `SyncSessionLocal` + `get_session_sync()` here that
# NO code used — zero references in app/, flow/, executor/, alembic/ and
# tests/. Alembic did not depend on them: `alembic/env.py` builds its own psycopg2
# URL in `_get_sync_url()` and uses `engine_from_config`.
#
# It was not just dead code, it was a trap. The sync engine was configured with
# the SAME POOL_SIZE/MAX_OVERFLOW as the async one, so the process's real connection
# ceiling was `2 × (POOL_SIZE + MAX_OVERFLOW)`, not `1 ×`. SQLAlchemy
# pools are lazy and the dead pool never opened a connection, so in practice it never
# cost anything — but the first use of `SyncSessionLocal` would silently double the
# ceiling, precisely the number that must stay below the server's
# `max_connections` (see the pool comment in app/core/config.py).
#
# If sync code is ever needed, create an engine with its own explicit
# pool (probably NullPool), do not reuse the async constants.
