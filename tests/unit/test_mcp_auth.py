# tests/unit/test_mcp_auth.py
"""
`AutenticacaoPAT` — the only line between a token and the user's data.

The tests here are, for the most part, about what must NOT happen:

- nothing gets through without `Authorization: Bearer atl_pat_…`: neither a session
  JWT (`/mcp` stays out of the global dependencies on purpose) nor a token in the URL
  (the query string leaks into proxy logs, history and Referer);
- a revoked, expired or suspended-user token gets the SAME response as a
  token that never existed — the endpoint must not become an oracle of valid tokens;
- the token's reach is `user's workspaces ∩ token's workspace_ids`, and
  `workspace_ids = NULL` means "all, including future ones". Treating NULL
  as an empty list would take from the token exactly what the owner chose on screen.

And about what must happen: the scope arrives through both channels (the
`request.state`, which the tools read, and the `ContextVar`, the only path to
`list_tools`), the `ContextVar` is reset at the end, and a missing Redis brings
nothing down.

Two method and lifecycle cases complete the edge: `GET /mcp` is a 405 without
going to the database (the transport is stateless, there is no server stream to deliver,
and an accepted GET would hold a worker connection forever) and the
`lifespan` event is answered HERE, without reaching the SDK's app — the one that enters
`session_manager.run()` is `app.main`, only once.
"""
from __future__ import annotations

import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app.core.utils.datetime_utils import utc_now_naive
from app.mcp import infra
from app.mcp.auth import AutenticacaoPAT
from app.mcp.escopo import ESCOPO_ATUAL
from app.models.api_token import ApiToken
from tests.unit._mcp_harness import (
    RedisFalso,
    banco_em_memoria,
    criar_pat,
    criar_usuario,
    criar_workspace,
    sessao_de,
)


@pytest.fixture
async def ambiente(monkeypatch):
    """In-memory database with one user, one workspace and the MCP infrastructure redirected."""
    async with banco_em_memoria() as fabrica:
        async with fabrica() as db:
            await criar_usuario(db, "usr-1", "ana")
            await criar_usuario(db, "usr-2", "bruno")
            await criar_workspace(db, "ws-1", "usr-1", "Principal")
            await criar_workspace(db, "ws-2", "usr-1", "Segundo")
            await criar_workspace(db, "ws-alheio", "usr-2", "De outro")

        redis = RedisFalso()
        monkeypatch.setattr(infra, "sessao", sessao_de(fabrica))
        monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
        yield _Ambiente(fabrica, redis)


class _Ambiente:
    def __init__(self, fabrica, redis):
        self.fabrica = fabrica
        self.redis = redis
        self.visto: dict = {}

    def app(self):
        """The middleware in front of an app that just records what it received."""
        visto = self.visto

        async def adiante(scope, receive, send):
            visto["escopo"] = (scope.get("state") or {}).get("escopo")
            visto["contextvar"] = ESCOPO_ATUAL.get()
            corpo = b'{"ok":true}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", b"11")],
                }
            )
            await send({"type": "http.response.body", "body": corpo})

        return AutenticacaoPAT(adiante)

    def cliente(self):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app()), base_url="http://localhost"
        )


async def _pat(ambiente, *, user_id="usr-1", scopes=("workflows:read",), workspace_ids=None) -> str:
    async with ambiente.fabrica() as db:
        return await criar_pat(db, user_id, scopes, workspace_ids)


# ── Method and lifecycle ──────────────────────────────────────────────────────


async def test_get_no_mcp_e_405_com_allow_post(ambiente):
    """With `stateless_http` there is no server stream: the GET would only hold a worker.

    And the refusal comes before the database — not even a valid token gets resolved.
    """
    segredo = await _pat(ambiente)
    async with ambiente.cliente() as c:
        r = await c.get("/mcp", headers={"Authorization": f"Bearer {segredo}"})
    assert r.status_code == 405
    assert r.headers["allow"] == "POST"
    assert r.json()["error"] == "method_not_allowed"
    # It was not passed on: the inner app was never called.
    assert ambiente.visto == {}


