"""
Schedule IDOR: delete/update cross-tenant.

Regressao: schedules sao resolvidos por `job_id` global. A rota autoriza apenas
o workflow do path (a dependencia `workflow_com_papel`), mas o service nao confirmava que
o schedule pertence a ele. Um usuario apontava DELETE/PUT de um workflow proprio
para o `job_id` de outro tenant e deletava/reconfigurava o agendamento alheio.

Correcao: os metodos recebem `owner_workflow_hash` e exigem
`sch.workflow_hash == owner`, respondendo 404 (nao 403) para nao revelar
existencia.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import ScheduleNotFoundError
from app.services.schedule_service import ScheduleService


def _service_with(sch):
    svc = ScheduleService.__new__(ScheduleService)  # sem tocar o DB real
    svc.schedule_crud = MagicMock()
    svc.schedule_crud.get = AsyncMock(return_value=sch)
    svc.schedule_crud.delete = AsyncMock()
    svc.schedule_crud.update_by_id = AsyncMock(return_value=sch)
    return svc


def _schedule(job_id="job-1", workflow_hash="wf-do-dono"):
    return MagicMock(job_id=job_id, workflow_hash=workflow_hash)


# ── DELETE ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_de_outro_workflow_recusado():
    svc = _service_with(_schedule(workflow_hash="wf-DO-DONO"))

    with pytest.raises(ScheduleNotFoundError):
        await svc.delete_schedule("job-1", owner_workflow_hash="wf-do-atacante")

    svc.schedule_crud.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_do_proprio_workflow_permitido():
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))

    await svc.delete_schedule("job-1", owner_workflow_hash="wf-do-dono")

    svc.schedule_crud.delete.assert_awaited_once()


# ── UPDATE ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_de_outro_workflow_recusado():
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))
    payload = MagicMock()
    payload.dict = MagicMock(return_value={"active": False})

    with pytest.raises(ScheduleNotFoundError):
        await svc.update_schedule("job-1", payload, owner_workflow_hash="wf-do-atacante")

    svc.schedule_crud.update_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_do_proprio_workflow_permitido():
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))
    payload = MagicMock()
    payload.dict = MagicMock(return_value={"active": False})

    await svc.update_schedule("job-1", payload, owner_workflow_hash="wf-do-dono")

    svc.schedule_crud.update_by_id.assert_awaited_once()


# ── O dono e obrigatorio ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_omitir_o_dono_quebra_na_chamada():
    """Era opcional, e com `None` a confirmacao de posse era PULADA.

    A defesa contra o IDOR ficava desligada por omissao — bastava um chamador
    novo (uma tool do servidor MCP, um script) esquecer o parametro para
    apagar agendamento de outro tenant. Nenhum chamador real usava o atalho:
    as duas rotas sempre passaram o dono. Agora esquece-lo e erro de chamada.

    O `match` importa: sem ele qualquer TypeError satisfaria o teste.
    """
    svc = _service_with(_schedule())

    with pytest.raises(TypeError, match="owner_workflow_hash"):
        await svc.delete_schedule("job-1")


@pytest.mark.asyncio
@pytest.mark.parametrize("metodo", ["delete", "update"])
async def test_dono_None_explicito_falha_fechado(metodo):
    """O caso que a assinatura obrigatoria NAO cobre — e que e o perigoso.

    Tornar o parametro obrigatorio pega quem o OMITE. Nao pega quem passa uma
    variavel que por acaso e `None`, e e assim que o defeito apareceria num
    chamador real. Com o atalho antigo (`owner_workflow_hash is not None and
    ...`) isso PULAVA a confirmacao de posse e apagava agendamento alheio; hoje
    `None` nao casa com `workflow_hash` nenhum e a recusa e 404.

    Sem este teste, restaurar o atalho antigo mantendo o parametro obrigatorio
    passa o arquivo inteiro — conferido por mutacao.
    """
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))

    with pytest.raises(ScheduleNotFoundError):
        if metodo == "delete":
            await svc.delete_schedule("job-1", owner_workflow_hash=None)
        else:
            payload = MagicMock()
            payload.dict = MagicMock(return_value={"active": False})
            await svc.update_schedule("job-1", payload, owner_workflow_hash=None)

    svc.schedule_crud.delete.assert_not_awaited()
    svc.schedule_crud.update_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_inexistente_404():
    svc = _service_with(None)

    with pytest.raises(ScheduleNotFoundError):
        await svc.delete_schedule("nao-existe", owner_workflow_hash="wf-x")
