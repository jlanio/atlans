"""Ciclo de vida dos nós de consulta em banco.

Os dois nós de leitura não chamavam `self.validate()` — e é só por isso que
funcionavam. `validate_node_parameters` reconstrói os parâmetros a partir das
propriedades DECLARADAS e descarta o resto, e nenhum dos dois declarava
`connectionString`, que é injetada pelo servidor. Bastava alguém seguir a
instrução da docstring de `BaseNode.validate` — que manda chamá-la no início do
`execute()`, como os nós de escrita já faziam — para toda consulta de banco da
plataforma parar de achar a conexão.
"""
import pytest

from flow.nodes.datasource.database_query import DatabaseQuery
from flow.nodes.datasource.database_spatial_query import DatabaseSpatialQuery
from flow.nodes.outputs.save_to_postgres import SaveToPostgres
from flow.nodes.outputs.save_to_postgis import SaveToPostGIS

TODOS = [DatabaseQuery, DatabaseSpatialQuery, SaveToPostgres, SaveToPostGIS]


def _nomes(cls):
    return [p["name"] for p in cls.description()["properties"]]


@pytest.mark.parametrize("cls", TODOS, ids=lambda c: c.__name__)
def test_connectionstring_e_declarada(cls):
    """Guarda direta da causa: sem a declaração, o `validate()` a descarta."""
    assert "connectionString" in _nomes(cls)


@pytest.mark.parametrize("cls", [DatabaseQuery, DatabaseSpatialQuery],
                         ids=lambda c: c.__name__)
def test_conexao_sobrevive_ao_validate(cls):
    no = cls(node_id="n1", parameters={
        "query": "SELECT 1",
        "connectionString": "postgresql://u:p@h/db",  # pragma: allowlist secret
    })
    no.validate()
    assert no.parameters["connectionString"] == "postgresql://u:p@h/db"  # pragma: allowlist secret


@pytest.mark.parametrize("cls", TODOS, ids=lambda c: c.__name__)
def test_execute_chama_validate(cls):
    """Contrato da BaseNode. Os nós de leitura eram os dois que não cumpriam."""
    import inspect
    assert "self.validate()" in inspect.getsource(cls.execute)


def test_timeout_do_espacial_e_declarado():
    """O `execute` sempre leu `timeout`, mas ele não estava na lista de
    propriedades: a UI não desenhava campo, e o único jeito de mudá-lo era
    editar o JSON do workflow na mão."""
    props = {p["name"]: p for p in DatabaseSpatialQuery.description()["properties"]}
    assert "timeout" in props
    assert props["timeout"]["default"] == 120

    no = DatabaseSpatialQuery(node_id="n1", parameters={
        "query": "SELECT 1", "connectionString": "x", "timeout": "600",
    })
    no.validate()
    # Coagido para inteiro pelo próprio validate — o campo da UI grava texto.
    assert no.parameters["timeout"] == 600


def test_defaults_declarados_sao_aplicados_no_espacial():
    no = DatabaseSpatialQuery(node_id="n1", parameters={
        "query": "SELECT 1", "connectionString": "x",
    })
    no.validate()
    assert no.parameters["crs"] == "EPSG:4326"
    assert no.parameters["geometryColumn"] == "geom"
    assert no.parameters["queryParams"] == {}


def test_queryparams_como_texto_json_e_aceito():
    """O canvas só grava primitivos, então estrutura chega serializada."""
    no = DatabaseQuery(node_id="n1", parameters={
        "query": "SELECT 1", "connectionString": "x",
        "queryParams": '{"bairro": "Centro"}',
    })
    no.validate()
    assert no.parameters["queryParams"] == {"bairro": "Centro"}


# ── queryParams vazio vindo da aresta ───────────────────────────────────────

@pytest.mark.parametrize("cls", [DatabaseQuery, DatabaseSpatialQuery],
                         ids=lambda c: c.__name__)
def test_o_no_respeita_o_queryparams_vazio_da_aresta(cls):
    """Guarda de integração: o `or` que causava isso vivia no `execute()`."""
    import inspect
    fonte = inspect.getsource(cls.execute)
    assert "resolver_query_params(inputs, self.parameters)" in fonte
    assert "inputs.get" not in fonte


@pytest.mark.parametrize("cls", [DatabaseQuery, DatabaseSpatialQuery],
                         ids=lambda c: c.__name__)
def test_placeholder_sem_valor_da_erro_acionavel(cls):
    """Com params vazio, o `if query_params:` pulava o `prepare_query` e mandava
    o `:bairro` literal para o Postgres, que respondia com erro de sintaxe
    apontando um caractere. Agora a mensagem diz qual parâmetro falta."""
    import asyncio
    no = cls(node_id="n1", parameters={
        "query": "SELECT * FROM t WHERE b = :bairro",
        "connectionString": "postgresql://u:p@h/db",  # pragma: allowlist secret
    })
    with pytest.raises(ValueError, match="'bairro' não fornecido"):
        asyncio.run(no.execute({"queryParams": {}}))
