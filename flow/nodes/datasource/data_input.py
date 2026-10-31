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
from flow.utils.coordenadas import pontos_de_colunas as _pontos_de_colunas
from flow.utils.logger import get_logger
from flow.utils.drive_resolver import resolve_drive_file, resolve_artifact_file

logger = get_logger(__name__)

_GEO_EXTENSIONS = {"geojson", "shp", "zip", "kml", "kmz", "gpkg", "gml", "fgb"}

# Download limit of the URL context when the field is left as is. A year of
# INMET stations or a national municipal grid fits; what does not fit is
# usually the wrong file.
_MAX_DOWNLOAD_MB_PADRAO = 800

# The formats of the URL origin, as `expectedFormat` names them. The person says
# what the address delivers and the node checks the content against it: the name
# on the URL can be `download.php?id=123`, and a portal's error page often comes
# as 200 — guessing would turn a JSON error into the node's output, and the
# workflow would go on with it.
_FORMATOS_URL = {
    "csv": "CSV",
    "zip": "ZIP (shapefile ou outros arquivos dentro)",
    "geojson": "GeoJSON",
    "json": "JSON",
    "kml": "KML",
    "kmz": "KMZ",
    "gpkg": "GeoPackage",
    "xlsx": "XLSX (Excel)",
}
# The form's select cannot start empty (Radix refuses an empty item value), so
# the field starts on an option that is not a format, and the node refuses it.
_ESCOLHER = "escolher"

# What each choice accepts among the kinds `_o_que_veio` tells apart. A GeoJSON
# is JSON too; a ZIP holding only KML (a KMZ under another name) is still a ZIP.
_ACEITA = {
    "csv": {"texto"},
    "zip": {"zip", "kmz"},
    "geojson": {"geojson"},
    "json": {"json", "geojson"},
    "kml": {"kml"},
    "kmz": {"kmz"},
    "gpkg": {"gpkg"},
    "xlsx": {"xlsx"},
}

# Kinds told apart by the content's first bytes.
_ASSINATURAS = (
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),  # empty ZIP
    (b"SQLite format 3\x00", "gpkg"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "xls"),
    (b"fgb\x03", "fgb"),
    (b"\x1f\x8b", "gz"),
)
_GEOJSON = re.compile(rb'"type"\s*:\s*"(FeatureCollection|Feature)"')
_BLOCO_GEOJSON = 1024 * 1024
_SOBREPOSICAO_GEOJSON = 256

# The URL formats that are tables, where latitude/longitude columns make points.
# The same list decides what the form shows (`visibleWhen`) and what the node
# applies: a value typed under another format stays saved, out of sight.
_FORMATOS_COM_COORDENADAS = ("csv", "xlsx", "zip")

# How the message names what came, and what to do about the kinds that are
# not a choice of the field.
_O_QUE_E = {
    "html": "uma página HTML",
    "gz": "um arquivo gzip (.gz)",
    "xls": "uma planilha XLS (Excel antigo)",
    "fgb": "um FlatGeobuf",
    "zip": "um ZIP",
    "kmz": "um KMZ",
    "xlsx": "uma planilha XLSX",
    "gpkg": "um GeoPackage",
    "json": "um JSON",
    "geojson": "um GeoJSON",
    "kml": "um KML",
    "xml": "um XML",
    "texto": "um arquivo de texto",
    "binario": "um arquivo binário",
}
_O_QUE_FAZER = {
    "html": " Costuma ser tela de login, captcha ou página de erro do portal: abra a URL "
            "no navegador para conferir o endereço direto do arquivo.",
    "gz": " A Entrada de Dados não lê .gz: use a versão .zip ou sem compressão, se o "
          "portal oferecer.",
    "xls": " O executor não lê o Excel antigo: use a versão XLSX ou CSV, se o portal oferecer.",
}

# The fields of a file format. On the Drive and in Artifacts the file is chosen
# in the picker and its format is only known when the node runs, so they always
# show; on the URL origin they show for the format chosen. `any` is an OR of
# rules (node-config-form's visibility).
_NA_ORIGEM_ARMAZENADA = {"field": "context", "in": ["drive", "artifacts"]}
# An editor older than `any` (a tab left open across the deploy) reads only
# `field`/`in` and broke the form on `r.in` without them. Naming every origin
# there makes it show the field, as it did before the formats existed; the
# current editor reads `any` first and never looks at them.
_EM_QUALQUER_ORIGEM = {"field": "context", "in": ["drive", "artifacts", "url"]}


