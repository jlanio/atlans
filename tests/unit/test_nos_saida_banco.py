"""Nós de escrita em banco: SaveToPostgres e SaveToPostGIS.

Dois defeitos que só aparecem no caminho feliz de tabelas grandes ou no
caminho infeliz de uma gravação que falha — nenhum dos dois tinha teste.
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


# ── Lote seguro ─────────────────────────────────────────────────────────────
#
# `method='multi'` monta UM `INSERT ... VALUES (...), (...)` com um parâmetro
# por célula, e o protocolo do Postgres não aceita mais de 65535 por instrução.
# O campo de lote vinha com 0 de fábrica e a ajuda dizia "0 = todas de uma vez":
# o padrão era exatamente o valor que quebra.

@pytest.mark.parametrize("linhas,colunas", [
    (8_000, 10),      # 80.000 parâmetros — estourava
    (100_000, 3),     # 300.000
    (500, 200),       # 100.000
    (10, 2),          # cabia, e tem de continuar cabendo
])
def test_o_lote_nunca_estoura_o_limite_do_protocolo(linhas, colunas):
    lote = lote_seguro(colunas, 0)
    assert lote * colunas <= _MAX_PARAMETROS_POR_INSTRUCAO
    assert lote >= 1


def test_lote_escolhido_pelo_usuario_e_respeitado():
    assert lote_seguro(10, 1_000) == 1_000


def test_lote_escolhido_grande_demais_e_cortado():
    """Quantas linhas vão por instrução é ajuste de desempenho; nenhum valor de
    desempenho justifica montar uma instrução que o banco recusa."""
    lote = lote_seguro(10, 50_000)
    assert lote * 10 <= _MAX_PARAMETROS_POR_INSTRUCAO


def test_tabela_com_muitas_colunas_ainda_grava_uma_linha_por_vez():
    assert lote_seguro(100_000, 0) == 1


def test_o_no_deriva_o_lote_do_numero_de_colunas(monkeypatch):
    """Integração: o valor que chega ao `to_sql` tem de caber no protocolo."""
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


# ── Atomicidade do "limpar e gravar" ────────────────────────────────────────
#
# O TRUNCATE abria a SUA transação e commitava sozinho; a gravação vinha depois,
# em outra. Uma falha no meio — tipo incompatível, queda de rede — deixava a
# tabela VAZIA: o dado velho já tinha ido e o novo nunca chegou. Numa opção
# chamada "limpar e gravar", perder as duas pontas é o pior desfecho.
#
# O teste usa sqlite, que não tem TRUNCATE: só o comando é trocado por DELETE.
# A estrutura de transação exercitada é a do nó, sem simulação.

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
    """`TRUNCATE` não existe no sqlite — mesma semântica via DELETE."""
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

    # Antes: 0 — o TRUNCATE já tinha commitado sozinho.
    assert _conta(banco) == 3


def test_limpar_e_gravar_com_sucesso_substitui_o_conteudo(banco, truncate_sqlite):
    no = SaveToPostgres(node_id="n1", parameters={})
    no._save_to_postgres(pd.DataFrame({"a": [7]}), "destino", None, "truncate", False, 0, banco)

    assert _conta(banco) == 1
    with banco.connect() as c:
        assert c.exec_driver_sql("SELECT a FROM destino").scalar() == 7


# ── Estrutura: a conexão é compartilhada ────────────────────────────────────

@pytest.mark.parametrize("cls,metodo", [
    (SaveToPostgres, "_save_to_postgres"),
    (SaveToPostGIS, "_save_to_postgis"),
])
def test_o_no_grava_dentro_de_uma_transacao(cls, metodo):
    """Guarda direta da causa: passar a ENGINE para o `to_sql`/`to_postgis` abre
    uma conexão nova, fora da transação do TRUNCATE."""
    import inspect
    fonte = inspect.getsource(getattr(cls, metodo))
    assert "with engine.begin() as conn:" in fonte
    assert "con=conn" in fonte
    assert "con=engine" not in fonte


# ── CRS ausente ─────────────────────────────────────────────────────────────

def test_camada_sem_crs_avisa_no_painel_da_run(caplog):
    """O geopandas grava SRID 0 e avisa por `warnings.warn`, que não aparece
    para quem disparou o fluxo. A camada fica no banco sem sistema de
    coordenadas e o problema só aparece quando ela não se alinha com nada."""
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

    # O aviso sai ANTES de qualquer contato com o banco — é essa ordem que
    # importa, e é ela que o teste fixa. `_get_engine` e a gravação viram no-op
    # (o ambiente de teste não tem psycopg2, e não precisa ter).
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


# ── Mesma garantia no PostGIS ───────────────────────────────────────────────
#
# O geopandas reaproveita a transação quando recebe uma Connection já aberta
# (`_get_conn`), então a gravação entra na MESMA transação do TRUNCATE.

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
    """Sem lote, o geopandas serializa a camada INTEIRA num CSV em memória
    antes de enviar a primeira linha."""
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
    """GDF vindo de outros nós chega com geometry.name == 'geometry'; a tabela
    PostGIS convenciona 'geom'."""
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
