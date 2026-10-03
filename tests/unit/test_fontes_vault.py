# tests/unit/test_fontes_vault.py
"""The Vault parser: Obsidian markdown becomes catalog records.

The fixtures in `tests/fixtures/vault/` are REAL copies of the owner's Vault
(all of FUNAI; a slice of IBGE, which is WFS 1.0.0; a slice of TIGERweb,
which is ArcGIS; the Dominica placeholder) plus a folder in the NEW format —
frontmatter, inline tags and `_sinonimos.md` — which is what this parser now
accepts on top of today's format.
"""
from __future__ import annotations

import shutil
import unicodedata
from pathlib import Path

import pytest

from app.services import fontes_vault as fv

VAULT = Path(__file__).resolve().parents[1] / "fixtures" / "vault"


def _registros(pasta=VAULT):
    itens = list(fv.read_folder(pasta))
    return (
        [r for r in itens if isinstance(r, fv.RegistroDoVault)],
        [i for i in itens if isinstance(i, fv.Skipped)],
    )


def _da(instituicao, registros):
    return {r.type_name: r for r in registros if r.instituicao == instituicao}


# ── Today's format ────────────────────────────────────────────────────────────


def test_whole_funai_becomes_eight_layers_with_schema():
    registros, _ = _registros()
    funai = _da("FUNAI", registros)

    assert len(funai) == 8
    tis = funai["Funai:tis_poligonais"]
    assert tis.url == "https://geoserver.funai.gov.br/geoserver/ows"
    assert tis.titulo == "Terras indígenas (poligonais)"
    assert tis.grupo == "Funai"
    assert tis.versao == "2.0.0"
    assert tis.coletada_em == "2026-09-17 10:07 UTC"
    assert tis.prioridade == 2
    assert tis.descricao.startswith("Fundação Nacional dos Povos Indígenas — FUNAI. Terras indígenas")
    assert "FUNAI" in tis.temas and "Funai" in tis.temas
    assert tis.dicas and "Confirme atualização" in tis.dicas

    esquema = tis.esquema
    assert esquema["columns_source"] == "vault"
    assert len(esquema["columns"]) == 19
    assert esquema["geometry_column"] == "the_geom"
    assert esquema["geometry_type"] == "MultiPolygon"  # gml:MultiSurfacePropertyType
    nomes = {c["name"]: c for c in esquema["columns"]}
    assert nomes["uf_sigla"]["type"] == "string" and nomes["uf_sigla"]["xsd"] == "xsd:string"
    assert nomes["superficie_perimetro_ha"]["type"] == "double"
    assert nomes["the_geom"]["type"] == "MultiPolygon"


def test_sort_by_comes_from_the_first_existing_id_column():
    registros, _ = _registros()
    funai = _da("FUNAI", registros)
    # `tis_poligonais` has `gid`; `aldeias_pontos` has no candidate at all.
    assert funai["Funai:tis_poligonais"].propriedades == {
        "url": "https://geoserver.funai.gov.br/geoserver/ows",
        "typeName": "Funai:tis_poligonais",
        "version": "2.0.0",
        "sortBy": "gid",
    }
    assert "sortBy" not in funai["Funai:aldeias_pontos"].propriedades
    assert funai["Funai:aldeias_pontos"].esquema["geometry_type"] == "Point"


def test_ibge_is_wfs_1_0_0_and_the_slice_has_two_layers():
    registros, _ = _registros()
    ibge = _da("IBGE", registros)

    assert set(ibge) == {"APONDS:aponds_ibge", "APONDS:aponds_prefeitura"}
    fonte = ibge["APONDS:aponds_ibge"]
    assert fonte.versao == "1.0.0"
    assert fonte.propriedades["version"] == "1.0.0"
    assert fonte.propriedades["sortBy"] == "id"
    assert fonte.esquema["geometry_type"] == "MultiPolygon"  # gml:MultiPolygonPropertyType
    assert fonte.esquema["geometry_column"] == "geom_ibge"
    assert fonte.grupo == "APONDS"


