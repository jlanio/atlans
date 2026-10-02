# tests/unit/test_credential_resolver_wfs.py
"""As credenciais do nó WFS chegam em `http_auth`, como as do HttpRequest.

Antes, a credencial "wfs" era resolvida, tinha o `credential_id` removido e
sumia sem nada no lugar — o nó saía anônimo. Agora ela e a nova
`geoserver_authkey` são injetadas, só com os campos que autenticam (a lista
fechada: nada de `expires_at` atravessando até o executor).
"""
import pytest

from app.services.credential_resolver import http_auth_da_credencial, inject_credentials

pytestmark = pytest.mark.asyncio

CID = "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"


def _definicao():
    return {"nodes": [{"id": "n1", "name": "WFS", "type": "datasource",
                       "properties": {"url": "https://geo.x/ows", "typeName": "ns:c", "credential_id": CID}}]}


async def test_authkey_do_geoserver_vai_em_http_auth():
    resolvido = {CID: {"type": "geoserver_authkey", "token": "K", "parameter": "authkey",
                       "location": "url", "expires_at": "2027-01-01T00:00:00Z"}}
    saida = await inject_credentials(_definicao(), pre_resolved=resolvido)
    props = saida["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K", "parameter": "authkey", "location": "url"}
    assert "credential_id" not in props


async def test_o_id_em_maiusculas_tambem_e_resolvido():
    # O resolver devolve o id canônico (minúsculas); gravado em maiúsculas no
    # nó, ele não casava com nada e a credencial sumia sem aviso — enquanto a
    # guarda do /validate, que converte para UUID, o aceitava.
    definicao = _definicao()
    definicao["nodes"][0]["properties"]["credential_id"] = CID.upper()
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "geoserver_authkey", "token": "K"}})
    props = saida["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K"} and "credential_id" not in props


async def test_credencial_wfs_basic_deixa_de_sumir():
    resolvido = {CID: {"type": "wfs", "username": "u", "password": "p"}}
    saida = await inject_credentials(_definicao(), pre_resolved=resolvido)
    assert saida["nodes"][0]["properties"]["http_auth"] == {"type": "wfs", "username": "u", "password": "p"}


async def test_a_definicao_guardada_nao_recebe_o_segredo():
    definicao = _definicao()
    await inject_credentials(definicao, pre_resolved={CID: {"type": "geoserver_authkey", "token": "K"}})
    assert "http_auth" not in definicao["nodes"][0]["properties"]  # só a cópia do despacho


async def test_http_auth_da_credencial_so_para_quem_assina_requisicao():
    # A de banco vira `connectionString`, não `http_auth`: a listagem do WFS a recusa.
    assert http_auth_da_credencial({"type": "postgresql", "connectionString": "postgresql://h/db"}) is None
    assert http_auth_da_credencial(
        {"type": "geoserver_authkey", "token": "K", "location": "header", "expires_at": "2027-01-01T00:00:00Z"}
    ) == {"type": "geoserver_authkey", "token": "K", "location": "header"}


# ── O tipo da credencial contra o que o nó declara ───────────────────────────
# Só a tela filtra por tipo; pela API e pelo assistente chega qualquer uma.

import flow.nodes.datasource.wfs  # noqa: E402,F401 — registra o nó WFS


@pytest.mark.parametrize("cred", [
    {"type": "postgresql", "connectionString": "postgresql://leitor:senha@h/db"},  # pragma: allowlist secret
    {"type": "smtp", "host": "smtp.x", "password": "p"},
    {"type": "http_bearer", "token": "T"},
])
async def test_tipo_que_o_no_nao_aceita_nao_injeta_nada_e_o_id_fica(cred):
    saida = await inject_credentials(_definicao(), pre_resolved={CID: cred})
    props = saida["nodes"][0]["properties"]
    # O nó recusa por "não pôde ser resolvida" em vez de consultar anônimo — e
    # a DSN do banco não viaja até um nó WFS.
    assert props["credential_id"] == CID
    assert "connectionString" not in props and "http_auth" not in props


