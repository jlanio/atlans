# tests/unit/test_attribute_join.py
"""
Join por atributo — casa duas entradas por uma coluna-chave.

O catalogo nao tinha isso: `Merge` mescla branches do fluxo, `Aggregate` empilha
linhas, `SpatialJoin` casa por geometria. Trazer a populacao de uma tabela para
a malha de setores pelo codigo do setor so era possivel escrevendo um script.

Os testes se concentram no que FALHA EM SILENCIO num merge, que e onde este no
ganha o direito de existir em vez de o usuario chamar `pd.merge` num
PythonScript:

  MULTIPLICA    chave repetida em B duplica as feicoes de A, e o run termina em
                verde com mais feicoes do que entrou.

  NAO CASA      chave texto de um lado e numero do outro nao casa NADA, e o
                pandas nao reclama — a coluna inteira volta nula.

  RENOMEIA      coluna de mesmo nome nos dois lados vira `_x`/`_y`, e o no
                seguinte procura uma coluna que nao existe mais.

  PERDE O TIPO  `B.merge(A)` devolve DataFrame comum: geometria e CRS somem e os
                nos espaciais seguintes falham.
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
    """Recortar B ANTES do merge e o que impede colunas nao pedidas de entrarem
    de carona — e nomes iguais aos de A de virarem `_x`/`_y`."""
    r = _rodar(_no(), A, B)
    assert "populacao" in r.columns
    assert "renda" not in r.columns


def test_preserva_geometria_e_crs(A, B):
    """`A.merge(b)`, e nao `b.merge(A)`: chamado a partir do GeoDataFrame o
    resultado continua GeoDataFrame. Ao contrario viraria DataFrame comum e os
    nos espaciais seguintes falhariam com 'sem geometria'."""
    r = _rodar(_no(), A, B)
    assert isinstance(r, gpd.GeoDataFrame)
    assert r.crs == A.crs
    assert list(r.geometry.geom_type) == ["Polygon"] * 3


def test_vazio_traz_todas_as_colunas_menos_a_chave(A, B):
    r = _rodar(_no(columns=""), A, B)
    assert {"populacao", "renda"} <= set(r.columns)
    # A chave nao e duplicada.
    assert list(r.columns).count("cod") == 1


def test_chave_com_nome_diferente_nos_dois_lados(A):
    b = pd.DataFrame({"setor": ["001", "002"], "populacao": [10, 20]})
    r = _rodar(_no(keyB="setor"), A, b)
    assert r.loc[r["cod"] == "001", "populacao"].iloc[0] == 10
    # A chave de B nao sobra como coluna extra.
    assert "setor" not in r.columns


# ── Feicao sem par ───────────────────────────────────────────────────────────

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
    """Sem isto, 3 feicoes entram e 4 saem — e nada na tela indica."""
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


# ── Os erros que o pandas nao daria ──────────────────────────────────────────

def test_tipos_diferentes_interrompem(A):
    """Texto de um lado e numero do outro nao casa NADA e o pandas nao avisa: a
    coluna volta inteira nula e parece 'nenhum registro bateu'."""
    b = pd.DataFrame({"cod": [1, 2, 3], "populacao": [10, 20, 30]})
    with pytest.raises(ValueError) as e:
        _rodar(_no(), A, b)
    msg = str(e.value)
    assert "texto" in msg and "número" in msg


def test_coluna_que_ja_existe_em_A_interrompe(A):
    """Sem isto o pandas produz `nome_x`/`nome_y` e o proximo no procura uma
    coluna que deixou de existir."""
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
    """O caso NORMAL: uma planilha de populacao, o retorno de uma consulta SQL.
    `get_input_gdf` da classe base exigiria GeoDataFrame e recusaria."""
    assert not isinstance(B, gpd.GeoDataFrame)
    r = _rodar(_no(), A, B)
    assert len(r) == 3


def test_entrada_nao_conectada_diz_o_que_chegou(A):
    no = _no()
    with pytest.raises(ValueError) as e:
        asyncio.run(no.execute({"layerA": A}))
    assert "layerB" in str(e.value)


def test_declara_duas_portas_de_entrada():
    """E o que faz o canvas desenhar dois pontos de conexao e o editor preencher
    o `to_key` da aresta. Um no sem portas declaradas recebe as duas arestas na
    MESMA chave e perde uma delas."""
    d = NODE_REGISTRY["AttributeJoin"].description()
    assert [p["name"] for p in d["inputs"]] == ["layerA", "layerB"]


# ── Defeitos achados na revisao da semana ────────────────────────────────────

def test_sem_par_nao_conta_nulo_legitimo_de_B(A):
    """REGRESSAO: o "sem correspondência" era inferido de a coluna trazida estar
    nula — o que conta como falta de par toda linha em que B tem NULO de
    verdade. O log mandava procurar um problema de chave que não existe.

    Aqui as tres chaves casam; dois valores de `populacao` sao nulos em B.
    """
    B = pd.DataFrame({"cod": ["001", "002", "003"], "populacao": [None, None, 50]})
    no = _no(how="left", columns="populacao")
    resultado = _rodar(no, A, B)

    assert len(resultado) == 3
    assert any("0 sem correspondência" in linha for linha in no.logs), no.logs


def test_sem_par_continua_contando_quem_nao_casou(A, B):
    """A contagem certa nao pode virar sempre zero: em B a chave '003' nao
    existe, e essa feicao de A fica mesmo sem par."""
    no = _no(how="left")
    _rodar(no, A, B)
    assert any("1 sem correspondência" in linha for linha in no.logs), no.logs


def test_pedir_a_propria_chave_de_B_em_columns(A):
    """REGRESSAO: `columns` com o nome da chave de B duplicava a coluna no
    recorte, `b[key_b]` deixava de ser Series, e a checagem de duplicata
    quebrava com "'DataFrame' object has no attribute 'unique'" — um erro
    interno, sem relacao com o que a pessoa pediu.
    """
    B = pd.DataFrame({"codigo": ["001", "002", "003"], "populacao": [1, 2, 3]})
    resultado = _rodar(_no(keyB="codigo", columns="codigo,populacao"), A, B)

    assert "populacao" in resultado.columns
    # A chave de B nao volta como coluna: ja esta em A, com o nome de la.
    assert "codigo" not in resultado.columns
    assert list(resultado["populacao"]) == [1, 2, 3]


def test_a_marca_interna_do_join_nao_vaza_para_a_saida(A, B):
    """O `indicator` do merge e detalhe de implementacao: uma coluna a mais na
    saida iria parar em tudo que vier depois — inclusive num arquivo salvo."""
    resultado = _rodar(_no(), A, B)
    assert not [c for c in resultado.columns if c.startswith("__")]


def test_continua_geodataframe_depois_da_marca(A, B):
    """A marca e removida DEPOIS do reempacotamento; o drop nao pode rebaixar o
    resultado a DataFrame comum."""
    resultado = _rodar(_no(), A, B)
    assert isinstance(resultado, gpd.GeoDataFrame)
    assert resultado.crs == A.crs


# ── O campo de colunas virou lista de fichas ─────────────────────────────────

@pytest.mark.parametrize("guardado,esperado", [
    ('["populacao","renda"]', ["populacao", "renda"]),   # formato novo (JSON)
    (["populacao", "renda"], ["populacao", "renda"]),    # lista de verdade
    ("populacao, renda", ["populacao", "renda"]),        # formato ANTIGO, ja salvo
    ("populacao", ["populacao"]),
    ("", []),
    (None, []),
    ("[]", []),
    ("  populacao ,, renda  ", ["populacao", "renda"]),
])
def test_colunas_pedidas_aceita_os_dois_formatos(guardado, esperado):
    """O campo passou a gravar JSON, mas as definitions ja salvas tem texto com
    virgulas. Ler os dois e o que dispensa migrar a definition de todo workflow
    que use o no — e colar "a, b, c" continua sendo o caminho rapido no campo
    novo."""
    from flow.nodes.action.attribute_join import _colunas_pedidas
    assert _colunas_pedidas(guardado) == esperado


def test_json_quebrado_nao_engole_o_valor():
    """Cair no formato de texto e melhor que devolver vazio: vazio significa
    'traga todas as colunas', que e o oposto do que a pessoa pediu."""
    from flow.nodes.action.attribute_join import _colunas_pedidas
    assert _colunas_pedidas('["populacao", renda') == ['["populacao"', 'renda']


def test_o_no_funciona_com_a_lista_em_json(A, B):
    """Ponta a ponta: o valor que a tela grava tem de chegar ao merge."""
    resultado = _rodar(_no(columns='["populacao"]'), A, B)
    assert "populacao" in resultado.columns
    assert "renda" not in resultado.columns


def test_o_no_continua_funcionando_com_o_formato_antigo(A, B):
    """Workflow salvo antes da mudanca do campo nao pode mudar de comportamento."""
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
