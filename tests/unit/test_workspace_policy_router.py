# tests/unit/test_workspace_policy_router.py
"""
Endpoints da política de execução (spec §9) e do piso (§4.5, Q10).

A garantia vem das dependencies/gates dos handlers; estes testes falham se um
endpoint for movido para fora do gate — como test_admin_workspaces_router faz
para a lixeira.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.fixture
def db_override(client):
    from app.api.dependencies import get_db
    from app.main import app

    db = MagicMock(); db.commit = AsyncMock(); db.add = MagicMock()

    async def _fake_db():
        yield db

    app.dependency_overrides[get_db] = _fake_db
    yield client, db
    app.dependency_overrides.pop(get_db, None)


def _ws():
    ws = MagicMock(); ws.id_hash = "ws-test-001"; ws.name = "Bacia"
    ws.target_executor_id = None; ws.fallback_terminal = "fail"; ws.isolation_floor = "none"
    return ws


def _saida():
    from app.api.routers.workspace_router import WorkspacePolicyOut
    return WorkspacePolicyOut(
        workspace_id="ws-test-001", mode="pool", primary=[], fallback=[],
        fallback_terminal="fail", effective_terminal="fail", isolation_floor="none",
        available_primary=0, available_fallback=0, pool=None, policy_routing_enabled=False,
    )


# ── inclusão de membro ────────────────────────────────────────────────────────

async def test_viewer_nao_inclui_membro(db_override):
    client, _ = db_override
    negado = AsyncMock(side_effect=HTTPException(status_code=403, detail="Requer role 'admin'."))
    with patch("app.api.routers.workspace_router._get_admin_managed_workspace", negado):
        resp = await client.post("/workspaces/ws-test-001/executors/ex-1?tier=1")
    assert resp.status_code == 403


async def test_admin_do_workspace_inclui_no_nivel_pedido(db_override):
    client, db = db_override
    add = AsyncMock()
    with patch("app.api.routers.workspace_router._get_admin_managed_workspace", AsyncMock(return_value=_ws())), \
         patch("app.api.routers.workspace_router._accessible_ids_for", AsyncMock(return_value={"ex-1"})), \
         patch("app.api.routers.workspace_router._policy_out", AsyncMock(return_value=_saida())), \
         patch("app.services.workspace_executor_service.add_member", add):
        resp = await client.post("/workspaces/ws-test-001/executors/ex-1?tier=2")
    assert resp.status_code == 200, resp.text
    assert add.await_args.args[2:4] == ("ex-1", 2)
    assert add.await_args.kwargs["accessible_ids"] == {"ex-1"}


async def test_tier_fora_do_intervalo_e_422(db_override):
    client, _ = db_override
    with patch("app.api.routers.workspace_router._get_admin_managed_workspace", AsyncMock(return_value=_ws())):
        resp = await client.post("/workspaces/ws-test-001/executors/ex-1?tier=3")
    assert resp.status_code == 422


async def test_erro_de_politica_vira_422_com_mensagem(db_override):
    from app.core.exceptions import WorkspacePolicyError
    client, _ = db_override
    with patch("app.api.routers.workspace_router._get_admin_managed_workspace", AsyncMock(return_value=_ws())), \
         patch("app.api.routers.workspace_router._accessible_ids_for", AsyncMock(return_value=None)), \
         patch("app.services.workspace_executor_service.add_member",
               AsyncMock(side_effect=WorkspacePolicyError("'pool-a' pertence ao pool compartilhado"))):
        resp = await client.post("/workspaces/ws-test-001/executors/pool-a?tier=1")
    assert resp.status_code == 422
    # Exceções de domínio saem pelo handler global: {"error": code, "message": detail}.
    corpo = resp.json()
    assert corpo["error"] == "workspace_policy_invalid"
    assert "pool compartilhado" in corpo["message"]


# ── terminal ──────────────────────────────────────────────────────────────────

async def test_terminal_pool_sob_piso_e_403(db_override):
    from app.core.exceptions import WorkspacePolicyFloorError
    client, _ = db_override
    with patch("app.api.routers.workspace_router._get_admin_managed_workspace", AsyncMock(return_value=_ws())), \
         patch("app.services.workspace_executor_service.set_terminal",
               AsyncMock(side_effect=WorkspacePolicyFloorError("piso"))):
        resp = await client.put("/workspaces/ws-test-001/fallback", json={"terminal": "pool"})
    assert resp.status_code == 403


async def test_terminal_invalido_e_422_antes_de_tocar_no_servico(db_override):
    client, _ = db_override
    with patch("app.api.routers.workspace_router._get_admin_managed_workspace", AsyncMock(return_value=_ws())), \
         patch("app.services.workspace_executor_service.set_terminal", AsyncMock()) as st:
        resp = await client.put("/workspaces/ws-test-001/fallback", json={"terminal": "esperar"})
    assert resp.status_code == 422
    st.assert_not_awaited()


# ── leitura ───────────────────────────────────────────────────────────────────

async def test_leitura_exige_ser_membro(db_override):
    client, _ = db_override
    negado = AsyncMock(side_effect=HTTPException(status_code=403, detail="não é membro"))
    with patch("app.api.routers.workspace_router._get_visible_workspace", negado):
        resp = await client.get("/workspaces/ws-test-001/executors")
    assert resp.status_code == 403


async def test_leitura_devolve_a_politica_com_a_flag(db_override):
    client, _ = db_override
    with patch("app.api.routers.workspace_router._get_visible_workspace", AsyncMock(return_value=(_ws(), "viewer"))), \
         patch("app.api.routers.workspace_router._policy_out", AsyncMock(return_value=_saida())):
        resp = await client.get("/workspaces/ws-test-001/executors")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["mode"] == "pool" and corpo["policy_routing_enabled"] is False


# ── piso do admin da plataforma ──────────────────────────────────────────────

async def test_piso_negado_para_usuario_comum(client):
    resp = await client.put("/admin/workspaces/ws-test-001/isolation-floor", json={"floor": "no_pool"})
    assert resp.status_code == 403


async def test_piso_pelo_admin_forca_terminal_e_avisa(db_override, mock_current_user):
    client, db = db_override
    mock_current_user.role = "admin"; mock_current_user.username = "admin-test"
    ws = _ws(); ws.fallback_terminal = "pool"
    res = MagicMock(); res.scalar_one_or_none = MagicMock(return_value=ws)
    db.execute = AsyncMock(return_value=res)
    from app.services import workspace_executor_service as svc
    com_principal = svc.WorkspacePolicy(workspace_id="ws-test-001", primary=[MagicMock()])
    with patch("app.services.execution_alert_service.notify_floor_forced", AsyncMock()) as avisar, \
         patch("app.services.workspace_executor_service.load_policy", AsyncMock(return_value=com_principal)):
        resp = await client.put("/admin/workspaces/ws-test-001/isolation-floor", json={"floor": "no_pool"})
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["isolation_floor"] == "no_pool" and corpo["fallback_terminal"] == "fail"
    assert corpo["terminal_forced_to_fail"] is True
    avisar.assert_awaited_once()


async def test_piso_sem_principal_nao_avisa(db_override, mock_current_user):
    # "Passou a ser isolado" só faz sentido para quem tem executor dedicado.
    client, db = db_override
    mock_current_user.role = "admin"; mock_current_user.username = "admin-test"
    ws = _ws(); ws.fallback_terminal = "pool"
    res = MagicMock(); res.scalar_one_or_none = MagicMock(return_value=ws)
    db.execute = AsyncMock(return_value=res)
    from app.services import workspace_executor_service as svc
    sem_principal = svc.WorkspacePolicy(workspace_id="ws-test-001")
    with patch("app.services.execution_alert_service.notify_floor_forced", AsyncMock()) as avisar, \
         patch("app.services.workspace_executor_service.load_policy", AsyncMock(return_value=sem_principal)):
        resp = await client.put("/admin/workspaces/ws-test-001/isolation-floor", json={"floor": "no_pool"})
    assert resp.status_code == 200, resp.text
    avisar.assert_not_awaited()



async def test_admin_lista_a_politica_de_todos_os_workspaces(db_override, mock_current_user):
    """Tela de admin "Piso de isolamento": uma linha por workspace vivo, com o
    modo derivado das CONTAGENS dos níveis — sem carregar executores."""
    client, db = db_override
    mock_current_user.role = "admin"; mock_current_user.username = "admin-test"

    def _ws(id_hash, name, owner, floor="none", terminal="fail"):
        w = MagicMock(); w.id_hash = id_hash; w.name = name; w.owner_id = owner
        w.is_default = False; w.isolation_floor = floor; w.fallback_terminal = terminal
        return w

    lista = MagicMock(); lista.scalars = MagicMock(return_value=MagicMock(
        all=MagicMock(return_value=[_ws("ws-1", "Bacia", "u-1", terminal="pool"), _ws("ws-2", "Defesa", "u-2", floor="no_pool")]),
    ))
    contagem = MagicMock(); contagem.all = MagicMock(return_value=[("ws-1", 1, 2), ("ws-1", 2, 1)])
    donos = MagicMock(); donos.all = MagicMock(return_value=[("u-1", "jl")])
    db.execute = AsyncMock(side_effect=[lista, contagem, donos])

    resp = await client.get("/admin/workspaces/policies")
    assert resp.status_code == 200, resp.text
    linhas = {l["id_hash"]: l for l in resp.json()}
    assert linhas["ws-1"]["mode"] == "dedicated_pool"
    assert linhas["ws-1"]["primary_count"] == 2 and linhas["ws-1"]["fallback_count"] == 1
    assert linhas["ws-1"]["owner_username"] == "jl"
    # Sem principal e sob piso: isolado com zero executores, terminal efetivo fail.
    assert linhas["ws-2"]["mode"] == "isolated"
    assert linhas["ws-2"]["effective_terminal"] == "fail" and linhas["ws-2"]["primary_count"] == 0
    assert linhas["ws-2"]["owner_username"] is None


async def test_lista_de_politicas_exige_admin(db_override, mock_current_user):
    client, _ = db_override
    mock_current_user.role = "user"
    resp = await client.get("/admin/workspaces/policies")
    assert resp.status_code == 403