async def test_get_sem_token_nenhum_tambem_e_405(ambiente):
    """The method does not work with any token — and the response does not become an oracle."""
    async with ambiente.cliente() as c:
        r = await c.get("/mcp")
    assert r.status_code == 405
    assert "www-authenticate" not in r.headers


async def test_lifespan_e_respondido_sem_alcancar_o_app_interno(ambiente):
    """One extra `run()` on the same session manager would be fatal.

    The manager is a single-use context; if a refactor swaps the route for a
    `Mount`, the lifecycle event would start arriving here — and this test says
    what happens then: we answer the protocol and do NOT pass it on.
    """
    chegou = []

    async def adiante(scope, receive, send):  # pragma: no cover - must not run
        chegou.append(scope.get("type"))

    app = AutenticacaoPAT(adiante)
    recebidos = [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}]
    enviados = []

    async def receive():
        return recebidos.pop(0)

    async def send(mensagem):
        enviados.append(mensagem["type"])

    await app({"type": "lifespan"}, receive, send)

    assert enviados == ["lifespan.startup.complete", "lifespan.shutdown.complete"]
    assert chegou == []


# ── Recusas ───────────────────────────────────────────────────────────────────


async def test_sem_cabecalho_authorization_e_401_com_desafio(ambiente):
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == 'Bearer realm="atlans-mcp"'
    assert r.json()["error"] == "unauthorized"
    assert "escopo" not in ambiente.visto


async def test_jwt_de_sessao_nao_vale_no_mcp(ambiente):
    # Assembled in pieces on purpose: a whole JWT in the source would trip the
    # CI's secret scanner, which does not tell an example from a real credential.
    jwt = ".".join(["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiJ1c3ItMSJ9", "assinatura"])
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {jwt}"})
    assert r.status_code == 401
    # The wrong format does not even query the database — and does not get `invalid_token`,
    # which would say "the format was right".
    assert "invalid_token" not in r.headers["www-authenticate"]


async def test_esquema_que_nao_e_bearer_e_recusado(ambiente):
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": "Basic YWJjOjEyMw=="})
    assert r.status_code == 401


async def test_prefixo_errado_e_recusado(ambiente):
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": "Bearer ghp_" + "a" * 43})
    assert r.status_code == 401


@pytest.mark.parametrize("parametro", ["access_token", "token"])
async def test_token_na_query_string_e_recusado_mesmo_com_header_valido(ambiente, parametro):
    segredo = await _pat(ambiente)
    async with ambiente.cliente() as c:
        r = await c.post(
            f"/mcp?{parametro}={segredo}", json={}, headers={"Authorization": f"Bearer {segredo}"}
        )
    assert r.status_code == 401
    assert "escopo" not in ambiente.visto


async def test_token_revogado_e_401_indistinguivel_de_inexistente(ambiente):
    segredo = await _pat(ambiente)
    async with ambiente.fabrica() as db:
        token = (await db.execute(select(ApiToken))).scalar_one()
        token.revoked_at = utc_now_naive()
        await db.commit()

    async with ambiente.cliente() as c:
        revogado = await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
        inexistente = await c.post(
            "/mcp", json={}, headers={"Authorization": "Bearer atl_pat_" + "z" * 43}
        )
    assert revogado.status_code == inexistente.status_code == 401
    assert revogado.json() == inexistente.json()
    assert 'error="invalid_token"' in revogado.headers["www-authenticate"]


async def test_token_expirado_e_401(ambiente):
    segredo = await _pat(ambiente)
    async with ambiente.fabrica() as db:
        token = (await db.execute(select(ApiToken))).scalar_one()
        token.expires_at = utc_now_naive() - timedelta(days=1)
        await db.commit()

    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    assert r.status_code == 401


async def test_usuario_suspenso_derruba_o_token_ainda_valido(ambiente):
    segredo = await _pat(ambiente)
    async with ambiente.fabrica() as db:
        from app.models.user import User

        usuario = (await db.execute(select(User).where(User.id_hash == "usr-1"))).scalar_one()
        usuario.status = "suspended"
        await db.commit()

    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    assert r.status_code == 401


async def test_a_mensagem_de_recusa_nunca_diz_o_motivo(ambiente):
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": "Bearer atl_pat_" + "z" * 43})
    texto = json.dumps(r.json()).lower()
    for palavra in ("revogado", "expirado", "suspenso", "não existe"):
        assert palavra not in texto


