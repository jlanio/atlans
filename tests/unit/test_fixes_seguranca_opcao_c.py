"""Regressão dos fixes de segurança aplicados na opção C da auditoria.

Cada teste falha SEM o fix correspondente:
 - item 10: WS de telemetria só para admin (require_role=ROLE_ADMIN);
 - item 13: cancel_run autoriza pelo workspace DO RUN, não do workflow;
 - item 18: handler 422 não ecoa o valor submetido pelo cliente (input/ctx).

(O item 11 — idempotência cobrir 'cancelled' — tem sua regressão em
 test_fix_ws_router.py::test_job_result_de_run_cancelado_e_ignorado.)
"""
import json

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.models import Workflow, WorkflowGroup, WorkflowRun
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


# ── Item 18: 422 não vaza o input do cliente ────────────────────────────────

async def test_422_nao_ecoa_input_nem_ctx_do_cliente():
    from app.core.utils.error_handlers import validation_exception_handler

    exc = RequestValidationError([
        {
            "type": "string_too_short",
            "loc": ("body", "password"),
            "msg": "String should have at least 8 characters",
            "input": "senha-secreta-do-usuario",
            "ctx": {"min_length": 8},
        },
    ])

    resp = await validation_exception_handler(None, exc)
    body = json.loads(resp.body)
    detalhes = body["details"]

    # O valor submetido NÃO pode voltar na resposta — nem em 'input', nem solto.
    assert all("input" not in e for e in detalhes)
    assert all("ctx" not in e for e in detalhes)
    assert "senha-secreta-do-usuario" not in resp.body.decode()

    # Mas o que o cliente precisa para corrigir continua lá.
    assert detalhes[0]["loc"] == ["body", "password"]
    assert detalhes[0]["msg"]
    assert detalhes[0]["type"] == "string_too_short"


# ── Item 10: telemetria exige admin ─────────────────────────────────────────

async def test_telemetria_ws_exige_admin(monkeypatch):
    from app.api.routers import telemetry_router as TR

    capturado = {}

    async def _auth(ws, *, scope=None, require_role=None):
        capturado["require_role"] = require_role
        return None  # fecha a conexão e faz o handler retornar cedo

    monkeypatch.setattr(TR, "ws_authenticate", _auth)

    class _WS:
        async def close(self, *a, **k):
            pass

    await TR.websocket_telemetry(_WS())
    assert capturado["require_role"] == TR.ROLE_ADMIN


# ── Item 13: cancel_run autoriza pelo workspace do RUN ──────────────────────

@pytest_asyncio.fixture
async def banco_do_cancelamento():
    """Um workflow MOVIDO: o run aconteceu em ws-A, o workflow hoje é de ws-B.

    É a situação que separa os dois critérios de autorização — e, com banco de
    verdade em vez de dublê, o teste exercita a query real de papel.
    """
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(
            Workspace.metadata.create_all,
            tables=[
                Workspace.__table__,
                WorkspaceMember.__table__,
                WorkflowGroup.__table__,
                Workflow.__table__,
                WorkflowRun.__table__,
            ],
        )
    async with AsyncSession(eng) as db:
        db.add(Workspace(id_hash="ws-A", name="antigo", owner_id="dono"))
        db.add(Workspace(id_hash="ws-B", name="atual", owner_id="dono"))
        db.add(Workflow(id_hash="wf-1", name="fluxo", workspace_id="ws-B", definition={}))
        db.add(WorkflowRun(
            task_id="run-1", workflow_hash="wf-1", workspace_id="ws-A", status="running",
        ))
        # Operator no workspace ATUAL do workflow, nada no workspace do run.
        db.add(WorkspaceMember(workspace_id="ws-B", user_id="u-1", role="operator"))
        await db.commit()
        yield db
    await eng.dispose()


async def test_cancel_run_recusa_quem_so_tem_papel_no_workspace_atual(banco_do_cancelamento):
    """Operator no workspace de HOJE não cancela execução que rodou em OUTRO.

    Um workflow pode ser movido de A para B depois do disparo. Quem controla B
    não deve poder cancelar uma execução que rodou — e consumiu recursos — em A.
    """
    from app.services.workflow_execution_service import cancel_run

    with pytest.raises(HTTPException) as exc:
        await cancel_run(banco_do_cancelamento, "run-1", user_id="u-1")

    assert exc.value.status_code == 403


