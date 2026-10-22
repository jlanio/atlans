"""
DataInput — Data Input from the Workspace Drive, from Artifacts or from a URL.

Reads a stored file (Drive or Artifacts context), downloads it from MinIO to
temp and loads the data — or downloads it from a URL (URL context), on the
executor, with the defenses of flow/utils/download_seguro.py. It's the
read-side mirror of DataOutput (output).

Supported formats:
  Geospatial    -> GeoJSON, Shapefile (.zip or .shp), KML/KMZ, GeoPackage (.gpkg)
                -> output: GeoDataFrame (geopandas); a GeoPackage table
                   without geometry comes out as a DataFrame
  Tabular       -> CSV, XLSX, JSON
                -> output: DataFrame (pandas) or list[dict]; with latitude and
                   longitude columns filled in, a table becomes points
  ZIP           -> read as GDAL sees it, or ONE file chosen inside it
                   (flow/utils/leitura_zip.py)
  Others        -> raw bytes or dict with metadata
"""
import asyncio
import os
import posixpath
import re
from typing import Any, Dict
from urllib.parse import unquote, urlparse

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.drive_resolver import resolve_drive_file, resolve_artifact_file

logger = get_logger(__name__)

_GEO_EXTENSIONS = {"geojson", "shp", "zip", "kml", "kmz", "gpkg", "gml", "fgb"}

# Download limit of the URL context when the field is left as is. A year of
# INMET stations or a national municipal grid fits; what does not fit is
# usually the wrong file.
_MAX_DOWNLOAD_MB_PADRAO = 800

# Formats told apart by the content's first bytes — the name on the URL can be
# `download.php?id=123`, and a portal's error page often comes as 200.
_ASSINATURAS = (
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),  # empty ZIP
    (b"SQLite format 3\x00", "gpkg"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "xls"),
    (b"fgb\x03", "fgb"),
    (b"\x1f\x8b", "gz"),
)
_BINARIOS = frozenset({"zip", "xlsx", "kmz", "gpkg", "xls", "fgb"})
_TEXTO = frozenset({"csv", "json", "geojson", "kml", "gml"})
_POR_CONTENT_TYPE = {
    "text/csv": "csv",
    "application/csv": "csv",
    "text/comma-separated-values": "csv",
    "application/geo+json": "geojson",
    "application/vnd.geo+json": "geojson",
    "application/json": "json",
    "application/vnd.google-earth.kml+xml": "kml",
    "application/gml+xml": "gml",
}
_GEOJSON = re.compile(rb'"type"\s*:\s*"(FeatureCollection|Feature)"')


def _ler_kmz(path: str) -> Any:
    """A KMZ holding a single KML (Google Earth's, and Salvar arquivo's) is
    read through that KML: GDAL's LIBKML, opening the .kmz itself, drops the
    attributes (SchemaData) it reads from the same doc.kml outside the zip. A
    KMZ made of several KML (LIBKML's own, with layers/) is read as it is.

    The KML goes to a file, not to memory: as bytes it was held twice (here
    and in GDAL's /vsimem), half again the RAM for a large KMZ.
    """
    import shutil
    import tempfile
    import zipfile
    from flow.utils.leitura_geo import read_geodataframe

    with zipfile.ZipFile(path) as kmz:
        kmls = [nome for nome in kmz.namelist() if nome.lower().endswith(".kml")]
        if len(kmls) != 1:
            return read_geodataframe(path)
        with tempfile.TemporaryDirectory() as pasta:
            doc = os.path.join(pasta, "doc.kml")
            with kmz.open(kmls[0]) as origem, open(doc, "wb") as destino:
                shutil.copyfileobj(origem, destino)
            return read_geodataframe(doc)


def _ler_geo(path: str, ext: str, crs: str) -> Any:
    from flow.utils.leitura_geo import read_geodataframe
    return _aplicar_crs(_ler_kmz(path) if ext == "kmz" else read_geodataframe(path), crs)


def _aplicar_crs(gdf: Any, crs: str) -> Any:
    import geopandas as gpd
    # A GeoPackage can hold a table without geometry (Salvar arquivo
    # writes one): it comes back as a DataFrame, with no CRS to touch.
    if not isinstance(gdf, gpd.GeoDataFrame):
        return gdf
    if crs and gdf.crs is not None and str(gdf.crs) != crs:
        gdf = gdf.to_crs(crs)
    elif gdf.crs is None and crs:
        gdf = gdf.set_crs(crs)
    return gdf


