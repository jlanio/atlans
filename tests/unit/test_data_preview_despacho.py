# tests/unit/test_data_preview_despacho.py
"""
`data_preview` from the editor's request to the executor's envelope, under the
admin switch (docs/specs/node-data-panels.md §4.1 and §4.3).

Real data leaves the executor only when the editor asked AND the admin did not
turn samples off; the response tells the editor which of the two happened.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.system_config import SystemConfig
from app.services import amostras_de_dados as amostras
from app.services import workflow_execution_service as wes
from tests.unit.test_run_trigger_source import (
    _patches_do_start_analysis,
    _service_with_captured_dispatch,
)


def _db_com_config(valor=..., *, ausente=False):
    db = MagicMock()
    cfg = None if ausente else SystemConfig(key=amostras.CONFIG_KEY, value=valor)
    db.get = AsyncMock(return_value=cfg)
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


# ── The switch ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("valor,esperado", [
    (True, True), (False, False), ("false", False), ("true", True), (None, True), (0, False),
])
async def test_valor_gravado_da_chave(valor, esperado):
    assert await amostras.amostras_habilitadas(_db_com_config(valor)) is esperado


@pytest.mark.asyncio
async def test_sem_linha_gravada_as_amostras_ficam_ligadas():
    assert await amostras.amostras_habilitadas(_db_com_config(ausente=True)) is True


@pytest.mark.asyncio
async def test_definir_cria_ou_atualiza_a_linha():
    db = _db_com_config(ausente=True)
    assert await amostras.definir_amostras(db, False) is False
    criada = db.add.call_args.args[0]
    assert criada.key == amostras.CONFIG_KEY and criada.value is False

    db = _db_com_config(True)
    await amostras.definir_amostras(db, False)
    assert db.get.return_value.value is False
    db.add.assert_not_called()


# ── start_analysis ───────────────────────────────────────────────────────────

async def _iniciar(data_preview: bool, habilitado: bool):
    service, capturado = _service_with_captured_dispatch()
    leitura = AsyncMock(return_value=habilitado)
    a, b, c = _patches_do_start_analysis()
    with a, b, c, patch("app.services.workflow_service.amostras_habilitadas", leitura):
        result = await service.start_analysis(
            "wf-1", inputs={}, autenticar_entrada=False, data_preview=data_preview,
        )
    return result, capturado, leitura


@pytest.mark.asyncio
async def test_pedido_do_editor_com_a_chave_ligada_chega_ao_despacho():
    result, capturado, _ = await _iniciar(True, True)
    assert capturado["data_preview"] is True
    assert result.data_preview is True


@pytest.mark.asyncio
async def test_admin_desligou_vence_o_pedido():
    result, capturado, _ = await _iniciar(True, False)
    assert capturado["data_preview"] is False
    assert result.data_preview is False


@pytest.mark.asyncio
async def test_sem_pedido_nao_le_a_chave():
    result, capturado, leitura = await _iniciar(False, True)
    assert capturado["data_preview"] is False
    assert result.data_preview is False
    leitura.assert_not_awaited()


# ── The envelope ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("valor", [True, False])
async def test_envelope_leva_data_preview(valor):
    wf = SimpleNamespace(id_hash="wf-1", workspace_id="ws-1", pinned_outputs=None, pin_metadata=None)
    with patch.object(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d)):
        corpo = await wes._serializar_payload(
            wf, {"nodes": [], "edges": []}, "job-1", None, False,
            data_preview=valor, pre_resolved={}, disabled_nodes=None, subworkflow_definitions=None,
        )
    assert json.loads(corpo)["data_preview"] is valor


# ── Routes ───────────────────────────────────────────────────────────────────

@pytest.fixture
def rota_execute(client, mock_current_user):
    from app.api.dependencies import get_accessible_workflow_with_role, get_workflow_service
    from app.main import app
    from tests.unit.test_run_trigger_source import _wf

    svc = MagicMock()
    async def _svc():
        return svc
    async def _wf_with_role(id_hash: str):
        return _wf(id_hash), "owner"
    app.dependency_overrides[get_workflow_service] = _svc
    app.dependency_overrides[get_accessible_workflow_with_role] = _wf_with_role
    yield client, svc
    for dep in (get_workflow_service, get_accessible_workflow_with_role):
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("efetivo", [True, False])
async def test_execute_repassa_o_pedido_e_responde_o_efetivo(rota_execute, efetivo):
    ac, svc = rota_execute
    svc.start_analysis = AsyncMock(return_value=wes.DispatchResult(id="task-1", data_preview=efetivo))
    resp = await ac.post("/workflows/wf-1/execute", json={"inputs": {}, "data_preview": True})
    assert resp.status_code == 202, resp.text
    assert svc.start_analysis.await_args.kwargs["data_preview"] is True
    assert resp.json()["data_preview"] is efetivo


@pytest.mark.asyncio
async def test_execute_sem_o_campo_nao_pede_amostras(rota_execute):
    ac, svc = rota_execute
    svc.start_analysis = AsyncMock(return_value=wes.DispatchResult(id="task-1"))
    resp = await ac.post("/workflows/wf-1/execute", json={"inputs": {}})
    assert resp.status_code == 202, resp.text
    assert svc.start_analysis.await_args.kwargs["data_preview"] is False
    assert resp.json()["data_preview"] is False


@pytest.fixture
def rota_admin(client, mock_current_user):
    from app.api.dependencies import get_db
    from app.main import app

    db = _db_com_config(ausente=True)
    async def _db():
        return db
    app.dependency_overrides[get_db] = _db
    yield client, db, mock_current_user
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_rotas_do_admin_leem_e_gravam(rota_admin):
    ac, db, usuario = rota_admin
    usuario.role = "admin"
    resp = await ac.get("/admin/workflows/data-preview")
    assert resp.status_code == 200 and resp.json() == {"enabled": True}
    resp = await ac.put("/admin/workflows/data-preview", json={"enabled": False})
    assert resp.status_code == 200 and resp.json() == {"enabled": False}
    assert db.add.call_args.args[0].value is False


@pytest.mark.asyncio
async def test_rotas_do_admin_recusam_quem_nao_e_admin_e_corpo_invalido(rota_admin):
    ac, _, usuario = rota_admin
    usuario.role = "editor"
    assert (await ac.get("/admin/workflows/data-preview")).status_code == 403
    assert (await ac.put("/admin/workflows/data-preview", json={"enabled": False})).status_code == 403
    usuario.role = "admin"
    assert (await ac.put("/admin/workflows/data-preview", json={"enabled": "talvez"})).status_code == 422
