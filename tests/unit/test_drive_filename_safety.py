# tests/unit/test_drive_filename_safety.py
"""Sanitization of the Drive file name.

Two functions with distinct roles:
  - `sanitize_name`      -> strict ASCII slug, used in the S3 KEY.
  - `safe_display_name`  -> safe basename for `original_name`, the name the
    user sees AND that is propagated to the executor as the write target in GeoSync.

The mistake to avoid here is using the aggressive slug on `original_name`: it
would stop the traversal, but would destroy accents and spaces in every
legitimate name.
"""
from app.services.drive_service import safe_display_name, sanitize_name


# ── Traversal neutralizado ────────────────────────────────────────────────────

def test_relative_traversal_becomes_basename():
    assert safe_display_name("../../../etc/passwd.geojson") == "passwd.geojson"


def test_absolute_path_becomes_basename():
    assert safe_display_name("/etc/cron.d/x.geojson") == "x.geojson"
    assert safe_display_name("C:\\Windows\\system32\\x.geojson") == "x.geojson"


def test_degenerate_name_becomes_placeholder():
    assert safe_display_name("..") == "arquivo"
    assert safe_display_name(".") == "arquivo"
    assert safe_display_name("") == "arquivo"


def test_separators_do_not_survive():
    resultado = safe_display_name("pasta/sub/arquivo.shp")
    assert "/" not in resultado and "\\" not in resultado


# ── Nomes legitimos preservados ───────────────────────────────────────────────

def test_accents_and_spaces_are_preserved():
    """Regression: applying the ASCII slug here would turn this into
    '_rea_de_risco.gpkg' and degrade the UI with no security gain."""
    assert safe_display_name("área de risco.gpkg") == "área de risco.gpkg"
    assert safe_display_name("Munícipios SP 2024.geojson") == "Munícipios SP 2024.geojson"


def test_extension_preserved_in_name_with_leading_dots():
    """'..geojson' must not become 'geojson' — it would lose the extension and the
    upload would be rejected for 'arquivo sem extensao' (file without extension)."""
    assert safe_display_name("..geojson").endswith(".geojson")


# ── Content-Disposition ───────────────────────────────────────────────────────

def test_quotes_semicolons_and_control_chars_are_neutralized():
    """These go into `Content-Disposition: attachment; filename="..."` in the presigned GET."""
    assert '"' not in safe_display_name('rel"atorio.csv')
    assert ";" not in safe_display_name("rel;atorio.csv")
    assert "\n" not in safe_display_name("rel\natorio.csv")


# ── Slug da chave S3 mantem o comportamento estrito ───────────────────────────

def test_sanitize_name_stays_strict_slug():
    assert sanitize_name("área de risco.gpkg") == "_rea_de_risco.gpkg"
    assert sanitize_name("../../etc/passwd") == "passwd"
