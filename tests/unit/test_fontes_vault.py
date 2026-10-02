# tests/unit/test_fontes_vault.py
"""O parser do Vault: o markdown do Obsidian vira registros do catálogo.

As fixtures em `tests/fixtures/vault/` são cópias REAIS do Vault do dono
(FUNAI inteira; um recorte do IBGE, que é WFS 1.0.0; um recorte do TIGERweb,
que é ArcGIS; o placeholder da Dominica) mais uma pasta no formato NOVO —
frontmatter, tags inline e `_sinonimos.md` — que é o que este parser passa a
aceitar por cima do formato de hoje.
"""
from __future__ import annotations

import shutil
import unicodedata
from pathlib import Path

import pytest

from app.services import fontes_vault as fv

VAULT = Path(__file__).resolve().parents[1] / "fixtures" / "vault"


def _registros(pasta=VAULT):
    itens = list(fv.ler_pasta(pasta))
    return (
        [r for r in itens if isinstance(r, fv.RegistroDoVault)],
        [i for i in itens if isinstance(i, fv.Ignorada)],
    )


def _da(instituicao, registros):
    return {r.type_name: r for r in registros if r.instituicao == instituicao}


# ── O formato de hoje ─────────────────────────────────────────────────────────


def test_funai_inteira_vira_oito_camadas_com_esquema():
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


def test_sort_by_vem_da_primeira_coluna_de_id_que_existe():
    registros, _ = _registros()
    funai = _da("FUNAI", registros)
    # `tis_poligonais` tem `gid`; `aldeias_pontos` não tem nenhum candidato.
    assert funai["Funai:tis_poligonais"].propriedades == {
        "url": "https://geoserver.funai.gov.br/geoserver/ows",
        "typeName": "Funai:tis_poligonais",
        "version": "2.0.0",
        "sortBy": "gid",
    }
    assert "sortBy" not in funai["Funai:aldeias_pontos"].propriedades
    assert funai["Funai:aldeias_pontos"].esquema["geometry_type"] == "Point"


def test_ibge_e_wfs_1_0_0_e_o_recorte_tem_duas_camadas():
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


def test_arcgis_e_placeholder_sao_ignorados_com_motivo():
    _, ignoradas = _registros()
    por_pasta = {i.pasta: i.motivo for i in ignoradas}
    assert por_pasta["EUA TIGERweb"] == "sem_endpoint_wfs"
    assert por_pasta["Dominica DomiNode"] == "sem_endpoint_wfs"
    # E nada da pasta ArcGIS virou registro por engano.
    registros, _ = _registros()
    assert not [r for r in registros if r.instituicao == "EUA TIGERweb"]


# ── O formato novo (opcional, por cima do de hoje) ────────────────────────────


def test_frontmatter_tags_e_prioridade():
    registros, _ = _registros()
    exemplo = _da("Exemplo Novo", registros)

    focos = exemplo["queimadas:focos_24h"]
    assert focos.url == "https://geoserver.exemplo.gov.br/geoserver/ows"
    assert focos.titulo == "Focos de calor (24 h)"  # sem as tags
    assert focos.prioridade == 1  # #preferida
    assert focos.coletada_em == "2026-09-19"
    for tema in ("EXEMPLO", "queimadas", "focos de calor", "BR", "MT"):
        assert tema in focos.temas, tema
    assert focos.temas.count("queimadas") == 1  # tag == grupo == tema: sem duplicar
    assert focos.propriedades["sortBy"] == "id"
    assert focos.dicas and "sortBy: id" in focos.dicas

    risco = exemplo["queimadas:risco_fogo"]
    assert risco.prioridade == 3  # #secundaria
    assert risco.titulo == "Risco de fogo — previsão diária"
    assert risco.esquema["geometry_type"] == "MultiPolygon"


def test_ler_frontmatter_aceita_lista_em_bloco_e_valor_entre_aspas():
    texto = '---\nsigla: "X Y"\ntemas:\n  - um\n  - "dois"\nprioridade: 1\n---\n# Título\n'
    campos, resto = fv.ler_frontmatter(texto)
    assert campos == {"sigla": "X Y", "temas": ["um", "dois"], "prioridade": "1"}
    assert resto.startswith("# Título")


def test_sem_frontmatter_devolve_o_texto_inteiro():
    campos, resto = fv.ler_frontmatter("# Só um título\n")
    assert campos == {} and resto == "# Só um título\n"


def test_sinonimos_da_raiz():
    sinonimos = fv.sinonimos_de(VAULT)
    assert sinonimos["focos de calor"] == {"queimadas", "incêndio", "hotspot", "fogo"}
    assert sinonimos["terra indígena"] == {"TI", "indígena", "aldeia"}
    assert sinonimos["unidade de conservação"] == {"UC", "parque", "reserva"}
    assert fv.sinonimos_de(VAULT / "nao-existe") == {}


