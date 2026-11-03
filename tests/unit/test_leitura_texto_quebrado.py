"""A shapefile whose text is not the UTF-8 its .cpg promises is still read.

ICMBio's autos_infracao_icmbio_shp.zip (gov.br) failed in DataInput with
"'utf-8' codec can't decode byte 0xc3 in position 253: unexpected end of
data": the DBF keeps text in fields of up to 254 BYTES, and the program that
wrote it cut a 2-byte "ã"/"ç" at the border. pyogrio decodes the whole layer
in the declared encoding and gave up on that one value, so the file did not
open at all. The files here are written by GDAL and then get the same defect
put into their bytes.
"""
from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import pytest

gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")

from flow.utils.leitura_geo import _texto_utf8, read_geodataframe  # noqa: E402

_LONGO = "a" * 253 + "b"


def _shapefile(pasta: Path, descricoes: list[str], municipios: list[str]) -> Path:
    from shapely.geometry import Point

    gdf = gpd.GeoDataFrame(
        {"descricao": descricoes, "municipio": municipios},
        geometry=[Point(-52 - i / 10, -6) for i in range(len(descricoes))],
        crs="EPSG:4674",
    )
    shp = pasta / "autos.shp"
    gdf.to_file(shp, encoding="UTF-8")
    return shp


def _trocar_no_dbf(shp: Path, antes: bytes, depois: bytes) -> None:
    dbf = shp.with_suffix(".dbf")
    conteudo = dbf.read_bytes()
    assert conteudo.count(antes) == 1
    dbf.write_bytes(conteudo.replace(antes, depois))


def _com_caractere_cortado(pasta: Path) -> Path:
    """Record 0: a 254-byte field whose last byte is the first half of an "ã"."""
    shp = _shapefile(
        pasta,
        [_LONGO, "Ação de fiscalização em área protegida"],
        ["São Félix do Xingu", "Altamira"],
    )
    _trocar_no_dbf(shp, _LONGO.encode(), _LONGO[:253].encode() + b"\xc3")
    with pytest.raises(UnicodeDecodeError, match="unexpected end of data"):
        gpd.read_file(shp)  # the defect, as pyogrio sees it
    return shp


def _zipar(shp: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for parte in shp.parent.glob("autos.*"):
            z.write(parte, parte.name)
    return buf.getvalue()


def _confere(gdf) -> None:
    assert len(gdf) == 2
    # The cut half goes; the 253 bytes before it stay.
    assert gdf.loc[0, "descricao"] == _LONGO[:253]
    # Every other accent, valid UTF-8, is read as it is.
    assert gdf.loc[1, "descricao"] == "Ação de fiscalização em área protegida"
    assert list(gdf["municipio"]) == ["São Félix do Xingu", "Altamira"]
    assert gdf.crs.to_epsg() == 4674
    assert gdf.geometry.iloc[0].x == pytest.approx(-52)


def test_a_character_cut_at_the_end_of_the_field_no_longer_stops_the_read(tmp_path, caplog):
    shp = _com_caractere_cortado(tmp_path)
    with caplog.at_level(logging.WARNING, logger="flow.utils.leitura_geo"):
        gdf = read_geodataframe(shp)
    _confere(gdf)
    assert "1 texto(s)" in caplog.text
    assert "254 bytes" in caplog.text


def test_the_zipped_shapefile_reads_from_a_buffer_too(tmp_path):
    """The first read consumes the buffer: the second one gets it anew."""
    dados = _zipar(_com_caractere_cortado(tmp_path))
    _confere(read_geodataframe(io.BytesIO(dados)))
    _confere(read_geodataframe(dados))


def test_datainput_reads_the_zip_it_downloaded(tmp_path):
    """The path of the report: DataInput, a .zip with the shapefile inside."""
    from flow.nodes.datasource.data_input import _ler

    origem = tmp_path / "shp"
    origem.mkdir()
    arquivo = tmp_path / "autos_infracao_icmbio_shp.zip"
    arquivo.write_bytes(_zipar(_com_caractere_cortado(origem)))
    _confere(_ler(str(arquivo), "zip", ""))


def test_a_cpg_that_says_utf8_over_a_windows_file_reads_as_cp1252(tmp_path):
    shp = _shapefile(tmp_path, ["Fiscalização", "Ok"], ["São Félix", "Altamira"])
    for texto in ("Fiscalização", "São Félix"):
        # Same length in bytes (DBF fields are fixed-width): the padding is
        # the spaces DBF pads with.
        utf8, cp1252 = texto.encode("utf-8"), texto.encode("cp1252")
        _trocar_no_dbf(shp, utf8, cp1252.ljust(len(utf8)))
    gdf = read_geodataframe(shp)
    assert list(gdf["descricao"]) == ["Fiscalização", "Ok"]
    assert list(gdf["municipio"]) == ["São Félix", "Altamira"]


def test_a_valid_file_is_read_once_and_untouched(tmp_path, caplog, monkeypatch):
    shp = _shapefile(tmp_path, ["Ação", "x"], ["São Félix", "Altamira"])
    leituras = []
    original = gpd.read_file
    monkeypatch.setattr(gpd, "read_file", lambda *a, **k: leituras.append(k) or original(*a, **k))
    with caplog.at_level(logging.WARNING, logger="flow.utils.leitura_geo"):
        gdf = read_geodataframe(shp)
    assert list(gdf["descricao"]) == ["Ação", "x"]
    assert leituras == [{}]
    assert not [r for r in caplog.records if r.name == "flow.utils.leitura_geo"]


def test_an_encoding_asked_by_the_caller_is_respected(tmp_path):
    shp = _com_caractere_cortado(tmp_path)
    with pytest.raises(UnicodeDecodeError):
        read_geodataframe(shp, encoding="UTF-8")


@pytest.mark.parametrize("bruto, esperado, consertado", [
    ("Ação".encode(), "Ação", False),
    (b"abc", "abc", False),
    # Cut at the end: the half character goes.
    ("Ação".encode() + b"\xc3", "Ação", True),
    (b"abc\xe2\x80", "abc", True),
    # A broken byte in the middle of UTF-8 text: only it becomes U+FFFD.
    ("São".encode() + b"\xff" + "Félix".encode(), "São�Félix", True),
    # No UTF-8 at all: Windows-1252.
    ("São Félix".encode("cp1252"), "São Félix", True),
    ("Paraná – “PR”".encode("cp1252"), "Paraná – “PR”", True),
])
def test_each_value_is_turned_back_into_its_text(bruto, esperado, consertado):
    assert _texto_utf8(bruto.decode("latin-1")) == (esperado, consertado)


def test_other_formats_still_fail_as_before(tmp_path):
    """Not a shapefile: no recovery, the caller's own fallback runs (a CSV in a
    ZIP goes to DataInput's CSV reader, which reads decimal commas)."""
    arquivo = tmp_path / "pontos.geojson"
    arquivo.write_bytes(
        b'{"type":"FeatureCollection","features":[{"type":"Feature","properties":'
        b'{"nome":"S\xe3o Paulo"},"geometry":{"type":"Point","coordinates":[-46.6,-23.5]}}]}'
    )
    with pytest.raises(UnicodeDecodeError):
        read_geodataframe(arquivo)
