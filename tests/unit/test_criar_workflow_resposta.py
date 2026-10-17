"""What POST /workflows answers: `{"id", "name", "schedule_notices"}`, not the workflow.

The editor opens the new workflow from this answer
(`web/app/hooks/workflow/useSaveWorkflow.ts`): it reads `id`, and with it moves from
/workflow/create to /workflow/<id>, where Executar shows up. It used to read `id_hash`,
which this answer does not have, and the editor stayed on the create screen; the next
save tried to create the workflow again. Changing the shape here breaks the editor
again, so it is pinned.

`schedule_notices` is what the first save did NOT do to the schedule (an invalid
expression, an inactive workflow), as in the PUT's answer: the editor turns each
one into a toast. Before, the create answer had none, and a new workflow could be
born without the schedule it showed on the canvas with only "Salvo" on screen.

The route is called directly, with no HTTP client: role and limiter are out of the way.
"""
import pytest

from app.api.routers import workflows_router as WR
from app.schemas.schedule import ScheduleNotice
from app.schemas.workflow import WorkflowCreate


class _FakeUser:
    id_hash = "u-1"


class _Criado:
    id_hash = "wf-novo"
    name = "Novo fluxo"


class _CriadoComAviso(_Criado):
    schedule_notices = [
        ScheduleNotice(code="invalid_schedule", message="Configuração de agendamento inválida."),
    ]


class _FakeService:
    def __init__(self, criado=None):
        self.chamadas = []
        self.criado = criado or _Criado()

    async def create_workflow(self, name, definition, **kwargs):
        self.chamadas.append((name, definition, kwargs))
        return self.criado


@pytest.fixture
def open_route(monkeypatch):
    from app.core.authorization import workflow_access

    async def _role(db, ws_id, uid):
        return "editor"

    monkeypatch.setattr(WR.limiter, "enabled", False)
    monkeypatch.setattr(workflow_access, "get_workspace_member_role", _role)


async def test_create_answers_id_and_name(open_route):
    service = _FakeService()
    payload = WorkflowCreate(name="Novo fluxo", workspace_id="ws-1", definition={"nodes": [], "edges": []})

    resposta = await WR.create_workflow(
        request=None, payload=payload, service=service, current_user=_FakeUser(), db=None,
    )

    # What the editor reads. Other fields may join the answer; these two may not leave.
    assert resposta["id"] == "wf-novo"
    assert resposta["name"] == "Novo fluxo"
    assert len(service.chamadas) == 1
    assert resposta["schedule_notices"] == []


async def test_create_answers_what_the_schedule_did_not_apply(open_route):
    service = _FakeService(_CriadoComAviso())
    payload = WorkflowCreate(name="Novo fluxo", workspace_id="ws-1", definition={"nodes": [], "edges": []})

    resposta = await WR.create_workflow(
        request=None, payload=payload, service=service, current_user=_FakeUser(), db=None,
    )

    assert resposta["schedule_notices"] == [{
        "code": "invalid_schedule",
        "severity": "warning",
        "message": "Configuração de agendamento inválida.",
        "details": {},
    }]
