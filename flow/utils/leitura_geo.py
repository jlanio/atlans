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

import functools
import io
import logging
import os
import zipfile

# 1) Disables the VRT drivers before GDAL registers them (if imported in time).
_current_skip = {s for s in os.environ.get("GDAL_SKIP", "").split(",") if s}
os.environ["GDAL_SKIP"] = ",".join(sorted(_current_skip | {"OGR_VRT", "VRT"}))

import geopandas as gpd  # noqa: E402  (import apos configurar GDAL_SKIP)

logger = logging.getLogger(__name__)


class UnsafeGeoSourceError(ValueError):
    """The geospatial source is a VRT or a virtual path — refused for security."""


# Assinaturas de VRT (vetor e raster). Comparadas em minusculas.
_VRT_SIGNATURES = (b"<ogrvrtdatasource", b"<vrtdataset")
# Path prefixes that GDAL treats as a virtual file system (network,
# nested files) or as a connection to an external datasource.
_VIRTUAL_PREFIXES = ("/vsi",)
_CONNECTION_PREFIXES = (
    "csv:", "pg:", "mysql:", "oci:", "wfs:", "gtiff:", "gpkg:", "sqlite:",
    "http:", "https:", "ftp:", "postgresql:", "mongodb:", "es:", "carto:",
)


def _has_vrt_signature(cabecalho: bytes) -> bool:
    trecho = cabecalho[:8192].lower()
    return any(a in trecho for a in _VRT_SIGNATURES)


