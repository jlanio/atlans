import asyncio

import pandas as pd
import geopandas as gpd
from shapely import from_wkb
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.get_asyncpg_pool import get_asyncpg_pool
from flow.utils.query_param_formatter import prepare_query, resolver_query_params
from flow.utils.sql_guard import validate_readonly_sql
from flow.utils.credencial import obter_conexao

logger = get_logger(__name__)


def _batch_to_df(batch) -> pd.DataFrame:
    """Converts a chunk of Records into a DataFrame. Runs in a thread (see execute)."""
    return pd.DataFrame([dict(r) for r in batch])


def _montar_gdf(chunks: list, geom_col: str, crs: str) -> gpd.GeoDataFrame:
    """Concatenates the chunks and converts the WKB to geometry. Runs in a thread.

    It's the heaviest part of the node: `pd.concat` copies the entire result and
    `from_wkb` walks all the geometries. On the event loop this left the
    executor silent for tens of seconds at the end of a large query.
    """
    df = pd.concat(chunks, ignore_index=True)
    if geom_col not in df.columns:
        raise ValueError(f"Coluna '{geom_col}' não encontrada nos resultados.")

    # F3: from_wkb expects bytes/hex. If the user wrote ST_AsText(...) in the
    # query, WKT (text) arrives and shapely blows up with an obscure error. Sampling
    # the first non-null value detects the case and gives an actionable message.
    sample = df[geom_col].dropna()
    if not sample.empty:
        first = sample.iloc[0]
        if isinstance(first, str) and first.lstrip().upper().startswith(
            ("POINT", "LINESTRING", "POLYGON", "MULTIPOINT", "MULTILINESTRING",
             "MULTIPOLYGON", "GEOMETRYCOLLECTION")
        ):
            raise ValueError(
                f"Coluna '{geom_col}' contem WKT (texto). Use ST_AsBinary({geom_col}) "
                "no SELECT ou selecione a coluna geometry diretamente para obter WKB."
            )

    # PERF: vectorized from_wkb accepts arrays, ~10x faster than .apply(wkb.loads)
    df["geometry"] = from_wkb(df[geom_col])
    return gpd.GeoDataFrame(df.drop(columns=[geom_col]), geometry="geometry", crs=crs)


