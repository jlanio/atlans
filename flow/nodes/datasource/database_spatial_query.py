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
    """Converte um chunk de Record em DataFrame. Roda em thread (ver execute)."""
    return pd.DataFrame([dict(r) for r in batch])


def _montar_gdf(chunks: list, geom_col: str, crs: str) -> gpd.GeoDataFrame:
    """Concatena os chunks e converte o WKB em geometria. Roda em thread.

    É o trecho mais pesado do nó: `pd.concat` copia o resultado inteiro e o
    `from_wkb` percorre todas as geometrias. No event loop isso deixava o
    executor mudo por dezenas de segundos no fim de uma consulta grande.
    """
    df = pd.concat(chunks, ignore_index=True)
    if geom_col not in df.columns:
        raise ValueError(f"Coluna '{geom_col}' não encontrada nos resultados.")

    # F3: from_wkb espera bytes/hex. Se o usuario escreveu ST_AsText(...) na
    # query, chega WKT (texto) e o shapely explode com erro obscuro. Sample
    # do primeiro nao-nulo detecta o caso e da mensagem acionavel.
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

    # PERF: from_wkb vetorizado aceita arrays, ~10x mais rápido que .apply(wkb.loads)
    df["geometry"] = from_wkb(df[geom_col])
    return gpd.GeoDataFrame(df.drop(columns=[geom_col]), geometry="geometry", crs=crs)


@register_node
class DatabaseSpatialQuery(BaseNode):
    """
    Executa uma consulta espacial que retorna geometria WKB e converte em GeoDataFrame.
    Requer que o campo 'connectionString' já esteja resolvido nos parâmetros.
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
                # Injetada pelo servidor a partir de `credential_id`. Precisa estar
                # declarada: `validate_node_parameters` reconstroi os parametros a
                # partir desta lista e descarta o que nao esta nela. O no
                # funcionava sem a declaracao apenas porque nao chamava
                # `validate()`. A UI nao desenha campo para ela.
                {'name': 'connectionString', 'type': 'string', 'default': '', 'description': 'DSN de conexao (injetada automaticamente pela credencial)'},
                {'name': 'query', 'required': True,           'label': 'Consulta SQL', 'type': 'sql', 'default': '', 'description': 'Query SQL (apenas SELECT)'},
                {'name': 'queryParams',     'label': 'Parâmetros da consulta', 'type': 'object', 'default': {}, 'description': 'Valores para os placeholders nomeados :param'},
                {'name': 'geometryColumn',  'label': 'Coluna de geometria', 'type': 'string', 'default': 'geom'},
                {'name': 'crs',             'label': 'CRS de entrada', 'type': 'string', 'default': 'EPSG:4326'},
                # O `execute` sempre leu este parametro, mas ele nunca foi
                # declarado: sem entrada aqui a UI nao desenha campo nenhum, e o
                # unico jeito de mudar o tempo limite era editar o JSON do
                # workflow na mao. Consulta espacial grande e exatamente o caso
                # em que 120s nao basta.
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
        # F1: usuario pode ter salvo o campo em branco — get(chave, "geom") so
        # aplica o default se a CHAVE estiver ausente, nao se for "". Trim
        # remove espacos acidentais na UI.
        geom_col = (self.parameters.get("geometryColumn") or "geom").strip()

        if not raw_query:
            raise ValueError("Parâmetro 'query' é obrigatório.")

        validate_readonly_sql(raw_query)

        # Substitui :placeholders por $1, $2, ... com valores seguros
        # Sem o `if`: com params vazio e query SEM placeholder o
        # `prepare_query` devolve a query intacta, e com placeholder ele levanta
        # "Parâmetro SQL 'x' não fornecido" — que é o erro certo. O desvio antigo
        # pulava esse aviso e mandava o `:bairro` literal para o Postgres.
        prepared_query, values = prepare_query(raw_query, query_params)

        # PERF: timeout configurável (padrão 120s) para queries grandes
        _timeout = int(self.parameters.get("timeout", 120))
        _CHUNK_SIZE = 10_000

        pool = await get_asyncpg_pool(conn_str)
        async with pool.acquire(timeout=_timeout) as conn:
            try:
                # PERF: cursor streaming em chunks — evita materializar milhões de registros de uma vez
                # SEG: readonly=True impoe SET TRANSACTION READ ONLY no Postgres.
                # Defesa real no engine — validate_readonly_sql roda antes so para
                # dar erro acionavel ao usuario e barrar o que a transacao nao pega
                # (dblink abre outra conexao, onde o READ ONLY local nao vale).
                chunks = []
                async with conn.transaction(readonly=True):
                    cursor = await conn.cursor(prepared_query, *values)
                    while True:
                        batch = await cursor.fetch(_CHUNK_SIZE)
                        if not batch:
                            break
                        # Cada chunk vira DataFrame numa thread: com 10k registros
                        # por batch, montar no loop bloqueava o WebSocket entre uma
                        # busca e outra.
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
        # F1: mesmo normalize do execute — campo vazio na UI cai no default.
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
