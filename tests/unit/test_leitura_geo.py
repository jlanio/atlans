"""Regressao da leitura geoespacial segura (auditoria SEG-04/05/14/84).

O GDAL/pyogrio detecta o driver pelo CONTEUDO. Um documento OGR VRT entregue por
um servidor WFS malicioso, ou salvo com extensao geoespacial no Drive, faz o GDAL
ler arquivo local do executor (CSV:/data/certs/key.pem) ou fazer SSRF via
/vsicurl. `ler_geodataframe` recusa VRT e caminhos virtuais antes de qualquer
open do GDAL.
"""
import io
import os
import tempfile
import zipfile

import pytest

gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")

from flow.utils.leitura_geo import FonteGeoInseguraError, ler_geodataframe

_VRT = (
    b'<OGRVRTDataSource><OGRVRTLayer name="x">'
    b"<SrcDataSource>CSV:/etc/hostname</SrcDataSource>"
    b"<SrcLayer>x</SrcLayer></OGRVRTLayer></OGRVRTDataSource>"
)
_VRT_COM_DECL = b'<?xml version="1.0"?>\n' + _VRT


@pytest.mark.parametrize("dados", [_VRT, _VRT_COM_DECL])
def test_recusa_vrt_em_buffer(dados):
    with pytest.raises(FonteGeoInseguraError):
        ler_geodataframe(io.BytesIO(dados))


def test_recusa_vrt_disfarcado_de_geojson():
    p = os.path.join(tempfile.gettempdir(), "atl_vrt_disfarcado.geojson")
    with open(p, "wb") as fh:
        fh.write(_VRT)
    try:
        with pytest.raises(FonteGeoInseguraError):
            ler_geodataframe(p)
    finally:
        os.remove(p)


def test_recusa_vrt_embutido_em_zip():
    p = os.path.join(tempfile.gettempdir(), "atl_vrt.zip")
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("mau.vrt", _VRT.decode())
    try:
        with pytest.raises(FonteGeoInseguraError):
            ler_geodataframe(p)
    finally:
        os.remove(p)


@pytest.mark.parametrize("caminho", [
    "/vsicurl/http://169.254.169.254/latest/meta-data/",
    "CSV:/etc/passwd",
    "PG:host=interno dbname=x",
])
def test_recusa_caminho_virtual_do_gdal(caminho):
    with pytest.raises(FonteGeoInseguraError):
        ler_geodataframe(caminho)


def test_le_geojson_legitimo_por_arquivo_e_por_buffer():
    gdf = gpd.GeoDataFrame({"n": [1]}, geometry=[shapely.Point(0, 0)], crs="EPSG:4326")
    p = os.path.join(tempfile.gettempdir(), "atl_ok.geojson")
    gdf.to_file(p, driver="GeoJSON")
    try:
        assert ler_geodataframe(p).shape[0] == 1
    finally:
        os.remove(p)
    buf = gdf.to_json().encode()
    assert ler_geodataframe(io.BytesIO(buf)).shape[0] == 1
