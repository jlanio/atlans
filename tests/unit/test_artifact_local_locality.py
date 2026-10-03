# tests/unit/test_artifact_local_locality.py
"""
Content locality of artifacts (LGPD).

An artifact marked as local is born and stays on the executor's disk. The server
keeps only the catalog. These tests lock down the three properties that make
this worth anything:

  DOESN'T LEAVE    `save_artifact_local` does not make ONE HTTP call. If it does,
                   the data that was marked not to leave has left.

  DOESN'T VANISH   resolving a local artifact must NOT delete the original file.
                   `read_drive_file_as` does `os.unlink` in the `finally` because
                   until now the path was always a downloaded temporary file —
                   returning the real file would make the first workflow that read
                   it destroy the customer's data, silently.

  DOESN'T ESCAPE   `local_path` travels over the network. A `../` must not turn
                   into reading an arbitrary file on the machine.
"""
import os
from pathlib import Path

import pytest

from flow.utils import artifact_helpers, drive_resolver


@pytest.fixture
def artefatos(tmp_path, monkeypatch):
    """Aponta EXECUTOR_ARTIFACTS_DIR para um diretorio temporario."""
    raiz = tmp_path / "artifacts"
    raiz.mkdir()
    monkeypatch.setenv("EXECUTOR_ARTIFACTS_DIR", str(raiz))
    return raiz


# ── Escrita ──────────────────────────────────────────────────────────────────

def test_save_artifact_local_grava_no_disco(artefatos):
    chave, meta = artifact_helpers.save_artifact_local(
        content=b'{"tipo":"teste"}', filename="saida.geojson",
        workspace_id="ws-1", task_id="run-9", label="Saida", fmt="geojson", features=3,
    )

    destino = artefatos / "ws-1" / "run-9" / "saida.geojson"
    assert destino.read_bytes() == b'{"tipo":"teste"}'
    assert chave == "ws-1/run-9/saida.geojson"
    assert meta["content_location"] == "executor"
    assert meta["local_path"] == "ws-1/run-9/saida.geojson"
    assert meta["size_bytes"] == 16
    assert meta["features"] == 3


def test_save_artifact_local_nao_faz_nenhuma_chamada_http(artefatos, monkeypatch):
    """The central test of the policy: not a single byte may leave the machine."""
    import httpx

    def explode(*a, **k):
        raise AssertionError("save_artifact_local NAO pode falar com a rede")

    for nome in ("post", "put", "get", "request", "stream"):
        monkeypatch.setattr(httpx, nome, explode, raising=False)
    monkeypatch.setattr(httpx, "Client", explode)

    artifact_helpers.save_artifact_local(
        content=b"x", filename="a.json", workspace_id="ws-1", task_id="run-1",
    )


def test_save_artifact_local_nao_tem_fallback_para_upload(artefatos, monkeypatch):
    """If the local write fails, the exception PROPAGATES.

    Falling back to the upload would send to the cloud exactly the data that was
    marked not to leave — the opposite of what the failure should cause.
    """
    def sem_escrita(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(artifact_helpers, "_write_local", sem_escrita)
    with pytest.raises(OSError):
        artifact_helpers.save_artifact_local(
            content=b"x", filename="a.json", workspace_id="ws-1", task_id="run-1",
        )


def test_local_nao_e_confundido_com_fallback_de_falha(artefatos):
    """`local_fallback` means "the upload broke"; `content_location` means
    "it was decided that it stays here". Mixing the two would turn a network
    outage into silent compliance in the server's records."""
    _, meta = artifact_helpers.save_artifact_local(
        content=b"x", filename="a.json", workspace_id="ws-1", task_id="run-1",
    )
    assert meta["local_fallback"] is False
    assert meta["content_location"] == "executor"
    assert meta["s3_key"] is None


# ── Leitura ──────────────────────────────────────────────────────────────────

def _resposta_local(local_path: str, dono: str = "exec-1") -> dict:
    return {
        "content_location": "executor",
        "executor_id": dono,
        "local_path": local_path,
        "original_name": "saida.geojson",
        "extension": "geojson",
    }


def test_resolver_local_devolve_copia_e_NAO_apaga_o_original(artefatos):
    """The `os.unlink` pitfall.

    The caller (`read_drive_file_as`) deletes the returned path. If we resolved
    to the real file, the first workflow to read it would destroy the data.
    """
    original = artefatos / "ws-1" / "run-9" / "saida.geojson"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"conteudo importante")

    temp, ext, nome = drive_resolver._copy_local_to_temp(
        "ws-1/run-9/saida.geojson", "exec-1", "geojson", "saida.geojson",
    )
    try:
        assert Path(temp) != original
        assert Path(temp).read_bytes() == b"conteudo importante"
        assert ext == "geojson" and nome == "saida.geojson"

        # Simulates what the caller does with the returned path.
        os.unlink(temp)
        assert original.is_file(), "o arquivo do usuario foi apagado pela leitura"
        assert original.read_bytes() == b"conteudo importante"
    finally:
        Path(temp).unlink(missing_ok=True)


def test_artefato_de_outro_executor_da_erro_nomeado(artefatos):
    """It must not be a raw FileNotFoundError: the operator needs to know that the
    file is on ANOTHER machine, and not go looking for a lost file."""
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._copy_local_to_temp(
            "ws-1/run-9/ausente.geojson", "exec-outro", "geojson", "ausente.geojson",
        )
    msg = str(exc.value)
    assert "exec-outro" in msg
    assert "executor" in msg.lower()


@pytest.mark.parametrize("malicioso", [
    "../../../../etc/passwd",
    "ws-1/../../../windows/system32/config/sam",
    "ws-1/run-9/../../../../segredo.txt",
])
def test_path_traversal_no_local_path_e_barrado(artefatos, malicioso):
    """`local_path` arrives over the network. The server derives it, but relying on
    that would be outsourcing our own security."""
    with pytest.raises(PermissionError):
        drive_resolver._copy_local_to_temp(malicioso, "exec-1", "", "x")


def test_local_path_vazio_da_mensagem_util(artefatos):
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._copy_local_to_temp("", "exec-1", "", "saida.geojson")
    assert "caminho" in str(exc.value).lower()


def test_raiz_dos_artefatos_e_a_mesma_na_escrita_e_na_leitura(artefatos):
    """Writing and reading must agree on where the files live; if they diverge,
    every local artifact becomes 'not found'."""
    artifact_helpers.save_artifact_local(
        content=b"z", filename="b.json", workspace_id="ws-2", task_id="run-2",
    )
    temp, _, _ = drive_resolver._copy_local_to_temp(
        "ws-2/run-2/b.json", "exec-1", "json", "b.json",
    )
    try:
        assert Path(temp).read_bytes() == b"z"
    finally:
        Path(temp).unlink(missing_ok=True)
