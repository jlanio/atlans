# tests/unit/test_idempotencia_por_usuario.py
"""
Idempotency of `POST /workflows/{id}/execute` per USER and per WORKFLOW.

The Redis key was global to the installation: two users sending
`Idempotency-Key: 1` got each other's `task_id` — and the second one did not even
trigger. With the MCP server, different agents will generate short, predictable
keys ("1", "retry-2"), so the collision stopped being theoretical. Now the
key carries who triggered and which workflow.

A fake Redis backed by a dictionary (not `AsyncMock`): a mock that always returns None
cannot distinguish "did not collide" from "did not write".
"""
from __future__ import annotations

from itertools import count
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.workflow_crud import WorkflowCRUD
from app.models.workflow import Workflow
from app.services.workflow_service import DispatchResult, WorkflowService


class _RedisFalso:
    def __init__(self):
        self.dados: dict[str, str] = {}
        self.gravacoes: list[tuple[str, str, int | None]] = []

    async def get(self, chave):
        return self.dados.get(chave)

    async def set(self, chave, valor, ex=None, **_):
        self.dados[chave] = valor
        self.gravacoes.append((chave, valor, ex))
        return True

    async def lpush(self, *_a, **_k):
        return 1


@pytest.fixture
def redis():
    r = _RedisFalso()
    with patch("app.core.redis._pool", r):
        yield r


@pytest.fixture(autouse=True)
def _sem_banco():
    with patch("app.services.disabled_nodes_service.disabled_names", new=AsyncMock(return_value=set())), \
         patch("flow.utils.workflow_contract.collect_subworkflow_definitions_recursive", new=AsyncMock(return_value={})):
        yield


@pytest.fixture
def service():
    """`start_analysis` with everything before and after the dispatch mocked; each
    dispatch returns a new id, so two triggers can be told apart."""
    db = AsyncMock()
    db.add = MagicMock()
    svc = WorkflowService(db)
    svc.crud = AsyncMock(spec=WorkflowCRUD)
    svc.crud.db = db

    def _wf(id_hash: str) -> Workflow:
        wf = Workflow(name=id_hash, definition={"nodes": [], "edges": []}, flag_ative=True)
        wf.id_hash, wf.workspace_id = id_hash, "ws-1"
        wf.pinned_outputs = wf.pin_metadata = None
        return wf

    svc._load_workflow = AsyncMock(side_effect=lambda id_hash, *_a, **_k: (_wf(id_hash), {"nodes": [], "edges": []}))
    svc._resolve_candidates = AsyncMock(return_value=[MagicMock(id_hash="ag-1", public_key="PEM")])
    ids = count(1)
    svc._dispatch_job = AsyncMock(side_effect=lambda *a, **k: DispatchResult(id=f"task-{next(ids)}"))
    return svc


async def _disparar(service, wf: str, usuario: str | None, chave: str) -> str:
    r = await service.start_analysis(wf, idempotency_key=chave, triggered_by=usuario, trigger_source="manual")
    return r.id


@pytest.mark.asyncio
async def test_formato_da_chave_usuario_workflow_e_chave(service, redis):
    await _disparar(service, "wf-1", "usr-a", "k1")
    assert [g[0] for g in redis.gravacoes] == ["idempotency:wf_execute:usr-a:wf-1:k1"]
    (_, valor, ttl), = redis.gravacoes
    assert valor == "task-1"
    assert ttl == 24 * 60 * 60


@pytest.mark.asyncio
async def test_mesma_chave_dois_usuarios_sao_duas_execucoes(service, redis):
    a = await _disparar(service, "wf-1", "usr-a", "1")
    b = await _disparar(service, "wf-1", "usr-b", "1")
    assert a != b
    assert service._dispatch_job.await_count == 2


@pytest.mark.asyncio
async def test_mesmo_usuario_mesma_chave_devolve_a_mesma_execucao_sem_despachar(service, redis):
    a = await _disparar(service, "wf-1", "usr-a", "1")
    b = await _disparar(service, "wf-1", "usr-a", "1")
    assert a == b == "task-1"
    assert service._dispatch_job.await_count == 1
    assert len(redis.gravacoes) == 1


@pytest.mark.asyncio
async def test_mesmo_usuario_mesma_chave_workflows_diferentes_sao_duas_execucoes(service, redis):
    a = await _disparar(service, "wf-1", "usr-a", "1")
    b = await _disparar(service, "wf-2", "usr-a", "1")
    assert a != b
    assert service._dispatch_job.await_count == 2


@pytest.mark.asyncio
async def test_sem_usuario_a_chave_leva_um_traco(service, redis):
    """Cron and webhook do not pass a key today; if they do, they must not fall into
    any user's slice."""
    await _disparar(service, "wf-1", None, "k1")
    assert redis.gravacoes[0][0] == "idempotency:wf_execute:-:wf-1:k1"


@pytest.mark.asyncio
async def test_sem_chave_nada_e_gravado(service, redis):
    await service.start_analysis("wf-1", triggered_by="usr-a")
    assert redis.gravacoes == []
