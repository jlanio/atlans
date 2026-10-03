import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.sql_engine import make_engine_cache, get_engine, ensure_schema, truncate_table
from flow.utils.credencial import get_connection

logger = get_logger(__name__)

# Features per COPY when the user leaves the batch size on automatic. COPY has
# no parameter limit like INSERT, so what this number controls is
# MEMORY: geopandas serializes each batch into an in-RAM CSV before sending.
_DEFAULT_BATCH = 50_000

# Own cache (separate from SaveToPostgres) so as not to compete for slots.
_engine_cache = make_engine_cache("SaveToPostGIS")


def _get_engine(conn_str: str):
    return get_engine(_engine_cache, conn_str, label="SaveToPostGIS")


@register_node
class SaveToPostGIS(BaseNode):
    """
    Node that writes a GeoDataFrame to a PostGIS table.

    Properties:
      - connectionString: connection DSN for the database (string; required)
      - tableName: name of the destination table (string; required)
      - schema: Postgres schema (string; default 'public' when empty)
      - geometryColumn: name of the geometry column in the PostGIS table (string; default 'geom')
      - ifExists: behavior if the table already exists ('fail'|'replace'|'truncate'|'append'; default 'append')
      - index: save the index to PostGIS (boolean; default False)
      - chunksize: features per COPY (0 -> automatic; controls peak memory)
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SaveToPostGIS',
            'alias': 'Salvar em PostGIS',
            'description': 'Salva um GeoDataFrame em uma tabela PostGIS',
            'type': 'output',
            'requires_credential': True,
            'properties': [
                {'name': 'credential_id', 'type': 'string', 'default': '', 'description': 'UUID da credencial PostgreSQL/PostGIS'},
                # Injected by the backend via inject_credentials — it must be
                # declared here, otherwise validate_node_parameters drops the key
                # after self.validate() in execute() and the node blows up with
                # "Parametro 'connectionString' e obrigatorio.". The frontend does
                # not render the field (whitelist in node-config-form.tsx).
                {'name': 'connectionString', 'type': 'string', 'default': '', 'description': 'DSN de conexao (injetada automaticamente pela credencial)'},
                {'name': 'tableName', 'required': True, 'type': 'string', 'label': 'Tabela de destino', 'default': '', 'description': 'Nome da tabela onde as feicoes serao gravadas'},
                {'name': 'schema', 'type': 'string', 'label': 'Schema', 'default': 'public', 'description': "Schema do Postgres (vazio = 'public')"},
                {'name': 'geometryColumn', 'type': 'string', 'label': 'Coluna de geometria', 'default': 'geom', 'description': "Nome da coluna de geometria na tabela (padrao 'geom', convencao PostGIS)"},
                {
                    'name': 'ifExists',
                    'type': 'select',
                    'label': 'Se a tabela já existir',
                    'default': 'append',
                    'description': "O que fazer quando a tabela de destino ja existe",
                    'options': [
                        {'value': 'append',   'label': 'Anexar — adiciona as feições ao final da tabela'},
                        {'value': 'truncate', 'label': 'Limpar e gravar — esvazia a tabela (TRUNCATE) mantendo a estrutura'},
                        {'value': 'replace',  'label': 'Substituir — apaga a tabela (DROP) e recria do zero'},
                        {'value': 'fail',     'label': 'Falhar — cancela a operação se a tabela existir'},
                    ],
                },
                {'name': 'index', 'type': 'boolean', 'label': 'Gravar índice como coluna', 'default': False, 'description': 'Inclui o indice do GeoDataFrame como uma coluna na tabela'},
                # Without a batch size, geopandas builds the COPY CSV with the
                # WHOLE layer in a memory buffer before sending the first
                # row. On a large layer that is the executor's memory peak,
                # and there was no way to reduce it from the interface.
                {'name': 'chunksize', 'type': 'number', 'label': 'Tamanho do lote (feicoes por COPY)', 'default': 0,
                 'description': 'Quantas feicoes enviar por vez (0 = automatico). Lotes menores usam menos memoria.'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'object', 'description': 'Objeto com a quantidade de linhas inseridas (rowsInserted)'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        conn_str = get_connection(self.parameters)

        # Gets the GeoDataFrame via the base class helper
        gdf = self.get_first_gdf(inputs)

        table_name = self.parameters.get('tableName', '').strip()
        if not table_name:
            raise ValueError("Parâmetro 'tableName' é obrigatório.")
        # Default 'public' when the user does not provide a schema (instead of leaving
        # None and depending on the user's search_path, which may vary).
        schema_raw = (self.parameters.get('schema') or '').strip()
        schema = schema_raw or 'public'
        if_exists = self.parameters.get('ifExists', 'append')
        index = self.parameters.get('index', False)
        # get(key, default) only returns the default if the key is missing;
        # if "" came from the UI, the `or 'geom'` covers it. strip avoids stray spaces.
        geom_col = (self.parameters.get('geometryColumn') or 'geom').strip()
        chunksize_raw = self.parameters.get('chunksize', 0) or 0
        try:
            chunksize = int(chunksize_raw) or _DEFAULT_BATCH
        except (TypeError, ValueError):
            chunksize = _DEFAULT_BATCH

        # Without a CRS, geopandas writes SRID 0 and warns via `warnings.warn` — which
        # shows up nowhere for whoever triggered the workflow. The layer ends up
        # in the database without a coordinate system, and the problem only shows
        # later, when it doesn't line up with anything. `self.log` reaches the run panel.
        if gdf.crs is None:
            self.log(
                f"A camada nao tem CRS definido: a tabela '{schema}.{table_name}' sera "
                "gravada com SRID 0 (indefinido). Defina o CRS antes de salvar para "
                "que ela possa ser reprojetada e cruzada com outras camadas."
            )

        logger.info(
            "Salvando %d feicoes em '%s%s' (geom_col=%s, ifExists=%s, index=%s)",
            len(gdf), f"{schema}." if schema else "", table_name, geom_col, if_exists, index,
        )

        engine = _get_engine(conn_str)
        try:
            await asyncio.to_thread(
                self._save_to_postgis, gdf, table_name, schema, if_exists, index, engine, geom_col, chunksize,
            )
        except Exception as e:
            logger.error(f"Erro ao salvar em PostGIS: {e}")
            raise RuntimeError(f"Erro ao salvar em PostGIS: {e}") from e

        return {'output': {'rowsInserted': len(gdf)}}

    def _save_to_postgis(self, gdf, table_name, schema, if_exists, index, engine, geom_col, chunksize):
        # gdf.to_postgis uses gdf.geometry.name as the column name in the database.
        # Renames the active geometry column to geom_col — without this, a GDF
        # coming from other nodes (which usually have geometry.name=="geometry")
        # would write a "geometry" column instead of "geom" (PostGIS convention).
        if gdf.geometry.name != geom_col:
            gdf = gdf.rename_geometry(geom_col)

        # ONE transaction to empty and write. While there were two, the TRUNCATE
        # committed on its own and a failure while writing left the table EMPTY:
        # the old data was already gone and the new data never arrived.
        with engine.begin() as conn:
            ensure_schema(conn, schema)
            efetivo = if_exists
            # 'truncate' does not exist in to_postgis: we empty the table here and
            # write as 'append' (which also creates the table if it does not exist).
            if efetivo == 'truncate':
                if truncate_table(conn, schema, table_name):
                    logger.info("Tabela '%s.%s' esvaziada (TRUNCATE) antes da gravacao", schema, table_name)
                efetivo = 'append'
            gdf.to_postgis(
                name=table_name,
                con=conn,
                schema=schema,
                if_exists=efetivo,
                index=index,
                chunksize=chunksize,
            )