def test_arcgis_and_placeholder_are_ignored_with_reason():
    _, ignoradas = _registros()
    by_folder = {i.pasta: i.motivo for i in ignoradas}
    assert by_folder["EUA TIGERweb"] == "sem_endpoint_wfs"
    assert by_folder["Dominica DomiNode"] == "sem_endpoint_wfs"
    # And nothing from the ArcGIS folder became a record by mistake.
    registros, _ = _registros()
    assert not [r for r in registros if r.instituicao == "EUA TIGERweb"]


# ── The new format (optional, on top of today's) ──────────────────────────────


def test_frontmatter_tags_and_priority():
    registros, _ = _registros()
    exemplo = _da("Exemplo Novo", registros)

    focos = exemplo["queimadas:focos_24h"]
    assert focos.url == "https://geoserver.exemplo.gov.br/geoserver/ows"
    assert focos.titulo == "Focos de calor (24 h)"  # without the tags
    assert focos.prioridade == 1  # #preferida
    assert focos.coletada_em == "2026-09-19"
    for tema in ("EXEMPLO", "queimadas", "focos de calor", "BR", "MT"):
        assert tema in focos.temas, tema
    assert focos.temas.count("queimadas") == 1  # tag == group == theme: no duplication
    assert focos.propriedades["sortBy"] == "id"
    assert focos.dicas and "sortBy: id" in focos.dicas

    risco = exemplo["queimadas:risco_fogo"]
    assert risco.prioridade == 3  # #secundaria
    assert risco.titulo == "Risco de fogo — previsão diária"
    assert risco.esquema["geometry_type"] == "MultiPolygon"


def test_read_frontmatter_accepts_block_list_and_quoted_value():
    texto = '---\nsigla: "X Y"\ntemas:\n  - um\n  - "dois"\nprioridade: 1\n---\n# Título\n'
    campos, resto = fv.read_frontmatter(texto)
    assert campos == {"sigla": "X Y", "temas": ["um", "dois"], "prioridade": "1"}
    assert resto.startswith("# Título")


def test_without_frontmatter_returns_the_whole_text():
    campos, resto = fv.read_frontmatter("# Só um título\n")
    assert campos == {} and resto == "# Só um título\n"


def test_root_synonyms():
    synonyms = fv.synonyms_of(VAULT)
    assert synonyms["focos de calor"] == {"queimadas", "incêndio", "hotspot", "fogo"}
    assert synonyms["terra indígena"] == {"TI", "indígena", "aldeia"}
    assert synonyms["unidade de conservação"] == {"UC", "parque", "reserva"}
    assert fv.synonyms_of(VAULT / "nao-existe") == {}


# ── Edge cases ────────────────────────────────────────────────────────────────


def _minimal_folder(raiz: Path, nome: str, endpoint: str, camadas: str | None = "- `a:b` — B\n") -> Path:
    pasta = raiz / nome
    pasta.mkdir(parents=True)
    (pasta / "Nota — SIGLA.md").write_text(
        f"# Nota — SIGLA\n\n- **Endpoint WFS:** <{endpoint}>\n", encoding="utf-8"
    )
    if camadas is not None:
        (pasta / "Camadas.md").write_text("# SIGLA — camadas\n\n## G (1)\n" + camadas, encoding="utf-8")
    return pasta


def test_nfd_folder_name_becomes_nfc(tmp_path):
    nfd = unicodedata.normalize("NFD", "Instituição")
    _minimal_folder(tmp_path, nfd, "https://h/ows")
    registros, _ = _registros(tmp_path)
    assert registros[0].instituicao == "Instituição"
    assert unicodedata.is_normalized("NFC", registros[0].instituicao)


def test_url_with_credential_is_refused(tmp_path):
    _minimal_folder(tmp_path, "Segredo", "https://user:senha@h/ows")  # pragma: allowlist secret
    registros, ignoradas = _registros(tmp_path)
    assert registros == []
    assert [(i.pasta, i.motivo) for i in ignoradas] == [("Segredo", "url_com_credencial")]


