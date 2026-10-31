"""Private portal shared by e-mail (review of 2026-10-31): the form offers
"e-mail ou username" but the token carries no e-mail, so e-mail entries never
matched."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routers import portal_router as P


def _request():
    return SimpleNamespace(headers={"Authorization": "Bearer t"})


def _wf(*compartilhado):
    return SimpleNamespace(flag_ative=True, portal_access="private", portal_shared_with=list(compartilhado))


@pytest.fixture
def claims(monkeypatch):
    async def _claims(_token):
        return {"sub": "u-1", "username": "alice"}
    monkeypatch.setattr("app.api.dependencies.validate_access_token_claims", _claims)


@pytest.mark.asyncio
async def test_an_e_mail_entry_lets_its_owner_in(claims, monkeypatch):
    async def _email(sub, _db=None):
        return "alice@exemplo.org" if sub == "u-1" else None
    monkeypatch.setattr(P, "_email_do_usuario", _email)
    await P.enforce_portal_access(_wf("Alice@Exemplo.org"), _request())


@pytest.mark.asyncio
async def test_someone_else_s_e_mail_is_still_refused(claims, monkeypatch):
    async def _email(_sub, _db=None):
        return "alice@exemplo.org"
    monkeypatch.setattr(P, "_email_do_usuario", _email)
    with pytest.raises(HTTPException) as erro:
        await P.enforce_portal_access(_wf("bob@exemplo.org"), _request())
    assert erro.value.status_code == 403


@pytest.mark.asyncio
async def test_username_entries_need_no_lookup(claims, monkeypatch):
    async def _nao_consultar(_sub, _db=None):
        raise AssertionError("lookup without an e-mail entry")
    monkeypatch.setattr(P, "_email_do_usuario", _nao_consultar)
    await P.enforce_portal_access(_wf("ALICE"), _request())


@pytest.mark.asyncio
async def test_the_lookup_uses_the_request_session_not_a_new_one(claims, monkeypatch):
    """A second pooled session per tile, while the route's session holds a
    connection, exhausted the pool under a burst of tiles."""
    from app.core import db as core_db

    def _proibido():
        raise AssertionError("opened a second session")

    monkeypatch.setattr(core_db, "AsyncSessionLocal", _proibido)

    class _Resultado:
        def first(self):
            return ("Alice@Exemplo.org", "active")

    class _Sessao:
        def __init__(self):
            self.consultas = 0

        async def execute(self, _stmt):
            self.consultas += 1
            return _Resultado()

    sessao = _Sessao()
    await P.enforce_portal_access(_wf("alice@exemplo.org"), _request(), sessao)
    assert sessao.consultas == 1
