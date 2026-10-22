# flow/utils/leitura_zip.py
"""Choosing and extracting ONE file from a ZIP, for DataInput.

Handed to GDAL as is, a ZIP is read the way GDAL sees it, and that failed in
the cases that are routine in Brazilian open data (geopandas 1.1.4,
pyogrio 0.13.0):

  - shapefile inside a subfolder: "not recognized as being in a supported file
    format";
  - two shapefiles: the first is read, with no error and no sign of the other;
  - CSV with ';' in cp1252 (Excel in Portuguese): UnicodeDecodeError;
  - INMET's CSVs (metadata lines above the header): wrong columns, no error.

Here the ZIP is opened with `zipfile`, the file the user asked for (or the only
readable one) is extracted to a temporary folder — with its sidecars, for a
shapefile — and read by the reader of ITS extension, the same one a loose file
would get.

What is refused before writing a single byte, because the ZIP comes from
outside (a URL, or a Drive file anyone in the workspace uploaded):
  - member names with an absolute path or `..` (zip slip). The extraction
    flattens the name anyway; refusing says the ZIP is malformed;
  - more than `_MAX_MEMBROS` entries, a suspicious compression ratio and more
    than `LIMITE_EXTRACAO` bytes to extract (zip bomb);
  - any `.vrt` in the ZIP, the same rule as `leitura_geo`;
  - encrypted members and compression methods `zipfile` does not read, with a
    sentence instead of a traceback.
"""
import fnmatch
import os
import posixpath
import shutil
import struct
import tempfile
import zipfile
import zlib
from contextlib import contextmanager
from typing import Iterator

# Extensions of a file DataInput knows how to read once extracted. A ZIP inside
# the ZIP is not among them: one level is what portals publish, and recursion
# would multiply the bomb checks for no case seen in practice. Nor is the old
# Excel `.xls`: the executor has no reader for it (pandas would need xlrd), so
# counting it would only pick, or ask about, a file that then fails to open.
EXTENSOES_LEGIVEIS = frozenset({
    "shp", "geojson", "json", "gpkg", "kml", "kmz", "gml", "fgb", "csv", "xlsx",
})

_MAX_MEMBROS = 50_000
# Above this ratio, and for a member that would expand to more than
# `_PISO_RAZAO_BYTES`, the content is not data: a CSV compresses 5-20x, a
# shapefile less than that. A zip bomb starts in the thousands.
_RAZAO_MAXIMA = 1000
_PISO_RAZAO_BYTES = 100 * 1024 * 1024
# What may be extracted to disk for ONE read (the chosen file and its sidecars).
LIMITE_EXTRACAO = 8 * 1024 ** 3

_LISTA_MAXIMA = 12


class ZipInvalidoError(ValueError):
    """The ZIP cannot be read safely, or the choice of file is ambiguous."""


def _ignorado(nome: str) -> bool:
    """macOS metadata (`__MACOSX/`, `._x`) and folder entries."""
    base = posixpath.basename(nome)
    return nome.endswith("/") or nome.startswith("__MACOSX/") or base.startswith("._")


def _extensao(nome: str) -> str:
    return posixpath.splitext(nome)[1].lower().lstrip(".")


def _nome_seguro(nome: str) -> bool:
    normalizado = nome.replace("\\", "/")
    if normalizado.startswith("/") or (len(normalizado) > 1 and normalizado[1] == ":"):
        return False
    return ".." not in normalizado.split("/")


def _resumo(nomes: list[str]) -> str:
    mostrados = ", ".join(nomes[:_LISTA_MAXIMA])
    resto = len(nomes) - _LISTA_MAXIMA
    return mostrados + (f" (e mais {resto})" if resto > 0 else "")


def _muitas_entradas(n: int) -> str:
    return f"O ZIP tem {n} entradas, acima do máximo de {_MAX_MEMBROS} que o nó abre."


