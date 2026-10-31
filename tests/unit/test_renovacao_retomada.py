"""
Executor side of an interrupted cert renewal (executor/renewal.py): the key
and CSR are kept until the bundle is persisted, and resumed as they were.
"""
import json
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from executor import renewal


def test_pending_renewal_round_trip(tmp_path):
    chave = Ed25519PrivateKey.generate()
    renewal._save_pending(tmp_path, chave, "CSR-PEM")

    arquivo = tmp_path / renewal.PENDING_FILE
    assert oct(arquivo.stat().st_mode & 0o777) == "0o600"
    carregada, csr = renewal._load_pending(tmp_path)
    assert csr == "CSR-PEM"
    assert carregada.public_key().public_bytes_raw() == chave.public_key().public_bytes_raw()
    assert renewal.has_pending_renewal(tmp_path)

    renewal._drop_pending(tmp_path)
    assert not renewal.has_pending_renewal(tmp_path)


def test_a_stale_pending_renewal_is_dropped(tmp_path):
    renewal._save_pending(tmp_path, Ed25519PrivateKey.generate(), "CSR")
    arquivo = tmp_path / renewal.PENDING_FILE
    dados = json.loads(arquivo.read_text())
    dados["criado_em"] = time.time() - renewal._PENDING_MAX_AGE_S - 1
    arquivo.write_text(json.dumps(dados))

    assert renewal._load_pending(tmp_path) is None
    assert not arquivo.exists()


def test_an_unreadable_pending_renewal_is_dropped(tmp_path):
    (tmp_path / renewal.PENDING_FILE).write_text("{nao e json")
    assert renewal._load_pending(tmp_path) is None
    assert not (tmp_path / renewal.PENDING_FILE).exists()
