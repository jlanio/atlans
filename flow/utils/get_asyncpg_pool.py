import asyncpg
import asyncio
import os
from cachetools import TTLCache
from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _sanitize_pg_conn_str(conn_str: str) -> str:
    parts = conn_str.split('@', 1)
    return parts[1] if len(parts) > 1 else ''


class _PoolCache(TTLCache):
    """TTLCache que fecha o asyncpg.Pool ao evicionar entradas."""

    def popitem(self):
        key, pool = super().popitem()
        self._close_pool(pool)
        return key, pool

    def __delitem__(self, key):
        pool = self.get(key)
        if pool is not None:
            self._close_pool(pool)
        super().__delitem__(key)

    @staticmethod
    def _close_pool(pool: asyncpg.Pool) -> None:
        try:
            loop = asyncio.get_running_loop()
            # Loop está rodando: agenda o fechamento de forma assíncrona
            asyncio.ensure_future(pool.close(), loop=loop)
        except RuntimeError:
            # Nenhum event loop rodando (ex: shutdown após asyncio.run() encerrar)
            # Não é possível fechar corretamente; o GC do asyncpg cuidará do cleanup.
            pass
        except Exception as e:
            logger.warning(f"[PoolCache] Erro ao fechar pool asyncpg: {e}")


# Chaveado por (loop_id, conn_str) — ver _cache_key. A premissa anterior de
# "um event loop por processo" nao vale desde que sub-workflows passaram a
# executar aninhados.
_pool_cache = _PoolCache(maxsize=50, ttl=600)


async def close_all_pools() -> None:
    """
    Fecha explicitamente todos os pools em cache.
    Deve ser chamado durante o shutdown gracioso do executor, antes do event loop fechar.
    """
    keys = list(_pool_cache.keys())
    for key in keys:
        pool = _pool_cache.pop(key, None)
        if pool is not None:
            try:
                await pool.close()
                logger.info("[close_all_pools] Pool fechado para: %s", _sanitize_pg_conn_str(key[1] if isinstance(key, tuple) else key))
            except Exception as e:
                logger.warning("[close_all_pools] Erro ao fechar pool: %s", e)


def _cache_key(conn_str: str) -> tuple:
    """Chave do cache: (event loop, connection string).

    Um asyncpg.Pool fica atrelado ao event loop que o criou — reusa-lo em outro
    loop falha com "got Future attached to a different loop". A chave anterior
    era so a conn_str, apoiada na premissa de "um loop por processo", que
    qualquer caminho criando loop novo (ex: asyncio.run em thread) quebra de
    forma intermitente e dificil de diagnosticar.

    Fora de loop (chamada sincrona) cai para None — sem loop nao ha pool a
    reutilizar de qualquer forma.
    """
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = None
    return (loop_id, conn_str)


async def get_asyncpg_pool(conn_str: str) -> asyncpg.Pool:
    """
    Retorna ou cria um asyncpg.Pool para a connectionString informada.
    O pool é reutilizado enquanto estiver no cache (TTL=600s, max=50 entradas)
    E enquanto o event loop for o mesmo que o criou (ver _cache_key).
    Ao ser eviccionado, o pool é fechado corretamente para liberar conexões.
    """
    key = _cache_key(conn_str)
    if key not in _pool_cache:
        logger.info(f"[get_asyncpg_pool] Criando pool para: {_sanitize_pg_conn_str(conn_str)}")
        try:
            # application_name aparece em pg_stat_activity — facilita identificar
            # conexões do Atlas Studio no banco (ex: SELECT * FROM pg_stat_activity)
            executor_id = os.getenv("EXECUTOR_ID", "")
            app_name = f"apolo/{executor_id[-5:]}" if executor_id else "apolo"
            pool = await asyncpg.create_pool(
                dsn=conn_str,
                min_size=0,
                max_size=5,
                timeout=30.0,
                max_inactive_connection_lifetime=60,
                server_settings={"application_name": app_name},
            )
            _pool_cache[key] = pool
        except asyncpg.TooManyConnectionsError:
            logger.error("[get_asyncpg_pool] Banco atingiu limite de conexões.")
            raise RuntimeError("Banco recusou conexão: too many clients.")
    return _pool_cache[key]
