"""Database write nodes: SaveToPostgres and SaveToPostGIS.

Two defects that only show up on the happy path of large tables or on the
unhappy path of a write that fails — neither of them had a test.
"""
import asyncio
import logging

import pandas as pd
import pytest
import sqlalchemy as sa

import flow.nodes.outputs.save_to_postgres as mod_pg
from flow.nodes.outputs.save_to_postgres import SaveToPostgres
from flow.nodes.outputs.save_to_postgis import SaveToPostGIS
from flow.utils.sql_engine import safe_batch_size, _MAX_PARAMS_PER_STATEMENT


# ── Safe batch ──────────────────────────────────────────────────────────────
#
# `method='multi'` builds ONE `INSERT ... VALUES (...), (...)` with one parameter
# per cell, and the Postgres protocol doesn't accept more than 65535 per statement.
# The batch field came with 0 out of the box and the help said "0 = todas de uma
# vez" (0 = all at once): the default was exactly the value that breaks.

@pytest.mark.parametrize("linhas,colunas", [
    (8_000, 10),      # 80,000 parameters — overflowed
    (100_000, 3),     # 300.000
    (500, 200),       # 100.000
    (10, 2),          # fit, and has to keep fitting
])
def test_the_batch_never_exceeds_the_protocol_limit(linhas, colunas):
    lote = safe_batch_size(colunas, 0)
    assert lote * colunas <= _MAX_PARAMS_PER_STATEMENT
    assert lote >= 1


def test_batch_chosen_by_the_user_is_respected():
    assert safe_batch_size(10, 1_000) == 1_000


def test_chosen_batch_too_large_is_cut():
    """How many rows go per statement is performance tuning; no performance
    value justifies building a statement the database refuses."""
    lote = safe_batch_size(10, 50_000)
    assert lote * 10 <= _MAX_PARAMS_PER_STATEMENT


def test_table_with_many_columns_still_writes_one_row_at_a_time():
    assert safe_batch_size(100_000, 0) == 1


def test_the_node_derives_the_batch_from_the_column_count(monkeypatch):
    """Integration: the value that reaches `to_sql` has to fit in the protocol."""
    recebido = {}
    df = pd.DataFrame({f"c{i}": range(10) for i in range(10)})

    def spy(**kw):
        recebido.update(kw)

    monkeypatch.setattr(pd.DataFrame, "to_sql", lambda self, *a, **kw: spy(**kw))
    engine = sa.create_engine("sqlite://")
    no = SaveToPostgres(node_id="n1", parameters={})
    no._save_to_postgres(df, "t", None, "append", False, 0, engine)

    assert recebido["chunksize"] * 10 <= _MAX_PARAMS_PER_STATEMENT
    assert recebido["method"] == "multi"


# ── Atomicity of "clear and write" ──────────────────────────────────────────
#
# TRUNCATE opened ITS OWN transaction and committed on its own; the write came
# afterwards, in another one. A failure in between — incompatible type, network
# drop — left the table EMPTY: the old data was already gone and the new never
# arrived. In an option called "clear and write", losing both ends is the worst
# outcome.
#
# The test uses sqlite, which has no TRUNCATE: only the command is swapped for
# DELETE. The transaction structure exercised is the node's, with no simulation.

@pytest.fixture
def banco(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path/'t.db'}")
    pd.DataFrame({"a": [1, 2, 3]}).to_sql("destino", engine, index=False)
    return engine


def _count(engine, tabela="destino"):
    with engine.connect() as c:
        return c.exec_driver_sql(f"SELECT count(*) FROM {tabela}").scalar()


@pytest.fixture
def truncate_sqlite(monkeypatch):
    """`TRUNCATE` doesn't exist in sqlite — same semantics via DELETE."""
    def falso(conn, schema, table):
        conn.exec_driver_sql(f"DELETE FROM {table}")
        return True
    monkeypatch.setattr(mod_pg, "truncate_table", falso)
    monkeypatch.setattr(mod_pg, "ensure_schema", lambda conn, schema: None)


def test_failing_write_does_not_leave_the_table_empty(banco, truncate_sqlite, monkeypatch):
    df = pd.DataFrame({"a": [9, 9]})

    def explode(self, *a, **kw):
        raise RuntimeError("tipo incompativel")
    monkeypatch.setattr(pd.DataFrame, "to_sql", explode)

    no = SaveToPostgres(node_id="n1", parameters={})
    with pytest.raises(RuntimeError, match="tipo incompativel"):
        no._save_to_postgres(df, "destino", None, "truncate", False, 0, banco)

    # Before: 0 — TRUNCATE had already committed on its own.
    assert _count(banco) == 3


def test_successful_clear_and_write_replaces_the_content(banco, truncate_sqlite):
    no = SaveToPostgres(node_id="n1", parameters={})
    no._save_to_postgres(pd.DataFrame({"a": [7]}), "destino", None, "truncate", False, 0, banco)

    assert _count(banco) == 1
    with banco.connect() as c:
        assert c.exec_driver_sql("SELECT a FROM destino").scalar() == 7


# ── Structure: the connection is shared ─────────────────────────────────────

