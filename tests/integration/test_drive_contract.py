# tests/integration/test_drive_contract.py
"""
Testes de contrato HTTP para o drive_router.
Verificam status codes esperados — base para refatorações seguras.

Nota: helpers de baixo nível (_sanitize_name, _make_s3_key, _validate_upload)
estão cobertos em tests/unit/test_drive_filename_safety.py (e a variante do
executor em test_auditoria_seguranca_regressao.py). Aqui focamos nos endpoints
HTTP. (O antigo test_drive_router.py foi absorvido por esses na F5.)
"""
import pytest
from unittest.mock import AsyncMock


def _fake_file_out(id_hash="file-001"):
    """Retorna um dict compatível com WorkspaceFileOut."""
    return {
        "id_hash": id_hash,
        "workspace_id": "ws-test-001",
        "original_name": "dados.geojson",
        "extension": "geojson",
        "mime_type": "application/geo+json",
        "size": 2048,
        "s3_key": f"drive/ws-test-001/uuid_{id_hash}.geojson",
        "status": "confirmed",
        "uploaded_by": "usr-test-001",
        "content_md5": None,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": None,
    }


@pytest.fixture
def override_drive_deps(client):
    """Injeta DriveService mockado nas rotas do drive."""
    from app.main import app
    from app.api.routers.drive_router import get_drive_service

    svc = AsyncMock()
    svc.list_files = AsyncMock(return_value=([], 0))
    svc.upload_file = AsyncMock()
    svc.delete_file = AsyncMock()

    async def _svc():
        return svc

    app.dependency_overrides[get_drive_service] = _svc

    yield client, svc

    app.dependency_overrides.pop(get_drive_service, None)


class TestListFiles:
    async def test_returns_200_with_workspace_id(self, override_drive_deps):
        """GET /drive/?workspace_id=... deve retornar 200."""
        ac, _ = override_drive_deps
        res = await ac.get("/drive?workspace_id=ws-test-001")
        assert res.status_code == 200

    async def test_requires_workspace_id(self, override_drive_deps):
        """GET /drive/ sem workspace_id deve retornar 422 (parâmetro obrigatório)."""
        ac, _ = override_drive_deps
        res = await ac.get("/drive")
        assert res.status_code == 422

    async def test_returns_403_for_inaccessible_workspace(self, override_drive_deps):
        """GET /drive/?workspace_id=outro-ws deve retornar 403."""
        ac, _ = override_drive_deps
        res = await ac.get("/drive?workspace_id=ws-outro-001")
        assert res.status_code == 403

    async def test_response_has_items_and_total(self, override_drive_deps):
        ac, _ = override_drive_deps
        res = await ac.get("/drive?workspace_id=ws-test-001")
        data = res.json()
        assert "items" in data
        assert "total" in data
