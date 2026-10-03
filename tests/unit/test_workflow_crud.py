# tests/unit/test_workflow_crud.py
"""Unit tests for WorkflowCRUD."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


@pytest.fixture
def mock_db():
    """Mock of AsyncSession."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def crud(mock_db):
    from app.crud.workflow_crud import WorkflowCRUD
    return WorkflowCRUD(mock_db)


class TestWorkflowCRUD:

    @pytest.mark.asyncio
    async def test_create_workflow(self, crud, mock_db):
        """Should create a workflow with name and definition."""
        mock_db.refresh = AsyncMock(side_effect=lambda wf: setattr(wf, 'id_hash', str(uuid4())))

        wf = await crud.create("test-workflow", {"nodes": [], "edges": []})

        assert wf.name == "test-workflow"
        assert wf.definition == {"nodes": [], "edges": []}
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_workflow_with_workspace(self, crud, mock_db):
        """Deve criar workflow vinculado a um workspace."""
        mock_db.refresh = AsyncMock()
        ws_id = str(uuid4())

        wf = await crud.create("test-wf", {"nodes": []}, workspace_id=ws_id)

        assert wf.workspace_id == ws_id

    @pytest.mark.asyncio
    async def test_get_by_hash_found(self, crud, mock_db):
        """Should return the workflow when found."""
        from app.models.workflow import Workflow
        fake_wf = Workflow(name="found", definition={})
        fake_wf.id_hash = "abc123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_wf
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_by_hash("abc123")
        assert result is not None
        assert result.name == "found"

    @pytest.mark.asyncio
    async def test_get_by_hash_not_found(self, crud, mock_db):
        """Should return None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_by_hash("inexistente")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_workflow(self, crud, mock_db):
        """Should update the workflow's fields."""
        from app.models.workflow import Workflow
        wf = Workflow(name="old-name", definition={})
        wf.id_hash = "abc123"

        updated = await crud.update(wf, {"name": "new-name", "priority": 5})

        assert updated.name == "new-name"
        assert updated.priority == 5
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_by_hash(self, crud, mock_db):
        """Should soft-delete the workflow (flag_ative=False) by id_hash."""
        from app.models.workflow import Workflow
        fake_wf = Workflow(name="to-delete", definition={})
        fake_wf.id_hash = "del123"
        fake_wf.flag_ative = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = fake_wf
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.soft_delete_by_hash("del123")
        assert result is not None
        assert fake_wf.flag_ative is False
        mock_db.commit.assert_called_once()
