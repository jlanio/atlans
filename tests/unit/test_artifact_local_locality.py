# tests/unit/test_artifact_local_locality.py
"""
Localidade de conteudo de artefatos (LGPD).

Um artefato marcado como local nasce e permanece no disco do executor. O servidor
guarda so o catalogo. Estes testes travam as tres propriedades que fazem isso
valer alguma coisa:

  NAO SAI       `save_artifact_local` nao faz UMA chamada HTTP. Se fizer, o dado
                que foi marcado para nao sair saiu.

  NAO SOME      resolver um artefato local NAO pode apagar o arquivo original.
                `read_drive_file_as` faz `os.unlink` no `finally` porque ate
                entao o caminho era sempre um temporario baixado — devolver o
                arquivo real faria o primeiro workflow que o lesse destruir o
                dado do cliente, em silencio.

  NAO ESCAPA    `local_path` viaja pela rede. Um `../` nao pode virar leitura de
                arquivo arbitrario da maquina.
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
    """O teste central da politica: nenhum byte pode sair da maquina."""
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
    """Se a gravacao local falhar, a excecao SOBE.

    Cair para o upload seria enviar para a nuvem exatamente o dado que foi
    marcado para nao sair — o oposto do que a falha deveria provocar.
    """
    def sem_escrita(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(artifact_helpers, "_write_local", sem_escrita)
    with pytest.raises(OSError):
        artifact_helpers.save_artifact_local(
            content=b"x", filename="a.json", workspace_id="ws-1", task_id="run-1",
        )


def test_local_nao_e_confundido_com_fallback_de_falha(artefatos):
    """`local_fallback` significa "o upload quebrou"; `content_location` significa
    "foi decidido que fica aqui". Misturar os dois faria uma queda de rede virar
    conformidade silenciosa no registro do servidor."""
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
    """A armadilha do `os.unlink`.

    O caller (`read_drive_file_as`) apaga o caminho devolvido. Se resolvessemos
    para o arquivo real, o primeiro workflow a le-lo destruiria o dado.
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

        # Simula o que o caller faz com o caminho devolvido.
        os.unlink(temp)
        assert original.is_file(), "o arquivo do usuario foi apagado pela leitura"
        assert original.read_bytes() == b"conteudo importante"
    finally:
        Path(temp).unlink(missing_ok=True)


def test_artefato_de_outro_executor_da_erro_nomeado(artefatos):
    """Nao pode ser um FileNotFoundError cru: o operador precisa saber que o
    arquivo esta em OUTRA maquina, e nao procurar um arquivo perdido."""
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
    """`local_path` chega pela rede. O servidor o deriva, mas depender disso
    seria terceirizar a propria seguranca."""
    with pytest.raises(PermissionError):
        drive_resolver._copy_local_to_temp(malicioso, "exec-1", "", "x")


def test_local_path_vazio_da_mensagem_util(artefatos):
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._copy_local_to_temp("", "exec-1", "", "saida.geojson")
    assert "caminho" in str(exc.value).lower()


def test_raiz_dos_artefatos_e_a_mesma_na_escrita_e_na_leitura(artefatos):
    """Escrita e leitura precisam concordar sobre onde os arquivos moram; se
    divergirem, todo artefato local vira 'nao encontrado'."""
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
