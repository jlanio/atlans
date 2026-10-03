"""
SQLAlchemy engine with a TTL cache (dispose on evict) + schema utilities.

Shared by SaveToPostGIS and SaveToPostgres, which used to reimplement the
same _EngineCache/_get_engine/_ensure_schema. Each node keeps ITS OWN EngineCache
instance (via make_engine_cache) so they don't compete for TTLCache slots
when running concurrently on the same executor.
"""
import sqlalchemy
from cachetools import TTLCache

from flow.utils.logger import get_logger

logger = get_logger(__name__)


class EngineCache(TTLCache):
    """TTLCache that calls engine.dispose() when evicting/removing entries."""

    def __init__(self, maxsize: int = 20, ttl: int = 600, *, label: str = "SQL"):
        super().__init__(maxsize=maxsize, ttl=ttl)
        self._label = label

    def _dispose(self, engine) -> None:
        try:
            engine.dispose()
        except Exception as e:
            logger.warning("[%s] Erro ao descartar engine: %s", self._label, e)

    def popitem(self):
        key, engine = super().popitem()
        self._dispose(engine)
        return key, engine

    def __delitem__(self, key):
        engine = self.get(key)
        if engine is not None:
            self._dispose(engine)
        super().__delitem__(key)


def make_engine_cache(label: str, *, maxsize: int = 20, ttl: int = 600) -> EngineCache:
    return EngineCache(maxsize=maxsize, ttl=ttl, label=label)


def get_engine(cache: EngineCache, conn_str: str, *, label: str = "SQL") -> sqlalchemy.engine.Engine:
    """Retorna (criando e cacheando) um Engine para a connection string."""
    if conn_str not in cache:
        logger.info("[%s] Criando engine SQLAlchemy para nova connection string", label)
        cache[conn_str] = sqlalchemy.create_engine(
            conn_str,
            pool_size=2,
            max_overflow=2,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return cache[conn_str]


# Limit of bind parameters per statement in the Postgres protocol. pandas'
# `method="multi"` builds ONE `INSERT ... VALUES (...), (...), ...` with
# one parameter per cell, so `linhas × colunas` (rows × columns) cannot exceed this.
_MAX_PARAMS_PER_STATEMENT = 65535


def safe_batch_size(n_columns: int, escolhido: int | None) -> int:
    """How many rows fit in one statement, respecting the protocol's ceiling.

    Without this, writing a 10-column table with more than ~6,500 rows builds
    a statement with more than 65,535 parameters and the driver rejects it — in a
    node whose batch field ships as 0 and whose help says "0 = todas de uma vez"
    (0 = all at once). In other words: the default was the value that breaks, and
    the interface presented it as normal.

    A batch chosen by the user is respected up to the ceiling and cut above
    it: how many rows go per statement is performance tuning, and no
    performance value justifies building a statement the database rejects.
    """
    teto = max(1, _MAX_PARAMS_PER_STATEMENT // max(1, n_columns))
    if not escolhido or escolhido <= 0:
        return teto
    return min(int(escolhido), teto)


def ensure_schema(conn, schema: str | None) -> None:
    """CREATE SCHEMA IF NOT EXISTS. No-op if `schema` is empty ('public' always
    exists). The name comes from the user → quoted via identifier_preparer (anti
    SQL-injection). to_postgis/to_sql do not create the schema on their own.

    Receives a CONNECTION, not the engine: the caller opens the transaction and
    writes inside it (see truncate_table).
    """
    if not schema:
        return
    quoted = conn.dialect.identifier_preparer.quote(schema)
    conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {quoted}")


def truncate_table(conn, schema: str | None, table: str) -> bool:
    """TRUNCATE on the table, if it already exists. Returns True if it emptied something.

    Unlike to_postgis/to_sql's `if_exists='replace'` (which does DROP +
    CREATE), it preserves the table's structure: column types, geometry SRID,
    indexes, constraints, defaults, triggers and GRANTs. After that
    the node writes with if_exists='append'.

    If the table doesn't exist, it is a no-op (the subsequent append creates it).
    Names come from the user → quoted via identifier_preparer (anti SQL-injection).

    Receives a CONNECTION, not the engine, because emptying and writing
    must be the SAME transaction. While each opened its own, the TRUNCATE
    committed on its own and a failure in the following write — incompatible type,
    network drop, anything — left the table EMPTY: the old data was already
    gone and the new never arrived. In an option called "Limpar e
    gravar" (clear and write), losing both ends is the worst possible outcome.
    """
    if not sqlalchemy.inspect(conn).has_table(table, schema=schema or None):
        return False
    prep = conn.dialect.identifier_preparer
    qualified = f"{prep.quote(schema)}.{prep.quote(table)}" if schema else prep.quote(table)
    conn.exec_driver_sql(f"TRUNCATE TABLE {qualified}")
    return True
