"""
Executor side of an interrupted cert renewal (executor/renewal.py): the key
and CSR are kept until the bundle is persisted, and resumed as they were.
"""
import json
import time
import pytest

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


@pytest.mark.asyncio
async def test_a_failed_resume_keeps_retrying_while_the_saved_renewal_is_valid(monkeypatch):
    """One quick attempt and then stopping for good left the machine unable to
    connect until a manual re-enrollment; while the saved renewal is valid the
    refusal is not final (fix review)."""
    import asyncio
    from unittest.mock import AsyncMock

    from executor import connection as C
    from executor.job_queue import ExecutorJobQueue

    conn = C.ExecutorConnection(job_queue=ExecutorJobQueue(on_execute=AsyncMock()), result_queue=asyncio.Queue())
    tentativas = {"n": 0}

    async def _sessao():
        tentativas["n"] += 1
        raise RuntimeError("401")

    pendente = {"valida": True}
    retomadas = []

    async def _retomar():
        retomadas.append(1)
        if len(retomadas) >= 3:
            pendente["valida"] = False      # the saved renewal expired
        return False

    monkeypatch.setattr(conn, "_connect_and_run", _sessao)
    monkeypatch.setattr(C, "_classify_connection_error", lambda exc: ("negado", False, True))
    monkeypatch.setattr(conn, "_retomar_renovacao_interrompida", _retomar)
    monkeypatch.setattr(type(conn), "_ha_renovacao_pendente", staticmethod(lambda: pendente["valida"]))
    monkeypatch.setattr(conn, "_esperar_retry", AsyncMock(return_value=True))

    await asyncio.wait_for(conn.run(), timeout=5)

    assert len(retomadas) == 3            # kept trying while the renewal was valid
    assert conn.terminal_deny == "negado"  # final only after it expired