@register_node
class DatabaseSpatialQuery(BaseNode):
    """
    Executes a spatial query that returns WKB geometry and converts it into a GeoDataFrame.
    Requires the 'connectionString' field to already be resolved in the parameters.
    """

    @classmethod
    def description(cls) -> dict:
        return {
            'name': 'DatabaseSpatialQuery',
            'alias': 'Banco de Dados Espacial',
            'description': (
                'Executa SQL espacial e retorna um GeoDataFrame. '
                'A coluna indicada em geometryColumn deve conter WKB (use ST_AsBinary(geom) '
                'ou selecione a coluna geometry diretamente). '
                'Se a query retorna multiplas colunas geometricas, apenas geometryColumn e '
                'convertida — as demais viram bytes brutos no DataFrame.'
            ),
            'type': 'datasource',
            'requires_credential': True,
            'properties': [
                {'name': 'alias',           'type': 'string', 'default': ''},
                {'name': 'credential_id',   'type': 'string', 'default': '', 'description': 'UUID da credencial de banco de dados'},
                # Injected by the server from `credential_id`. It needs to be
                # declared: `validate_node_parameters` rebuilds the parameters
                # from this list and discards whatever is not in it. The node
                # worked without the declaration only because it didn't call
                # `validate()`. The UI draws no field for it.
                {'name': 'connectionString', 'type': 'string', 'default': '', 'description': 'DSN de conexao (injetada automaticamente pela credencial)'},
                {'name': 'query', 'required': True,           'label': 'Consulta SQL', 'type': 'sql', 'default': '', 'description': 'Query SQL (apenas SELECT)'},
                {'name': 'queryParams',     'label': 'Parâmetros da consulta', 'type': 'object', 'default': {}, 'description': 'Valores para os placeholders nomeados :param'},
                {'name': 'geometryColumn',  'label': 'Coluna de geometria', 'type': 'string', 'default': 'geom'},
                {'name': 'crs',             'label': 'CRS de entrada', 'type': 'string', 'default': 'EPSG:4326'},
                # `execute` always read this parameter, but it was never
                # declared: without an entry here the UI draws no field at all, and
                # the only way to change the time limit was to edit the workflow's
                # JSON by hand. A large spatial query is exactly the case
                # where 120s isn't enough.
                {'name': 'timeout', 'label': 'Tempo limite (s)', 'type': 'integer', 'default': 120,
                 'description': 'Tempo maximo de espera por uma conexao do pool, em segundos.'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da consulta espacial'},
            ],
            'dynamic_output': True,
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        conn_str = obter_conexao(self.parameters)
        raw_query = self.parameters.get("query")
        query_params = resolver_query_params(inputs, self.parameters)
        crs = self.parameters.get("crs", "EPSG:4326")
        # F1: the user may have saved the field blank — get(chave, "geom") only
        # applies the default if the KEY is missing, not if it's "". Trim
        # removes accidental spaces in the UI.
        geom_col = (self.parameters.get("geometryColumn") or "geom").strip()

        if not raw_query:
            raise ValueError("Parâmetro 'query' é obrigatório.")

        validate_readonly_sql(raw_query)

        # Replaces :placeholders with $1, $2, ... with safe values
        # Without the `if`: with empty params and a query WITHOUT placeholders,
        # `prepare_query` returns the query intact, and with a placeholder it raises
        # "Parâmetro SQL 'x' não fornecido" — which is the right error. The old shortcut
        # skipped that warning and sent the literal `:bairro` to Postgres.
        prepared_query, values = prepare_query(raw_query, query_params)

        # PERF: configurable timeout (default 120s) for large queries
        _timeout = int(self.parameters.get("timeout", 120))
        _CHUNK_SIZE = 10_000

        pool = await get_asyncpg_pool(conn_str)
        async with pool.acquire(timeout=_timeout) as conn:
            try:
                # PERF: streaming cursor in chunks — avoids materializing millions of records at once
                # SEC: readonly=True enforces SET TRANSACTION READ ONLY in Postgres.
                # The real defense is in the engine — validate_readonly_sql runs first only
                # to give the user an actionable error and block what the transaction
                # doesn't catch (dblink opens another connection, where the local READ ONLY
                # doesn't apply).
                chunks = []
                async with conn.transaction(readonly=True):
                    cursor = await conn.cursor(prepared_query, *values)
                    while True:
                        batch = await cursor.fetch(_CHUNK_SIZE)
                        if not batch:
                            break
                        # Each chunk becomes a DataFrame in a thread: with 10k records
                        # per batch, building it on the loop blocked the WebSocket between
                        # one fetch and the next.
                        chunks.append(await asyncio.to_thread(_batch_to_df, batch))
            except Exception as e:
                raise RuntimeError(f"Erro ao executar consulta SQL: {e}") from e

        if not chunks:
            return {"output": gpd.GeoDataFrame([], geometry=None, crs=crs)}

        gdf = await asyncio.to_thread(_montar_gdf, chunks, geom_col, crs)

        logger.info("Query concluída: %d registros em %d chunks.", len(gdf), len(chunks))

        return {"output": gdf}

    @classmethod
    async def simulate(cls, parameters: dict, simulated_inputs: dict = None) -> list:
        from app.core.authorization.credential_loader import resolve_credentials_from_ids

        credential_id = parameters.get('credential_id')
        query = parameters.get('query')
        # F1: same normalization as execute — an empty field in the UI falls back to the default.
        geom_col = (parameters.get('geometryColumn') or 'geom').strip()

        if not credential_id or not query:
            raise ValueError("Simulação requer 'credential_id' e 'query'.")

        credentials = await resolve_credentials_from_ids([credential_id])
        conn_str = credentials.get(credential_id, {}).get("connectionString")
        if not conn_str:
            raise ValueError(f"Credencial '{credential_id}' não encontrada ou sem 'connectionString'.")

        validate_readonly_sql(query)

        pool = await get_asyncpg_pool(conn_str)
        async with pool.acquire(timeout=15) as conn:
            stmt = await conn.prepare(f"SELECT * FROM ({query}) AS subq LIMIT 0")
            fields = []
            for col in stmt.get_attributes():
                name = col.name
                pgtype = col.type.name if hasattr(col.type, 'name') else 'unknown'
                if name == geom_col:
                    pgtype = 'geometry'
                fields.append({'name': name, 'type': pgtype})

            return [{
                'name': 'result',
                'type': 'object',
                'fields': fields
            }]
