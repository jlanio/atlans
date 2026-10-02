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
from flow.utils.credencial import obter_conexao

logger = get_logger(__name__)


# PERF: cursor streaming em chunks — mesmo tamanho do DatabaseSpatialQuery.
_CHUNK_SIZE = 10_000


def _records_to_df(records) -> pd.DataFrame:
    """Converte um lote de Record do asyncpg em DataFrame. Roda em thread."""
    return pd.DataFrame([dict(rec) for rec in records])


def _concat_chunks(chunks: list) -> pd.DataFrame:
    """Junta os DataFrames de cada chunk num so. Roda em thread (ver execute)."""
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


@register_node
class DatabaseQuery(BaseNode):
    """
    Executa uma consulta SQL parametrizada em um banco de dados e retorna o resultado como DataFrame.
    Suporta named parameters no formato :param via queryParams, com fallback a parâmetros estáticos.
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
                    # Injetada pelo servidor a partir de `credential_id`. Precisa
                    # estar declarada: `validate_node_parameters` reconstroi os
                    # parametros a partir desta lista e descarta o que nao esta
                    # nela. O no funcionava sem a declaracao apenas porque nao
                    # chamava `validate()` — bastava alguem seguir a instrucao da
                    # docstring de `BaseNode.validate` para toda consulta de banco
                    # da plataforma parar de achar a conexao. E o mesmo tratamento
                    # que SaveToPostgres e SaveToPostGIS ja faziam. A UI nao
                    # desenha campo para ela (lista de nomes em node-config-form).
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
        conn_str     = obter_conexao(self.parameters)
        raw_query    = self.parameters.get('query', '')
        query_params = resolver_query_params(inputs, self.parameters)

        if not raw_query:
            raise ValueError("Parâmetro 'query' é obrigatório.")

        validate_readonly_sql(raw_query)

        # Antes do pool, como no DatabaseSpatialQuery: montar a query é trabalho
        # puro, e fazê-lo depois de abrir conexão gastava uma ida ao banco para
        # descobrir que faltava um parâmetro — ou prendia uma conexão do pool
        # durante a substituição.
        #
        # Sem o `if query_params:` que havia aqui: com params vazio e query SEM
        # placeholder o `prepare_query` devolve a query intacta, e com
        # placeholder ele levanta "Parâmetro SQL 'x' não fornecido" — que é o
        # erro certo. O desvio antigo pulava justamente esse aviso e mandava o
        # `:bairro` literal para o Postgres, que respondia com erro de sintaxe
        # apontando um caractere.
        prepared_query, values = prepare_query(raw_query, query_params)

        pool = await get_asyncpg_pool(conn_str)

        chunks: list = []
        async with pool.acquire(timeout=15) as connection:
            try:
                # SEG: readonly=True impoe SET TRANSACTION READ ONLY no Postgres.
                # Defesa real no engine — validate_readonly_sql roda antes so para
                # dar erro acionavel ao usuario e barrar o que a transacao nao pega
                # (dblink abre outra conexao, onde o READ ONLY local nao vale).
                #
                # PERF: cursor em chunks (como o DatabaseSpatialQuery) em vez de
                # `fetch()` de tudo. `dict(rec)` + construcao do DataFrame de
                # centenas de milhares de linhas de UMA vez segurava o event loop
                # por dezenas de segundos (passando de 90s o servidor fecha a
                # sessao com 4408). Cada chunk vira DataFrame numa thread; a
                # conversao nao bloqueia o loop entre uma busca e outra.
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

        # Concatena fora do `acquire`: a conexao do pool nao fica presa durante a
        # montagem final do DataFrame.
        df = await asyncio.to_thread(_concat_chunks, chunks)

        return {"output": df}
