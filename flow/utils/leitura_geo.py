# flow/utils/leitura_geo.py
# SAFE geospatial reading. GDAL/pyogrio (geopandas 1.x's engine) detects the
# driver by CONTENT, not by extension. An OGR VRT document
# (<OGRVRTDataSource>) delivered as a WFS server's response, or saved with a
# .geojson/.shp/.gpkg extension in the Drive, makes GDAL open the OGR_VRT driver
# and follow the <SrcDataSource> — which may point to a local file on the executor
# (CSV:/data/certs/key.pem) or to /vsicurl/http://169.254.169.254/... (SSRF).
#
# Two defenses, both before any GDAL open:
#   1) GDAL_SKIP disables the VRT drivers when this module is imported before
#      GDAL registers the drivers (best-effort; the executor also sets it early).
#   2) Deterministic content inspection: refuses sources whose content is a VRT,
#      refuses GDAL virtual paths (/vsicurl, CSV:..., PG:...) and, for .zip,
#      refuses when there is an embedded .vrt. Independent of import order.

import io
import os
import zipfile

# 1) Disables the VRT drivers before GDAL registers them (if imported in time).
_skip_atual = {s for s in os.environ.get("GDAL_SKIP", "").split(",") if s}
os.environ["GDAL_SKIP"] = ",".join(sorted(_skip_atual | {"OGR_VRT", "VRT"}))

import geopandas as gpd  # noqa: E402  (import apos configurar GDAL_SKIP)


class FonteGeoInseguraError(ValueError):
    """The geospatial source is a VRT or a virtual path — refused for security."""


# Assinaturas de VRT (vetor e raster). Comparadas em minusculas.
_ASSINATURAS_VRT = (b"<ogrvrtdatasource", b"<vrtdataset")
# Path prefixes that GDAL treats as a virtual file system (network,
# nested files) or as a connection to an external datasource.
_PREFIXOS_VIRTUAIS = ("/vsi",)
_PREFIXOS_CONEXAO = (
    "csv:", "pg:", "mysql:", "oci:", "wfs:", "gtiff:", "gpkg:", "sqlite:",
    "http:", "https:", "ftp:", "postgresql:", "mongodb:", "es:", "carto:",
)


def _tem_assinatura_vrt(cabecalho: bytes) -> bool:
    trecho = cabecalho[:8192].lower()
    return any(a in trecho for a in _ASSINATURAS_VRT)


def _zip_tem_vrt(dados_ou_caminho) -> bool:
    try:
        zf = (zipfile.ZipFile(io.BytesIO(dados_ou_caminho)) if isinstance(dados_ou_caminho, (bytes, bytearray))
              else zipfile.ZipFile(dados_ou_caminho))
        with zf:
            return any(nome.lower().endswith(".vrt") for nome in zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def _validar_bytes(dados: bytes) -> None:
    if _tem_assinatura_vrt(dados):
        raise FonteGeoInseguraError(
            "Conteudo recusado: documento OGR VRT nao e permitido (pode ler "
            "arquivos locais do executor ou fazer requisicoes de rede)."
        )
    if dados[:4] == b"PK\x03\x04" and _zip_tem_vrt(dados):
        raise FonteGeoInseguraError("Arquivo .zip contem um .vrt — recusado por seguranca.")


def _validar_caminho(caminho: str) -> None:
    baixo = caminho.lower()
    if baixo.startswith(_PREFIXOS_VIRTUAIS) or baixo.startswith(_PREFIXOS_CONEXAO):
        raise FonteGeoInseguraError(
            f"Caminho '{caminho[:60]}' nao e um arquivo local simples e foi recusado."
        )
    try:
        with open(caminho, "rb") as fh:
            cabecalho = fh.read(8192)
    except OSError:
        return  # deixa o gpd.read_file dar o erro de I/O apropriado
    if _tem_assinatura_vrt(cabecalho):
        raise FonteGeoInseguraError(
            "Conteudo recusado: documento OGR VRT nao e permitido."
        )
    if cabecalho[:4] == b"PK\x03\x04" and _zip_tem_vrt(caminho):
        raise FonteGeoInseguraError("Arquivo .zip contem um .vrt — recusado por seguranca.")


def ler_geodataframe(fonte, **kwargs):
    """Hardened `geopandas.read_file`: refuses VRT and virtual paths.

    `fonte` may be a path (str/PathLike), bytes or a binary buffer
    (io.BytesIO), as `gpd.read_file` accepts.
    """
    if isinstance(fonte, (bytes, bytearray)):
        _validar_bytes(bytes(fonte))
    elif isinstance(fonte, io.BytesIO):
        dados = fonte.getvalue()
        _validar_bytes(dados)
    elif hasattr(fonte, "read"):
        # Buffer generico: le, valida e reembrulha para o read_file.
        dados = fonte.read()
        _validar_bytes(dados)
        fonte = io.BytesIO(dados)
    else:
        _validar_caminho(os.fspath(fonte))
    return gpd.read_file(fonte, **kwargs)