@pytest.mark.parametrize("cls,metodo", [
    (SaveToPostgres, "_save_to_postgres"),
    (SaveToPostGIS, "_save_to_postgis"),
])
def test_the_node_writes_inside_a_transaction(cls, metodo):
    """Direct guard on the cause: passing the ENGINE to `to_sql`/`to_postgis`
    opens a new connection, outside the TRUNCATE's transaction."""
    import inspect
    fonte = inspect.getsource(getattr(cls, metodo))
    assert "with engine.begin() as conn:" in fonte
    assert "con=conn" in fonte
    assert "con=engine" not in fonte


# ── CRS ausente ─────────────────────────────────────────────────────────────

def test_layer_without_crs_warns_in_the_run_panel(caplog):
    """geopandas writes SRID 0 and warns via `warnings.warn`, which doesn't show
    up for whoever triggered the workflow. The layer sits in the database with
    no coordinate system and the problem only shows when it aligns with nothing."""
    import geopandas as gpd
    from shapely.geometry import Point

    gdf = gpd.GeoDataFrame({"a": [1]}, geometry=[Point(0, 0)], crs=None)
    no = SaveToPostGIS(node_id="n1", parameters={
        "connectionString": "postgresql://u:p@h/db",  # pragma: allowlist secret
        "tableName": "destino",
    })

    import flow.nodes.outputs.save_to_postgis as mod_gis
    from unittest.mock import patch

    async def fake_thread(fn, *a):
        return None

    # The warning goes out BEFORE any contact with the database — that order is
    # what matters, and it is what the test pins down. `_get_engine` and the write
    # become no-ops (the test environment has no psycopg2, and doesn't need it).
    with patch.object(mod_gis, "_get_engine", return_value=object()), \
         patch.object(mod_gis.asyncio, "to_thread", fake_thread), \
         caplog.at_level(logging.INFO):
        asyncio.run(no.execute({"camada": gdf}))

    assert "SRID 0" in caplog.text


def test_layer_with_crs_does_not_warn(caplog):
    import geopandas as gpd
    from shapely.geometry import Point
    import flow.nodes.outputs.save_to_postgis as mod_gis
    from unittest.mock import patch

    gdf = gpd.GeoDataFrame({"a": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    no = SaveToPostGIS(node_id="n1", parameters={
        "connectionString": "postgresql://u:p@h/db",  # pragma: allowlist secret
        "tableName": "destino",
    })

    async def fake_thread(fn, *a):
        return None

    with patch.object(mod_gis, "_get_engine", return_value=object()), \
         patch.object(mod_gis.asyncio, "to_thread", fake_thread), \
         caplog.at_level(logging.INFO):
        asyncio.run(no.execute({"camada": gdf}))

    assert "SRID 0" not in caplog.text


# ── Same guarantee in PostGIS ───────────────────────────────────────────────
#
# geopandas reuses the transaction when it receives an already open Connection
# (`_get_conn`), so the write goes into the SAME transaction as the TRUNCATE.

def test_postgis_failing_write_does_not_leave_the_table_empty(banco, monkeypatch):
    import flow.nodes.outputs.save_to_postgis as mod_gis

    monkeypatch.setattr(mod_gis, "ensure_schema", lambda conn, schema: None)
    def fake_truncate(conn, schema, table):
        conn.exec_driver_sql(f"DELETE FROM {table}")
        return True
    monkeypatch.setattr(mod_gis, "truncate_table", fake_truncate)

    import geopandas as gpd
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({"a": [9]}, geometry=[Point(0, 0)], crs="EPSG:4326")

    def explode(self, *a, **kw):
        raise RuntimeError("SRID divergente")
    monkeypatch.setattr(gpd.GeoDataFrame, "to_postgis", explode)

    no = SaveToPostGIS(node_id="n1", parameters={})
    with pytest.raises(RuntimeError, match="SRID divergente"):
        no._save_to_postgis(gdf, "destino", None, "truncate", False, banco, "geom", 50_000)

    assert _count(banco) == 3


def test_postgis_passes_the_batch_along(banco, monkeypatch):
    """Without batching, geopandas serializes the WHOLE layer into an in-memory
    CSV before sending the first row."""
    import flow.nodes.outputs.save_to_postgis as mod_gis
    monkeypatch.setattr(mod_gis, "ensure_schema", lambda conn, schema: None)

    recebido = {}
    import geopandas as gpd
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({"a": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    monkeypatch.setattr(gpd.GeoDataFrame, "to_postgis",
                        lambda self, *a, **kw: recebido.update(kw))

    no = SaveToPostGIS(node_id="n1", parameters={})
    no._save_to_postgis(gdf, "destino", None, "append", False, banco, "geom", 12_345)

    assert recebido["chunksize"] == 12_345


def test_postgis_renames_the_geometry_to_the_configured_column(banco, monkeypatch):
    """A GDF coming from other nodes arrives with geometry.name == 'geometry'; the
    PostGIS table convention is 'geom'."""
    import flow.nodes.outputs.save_to_postgis as mod_gis
    monkeypatch.setattr(mod_gis, "ensure_schema", lambda conn, schema: None)

    import geopandas as gpd
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({"a": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    assert gdf.geometry.name == "geometry"

    visto = {}
    def spy(self, *a, **kw):
        visto["nome"] = self.geometry.name
    monkeypatch.setattr(gpd.GeoDataFrame, "to_postgis", spy)

    no = SaveToPostGIS(node_id="n1", parameters={})
    no._save_to_postgis(gdf, "destino", None, "append", False, banco, "geom", 0)

    assert visto["nome"] == "geom"
