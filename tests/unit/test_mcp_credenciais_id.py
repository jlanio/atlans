# tests/unit/test_mcp_credenciais_id.py
"""`list_credentials` delivers the id the resolver looks for.

The definition carries `credential_id` = `Credential.id` (the primary key: it is what the
screen saves and what `resolve_credentials_from_ids` queries). The tool delivered the
`id_hash` — another, independent UUID —, and every credential chosen by the
assistant failed resolution: the node refused with "credencial não resolvida" (unresolved credential).
"""
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import app.mcp.tools.credenciais as tool

pytestmark = pytest.mark.asyncio


async def test_o_id_entregue_e_a_chave_primaria(monkeypatch):
    chave = uuid.uuid4()
    credencial = SimpleNamespace(
        id=chave, id_hash=str(uuid.uuid4()), type="geoserver_authkey", owner_id="u1",
        workspace_id=None, expires_at=None, last_used_at=None, name="GeoServer", description=None,
    )

    @asynccontextmanager
    async def _sessao():
        yield object()

    async def _listar(db, owner_id, workspace_ids):
        return [credencial]

    monkeypatch.setattr(tool, "escopo_da_chamada", lambda ctx: SimpleNamespace(user_id="u1", workspace_ids={"ws1"}))
    monkeypatch.setattr(tool, "exigir_escopo", lambda escopo, permissao: None)
    monkeypatch.setattr(tool.infra, "sessao", _sessao)
    monkeypatch.setattr(tool, "list_credential_metadata", _listar)

    resposta = await tool.list_credentials(ctx=None)
    (item,) = resposta["items"]
    assert item["id"] == str(chave) != credencial.id_hash
