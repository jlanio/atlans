# flow/utils/leitura_geo.py
# Leitura geoespacial SEGURA. O GDAL/pyogrio (engine do geopandas 1.x) detecta o
# driver pelo CONTEUDO, nao pela extensao. Um documento OGR VRT
# (<OGRVRTDataSource>) entregue como resposta de um servidor WFS, ou salvo com
# extensao .geojson/.shp/.gpkg no Drive, faz o GDAL abrir o driver OGR_VRT e
# seguir o <SrcDataSource> — que pode apontar para um arquivo local do executor
# (CSV:/data/certs/key.pem) ou para /vsicurl/http://169.254.169.254/... (SSRF).
#
# Duas defesas, ambas antes de qualquer open do GDAL:
#   1) GDAL_SKIP desabilita os drivers VRT quando este modulo e importado antes
#      do GDAL registrar os drivers (best-effort; o executor tambem seta cedo).
#   2) Inspecao de conteudo determinista: recusa fontes cujo conteudo e um VRT,
#      recusa caminhos virtuais do GDAL (/vsicurl, CSV:..., PG:...) e, em .zip,
#      recusa quando ha um .vrt embutido. Independe da ordem de import.

import io
import os
import zipfile

# 1) Desabilita os drivers VRT antes de o GDAL registrar (se importado a tempo).
_skip_atual = {s for s in os.environ.get("GDAL_SKIP", "").split(",") if s}
os.environ["GDAL_SKIP"] = ",".join(sorted(_skip_atual | {"OGR_VRT", "VRT"}))

import geopandas as gpd  # noqa: E402  (import apos configurar GDAL_SKIP)


class FonteGeoInseguraError(ValueError):
    """A fonte geoespacial e um VRT ou caminho virtual — recusada por seguranca."""


# Assinaturas de VRT (vetor e raster). Comparadas em minusculas.
_ASSINATURAS_VRT = (b"<ogrvrtdatasource", b"<vrtdataset")
# Prefixos de caminho que o GDAL trata como sistema de arquivos virtual (rede,
# arquivos aninhados) ou como conexao a datasource externo.
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
    """`geopandas.read_file` endurecido: recusa VRT e caminhos virtuais.

    `fonte` pode ser um caminho (str/PathLike), bytes ou um buffer binario
    (io.BytesIO), como o `gpd.read_file` aceita.
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
