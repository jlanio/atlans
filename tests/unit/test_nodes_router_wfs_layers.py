# tests/unit/test_nodes_router_wfs_layers.py
"""`GET /nodes/wfs/layers` stays the same for the editor.

The route became a thin wrapper of `fontes_service.listar_camadas_wfs` — the SAME
probe the source catalog uses. What the editor sees doesn't change: the body
`{layers: [{name, title}]}` and the statuses (400 invalid URL, 403 SSRF, 502
server, 504 timeout, 404 no layers).

With `credential_id`, it lists as the node's execution would see it (a
GeoServer's protected layers), within the /validate scope: the requester's
credentials and, for operator or above in the given workflow's workspace
(`workflow_id`), those shared with it — the workflow states the workspace, not
the client.
"""
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import flow.utils.geo_helpers as geo
from app.services import fontes_service as fs

ROTA = "/nodes/wfs/layers"


@pytest.fixture
def sem_dns(monkeypatch):
    """SSRF validation resolves DNS; here it just lets things through."""
    monkeypatch.setattr(geo, "validate_url_ssrf", lambda url: None)


async def test_devolve_as_camadas_do_servico_com_a_url_normalizada(client, monkeypatch, sem_dns):
    chamadas: list[str] = []

    async def _listar(url, version="2.0.0", *, auth=None):
        chamadas.append(url)
        assert auth is None  # with no credential on the node, the listing is anonymous
        return [{"name": "Funai:tis_poligonais", "title": "Terras indígenas"}]

    monkeypatch.setattr(fs, "listar_camadas_wfs", _listar)
    r = await client.get(ROTA, params={"url": "https://geoserver.funai.gov.br/geoserver/ows?service=WFS&request=GetCapabilities"})
    assert r.status_code == 200
    assert r.json() == {"layers": [{"name": "Funai:tis_poligonais", "title": "Terras indígenas"}]}
    # The input's query string is discarded before probing.
    assert chamadas == ["https://geoserver.funai.gov.br/geoserver/ows"]


@pytest.mark.parametrize(
    "codigo,status",
    [("timeout", 504), ("http_status", 502), ("sem_camadas", 404), ("ssrf", 403), ("xml", 502), ("rede", 502)],
)
async def test_traduz_os_erros_da_sondagem_nos_status_de_sempre(client, monkeypatch, sem_dns, codigo, status):
    async def _falha(url, version="2.0.0", *, auth=None):
        raise fs.SondagemError(codigo, "deu errado", status=503 if codigo == "http_status" else None)

    monkeypatch.setattr(fs, "listar_camadas_wfs", _falha)
    r = await client.get(ROTA, params={"url": "https://x.gov.br/ows"})
    assert r.status_code == status
    assert r.json()["message"]


async def test_url_sem_http_e_400_sem_sondar(client, monkeypatch, sem_dns):
    async def _nao_chama(url, version="2.0.0", *, auth=None):
        raise AssertionError("não devia sondar")

    monkeypatch.setattr(fs, "listar_camadas_wfs", _nao_chama)
    r = await client.get(ROTA, params={"url": "ftp://x.gov.br/ows"})
    assert r.status_code == 400


# ── With the node's credential ─────────────────────────────────────────────────

CID = "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"
CHAVE = "c0ffee-SEGREDO-42"
USUARIO = "usr-test-001"  # the `client`'s one


@pytest.fixture
def banco(monkeypatch):
    """The session (with the workflows that exist), the workspace role and the
    resolver stubbed; records the requested scope."""
    import app.core.authorization.credential_loader as loader
    import app.core.authorization.workflow_access as acesso
    import app.core.db as db

    estado = SimpleNamespace(
        papel="operator", credenciais={}, escopos=[], commits=0, fluxos={"wf1": "ws1"}, consultas=[],
    )

    class _Sessao:
        async def commit(self):
            estado.commits += 1

        async def execute(self, stmt):
            # The workflow's workspace query, compiled: what it asks for is in plain view.
            sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            estado.consultas.append(sql)
            achado = next((ws for wf, ws in estado.fluxos.items() if f"'{wf}'" in sql), None)
            return SimpleNamespace(scalar_one_or_none=lambda: achado)

    @asynccontextmanager
    async def _sessao():
        yield _Sessao()

    async def _papel(db, workspace_id, user_id):
        return estado.papel

    async def _resolver(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):
        estado.escopos.append((list(ids), set(allowed_owner_ids or ()), shared_workspace_id))
        return {cid: estado.credenciais[cid] for cid in ids if cid in estado.credenciais}

    monkeypatch.setattr(db, "get_session_async", _sessao)
    monkeypatch.setattr(acesso, "get_workspace_member_role", _papel)
    monkeypatch.setattr(loader, "resolve_credentials_from_ids", _resolver)
    return estado


