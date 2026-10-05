"""`make check-db`: each way a connection fails becomes one sentence that says
what to fix. The exceptions are the real ones asyncpg raises (and SQLAlchemy
wraps), so the classification follows the chain, not just the outer type.
"""
from __future__ import annotations

import socket

import asyncpg
import pytest
from sqlalchemy.exc import DBAPIError

from app.services.diagnostico_banco import Relatorio, avaliar_extensoes, explicar_falha

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
    # With or without an engine built at import (it depends on the environment's .env).
    for motor in (None, object()):
        monkeypatch.setattr("app.core.db.async_engine", motor)
        rel = await diagnostico_banco.diagnosticar()
        assert rel.ok is False
        assert "exemplo" in rel.linhas[0]


async def test_sem_url_diz_que_falta(monkeypatch):
    from app.services import diagnostico_banco

    monkeypatch.setattr("app.core.config.DATABASE_URL", None)
    monkeypatch.setattr("app.core.db.async_engine", None)
    rel = await diagnostico_banco.diagnosticar()
    assert rel.ok is False
    assert "nao esta definida" in rel.linhas[0]


TODAS = {"postgis", "uuid-ossp"}


def _avaliar(instaladas, disponiveis, superusuario):
    rel = Relatorio()
    avaliar_extensoes(rel, set(instaladas), set(disponiveis), superusuario=superusuario,
                      usuario="atlans", banco="atlans")
    return rel


def test_extensoes_instaladas():
    rel = _avaliar(TODAS, TODAS, superusuario=False)
    assert rel.ok and rel.linhas[0].startswith("[ok]")


def test_faltam_e_o_usuario_comum_recebe_o_comando_de_superusuario():
    rel = _avaliar(set(), TODAS, superusuario=False)
    assert not rel.ok
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in rel.linhas[0]


def test_faltam_e_o_superusuario_deixa_para_a_migracao():
    rel = _avaliar(set(), TODAS, superusuario=True)
    assert rel.ok and rel.linhas[0].startswith("[aviso]")


def test_sem_o_pacote_nem_o_superusuario_cria():
    """The package missing on the server: one failure, and no promise that the migration will create it."""
    rel = _avaliar({"uuid-ossp"}, {"uuid-ossp"}, superusuario=True)
    assert not rel.ok
    assert len(rel.linhas) == 1 and "pacote" in rel.linhas[0]
