# tests/unit/test_artifact_purge.py
"""
Remocao de artefatos locais por ordem do servidor.

Isto apaga arquivo do disco do usuario a partir de uma mensagem que chega pela
REDE. O `connection.py` so aceita `control` com assinatura Ed25519 valida, mas
a assinatura garante QUEM mandou, nao que o conteudo esteja correto — um bug de
derivacao de caminho no servidor, ou um servidor comprometido, viraria perda de
dados na maquina do cliente.

Por isso o caminho e tratado como entrada hostil, e e o que estes casos travam.
"""
from pathlib import Path

import pytest

from executor import artifact_purge


@pytest.fixture
def artefatos(tmp_path, monkeypatch):
    raiz = tmp_path / "artifacts"
    raiz.mkdir()
    monkeypatch.setenv("EXECUTOR_ARTIFACTS_DIR", str(raiz))
    return raiz


def _criar(raiz: Path, rel: str, conteudo: bytes = b"x") -> Path:
    alvo = raiz / rel
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(conteudo)
    return alvo


# ── Caminho feliz ────────────────────────────────────────────────────────────

def test_remove_o_arquivo_pedido(artefatos):
    alvo = _criar(artefatos, "ws-1/run-1/saida.geojson")

    n = artifact_purge.purgar([{"id_hash": "a1", "local_path": "ws-1/run-1/saida.geojson"}])

    assert n == 1
    assert not alvo.exists()


def test_remove_varios_de_uma_vez(artefatos):
    _criar(artefatos, "ws-1/run-1/a.json")
    _criar(artefatos, "ws-1/run-2/b.json")

    n = artifact_purge.purgar([
        {"id_hash": "a", "local_path": "ws-1/run-1/a.json"},
        {"id_hash": "b", "local_path": "ws-1/run-2/b.json"},
    ])
    assert n == 2


def test_diretorios_vazios_sao_removidos(artefatos):
    """Sem isso, `artifacts/` acumula uma arvore vazia por execucao, para sempre."""
    _criar(artefatos, "ws-1/run-1/a.json")
    artifact_purge.purgar([{"id_hash": "a", "local_path": "ws-1/run-1/a.json"}])

    assert not (artefatos / "ws-1" / "run-1").exists()
    assert not (artefatos / "ws-1").exists()
    assert artefatos.exists(), "a raiz de artefatos nunca pode ser removida"


def test_diretorio_com_outros_arquivos_e_preservado(artefatos):
    _criar(artefatos, "ws-1/run-1/a.json")
    _criar(artefatos, "ws-1/run-1/b.json")

    artifact_purge.purgar([{"id_hash": "a", "local_path": "ws-1/run-1/a.json"}])
    assert (artefatos / "ws-1" / "run-1" / "b.json").is_file()


def test_arquivo_ja_ausente_nao_e_erro(artefatos):
    """Ordem repetida, ou arquivo apagado a mao: nao ha o que corrigir."""
    assert artifact_purge.purgar([{"id_hash": "a", "local_path": "ws-1/run-1/sumiu.json"}]) == 0


# ── Travessia de caminho ─────────────────────────────────────────────────────

@pytest.mark.parametrize("malicioso", [
    "../../../etc/passwd",
    "..\\..\\..\\Windows\\System32\\config\\SAM",
    "ws-1/../../fora.txt",
    "ws-1/run-1/../../../../fora.txt",
    "/etc/passwd",
    "C:\\Windows\\System32\\drivers\\etc\\hosts",
    "/absoluto/qualquer",
])
def test_caminho_que_escapa_da_raiz_e_recusado(artefatos, tmp_path, malicioso):
    vitima = tmp_path / "fora.txt"
    vitima.write_bytes(b"nao me apague")

    n = artifact_purge.purgar([{"id_hash": "x", "local_path": malicioso}])

    assert n == 0
    assert vitima.read_bytes() == b"nao me apague"


def test_caminho_recusado_nao_impede_os_demais(artefatos):
    """Uma entrada hostil no lote nao pode abortar a limpeza legitima."""
    ok = _criar(artefatos, "ws-1/run-1/ok.json")

    n = artifact_purge.purgar([
        {"id_hash": "mau", "local_path": "../../fora.txt"},
        {"id_hash": "bom", "local_path": "ws-1/run-1/ok.json"},
    ])
    assert n == 1
    assert not ok.exists()


def test_symlink_apontando_para_fora_nao_apaga_o_alvo(artefatos, tmp_path):
    """A checagem textual nao pega symlink — quem pega e o `resolve()`."""
    vitima = tmp_path / "segredo.txt"
    vitima.write_bytes(b"dado")

    link = artefatos / "ws-1" / "run-1" / "link.json"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(vitima)
    except (OSError, NotImplementedError):
        pytest.skip("symlink exige privilegio no Windows sem Modo de Desenvolvedor")

    artifact_purge.purgar([{"id_hash": "s", "local_path": "ws-1/run-1/link.json"}])
    assert vitima.is_file(), "o alvo do symlink foi apagado"


# ── Entrada malformada ───────────────────────────────────────────────────────

@pytest.mark.parametrize("entrada", [None, "texto", 42, {"a": 1}])
def test_payload_nao_lista_nao_derruba(artefatos, entrada):
    assert artifact_purge.purgar(entrada) == 0


@pytest.mark.parametrize("item", [None, "texto", 42, {}, {"id_hash": "a"}, {"local_path": ""}])
def test_item_malformado_e_ignorado(artefatos, item):
    assert artifact_purge.purgar([item]) == 0
