import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.sql_engine import make_engine_cache, get_engine, ensure_schema, truncate_table, lote_seguro
from flow.utils.credencial import obter_conexao

logger = get_logger(__name__)

# Cache separado do SaveToPostGIS para não competir por slots do TTLCache
# quando os dois nodes rodam concorrentes no mesmo executor.
_engine_cache = make_engine_cache("SaveToPostgres")


def _get_engine(conn_str: str):
    return get_engine(_engine_cache, conn_str, label="SaveToPostgres")


@register_node
class SaveToPostgres(BaseNode):
    """
    No que escreve um DataFrame em uma tabela PostgreSQL comum (sem PostGIS).

    Aceita `pandas.DataFrame` OU `geopandas.GeoDataFrame`. Se receber um
    GDF, a coluna de geometria e removida automaticamente antes do insert
    (Postgres puro nao lida com geometria — para gravar com geom, use
    SaveToPostGIS).

    Propriedades:
      - credential_id: UUID da credencial PostgreSQL
      - connectionString: DSN (injetado pelo backend via credencial)
      - tableName: nome da tabela destino (obrigatorio)
      - schema: schema Postgres (default 'public' quando vazio)
      - ifExists: 'fail' | 'replace' | 'truncate' | 'append' (default 'append')
      - index: gravar indice do DataFrame como coluna (default False)
      - chunksize: linhas por batch no INSERT (0 -> automatico pelo n. de colunas)
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
                # Injetada pelo backend via inject_credentials — precisa estar
                # declarada aqui, senao validate_node_parameters descarta a chave
                # apos self.validate() no execute() e o node explode com
                # "Parametro 'connectionString' e obrigatorio.". Frontend nao
                # renderiza campo (whitelist em node-config-form.tsx).
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

        # Default 'public' quando o usuario nao informa schema (em vez de deixar
        # None e depender do search_path do usuario, que pode variar).
        schema_raw = (self.parameters.get('schema') or '').strip()
        schema = schema_raw or 'public'
        if_exists = self.parameters.get('ifExists', 'append')
        index = self.parameters.get('index', False)
        chunksize_raw = self.parameters.get('chunksize', 0) or 0
        try:
            chunksize = int(chunksize_raw) or None
        except (TypeError, ValueError):
            chunksize = None

        # Dropa coluna de geometria se o input for GeoDataFrame — Postgres
        # puro sem extensao PostGIS nao aceita geometry. Usuario que queira
        # persistir geom deve usar SaveToPostGIS.
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
        """Retorna o primeiro DataFrame (pandas ou geopandas) nao vazio."""
        import pandas as pd
        for value in inputs.values():
            if isinstance(value, pd.DataFrame) and not value.empty:
                return value
        raise ValueError("Nenhum DataFrame encontrado nos inputs.")

    def _drop_geometry_column(self, df):
        """Se for GeoDataFrame, remove a coluna ativa de geometria."""
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
        # `method='multi'` monta UM INSERT com um parametro por celula, e o
        # protocolo do Postgres nao aceita mais de 65535 por instrucao. Com o
        # lote em 0 (o padrao de fabrica, cuja ajuda diz "todas de uma vez"),
        # qualquer tabela de 10 colunas com mais de ~6.500 linhas era recusada
        # pelo driver. O lote passa a ser derivado do numero de colunas.
        colunas = len(df.columns) + (1 if index else 0)
        lote = lote_seguro(colunas, chunksize)
        if chunksize and lote < chunksize:
            logger.warning(
                "Lote de %s linhas excede o limite do protocolo para %d colunas; "
                "usando %d linhas por instrucao.", chunksize, colunas, lote,
            )

        # UMA transacao para esvaziar e gravar. Enquanto eram duas, o TRUNCATE
        # commitava sozinho e uma falha na gravacao deixava a tabela VAZIA: o
        # dado velho ja tinha ido e o novo nunca chegou.
        with engine.begin() as conn:
            ensure_schema(conn, schema)
            efetivo = if_exists
            # 'truncate' nao existe no to_sql: esvaziamos a tabela aqui e
            # gravamos como 'append' (que tambem cria a tabela se nao existir).
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
                method='multi',  # 1 INSERT com multi-values — mais rapido em batches
            )