def _visivel_no_formato(*formatos: str) -> dict:
    return {
        "any": [_NA_ORIGEM_ARMAZENADA, {"field": "expectedFormat", "in": list(formatos)}],
        **_EM_QUALQUER_ORIGEM,
    }


def _ler_kmz(path: str) -> Any:
    """A KMZ holding a single KML (Google Earth's, and Salvar arquivo's) is
    read through that KML: GDAL's LIBKML, opening the .kmz itself, drops the
    attributes (SchemaData) it reads from the same doc.kml outside the zip. A
    KMZ made of several KML (LIBKML's own, with layers/) is read as it is.

    The KML goes to a file, not to memory: as bytes it was held twice (here
    and in GDAL's /vsimem), half again the RAM for a large KMZ. It is extracted
    like any member of a ZIP, with the same refusals (zip bomb, size, names): a
    KMZ downloaded from a URL is as foreign as a ZIP.
    """
    from flow.utils import leitura_zip
    from flow.utils.leitura_geo import read_geodataframe

    kmls = [i.filename for i in leitura_zip.membros(path) if i.filename.lower().endswith(".kml")]
    if len(kmls) != 1:
        leitura_zip.conferir_para_gdal(path)
        return read_geodataframe(path)
    with leitura_zip.extrair(path, kmls[0]) as (doc, _ext, _nome):
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
    """A `.json` that is GeoJSON — what APIs and many portals serve.

    The marker is searched in the whole file, not only in its start: a
    serializer that sorts the keys (`json.dumps(sort_keys=True)`) writes `type`
    after `features` and, in each feature, after the geometry — for a municipal
    boundary, megabytes in. Read in blocks, with an overlap that keeps a marker
    split between two of them.
    """
    resto = b""
    with open(path, "rb") as f:
        while bloco := f.read(_BLOCO_GEOJSON):
            janela = resto + bloco
            if _GEOJSON.search(janela):
                return True
            resto = janela[-_SOBREPOSICAO_GEOJSON:]
    return False


# Formats that are always ONE layer for GDAL. A ZIP whose only readable file is
# one of them needs no listing before the read: the listing opened the ZIP in
# GDAL a second time on every read, Drive workflows included.
_UMA_CAMADA = frozenset({"shp", "geojson", "json", "csv", "fgb"})


def _talvez_varias_camadas(membros: list) -> bool:
    from flow.utils.leitura_zip import legiveis
    lidos = legiveis(membros)
    return len(lidos) != 1 or posixpath.splitext(lidos[0])[1].lower().lstrip(".") not in _UMA_CAMADA


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
        # Handed whole to GDAL, every member gets the zip-bomb rule first: GDAL
        # inflates what it reads. A ZIP `zipfile` cannot read at all still goes
        # to GDAL, as before, and the fallback below says what is wrong.
        try:
            membros = leitura_zip.conferir_para_gdal(path)
        except leitura_zip.ZipIlegivelError:
            membros = None
        # Only GDAL's own reading inside the `try`: a CRS that does not exist,
        # for one, must fail as itself, not as a ZIP that would not open.
        try:
            leitura = {}
            if membros is None or _talvez_varias_camadas(membros):
                camadas = list_layers(path)
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
        # utf-8-sig: a BOM (IIS/.NET portals write one) is skipped, as the
        # format check skips it; plain UTF-8 reads the same.
        with open(path, "r", encoding="utf-8-sig") as f:
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

def _nome_da_url(url: str) -> str:
    return posixpath.basename(unquote(urlparse(url).path)) or "download"


