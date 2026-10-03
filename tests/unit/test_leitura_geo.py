"""Regression for safe geospatial reading (audit SEG-04/05/14/84).

GDAL/pyogrio detects the driver by CONTENT. An OGR VRT document delivered by
a malicious WFS server, or saved with a geospatial extension in the Drive, makes GDAL
read a local file of the executor (CSV:/data/certs/key.pem) or perform SSRF via
/vsicurl. `read_geodataframe` rejects VRT and virtual paths before any
GDAL open.
"""
import io
import os
import tempfile
import zipfile

import pytest

gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")

from flow.utils.leitura_geo import UnsafeGeoSourceError, read_geodataframe

_VRT = (
    b'<OGRVRTDataSource><OGRVRTLayer name="x">'
    b"<SrcDataSource>CSV:/etc/hostname</SrcDataSource>"
    b"<SrcLayer>x</SrcLayer></OGRVRTLayer></OGRVRTDataSource>"
)
_VRT_WITH_DECL = b'<?xml version="1.0"?>\n' + _VRT


@pytest.mark.parametrize("dados", [_VRT, _VRT_WITH_DECL])
def test_rejects_vrt_in_buffer(dados):
    with pytest.raises(UnsafeGeoSourceError):
        read_geodataframe(io.BytesIO(dados))


def test_rejects_vrt_disguised_as_geojson():
    p = os.path.join(tempfile.gettempdir(), "atl_vrt_disfarcado.geojson")
    with open(p, "wb") as fh:
        fh.write(_VRT)
    try:
        with pytest.raises(UnsafeGeoSourceError):
            read_geodataframe(p)
    finally:
        os.remove(p)


def test_rejects_vrt_embedded_in_zip():
    p = os.path.join(tempfile.gettempdir(), "atl_vrt.zip")
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("mau.vrt", _VRT.decode())
    try:
        with pytest.raises(UnsafeGeoSourceError):
            read_geodataframe(p)
    finally:
        os.remove(p)


@pytest.mark.parametrize("caminho", [
    "/vsicurl/http://169.254.169.254/latest/meta-data/",
    "CSV:/etc/passwd",
    "PG:host=interno dbname=x",
])
def test_rejects_gdal_virtual_path(caminho):
    with pytest.raises(UnsafeGeoSourceError):
        read_geodataframe(caminho)


def test_reads_legitimate_geojson_from_file_and_buffer():
    gdf = gpd.GeoDataFrame({"n": [1]}, geometry=[shapely.Point(0, 0)], crs="EPSG:4326")
    p = os.path.join(tempfile.gettempdir(), "atl_ok.geojson")
    gdf.to_file(p, driver="GeoJSON")
    try:
        assert read_geodataframe(p).shape[0] == 1
    finally:
        os.remove(p)
    buf = gdf.to_json().encode()
    assert read_geodataframe(io.BytesIO(buf)).shape[0] == 1
