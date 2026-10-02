# tests/unit/test_nodes_router_wfs_layers.py
"""`GET /nodes/wfs/layers` continua igual para o editor.

A rota virou um wrapper fino de `fontes_service.listar_camadas_wfs` — a MESMA
sondagem que o catálogo de fontes usa. O que o editor vê não muda: o corpo
`{layers: [{name, title}]}` e os status (400 URL inválida, 403 SSRF, 502
servidor, 504 timeout, 404 sem camadas).

Com `credential_id`, lista como a execução do nó veria (as camadas protegidas
de um GeoServer), no escopo do /validate: as credenciais de quem pede e, para
operator ou acima no workspace do fluxo informado (`workflow_id`), as
compartilhadas com ele — é o fluxo que diz o workspace, não o cliente.
"""
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import flow.utils.geo_helpers as geo
from app.services import fontes_service as fs

ROTA = "/nodes/wfs/layers"


@pytest.fixture
def sem_dns(monkeypatch):
    """A validação SSRF resolve DNS; aqui ela só deixa passar."""
    monkeypatch.setattr(geo, "validate_url_ssrf", lambda url: None)


async def test_devolve_as_camadas_do_servico_com_a_url_normalizada(client, monkeypatch, sem_dns):
    chamadas: list[str] = []

    async def _listar(url, version="2.0.0", *, auth=None):
        chamadas.append(url)
        assert auth is None  # sem credencial no nó, a listagem é anônima
        return [{"name": "Funai:tis_poligonais", "title": "Terras indígenas"}]

    monkeypatch.setattr(fs, "listar_camadas_wfs", _listar)
    r = await client.get(ROTA, params={"url": "https://geoserver.funai.gov.br/geoserver/ows?service=WFS&request=GetCapabilities"})
    assert r.status_code == 200
    assert r.json() == {"layers": [{"name": "Funai:tis_poligonais", "title": "Terras indígenas"}]}
    # A query do input é descartada antes de sondar.
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


# ── Com a credencial do nó ─────────────────────────────────────────────────────

CID = "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"
CHAVE = "c0ffee-SEGREDO-42"
USUARIO = "usr-test-001"  # o do `client`


@pytest.fixture
def banco(monkeypatch):
    """A sessão (com os fluxos que existem), o papel no workspace e o resolver
    dublados; guarda o escopo pedido."""
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
            # A consulta do workspace do fluxo, compilada: o que ela pede fica à vista.
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
    """As credenciais com que a rota listou (uma por pedido que chegou à rede)."""
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
    # Sem workspace, o escopo é só o de quem pede.
    assert banco.escopos == [([CID], {USUARIO}, None)]
    assert banco.commits == 1  # o carimbo de uso


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
    assert "deleted_at IS NULL" in consulta  # fluxo na lixeira não dá escopo


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
    # `workspace_id` deixou de ser parâmetro: o alcance vem de um fluxo que
    # existe (e do workspace dele), não de um id de workspace escolhido à mão.
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