def _entradas_declaradas(caminho_zip: str) -> int | None:
    """How many entries the ZIP's end record declares, read WITHOUT parsing them.

    `zipfile.ZipFile` parses the whole central directory as it opens: a 100 MB
    ZIP of a million empty entries took ~10 s and hundreds of MB before
    `_MAX_MEMBROS` could refuse it. The record is read by the same function
    `ZipFile` uses (ZIP64 included), so the count is the one it would parse.
    None when it cannot be read — `ZipFile` then says what is wrong.
    """
    ler_fim = getattr(zipfile, "_EndRecData", None)
    indice = getattr(zipfile, "_ECD_ENTRIES_TOTAL", None)
    if ler_fim is None or indice is None:
        return None
    try:
        with open(caminho_zip, "rb") as f:
            fim = ler_fim(f)
    except (OSError, zipfile.BadZipFile, struct.error):
        return None
    return None if fim is None else int(fim[indice])


def abrir(caminho_zip: str) -> zipfile.ZipFile:
    """Opens a ZIP that came from outside, refusing more than `_MAX_MEMBROS`
    entries BEFORE parsing them, and a file that is not a ZIP with a sentence."""
    declaradas = _entradas_declaradas(caminho_zip)
    if declaradas is not None and declaradas > _MAX_MEMBROS:
        raise ZipInvalidoError(_muitas_entradas(declaradas))
    try:
        return zipfile.ZipFile(caminho_zip)
    except zipfile.BadZipFile as e:
        raise ZipInvalidoError(f"O arquivo não é um ZIP válido: {e}") from e


