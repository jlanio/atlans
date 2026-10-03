"""Lifecycle of the database query nodes.

The two read nodes didn't call `self.validate()` — and that is the only reason
they worked. `validate_node_parameters` rebuilds the parameters from the
DECLARED properties and discards the rest, and neither of them declared
`connectionString`, which is injected by the server. All it took was someone
following the instruction in `BaseNode.validate`'s docstring — which says to
call it at the start of `execute()`, as the write nodes already did — for every
database query on the platform to stop finding the connection.
"""
import pytest

from flow.nodes.datasource.database_query import DatabaseQuery
from flow.nodes.datasource.database_spatial_query import DatabaseSpatialQuery
from flow.nodes.outputs.save_to_postgres import SaveToPostgres
from flow.nodes.outputs.save_to_postgis import SaveToPostGIS

TODOS = [DatabaseQuery, DatabaseSpatialQuery, SaveToPostgres, SaveToPostGIS]


def _names(cls):
    return [p["name"] for p in cls.description()["properties"]]


@pytest.mark.parametrize("cls", TODOS, ids=lambda c: c.__name__)
def test_connectionstring_is_declared(cls):
    """Direct guard on the cause: without the declaration, `validate()` discards it."""
    assert "connectionString" in _names(cls)


@pytest.mark.parametrize("cls", [DatabaseQuery, DatabaseSpatialQuery],
                         ids=lambda c: c.__name__)
def test_connection_survives_validate(cls):
    no = cls(node_id="n1", parameters={
        "query": "SELECT 1",
        "connectionString": "postgresql://u:p@h/db",  # pragma: allowlist secret
    })
    no.validate()
    assert no.parameters["connectionString"] == "postgresql://u:p@h/db"  # pragma: allowlist secret


@pytest.mark.parametrize("cls", TODOS, ids=lambda c: c.__name__)
def test_execute_calls_validate(cls):
    """BaseNode's contract. The read nodes were the two that didn't comply."""
    import inspect
    assert "self.validate()" in inspect.getsource(cls.execute)


def test_spatial_timeout_is_declared():
    """`execute` always read `timeout`, but it wasn't in the property list:
    the UI drew no field, and the only way to change it was editing the
    workflow's JSON by hand."""
    props = {p["name"]: p for p in DatabaseSpatialQuery.description()["properties"]}
    assert "timeout" in props
    assert props["timeout"]["default"] == 120

    no = DatabaseSpatialQuery(node_id="n1", parameters={
        "query": "SELECT 1", "connectionString": "x", "timeout": "600",
    })
    no.validate()
    # Coerced to an integer by validate itself — the UI field saves text.
    assert no.parameters["timeout"] == 600


def test_declared_defaults_are_applied_in_the_spatial_one():
    no = DatabaseSpatialQuery(node_id="n1", parameters={
        "query": "SELECT 1", "connectionString": "x",
    })
    no.validate()
    assert no.parameters["crs"] == "EPSG:4326"
    assert no.parameters["geometryColumn"] == "geom"
    assert no.parameters["queryParams"] == {}


def test_queryparams_as_json_text_is_accepted():
    """The canvas only saves primitives, so structures arrive serialized."""
    no = DatabaseQuery(node_id="n1", parameters={
        "query": "SELECT 1", "connectionString": "x",
        "queryParams": '{"bairro": "Centro"}',
    })
    no.validate()
    assert no.parameters["queryParams"] == {"bairro": "Centro"}


# ── Empty queryParams coming from the edge ──────────────────────────────────

@pytest.mark.parametrize("cls", [DatabaseQuery, DatabaseSpatialQuery],
                         ids=lambda c: c.__name__)
def test_the_node_respects_the_empty_queryparams_from_the_edge(cls):
    """Integration guard: the `or` that caused this lived in `execute()`."""
    import inspect
    fonte = inspect.getsource(cls.execute)
    assert "resolver_query_params(inputs, self.parameters)" in fonte
    assert "inputs.get" not in fonte


@pytest.mark.parametrize("cls", [DatabaseQuery, DatabaseSpatialQuery],
                         ids=lambda c: c.__name__)
def test_placeholder_without_value_gives_actionable_error(cls):
    """With empty params, `if query_params:` skipped `prepare_query` and sent the
    literal `:bairro` to Postgres, which answered with a syntax error pointing
    at a character. Now the message says which parameter is missing."""
    import asyncio
    no = cls(node_id="n1", parameters={
        "query": "SELECT * FROM t WHERE b = :bairro",
        "connectionString": "postgresql://u:p@h/db",  # pragma: allowlist secret
    })
    with pytest.raises(ValueError, match="'bairro' não fornecido"):
        asyncio.run(no.execute({"queryParams": {}}))