# ── Casos de borda ────────────────────────────────────────────────────────────


def _pasta_minima(raiz: Path, nome: str, endpoint: str, camadas: str | None = "- `a:b` — B\n") -> Path:
    pasta = raiz / nome
    pasta.mkdir(parents=True)
    (pasta / "Nota — SIGLA.md").write_text(
        f"# Nota — SIGLA\n\n- **Endpoint WFS:** <{endpoint}>\n", encoding="utf-8"
    )
    if camadas is not None:
        (pasta / "Camadas.md").write_text("# SIGLA — camadas\n\n## G (1)\n" + camadas, encoding="utf-8")
    return pasta


def test_nome_de_pasta_em_nfd_vira_nfc(tmp_path):
    nfd = unicodedata.normalize("NFD", "Instituição")
    _pasta_minima(tmp_path, nfd, "https://h/ows")
    registros, _ = _registros(tmp_path)
    assert registros[0].instituicao == "Instituição"
    assert unicodedata.is_normalized("NFC", registros[0].instituicao)


def test_url_com_credencial_e_recusada(tmp_path):
    _pasta_minima(tmp_path, "Segredo", "https://user:senha@h/ows")  # pragma: allowlist secret
    registros, ignoradas = _registros(tmp_path)
    assert registros == []
    assert [(i.pasta, i.motivo) for i in ignoradas] == [("Segredo", "url_com_credencial")]


def test_endpoint_sem_camadas_e_ignorado(tmp_path):
    _pasta_minima(tmp_path, "Vazia", "https://h/ows", camadas=None)
    _pasta_minima(tmp_path, "SoTitulo", "https://h/ows", camadas="nenhum bullet aqui\n")
    _, ignoradas = _registros(tmp_path)
    assert {(i.pasta, i.motivo) for i in ignoradas} == {("Vazia", "sem_camadas"), ("SoTitulo", "sem_camadas")}


def test_nota_ilegivel_nao_derruba_a_leitura(tmp_path):
    pasta = _pasta_minima(tmp_path, "Quebrada", "https://h/ows")
    (pasta / "Camadas.md").write_bytes(b"\xff\xfe nao e utf-8")
    _pasta_minima(tmp_path, "Boa", "https://h/ows")
    registros, ignoradas = _registros(tmp_path)
    assert [r.instituicao for r in registros] == ["Boa"]
    assert [(i.pasta, i.motivo) for i in ignoradas] == [("Quebrada", "nota_ilegivel")]


def test_nota_base_so_vale_quando_a_nota_nomeada_nao_tem_endpoint(tmp_path):
    pasta = tmp_path / "Duas"
    pasta.mkdir()
    (pasta / "nota-base.md").write_text("# Duas\n\n**Endpoint WFS:** <https://base/ows>\n", encoding="utf-8")
    (pasta / "Nome — D.md").write_text("# Nome — D\n\n- **Finalidade:** sem endpoint aqui\n", encoding="utf-8")
    (pasta / "Camadas.md").write_text("## G (1)\n- `x:y` — Y\n", encoding="utf-8")
    registros, _ = _registros(tmp_path)
    assert registros[0].url == "https://base/ows"


def test_pasta_inexistente_nao_gera_nada():
    assert list(fv.ler_pasta(VAULT / "nao-existe")) == []


def test_arquivos_soltos_na_raiz_sao_pulados(tmp_path):
    shutil.copytree(VAULT / "FUNAI", tmp_path / "FUNAI")
    (tmp_path / "Índice.md").write_text("# Índice\n- **Endpoint WFS:** <https://x/ows>\n", encoding="utf-8")
    registros, ignoradas = _registros(tmp_path)
    assert len(registros) == 8 and ignoradas == []


def test_vault_hash_e_estavel_e_sensivel_ao_conteudo(tmp_path):
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
def test_tipos_de_geometria(xsd, esperado):
    esquema = fv.ler_atributos(f"### `a:b`\n\n| Campo | Tipo XSD | Nulo | Ocorrência |\n|---|---|---:|---|\n| `g` | `{xsd}` | true | 0..1 |\n")
    assert esquema["a:b"].geometry_type == esperado
    assert esquema["a:b"].geometry_column == "g"


def test_versao_tolera_formas():
    assert fv._versao("WFS 1.1.0") == "1.1.0"
    assert fv._versao("2.0") == "2.0.0"
    assert fv._versao(None) == "2.0.0"
    assert fv._versao("sem número") == "2.0.0"
