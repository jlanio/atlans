"""
Engine SQLAlchemy com cache TTL (dispose no evict) + utilitários de schema.

Compartilhado por SaveToPostGIS e SaveToPostgres, que antes reimplementavam o
mesmo _EngineCache/_get_engine/_ensure_schema. Cada nó mantém a SUA instância de
EngineCache (via make_engine_cache) para não competirem por slots do TTLCache
quando rodam concorrentes no mesmo executor.
"""
import sqlalchemy
from cachetools import TTLCache

from flow.utils.logger import get_logger

logger = get_logger(__name__)


class EngineCache(TTLCache):
    """TTLCache que chama engine.dispose() ao evicionar/remover entradas."""

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


# Limite de parâmetros de bind por instrução no protocolo do Postgres. O
# `method="multi"` do pandas monta UM `INSERT ... VALUES (...), (...), ...` com
# um parâmetro por célula, então `linhas × colunas` não pode passar disto.
_MAX_PARAMETROS_POR_INSTRUCAO = 65535


def lote_seguro(n_colunas: int, escolhido: int | None) -> int:
    """Quantas linhas cabem numa instrução, respeitando o teto do protocolo.

    Sem isto, gravar uma tabela de 10 colunas com mais de ~6.500 linhas monta
    uma instrução com mais de 65.535 parâmetros e o driver recusa — num nó cujo
    campo de lote vem com 0 de fábrica e cuja ajuda diz "0 = todas de uma vez".
    Ou seja: o padrão era o valor que quebra, e a interface o apresentava como
    normal.

    Um lote escolhido pelo usuário é respeitado até o teto e cortado acima
    dele: quantas linhas vão por instrução é ajuste de desempenho, e nenhum
    valor de desempenho justifica montar uma instrução que o banco recusa.
    """
    teto = max(1, _MAX_PARAMETROS_POR_INSTRUCAO // max(1, n_colunas))
    if not escolhido or escolhido <= 0:
        return teto
    return min(int(escolhido), teto)


def ensure_schema(conn, schema: str | None) -> None:
    """CREATE SCHEMA IF NOT EXISTS. No-op se `schema` vazio ('public' sempre
    existe). O nome vem do usuário → quotado via identifier_preparer (anti
    SQL-injection). to_postgis/to_sql não criam o schema sozinhos.

    Recebe uma CONEXÃO, não a engine: quem chama abre a transação e grava
    dentro dela (ver truncate_table).
    """
    if not schema:
        return
    quoted = conn.dialect.identifier_preparer.quote(schema)
    conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {quoted}")


def truncate_table(conn, schema: str | None, table: str) -> bool:
    """TRUNCATE na tabela, se ela já existir. Retorna True se esvaziou algo.

    Diferente do `if_exists='replace'` do to_postgis/to_sql (que faz DROP +
    CREATE), preserva a estrutura da tabela: tipos das colunas, SRID da
    geometria, índices, constraints, defaults, triggers e GRANTs. Depois disso
    o node grava com if_exists='append'.

    Se a tabela não existe, é no-op (o append subsequente a cria).
    Nomes vêm do usuário → quotados via identifier_preparer (anti SQL-injection).

    Recebe uma CONEXÃO, e não a engine, porque o esvaziamento e a gravação
    precisam ser a MESMA transação. Enquanto cada um abria a sua, o TRUNCATE
    commitava sozinho e uma falha na gravação seguinte — tipo incompatível,
    queda de rede, qualquer coisa — deixava a tabela VAZIA: o dado velho já
    tinha ido embora e o novo nunca chegou. Numa opção chamada "limpar e
    gravar", perder as duas pontas é o pior desfecho possível.
    """
    if not sqlalchemy.inspect(conn).has_table(table, schema=schema or None):
        return False
    prep = conn.dialect.identifier_preparer
    qualified = f"{prep.quote(schema)}.{prep.quote(table)}" if schema else prep.quote(table)
    conn.exec_driver_sql(f"TRUNCATE TABLE {qualified}")
    return True
