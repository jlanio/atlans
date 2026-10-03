# tests/integration/test_drive_contract.py
"""
HTTP contract tests for drive_router.
They check the expected status codes — a basis for safe refactorings.

Note: the low-level helpers (_sanitize_name, _make_s3_key, _validate_upload)
are covered in tests/unit/test_drive_filename_safety.py (and the executor
variant in test_auditoria_seguranca_regressao.py). Here we focus on the HTTP
endpoints. (The old test_drive_router.py was absorbed by those in F5.)
"""
import pytest
from unittest.mock import AsyncMock


def _fake_file_out(id_hash="file-001"):
    """Returns a dict compatible with WorkspaceFileOut."""
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
    """Injects a mocked DriveService into the drive routes."""
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
        """GET /drive/ without workspace_id must return 422 (required parameter)."""
        ac, _ = override_drive_deps
        res = await ac.get("/drive")
        assert res.status_code == 422

    async def test_returns_403_for_inaccessible_workspace(self, override_drive_deps):
        """GET /drive/?workspace_id=outro-ws must return 403."""
        ac, _ = override_drive_deps
        res = await ac.get("/drive?workspace_id=ws-outro-001")
        assert res.status_code == 403

    async def test_response_has_items_and_total(self, override_drive_deps):
        ac, _ = override_drive_deps
        res = await ac.get("/drive?workspace_id=ws-test-001")
        data = res.json()
        assert "items" in data
        assert "total" in data
