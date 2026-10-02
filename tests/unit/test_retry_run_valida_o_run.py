# tests/unit/test_retry_run_valida_o_run.py
"""
`POST /workflows/{id_hash}/runs/{run_id}/retry` e o run que ele ignorava.

A rota declarava `{run_id}` no path, recebia o parametro e nunca o lia. Qualquer
string passava — inclusive o task_id de uma run de OUTRO workflow — e a rota
disparava a execucao do mesmo jeito. Quem chamasse achando estar reexecutando
uma run especifica estava disparando outra coisa, sem nenhum sinal disso.

O que NAO foi feito, de proposito: implementar o replay de verdade.
`WorkflowRun` nao guarda os parametros de entrada, entao reexecutar exatamente
aquela run exigiria coluna nova — feature, nao correcao. A rota passou a
VALIDAR o run e a dizer na docstring o que de fato faz.
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
    """Request minima: a rota tem rate limit, e o slowapi recusa qualquer coisa
    que nao seja uma Request de verdade (mesmo padrao de
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
    """A regressao central: id desconhecido nao pode disparar execucao."""
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
    # A query precisa restringir pelos DOIS campos; so por task_id acharia a run
    # alheia e disparia a execucao deste workflow.
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
    # Escopo D: o retry também repassa quem disparou.
    assert svc.start_analysis.await_args.kwargs["triggered_by"] == "user-x"


@pytest.mark.asyncio
async def test_papel_insuficiente_e_barrado_antes_da_consulta(client):
    """403 continua vindo antes de qualquer I/O.

    Pela app, e não chamando a função: o papel agora é da dependência da rota
    (`workflow_com_papel`), que roda antes do corpo — é ela que tem de barrar.
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