async def test_a_recusa_diz_onde_se_cria_o_token_e_quem_alcanca_a_pagina(ambiente):
    """`/settings/tokens`, like every page outside the Home, sends to `/` whoever does not
    administer the system (`web/proxy.ts`), and the token is personal: the admin only
    creates tokens for their OWN account. The refusal says both things, without telling
    anyone to ask for someone else's token."""
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={})
    mensagem = r.json()["message"]
    assert "/settings/tokens" in mensagem
    assert "administradores" in mensagem
    assert "peça" not in mensagem


# ── Sucesso ───────────────────────────────────────────────────────────────────


async def test_escopo_chega_em_request_state_e_no_contextvar(ambiente):
    segredo = await _pat(ambiente, scopes=("workflows:read", "drive:read"))
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    assert r.status_code == 200
    escopo = ambiente.visto["escopo"]
    assert escopo is ambiente.visto["contextvar"]
    assert escopo.user_id == "usr-1"
    assert escopo.username == "ana"
    assert escopo.scopes == frozenset({"workflows:read", "drive:read"})
    assert escopo.token_prefix.startswith("atl_pat_")


async def test_contextvar_e_resetado_depois_da_request(ambiente):
    segredo = await _pat(ambiente)
    async with ambiente.cliente() as c:
        await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    assert ESCOPO_ATUAL.get() is None


async def test_marcar_uso_carimba_pelo_throttle_do_redis(ambiente):
    segredo = await _pat(ambiente)
    async with ambiente.cliente() as c:
        await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    escopo = ambiente.visto["escopo"]
    assert f"pat:lu:{escopo.token_id}" in ambiente.redis.dados

    async with ambiente.fabrica() as db:
        token = (await db.execute(select(ApiToken))).scalar_one()
        assert token.last_used_at is not None


async def test_sem_redis_a_autenticacao_continua_funcionando(ambiente, monkeypatch):
    monkeypatch.setattr(infra, "redis_ou_none", lambda: None)
    segredo = await _pat(ambiente)
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    assert r.status_code == 200
    assert ambiente.visto["escopo"] is not None


# ── Reach per workspace ───────────────────────────────────────────────────────


async def test_token_sem_lista_alcanca_workspace_criado_depois_da_emissao(ambiente):
    segredo = await _pat(ambiente, workspace_ids=None)
    async with ambiente.fabrica() as db:
        await criar_workspace(db, "ws-novo", "usr-1", "Criado depois")

    async with ambiente.cliente() as c:
        await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    escopo = ambiente.visto["escopo"]
    assert escopo.todos_os_workspaces is True
    assert "ws-novo" in escopo.workspace_ids


async def test_lista_explicita_nao_alcanca_workspace_criado_depois(ambiente):
    segredo = await _pat(ambiente, workspace_ids=["ws-1"])
    async with ambiente.fabrica() as db:
        await criar_workspace(db, "ws-novo", "usr-1", "Criado depois")

    async with ambiente.cliente() as c:
        await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    escopo = ambiente.visto["escopo"]
    assert escopo.todos_os_workspaces is False
    assert escopo.workspace_ids == frozenset({"ws-1"})


async def test_workspace_que_o_usuario_perdeu_sai_do_alcance(ambiente):
    """The intersection is with the user's CURRENT workspaces, not with the token's list."""
    segredo = await _pat(ambiente, workspace_ids=["ws-1", "ws-2"])
    async with ambiente.fabrica() as db:
        from app.models.workspace import Workspace

        ws2 = (await db.execute(select(Workspace).where(Workspace.id_hash == "ws-2"))).scalar_one()
        ws2.deleted_at = utc_now_naive()
        await db.commit()

    async with ambiente.cliente() as c:
        await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    assert ambiente.visto["escopo"].workspace_ids == frozenset({"ws-1"})


async def test_token_nao_alcanca_workspace_de_outro_usuario(ambiente):
    segredo = await _pat(ambiente, workspace_ids=None)
    async with ambiente.cliente() as c:
        await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {segredo}"})
    assert "ws-alheio" not in ambiente.visto["escopo"].workspace_ids
