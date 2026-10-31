"""
Choosing and extracting one file from a ZIP (flow/utils/leitura_zip.py).

The ZIP comes from outside — a URL, or a Drive file anyone in the workspace
uploaded —, so what is refused is refused BEFORE a byte is written: a name
with `..`, an entry that expands a thousandfold, a `.vrt`.
"""
import os
import struct
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


def test_too_many_entries_are_refused_before_the_zip_is_parsed(tmp_path, monkeypatch):
    monkeypatch.setattr(leitura_zip, "_MAX_MEMBROS", 10)
    caminho = _zip(tmp_path, [(f"f{i}.csv", b"a\n") for i in range(20)])

    def sem_parse(*_a, **_k):
        raise AssertionError("ZipFile parsed the whole central directory before the refusal")

    monkeypatch.setattr(leitura_zip.zipfile, "ZipFile", sem_parse)

    with pytest.raises(ZipInvalidoError, match="mais de 10 entradas"):
        with extrair(caminho, ""):
            pass


def _com_total_declarado(caminho: str, total: int) -> None:
    """Rewrites the end record's entry count, leaving the directory as it is."""
    dados = bytearray(open(caminho, "rb").read())
    fim = dados.rfind(b"PK\x05\x06")
    struct.pack_into("<HH", dados, fim + 8, total, total)
    open(caminho, "wb").write(dados)


def test_an_end_record_that_lies_about_the_count_does_not_get_past(tmp_path, monkeypatch):
    # zipfile walks the directory by its size and ignores the declared total:
    # a ZIP declaring 1 entry was parsed whole before the refusal.
    monkeypatch.setattr(leitura_zip, "_MAX_MEMBROS", 10)
    caminho = _zip(tmp_path, [(f"f{i}.csv", b"a\n") for i in range(20)])
    _com_total_declarado(caminho, 1)

    def sem_parse(*_a, **_k):
        raise AssertionError("ZipFile parsed the whole central directory before the refusal")

    monkeypatch.setattr(leitura_zip.zipfile, "ZipFile", sem_parse)

    with pytest.raises(ZipInvalidoError, match="mais de 10 entradas"):
        leitura_zip.membros(caminho)


def test_the_walk_counts_what_zipfile_parses(tmp_path):
    caminho = _zip(tmp_path, [(f"pasta/f{i}.csv", b"a\n") for i in range(7)])
    _com_total_declarado(caminho, 1)

    assert leitura_zip._contar_entradas(caminho) == 7
    assert len(zipfile.ZipFile(caminho).infolist()) == 7


def test_a_name_flagged_utf8_that_is_not_gives_a_sentence(tmp_path):
    caminho = _zip(tmp_path, [("municipio.csv", b"a;b\n1;2\n")])
    dados = bytearray(open(caminho, "rb").read())
    diretorio = dados.rfind(b"PK\x01\x02")
    nome = dados.find(b"municipio.csv", diretorio)
    dados[nome + 7] = 0xED  # 'município' written in cp1252
    flags = struct.unpack_from("<H", dados, diretorio + 8)[0]
    struct.pack_into("<H", dados, diretorio + 8, flags | 0x800)
    open(caminho, "wb").write(dados)

    with pytest.raises(leitura_zip.ZipIlegivelError, match="marcado como UTF-8"):
        leitura_zip.membros(caminho)


def test_the_whole_zip_for_gdal_gets_the_bomb_rule_on_every_member(tmp_path, monkeypatch):
    monkeypatch.setattr(leitura_zip, "_PISO_RAZAO_BYTES", 1024)
    monkeypatch.setattr(leitura_zip, "_RAZAO_MAXIMA", 100)
    caminho = _zip(tmp_path, [("dados.csv", b"a;b\n1;2\n"), ("dados.dbf", b"0" * 5_000_000)])

    with pytest.raises(ZipInvalidoError, match="zip bomb"):
        leitura_zip.conferir_para_gdal(caminho)


def test_the_whole_zip_for_gdal_passes_a_normal_zip(tmp_path):
    caminho = _zip(tmp_path, [("dados.csv", b"a;b\n1;2\n"), ("__MACOSX/._dados.csv", b"x")])

    assert [i.filename for i in leitura_zip.conferir_para_gdal(caminho)] == ["dados.csv"]


def test_a_corrupted_member_is_named(tmp_path):
    caminho = tmp_path / "dados.zip"
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("a.csv", b"coluna\nvalor-original\n")
    caminho.write_bytes(caminho.read_bytes().replace(b"valor-original", b"valor-ALTERADO"))

    with pytest.raises(ZipInvalidoError, match="'a.csv' está corrompido"):
        with extrair(str(caminho), ""):
            pass


def test_an_old_excel_does_not_count_as_readable():
    # The executor has no `.xls` reader: the CSV beside the data dictionary is the one.
    assert escolher(_infos(["dados.csv", "dicionario.xls"]), "") == "dados.csv"


def test_a_file_that_is_not_a_zip(tmp_path):
    caminho = tmp_path / "falso.zip"
    caminho.write_bytes(b"isto nao e zip")

    with pytest.raises(ZipInvalidoError, match="não é um ZIP válido"):
        with extrair(str(caminho), ""):
            pass
