# tests/unit/test_encryption_rotation.py
"""Fernet key rotation (F4).

The encryption module now uses MultiFernet: the first key encrypts, all of them
decrypt. This allows changing the master key without invalidating already
encrypted secrets.
"""
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

import pytest


def test_encryption_module_uses_multifernet():
    """The app's cipher object is a MultiFernet and the basic round-trip works."""
    import app.core.utils.encryption as enc

    assert isinstance(enc.fernet, MultiFernet)
    assert enc.decrypt_string(enc.encrypt_string("segredo")) == "segredo"


def test_multifernet_reads_old_and_encrypts_with_new():
    """Rotation contract the module delivers when given [new, old].

    - A token encrypted with the OLD key remains readable.
    - New text is encrypted with the NEW key (the old one cannot read it).
    """
    antiga = Fernet(Fernet.generate_key())
    nova = Fernet(Fernet.generate_key())
    mf = MultiFernet([nova, antiga])   # order = the one the config produces from "new,old"

    old_token = antiga.encrypt(b"valor-legado")
    assert mf.decrypt(old_token) == b"valor-legado"

    new_token = mf.encrypt(b"valor-novo")
    assert nova.decrypt(new_token) == b"valor-novo"
    with pytest.raises(InvalidToken):
        antiga.decrypt(new_token)


def test_config_parseia_fernet_keys():
    """FERNET_KEYS becomes an ordered list, and FERNET_KEY is ALWAYS kept for
    decryption — appended at the end if the operator forgets to re-list it.

    It is the safety net against a rotation blunder: setting FERNET_KEYS without
    the current key must not 'orphan' (make unreadable) what was already encrypted."""
    def build(raw: str, fernet_key: str) -> list[str]:
        # mirrors the logic in app/core/config.py
        ks = [k.strip() for k in raw.split(",") if k.strip()]
        if fernet_key not in ks:
            ks.append(fernet_key)
        return ks

    assert build(" nova , antiga ", "antiga") == ["nova", "antiga"]     # already listed: position preserved
    assert build("nova", "antiga") == ["nova", "antiga"]                # forgot the current one → appended (still reads legacy data)
    assert build("", "FKEY") == ["FKEY"]                                 # no rotation → only FERNET_KEY
    assert build("  ", "FKEY") == ["FKEY"]
    assert build("nova,antiga", "atual")[0] == "nova"                    # the first one is always the one that encrypts


def test_config_always_includes_fernet_key_in_the_effective_set():
    """In the real module (FERNET_KEYS not set in the test environment), the
    effective set contains FERNET_KEY."""
    from app.core import config
    assert config.FERNET_KEY in config.FERNET_KEYS