def test_endpoint_without_layers_is_ignored(tmp_path):
    _minimal_folder(tmp_path, "Vazia", "https://h/ows", camadas=None)
    _minimal_folder(tmp_path, "SoTitulo", "https://h/ows", camadas="nenhum bullet aqui\n")
    _, ignoradas = _registros(tmp_path)
    assert {(i.pasta, i.motivo) for i in ignoradas} == {("Vazia", "sem_camadas"), ("SoTitulo", "sem_camadas")}


def test_unreadable_note_does_not_break_the_read(tmp_path):
    pasta = _minimal_folder(tmp_path, "Quebrada", "https://h/ows")
    (pasta / "Camadas.md").write_bytes(b"\xff\xfe nao e utf-8")
    _minimal_folder(tmp_path, "Boa", "https://h/ows")
    registros, ignoradas = _registros(tmp_path)
    assert [r.instituicao for r in registros] == ["Boa"]
    assert [(i.pasta, i.motivo) for i in ignoradas] == [("Quebrada", "nota_ilegivel")]


def test_base_note_applies_only_when_named_note_has_no_endpoint(tmp_path):
    pasta = tmp_path / "Duas"
    pasta.mkdir()
    (pasta / "nota-base.md").write_text("# Duas\n\n**Endpoint WFS:** <https://base/ows>\n", encoding="utf-8")
    (pasta / "Nome — D.md").write_text("# Nome — D\n\n- **Finalidade:** sem endpoint aqui\n", encoding="utf-8")
    (pasta / "Camadas.md").write_text("## G (1)\n- `x:y` — Y\n", encoding="utf-8")
    registros, _ = _registros(tmp_path)
    assert registros[0].url == "https://base/ows"


def test_missing_folder_yields_nothing():
    assert list(fv.read_folder(VAULT / "nao-existe")) == []


def test_loose_files_at_root_are_skipped(tmp_path):
    shutil.copytree(VAULT / "FUNAI", tmp_path / "FUNAI")
    (tmp_path / "Índice.md").write_text("# Índice\n- **Endpoint WFS:** <https://x/ows>\n", encoding="utf-8")
    registros, ignoradas = _registros(tmp_path)
    assert len(registros) == 8 and ignoradas == []


def test_vault_hash_is_stable_and_content_sensitive(tmp_path):
    shutil.copytree(VAULT / "FUNAI", tmp_path / "FUNAI")
    antes = {r.type_name: r.vault_hash for r in _registros(tmp_path)[0]}
    assert antes == {r.type_name: r.vault_hash for r in _registros(tmp_path)[0]}

    camadas = tmp_path / "FUNAI" / "Camadas.md"
    camadas.write_text(
        camadas.read_text(encoding="utf-8").replace("Aldeias Indígenas (pontos)", "Aldeias (pontos)"),
        encoding="utf-8",
    )
    depois = {r.type_name: r.vault_hash for r in _registros(tmp_path)[0]}
    assert depois["Funai:aldeias_pontos"] != antes["Funai:aldeias_pontos"]
    assert depois["Funai:tis_poligonais"] == antes["Funai:tis_poligonais"]


@pytest.mark.parametrize(
    "xsd,esperado",
    [("gml:PointPropertyType", "Point"), ("gml:MultiSurfacePropertyType", "MultiPolygon"),
     ("gml:MultiCurvePropertyType", "MultiLineString"), ("gml:GeometryPropertyType", "Geometry"),
     ("gml:CoisaNova", "Geometry")],
)
def test_geometry_types(xsd, esperado):
    esquema = fv.read_attributes(f"### `a:b`\n\n| Campo | Tipo XSD | Nulo | Ocorrência |\n|---|---|---:|---|\n| `g` | `{xsd}` | true | 0..1 |\n")
    assert esquema["a:b"].geometry_type == esperado
    assert esquema["a:b"].geometry_column == "g"


def test_version_tolerates_forms():
    assert fv._version("WFS 1.1.0") == "1.1.0"
    assert fv._version("2.0") == "2.0.0"
    assert fv._version(None) == "2.0.0"
    assert fv._version("sem número") == "2.0.0"
