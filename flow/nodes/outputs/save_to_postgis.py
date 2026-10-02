import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.sql_engine import make_engine_cache, get_engine, ensure_schema, truncate_table
from flow.utils.credencial import obter_conexao

logger = get_logger(__name__)

# Feicoes por COPY quando o usuario deixa o lote em automatico. O COPY nao tem
# limite de parametros como o INSERT, entao o que este numero controla e
# MEMORIA: o geopandas serializa cada lote num CSV em RAM antes de enviar.
_LOTE_PADRAO = 50_000

# Cache próprio (separado do SaveToPostgres) para não competir por slots.
_engine_cache = make_engine_cache("SaveToPostGIS")


def _get_engine(conn_str: str):
    return get_engine(_engine_cache, conn_str, label="SaveToPostGIS")


@register_node
class SaveToPostGIS(BaseNode):
    """
    Nó que escreve um GeoDataFrame em uma tabela PostGIS.

    Propriedades:
      - connectionString: DSN de conexão para o banco (string; obrigatório)
      - tableName: nome da tabela destino (string; obrigatório)
      - schema: schema Postgres (string; default 'public' quando vazio)
      - geometryColumn: nome da coluna geometria na tabela PostGIS (string; default 'geom')
      - ifExists: comportamento se a tabela já existir ('fail'|'replace'|'truncate'|'append'; default 'append')
      - index: salvar índice no PostGIS (boolean; default False)
      - chunksize: feições por COPY (0 -> automático; controla o pico de memória)
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
                # Injetada pelo backend via inject_credentials — precisa estar
                # declarada aqui, senao validate_node_parameters descarta a chave
                # apos self.validate() no execute() e o node explode com
                # "Parametro 'connectionString' e obrigatorio.". Frontend nao
                # renderiza campo (whitelist em node-config-form.tsx).
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
                # Sem lote, o geopandas monta o CSV do COPY com a camada
                # INTEIRA num buffer de memoria antes de enviar a primeira
                # linha. Numa camada grande isso e o pico de memoria do
                # executor, e nao havia como reduzi-lo pela interface.
                {'name': 'chunksize', 'type': 'number', 'label': 'Tamanho do lote (feicoes por COPY)', 'default': 0,
                 'description': 'Quantas feicoes enviar por vez (0 = automatico). Lotes menores usam menos memoria.'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'object', 'description': 'Objeto com a quantidade de linhas inseridas (rowsInserted)'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        conn_str = obter_conexao(self.parameters)

        # Obtém o GeoDataFrame via helper da classe base
        gdf = self.get_first_gdf(inputs)

        table_name = self.parameters.get('tableName', '').strip()
        if not table_name:
            raise ValueError("Parâmetro 'tableName' é obrigatório.")
        # Default 'public' quando o usuario nao informa schema (em vez de deixar
        # None e depender do search_path do usuario, que pode variar).
        schema_raw = (self.parameters.get('schema') or '').strip()
        schema = schema_raw or 'public'
        if_exists = self.parameters.get('ifExists', 'append')
        index = self.parameters.get('index', False)
        # get(chave, default) so devolve default se a chave estiver ausente;
        # se veio "" da UI, o `or 'geom'` cobre. strip evita espacos acidentais.
        geom_col = (self.parameters.get('geometryColumn') or 'geom').strip()
        chunksize_raw = self.parameters.get('chunksize', 0) or 0
        try:
            chunksize = int(chunksize_raw) or _LOTE_PADRAO
        except (TypeError, ValueError):
            chunksize = _LOTE_PADRAO

        # Sem CRS, o geopandas grava SRID 0 e avisa por `warnings.warn` — que
        # nao aparece em lugar nenhum para quem disparou o fluxo. A camada fica
        # no banco sem sistema de coordenadas, e o problema so aparece depois,
        # quando ela nao se alinha com nada. `self.log` chega ao painel da run.
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
        # gdf.to_postgis usa gdf.geometry.name como nome da coluna no banco.
        # Renomeia a coluna ativa de geometria para geom_col — sem isso, um GDF
        # vindo de outros nodes (que normalmente tem geometry.name=="geometry")
        # gravaria uma coluna "geometry" em vez de "geom" (convencao PostGIS).
        if gdf.geometry.name != geom_col:
            gdf = gdf.rename_geometry(geom_col)

        # UMA transacao para esvaziar e gravar. Enquanto eram duas, o TRUNCATE
        # commitava sozinho e uma falha na gravacao deixava a tabela VAZIA: o
        # dado velho ja tinha ido e o novo nunca chegou.
        with engine.begin() as conn:
            ensure_schema(conn, schema)
            efetivo = if_exists
            # 'truncate' nao existe no to_postgis: esvaziamos a tabela aqui e
            # gravamos como 'append' (que tambem cria a tabela se nao existir).
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
