# desktop/scripts/smoke.py
#
# Smoke test do bundle Python empacotado no app desktop.
#
# Roda DENTRO do runtime embarcado, com cwd=resources e PYTHONPATH=resources —
# exatamente o ambiente do spawn em producao. Se algo aqui falha, o instalador
# gerado seria um app que abre e nao executa workflow nenhum.
#
# O passo mais importante e o 3: e ele que exercita o sys.path hack de
# executor/job_executor.py e o registry dinamico de flow/, que carrega ~60
# modulos de nos via importlib. E o unico jeito de descobrir, em tempo de build,
# que a poda comeu algo de que um no precisava.
#
# Invocado por scripts/smoke-python.mjs. Nao depende de pytest de proposito:
# o runtime empacotado nao tem pytest, e nao vai ter.
import json
import os
import sys
import tempfile
import traceback

MIN_NOS = 60          # eram 64 na Fase 0; margem para remocao pontual de no
MIN_CAMPOS_SNAPSHOT = 50  # eram 55; o contrato do IPC vive aqui

_passos = []


def passo(nome):
    def deco(fn):
        _passos.append((nome, fn))
        return fn
    return deco


@passo("import executor.config (dispara load_dotenv)")
def _():
    from executor import config
    return f"server={config.SERVER_URL}"


@passo("import executor.main (httpx, websockets, cryptography, rich)")
def _():
    import executor.main  # noqa: F401
    return "ok"


@passo("executor.job_executor -> flow.executor (sys.path hack)")
def _():
    import executor.job_executor  # noqa: F401  — insere o pai no sys.path
    from flow.executor import WorkflowExecutor
    return WorkflowExecutor.__module__


@passo("registry dinamico de nos (importlib sobre flow/nodes/)")
def _():
    from flow.registry import NODE_REGISTRY, auto_discover_nodes
    auto_discover_nodes()
    n = len(NODE_REGISTRY)
    assert n >= MIN_NOS, f"apenas {n} nos registrados (minimo {MIN_NOS})"
    return f"{n} nos"


@passo("import do stack GIS e de dados")
def _():
    import geopandas, pyogrio, pyarrow, pyproj, shapely  # noqa: F401
    import asyncpg, boto3, psutil, psycopg2, redis, sqlalchemy  # noqa: F401
    return (f"geopandas={geopandas.__version__} pyogrio={pyogrio.__version__} "
            f"pyarrow={pyarrow.__version__} shapely={shapely.__version__}")


@passo("PROJ: to_crs(3857) — prova que proj.db sobreviveu a poda")
def _():
    import geopandas as gpd
    s = gpd.GeoSeries.from_wkt(["POINT (-38.5 -3.7)"], crs=4326).to_crs(3857)
    x = s.geometry.x.iloc[0]
    assert -4.3e6 < x < -4.2e6, f"reprojecao devolveu x={x}, fora do esperado"
    return f"x={x:.1f}"


@passo("GDAL/pyogrio: GeoJSON write+read")
def _():
    import geopandas as gpd
    p = os.path.join(tempfile.mkdtemp(), "smoke.geojson")
    _gdf().to_file(p, driver="GeoJSON")
    return f"{len(gpd.read_file(p))} feicao"


@passo("GDAL/pyogrio: Shapefile write+read (sem fiona)")
def _():
    import geopandas as gpd
    p = os.path.join(tempfile.mkdtemp(), "smoke.shp")
    _gdf().to_file(p)
    return f"{len(gpd.read_file(p))} feicao"


@passo("pyarrow: GeoParquet write+read")
def _():
    import geopandas as gpd
    p = os.path.join(tempfile.mkdtemp(), "smoke.parquet")
    _gdf().to_parquet(p)
    return f"{len(gpd.read_parquet(p))} linha"


@passo("matplotlib: contourf em PNG e PDF (carta imagem)")
def _():
    # O no CartaImagem so importa o matplotlib quando roda, entao nenhum passo
    # acima o carregava: as extensoes nativas que ele puxa (contourpy,
    # kiwisolver, as fontes via fonttools) — trocadas a cada versao do CPython —
    # so falhariam na maquina do usuario. contourf exercita o contourpy; o PDF,
    # a embutida de fontes do fonttools.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    x, y = np.meshgrid(np.linspace(-1, 1, 20), np.linspace(-1, 1, 20))
    fig, ax = plt.subplots()
    ax.contourf(x, y, x * x + y * y)
    ax.set_title("smoke")
    pasta = tempfile.mkdtemp()
    tamanhos = []
    for formato in ("png", "pdf"):
        p = os.path.join(pasta, f"smoke.{formato}")
        fig.savefig(p, format=formato)
        tamanhos.append(os.path.getsize(p))
    plt.close(fig)
    assert all(t > 1000 for t in tamanhos), f"arquivos pequenos demais: {tamanhos}"
    return f"matplotlib={matplotlib.__version__} png={tamanhos[0]}B pdf={tamanhos[1]}B"


@passo("boto3: client S3 (botocore/data podado)")
def _():
    import boto3
    c = boto3.client("s3", endpoint_url="http://127.0.0.1:9000",
                     aws_access_key_id="x", aws_secret_access_key="y",
                     region_name="us-east-1")
    return type(c).__name__


@passo("executor._ca_bootstrap importavel (roda antes de tudo no __main__)")
def _():
    from executor._ca_bootstrap import bootstrap_ca  # noqa: F401
    return "ok"


@passo("executor.stats.Snapshot serializavel (contrato do IPC)")
def _():
    import dataclasses
    from executor.stats import Snapshot
    campos = [f.name for f in dataclasses.fields(Snapshot)]
    assert len(campos) >= MIN_CAMPOS_SNAPSHOT, f"Snapshot com {len(campos)} campos"
    json.dumps(campos)
    return f"{len(campos)} campos"


def _gdf():
    import geopandas as gpd
    return gpd.GeoSeries.from_wkt(
        ["POLYGON ((0 0, 1 0, 1 1, 0 0))"], crs=4326
    ).to_frame("geometry")


def main() -> int:
    total = len(_passos)
    for i, (nome, fn) in enumerate(_passos, 1):
        try:
            print(f"  [{i:2}/{total}] OK    {nome}  ->  {fn()}", flush=True)
        except Exception:
            print(f"  [{i:2}/{total}] FALHA {nome}", flush=True)
            traceback.print_exc()
            return 1
    print(f"\n  python={sys.version.split()[0]}  {total}/{total} passos", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