async def test_o_tipo_decide_nao_a_dsn_esquecida_no_data():
    # Credencial que já foi de banco e virou authkey: a edição trocou o tipo e
    # manteve os campos, e a `connectionString` antiga ganhava.
    resolvido = {CID: {"type": "geoserver_authkey", "token": "K",
                       "connectionString": "postgresql://leitor:senha@h/db"}}  # pragma: allowlist secret
    props = (await inject_credentials(_definicao(), pre_resolved=resolvido))["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K"}
    assert "connectionString" not in props and "credential_id" not in props


async def test_no_de_banco_com_credencial_authkey_nao_recebe_nada_e_o_id_fica():
    import flow.nodes.datasource.database_spatial_query  # noqa: F401 — registra o nó
    definicao = {"nodes": [{"id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
                            "properties": {"credential_id": CID, "query": "SELECT 1"}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "geoserver_authkey", "token": "K"}})
    props = saida["nodes"][0]["properties"]
    assert props["credential_id"] == CID and "http_auth" not in props and "connectionString" not in props


async def test_o_nome_do_no_so_em_data_tambem_e_conferido():
    # O editor grava nome e propriedades em `data`; o tipo é conferido do mesmo jeito.
    definicao = {"nodes": [{"id": "n1", "type": "datasource",
                            "data": {"name": "WFS", "properties": {"url": "https://geo.x/ows", "credential_id": CID}}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "postgresql", "connectionString": "postgresql://h/db"}})
    props = saida["nodes"][0]["data"]["properties"]
    assert props["credential_id"] == CID and "connectionString" not in props


async def test_so_os_campos_do_tipo_viajam():
    # Credencial que já foi Basic e virou authkey ainda carrega usuário e senha
    # no `data`: só o que o catálogo declara para o tipo vai ao executor.
    resolvido = {CID: {"type": "geoserver_authkey", "token": "K", "username": "u", "password": "p", "location": "header"}}
    props = (await inject_credentials(_definicao(), pre_resolved=resolvido))["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K", "location": "header"}
    assert http_auth_da_credencial({"type": "wfs", "username": "u", "password": "p", "token": "T"}) == {
        "type": "wfs", "username": "u", "password": "p",
    }
    assert http_auth_da_credencial({"type": "http_bearer", "token": "T", "password": "p"}) == {"type": "http_bearer", "token": "T"}


async def test_no_que_nao_declara_a_propriedade_nao_recebe_a_credencial(monkeypatch):
    # Um nó que aceita o tipo mas não declara `http_auth`: `validate()` descarta
    # o que não está no descriptor, e o nó perdia a credencial E o id — saía
    # anônimo sem ninguém avisar. Com o id no lugar, ele recusa.
    from flow.registry import NODE_REGISTRY

    class _SemHttpAuth:
        @classmethod
        def description(cls):
            return {"name": "SemHttpAuth", "properties": [
                {"name": "credential_id", "type": "credential", "credential_types": ["http_bearer"]},
            ]}

    monkeypatch.setitem(NODE_REGISTRY, "SemHttpAuth", _SemHttpAuth)
    definicao = {"nodes": [{"id": "n1", "name": "SemHttpAuth", "type": "action", "properties": {"credential_id": CID}}]}
    props = (await inject_credentials(definicao, pre_resolved={CID: {"type": "http_bearer", "token": "T"}}))["nodes"][0]["properties"]
    assert props == {"credential_id": CID}


async def test_o_dataoutput_nao_publico_continua_com_o_id_da_credencial():
    # O webhook_token não vira DSN nem autenticação HTTP: o DataOutput usa o
    # PRÓPRIO id para proteger o artefato. Removê-lo fazia o nó recusar por
    # "exige uma credencial" com a credencial escolhida.
    import flow.nodes.outputs.data_output  # noqa: F401 — registra o nó
    definicao = {"nodes": [{"id": "n1", "name": "DataOutput", "type": "output",
                            "properties": {"isPublic": False, "credential_id": CID}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "webhook_token", "token": "T"}})
    assert saida["nodes"][0]["properties"]["credential_id"] == CID


async def test_no_fora_do_registro_segue_como_antes():
    definicao = {"nodes": [{"id": "n1", "name": "NoQueNaoExiste", "type": "datasource",
                            "properties": {"credential_id": CID}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "postgresql", "connectionString": "postgresql://h/db"}})
    props = saida["nodes"][0]["properties"]
    assert props["connectionString"] == "postgresql://h/db" and "credential_id" not in props
