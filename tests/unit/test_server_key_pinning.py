# tests/unit/test_server_key_pinning.py
"""Pinning of the server's Ed25519 signing key (finding S8).

Before, when SERVER_SIGNING_PUBLIC_KEY was not in .env — the DEFAULT case, since
neither enroll nor setup wrote it — the executor fetched the key over HTTP on every
boot, with no pinning and with follow_redirects=True. Consequence: verifying job
signatures added nothing on top of TLS, because whoever won the channel delivered
their own key and could then sign arbitrary jobs. And the attack repeated on every
restart, leaving no trace.
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

def test_pin_writes_and_reloads(tmp_path):
    chave = _pub_b64()
    pin_key(tmp_path, chave, source="teste")

    assert load_pinned_key(tmp_path) == chave
    assert pinned_key_path(tmp_path).is_file()


def test_repeated_pin_with_the_same_key_is_idempotent(tmp_path):
    chave = _pub_b64()
    pin_key(tmp_path, chave, source="teste")
    pin_key(tmp_path, chave, source="teste")  # must not raise

    assert load_pinned_key(tmp_path) == chave


def test_divergent_key_does_not_overwrite_the_pin(tmp_path):
    """O ponto central do S8: aceitar a troca automaticamente reabre o buraco."""
    original = _pub_b64()
    pin_key(tmp_path, original, source="enroll")

    with pytest.raises(ServerKeyError, match="MUDOU"):
        pin_key(tmp_path, _pub_b64(), source="atacante")

    assert load_pinned_key(tmp_path) == original, "o pin original deve sobreviver"


@pytest.mark.parametrize("valor", [
    "nao-e-base64!!",
    base64.b64encode(b"curta").decode(),          # 5 bytes, not 32
    base64.b64encode(b"x" * 64).decode(),         # 64 bytes, not 32
    "",
])
def test_invalid_material_is_rejected(tmp_path, valor):
    with pytest.raises(ServerKeyError):
        pin_key(tmp_path, valor, source="teste")
    assert load_pinned_key(tmp_path) is None


# ── resolve_server_signing_key ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_env_takes_precedence_and_does_not_touch_the_network(tmp_path, monkeypatch):
    chave = _pub_b64()
    monkeypatch.setenv("SERVER_SIGNING_PUBLIC_KEY", chave)

    async def _explode(_url):
        raise AssertionError("nao deveria buscar na rede com a chave no ambiente")

    monkeypatch.setattr(server_key, "_fetch_server_key", _explode)

    assert await resolve_server_signing_key(tmp_path, "wss://x") == chave


@pytest.mark.asyncio
async def test_existing_pin_skips_the_network(tmp_path, monkeypatch):
    """Boots after the first one must not have a TOFU window."""
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)
    chave = _pub_b64()
    pin_key(tmp_path, chave, source="enroll")

    async def _explode(_url):
        raise AssertionError("com pin em disco nao se busca chave na rede")

    monkeypatch.setattr(server_key, "_fetch_server_key", _explode)

    assert await resolve_server_signing_key(tmp_path, "wss://x") == chave


@pytest.mark.asyncio
async def test_tofu_happens_only_once(tmp_path, monkeypatch):
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
async def test_failure_to_obtain_the_key_aborts(tmp_path, monkeypatch):
    """Starting without a trusted key would mean accepting jobs from any origin."""
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)

    async def _falha(_url):
        raise ServerKeyError("servidor fora do ar")

    monkeypatch.setattr(server_key, "_fetch_server_key", _falha)

    with pytest.raises(ServerKeyError):
        await resolve_server_signing_key(tmp_path, "wss://x")


@pytest.mark.asyncio
async def test_empty_pin_aborts_instead_of_redoing_tofu(tmp_path, monkeypatch):
    """A corrupted pin must not turn into "absent" and downgrade trust to TOFU.

    A truncated file (disk error, or an adversary with access to the volume)
    would make the executor fetch the key over the network again — reopening
    exactly the window that pinning closes.
    """
    monkeypatch.delenv("SERVER_SIGNING_PUBLIC_KEY", raising=False)
    pinned_key_path(tmp_path).write_text("   \n", encoding="utf-8")

    async def _explode(_url):
        raise AssertionError("pin corrompido nao pode disparar TOFU")

    monkeypatch.setattr(server_key, "_fetch_server_key", _explode)

    with pytest.raises(ServerKeyError, match="vazia"):
        await resolve_server_signing_key(tmp_path, "wss://x")


@pytest.mark.asyncio
async def test_rotation_via_renewal_for_the_next_boot(tmp_path, monkeypatch):
    """Real divergence path: the renewal bundle brings a new key.

    `resolve_server_signing_key` never fetches over the network when it has a pin,
    so divergence only arrives via enroll/renewal — and there `pin_key` refuses
    the swap. What the previous version let through: the next boot silently loaded
    the OLD pin and the executor came up rejecting 100% of jobs with
    "Assinatura Ed25519 invalida" (invalid Ed25519 signature), with nothing
    mentioning the key. Now the conflict is recorded and the boot ABORTS with the
    actionable message.
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
async def test_environment_override_unlocks_the_conflict(tmp_path, monkeypatch):
    """O operador confirmou a rotacao com o admin: o env explicito vence."""
    pin_key(tmp_path, _pub_b64(), source="enroll")
    nova = _pub_b64()
    with pytest.raises(ServerKeyError):
        pin_key(tmp_path, nova, source="bundle do renewal")

    monkeypatch.setenv("SERVER_SIGNING_PUBLIC_KEY", nova)
    assert await resolve_server_signing_key(tmp_path, "wss://x") == nova


def test_consistent_repin_clears_the_marker(tmp_path):
    """Without clearing, the executor would stay stuck even after it was resolved."""
    original = _pub_b64()
    pin_key(tmp_path, original, source="enroll")
    with pytest.raises(ServerKeyError):
        pin_key(tmp_path, _pub_b64(), source="atacante")
    assert conflict_marker_path(tmp_path).is_file()

    pin_key(tmp_path, original, source="renewal seguinte")
    assert not conflict_marker_path(tmp_path).exists()


# ── Pin WRITE failure ─────────────────────────────────────────────────────────

def test_pin_in_unwritable_directory_becomes_actionable_error(tmp_path):
    """A write OSError must not escape as a raw traceback in the middle of boot.

    `load_pinned_key` already turned a READ OSError into ServerKeyError; the
    write path did nothing of the sort, and a `:ro` bind in compose became a
    crash loop with no message linking the failure to file permissions.
    """
    bloqueado = tmp_path / "certs"
    bloqueado.write_text("nao sou um diretorio", encoding="utf-8")

    with pytest.raises(ServerKeyPersistError, match="gravável|gravavel"):
        pin_key(bloqueado, _pub_b64(), source="teste")


@pytest.mark.asyncio
async def test_boot_degrades_to_memory_when_it_cannot_write(
    tmp_path, monkeypatch, caplog
):
    """The key came over verified mTLS — bringing the boot down trades risk for an outage."""
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
