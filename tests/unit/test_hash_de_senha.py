# tests/unit/test_hash_de_senha.py
"""
O hash de senha de verdade, sem mock: o bcrypt instalado, no esquema
`bcrypt_sha256` (o formato que o passlib definiu e que o banco guarda).

Os testes de rota trocam o `hash_password` por um lambda, então nada no resto da
suíte chama o bcrypt. Foi assim que o bcrypt 5.0 entrou (Dependabot) com o CI
verde: o hash era pelo passlib 1.7.4, que levanta ValueError com ele, e login e
cadastro caíam com 500. O passlib saiu; o esquema ficou, reproduzido sobre o
bcrypt direto — e os hashes abaixo, gerados pelo passlib, provam que quem já
tem conta continua entrando.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.utils import jwt_utils
from app.core.utils.jwt_utils import hash_password, verify_password

# Gerados pelo passlib 1.7.4 (`bcrypt_sha256`): a versão 2 que está em produção
# desde antes, e a versão 1 (SHA-256 puro, com `2b` e com `2a`), caso exista.
_EXISTENTES = {
    "$bcrypt-sha256$v=2,t=2b,r=12$G4Hl4bVYPyC7wzKKij1/OO$oVSmlOfsCSevJc8MX5yGu7T3Iv4O.QW",  # pragma: allowlist secret
    "$bcrypt-sha256$v=2,t=2b,r=12$a1VACTkiQItjpdkDgfEbb.$8TPaW52d40iMoibAeMAH3OrPfY7voY6",  # pragma: allowlist secret
    "$bcrypt-sha256$2b,5$A.PSEbhmqC1f.La59aF4ce$2Jv0mKdFNdMWlD5udcniteW77JQJi06",  # pragma: allowlist secret
    "$bcrypt-sha256$2a,5$.u8al6yKkPbT5dX2/j.sIu$IwilJgD/M0oXONpzipfEWGOgs6hFMkK",  # pragma: allowlist secret
}
# A senha longa (120 bytes em UTF-8), também pelo passlib.
_LONGA = "ç" * 60
_HASH_DA_LONGA = "$bcrypt-sha256$v=2,t=2b,r=5$TZODI3iMQXZ6n4b.TEfSV.$cGbzAH8JiGgQ.dUTY0x5p7Bb26Er/hS"  # pragma: allowlist secret

_FORMATO_V2 = re.compile(r"^\$bcrypt-sha256\$v=2,t=2b,r=12\$[./A-Za-z0-9]{22}\$[./A-Za-z0-9]{31}$")


def test_hash_e_verificacao_de_ponta_a_ponta():
    hashed = hash_password("senha-correta")
    assert _FORMATO_V2.match(hashed), hashed
    assert verify_password("senha-correta", hashed)
    assert not verify_password("senha-errada", hashed)
    # Salt novo a cada hash.
    assert hash_password("senha-correta") != hashed


def test_senha_acima_de_72_bytes():
    # O bcrypt_sha256 existe para isto: sem ele, só os 72 primeiros bytes contam.
    hashed = hash_password(_LONGA)
    assert verify_password(_LONGA, hashed)
    assert not verify_password(_LONGA[:-1] + "c", hashed)
    assert verify_password(_LONGA, _HASH_DA_LONGA)


def test_hash_ja_gravado_continua_valido():
    for existente in _EXISTENTES:
        assert verify_password("senha-antiga", existente), existente
        assert not verify_password("senha-outra", existente), existente


def test_hash_fora_do_formato_e_falso_e_nao_levanta():
    for lixo in ("", "x", "$2b$12$" + "a" * 53, "$bcrypt-sha256$v=3,t=2b,r=12$" + "a" * 22 + "$" + "b" * 31, None):
        assert verify_password("qualquer", lixo) is False  # type: ignore[arg-type]
    assert verify_password(None, hash_password("x")) is False  # type: ignore[arg-type]


def test_o_hash_nao_passa_mais_pelo_passlib():
    fonte = Path(jwt_utils.__file__).read_text(encoding="utf-8")
    assert "from passlib" not in fonte and "import passlib" not in fonte
