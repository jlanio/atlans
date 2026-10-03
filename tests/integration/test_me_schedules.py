# tests/integration/test_me_schedules.py
"""`GET /me/schedules` — the person's schedules, across all their
workspaces, one per row. The logic lives in `list_schedules_for`, tested
here against real tables in an in-memory SQLite (the endpoint is just a
`Depends(get_user_workspace_ids)` wrapper + the call).

Model: `test_listagem_projetos.py` — same family of cross-cutting listing.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.models import Schedule, Workflow
from app.schemas.me import MySchedule
from app.services.schedule_service import list_schedules_for

WS_1 = "ws-1"
WS_2 = "ws-2"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[Workflow.__table__, Schedule.__table__],
        )
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


async def _workflow(db, hash_, *, workspace=WS_1, flag_ative=True, deleted_at=None, origem="usuario"):
    db.add(Workflow(
        id_hash=hash_, name=hash_, definition={"nodes": [], "edges": []},
        flag_ative=flag_ative, workspace_id=workspace, deleted_at=deleted_at,
        origem=origem,
    ))
    await db.commit()


async def _schedule(db, workflow_hash, *, active=True, next_run_at=None):
    job = f"job-{uuid4()}"
    db.add(Schedule(
        workflow_hash=workflow_hash, strategy="cron", cron_expression="0 6 * * *",
        timezone="America/Cuiaba", active=active, next_run_at=next_run_at,
        job_id=job, workspace_id=workflow_hash,  # the schedule's workspace_id is ignored on purpose
    ))
    await db.commit()
    return job


async def _list_schedules(db, workspace_ids):
    itens = await list_schedules_for(db, workspace_ids)
    # Validates the output contract along the way.
    for i in itens:
        MySchedule.model_validate(i)
    return itens


@pytest.mark.asyncio
async def test_only_my_workspaces(db):
    await _workflow(db, "meu", workspace=WS_1)
    await _workflow(db, "alheio", workspace=WS_2)
    await _schedule(db, "meu")
    await _schedule(db, "alheio")

    itens = await _list_schedules(db, [WS_1])
    assert [i["workflow_id"] for i in itens] == ["meu"]


@pytest.mark.asyncio
async def test_soft_deleted_is_left_out(db):
    await _workflow(db, "vivo", workspace=WS_1)
    await _workflow(db, "lixeira", workspace=WS_1, deleted_at=datetime(2026, 1, 1))
    await _schedule(db, "vivo")
    await _schedule(db, "lixeira")

    itens = await _list_schedules(db, [WS_1])
    assert [i["workflow_id"] for i in itens] == ["vivo"]


@pytest.mark.asyncio
async def test_order_active_first_then_next_nulls_last(db):
    await _workflow(db, "wf", workspace=WS_1)
    cedo = datetime(2030, 1, 1, 6, 0)
    tarde = datetime(2030, 1, 1, 18, 0)
    await _schedule(db, "wf", active=False, next_run_at=cedo)     # paused → last
    await _schedule(db, "wf", active=True, next_run_at=None)      # active with no next run → after the active ones with a date
    await _schedule(db, "wf", active=True, next_run_at=tarde)
    await _schedule(db, "wf", active=True, next_run_at=cedo)

    itens = await _list_schedules(db, [WS_1])
    ativos = [i for i in itens if i["active"]]
    # Active ones first; among them, by ascending next run, null last.
    assert [i["next_run_at"] for i in ativos[:2]] == [
        cedo.replace(tzinfo=timezone.utc), tarde.replace(tzinfo=timezone.utc),
    ]
    assert ativos[-1]["next_run_at"] is None
    # The paused one comes after all the active ones.
    assert itens[-1]["active"] is False


@pytest.mark.asyncio
async def test_dates_come_out_tz_aware(db):
    """Naive in the database (UTC) → with offset in the response, otherwise the web reads it as local."""
    await _workflow(db, "wf", workspace=WS_1)
    await _schedule(db, "wf", next_run_at=datetime(2030, 5, 1, 9, 0))

    item = (await _list_schedules(db, [WS_1]))[0]
    assert item["next_run_at"].tzinfo is not None
    assert item["next_run_at"] == datetime(2030, 5, 1, 9, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_brings_workflow_name_and_flag_ative(db):
    await _workflow(db, "wf-desligado", workspace=WS_1, flag_ative=False)
    await _schedule(db, "wf-desligado", active=True)

    item = (await _list_schedules(db, [WS_1]))[0]
    assert item["workflow_name"] == "wf-desligado"
    # "Paused" has two causes: the schedule is active, but the workflow is not.
    assert item["active"] is True
    assert item["flag_ative"] is False


@pytest.mark.asyncio
async def test_brings_workflow_origin(db):
    """The origin comes from the JOIN with Workflow, for the "assistente" badge on
    Home. Defaults to "usuario" when the workflow did not come from the assistant."""
    await _workflow(db, "do-usuario", workspace=WS_1, origem="usuario")
    await _workflow(db, "do-assistente", workspace=WS_1, origem="assistente")
    await _schedule(db, "do-usuario")
    await _schedule(db, "do-assistente")

    itens = await _list_schedules(db, [WS_1])
    origin_by_workflow = {i["workflow_id"]: i["origem"] for i in itens}
    assert origin_by_workflow == {"do-usuario": "usuario", "do-assistente": "assistente"}


@pytest.mark.asyncio
async def test_without_workspaces_empty_list(db):
    await _workflow(db, "wf", workspace=WS_1)
    await _schedule(db, "wf")
    assert await _list_schedules(db, []) == []


@pytest.mark.asyncio
async def test_page_with_limit_and_offset(db):
    """It was the only new listing without a ceiling — Chats cuts at 50, Collection at 200."""
    for i in range(5):
        await _workflow(db, f"wf-{i}")
        await _schedule(db, f"wf-{i}", next_run_at=datetime(2026, 1, 1 + i, tzinfo=timezone.utc))

    primeira = await list_schedules_for(db, [WS_1], limit=2, offset=0)
    segunda = await list_schedules_for(db, [WS_1], limit=2, offset=2)
    inteira = await list_schedules_for(db, [WS_1], limit=100, offset=0)

    assert len(primeira) == 2 and len(segunda) == 2 and len(inteira) == 5
    # Disjoint pages, in the same order as the full list.
    assert [i["job_id"] for i in primeira + segunda] == [i["job_id"] for i in inteira[:4]]


@pytest.mark.asyncio
async def test_order_breaks_ties_stably(db):
    """Same `active` and same `next_run_at`: without the third criterion, two
    rows could swap pages between requests."""
    quando = datetime(2026, 3, 1, tzinfo=timezone.utc)
    for i in range(4):
        await _workflow(db, f"igual-{i}")
        await _schedule(db, f"igual-{i}", next_run_at=quando)

    uma = [i["job_id"] for i in await list_schedules_for(db, [WS_1])]
    outra = [i["job_id"] for i in await list_schedules_for(db, [WS_1])]
    assert uma == outra


@pytest.mark.asyncio
async def test_route_responds_and_passes_limit_offset(client, db, monkeypatch):
    """Closes the loop: the limiter decorator, the query params and the ENVELOPE.

    The response is `{itens, total}` — the same format as `GET /assistente/conversas`.
    Without `total`, the ceiling of 200 truncated silently: the web received the
    page and had no way of knowing there were more rows to request.
    """
    from app.api.dependencies import get_db
    from app.core.rate_limiter import limiter
    from app.main import app

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    monkeypatch.setattr(limiter, "enabled", False)  # the 60/min counts per IP across tests
    try:
        for i in range(3):
            await _workflow(db, f"rota-{i}", workspace="ws-test-001")
            await _schedule(db, f"rota-{i}", next_run_at=datetime(2026, 5, 1 + i, tzinfo=timezone.utc))

        inteira = await client.get("/me/schedules")
        pagina = await client.get("/me/schedules", params={"limit": 1, "offset": 1})
        # Limite absurdo e aparado, nao recusado.
        aparado = await client.get("/me/schedules", params={"limit": 99999, "offset": -5})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert inteira.status_code == 200
    assert len(inteira.json()["itens"]) == 3 and inteira.json()["total"] == 3
    assert pagina.status_code == 200 and len(pagina.json()["itens"]) == 1
    # The total is NOT the page size: it is how many rows exist in the slice.
    assert pagina.json()["total"] == 3
    assert pagina.json()["itens"][0]["job_id"] == inteira.json()["itens"][1]["job_id"]
    assert aparado.status_code == 200 and len(aparado.json()["itens"]) == 3


@pytest.mark.asyncio
async def test_total_uses_the_same_slice_as_the_page(client, db, monkeypatch):
    """The total counts what the list lists: neither other people's workflows nor
    workflows in the trash.

    A total larger than the slice would make the web offer "Ver mais" (see
    more) for rows that would never arrive.
    """
    from app.api.dependencies import get_db
    from app.core.rate_limiter import limiter
    from app.main import app

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    monkeypatch.setattr(limiter, "enabled", False)
    try:
        await _workflow(db, "meu", workspace="ws-test-001")
        await _workflow(db, "alheio", workspace="ws-de-outro")
        await _workflow(db, "lixeira", workspace="ws-test-001", deleted_at=datetime(2026, 1, 1))
        for hash_ in ("meu", "alheio", "lixeira"):
            await _schedule(db, hash_)

        r = await client.get("/me/schedules", params={"limit": 1})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert [i["workflow_id"] for i in r.json()["itens"]] == ["meu"]