def _tamanho_legivel(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _amostra(inicio: bytes) -> str:
    return repr(inicio[:40])[2:-1]


def _o_que_veio(caminho: str, inicio: bytes) -> str:
    """The kind of content a download delivered, told by its first bytes —
    never by the name or the `Content-Type`, which an error page shares with
    the file it replaced."""
    magia = next((tipo for assinatura, tipo in _ASSINATURAS if inicio.startswith(assinatura)), None)
    if magia == "zip":
        return _tipo_do_zip(caminho)
    if magia:
        return magia
    cabeca = inicio.lstrip(b"\xef\xbb\xbf").lstrip()
    baixo = cabeca[:512].lower()
    if baixo.startswith(b"<!doctype html") or baixo.startswith(b"<html"):
        return "html"
    if b"\x00" in inicio:
        return "binario"
    if cabeca[:1] in (b"{", b"["):
        return "geojson" if _GEOJSON.search(inicio) else "json"
    if cabeca[:1] == b"<":
        return "kml" if b"<kml" in cabeca[:4096].lower() else "xml"
    return "texto"


def _tipo_do_zip(caminho: str) -> str:
    """XLSX and KMZ are ZIPs too: the names inside say which one this is."""
    from flow.utils.leitura_zip import ZipInvalidoError, legiveis, membros
    try:
        # `membros` refuses an absurd number of entries before parsing them all.
        infos = membros(caminho)
    except ZipInvalidoError:
        return "zip"  # the read says what is wrong with it
    nomes = [i.filename for i in infos]
    if "[Content_Types].xml" in nomes and any(n.startswith("xl/") for n in nomes):
        return "xlsx"
    lidos = legiveis(infos)
    if lidos and all(n.lower().endswith(".kml") for n in lidos):
        return "kmz"
    return "zip"


def _conferir_formato(esperado: str, caminho: str, inicio: bytes) -> None:
    """Fails when the content is not the format the person said would come,
    saying what came — and, when it is another choice of the field, which one.

    Blocking (it may open a ZIP or read the whole file): runs off the event loop.
    """
    veio = _o_que_veio(caminho, inicio)
    # The first 8 KB say "json" when the GeoJSON marker comes later (sorted keys,
    # a large first geometry); only who expects GeoJSON pays to look further.
    if veio == "json" and esperado == "geojson" and _arquivo_geojson(caminho):
        veio = "geojson"
    if veio in _ACEITA[esperado]:
        return
    opcao = "csv" if veio == "texto" else veio
    o_que_fazer = _O_QUE_FAZER.get(veio) or (
        f" Se é isso mesmo, escolha '{_FORMATOS_URL[opcao]}' em 'Formato esperado'."
        if opcao in _FORMATOS_URL else ""
    )
    raise ValueError(
        f"Esperava {_FORMATOS_URL[esperado].split(' (')[0]}, mas o servidor devolveu "
        f"{_O_QUE_E[veio]} (começa com: {_amostra(inicio)}).{o_que_fazer}"
    )


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
                    "name": "expectedFormat", "required": True,
                    "label": "Formato esperado",
                    "type": "select",
                    "default": _ESCOLHER,
                    "description": "O formato do arquivo que a URL entrega. O nó confere o "
                                   "conteúdo baixado e falha se vier outra coisa — uma página "
                                   "de login ou um JSON de erro no lugar do arquivo, por exemplo.",
                    "options": [{"value": _ESCOLHER, "label": "Escolha o formato do arquivo"}] + [
                        {"value": valor, "label": rotulo} for valor, rotulo in _FORMATOS_URL.items()
                    ],
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
                    "visibleWhen": _visivel_no_formato("zip"),
                },
                {
                    "name": "skipRows",
                    "label": "Linhas a ignorar no início (CSV)",
                    "type": "integer",
                    "default": 0,
                    "description": "Linhas acima do cabeçalho, como os metadados da estação "
                                   "nos CSVs do INMET (8).",
                    "visibleWhen": _visivel_no_formato("csv", "zip"),
                },
                {
                    "name": "latColumn",
                    "label": "Coluna de latitude",
                    "type": "string",
                    "default": "",
                    "description": "Opcional. Com latitude e longitude preenchidas, uma tabela "
                                   "(CSV, XLSX) vira pontos, com as coordenadas no CRS de saída.",
                    "visibleWhen": _visivel_no_formato(*_FORMATOS_COM_COORDENADAS),
                },
                {
                    "name": "lonColumn",
                    "label": "Coluna de longitude",
                    "type": "string",
                    "default": "",
                    "description": "Opcional. Veja a coluna de latitude.",
                    "visibleWhen": _visivel_no_formato(*_FORMATOS_COM_COORDENADAS),
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
        esperado: str = self.get_param("expectedFormat", _ESCOLHER)
        if esperado not in _FORMATOS_URL:
            raise ValueError(
                "Escolha o 'Formato esperado' do arquivo (CSV, ZIP, GeoJSON…): o nó confere "
                "o que chegar contra ele e falha se vier outra coisa."
            )
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
            # Off the event loop, which also serves the executor's WebSocket:
            # telling a ZIP's kind parses its central directory, and checking a
            # GeoJSON may read the whole file.
            await asyncio.to_thread(_conferir_formato, esperado, download.caminho, download.inicio)
            ext = esperado
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
        if (lat_col or lon_col) and context == "url" \
                and self.get_param("expectedFormat", _ESCOLHER) not in _FORMATOS_COM_COORDENADAS:
            # The form hides the columns for this format, but what was typed under
            # another one stays saved: applying it would fail the run over fields
            # the person cannot see.
            logger.info("DataInput: colunas de latitude/longitude ignoradas — o formato escolhido não é tabela.")
            lat_col = lon_col = ""
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
