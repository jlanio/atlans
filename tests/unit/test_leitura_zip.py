"""
Choosing and extracting one file from a ZIP (flow/utils/leitura_zip.py).

The ZIP comes from outside — a URL, or a Drive file anyone in the workspace
uploaded —, so what is refused is refused BEFORE a byte is written: a name
with `..`, an entry that expands a thousandfold, a `.vrt`.
"""
import os
import zipfile

import pytest

from flow.utils import leitura_zip
from flow.utils.leitura_zip import ZipInvalidoError, escolher, extrair


def _zip(tmp_path, entradas, nome="dados.zip"):
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, conteudo in entradas:
            zf.writestr(arcname, conteudo)
    return str(caminho)


def _infos(nomes):
    return [zipfile.ZipInfo(n) for n in nomes]


def test_the_only_readable_file_needs_no_pattern():
    infos = _infos(["leiame.txt", "dados/municipios.shp", "dados/municipios.dbf", "__MACOSX/._municipios.shp"])
    assert escolher(infos, "") == "dados/municipios.shp"


def test_the_pattern_matches_the_name_or_the_path_ignoring_case():
    infos = _infos(["dados/Municipios.SHP", "dados/estados.shp"])
    assert escolher(infos, "municipios.shp") == "dados/Municipios.SHP"
    assert escolher(infos, "dados/est*") == "dados/estados.shp"


def test_an_exact_name_wins_over_the_pattern_syntax():
    infos = _infos(["censo [2022].csv", "censo 2.csv"])
    assert escolher(infos, "censo [2022].csv") == "censo [2022].csv"


def test_several_readable_files_without_a_pattern_are_listed():
    with pytest.raises(ZipInvalidoError, match="2 arquivos que o nó lê: a.shp, b.shp"):
        escolher(_infos(["a.shp", "b.shp"]), "")


def test_an_ambiguous_pattern_is_refused():
    with pytest.raises(ZipInvalidoError, match="casa com 2 arquivos"):
        escolher(_infos(["INMET_A001.CSV", "INMET_A002.CSV"]), "INMET*")


def test_a_pattern_that_finds_nothing_lists_what_can_be_read():
    with pytest.raises(ZipInvalidoError, match="Arquivos que o nó lê: a.shp"):
        escolher(_infos(["a.shp", "b.dbf"]), "*.geojson")


def test_a_zip_inside_the_zip_is_named_as_such():
    with pytest.raises(ZipInvalidoError, match="ZIP dentro de ZIP"):
        escolher(_infos(["camadas.zip", "a.csv"]), "camadas*")


def test_extracts_the_shapefile_with_its_sidecars(tmp_path):
    caminho = _zip(tmp_path, [
        ("dados/municipios.shp", b"shp"), ("dados/municipios.dbf", b"dbf"),
        ("dados/municipios.shx", b"shx"), ("dados/municipios.prj", b"prj"),
        ("dados/municipios_2010.shp", b"outro"), ("outra/municipios.dbf", b"outra pasta"),
    ])

    with extrair(caminho, "municipios.shp") as (local, ext, nome):
        pasta = os.path.dirname(local)
        assert (ext, nome) == ("shp", "dados/municipios.shp")
        assert sorted(os.listdir(pasta)) == ["municipios.dbf", "municipios.prj", "municipios.shp", "municipios.shx"]
        with open(os.path.join(pasta, "municipios.dbf"), "rb") as f:
            assert f.read() == b"dbf"
    assert not os.path.exists(pasta)


def test_a_name_with_dot_dot_is_refused(tmp_path):
    caminho = _zip(tmp_path, [("../../fora.csv", b"a,b\n")])

    with pytest.raises(ZipInvalidoError, match="Nome de arquivo inseguro"):
        with extrair(caminho, ""):
            pass


def test_an_absolute_name_is_refused(tmp_path):
    caminho = _zip(tmp_path, [("/etc/cron.d/x.csv", b"a,b\n")])

    with pytest.raises(ZipInvalidoError, match="Nome de arquivo inseguro"):
        with extrair(caminho, ""):
            pass


def test_a_vrt_anywhere_refuses_the_zip(tmp_path):
    caminho = _zip(tmp_path, [("a.csv", b"a,b\n"), ("x.vrt", b"<OGRVRTDataSource/>")])

    with pytest.raises(ZipInvalidoError, match=r"\.vrt"):
        with extrair(caminho, "a.csv"):
            pass


def test_a_zip_bomb_is_refused_before_extracting(tmp_path, monkeypatch):
    monkeypatch.setattr(leitura_zip, "_PISO_RAZAO_BYTES", 1024)
    monkeypatch.setattr(leitura_zip, "_RAZAO_MAXIMA", 100)
    caminho = _zip(tmp_path, [("zeros.csv", b"0" * 5_000_000)])

    with pytest.raises(ZipInvalidoError, match="zip bomb"):
        with extrair(caminho, ""):
            pass
    assert not [n for n in os.listdir(tmp_path) if n.startswith("atlans-zip-")]


def test_the_extraction_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(leitura_zip, "LIMITE_EXTRACAO", 100)
    caminho = _zip(tmp_path, [("grande.csv", os.urandom(500))])

    with pytest.raises(ZipInvalidoError, match="acima do limite"):
        with extrair(caminho, ""):
            pass


def test_an_encrypted_member_is_named():
    info = zipfile.ZipInfo("protegido.csv")
    info.flag_bits |= 0x1

    with pytest.raises(ZipInvalidoError, match="protegido por senha"):
        leitura_zip._checar_tamanhos([info])


def test_a_file_that_is_not_a_zip(tmp_path):
    caminho = tmp_path / "falso.zip"
    caminho.write_bytes(b"isto nao e zip")

    with pytest.raises(ZipInvalidoError, match="não é um ZIP válido"):
        with extrair(str(caminho), ""):
            pass
