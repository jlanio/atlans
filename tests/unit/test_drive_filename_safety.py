# tests/unit/test_drive_filename_safety.py
"""Sanitizacao do nome de arquivo do Drive.

Duas funcoes com papeis distintos:
  - `sanitize_name`      -> slug ASCII estrito, usado na CHAVE S3.
  - `safe_display_name`  -> basename seguro para `original_name`, o nome que o
    usuario ve E que e propagado ao executor como destino de escrita no GeoSync.

O erro a evitar aqui e usar o slug agressivo no `original_name`: seguraria o
traversal, mas destruiria acentos e espacos de todo nome legitimo.
"""
from app.services.drive_service import safe_display_name, sanitize_name


# ── Traversal neutralizado ────────────────────────────────────────────────────

def test_traversal_relativo_vira_basename():
    assert safe_display_name("../../../etc/passwd.geojson") == "passwd.geojson"


def test_caminho_absoluto_vira_basename():
    assert safe_display_name("/etc/cron.d/x.geojson") == "x.geojson"
    assert safe_display_name("C:\\Windows\\system32\\x.geojson") == "x.geojson"


def test_nome_degenerado_vira_placeholder():
    assert safe_display_name("..") == "arquivo"
    assert safe_display_name(".") == "arquivo"
    assert safe_display_name("") == "arquivo"


def test_separadores_nao_sobrevivem():
    resultado = safe_display_name("pasta/sub/arquivo.shp")
    assert "/" not in resultado and "\\" not in resultado


# ── Nomes legitimos preservados ───────────────────────────────────────────────

def test_acentos_e_espacos_sao_preservados():
    """Regressao: aplicar o slug ASCII aqui transformaria isto em
    '_rea_de_risco.gpkg' e degradaria a UI sem ganho de seguranca."""
    assert safe_display_name("área de risco.gpkg") == "área de risco.gpkg"
    assert safe_display_name("Munícipios SP 2024.geojson") == "Munícipios SP 2024.geojson"


def test_extensao_preservada_em_nome_com_pontos_iniciais():
    """'..geojson' nao pode virar 'geojson' — perderia a extensao e o upload
    seria rejeitado por 'arquivo sem extensao'."""
    assert safe_display_name("..geojson").endswith(".geojson")


# ── Content-Disposition ───────────────────────────────────────────────────────

def test_aspas_ponto_e_virgula_e_controle_sao_neutralizados():
    """Vao para `Content-Disposition: attachment; filename="..."` no presigned GET."""
    assert '"' not in safe_display_name('rel"atorio.csv')
    assert ";" not in safe_display_name("rel;atorio.csv")
    assert "\n" not in safe_display_name("rel\natorio.csv")


# ── Slug da chave S3 mantem o comportamento estrito ───────────────────────────

def test_sanitize_name_continua_slug_estrito():
    assert sanitize_name("área de risco.gpkg") == "_rea_de_risco.gpkg"
    assert sanitize_name("../../etc/passwd") == "passwd"
