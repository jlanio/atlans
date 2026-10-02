"""Regressao do sandbox Jinja endurecido (auditoria SEG-03).

O SandboxedEnvironment do Jinja bloqueia atributos com sublinhado e chamaveis
marcados como unsafe, mas deixava passar QUALQUER metodo publico dos objetos do
contexto. Os outputs dos nos entram no contexto como GeoDataFrame/DataFrame/
ndarray vivos, cujos metodos `to_file`/`to_csv(path)`/`to_parquet`/`tofile`
gravam arquivo no processo do executor (que guarda o cert mTLS e credenciais).
Cada teste falha sem o endurecimento de flow/utils/jinja_seguro.py.
"""
import os
import tempfile

import pytest
from jinja2 import StrictUndefined
from jinja2.exceptions import SecurityError

pd = pytest.importorskip("pandas")
gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")

from flow.utils.jinja_seguro import criar_ambiente_sandbox


def _ambiente():
    return criar_ambiente_sandbox(undefined=StrictUndefined)


def _contexto():
    gdf = gpd.GeoDataFrame(
        {"v": [1, 2]}, geometry=[shapely.Point(0, 0), shapely.Point(1, 1)], crs="EPSG:4326"
    )
    df = pd.DataFrame({"a": [1, 2]})
    return {"Camada": type("O", (), {"output": gdf})(),
            "Dados": type("O", (), {"output": df})()}


@pytest.mark.parametrize("expr", [
    "{{ Camada.output.to_file(alvo, driver='GPKG') }}",
    "{{ Dados.output.to_csv(alvo) }}",
    "{{ Dados.output.to_pickle(alvo) }}",
    "{{ Dados.output.to_parquet(alvo) }}",
    "{{ Dados.output.to_json(path_or_buf=alvo) }}",
])
def test_bloqueia_escrita_de_arquivo_e_nao_cria_o_arquivo(expr):
    env = _ambiente()
    ctx = _contexto()
    alvo = os.path.join(tempfile.gettempdir(), "atl_teste_jinja_io.out")
    if os.path.exists(alvo):
        os.remove(alvo)
    ctx["alvo"] = alvo
    with pytest.raises(SecurityError):
        env.from_string(expr).render(**ctx)
    assert not os.path.exists(alvo), "o sandbox deixou o arquivo ser gravado"


@pytest.mark.parametrize("expr,esperado_contains", [
    ("{{ Dados.output.to_csv() }}", "a"),          # sem destino → string
    ("{{ Camada.output.shape[0] }}", "2"),
    ("{{ Dados.output['a'].sum() }}", "3"),
])
def test_permite_uso_legitimo(expr, esperado_contains):
    env = _ambiente()
    saida = env.from_string(expr).render(**_contexto())
    assert esperado_contains in saida


def test_bloqueia_acesso_a_handle_de_modulo():
    env = _ambiente()
    with pytest.raises(SecurityError):
        env.from_string("{{ Dados.output.to_csv.__globals__ }}").render(**_contexto())