@pytest.fixture
def listagem(monkeypatch, sem_dns):
    """The credentials the route listed with (one per request that reached the network)."""
    usadas: list = []

    async def _listar(url, version="2.0.0", *, auth=None):
        usadas.append(auth)
        return [{"name": "ns:protegida", "title": "Protegida"}]

    monkeypatch.setattr(fs, "listar_camadas_wfs", _listar)
    return usadas


async def test_lista_com_a_credencial_propria(client, banco, listagem):
    banco.credenciais = {CID: {"type": "geoserver_authkey", "token": CHAVE, "expires_at": "2099-01-01T00:00:00Z"}}
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID})
    assert r.status_code == 200 and r.json()["layers"][0]["name"] == "ns:protegida"
    (auth,) = listagem
    assert (auth.tipo, auth.segredo, auth.nome, auth.no_cabecalho) == ("authkey", CHAVE, "authkey", False)
    # Without a workspace, the scope is only the requester's.
    assert banco.escopos == [([CID], {USUARIO}, None)]
    assert banco.commits == 1  # the usage stamp


@pytest.mark.parametrize("papel, compartilhado", [
    ("owner", "ws1"), ("admin", "ws1"), ("operator", "ws1"), ("editor", None), ("viewer", None),
])
async def test_compartilhadas_do_workspace_do_fluxo_so_para_quem_executa(client, banco, listagem, papel, compartilhado):
    banco.papel = papel
    banco.credenciais = {CID: {"type": "wfs", "username": "leitor", "password": CHAVE}}
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID, "workflow_id": "wf1"})
    assert r.status_code == 200
    assert banco.escopos == [([CID], {USUARIO}, compartilhado)]
    (consulta,) = banco.consultas
    assert "deleted_at IS NULL" in consulta  # a workflow in the trash grants no scope


async def test_quem_nao_e_do_workspace_do_fluxo_nao_resolve_nada(client, banco, listagem):
    banco.papel = None
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID, "workflow_id": "wf1"})
    assert r.status_code == 403
    assert banco.escopos == [] and listagem == []


async def test_fluxo_inexistente_e_404_e_o_cliente_nao_escolhe_o_workspace(client, banco, listagem):
    banco.credenciais = {CID: {"type": "geoserver_authkey", "token": CHAVE}}
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID, "workflow_id": "wf-sumido"})
    assert r.status_code == 404
    assert banco.escopos == [] and listagem == []
    # `workspace_id` is no longer a parameter: the reach comes from a workflow that
    # exists (and its workspace), not from a workspace id chosen by hand.
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID, "workspace_id": "ws1"})
    assert r.status_code == 200 and banco.escopos == [([CID], {USUARIO}, None)]


async def test_credencial_fora_do_alcance_e_403_e_nao_lista_anonimo(client, banco, listagem):
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID})
    assert r.status_code == 403 and "não está ao seu alcance" in r.json()["message"]
    assert listagem == []


@pytest.mark.parametrize("cred", [
    {"type": "postgresql", "connectionString": "postgresql://h/db"},
    {"type": "http_bearer", "token": CHAVE},
])
async def test_credencial_que_nao_serve_ao_wfs_e_400(client, banco, listagem, cred):
    banco.credenciais = {CID: cred}
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID})
    assert r.status_code == 400 and "não serve para o nó WFS" in r.json()["message"]
    assert CHAVE not in r.text and listagem == []


async def test_id_malformado_e_400_e_maiusculas_valem(client, banco, listagem):
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": "nao-e-uuid"})
    assert r.status_code == 400 and banco.escopos == []

    banco.credenciais = {CID: {"type": "geoserver_authkey", "token": CHAVE}}
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID.upper()})
    assert r.status_code == 200 and banco.escopos[-1][0] == [CID]


async def test_o_erro_da_sondagem_nao_devolve_a_chave(client, banco, monkeypatch, sem_dns):
    banco.credenciais = {CID: {"type": "geoserver_authkey", "token": CHAVE}}

    async def _falha(url, version="2.0.0", *, auth=None):
        raise fs.SondagemError("ssrf", f"bloqueado: https://geo.x.gov.br/ows?authkey={CHAVE}")

    monkeypatch.setattr(fs, "listar_camadas_wfs", _falha)
    r = await client.get(ROTA, params={"url": "https://geo.x.gov.br/ows", "credential_id": CID})
    assert r.status_code == 403
    assert CHAVE not in r.text and "authkey=***" in r.json()["message"]
