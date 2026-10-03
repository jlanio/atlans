# tests/integration/test_workflow_move_contract.py
"""HTTP contract of POST /workflows/{id}/move and /move/preview.

Exercises the real app: routing, Pydantic validation of the body and the
response, and authorization in both workspaces. The mutation logic is covered
in tests/unit/test_workflow_move.py — here the target is the HTTP edge.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


ORIGEM = "ws-test-001"
DESTINO = "ws-destino"


def _fake_workflow(id_hash="wf-abc123", workspace_id=ORIGEM):
    wf = MagicMock()
    wf.id_hash = id_hash
    wf.name = "Workflow de Teste"
    wf.workspace_id = workspace_id
    wf.flag_ative = True
    wf.deleted_at = None
    wf.definition = {"nodes": [], "edges": []}
    return wf


def _resultado(**kw):
    base = {
        "id": "wf-abc123", "name": "Workflow de Teste", "renamed": False,
        "from_workspace_id": ORIGEM, "to_workspace_id": DESTINO,
        "dry_run": False, "warnings": [],
    }
    base.update(kw)
    return base


@pytest.fixture
def move_deps(client):
    """Real app with the service stubbed and the `owner` role at the source.

    `get_workspace_member_role` is patched in the guards module
    (`workflow_access`, where `exigir_papel_no_workspace` looks it up; it is
    not an injectable dependency) — it decides the role at the DESTINATION.
    The source's role comes from the override of
    `get_accessible_workflow_with_role`, and the comparison is still the one
    in `workflow_com_papel`.
    """
    from unittest.mock import patch

    from app.main import app
    from app.api.dependencies import (
        get_db, get_workflow_service, get_accessible_workflow_with_role,
    )

    svc = AsyncMock()
    svc.move_workflow = AsyncMock(return_value=_resultado())

    async def _svc():
        return svc

    async def _wf_with_role(id_hash: str):
        return _fake_workflow(id_hash=id_hash), "owner"

    # The route takes `db` to resolve the role at the destination; without an
    # override, the real get_db tries to open a connection.
    async def _db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_workflow_service] = _svc
    app.dependency_overrides[get_accessible_workflow_with_role] = _wf_with_role

    with patch(
        "app.core.authorization.workflow_access.get_workspace_member_role",
        new=AsyncMock(return_value="owner"),
    ) as papel_destino:
        yield client, svc, papel_destino

    for dep in [get_db, get_workflow_service, get_accessible_workflow_with_role]:
        app.dependency_overrides.pop(dep, None)


# ── Caminho feliz ────────────────────────────────────────────────────────────

class TestMove:
    async def test_move_devolve_200(self, move_deps):
        ac, _, _ = move_deps
        res = await ac.post(
            "/workflows/wf-abc123/move", json={"target_workspace_id": DESTINO},
        )
        assert res.status_code == 200

    async def test_resposta_traz_o_contrato_completo(self, move_deps):
        ac, _, _ = move_deps
        res = await ac.post(
            "/workflows/wf-abc123/move", json={"target_workspace_id": DESTINO},
        )
        corpo = res.json()
        assert corpo["to_workspace_id"] == DESTINO
        assert corpo["from_workspace_id"] == ORIGEM
        assert corpo["warnings"] == []
        assert corpo["dry_run"] is False

    async def test_avisos_chegam_serializados(self, move_deps):
        ac, svc, _ = move_deps
        svc.move_workflow = AsyncMock(return_value=_resultado(warnings=[{
            "code": "credentials_unresolvable", "severity": "warning",
            "message": "A credencial 'Banco' deixará de ser resolvida.",
            "details": {"credential_id": "c-1", "node_ids": ["n1"]},
        }]))

        res = await ac.post(
            "/workflows/wf-abc123/move", json={"target_workspace_id": DESTINO},
        )
        aviso = res.json()["warnings"][0]
        assert aviso["code"] == "credentials_unresolvable"
        assert aviso["severity"] == "warning"
        assert aviso["details"]["node_ids"] == ["n1"]

    async def test_nome_opcional_e_repassado(self, move_deps):
        ac, svc, _ = move_deps
        await ac.post(
            "/workflows/wf-abc123/move",
            json={"target_workspace_id": DESTINO, "name": "Novo nome"},
        )
        assert svc.move_workflow.await_args.kwargs["new_name"] == "Novo nome"

    async def test_move_real_nao_e_dry_run(self, move_deps):
        ac, svc, _ = move_deps
        await ac.post("/workflows/wf-abc123/move", json={"target_workspace_id": DESTINO})
        assert svc.move_workflow.await_args.kwargs["dry_run"] is False


# ── Preview ──────────────────────────────────────────────────────────────────

class TestPreview:
    async def test_preview_devolve_200(self, move_deps):
        ac, svc, _ = move_deps
        svc.move_workflow = AsyncMock(return_value=_resultado(dry_run=True))

        res = await ac.post(
            "/workflows/wf-abc123/move/preview", json={"target_workspace_id": DESTINO},
        )
        assert res.status_code == 200

    async def test_preview_pede_dry_run_ao_service(self, move_deps):
        ac, svc, _ = move_deps
        svc.move_workflow = AsyncMock(return_value=_resultado(dry_run=True))

        await ac.post(
            "/workflows/wf-abc123/move/preview", json={"target_workspace_id": DESTINO},
        )
        assert svc.move_workflow.await_args.kwargs["dry_run"] is True

    async def test_preview_exige_a_mesma_permissao(self, move_deps):
        """Otherwise it would become an oracle about the contents of other people's workspaces."""
        ac, _, papel_destino = move_deps
        papel_destino.return_value = "editor"

        res = await ac.post(
            "/workflows/wf-abc123/move/preview", json={"target_workspace_id": DESTINO},
        )
        assert res.status_code == 403


