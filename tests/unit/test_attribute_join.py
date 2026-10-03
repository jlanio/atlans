# tests/unit/test_attribute_join.py
"""
Join by attribute — matches two inputs by a key column.

The catalog didn't have this: `Merge` merges workflow branches, `Aggregate`
stacks rows, `SpatialJoin` matches by geometry. Bringing the population from a
table onto the census tract grid by tract code was only possible by writing a
script.

The tests focus on what FAILS SILENTLY in a merge, which is where this node earns
the right to exist instead of the user calling `pd.merge` in a
PythonScript:

  MULTIPLIES    a repeated key in B duplicates A's features, and the run ends
                green with more features than went in.

  NO MATCH      a text key on one side and a number on the other matches
                NOTHING, and pandas doesn't complain — the whole column comes
                back null.

  RENAMES       a column with the same name on both sides becomes `_x`/`_y`, and
                the next node looks for a column that no longer exists.

  LOSES TYPE    `B.merge(A)` returns a plain DataFrame: geometry and CRS vanish
                and the following spatial nodes fail.
"""
import asyncio

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from flow.registry import auto_discover_nodes, NODE_REGISTRY

auto_discover_nodes()


def _no(**params):
    padrao = {"keyA": "cod", "keyB": "", "columns": "populacao",
              "how": "left", "seDuplicado": "falhar"}
    padrao.update(params)
    no = NODE_REGISTRY["AttributeJoin"]("n1", padrao)
    no._task_id, no._workspace_id = "t", "w"
    no.logs = []
    no.log = no.logs.append
    return no


