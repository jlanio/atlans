# tests/unit/test_server_key_pinning.py
"""Pinning da chave de assinatura Ed25519 do servidor (achado S8).

Antes, quando SERVER_SIGNING_PUBLIC_KEY nao estava no .env — o caso PADRAO, pois
nem o enroll nem o setup a gravavam — o executor buscava a chave por HTTP a cada
boot, sem pinning e com follow_redirects=True. Consequencia: a verificacao de
assinatura de jobs nao acrescentava nada sobre o TLS, porque quem vencesse o
canal entregava a propria chave e passava a assinar jobs arbitrarios. E o ataque
se repetia a cada reinicio, sem deixar rastro.
"""
import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from executor import server_key
from executor.server_key import (
    ServerKeyError,
    ServerKeyPersistError,
    conflict_marker_path,
    load_pinned_key,
    pin_key,
    pinned_key_path,
    resolve_server_signing_key,
)


def _pub_b64() -> str:
    priv = Ed25519PrivateKey.generate()
    return base64.b64encode(
        priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()


# ── pin_key ───────────────────────────────────────────────────────────────────

def test_pin_grava_e_recarrega(tmp_path):
    chave = _pub_b64()
    pin_key(tmp_path, chave, source="teste")

    assert load_pinned_key(tmp_path) == chave
    assert pinned_key_path(tmp_path).is_file()


def test_pin_repetido_com_a_mesma_chave_e_idempotente(tmp_path):
    chave = _pub_b64()
    pin_key(tmp_path, chave, source="teste")
    pin_key(tmp_path, chave, source="teste")  # nao pode levantar

    assert load_pinned_key(tmp_path) == chave


def test_chave_divergente_nao_sobrescreve_o_pin(tmp_path):
    """O ponto central do S8: aceitar a troca automaticamente reabre o buraco."""
    original = _pub_b64()
    pin_key(tmp_path, original, source="enroll")

    with pytest.raises(ServerKeyError, match="MUDOU"):
        pin_key(tmp_path, _pub_b64(), source="atacante")

    assert load_pinned_key(tmp_path) == original, "o pin original deve sobreviver"


@pytest.mark.parametrize("valor", [
    "nao-e-base64!!",
    base64.b64encode(b"curta").decode(),          # 5 bytes, nao 32
    base64.b64encode(b"x" * 64).decode(),         # 64 bytes, nao 32
    "",
])
def test_material_invalido_e_recusado(tmp_path, valor):
    with pytest.raises(ServerKeyError):
        pin_key(tmp_path, valor, source="teste")
    assert load_pinned_key(tmp_path) is None


# ── resolve_server_signing_key ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_env_tem_precedencia_e_nao_toca_a_rede(tmp_path, monkeypatch):
    chave = _pub_b64()
    monkeypatch.setenv("SERVER_SIGNING_PUBLIC_KEY", chave)

    async def _explode(_url):
        raise AssertionError("nao deveria buscar na rede com a chave no ambiente")

    monkeypatch.setattr(server_key, "_fetch_server_key", _explode)

    assert await resolve_server_signing_key(tmp_path, "wss://x") == chave


@pytest.mark.asyncio
async def test_pin_existente_dispensa_a_rede(tmp_path, monkeypatch):
    """Boots seguintes ao primeiro nao podem ter janela de TOFU."""
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)
    chave = _pub_b64()
    pin_key(tmp_path, chave, source="enroll")

    async def _explode(_url):
        raise AssertionError("com pin em disco nao se busca chave na rede")

    monkeypatch.setattr(server_key, "_fetch_server_key", _explode)

    assert await resolve_server_signing_key(tmp_path, "wss://x") == chave


@pytest.mark.asyncio
async def test_tofu_acontece_uma_unica_vez(tmp_path, monkeypatch):
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)
    chave = _pub_b64()
    chamadas = []

    async def _fake(_url):
        chamadas.append(_url)
        return chave

    monkeypatch.setattr(server_key, "_fetch_server_key", _fake)

    assert await resolve_server_signing_key(tmp_path, "wss://x") == chave
    assert await resolve_server_signing_key(tmp_path, "wss://x") == chave
    assert len(chamadas) == 1, "a segunda resolucao deve vir do pin, nao da rede"


@pytest.mark.asyncio
async def test_falha_ao_obter_a_chave_aborta(tmp_path, monkeypatch):
    """Subir sem chave confiavel significaria aceitar job de qualquer origem."""
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)

    async def _falha(_url):
        raise ServerKeyError("servidor fora do ar")

    monkeypatch.setattr(server_key, "_fetch_server_key", _falha)

    with pytest.raises(ServerKeyError):
        await resolve_server_signing_key(tmp_path, "wss://x")


