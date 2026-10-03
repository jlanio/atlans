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
from flow.utils.sql_engine import lote_seguro, _MAX_PARAMETROS_POR_INSTRUCAO


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
def test_o_lote_nunca_estoura_o_limite_do_protocolo(linhas, colunas):
    lote = lote_seguro(colunas, 0)
    assert lote * colunas <= _MAX_PARAMETROS_POR_INSTRUCAO
    assert lote >= 1


def test_lote_escolhido_pelo_usuario_e_respeitado():
    assert lote_seguro(10, 1_000) == 1_000


def test_lote_escolhido_grande_demais_e_cortado():
    """How many rows go per statement is performance tuning; no performance
    value justifies building a statement the database refuses."""
    lote = lote_seguro(10, 50_000)
    assert lote * 10 <= _MAX_PARAMETROS_POR_INSTRUCAO


def test_tabela_com_muitas_colunas_ainda_grava_uma_linha_por_vez():
    assert lote_seguro(100_000, 0) == 1


def test_o_no_deriva_o_lote_do_numero_de_colunas(monkeypatch):
    """Integration: the value that reaches `to_sql` has to fit in the protocol."""
    recebido = {}
    df = pd.DataFrame({f"c{i}": range(10) for i in range(10)})

    def espia(**kw):
        recebido.update(kw)

    monkeypatch.setattr(pd.DataFrame, "to_sql", lambda self, *a, **kw: espia(**kw))
    engine = sa.create_engine("sqlite://")
    no = SaveToPostgres(node_id="n1", parameters={})
    no._save_to_postgres(df, "t", None, "append", False, 0, engine)

    assert recebido["chunksize"] * 10 <= _MAX_PARAMETROS_POR_INSTRUCAO
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


def _conta(engine, tabela="destino"):
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


def test_gravacao_que_falha_nao_deixa_a_tabela_vazia(banco, truncate_sqlite, monkeypatch):
    df = pd.DataFrame({"a": [9, 9]})

    def explode(self, *a, **kw):
        raise RuntimeError("tipo incompativel")
    monkeypatch.setattr(pd.DataFrame, "to_sql", explode)

    no = SaveToPostgres(node_id="n1", parameters={})
    with pytest.raises(RuntimeError, match="tipo incompativel"):
        no._save_to_postgres(df, "destino", None, "truncate", False, 0, banco)

    # Before: 0 — TRUNCATE had already committed on its own.
    assert _conta(banco) == 3


def test_limpar_e_gravar_com_sucesso_substitui_o_conteudo(banco, truncate_sqlite):
    no = SaveToPostgres(node_id="n1", parameters={})
    no._save_to_postgres(pd.DataFrame({"a": [7]}), "destino", None, "truncate", False, 0, banco)

    assert _conta(banco) == 1
    with banco.connect() as c:
        assert c.exec_driver_sql("SELECT a FROM destino").scalar() == 7


# ── Structure: the connection is shared ─────────────────────────────────────

@pytest.mark.parametrize("cls,metodo", [
    (SaveToPostgres, "_save_to_postgres"),
    (SaveToPostGIS, "_save_to_postgis"),
])
def test_o_no_grava_dentro_de_uma_transacao(cls, metodo):
    """Direct guard on the cause: passing the ENGINE to `to_sql`/`to_postgis`
    opens a new connection, outside the TRUNCATE's transaction."""
    import inspect
    fonte = inspect.getsource(getattr(cls, metodo))
    assert "with engine.begin() as conn:" in fonte
    assert "con=conn" in fonte
    assert "con=engine" not in fonte


# ── CRS ausente ─────────────────────────────────────────────────────────────

def test_camada_sem_crs_avisa_no_painel_da_run(caplog):
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

    async def falso_thread(fn, *a):
        return None

    # The warning goes out BEFORE any contact with the database — that order is
    # what matters, and it is what the test pins down. `_get_engine` and the write
    # become no-ops (the test environment has no psycopg2, and doesn't need it).
    with patch.object(mod_gis, "_get_engine", return_value=object()), \
         patch.object(mod_gis.asyncio, "to_thread", falso_thread), \
         caplog.at_level(logging.INFO):
        asyncio.run(no.execute({"camada": gdf}))

    assert "SRID 0" in caplog.text


def test_camada_com_crs_nao_gera_aviso(caplog):
    import geopandas as gpd
    from shapely.geometry import Point
    import flow.nodes.outputs.save_to_postgis as mod_gis
    from unittest.mock import patch

    gdf = gpd.GeoDataFrame({"a": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    no = SaveToPostGIS(node_id="n1", parameters={
        "connectionString": "postgresql://u:p@h/db",  # pragma: allowlist secret
        "tableName": "destino",
    })

    async def falso_thread(fn, *a):
        return None

    with patch.object(mod_gis, "_get_engine", return_value=object()), \
         patch.object(mod_gis.asyncio, "to_thread", falso_thread), \
         caplog.at_level(logging.INFO):
        asyncio.run(no.execute({"camada": gdf}))

    assert "SRID 0" not in caplog.text


# ── Same guarantee in PostGIS ───────────────────────────────────────────────
#
# geopandas reuses the transaction when it receives an already open Connection
# (`_get_conn`), so the write goes into the SAME transaction as the TRUNCATE.

def test_postgis_gravacao_que_falha_nao_deixa_a_tabela_vazia(banco, monkeypatch):
    import flow.nodes.outputs.save_to_postgis as mod_gis

    monkeypatch.setattr(mod_gis, "ensure_schema", lambda conn, schema: None)
    def falso_truncate(conn, schema, table):
        conn.exec_driver_sql(f"DELETE FROM {table}")
        return True
    monkeypatch.setattr(mod_gis, "truncate_table", falso_truncate)

    import geopandas as gpd
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({"a": [9]}, geometry=[Point(0, 0)], crs="EPSG:4326")

    def explode(self, *a, **kw):
        raise RuntimeError("SRID divergente")
    monkeypatch.setattr(gpd.GeoDataFrame, "to_postgis", explode)

    no = SaveToPostGIS(node_id="n1", parameters={})
    with pytest.raises(RuntimeError, match="SRID divergente"):
        no._save_to_postgis(gdf, "destino", None, "truncate", False, banco, "geom", 50_000)

    assert _conta(banco) == 3


def test_postgis_passa_o_lote_adiante(banco, monkeypatch):
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


def test_postgis_renomeia_a_geometria_para_a_coluna_configurada(banco, monkeypatch):
    """A GDF coming from other nodes arrives with geometry.name == 'geometry'; the
    PostGIS table convention is 'geom'."""
    import flow.nodes.outputs.save_to_postgis as mod_gis
    monkeypatch.setattr(mod_gis, "ensure_schema", lambda conn, schema: None)

    import geopandas as gpd
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({"a": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    assert gdf.geometry.name == "geometry"

    visto = {}
    def espia(self, *a, **kw):
        visto["nome"] = self.geometry.name
    monkeypatch.setattr(gpd.GeoDataFrame, "to_postgis", espia)

    no = SaveToPostGIS(node_id="n1", parameters={})
    no._save_to_postgis(gdf, "destino", None, "append", False, banco, "geom", 0)

    assert visto["nome"] == "geom"
