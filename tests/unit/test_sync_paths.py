# tests/unit/test_sync_paths.py
"""Path containment in GeoSync.

Regression: `original_name` comes from the server (typed by a user in the Drive
upload) and was used directly as `sync_dir / original_name` in the download. A
name with `../` or an absolute one escaped the sync directory = arbitrary file
write on the executor's host.
"""
import pytest

from executor.sync.paths import UnsafePathError, safe_join, safe_join_or_none


@pytest.fixture
def sync_dir(tmp_path):
    d = tmp_path / "geosync"
    d.mkdir()
    return d


# ── Casos legitimos ───────────────────────────────────────────────────────────

def test_nome_simples_resolve_dentro_da_base(sync_dir):
    dest = safe_join(sync_dir, "municipios.geojson")
    assert dest == (sync_dir / "municipios.geojson").resolve()
    assert sync_dir.resolve() in dest.parents


def test_nome_com_espacos_e_acentos(sync_dir):
    dest = safe_join(sync_dir, "área de risco.gpkg")
    assert dest.name == "área de risco.gpkg"


# ── Traversal ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nome", [
    "../fora.geojson",
    "../../../../etc/passwd.geojson",
    "subdir/arquivo.geojson",
    "..\\..\\windows\\system32\\x.geojson",
    "pasta\\arquivo.geojson",
])
def test_traversal_e_rejeitado(sync_dir, nome):
    with pytest.raises(UnsafePathError):
        safe_join(sync_dir, nome)


@pytest.mark.parametrize("nome", ["/etc/cron.d/x.geojson", "C:\\Windows\\x.geojson"])
def test_caminho_absoluto_e_rejeitado(sync_dir, nome):
    with pytest.raises(UnsafePathError):
        safe_join(sync_dir, nome)


@pytest.mark.parametrize("nome", ["", ".", ".."])
def test_nomes_degenerados_sao_rejeitados(sync_dir, nome):
    with pytest.raises(UnsafePathError):
        safe_join(sync_dir, nome)


def test_symlink_apontando_para_fora_e_rejeitado(sync_dir, tmp_path):
    """resolve() segue o symlink — o destino real e que decide."""
    alvo = tmp_path / "fora"
    alvo.mkdir()
    link = sync_dir / "atalho.geojson"
    try:
        link.symlink_to(alvo / "arquivo.geojson")
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    with pytest.raises(UnsafePathError):
        safe_join(sync_dir, "atalho.geojson")


# ── Non-raising variant used in the sync loops ────────────────────────────────

def test_safe_join_or_none_devolve_none_em_vez_de_levantar(sync_dir):
    assert safe_join_or_none(sync_dir, "../fora.geojson") is None
    assert safe_join_or_none(sync_dir, "ok.geojson") is not None