# ── Autorizacao ──────────────────────────────────────────────────────────────

class TestAutorizacao:
    async def test_403_quando_nao_e_admin_no_destino(self, move_deps):
        ac, svc, papel_destino = move_deps
        papel_destino.return_value = "editor"

        res = await ac.post(
            "/workflows/wf-abc123/move", json={"target_workspace_id": DESTINO},
        )
        assert res.status_code == 403
        svc.move_workflow.assert_not_awaited()

    async def test_403_quando_nao_e_membro_do_destino(self, move_deps):
        ac, _, papel_destino = move_deps
        papel_destino.return_value = None

        res = await ac.post(
            "/workflows/wf-abc123/move", json={"target_workspace_id": DESTINO},
        )
        assert res.status_code == 403

    async def test_403_quando_e_apenas_editor_na_origem(self, move_deps):
        """The role at the source alone already blocks it — it does not even get to check the destination."""
        ac, svc, _ = move_deps
        from app.main import app
        from app.api.dependencies import get_accessible_workflow_with_role

        async def _wf_editor(id_hash: str):
            return _fake_workflow(id_hash=id_hash), "editor"

        app.dependency_overrides[get_accessible_workflow_with_role] = _wf_editor

        res = await ac.post(
            "/workflows/wf-abc123/move", json={"target_workspace_id": DESTINO},
        )
        assert res.status_code == 403
        svc.move_workflow.assert_not_awaited()


# ── Body validation ──────────────────────────────────────────────────────────

class TestValidacao:
    async def test_400_quando_o_destino_e_o_workspace_atual(self, move_deps):
        """The guard lives in the service (an invariant of the operation, not of the
        payload); here we only check that the domain error becomes 400 at the
        HTTP edge."""
        from app.core.exceptions import WorkflowMoveTargetError

        ac, svc, _ = move_deps
        svc.move_workflow = AsyncMock(
            side_effect=WorkflowMoveTargetError("O workflow já está neste workspace.")
        )
        res = await ac.post(
            "/workflows/wf-abc123/move", json={"target_workspace_id": ORIGEM},
        )
        assert res.status_code == 400

    async def test_422_sem_workspace_de_destino(self, move_deps):
        ac, _, _ = move_deps
        res = await ac.post("/workflows/wf-abc123/move", json={})
        assert res.status_code == 422

    async def test_422_com_campo_desconhecido(self, move_deps):
        """`extra="forbid"`: a silently ignored field would make the client think
        the change was applied."""
        ac, _, _ = move_deps
        res = await ac.post(
            "/workflows/wf-abc123/move",
            json={"target_workspace_id": DESTINO, "workspace_id": "outro"},
        )
        assert res.status_code == 422