@pytest.fixture
def A():
    return gpd.GeoDataFrame(
        {"cod": ["001", "002", "003"], "nome": ["Centro", "Norte", "Sul"],
         "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)]},
        crs="EPSG:4326",
    )


@pytest.fixture
def B():
    return pd.DataFrame({"cod": ["001", "002", "999"],
                         "populacao": [1200, 800, 50],
                         "renda": [3100, 2400, 900]})


def _rodar(no, A, B):
    return asyncio.run(no.execute({"layerA": A, "layerB": B}))["output"]


# ── O caminho feliz ──────────────────────────────────────────────────────────

def test_traz_so_a_coluna_pedida(A, B):
    """Slicing B BEFORE the merge is what keeps unrequested columns from tagging
    along — and names equal to A's from becoming `_x`/`_y`."""
    r = _rodar(_no(), A, B)
    assert "populacao" in r.columns
    assert "renda" not in r.columns


def test_preserva_geometria_e_crs(A, B):
    """`A.merge(b)`, not `b.merge(A)`: called from the GeoDataFrame, the result
    stays a GeoDataFrame. The other way around it would become a plain DataFrame
    and the following spatial nodes would fail with 'sem geometria' (no geometry)."""
    r = _rodar(_no(), A, B)
    assert isinstance(r, gpd.GeoDataFrame)
    assert r.crs == A.crs
    assert list(r.geometry.geom_type) == ["Polygon"] * 3


def test_vazio_traz_todas_as_colunas_menos_a_chave(A, B):
    r = _rodar(_no(columns=""), A, B)
    assert {"populacao", "renda"} <= set(r.columns)
    # The key is not duplicated.
    assert list(r.columns).count("cod") == 1


def test_chave_com_nome_diferente_nos_dois_lados(A):
    b = pd.DataFrame({"setor": ["001", "002"], "populacao": [10, 20]})
    r = _rodar(_no(keyB="setor"), A, b)
    assert r.loc[r["cod"] == "001", "populacao"].iloc[0] == 10
    # B's key is not left over as an extra column.
    assert "setor" not in r.columns


# ── Unmatched feature ────────────────────────────────────────────────────────

def test_left_mantem_feicao_sem_correspondencia(A, B):
    r = _rodar(_no(how="left"), A, B)
    assert len(r) == 3
    assert pd.isna(r.loc[r["cod"] == "003", "populacao"].iloc[0])


def test_inner_descarta_feicao_sem_correspondencia(A, B):
    r = _rodar(_no(how="inner"), A, B)
    assert len(r) == 2
    assert "003" not in set(r["cod"])


def test_log_diz_quantas_ficaram_sem_par(A, B):
    no = _no(how="left")
    _rodar(no, A, B)
    assert any("1 sem correspondência" in linha for linha in no.logs)


# ── Duplicata: o defeito que multiplica em silencio ──────────────────────────

def _b_duplicado():
    return pd.DataFrame({"cod": ["001", "001", "002"], "populacao": [1, 2, 3]})


def test_duplicata_interrompe_por_padrao(A):
    """Without this, 3 features go in and 4 come out — and nothing on the screen shows it."""
    with pytest.raises(ValueError) as e:
        _rodar(_no(), A, _b_duplicado())
    msg = str(e.value)
    assert "'cod' se repete" in msg
    assert "001" in msg, "a mensagem precisa dizer QUAL chave"
    assert "multiplicaria" in msg


def test_duplicata_com_primeira_passa_e_avisa(A):
    no = _no(seDuplicado="primeira")
    r = _rodar(no, A, _b_duplicado())
    assert len(r) == 3, "nao pode multiplicar"
    assert r.loc[r["cod"] == "001", "populacao"].iloc[0] == 1
    assert any("descartada" in linha for linha in no.logs), (
        "descartar linha de B em silencio esconde perda de dado"
    )


def test_duplicata_com_todas_multiplica_de_proposito(A):
    """Relacao 1:N intencional — um setor com varias ocorrencias."""
    r = _rodar(_no(seDuplicado="todas"), A, _b_duplicado())
    assert len(r) == 4


# ── The errors pandas wouldn't raise ─────────────────────────────────────────

def test_tipos_diferentes_interrompem(A):
    """Text on one side and number on the other matches NOTHING and pandas doesn't
    warn: the column comes back entirely null and looks like 'no record matched'."""
    b = pd.DataFrame({"cod": [1, 2, 3], "populacao": [10, 20, 30]})
    with pytest.raises(ValueError) as e:
        _rodar(_no(), A, b)
    msg = str(e.value)
    assert "texto" in msg and "número" in msg


def test_coluna_que_ja_existe_em_A_interrompe(A):
    """Without this pandas produces `nome_x`/`nome_y` and the next node looks for a
    column that no longer exists."""
    b = pd.DataFrame({"cod": ["001"], "nome": ["outro"]})
    with pytest.raises(ValueError) as e:
        _rodar(_no(columns="nome"), A, b)
    assert "nome" in str(e.value)


@pytest.mark.parametrize("params,trecho", [
    ({"keyA": "inexistente"}, "não existe em A"),
    ({"keyB": "inexistente"}, "não existe em B"),
    ({"columns": "fantasma"}, "não encontradas em B"),
    ({"keyA": ""}, "Informe a coluna-chave"),
])
def test_mensagens_dizem_o_que_esta_disponivel(A, B, params, trecho):
    with pytest.raises(ValueError) as e:
        _rodar(_no(**params), A, B)
    assert trecho in str(e.value)


# ── Entradas ─────────────────────────────────────────────────────────────────

def test_B_pode_ser_tabela_sem_geometria(A, B):
    """The NORMAL case: a population spreadsheet, the result of an SQL query.
    The base class's `get_input_gdf` would require a GeoDataFrame and refuse."""
    assert not isinstance(B, gpd.GeoDataFrame)
    r = _rodar(_no(), A, B)
    assert len(r) == 3


def test_entrada_nao_conectada_diz_o_que_chegou(A):
    no = _no()
    with pytest.raises(ValueError) as e:
        asyncio.run(no.execute({"layerA": A}))
    assert "layerB" in str(e.value)


def test_declara_duas_portas_de_entrada():
    """It is what makes the canvas draw two connection points and the editor fill
    in the edge's `to_key`. A node without declared ports receives both edges on
    the SAME key and loses one of them."""
    d = NODE_REGISTRY["AttributeJoin"].description()
    assert [p["name"] for p in d["inputs"]] == ["layerA", "layerB"]


# ── Defects found in the week's review ───────────────────────────────────────

def test_sem_par_nao_conta_nulo_legitimo_de_B(A):
    """REGRESSION: "no match" was inferred from the brought-in column being
    null — which counts as unmatched every row where B has a genuine NULL. The
    log sent people looking for a key problem that doesn't exist.

    Here all three keys match; two `populacao` values are null in B.
    """
    B = pd.DataFrame({"cod": ["001", "002", "003"], "populacao": [None, None, 50]})
    no = _no(how="left", columns="populacao")
    resultado = _rodar(no, A, B)

    assert len(resultado) == 3
    assert any("0 sem correspondência" in linha for linha in no.logs), no.logs


def test_sem_par_continua_contando_quem_nao_casou(A, B):
    """The correct count must not always become zero: key '003' doesn't exist in B,
    and that feature of A really is left unmatched."""
    no = _no(how="left")
    _rodar(no, A, B)
    assert any("1 sem correspondência" in linha for linha in no.logs), no.logs


def test_pedir_a_propria_chave_de_B_em_columns(A):
    """REGRESSION: `columns` with B's key name duplicated the column in the
    slice, `b[key_b]` stopped being a Series, and the duplicate check broke
    with "'DataFrame' object has no attribute 'unique'" — an internal error,
    unrelated to what the person asked for.
    """
    B = pd.DataFrame({"codigo": ["001", "002", "003"], "populacao": [1, 2, 3]})
    resultado = _rodar(_no(keyB="codigo", columns="codigo,populacao"), A, B)

    assert "populacao" in resultado.columns
    # B's key doesn't come back as a column: it is already in A, under A's name.
    assert "codigo" not in resultado.columns
    assert list(resultado["populacao"]) == [1, 2, 3]


def test_a_marca_interna_do_join_nao_vaza_para_a_saida(A, B):
    """The merge's `indicator` is an implementation detail: an extra column in the
    output would end up in everything downstream — including a saved file."""
    resultado = _rodar(_no(), A, B)
    assert not [c for c in resultado.columns if c.startswith("__")]


def test_continua_geodataframe_depois_da_marca(A, B):
    """The marker is removed AFTER the repackaging; the drop must not demote the
    result to a plain DataFrame."""
    resultado = _rodar(_no(), A, B)
    assert isinstance(resultado, gpd.GeoDataFrame)
    assert resultado.crs == A.crs


# ── The columns field became a list of chips ─────────────────────────────────

@pytest.mark.parametrize("guardado,esperado", [
    ('["populacao","renda"]', ["populacao", "renda"]),   # formato novo (JSON)
    (["populacao", "renda"], ["populacao", "renda"]),    # a real list
    ("populacao, renda", ["populacao", "renda"]),        # OLD format, already saved
    ("populacao", ["populacao"]),
    ("", []),
    (None, []),
    ("[]", []),
    ("  populacao ,, renda  ", ["populacao", "renda"]),
])
def test_colunas_pedidas_aceita_os_dois_formatos(guardado, esperado):
    """The field now stores JSON, but already-saved definitions have comma-separated
    text. Reading both is what avoids migrating the definition of every workflow
    that uses the node — and pasting "a, b, c" is still the quick path in the new
    field."""
    from flow.nodes.action.attribute_join import _colunas_pedidas
    assert _colunas_pedidas(guardado) == esperado


def test_json_quebrado_nao_engole_o_valor():
    """Falling back to the text format is better than returning empty: empty means
    'bring all columns', which is the opposite of what the person asked for."""
    from flow.nodes.action.attribute_join import _colunas_pedidas
    assert _colunas_pedidas('["populacao", renda') == ['["populacao"', 'renda']


def test_o_no_funciona_com_a_lista_em_json(A, B):
    """End to end: the value the screen stores has to reach the merge."""
    resultado = _rodar(_no(columns='["populacao"]'), A, B)
    assert "populacao" in resultado.columns
    assert "renda" not in resultado.columns


def test_o_no_continua_funcionando_com_o_formato_antigo(A, B):
    """A workflow saved before the field change must not change behavior."""
    resultado = _rodar(_no(columns="populacao"), A, B)
    assert "populacao" in resultado.columns
    assert "renda" not in resultado.columns


def test_campo_declara_o_tipo_de_fichas():
    from flow.registry import auto_discover_nodes, NODE_REGISTRY
    auto_discover_nodes()

    props = NODE_REGISTRY["AttributeJoin"].description()["properties"]
    campo = next(p for p in props if p["name"] == "columns")
    assert campo["type"] == "chips"
    assert campo["default"] == []