@pytest.mark.asyncio
async def test_pin_vazio_aborta_em_vez_de_refazer_tofu(tmp_path, monkeypatch):
    """Pin corrompido nao pode virar "ausente" e rebaixar a confianca para TOFU.

    Um arquivo truncado (erro de disco, ou adversario com acesso ao volume)
    faria o executor buscar a chave na rede de novo — reabrindo exatamente a
    janela que o pinning fecha.
    """
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)
    pinned_key_path(tmp_path).write_text("   \n", encoding="utf-8")

    async def _explode(_url):
        raise AssertionError("pin corrompido nao pode disparar TOFU")

    monkeypatch.setattr(server_key, "_fetch_server_key", _explode)

    with pytest.raises(ServerKeyError, match="vazia"):
        await resolve_server_signing_key(tmp_path, "wss://x")


@pytest.mark.asyncio
async def test_rotacao_pelo_renewal_para_o_boot_seguinte(tmp_path, monkeypatch):
    """Caminho real de divergencia: o bundle do renewal traz uma chave nova.

    `resolve_server_signing_key` nunca busca na rede tendo pin, entao a
    divergencia so chega por enroll/renewal — e ali `pin_key` recusa a troca.
    O que a versao anterior deixava passar: o boot seguinte carregava o pin
    ANTIGO em silencio e o executor subia rejeitando 100% dos jobs com
    "Assinatura Ed25519 invalida", sem nada mencionando chave. Agora o conflito
    fica registrado e o boot ABORTA com a mensagem acionavel.
    """
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)
    original = _pub_b64()
    pin_key(tmp_path, original, source="enroll")

    with pytest.raises(ServerKeyError, match="MUDOU"):
        pin_key(tmp_path, _pub_b64(), source="bundle do renewal")

    assert load_pinned_key(tmp_path) == original, "o pin original deve sobreviver"
    assert conflict_marker_path(tmp_path).is_file()

    with pytest.raises(ServerKeyError, match="MUDOU"):
        await resolve_server_signing_key(tmp_path, "wss://x")


@pytest.mark.asyncio
async def test_override_por_ambiente_destrava_o_conflito(tmp_path, monkeypatch):
    """O operador confirmou a rotacao com o admin: o env explicito vence."""
    pin_key(tmp_path, _pub_b64(), source="enroll")
    nova = _pub_b64()
    with pytest.raises(ServerKeyError):
        pin_key(tmp_path, nova, source="bundle do renewal")

    monkeypatch.setenv("SERVER_SIGNING_PUBLIC_KEY", nova)
    assert await resolve_server_signing_key(tmp_path, "wss://x") == nova


def test_repin_coerente_limpa_o_marcador(tmp_path):
    """Sem limpar, o executor ficaria travado mesmo depois de resolvido."""
    original = _pub_b64()
    pin_key(tmp_path, original, source="enroll")
    with pytest.raises(ServerKeyError):
        pin_key(tmp_path, _pub_b64(), source="atacante")
    assert conflict_marker_path(tmp_path).is_file()

    pin_key(tmp_path, original, source="renewal seguinte")
    assert not conflict_marker_path(tmp_path).exists()


# ── Falha de ESCRITA do pin ───────────────────────────────────────────────────

def test_pin_em_diretorio_nao_gravavel_vira_erro_acionavel(tmp_path):
    """OSError de escrita nao pode escapar como traceback cru no meio do boot.

    `load_pinned_key` ja convertia OSError de LEITURA em ServerKeyError; o
    caminho de escrita nao fazia nada disso, e um bind `:ro` do compose virava
    crash loop sem mensagem que ligasse a falha a permissao de arquivo.
    """
    bloqueado = tmp_path / "certs"
    bloqueado.write_text("nao sou um diretorio", encoding="utf-8")

    with pytest.raises(ServerKeyPersistError, match="gravável|gravavel"):
        pin_key(bloqueado, _pub_b64(), source="teste")


@pytest.mark.asyncio
async def test_boot_degrada_para_memoria_quando_nao_consegue_gravar(
    tmp_path, monkeypatch, caplog
):
    """A chave veio por mTLS verificado — derrubar o boot troca risco por outage."""
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)
    bloqueado = tmp_path / "certs"
    bloqueado.write_text("nao sou um diretorio", encoding="utf-8")

    chave = _pub_b64()

    async def _fake(_url):
        return chave

    monkeypatch.setattr(server_key, "_fetch_server_key", _fake)

    with caplog.at_level("ERROR"):
        assert await resolve_server_signing_key(bloqueado, "wss://x") == chave
    assert "EM MEMÓRIA" in caplog.text
