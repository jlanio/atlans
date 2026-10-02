# tests/unit/test_geosync_catalogo.py
"""
GeoSync em modo catalogo (LGPD).

O executor registra o dataset no Drive — nome, tipo, tamanho, CRS, bbox — e os
bytes NUNCA saem da pasta do usuario. Na leitura, o executor reencontra o
arquivo pelo proprio `.atlans-sync.json`.

O ponto de desenho que estes testes protegem: **nenhum caminho de sistema de
arquivos trafega pela rede**. O servidor guarda que o arquivo e local e de qual
executor, e nada mais. Isso elimina de saida a classe de ataque de path
traversal que o caminho de artefatos precisa tratar explicitamente.
"""
import json
from pathlib import Path

import pytest

from flow.utils import drive_resolver


def _manifesto(pasta: Path, datasets: dict) -> None:
    (pasta / ".atlans-sync.json").write_text(
        json.dumps({"version": 1, "datasets": datasets}), encoding="utf-8",
    )


@pytest.fixture
def sync_dir(tmp_path, monkeypatch):
    pasta = tmp_path / "GeoDados"
    pasta.mkdir()
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", str(pasta))
    return pasta


# ── Resolucao pelo manifesto ─────────────────────────────────────────────────

def test_resolve_dataset_de_arquivo_unico(sync_dir):
    (sync_dir / "parcelas.geojson").write_bytes(b'{"type":"FeatureCollection"}')
    _manifesto(sync_dir, {
        "parcelas": {
            "type": "geojson", "remote_id_hash": "id-1",
            "files": {"parcelas.geojson": {"md5": "x"}},
        },
    })

    temp, ext, nome = drive_resolver._resolve_do_manifesto_de_sync(
        "id-1", "exec-1", "geojson", "parcelas.geojson",
    )
    try:
        assert Path(temp).read_bytes() == b'{"type":"FeatureCollection"}'
        assert ext == "geojson" and nome == "parcelas.geojson"
    finally:
        Path(temp).unlink(missing_ok=True)


def test_shapefile_resolve_para_o_shp_e_nao_para_outro_componente(sync_dir):
    """Um shapefile e um bundle. Devolver o `.dbf` faria o ReadShapefile falhar
    de forma incompreensivel — o `primary_path` do scanner escolhe o `.shp`, e
    esta resolucao precisa concordar com ele."""
    for ext, conteudo in (("shp", b"GEOMETRIA"), ("dbf", b"ATRIBUTOS"), ("shx", b"INDICE")):
        (sync_dir / f"lotes.{ext}").write_bytes(conteudo)
    _manifesto(sync_dir, {
        "lotes": {
            "type": "shapefile", "remote_id_hash": "id-2",
            # Ordem proposital: o .dbf vem primeiro para provar que a escolha
            # nao e "o primeiro do dicionario".
            "files": {"lotes.dbf": {}, "lotes.shp": {}, "lotes.shx": {}},
        },
    })

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync(
        "id-2", "exec-1", "shp", "lotes.zip",
    )
    try:
        assert Path(temp).read_bytes() == b"GEOMETRIA"
    finally:
        Path(temp).unlink(missing_ok=True)


def test_copia_e_nao_devolve_o_arquivo_do_usuario(sync_dir):
    """Mesma armadilha do caminho de artefatos: o caller apaga o que recebe."""
    import os

    original = sync_dir / "dados.geojson"
    original.write_bytes(b"conteudo")
    _manifesto(sync_dir, {
        "dados": {"type": "geojson", "remote_id_hash": "id-3",
                  "files": {"dados.geojson": {}}},
    })

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync(
        "id-3", "exec-1", "geojson", "dados.geojson",
    )
    assert Path(temp) != original
    os.unlink(temp)                       # o que `read_drive_file_as` faz
    assert original.is_file(), "o arquivo do usuario foi apagado pela leitura"


def test_procura_em_todas_as_pastas_configuradas(tmp_path, monkeypatch):
    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir(), b.mkdir()
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", f"{a},{b}")

    _manifesto(a, {"outro": {"type": "geojson", "remote_id_hash": "id-x",
                             "files": {"outro.geojson": {}}}})
    (b / "alvo.geojson").write_bytes(b"achei")
    _manifesto(b, {"alvo": {"type": "geojson", "remote_id_hash": "id-4",
                            "files": {"alvo.geojson": {}}}})

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync(
        "id-4", "exec-1", "geojson", "alvo.geojson",
    )
    try:
        assert Path(temp).read_bytes() == b"achei"
    finally:
        Path(temp).unlink(missing_ok=True)


# ── Erros com causa ──────────────────────────────────────────────────────────

def test_dataset_de_outro_executor_da_erro_explicativo(sync_dir):
    _manifesto(sync_dir, {})
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._resolve_do_manifesto_de_sync(
            "id-inexistente", "exec-remoto", "geojson", "parcelas.geojson",
        )
    msg = str(exc.value)
    assert "exec-remoto" in msg
    assert "catalogo" in msg.lower() or "catálogo" in msg.lower()


def test_sem_pastas_de_sync_explica_o_que_falta(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", "")
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._resolve_do_manifesto_de_sync("id-1", "exec-1", "", "x.geojson")
    assert "EXECUTOR_SYNC_DIRS" in str(exc.value)


def test_arquivo_removido_do_disco_da_erro_distinto(sync_dir):
    """Manifesto conhece o dataset, mas o arquivo sumiu — diagnostico diferente
    de 'esta em outra maquina'."""
    _manifesto(sync_dir, {
        "sumido": {"type": "geojson", "remote_id_hash": "id-5",
                   "files": {"sumido.geojson": {}}},
    })
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._resolve_do_manifesto_de_sync("id-5", "exec-1", "geojson", "sumido.geojson")
    assert "movido ou apagado" in str(exc.value)


def test_manifesto_corrompido_nao_derruba_a_busca(tmp_path, monkeypatch):
    """Uma pasta com manifesto ilegivel nao pode impedir de achar nas outras."""
    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir(), b.mkdir()
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", f"{a},{b}")

    (a / ".atlans-sync.json").write_text("{{{ nao e json", encoding="utf-8")
    (b / "ok.geojson").write_bytes(b"ok")
    _manifesto(b, {"ok": {"type": "geojson", "remote_id_hash": "id-6",
                          "files": {"ok.geojson": {}}}})

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync("id-6", "exec-1", "geojson", "ok.geojson")
    try:
        assert Path(temp).read_bytes() == b"ok"
    finally:
        Path(temp).unlink(missing_ok=True)


# ── Escolha do arquivo principal ─────────────────────────────────────────────

def test_dataset_sem_arquivos_no_manifesto(sync_dir):
    assert drive_resolver._arquivo_principal(sync_dir, {"type": "geojson", "files": {}}) is None


def test_shapefile_sem_shp_no_bundle(sync_dir):
    """Bundle incompleto: melhor None (que vira erro nomeado) do que devolver o
    `.dbf` e falhar dentro do geopandas."""
    ds = {"type": "shapefile", "files": {"lotes.dbf": {}, "lotes.shx": {}}}
    assert drive_resolver._arquivo_principal(sync_dir, ds) is None
