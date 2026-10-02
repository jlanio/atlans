# tests/unit/test_mcp_auth.py
"""
`AutenticacaoPAT` — a única linha entre um token e os dados do usuário.

Os testes daqui são, na maioria, sobre o que NÃO deve acontecer:

- nada passa sem `Authorization: Bearer atl_pat_…`: nem JWT de sessão (o `/mcp`
  fica fora das dependencies globais de propósito), nem token na URL (query
  string vaza em log de proxy, histórico e Referer);
- token revogado, expirado ou de usuário suspenso recebe a MESMA resposta de um
  token que nunca existiu — o endpoint não pode virar oráculo de tokens válidos;
- o alcance do token é `workspaces do usuário ∩ workspace_ids do token`, e
  `workspace_ids = NULL` significa "todos, inclusive os futuros". Tratar NULL
  como lista vazia tiraria do token justamente o que o dono escolheu na tela.

E sobre o que precisa acontecer: o escopo chega pelos dois canais (o
`request.state`, que as tools leem, e o `ContextVar`, único caminho até o
`list_tools`), o `ContextVar` é resetado no fim, e a falta de Redis não derruba
nada.

Dois casos de método e ciclo de vida completam a borda: `GET /mcp` é 405 sem
ir ao banco (o transporte é stateless, não há stream de servidor para entregar,
e um GET aceito prenderia uma conexão de worker para sempre) e o evento de
`lifespan` é respondido AQUI, sem alcançar o app do SDK — quem entra em
`session_manager.run()` é `app.main`, uma vez só.
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
    """Banco em memória com um usuário, um workspace e a infra do MCP redirecionada."""
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
        """O middleware na frente de um app que só anota o que recebeu."""
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


# ── Método e ciclo de vida ────────────────────────────────────────────────────


async def test_get_no_mcp_e_405_com_allow_post(ambiente):
    """Com `stateless_http` não há stream de servidor: o GET só prenderia worker.

    E a recusa vem antes do banco — nem o token válido chega a ser resolvido.
    """
    segredo = await _pat(ambiente)
    async with ambiente.cliente() as c:
        r = await c.get("/mcp", headers={"Authorization": f"Bearer {segredo}"})
    assert r.status_code == 405
    assert r.headers["allow"] == "POST"
    assert r.json()["error"] == "method_not_allowed"
    # Não passou adiante: o app interno nunca foi chamado.
    assert ambiente.visto == {}


async def test_get_sem_token_nenhum_tambem_e_405(ambiente):
    """O método não serve com token nenhum — e a resposta não vira oráculo."""
    async with ambiente.cliente() as c:
        r = await c.get("/mcp")
    assert r.status_code == 405
    assert "www-authenticate" not in r.headers


async def test_lifespan_e_respondido_sem_alcancar_o_app_interno(ambiente):
    """Um `run()` a mais no mesmo gerenciador de sessões seria fatal.

    O gerenciador é contexto de uso único; se um refactor trocar a rota por um
    `Mount`, o evento de ciclo de vida passaria a chegar aqui — e este teste diz
    o que acontece então: respondemos o protocolo e NÃO repassamos.
    """
    chegou = []

    async def adiante(scope, receive, send):  # pragma: no cover - não deve rodar
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
    # Montado em pedaços de propósito: um JWT inteiro no fonte acusaria no
    # scanner de segredos do CI, que não distingue exemplo de credencial real.
    jwt = ".".join(["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiJ1c3ItMSJ9", "assinatura"])
    async with ambiente.cliente() as c:
        r = await c.post("/mcp", json={}, headers={"Authorization": f"Bearer {jwt}"})
    assert r.status_code == 401
    # Formato errado nem chega a consultar o banco — e não recebe `invalid_token`,
    # que diria "o formato estava certo".
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
    """`/settings/tokens`, como toda página fora da Home, devolve `/` a quem não
    administra o sistema (`web/proxy.ts`), e o token é pessoal: o admin só cria
    token da PRÓPRIA conta. A recusa diz as duas coisas, sem mandar ninguém
    pedir o token de outra pessoa."""
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


# ── Alcance por workspace ─────────────────────────────────────────────────────


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
    """A interseção é com os workspaces ATUAIS do usuário, não com a lista do token."""
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
