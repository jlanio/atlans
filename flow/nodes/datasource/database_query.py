import asyncio

import asyncpg
import pandas as pd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.get_asyncpg_pool import get_asyncpg_pool
from flow.utils.logger import get_logger
from flow.utils.query_param_formatter import prepare_query, resolver_query_params
from flow.utils.sql_guard import validate_readonly_sql
from flow.utils.credencial import get_connection

logger = get_logger(__name__)


# PERF: cursor streaming em chunks — mesmo tamanho do DatabaseSpatialQuery.
_CHUNK_SIZE = 10_000


def _records_to_df(records) -> pd.DataFrame:
    """Converts a batch of asyncpg Records into a DataFrame. Runs in a thread."""
    return pd.DataFrame([dict(rec) for rec in records])


def _concat_chunks(chunks: list) -> pd.DataFrame:
    """Joins each chunk's DataFrames into one. Runs in a thread (see execute)."""
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


@register_node
class DatabaseQuery(BaseNode):
    """
    Executes a parameterized SQL query on a database and returns the result as a DataFrame.
    Supports named parameters in the :param format via queryParams, falling back to static parameters.
    """

    @classmethod
    def description(cls) -> dict:
        return {
            'name': 'DatabaseQuery',
            'alias': 'Banco de Dados',
            'description': 'Executa uma consulta SQL em um banco de dados e retorna o resultado como DataFrame.',
            'type': 'datasource',
            'requires_credential': True,
            'properties': [
                {
                    'name': 'credential_id',
                    'type': 'string',
                    'default': '',
                    'description': 'UUID da credencial de banco de dados'
                },
                {
                    # Injected by the server from `credential_id`. It needs
                    # to be declared: `validate_node_parameters` rebuilds the
                    # parameters from this list and discards whatever is not
                    # in it. The node worked without the declaration only because it
                    # didn't call `validate()` — it was enough for someone to follow the
                    # instruction in `BaseNode.validate`'s docstring for every database
                    # query on the platform to stop finding the connection. It's the same
                    # treatment SaveToPostgres and SaveToPostGIS already had. The UI
                    # draws no field for it (list of names in node-config-form).
                    'name': 'connectionString',
                    'type': 'string',
                    'default': '',
                    'description': 'DSN de conexao (injetada automaticamente pela credencial)'
                },
                {
                    'name': 'query', 'required': True,
                    'label': 'Consulta SQL',
                    'type': 'sql',
                    'default': '',
                    'description': 'Query SQL com placeholders nomeados :param'
                },
                {
                    'name': 'queryParams',
                    'label': 'Parâmetros da consulta',
                    'type': 'object',
                    'default': {},
                    'description': 'Valores para os placeholders nomeados'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'object', 'description': 'DataFrame com os resultados da consulta SQL'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        conn_str     = get_connection(self.parameters)
        raw_query    = self.parameters.get('query', '')
        query_params = resolver_query_params(inputs, self.parameters)

        if not raw_query:
            raise ValueError("Parâmetro 'query' é obrigatório.")

        validate_readonly_sql(raw_query)

        # Before the pool, as in DatabaseSpatialQuery: building the query is pure
        # work, and doing it after opening a connection spent a round trip to the
        # database to find out a parameter was missing — or held a pool connection
        # during the substitution.
        #
        # Without the `if query_params:` that used to be here: with empty params and a
        # query WITHOUT placeholders, `prepare_query` returns the query intact, and with
        # a placeholder it raises "Parâmetro SQL 'x' não fornecido" — which is the
        # right error. The old shortcut skipped exactly that warning and sent the
        # literal `:bairro` to Postgres, which answered with a syntax error
        # pointing at a character.
        prepared_query, values = prepare_query(raw_query, query_params)

        pool = await get_asyncpg_pool(conn_str)

        chunks: list = []
        async with pool.acquire(timeout=15) as connection:
            try:
                # SEC: readonly=True enforces SET TRANSACTION READ ONLY in Postgres.
                # The real defense is in the engine — validate_readonly_sql runs first only
                # to give the user an actionable error and block what the transaction
                # doesn't catch (dblink opens another connection, where the local READ ONLY
                # doesn't apply).
                #
                # PERF: cursor in chunks (like DatabaseSpatialQuery) instead of
                # `fetch()` of everything. `dict(rec)` + building the DataFrame from
                # hundreds of thousands of rows AT ONCE held the event loop
                # for tens of seconds (past 90s the server closes the
                # session with 4408). Each chunk becomes a DataFrame in a thread; the
                # conversion doesn't block the loop between one fetch and the next.
                async with connection.transaction(readonly=True):
                    cursor = await connection.cursor(prepared_query, *values)
                    while True:
                        batch = await cursor.fetch(_CHUNK_SIZE)
                        if not batch:
                            break
                        chunks.append(await asyncio.to_thread(_records_to_df, batch))
            except asyncpg.exceptions.UndefinedColumnError as e:
                raise ValueError(f"Coluna inválida na consulta: {e.column}") from e
            except asyncpg.exceptions.InvalidTextRepresentationError as e:
                raise ValueError(f"Tipo de dado inválido no filtro: {e}") from e
            except ValueError:
                raise
            except Exception as e:
                logger.error(f"Erro ao executar consulta: {e}")
                raise RuntimeError(f"Erro ao executar consulta: {e}") from e

        # Concatenates outside the `acquire`: the pool connection isn't held during
        # the final assembly of the DataFrame.
        df = await asyncio.to_thread(_concat_chunks, chunks)

        return {"output": df}
