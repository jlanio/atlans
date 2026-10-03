import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.sql_engine import make_engine_cache, get_engine, ensure_schema, truncate_table, lote_seguro
from flow.utils.credencial import obter_conexao

logger = get_logger(__name__)

# Cache separate from SaveToPostGIS so as not to compete for TTLCache slots
# when both nodes run concurrently on the same executor.
_engine_cache = make_engine_cache("SaveToPostgres")


def _get_engine(conn_str: str):
    return get_engine(_engine_cache, conn_str, label="SaveToPostgres")


@register_node
class SaveToPostgres(BaseNode):
    """
    Node that writes a DataFrame to a regular PostgreSQL table (no PostGIS).

    Accepts `pandas.DataFrame` OR `geopandas.GeoDataFrame`. If it receives a
    GDF, the geometry column is removed automatically before the insert
    (plain Postgres does not handle geometry — to write with geom, use
    SaveToPostGIS).

    Properties:
      - credential_id: UUID of the PostgreSQL credential
      - connectionString: DSN (injected by the backend via the credential)
      - tableName: name of the destination table (required)
      - schema: Postgres schema (default 'public' when empty)
      - ifExists: 'fail' | 'replace' | 'truncate' | 'append' (default 'append')
      - index: write the DataFrame index as a column (default False)
      - chunksize: rows per batch in the INSERT (0 -> automatic from the number of columns)
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SaveToPostgres',
            'alias': 'Salvar em Postgres',
            'description': 'Salva um DataFrame em uma tabela PostgreSQL (sem PostGIS)',
            'type': 'output',
            'requires_credential': True,
            'properties': [
                {'name': 'credential_id', 'type': 'string', 'default': '', 'description': 'UUID da credencial PostgreSQL'},
                # Injected by the backend via inject_credentials — it must be
                # declared here, otherwise validate_node_parameters drops the key
                # after self.validate() in execute() and the node blows up with
                # "Parametro 'connectionString' e obrigatorio.". The frontend does
                # not render the field (whitelist in node-config-form.tsx).
                {'name': 'connectionString', 'type': 'string', 'default': '', 'description': 'DSN de conexao (injetada automaticamente pela credencial)'},
                {'name': 'tableName', 'required': True, 'type': 'string', 'label': 'Tabela de destino', 'default': '', 'description': 'Nome da tabela onde os dados serao gravados'},
                {'name': 'schema', 'type': 'string', 'label': 'Schema', 'default': 'public', 'description': "Schema do Postgres (vazio = 'public')"},
                {
                    'name': 'ifExists',
                    'type': 'select',
                    'label': 'Se a tabela já existir',
                    'default': 'append',
                    'description': "O que fazer quando a tabela de destino ja existe",
                    'options': [
                        {'value': 'append',   'label': 'Anexar — adiciona as linhas ao final da tabela'},
                        {'value': 'truncate', 'label': 'Limpar e gravar — esvazia a tabela (TRUNCATE) mantendo a estrutura'},
                        {'value': 'replace',  'label': 'Substituir — apaga a tabela (DROP) e recria do zero'},
                        {'value': 'fail',     'label': 'Falhar — cancela a operação se a tabela existir'},
                    ],
                },
                {'name': 'index', 'type': 'boolean', 'label': 'Gravar índice como coluna', 'default': False, 'description': 'Inclui o indice do DataFrame como uma coluna na tabela'},
                {'name': 'chunksize', 'type': 'number', 'label': 'Tamanho do lote (linhas por INSERT)', 'default': 0, 'description': 'Quantas linhas enviar por instrucao (0 = automatico, calculado a partir do numero de colunas)'},
            ],
            'outputs': [
                {'name': 'output', 'type': 'object', 'description': 'Objeto com a quantidade de linhas inseridas (rowsInserted)'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        conn_str = obter_conexao(self.parameters)

        df = self._get_first_df(inputs)

        table_name = self.parameters.get('tableName', '').strip()
        if not table_name:
            raise ValueError("Parametro 'tableName' e obrigatorio.")

        # Default 'public' when the user does not provide a schema (instead of leaving
        # None and depending on the user's search_path, which may vary).
        schema_raw = (self.parameters.get('schema') or '').strip()
        schema = schema_raw or 'public'
        if_exists = self.parameters.get('ifExists', 'append')
        index = self.parameters.get('index', False)
        chunksize_raw = self.parameters.get('chunksize', 0) or 0
        try:
            chunksize = int(chunksize_raw) or None
        except (TypeError, ValueError):
            chunksize = None

        # Drops the geometry column if the input is a GeoDataFrame — plain
        # Postgres without the PostGIS extension does not accept geometry. A user
        # who wants to persist geom should use SaveToPostGIS.
        df = self._drop_geometry_column(df)

        logger.info(
            "Salvando %d linhas em '%s%s' (ifExists=%s, index=%s, chunksize=%s)",
            len(df), f"{schema}." if schema else "", table_name, if_exists, index, chunksize,
        )

        engine = _get_engine(conn_str)
        try:
            await asyncio.to_thread(
                self._save_to_postgres,
                df, table_name, schema, if_exists, index, chunksize, engine,
            )
        except Exception as e:
            logger.error(f"Erro ao salvar em Postgres: {e}")
            raise RuntimeError(f"Erro ao salvar em Postgres: {e}") from e

        return {'output': {'rowsInserted': len(df)}}

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_first_df(self, inputs: Dict[str, Any]):
        """Returns the first non-empty DataFrame (pandas or geopandas)."""
        import pandas as pd
        for value in inputs.values():
            if isinstance(value, pd.DataFrame) and not value.empty:
                return value
        raise ValueError("Nenhum DataFrame encontrado nos inputs.")

    def _drop_geometry_column(self, df):
        """If it is a GeoDataFrame, removes the active geometry column."""
        import geopandas as gpd
        if isinstance(df, gpd.GeoDataFrame):
            geom_name = df.geometry.name if df.geometry is not None else None
            if geom_name and geom_name in df.columns:
                logger.info(
                    "Input e GeoDataFrame — removendo coluna de geometria '%s' "
                    "(SaveToPostgres nao persiste geometria; use SaveToPostGIS "
                    "para isso).",
                    geom_name,
                )
                return df.drop(columns=[geom_name])
        return df

    def _save_to_postgres(self, df, table_name, schema, if_exists, index, chunksize, engine):
        # `method='multi'` builds ONE INSERT with one parameter per cell, and the
        # Postgres protocol does not accept more than 65535 per statement. With the
        # batch size at 0 (the factory default, whose help says "todas de uma vez"),
        # any 10-column table with more than ~6,500 rows was rejected by the
        # driver. The batch size is now derived from the number of columns.
        colunas = len(df.columns) + (1 if index else 0)
        lote = lote_seguro(colunas, chunksize)
        if chunksize and lote < chunksize:
            logger.warning(
                "Lote de %s linhas excede o limite do protocolo para %d colunas; "
                "usando %d linhas por instrucao.", chunksize, colunas, lote,
            )

        # ONE transaction to empty and write. While there were two, the TRUNCATE
        # committed on its own and a failure while writing left the table EMPTY:
        # the old data was already gone and the new data never arrived.
        with engine.begin() as conn:
            ensure_schema(conn, schema)
            efetivo = if_exists
            # 'truncate' does not exist in to_sql: we empty the table here and
            # write as 'append' (which also creates the table if it does not exist).
            if efetivo == 'truncate':
                if truncate_table(conn, schema, table_name):
                    logger.info("Tabela '%s.%s' esvaziada (TRUNCATE) antes da gravacao", schema, table_name)
                efetivo = 'append'
            df.to_sql(
                name=table_name,
                con=conn,
                schema=schema,
                if_exists=efetivo,
                index=index,
                chunksize=lote,
                method='multi',  # 1 INSERT with multi-values — faster in batches
            )
