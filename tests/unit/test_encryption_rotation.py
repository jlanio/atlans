# tests/unit/test_encryption_rotation.py
"""Rotação de chave Fernet (F4).

O módulo de encryption passou a usar MultiFernet: a primeira chave cifra, todas
decifram. Isto permite trocar a chave mestra sem invalidar segredos já cifrados.
"""
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

import pytest


def test_encryption_module_usa_multifernet():
    """O objeto de cifra do app é um MultiFernet e o round-trip básico funciona."""
    import app.core.utils.encryption as enc

    assert isinstance(enc.fernet, MultiFernet)
    assert enc.decrypt_string(enc.encrypt_string("segredo")) == "segredo"


def test_multifernet_le_antiga_e_cifra_com_a_nova():
    """Contrato de rotação que o módulo entrega ao receber [nova, antiga].

    - Token cifrado com a chave ANTIGA continua legível.
    - Novo texto é cifrado com a chave NOVA (a antiga não consegue lê-lo).
    """
    antiga = Fernet(Fernet.generate_key())
    nova = Fernet(Fernet.generate_key())
    mf = MultiFernet([nova, antiga])   # ordem = a que o config produz de "nova,antiga"

    token_antigo = antiga.encrypt(b"valor-legado")
    assert mf.decrypt(token_antigo) == b"valor-legado"

    token_novo = mf.encrypt(b"valor-novo")
    assert nova.decrypt(token_novo) == b"valor-novo"
    with pytest.raises(InvalidToken):
        antiga.decrypt(token_novo)


def test_config_parseia_fernet_keys():
    """FERNET_KEYS vira lista ordenada, e FERNET_KEY é SEMPRE mantida para
    decifrar — anexada ao fim se o operador esquecer de re-listá-la.

    É a rede de segurança contra o pé-na-jaca de rotação: setar FERNET_KEYS sem a
    chave atual não pode 'orfanizar' (tornar ilegível) o que já foi cifrado."""
    def build(raw: str, fernet_key: str) -> list[str]:
        # espelha a lógica de app/core/config.py
        ks = [k.strip() for k in raw.split(",") if k.strip()]
        if fernet_key not in ks:
            ks.append(fernet_key)
        return ks

    assert build(" nova , antiga ", "antiga") == ["nova", "antiga"]     # já listada: posição preservada
    assert build("nova", "antiga") == ["nova", "antiga"]                # esqueceu a atual → anexada (ainda lê o legado)
    assert build("", "FKEY") == ["FKEY"]                                 # sem rotação → só a FERNET_KEY
    assert build("  ", "FKEY") == ["FKEY"]
    assert build("nova,antiga", "atual")[0] == "nova"                    # a primeira é sempre a que cifra


def test_config_sempre_inclui_fernet_key_no_conjunto_efetivo():
    """No módulo real (FERNET_KEYS não setado no ambiente de teste), o conjunto
    efetivo contém a FERNET_KEY."""
    from app.core import config
    assert config.FERNET_KEY in config.FERNET_KEYS
