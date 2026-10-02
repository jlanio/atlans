# tests/unit/test_contrato_app_executor_cripto.py
"""
Round-trip REAL da cripto de job entre servidor e executor.

`app/core/job_crypto.py` e `executor/crypto.py` sao pares de protocolo: um
cifra/assina, o outro decifra/verifica. Nao devem ser unificados — `executor/`
nao importa `app.*` em nenhum arquivo, e essa fronteira e deliberada (o executor
roda on-premise, na maquina do cliente). O remedio correto para um par assim e
teste de contrato, nao abstracao compartilhada.

So que o contrato nao era exercido. O unico teste que importava os dois lados
monkeypatchava justamente `verify_signature` e `decrypt_job_payload`, e a
`verify_job_signature` que o servidor mantinha so era usada por testes (saiu
do app) — ou seja, cada lado era testado contra a PROPRIA copia das regras. Uma divergencia nos bytes
canonicos, no HKDF, no salt ou no separador passaria verde nas duas suites e
quebraria 100% dos jobs em producao, de uma vez, sem nenhum teste vermelho.

Aqui nada e monkeypatchado: o servidor monta a mensagem de verdade e o executor
a abre de verdade.
"""
from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, PublicFormat,
)


@pytest.fixture
def chaves(monkeypatch):
    """Par Ed25519 do servidor + par X25519 do executor, como em producao.

    Patcha o ATRIBUTO do modulo, sem `importlib.reload`. `job_crypto` faz
    `from app.core.config import EXECUTOR_SIGNING_KEY`, entao recarrega-lo
    reimportaria o valor que `config` leu no proprio import — a chave nova
    do teste seria ignorada e os testes passariam a assinar com a chave de
    quem rodou primeiro. E o mesmo padrao de `tests/unit/test_job_crypto.py`.
    """
    servidor = Ed25519PrivateKey.generate()
    servidor_priv_b64 = base64.b64encode(
        servidor.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    ).decode()
    servidor_pub_b64 = base64.b64encode(
        servidor.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()

    executor = X25519PrivateKey.generate()
    executor_pub_pem = executor.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    ).decode()

    import app.core.job_crypto as jc
    monkeypatch.setattr(jc, "EXECUTOR_SIGNING_KEY", servidor_priv_b64)
    monkeypatch.setattr("app.core.config.EXECUTOR_SIGNING_KEY", servidor_priv_b64)

    return {
        "jc": jc,
        "servidor_pub_b64": servidor_pub_b64,
        "executor_priv": executor,
        "executor_pub_pem": executor_pub_pem,
    }


def _montar(chaves, payload=None, job_type="run_workflow"):
    return chaves["jc"].build_job_message(
        executor_id="exec-1",
        workspace_id="ws-1",
        agent_x25519_pub_pem=chaves["executor_pub_pem"],
        job_type=job_type,
        payload=payload if payload is not None else {"definition": {"nodes": []}},
    )


# ── O round-trip ─────────────────────────────────────────────────────────────

def test_o_executor_verifica_a_assinatura_que_o_servidor_produz(chaves):
    """Se os bytes canonicos divergirem entre os lados, isto cai."""
    from executor import crypto as ec

    msg = _montar(chaves)
    assert ec.verify_signature(msg, chaves["servidor_pub_b64"]) is True


def test_o_executor_decifra_o_payload_que_o_servidor_cifrou(chaves):
    """Cobre ECDH, HKDF (algoritmo, length, salt e info) e AES-GCM de uma vez."""
    from executor import crypto as ec

    original = {"definition": {"nodes": [{"id": "1", "name": "DataInput"}]}, "n": 42}
    msg = _montar(chaves, payload=original)

    assert ec.decrypt_job_payload(msg, chaves["executor_priv"]) == original


def test_payload_em_bytes_produz_o_mesmo_resultado_que_o_dict(chaves):
    """build_job_message aceita JSON ja serializado no caminho de failover."""
    from executor import crypto as ec

    original = {"definition": {"nodes": []}, "x": "acentuação"}
    msg = _montar(chaves, payload=json.dumps(original).encode())

    assert ec.decrypt_job_payload(msg, chaves["executor_priv"]) == original


# ── O contrato tambem tem de RECUSAR ─────────────────────────────────────────

def test_envelope_adulterado_invalida_a_assinatura(chaves):
    from executor import crypto as ec

    msg = _montar(chaves)
    msg["envelope"]["workspace_id"] = "ws-do-atacante"
    assert ec.verify_signature(msg, chaves["servidor_pub_b64"]) is False


def test_ciphertext_adulterado_invalida_a_assinatura(chaves):
    from executor import crypto as ec

    msg = _montar(chaves)
    msg["ciphertext"] = base64.b64encode(b"lixo").decode()
    assert ec.verify_signature(msg, chaves["servidor_pub_b64"]) is False


def test_assinatura_de_outro_servidor_e_recusada(chaves):
    from executor import crypto as ec

    outro = Ed25519PrivateKey.generate()
    outro_pub_b64 = base64.b64encode(
        outro.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()

    msg = _montar(chaves)
    assert ec.verify_signature(msg, outro_pub_b64) is False


def test_chave_de_executor_errada_nao_decifra(chaves):
    """Job endereçado a um executor nao pode ser aberto por outro."""
    from executor import crypto as ec

    msg = _montar(chaves)
    intruso = X25519PrivateKey.generate()

    with pytest.raises(ValueError):
        ec.decrypt_job_payload(msg, intruso)
