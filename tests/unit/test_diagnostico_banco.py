"""`make check-db`: each way a connection fails becomes one sentence that says
what to fix. The exceptions are the real ones asyncpg raises (and SQLAlchemy
wraps), so the classification follows the chain, not just the outer type.
"""
from __future__ import annotations

import socket

import asyncpg
import pytest
from sqlalchemy.exc import DBAPIError

from app.services.diagnostico_banco import Relatorio, explicar_falha

ONDE = "host.docker.internal:5432/atlans"


def _envolvida(erro: BaseException) -> BaseException:
    """As SQLAlchemy delivers it: the driver error in `orig`."""
    return DBAPIError("connect", None, erro)


@pytest.mark.parametrize(
    ("erro", "trecho"),
    [
        (asyncpg.exceptions.InvalidPasswordError('password authentication failed for user "atlans"'), "recusou o login"),
        (asyncpg.exceptions.InvalidAuthorizationSpecificationError('LDAP authentication failed for user "atlans"'), "LDAP"),
        (asyncpg.exceptions.InvalidAuthorizationSpecificationError(
            'no pg_hba.conf entry for host "172.19.0.3", user "atlans", database "atlans", no encryption'), "pg_hba.conf"),
        (asyncpg.exceptions.InvalidCatalogNameError('database "atlans" does not exist'), "nao existe"),
        (socket.gaierror(-2, "Name or service not known"), "nao resolve"),
        (ConnectionRefusedError(111, "Connect call failed ('172.17.0.1', 5432)"), "Nada escuta"),
        (TimeoutError(), "Sem resposta"),
    ],
)
def test_cada_falha_vira_uma_frase_com_o_conserto(erro, trecho):
    assert trecho in explicar_falha(erro, ONDE)
    # Wrapped by SQLAlchemy, the same sentence.
    assert trecho in explicar_falha(_envolvida(erro), ONDE)


def test_ldap_nao_vira_senha_errada():
    """Both are InvalidAuthorizationSpecificationError; LDAP needs its own advice
    (a locked or expired account), not just 'check the password'."""
    texto = explicar_falha(asyncpg.exceptions.InvalidAuthorizationSpecificationError(
        'LDAP authentication failed for user "atlans"'), ONDE)
    assert "bloqueada" in texto


def test_localhost_recusado_aponta_o_host_docker_internal():
    texto = explicar_falha(ConnectionRefusedError(111, "refused"), "localhost:5432/atlans")
    assert "host.docker.internal" in texto


def test_falha_desconhecida_diz_o_tipo_e_a_mensagem():
    texto = explicar_falha(RuntimeError("algo novo"), ONDE)
    assert "RuntimeError" in texto and "algo novo" in texto


def test_o_relatorio_falha_com_uma_falha_e_nao_com_um_aviso():
    rel = Relatorio()
    rel.bom("conectado")
    rel.aviso("schema ainda nao criado")
    assert rel.ok is True
    rel.falha("faltam extensoes")
    assert rel.ok is False
    assert [linha.split()[0] for linha in rel.linhas] == ["[ok]", "[aviso]", "[falha]"]


async def test_url_de_exemplo_nao_tenta_conectar(monkeypatch):
    from app.services import diagnostico_banco

    monkeypatch.setattr("app.core.config.DATABASE_URL", "postgresql+asyncpg://<usuario>:<senha>@<host>:5432/<banco>")
    rel = await diagnostico_banco.diagnosticar()
    assert rel.ok is False
    assert "exemplo" in rel.linhas[0]
