# tests/unit/test_retry_run_valida_o_run.py
"""
`POST /workflows/{id_hash}/runs/{run_id}/retry` and the run it ignored.

The route declared `{run_id}` in the path, received the parameter and never read
it. Any string passed — including the task_id of a run of ANOTHER workflow — and
the route triggered the execution all the same. Whoever called it thinking they
were re-running a specific run was triggering something else, with no sign of it.

What was NOT done, on purpose: implementing a real replay. `WorkflowRun` does not
store the input parameters, so re-running exactly that run would require a new
column — a feature, not a fix. The route now VALIDATES the run and says in its
docstring what it actually does.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.routers import workflows_router as mod


class _Wf:
    id_hash = "wf-1"


def _requisicao() -> Request:
    """Minimal Request: the route has a rate limit, and slowapi rejects anything
    that is not a real Request (same pattern as
    tests/integration/test_grupos_ordem.py)."""
    return Request({
        "type": "http", "method": "POST", "path": "/workflows/wf-1/runs/run-1/retry",
        "headers": [], "client": ("127.0.0.1", 0), "query_string": b"",
    })


def _db(encontrou: bool):
    db = MagicMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = "run-1" if encontrou else None
    db.execute = AsyncMock(return_value=res)
    return db


def _service():
    svc = MagicMock()
    svc.start_analysis = AsyncMock(return_value=MagicMock(id="task-novo"))
    return svc


@pytest.mark.asyncio
async def test_run_inexistente_recebe_404_em_vez_de_disparar():
    """The central regression: an unknown id must not trigger an execution."""
    svc = _service()
    with pytest.raises(HTTPException) as exc:
        await mod.retry_run(
            request=_requisicao(), run_id="nao-existe", db=_db(False),
            service=svc, wf=_Wf(),
        )
    assert exc.value.status_code == 404
    svc.start_analysis.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_de_outro_workflow_nao_dispara():
    """A consulta filtra por workflow_hash — o `db` fake devolve None p/ o par."""
    svc = _service()
    db = _db(False)
    with pytest.raises(HTTPException) as exc:
        await mod.retry_run(
            request=_requisicao(), run_id="run-de-outro", db=db,
            service=svc, wf=_Wf(),
        )
    assert exc.value.status_code == 404
    # The query must filter by BOTH fields; by task_id alone it would find the other
    # workflow's run and trigger the execution of this workflow.
    sql = str(db.execute.await_args.args[0]).lower()
    assert "task_id" in sql and "workflow_hash" in sql


@pytest.mark.asyncio
async def test_run_valido_dispara_a_execucao():
    svc = _service()
    resp = await mod.retry_run(
        request=_requisicao(), run_id="run-1", db=_db(True),
        service=svc, wf=_Wf(),
        current_user=MagicMock(id_hash="user-x"),
    )
    assert resp["task_id"] == "task-novo"
    svc.start_analysis.assert_awaited_once()
    # Scope D: the retry also passes along who triggered it.
    assert svc.start_analysis.await_args.kwargs["triggered_by"] == "user-x"


@pytest.mark.asyncio
async def test_papel_insuficiente_e_barrado_antes_da_consulta(client):
    """403 still comes before any I/O.

    Through the app, not by calling the function: the role now belongs to the
    route's dependency (`workflow_com_papel`), which runs before the body — it
    is the one that has to block.
    """
    from app.api.dependencies import get_accessible_workflow_with_role, get_db
    from app.main import app

    db = _db(True)

    async def _viewer(id_hash: str):
        return _Wf(), "viewer"

    async def _sessao():
        yield db

    app.dependency_overrides[get_accessible_workflow_with_role] = _viewer
    app.dependency_overrides[get_db] = _sessao

    resposta = await client.post("/workflows/wf-1/runs/run-1/retry")

    assert resposta.status_code == 403
    db.execute.assert_not_awaited()