def _arquivo_geojson(path: str) -> bool:
    """A `.json` that is GeoJSON — what APIs and many portals serve."""
    with open(path, "rb") as f:
        return bool(_GEOJSON.search(f.read(8192)))


def _ler_zip(path: str, crs: str, padrao: str, pular_linhas: int, info: dict | None) -> Any:
    """A ZIP read as GDAL sees it, as always, or through ONE member.

    With 'Arquivo dentro do ZIP' empty (and no lines to skip), the read is the
    one existing workflows already depend on; what changes is that a second
    layer stops being silent, and that a ZIP GDAL cannot open (shapefile in a
    subfolder, CSV in cp1252) falls back to its only readable file instead of
    failing. Filled in, the member is extracted and read by the reader of its
    own extension (see flow/utils/leitura_zip.py).
    """
    from flow.utils import leitura_zip
    from flow.utils.leitura_geo import UnsafeGeoSourceError, list_layers, read_geodataframe

    padrao = (padrao or "").strip()
    if not padrao and not pular_linhas:
        # Only GDAL's own reading inside the `try`: a CRS that does not exist,
        # for one, must fail as itself, not as a ZIP that would not open.
        try:
            camadas = list_layers(path)
            leitura = {}
            if len(camadas) > 1:
                logger.warning(
                    "DataInput: o ZIP tem %d camadas (%s); foi lida a primeira, '%s'. "
                    "Para ler outra, preencha 'Arquivo dentro do ZIP' (aceita padrão, como *.shp).",
                    len(camadas), ", ".join(camadas[:12]), camadas[0],
                )
                # The first layer is the one GDAL already read by default; naming
                # it only silences pyogrio's warning, which the sentence above replaces.
                leitura = {"layer": camadas[0]}
            lido = read_geodataframe(path, **leitura)
        except UnsafeGeoSourceError:
            raise
        except Exception as erro_gdal:
            try:
                with leitura_zip.extrair(path, "") as (membro, ext_membro, nome_membro):
                    logger.info(
                        "DataInput: o GDAL não abriu o ZIP como está (%s); lendo o único "
                        "arquivo legível dentro dele, '%s'.", erro_gdal, nome_membro,
                    )
                    return _ler_membro(membro, ext_membro, nome_membro, crs, pular_linhas, info)
            except leitura_zip.ZipInvalidoError as e:
                raise RuntimeError(f"{e} (Lido como está, o ZIP deu erro no GDAL: {erro_gdal})") from erro_gdal
        return _aplicar_crs(lido, crs)

    with leitura_zip.extrair(path, padrao) as (membro, ext_membro, nome_membro):
        logger.info("DataInput: lendo '%s' de dentro do ZIP.", nome_membro)
        return _ler_membro(membro, ext_membro, nome_membro, crs, pular_linhas, info)


def _ler_membro(path: str, ext: str, nome: str, crs: str, pular_linhas: int, info: dict | None) -> Any:
    if info is not None:
        info["zip_member"] = nome
    if ext == "json" and _arquivo_geojson(path):
        ext = "geojson"
    return _ler(path, ext, crs, skip_rows=pular_linhas)


def _ler(path: str, ext: str, crs: str, *, zip_member: str = "", skip_rows: int = 0,
         info: dict | None = None) -> Any:
    """Carrega o arquivo de forma sincrona."""
    if ext == "zip":
        return _ler_zip(path, crs, zip_member, skip_rows, info)

    if ext in _GEO_EXTENSIONS:
        return _ler_geo(path, ext, crs)

    if ext == "csv":
        from flow.utils.leitura_csv import ler_csv
        return ler_csv(path, pular_linhas=skip_rows)

    if ext == "xlsx":
        # Through GDAL, which the executor ships: pandas.read_excel needs
        # openpyxl, which it does not, and failed on every .xlsx. FORCE: the
        # first row is the header, as pandas reads it (GDAL only guesses so
        # when a row below it has a number).
        from flow.utils.leitura_geo import read_geodataframe
        return read_geodataframe(path, read_geometry=False, HEADERS="FORCE")

    if ext == "xls":
        import pandas as pd
        return pd.read_excel(path)

    if ext == "json":
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    with open(path, "rb") as f:
        return f.read()


