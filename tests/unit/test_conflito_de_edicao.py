# tests/unit/test_conflito_de_edicao.py
"""
Two editors on one workflow: the second save no longer erases the first.

The editor sends the whole definition on every save. A tab that opened the
workflow before someone else saved it — another tab, another person, an agent
through the MCP — wrote over that change and went on showing "Salvo": edges
added elsewhere vanished, and nothing said so. GET and PUT now return the
definition's tag; the editor sends it back as `expected_etag` and a stale save is
refused with 409.
"""
from __future__ import annotations

import json

import pytest

from app.api.routers import workflows_router as WR
from app.schemas.workflow import WorkflowUpdate
from app.services.workflow_version_service import definition_etag

DEF = {
    "nodes": [{"id": "a", "name": "ReadGeoJSON", "type": "datasource", "properties": {"path": "x.geojson"}}],
    "edges": [{"source": "a", "target": "b", "from_key": "output"}],
    "viewport": {"x": 0, "y": 0, "zoom": 1},
}


def _copia(**mudancas):
    d = json.loads(json.dumps(DEF))
    d.update(mudancas)
    return d


# ── The tag ───────────────────────────────────────────────────────────────────

def test_mesma_definicao_mesma_etiqueta():
    assert definition_etag(DEF) == definition_etag(_copia())


def test_mover_a_camera_nao_muda_a_etiqueta():
    assert definition_etag(DEF) == definition_etag(_copia(viewport={"x": 300, "y": -40, "zoom": 2}))


def test_religar_uma_aresta_muda_a_etiqueta():
    outra = _copia(edges=[{"source": "a", "target": "b", "from_key": "metadata"}])
    assert definition_etag(DEF) != definition_etag(outra)


def test_etiqueta_nao_depende_do_valor_de_um_segredo():
    # The tag goes to viewers too: a hash over the connection string would let
    # them test guesses offline.
    com = lambda senha: {"nodes": [{"id": "p", "name": "PostgreSQL", "properties": {
        "connectionString": f"postgresql://u:{senha}@db/x"}}], "edges": []}
    assert definition_etag(com("a")) == definition_etag(com("b"))


def test_definicao_cifrada_e_decifrada_tem_a_mesma_etiqueta():
    from app.core.utils.encryption import encrypt_workflow_connections
    claro = {"nodes": [{"id": "p", "name": "PostgreSQL", "properties": {
        "connectionString": "postgresql://u:s@db/x"}}], "edges": []}
    cifrado = encrypt_workflow_connections(json.loads(json.dumps(claro)))
    assert cifrado["nodes"][0]["properties"]["connectionString"].startswith("gAAAA")
    assert definition_etag(cifrado) == definition_etag(claro)


def test_definicao_vazia_tem_etiqueta():
    assert definition_etag(None) == definition_etag({})


# ── The route ─────────────────────────────────────────────────────────────────

class _Wf:
    id_hash = "wf-1"
    workspace_id = "ws-1"
    definition = DEF


class _User:
    id_hash = "u-1"


class _Resultado:
    def __init__(self, definition):
        self.definition = definition


@pytest.fixture
def rota(monkeypatch):
    monkeypatch.setattr(WR.limiter, "enabled", False)
    monkeypatch.setattr(WR, "_recusar_segredo", lambda *a, **k: None)

    async def _sem_subfluxo(*a, **k):
        return []
    import flow.utils.workflow_contract as contrato
    monkeypatch.setattr(contrato, "validate_subworkflow_references_against_db", _sem_subfluxo)

    gravados = []

    class _Service:
        async def update_workflow(self, id_hash, workflow_in, **kw):
            gravados.append(workflow_in.definition)
            return _Resultado(workflow_in.definition)

    async def salvar(definition, expected_etag):
        return await WR.update_workflow(
            request=None, workflow_in=WorkflowUpdate(definition=definition),
            expected_etag=expected_etag, service=_Service(), wf=_Wf(), db=None, current_user=_User(),
        )

    return salvar, gravados


async def test_salvar_por_cima_de_outra_edicao_e_recusado(rota):
    salvar, gravados = rota
    # The tab loaded the definition BEFORE someone else rewired an edge.
    etiqueta_antiga = definition_etag(_copia(edges=[]))
    resposta = await salvar(_copia(edges=[]), etiqueta_antiga)

    assert resposta.status_code == 409
    corpo = json.loads(resposta.body)
    assert corpo["error"] == "definition_conflict"
    assert "recarregue" in corpo["detail"]
    assert gravados == []


async def test_salvar_com_a_etiqueta_atual_grava_e_devolve_a_nova(rota):
    salvar, gravados = rota
    nova = _copia(edges=[])
    resposta = await salvar(nova, definition_etag(DEF))

    assert gravados == [nova]
    assert resposta.definition_etag == definition_etag(nova)


async def test_sem_etiqueta_nada_muda(rota):
    # MCP and any older client: the save goes through as before.
    salvar, gravados = rota
    await salvar(_copia(edges=[]), None)
    assert len(gravados) == 1


async def test_leitura_devolve_a_etiqueta():
    from datetime import datetime

    class _Lido:
        id = 1
        id_hash = "wf-1"
        name = "x"
        flag_ative = True
        description = None
        version = None
        priority = 0
        workspace_id = "ws-1"
        group_id = None
        params_schema = None
        notification_url = None
        definition = DEF
        portal_access = "disabled"
        portal_shared_with = None
        created_at = datetime(2026, 1, 1)
        updated_at = datetime(2026, 1, 1)
        deleted_at = None
        schedule_notices = []

    dados = await WR.read_workflow(wf=_Lido())
    assert dados.definition_etag == definition_etag(DEF)