def _inspecionar(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = zf.infolist()
    if len(infos) > _MAX_MEMBROS:  # the end record could not be read before opening
        raise ZipInvalidoError(_muitas_entradas(len(infos)))
    if any(i.filename.lower().endswith(".vrt") for i in infos):
        raise ZipInvalidoError("Arquivo .zip contem um .vrt — recusado por seguranca.")
    return [i for i in infos if not _ignorado(i.filename)]


def legiveis(infos: list[zipfile.ZipInfo]) -> list[str]:
    """Names of the members DataInput can read, in the ZIP's order."""
    return [
        i.filename for i in infos
        if not _ignorado(i.filename) and _extensao(i.filename) in EXTENSOES_LEGIVEIS
    ]


def _casa(nome: str, padrao: str) -> bool:
    """The pattern matches the whole path or just the file name, ignoring case:
    `*.shp` finds `dados/municipios.shp`, and `dados/*.shp` keeps working."""
    nome, padrao = nome.lower(), padrao.lower()
    return fnmatch.fnmatchcase(nome, padrao) or fnmatch.fnmatchcase(posixpath.basename(nome), padrao)


def escolher(infos: list[zipfile.ZipInfo], padrao: str) -> str:
    """The member to read: the only readable one matching `padrao` or, with an
    empty pattern, the only readable one in the ZIP."""
    candidatos = legiveis(infos)
    padrao = (padrao or "").strip()
    if not padrao:
        if len(candidatos) == 1:
            return candidatos[0]
        if not candidatos:
            raise ZipInvalidoError(_sem_legiveis(infos))
        raise ZipInvalidoError(
            f"O ZIP tem {len(candidatos)} arquivos que o nó lê: {_resumo(candidatos)}. "
            "Diga qual em 'Arquivo dentro do ZIP' (aceita padrão, como *.shp)."
        )

    # The exact name first: `censo [2022].csv` is a valid file name and, read
    # as a pattern, a character class that also matches `censo 2.csv`.
    exatos = [n for n in candidatos if padrao in (n, posixpath.basename(n))]
    if len(exatos) == 1:
        return exatos[0]

    escolhidos = [n for n in candidatos if _casa(n, padrao)]
    if len(escolhidos) == 1:
        return escolhidos[0]
    if len(escolhidos) > 1:
        raise ZipInvalidoError(
            f"O padrão '{padrao}' casa com {len(escolhidos)} arquivos do ZIP: "
            f"{_resumo(escolhidos)}. Deixe-o mais específico para escolher um só."
        )
    outros = [i.filename for i in infos if _casa(i.filename, padrao)]
    dica = ""
    if outros:
        dica = (f" O padrão casou com {_resumo(outros)}, que o nó não lê"
                + (" (ZIP dentro de ZIP não é aberto)" if any(_extensao(o) == "zip" for o in outros) else "")
                + ".")
    if not candidatos:
        raise ZipInvalidoError(f"Nenhum arquivo do ZIP casa com '{padrao}'.{dica} {_sem_legiveis(infos)}")
    raise ZipInvalidoError(
        f"Nenhum arquivo do ZIP casa com '{padrao}'.{dica} "
        f"Arquivos que o nó lê: {_resumo(candidatos)}."
    )


def _sem_legiveis(infos: list[zipfile.ZipInfo]) -> str:
    nomes = [i.filename for i in infos]
    return (
        "O ZIP não tem arquivo que o nó leia "
        f"({', '.join(sorted(EXTENSOES_LEGIVEIS))}). Conteúdo: {_resumo(nomes) or 'vazio'}."
    )


def _companheiros(infos: list[zipfile.ZipInfo], principal: str) -> list[zipfile.ZipInfo]:
    """The member plus, for a shapefile, the files of the same name in the same
    folder (.dbf, .shx, .prj, .cpg, .shp.xml…) — without them GDAL reads the
    geometry without attributes, or nothing at all."""
    if _extensao(principal) != "shp":
        return [i for i in infos if i.filename == principal]
    pasta = posixpath.dirname(principal)
    tronco = posixpath.splitext(posixpath.basename(principal))[0].lower() + "."
    return [
        i for i in infos
        if posixpath.dirname(i.filename) == pasta
        and posixpath.basename(i.filename).lower().startswith(tronco)
    ]


def _checar_tamanhos(membros: list[zipfile.ZipInfo]) -> None:
    total = 0
    for info in membros:
        if not _nome_seguro(info.filename):
            raise ZipInvalidoError(
                f"Nome de arquivo inseguro dentro do ZIP: {info.filename!r} "
                "(caminho absoluto ou '..'). O ZIP foi recusado."
            )
        if info.flag_bits & 0x1:
            raise ZipInvalidoError(
                f"'{info.filename}' está protegido por senha dentro do ZIP; o nó não lê ZIP com senha."
            )
        razao = info.file_size / max(info.compress_size, 1)
        if info.file_size > _PISO_RAZAO_BYTES and razao > _RAZAO_MAXIMA:
            raise ZipInvalidoError(
                f"'{info.filename}' se expande {razao:.0f} vezes ao descompactar — "
                "padrão de ZIP malicioso (zip bomb). O ZIP foi recusado."
            )
        total += info.file_size
    if total > LIMITE_EXTRACAO:
        raise ZipInvalidoError(
            f"O arquivo escolhido ocupa {total / 1024 ** 3:.1f} GB descompactado, acima do "
            f"limite de {LIMITE_EXTRACAO / 1024 ** 3:.0f} GB."
        )


@contextmanager
def extrair(caminho_zip: str, padrao: str) -> Iterator[tuple[str, str, str]]:
    """Extracts the chosen member to a temporary folder and yields
    (local path, extension, name inside the ZIP). The folder is removed on exit."""
    with abrir(caminho_zip) as zf:
        infos = _inspecionar(zf)
        principal = escolher(infos, padrao)
        membros = _companheiros(infos, principal)
        _checar_tamanhos(membros)

        pasta = tempfile.mkdtemp(prefix="atlans-zip-")
        try:
            destino_principal = ""
            for info in membros:
                # Flattened: only the file name, inside a folder that is ours.
                destino = os.path.join(pasta, posixpath.basename(info.filename.replace("\\", "/")))
                try:
                    with zf.open(info) as origem, open(destino, "wb") as saida:
                        shutil.copyfileobj(origem, saida, 1024 * 1024)
                except NotImplementedError as e:
                    raise ZipInvalidoError(
                        f"'{info.filename}' usa um método de compressão que o nó não lê ({e}). "
                        "Recompacte o arquivo com compressão padrão (deflate)."
                    ) from e
                except RuntimeError as e:  # zipfile: "File is encrypted, password required"
                    raise ZipInvalidoError(f"Não foi possível extrair '{info.filename}': {e}") from e
                except (zipfile.BadZipFile, EOFError, zlib.error) as e:
                    # Bad CRC, truncated or garbled data: a sentence instead of a
                    # traceback, and DataInput's fallback keeps GDAL's error beside it.
                    raise ZipInvalidoError(
                        f"'{info.filename}' está corrompido dentro do ZIP ({e}). Baixe ou gere o ZIP de novo."
                    ) from e
                if info.filename == principal:
                    destino_principal = destino
            yield destino_principal, _extensao(principal), principal
        finally:
            shutil.rmtree(pasta, ignore_errors=True)