def _load_file(path: str, ext: str, crs: str, *, zip_member: str = "", skip_rows: int = 0,
               info: dict | None = None) -> Any:
    """Carrega o arquivo de forma sincrona e remove o temporario."""
    try:
        return _ler(path, ext, crs, zip_member=zip_member, skip_rows=skip_rows, info=info)
    finally:
        # Limpa arquivo temporario
        try:
            os.unlink(path)
        except OSError:
            pass


# ── URL context ───────────────────────────────────────────────────────────────

def _extensao_do_nome(nome: str) -> str:
    return posixpath.splitext(nome or "")[1].lower().lstrip(".")


def _nome_da_url(url: str) -> str:
    return posixpath.basename(unquote(urlparse(url).path)) or "download"


def _tamanho_legivel(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _amostra(inicio: bytes) -> str:
    return repr(inicio[:40])[2:-1]


def _detectar_extensao(caminho: str, inicio: bytes, nome: str, content_type: str) -> str:
    """The format of a downloaded file, which DataInput's readers expect as an
    extension. The content decides what it can decide (magic bytes, HTML page);
    the name (`Content-Disposition` or the URL) and then the `Content-Type`
    decide among the text formats; a name that contradicts the content is an
    error, not a guess."""
    cabeca = inicio.lstrip(b"\xef\xbb\xbf").lstrip()
    baixo = cabeca[:512].lower()
    if baixo.startswith(b"<!doctype html") or baixo.startswith(b"<html"):
        raise ValueError(
            "O endereço devolveu uma página HTML, não um arquivo — costuma ser tela de "
            "login, captcha ou página de erro do portal. Abra a URL no navegador para "
            "conferir o endereço direto do arquivo."
        )

    pelo_nome = _extensao_do_nome(nome)
    pelo_conteudo = next((ext for magia, ext in _ASSINATURAS if inicio.startswith(magia)), None)

    if pelo_conteudo == "gz":
        raise ValueError(
            f"'{nome}' veio compactado em gzip (.gz), formato que a Entrada de Dados não "
            "lê. Use a versão .zip ou sem compressão, se o portal oferecer."
        )
    if pelo_conteudo == "zip":
        return _tipo_do_zip(caminho, pelo_nome)
    if pelo_conteudo:
        return pelo_conteudo

    if pelo_nome in _BINARIOS:
        raise ValueError(
            f"O arquivo se chama '{nome}', mas o conteúdo não é {pelo_nome.upper()} "
            f"(começa com: {_amostra(inicio)}). O servidor pode ter devolvido uma "
            "mensagem de erro no lugar do arquivo."
        )
    if b"\x00" in inicio:
        raise ValueError(
            f"Formato de '{nome}' não reconhecido (começa com: {_amostra(inicio)}). "
            "A Entrada de Dados lê CSV, ZIP, GeoJSON, KML/KMZ, GeoPackage, XLSX e JSON."
        )

    if pelo_nome == "csv" and cabeca[:1] in (b"{", b"[", b"<"):
        raise ValueError(
            f"O arquivo se chama '{nome}', mas o conteúdo não parece CSV "
            f"(começa com: {_amostra(cabeca)}). O servidor pode ter devolvido uma "
            "mensagem de erro no lugar do arquivo."
        )

    tipo = (content_type or "").split(";")[0].strip().lower()
    if pelo_nome in _TEXTO:
        ext = pelo_nome
    elif _POR_CONTENT_TYPE.get(tipo) in _TEXTO:
        ext = _POR_CONTENT_TYPE[tipo]
    elif cabeca[:1] in (b"{", b"["):
        ext = "json"
    elif cabeca[:1] == b"<":
        trecho = cabeca[:4096].lower()
        if b"<kml" in trecho:
            ext = "kml"
        elif b"gml" in trecho:
            ext = "gml"
        else:
            raise ValueError(
                f"'{nome}' é um XML que não é KML nem GML (começa com: {_amostra(cabeca)})."
            )
    else:
        ext = "csv"

    if ext == "json" and _GEOJSON.search(inicio):
        ext = "geojson"
    return ext


def _tipo_do_zip(caminho: str, pelo_nome: str) -> str:
    """XLSX and KMZ are ZIPs too: the content says which one this is."""
    import zipfile
    try:
        with zipfile.ZipFile(caminho) as zf:
            nomes = zf.namelist()
    except zipfile.BadZipFile:
        return "zip"
    if "[Content_Types].xml" in nomes and any(n.startswith("xl/") for n in nomes):
        return "xlsx"
    if pelo_nome == "kmz":
        return "kmz"
    from flow.utils.leitura_zip import EXTENSOES_LEGIVEIS
    legiveis = [n for n in nomes if _extensao_do_nome(n) in EXTENSOES_LEGIVEIS]
    if legiveis and all(n.lower().endswith(".kml") for n in legiveis):
        return "kmz"
    return "zip"


# ── Points from latitude/longitude columns ────────────────────────────────────

def _coordenada(serie, coluna: str):
    import pandas as pd
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce")
    # A ',' CSV can still quote a decimal comma ("-23,55"); XLSX keeps text as typed.
    texto = serie.astype("string").str.strip().str.replace(",", ".", regex=False)
    numeros = pd.to_numeric(texto, errors="coerce")
    invalidos = texto.notna() & (texto != "") & numeros.isna()
    if invalidos.any():
        exemplo = serie[invalidos].iloc[0]
        raise ValueError(f"A coluna '{coluna}' tem valor que não é número: {exemplo!r}.")
    return numeros


def _pontos_de_colunas(dados: Any, lat_col: str, lon_col: str, crs: str) -> Any:
    """A table with latitude/longitude columns as a GeoDataFrame of points, in
    `crs` — the same rule as ReadCSVWithCoords, now for any origin."""
    import geopandas as gpd
    import pandas as pd

    if isinstance(dados, gpd.GeoDataFrame):
        logger.info("DataInput: colunas de latitude/longitude ignoradas — o arquivo já tem geometria.")
        return dados
    if not isinstance(dados, pd.DataFrame):
        raise ValueError(
            "As colunas de latitude e longitude valem para tabelas (CSV, XLSX); "
            "este arquivo não foi lido como tabela."
        )
    for coluna, papel in ((lat_col, "latitude"), (lon_col, "longitude")):
        if coluna not in dados.columns:
            raise ValueError(
                f"Coluna de {papel} '{coluna}' não encontrada. "
                f"Colunas disponíveis: {list(dados.columns)}"
            )
    lat = _coordenada(dados[lat_col], lat_col)
    lon = _coordenada(dados[lon_col], lon_col)
    pontos = gpd.points_from_xy(lon, lat)
    vazias = (lat.isna() | lon.isna()).to_numpy()
    if vazias.any():
        # A point at (NaN, NaN) is not "no position": it breaks a spatial join
        # downstream. Without coordinates, the row stays without geometry.
        pontos[vazias] = None
        logger.warning("DataInput: %d linha(s) sem coordenada ficaram sem geometria.", int(vazias.sum()))
    return gpd.GeoDataFrame(dados, geometry=pontos, crs=crs)


@register_node
class DataInput(BaseNode):
    @classmethod
    def description(cls) -> Dict[str, Any]:
        from flow.utils.download_seguro import MAX_REDIRECTS
        return {
            "name": "DataInput",
            "alias": "Entrada de Dados",
            "description": (
                "Carrega um arquivo armazenado no Drive do Workspace, um "
                "Artefato de execucao anterior ou um arquivo baixado de uma URL, "
                "e o expoe como dado de entrada. "
                "Suporta GeoJSON, Shapefile, KML, KMZ, GeoPackage, CSV, XLSX e JSON, "
                "soltos ou dentro de um ZIP."
            ),
            "type": "datasource",
            "dynamic_output": True,
            "properties": [
                {
                    "name": "context",
                    "label": "Origem",
                    "type": "select",
                    "default": "drive",
                    "description": "De onde ler os dados.",
                    "options": [
                        {"value": "drive",     "label": "Drive do Workspace"},
                        {"value": "artifacts", "label": "Artefatos"},
                        {"value": "url",       "label": "URL (download)"},
                    ],
                },
                {
                    "name": "driveFileId", "required": True,
                    "label": "Arquivo do Drive",
                    "type": "drive",
                    "default": "",
                    "description": "Arquivo do Drive do Workspace a ser carregado.",
                    "visibleWhen": {"field": "context", "in": ["drive"]},
                },
                {
                    "name": "artifactId", "required": True,
                    "label": "Artefato",
                    "type": "artifact",
                    "default": "",
                    "description": "Artefato de execucao anterior a ser carregado.",
                    "visibleWhen": {"field": "context", "in": ["artifacts"]},
                },
                {
                    "name": "url", "required": True,
                    "label": "URL",
                    "type": "string",
                    "default": "",
                    "placeholder": "https://dados.exemplo.gov.br/arquivo.zip",
                    "description": (
                        "Endereço do arquivo. Aceita expressões: {{ now('%Y%m%d') }} "
                        "para a data do dia (UTC) ou $Alias.campo de um nó anterior. "
                        f"O download é feito pelo executor e segue até {MAX_REDIRECTS} "
                        "redirecionamentos, conferindo cada destino."
                    ),
                    "visibleWhen": {"field": "context", "in": ["url"]},
                },
                {
                    "name": "credential_id",
                    "label": "Credencial",
                    "type": "credential",
                    "credential_types": ["http_bearer", "http_basic"],
                    "default": "",
                    "description": "Opcional. Autenticação Bearer ou Basic para o download.",
                    "visibleWhen": {"field": "context", "in": ["url"]},
                },
                {
                    # INJECTED by the server from `credential_id`, and declared
                    # because `validate()` rebuilds the parameters from this list:
                    # without the entry, the resolved credential was thrown away and
                    # the download went out anonymous (the same as HttpRequest).
                    # The UI hides it by name (node-config-form).
                    "name": "http_auth",
                    "label": "Autenticacao resolvida",
                    "type": "object",
                    "default": {},
                    "description": "Preenchida automaticamente a partir da credencial escolhida. "
                                   "Nao editavel: o segredo nunca e gravado na definicao do workflow.",
                },
                {
                    "name": "maxDownloadMb",
                    "label": "Tamanho máximo do download (MB)",
                    "type": "integer",
                    "default": _MAX_DOWNLOAD_MB_PADRAO,
                    "description": "O download para assim que passa deste tamanho. 0 tira o limite.",
                    "visibleWhen": {"field": "context", "in": ["url"]},
                },
                {
                    "name": "timeout",
                    "label": "Tempo limite sem resposta (s)",
                    "type": "integer",
                    "default": 60,
                    "description": "Desiste se o servidor passar este tempo sem responder ou sem "
                                   "enviar dados. Não limita a duração total do download.",
                    "visibleWhen": {"field": "context", "in": ["url"]},
                },
                {
                    "name": "zipMember",
                    "label": "Arquivo dentro do ZIP",
                    "type": "string",
                    "default": "",
                    "placeholder": "*.shp",
                    "description": "Só para ZIP: qual arquivo ler, pelo nome ou por um padrão "
                                   "(*.shp, municipios*.shp, *A001*.CSV). Vazio lê o ZIP como "
                                   "sempre; se ele tiver mais de uma camada, o log lista as outras.",
                },
                {
                    "name": "skipRows",
                    "label": "Linhas a ignorar no início (CSV)",
                    "type": "integer",
                    "default": 0,
                    "description": "Linhas acima do cabeçalho, como os metadados da estação "
                                   "nos CSVs do INMET (8).",
                },
                {
                    "name": "latColumn",
                    "label": "Coluna de latitude",
                    "type": "string",
                    "default": "",
                    "description": "Opcional. Com latitude e longitude preenchidas, uma tabela "
                                   "(CSV, XLSX) vira pontos, com as coordenadas no CRS de saída.",
                },
                {
                    "name": "lonColumn",
                    "label": "Coluna de longitude",
                    "type": "string",
                    "default": "",
                    "description": "Opcional. Veja a coluna de latitude.",
                },
                {
                    "name": "crs",
                    "label": "CRS de saída",
                    "type": "string",
                    "default": "EPSG:4326",
                    "description": "CRS de saida para arquivos geoespaciais, e o das "
                                   "coordenadas de latitude/longitude.",
                },
            ],
            "outputs": [
                {"name": "output", "type": "object", "description": "Dados carregados do arquivo", "port": True},
                {"name": "metadata", "type": "object", "description": "Metadados do arquivo", "port": True},
            ],
        }

    async def _baixar(self) -> tuple[str, str, str, dict]:
        """Downloads the URL context's file. Returns (temporary path, extension,
        file name, metadata of the download)."""
        from flow.utils.autenticacao_http import apply_auth, exigir_credencial_resolvida
        from flow.utils.download_seguro import baixar_para_arquivo, nome_sugerido, para_registro

        url: str = self.get_param("url", "").strip()
        if not url:
            raise ValueError("Parametro 'url' e obrigatorio no contexto URL.")
        exigir_credencial_resolvida(self.parameters)
        headers = apply_auth({}, self.get_param("http_auth"))

        max_mb = self.get_param_int("maxDownloadMb", _MAX_DOWNLOAD_MB_PADRAO)
        if max_mb < 0:
            raise ValueError("'Tamanho máximo do download (MB)' não pode ser negativo.")
        timeout = self.get_param_int("timeout", 60)
        if timeout <= 0:
            raise ValueError("'Tempo limite sem resposta (s)' tem de ser maior que zero.")

        logger.info("DataInput: baixando %s", para_registro(url))
        download = await baixar_para_arquivo(
            url, headers=headers, timeout=float(timeout),
            max_bytes=max_mb * 1024 * 1024 if max_mb else None,
        )
        try:
            nome = nome_sugerido(download.headers) or _nome_da_url(download.url_final)
            if download.tamanho == 0:
                raise ValueError(f"O servidor devolveu '{nome}' vazio (0 bytes).")
            content_type = download.headers.get("content-type", "")
            ext = _detectar_extensao(download.caminho, download.inicio, nome, content_type)
            # The readers pick the driver by the extension (pyogrio opens a
            # `.zip` through /vsizip/, GDAL's XLSX driver wants `.xlsx`).
            caminho = f"{download.caminho}.{ext}"
            os.replace(download.caminho, caminho)
        except BaseException:
            try:
                os.unlink(download.caminho)
            except OSError:
                pass
            raise

        logger.info("DataInput: '%s' baixado (%s, %s).", nome, _tamanho_legivel(download.tamanho), ext)
        metadados = {
            "url": para_registro(url),
            "final_url": para_registro(download.url_final),
            "content_type": content_type or None,
            "size_bytes": download.tamanho,
            "etag": download.headers.get("etag"),
            "last_modified": download.headers.get("last-modified"),
        }
        return caminho, ext, nome, metadados

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        context: str = self.get_param("context", "drive")
        crs: str = self.get_param("crs", "EPSG:4326").strip()
        zip_member: str = self.get_param("zipMember", "").strip()
        skip_rows = self.get_param_int("skipRows", 0)
        if skip_rows < 0:
            raise ValueError("'Linhas a ignorar no início' não pode ser negativo.")
        lat_col: str = self.get_param("latColumn", "").strip()
        lon_col: str = self.get_param("lonColumn", "").strip()
        if bool(lat_col) != bool(lon_col):
            raise ValueError(
                "Preencha as duas colunas, latitude e longitude, para gerar pontos — ou nenhuma."
            )
        workspace_id: str | None = getattr(self, "_workspace_id", None)
        extra: dict = {}

        if context == "url":
            file_id = None
            temp_path, ext, original_name, extra = await self._baixar()
        elif context == "artifacts":
            file_id: str = self.get_param("artifactId", "").strip()
            if not file_id:
                raise ValueError("Parametro 'artifactId' e obrigatorio no contexto Artefatos.")
            logger.info("DataInput: resolvendo artefato id=%s workspace=%s", file_id, workspace_id)
            temp_path, ext, original_name = await asyncio.to_thread(
                resolve_artifact_file, file_id
            )
        else:
            file_id = self.get_param("driveFileId", "").strip()
            if not file_id:
                raise ValueError("Parametro 'driveFileId' e obrigatorio no contexto Drive.")
            logger.info("DataInput: resolvendo arquivo id=%s workspace=%s", file_id, workspace_id)
            temp_path, ext, original_name = await asyncio.to_thread(
                resolve_drive_file, file_id
            )

        logger.info("DataInput: carregando '%s' (ext=%s)", original_name, ext)
        if zip_member and ext != "zip":
            logger.info("DataInput: 'Arquivo dentro do ZIP' ignorado — '%s' não é um ZIP.", original_name)
        info: dict = {}
        data = await asyncio.to_thread(
            _load_file, temp_path, ext, crs, zip_member=zip_member, skip_rows=skip_rows, info=info,
        )
        if lat_col:
            data = await asyncio.to_thread(_pontos_de_colunas, data, lat_col, lon_col, crs or "EPSG:4326")

        metadata = {
            "context": context,
            "file_id": file_id,
            "original_name": original_name,
            "extension": ext,
            **extra,
            "zip_member": info.get("zip_member"),
        }

        import geopandas as gpd
        import pandas as pd
        if isinstance(data, gpd.GeoDataFrame):
            logger.info("DataInput: GeoDataFrame — %d feicoes, CRS: %s", len(data), data.crs)
        elif isinstance(data, pd.DataFrame):
            logger.info("DataInput: DataFrame — %d linhas x %d colunas", *data.shape)

        return {"output": data, "metadata": metadata}
