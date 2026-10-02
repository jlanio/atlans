# tests/unit/test_main_rota_mcp.py
"""
O encaixe do `/mcp` na app: rotas exatas, sem JWT e sem redirect.

Quatro coisas que um refactor bem-intencionado quebraria em silêncio:

- **`add_route`, nunca `app.mount`.** Um mount consumiria o prefixo e entregaria
  ao app do SDK um caminho vazio, que não casa a rota interna dele.
- **As duas grafias respondem.** `/mcp` e `/mcp/` apontam para o mesmo app ASGI.
  Sem a segunda rota, o roteador responde 307 para a primeira, e o `Location`
  desse salto é montado com o esquema que a app enxerga — atrás do Traefik, sem
  `--proxy-headers`, isso é `http://`. Um cliente que seguisse o salto mandaria
  o token pessoal fora do TLS. Nenhuma das duas pode redirecionar.
- **Sem dependency de JWT.** A rota é montada fora do `include_router`, então não
  herda as dependencies globais da app; a autenticação aqui é o PAT. Se alguém
  passasse a registrá-la como rota da API, um cliente com token válido receberia
  401 do JWT antes de o middleware do MCP ver o Bearer.
- **Fora do OpenAPI.** O contrato do `/mcp` é o protocolo MCP, não o schema REST.
"""
from __future__ import annotations

import pytest
from starlette.routing import Route

from app.main import app


def _rota_do_mcp() -> Route:
    rotas = [r for r in app.router.routes if getattr(r, "path", None) == "/mcp"]
    assert len(rotas) == 1, f"esperava uma rota /mcp, achei {len(rotas)}"
    return rotas[0]


def _rota_com_barra() -> Route:
    rotas = [r for r in app.router.routes if getattr(r, "path", None) == "/mcp/"]
    assert len(rotas) == 1, f"esperava uma rota /mcp/, achei {len(rotas)}"
    return rotas[0]


def test_a_rota_e_exata_e_nao_um_mount():
    rota = _rota_do_mcp()
    assert isinstance(rota, Route)
    assert rota.path == "/mcp"
    # `Mount` casaria qualquer caminho sob o prefixo e exigiria a barra final.
    from starlette.routing import Mount

    assert not isinstance(rota, Mount)


def test_a_rota_aceita_qualquer_metodo_do_protocolo():
    # `methods=None` significa "todos": o streamable HTTP usa POST, GET (SSE) e
    # DELETE (encerrar sessão).
    assert _rota_do_mcp().methods is None


def test_a_rota_nao_carrega_dependency_de_jwt():
    rota = _rota_do_mcp()
    from fastapi.routing import APIRoute

    assert not isinstance(rota, APIRoute)
    assert not getattr(rota, "dependencies", None)


def test_a_rota_fica_fora_do_openapi():
    assert "/mcp" not in app.openapi().get("paths", {})


def test_a_instancia_do_servidor_fica_em_app_state():
    from app.mcp.servidor import ServidorAtlans

    assert isinstance(app.state.mcp_server, ServidorAtlans)
    # É a mesma instância que o lifespan usa para abrir o gerenciador de sessões.
    assert app.state.mcp_server.session_manager is not None


@pytest.mark.usefixtures("mock_redis")
async def test_post_sem_pat_recebe_401_pela_app_real(client):
    """Pela fixture da app inteira: middlewares, CORS e headers de segurança."""
    r = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == 'Bearer realm="atlans-mcp"'
    assert r.json()["error"] == "unauthorized"


async def test_mcp_sem_barra_nao_redireciona(client):
    """Sem 307: a URL canônica responde no primeiro salto."""
    r = await client.post("/mcp", json={})
    assert r.status_code != 307


async def test_mcp_com_barra_tambem_responde_sem_redirecionar(client):
    """`/mcp/` é rota própria, não um 307 para `/mcp`.

    O redirect que existia aqui mandava o cliente de volta por um `Location`
    montado com o esquema visto pela app — `http://` atrás de um proxy que não
    repassa `X-Forwarded-Proto`. Repetir a requisição significa repetir o header
    `Authorization`, e o token pessoal sairia em claro. Sem salto, não há como.
    """
    r = await client.post("/mcp/", json={})
    assert r.status_code != 307
    assert "location" not in r.headers
    # E chega ao mesmo lugar: o middleware do PAT, não o roteador da API.
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == 'Bearer realm="atlans-mcp"'


def test_as_duas_grafias_sao_o_mesmo_app():
    """Mesmo transporte e mesmo `session_manager` — não uma segunda montagem.

    Duas instâncias do transporte significariam dois gerenciadores de sessão, e
    o `lifespan` só inicia o da instância que existia quando ele subiu: o outro
    responderia erro de sessão em toda chamada.
    """
    from app.main import _CaminhoSemBarraFinal

    com_barra = _rota_com_barra().endpoint
    assert isinstance(com_barra, _CaminhoSemBarraFinal)
    assert com_barra._app is _rota_do_mcp().endpoint