async def test_cancel_run_recusa_papel_insuficiente_no_workspace_do_run(banco_do_cancelamento):
    """Ser membro do workspace do run não basta: o mínimo é `operator`.

    Sem este caso, o 403 acima poderia vir de "não é membro" e a exigência de
    PAPEL — que é o outro metade da regra — passaria sem cobertura.
    """
    from app.services.workflow_execution_service import cancel_run

    banco_do_cancelamento.add(
        WorkspaceMember(workspace_id="ws-A", user_id="u-3", role="viewer")
    )
    await banco_do_cancelamento.commit()

    with pytest.raises(HTTPException) as exc:
        await cancel_run(banco_do_cancelamento, "run-1", user_id="u-3")

    assert exc.value.status_code == 403


async def test_cancel_run_aceita_quem_tem_papel_no_workspace_do_run(banco_do_cancelamento, monkeypatch):
    """O outro lado: com o papel no workspace certo, o cancelamento anda.

    Sem este par, o teste acima passaria com uma recusa que recusa todo mundo.

    O run ganha `host` e o registro do executor é dublado de propósito: sem
    isso o desfecho seria `already_finished` — o ramo "não tem executor
    associado" —, e a asserção provaria apenas que ninguém levantou 403.
    Assim ela prova que o cancelamento REALMENTE saiu depois da autorização.
    """
    from app.services import workflow_execution_service as WES

    banco_do_cancelamento.add(
        WorkspaceMember(workspace_id="ws-A", user_id="u-2", role="operator")
    )
    run = (await banco_do_cancelamento.execute(
        select(WorkflowRun).where(WorkflowRun.task_id == "run-1")
    )).scalar_one()
    run.host = "executor:ag-1"
    await banco_do_cancelamento.commit()

    enviados = []

    async def _send(executor_id, payload):
        enviados.append((executor_id, payload))
        return True

    monkeypatch.setattr(WES.executor_registry, "send_json", _send)

    outcome = await WES.cancel_run(banco_do_cancelamento, "run-1", user_id="u-2")

    assert outcome == "requested"
    assert enviados == [("ag-1", {"type": "cancel", "job_id": "run-1"})]


async def test_cancel_run_exige_user_id(banco_do_cancelamento):
    """A assinatura é a guarda: esquecer o parâmetro quebra na chamada.

    Era o defeito — `cancel_run(db, run_id)` não tinha autorização nenhuma, e
    qualquer chamador fora da rota atravessava tenant em silêncio.

    O `match` importa: sem ele, qualquer TypeError de qualquer origem (um dublê
    mal montado, por exemplo) satisfaria o teste.
    """
    from app.services.workflow_execution_service import cancel_run

    with pytest.raises(TypeError, match="user_id"):
        await cancel_run(banco_do_cancelamento, "run-1")


# ── Item 13b: a rota passa a identidade certa para o serviço ────────────────

async def test_rota_de_cancelamento_passa_o_usuario_e_o_atalho_de_admin(monkeypatch):
    """A regra mora no serviço; a FIAÇÃO mora na rota, e é ela que regride.

    Mover a autorização para o serviço deixou a rota sem nenhum teste: trocar
    `como_admin=...` por `como_admin=True` — isto é, dispensar a autorização de
    todo mundo — passava a suíte inteira. Este teste é o que torna essa troca
    visível.
    """
    from app.api.routers import workflows_router as WR

    recebido = {}

    async def _cancel(db, run_id, *, user_id, como_admin=False):
        recebido.update(run_id=run_id, user_id=user_id, como_admin=como_admin)
        return "requested"

    monkeypatch.setattr(
        "app.services.workflow_execution_service.cancel_run", _cancel,
    )
    # A rota é decorada por @limiter.limit, que exige um Request real antes do
    # corpo rodar. Desligar o limiter (revertido pelo monkeypatch) deixa chamar
    # a coroutine direto com request=None, que o corpo não usa.
    monkeypatch.setattr(WR.limiter, "enabled", False)

    class _Usuario:
        def __init__(self, role):
            self.role = role
            self.id_hash = "u-1"

    out = await WR.cancel_run(
        request=None, run_id="run-1", db=None, current_user=_Usuario(None),
    )
    assert out == {"run_id": "run-1", "outcome": "requested"}
    assert recebido["user_id"] == "u-1"
    assert recebido["como_admin"] is False       # não-admin NÃO pula a checagem

    await WR.cancel_run(
        request=None, run_id="run-1", db=None, current_user=_Usuario(WR.ROLE_ADMIN),
    )
    assert recebido["como_admin"] is True        # admin global, sim
