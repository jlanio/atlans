# tests/integration/test_me_schedules.py
"""`GET /me/schedules` — os agendamentos da pessoa, entre todos os seus
workspaces, um por linha. A lógica mora em `listar_agendamentos_de`, testada
aqui contra tabelas reais num SQLite de memória (o endpoint é só um wrapper
`Depends(get_user_workspace_ids)` + a chamada).

Molde: `test_listagem_projetos.py` — mesma família de listagem cruzada.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.models import Schedule, Workflow
from app.schemas.me import AgendamentoMeu
from app.services.schedule_service import listar_agendamentos_de

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
        job_id=job, workspace_id=workflow_hash,  # workspace_id do schedule é ignorado de propósito
    ))
    await db.commit()
    return job


async def _listar(db, workspace_ids):
    itens = await listar_agendamentos_de(db, workspace_ids)
    # Valida o contrato de saída de passagem.
    for i in itens:
        AgendamentoMeu.model_validate(i)
    return itens


@pytest.mark.asyncio
async def test_so_os_meus_workspaces(db):
    await _workflow(db, "meu", workspace=WS_1)
    await _workflow(db, "alheio", workspace=WS_2)
    await _schedule(db, "meu")
    await _schedule(db, "alheio")

    itens = await _listar(db, [WS_1])
    assert [i["workflow_id"] for i in itens] == ["meu"]


@pytest.mark.asyncio
async def test_soft_deletado_fica_de_fora(db):
    await _workflow(db, "vivo", workspace=WS_1)
    await _workflow(db, "lixeira", workspace=WS_1, deleted_at=datetime(2026, 1, 1))
    await _schedule(db, "vivo")
    await _schedule(db, "lixeira")

    itens = await _listar(db, [WS_1])
    assert [i["workflow_id"] for i in itens] == ["vivo"]


@pytest.mark.asyncio
async def test_ordem_ativos_primeiro_depois_proxima_nulls_por_ultimo(db):
    await _workflow(db, "wf", workspace=WS_1)
    cedo = datetime(2030, 1, 1, 6, 0)
    tarde = datetime(2030, 1, 1, 18, 0)
    await _schedule(db, "wf", active=False, next_run_at=cedo)     # pausado → por último
    await _schedule(db, "wf", active=True, next_run_at=None)      # ativo sem próxima → depois dos ativos com data
    await _schedule(db, "wf", active=True, next_run_at=tarde)
    await _schedule(db, "wf", active=True, next_run_at=cedo)

    itens = await _listar(db, [WS_1])
    ativos = [i for i in itens if i["active"]]
    # Ativos primeiro; entre eles, por próxima execução crescente, nulo por último.
    assert [i["next_run_at"] for i in ativos[:2]] == [
        cedo.replace(tzinfo=timezone.utc), tarde.replace(tzinfo=timezone.utc),
    ]
    assert ativos[-1]["next_run_at"] is None
    # O pausado vem depois de todos os ativos.
    assert itens[-1]["active"] is False


@pytest.mark.asyncio
async def test_datas_saem_tz_aware(db):
    """Naive no banco (UTC) → com offset na resposta, senão a web lê como local."""
    await _workflow(db, "wf", workspace=WS_1)
    await _schedule(db, "wf", next_run_at=datetime(2030, 5, 1, 9, 0))

    item = (await _listar(db, [WS_1]))[0]
    assert item["next_run_at"].tzinfo is not None
    assert item["next_run_at"] == datetime(2030, 5, 1, 9, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_traz_nome_e_flag_ative_do_workflow(db):
    await _workflow(db, "wf-desligado", workspace=WS_1, flag_ative=False)
    await _schedule(db, "wf-desligado", active=True)

    item = (await _listar(db, [WS_1]))[0]
    assert item["workflow_name"] == "wf-desligado"
    # "Pausado" tem duas causas: o schedule está ativo, mas o workflow não.
    assert item["active"] is True
    assert item["flag_ative"] is False


@pytest.mark.asyncio
async def test_traz_origem_do_workflow(db):
    """A origem vem do JOIN com Workflow, para o selo "assistente" na Home.
    Default "usuario" quando o fluxo não veio do assistente."""
    await _workflow(db, "do-usuario", workspace=WS_1, origem="usuario")
    await _workflow(db, "do-assistente", workspace=WS_1, origem="assistente")
    await _schedule(db, "do-usuario")
    await _schedule(db, "do-assistente")

    itens = await _listar(db, [WS_1])
    origem_por_fluxo = {i["workflow_id"]: i["origem"] for i in itens}
    assert origem_por_fluxo == {"do-usuario": "usuario", "do-assistente": "assistente"}


@pytest.mark.asyncio
async def test_sem_workspaces_lista_vazia(db):
    await _workflow(db, "wf", workspace=WS_1)
    await _schedule(db, "wf")
    assert await _listar(db, []) == []


@pytest.mark.asyncio
async def test_pagina_com_limit_e_offset(db):
    """Era a unica listagem nova sem teto — Chats corta em 50, Acervo em 200."""
    for i in range(5):
        await _workflow(db, f"wf-{i}")
        await _schedule(db, f"wf-{i}", next_run_at=datetime(2026, 1, 1 + i, tzinfo=timezone.utc))

    primeira = await listar_agendamentos_de(db, [WS_1], limit=2, offset=0)
    segunda = await listar_agendamentos_de(db, [WS_1], limit=2, offset=2)
    inteira = await listar_agendamentos_de(db, [WS_1], limit=100, offset=0)

    assert len(primeira) == 2 and len(segunda) == 2 and len(inteira) == 5
    # Paginas disjuntas e na mesma ordem da lista inteira.
    assert [i["job_id"] for i in primeira + segunda] == [i["job_id"] for i in inteira[:4]]


@pytest.mark.asyncio
async def test_a_ordem_desempata_de_forma_estavel(db):
    """Mesmo `active` e mesmo `next_run_at`: sem o terceiro criterio, duas linhas
    podiam trocar de pagina entre requisicoes."""
    quando = datetime(2026, 3, 1, tzinfo=timezone.utc)
    for i in range(4):
        await _workflow(db, f"igual-{i}")
        await _schedule(db, f"igual-{i}", next_run_at=quando)

    uma = [i["job_id"] for i in await listar_agendamentos_de(db, [WS_1])]
    outra = [i["job_id"] for i in await listar_agendamentos_de(db, [WS_1])]
    assert uma == outra


@pytest.mark.asyncio
async def test_a_rota_responde_e_repassa_limit_offset(client, db, monkeypatch):
    """Fecha o circuito: o decorador do limiter, os query params e o ENVELOPE.

    A resposta e `{itens, total}` — o mesmo formato de `GET /assistente/conversas`.
    Sem o `total`, o teto de 200 truncava em silencio: a web recebia a pagina e
    nao tinha como saber que havia mais linhas para pedir.
    """
    from app.api.dependencies import get_db
    from app.core.rate_limiter import limiter
    from app.main import app

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    monkeypatch.setattr(limiter, "enabled", False)  # o 60/min conta por IP entre testes
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
    # O total NAO e o tamanho da pagina: e quantas linhas existem no recorte.
    assert pagina.json()["total"] == 3
    assert pagina.json()["itens"][0]["job_id"] == inteira.json()["itens"][1]["job_id"]
    assert aparado.status_code == 200 and len(aparado.json()["itens"]) == 3


@pytest.mark.asyncio
async def test_o_total_usa_o_mesmo_recorte_da_pagina(client, db, monkeypatch):
    """O total conta o que a lista lista: nem fluxo alheio, nem fluxo na lixeira.

    Um total maior que o recorte faria a web oferecer "Ver mais" para linhas que
    nunca chegariam.
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