def _zip_has_vrt(data_or_path) -> bool:
    try:
        zf = (zipfile.ZipFile(io.BytesIO(data_or_path)) if isinstance(data_or_path, (bytes, bytearray))
              else zipfile.ZipFile(data_or_path))
        with zf:
            return any(nome.lower().endswith(".vrt") for nome in zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


@functools.lru_cache(maxsize=64)
def _zip_tem_vrt(caminho: str, _tamanho: int, _modificado_ns: int, _inode: int) -> bool:
    """`_zip_has_vrt` of a file on disk, remembered while the file is the same
    (size, modification time, inode): DataInput lists a ZIP's layers and then
    reads it, and each call parsed the whole central directory again."""
    return _zip_has_vrt(caminho)


def _zip_tem_vrt_no_disco(caminho: str) -> bool:
    try:
        estado = os.stat(caminho)
    except OSError:
        return _zip_has_vrt(caminho)
    return _zip_tem_vrt(
        os.path.realpath(caminho), estado.st_size, estado.st_mtime_ns, estado.st_ino,
    )


def _validate_bytes(dados: bytes) -> None:
    if _has_vrt_signature(dados):
        raise UnsafeGeoSourceError(
            "Conteudo recusado: documento OGR VRT nao e permitido (pode ler "
            "arquivos locais do executor ou fazer requisicoes de rede)."
        )
    if dados[:4] == b"PK\x03\x04" and _zip_has_vrt(dados):
        raise UnsafeGeoSourceError("Arquivo .zip contem um .vrt — recusado por seguranca.")


def _validate_path(caminho: str) -> None:
    baixo = caminho.lower()
    if baixo.startswith(_VIRTUAL_PREFIXES) or baixo.startswith(_CONNECTION_PREFIXES):
        raise UnsafeGeoSourceError(
            f"Caminho '{caminho[:60]}' nao e um arquivo local simples e foi recusado."
        )
    try:
        with open(caminho, "rb") as fh:
            cabecalho = fh.read(8192)
    except OSError:
        return  # deixa o gpd.read_file dar o erro de I/O apropriado
    if _has_vrt_signature(cabecalho):
        raise UnsafeGeoSourceError(
            "Conteudo recusado: documento OGR VRT nao e permitido."
        )
    if cabecalho[:4] == b"PK\x03\x04" and _zip_tem_vrt_no_disco(caminho):
        raise UnsafeGeoSourceError("Arquivo .zip contem um .vrt — recusado por seguranca.")


def read_geodataframe(fonte, **kwargs):
    """Hardened `geopandas.read_file`: refuses VRT and virtual paths.

    `fonte` may be a path (str/PathLike), bytes or a binary buffer
    (io.BytesIO), as `gpd.read_file` accepts.

    In a shapefile, text that is not valid UTF-8 where the file says it is
    does not stop the read: see `_reler_recuperando_texto`.
    """
    dados = None
    if isinstance(fonte, (bytes, bytearray)):
        dados = bytes(fonte)
        _validate_bytes(dados)
    elif isinstance(fonte, io.BytesIO):
        dados = fonte.getvalue()
        _validate_bytes(dados)
    elif hasattr(fonte, "read"):
        # Buffer generic: le, valida e reembrulha para o read_file.
        dados = fonte.read()
        _validate_bytes(dados)
        fonte = io.BytesIO(dados)
    else:
        _validate_path(os.fspath(fonte))
    try:
        return gpd.read_file(fonte, **kwargs)
    except UnicodeDecodeError as erro:
        # The first read consumed the buffer: the next ones get it anew.
        def de_novo():
            return io.BytesIO(dados) if dados is not None else fonte
        # Only a shapefile: its DBF is where the text gets cut (fixed-width
        # fields) and where a .cpg can lie about the encoding. Any other
        # format goes on failing as before — DataInput, for one, then reads a
        # CSV inside a ZIP with its own reader, which knows decimal commas.
        if "encoding" in kwargs or not _e_shapefile(de_novo(), kwargs.get("layer")):
            raise
        return _reler_recuperando_texto(de_novo(), kwargs, erro)


def _e_shapefile(fonte, camada) -> bool:
    try:
        import pyogrio
        return pyogrio.read_info(fonte, layer=camada)["driver"] == "ESRI Shapefile"
    except Exception:
        return False


def _texto_utf8(valor: str) -> tuple[str, bool]:
    """A value read as latin-1 (byte for byte) back to its text.

    Returns the text and whether it needed repair. In order:
    - valid UTF-8: as it is;
    - UTF-8 with the last character cut in half: a shapefile's DBF stores
      text in fields of up to 254 BYTES, and the program that wrote it cut a
      2-byte "ã"/"ç" at the border (ICMBio's autos_infracao_icmbio_shp.zip:
      0xc3 at position 253). The half character goes, the rest stays;
    - UTF-8 with a broken byte inside: only that byte becomes U+FFFD;
    - not UTF-8 at all (a .cpg that says UTF-8 over a Windows file): cp1252,
      the encoding of Brazilian files from that world.
    """
    bruto = valor.encode("latin-1")
    try:
        return bruto.decode("utf-8"), False
    except UnicodeDecodeError as erro:
        if erro.reason == "unexpected end of data":
            return bruto[:erro.start].decode("utf-8", errors="replace"), True
    texto = bruto.decode("utf-8", errors="replace")
    if any(ord(c) > 0x7F and c != "\ufffd" for c in texto):
        return texto, True
    return bruto.decode("cp1252", errors="replace"), True


def _reler_recuperando_texto(fonte, kwargs: dict, erro: UnicodeDecodeError):
    """Reads again with the text as raw bytes, and repairs each value.

    pyogrio decodes the whole layer in the encoding the file declares (the
    .cpg of a shapefile) and gives up on the first invalid value: one cut
    character in one record made the file unreadable. Asked for latin-1,
    pyogrio reads the bytes as they are (GDAL recodes nothing), one character
    per byte — nothing is lost, and `_texto_utf8` turns each value back into
    its text. The field names go through the same.
    """
    try:
        # "ISO-8859-1", not "latin-1": GDAL does not know the Python alias,
        # recodes nothing with it, and the same error comes back.
        gdf = gpd.read_file(fonte, encoding="ISO-8859-1", **kwargs)
    except Exception:
        raise erro from None
    consertados = 0

    def consertar(valor):
        nonlocal consertados
        if not isinstance(valor, str):
            return valor
        texto, consertado = _texto_utf8(valor)
        consertados += consertado
        return texto

    geometria = getattr(gdf, "_geometry_column_name", None)
    for coluna in gdf.columns:
        if coluna != geometria and (gdf[coluna].dtype == object or str(gdf[coluna].dtype) in ("string", "str")):
            gdf[coluna] = gdf[coluna].map(consertar)
    gdf = gdf.rename(columns=lambda nome: consertar(nome) if nome != geometria else nome)
    logger.warning(
        "Leitura do shapefile: ele diz estar em UTF-8, mas %d texto(s) não estavam "
        "(%s). Recuperados: um caractere cortado no fim do campo (o limite de 254 bytes "
        "do shapefile) sai; um texto em outra codificação é lido como cp1252.",
        consertados, erro.reason,
    )
    return gdf


def list_layers(fonte) -> list[str]:
    """Layer names of a file, with the same refusals as `read_geodataframe`.

    DataInput uses it to say, in the run log, that a ZIP has more than one layer
    and which one was read — pyogrio only warns about it, and the warning never
    reached the person who built the workflow.
    """
    _validate_path(os.fspath(fonte))
    import pyogrio

    return [str(linha[0]) for linha in pyogrio.list_layers(fonte)]
