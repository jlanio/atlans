# tests/integration/test_listagem_projetos.py
"""
The project listing says what each workflow IS: how it fires, whether it is
scheduled (and for when), and who touched it last.

Three sources, three queries per page — never one per row:
- triggers: SQL expressions over `definition`, in the same style as
  `is_subworkflow` (see test_listagem_marca_subfluxo.py);
- scheduling: `schedules WHERE workflow_hash IN (...)`, merged in the service;
- authorship: `users WHERE id_hash IN (...)`, likewise.

The tests bring up the real tables in an in-memory SQLite and go through the
service, which is what does the merging — an assertion on the CRUD alone would
not prove that `schedule` reaches the response, nor that it arrives with a
time zone.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.models import Schedule, Workflow
from app.models.user import User
from app.schemas.workflow import WorkflowListItem
from app.services.workflow_service import WorkflowService

WS = "ws-1"


def _definition(*nomes):
    return {
        "nodes": [{"id": f"n{i}", "name": nome} for i, nome in enumerate(nomes)],
        "edges": [],
    }


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[Workflow.__table__, Schedule.__table__, User.__table__],
        )
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


async def _semear(db, *workflows, workspace=WS):
    """Each item is (id_hash, definition) or (id_hash, definition, extras)."""
    for i, item in enumerate(workflows):
        hash_, definition, *resto = item
        extras = resto[0] if resto else {}
        db.add(Workflow(**{
            "id_hash": hash_, "name": hash_, "definition": definition,
            "flag_ative": True, "priority": i, "workspace_id": workspace,
            **extras,
        }))
    await db.commit()


def _schedule(workflow_hash, *, active=True, next_run_at=None, last_run_at=None,
              strategy="cron", cron_expression="0 6 * * *", **extras):
    return Schedule(
        workflow_hash=workflow_hash, active=active, strategy=strategy,
        cron_expression=cron_expression, next_run_at=next_run_at,
        last_run_at=last_run_at, timezone="America/Cuiaba",
        job_id=f"job-{uuid4()}", workspace_id=WS,
        **extras,
    )


async def _por_hash(db, workspace_id=WS):
    itens = await WorkflowService(db).list_workflows_metadata(workspace_id=workspace_id)
    return {item["id_hash"]: WorkflowListItem.model_validate(item) for item in itens}


# ── gatilhos ────────────────────────────────────────────────────────────────

GATILHOS = ["has_webhook_trigger", "has_schedule_trigger", "has_file_trigger", "has_geofence_trigger"]


class TestGatilhos:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("node, campo", [
        ("WebhookTrigger", "has_webhook_trigger"),
        ("ScheduleTrigger", "has_schedule_trigger"),
        ("FileTrigger", "has_file_trigger"),
        ("GeofenceTrigger", "has_geofence_trigger"),
    ])
    async def test_cada_gatilho_marca_so_o_seu_campo(self, db, node, campo):
        await _semear(db, ("wf", _definition(node, "PythonScript")))

        item = (await _por_hash(db))["wf"]
        for nome in GATILHOS:
            assert getattr(item, nome) is (nome == campo), nome

    @pytest.mark.asyncio
    async def test_dois_gatilhos_marcam_os_dois(self, db):
        """A workflow can fire through more than one path — the web shows
        "Agendado + webhook" (scheduled + webhook); no boolean may mask another."""
        await _semear(db, ("wf", _definition("ScheduleTrigger", "WebhookTrigger", "PythonScript")))

        item = (await _por_hash(db))["wf"]
        assert item.has_schedule_trigger is True
        assert item.has_webhook_trigger is True
        assert item.has_file_trigger is False
        assert item.has_geofence_trigger is False

    @pytest.mark.asyncio
    async def test_sem_gatilho_nenhum_e_so_manual(self, db):
        await _semear(db, ("wf", _definition("PythonScript", "PublishMap")))

        item = (await _por_hash(db))["wf"]
        assert not any(getattr(item, nome) for nome in GATILHOS)
        # The neighboring flags keep reading the same column without getting in each other's way.
        assert item.has_publish_map is True
        assert item.is_subworkflow is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("definition", [{}, {"edges": []}], ids=["vazia", "sem_a_chave_nodes"])
    async def test_definition_sem_nodes_nao_derruba_a_resposta(self, db, definition):
        """Same regression as `is_subworkflow`: without `nodes` LIKE propagates
        NULL and Pydantic rejects None in a `bool` — the whole list gave 500."""
        await _semear(db, ("torto", definition))

        item = (await _por_hash(db))["torto"]
        assert not any(getattr(item, nome) for nome in GATILHOS)


# ── agendamento ─────────────────────────────────────────────────────────────

class TestAgendamento:

    @pytest.mark.asyncio
    async def test_sem_schedule_e_none(self, db):
        await _semear(db, ("wf", _definition("PythonScript")))

        assert (await _por_hash(db))["wf"].schedule is None

    @pytest.mark.asyncio
    async def test_ativo_com_proxima_sai_em_utc_aware(self, db):
        """`next_run_at` is stored as NAIVE UTC by the scheduler. Without the tzinfo
        Pydantic serializes "2026-09-08T09:00:00", and the browser in Cuiabá
        reads it as 09:00 local — three hours after the real time."""
        await _semear(db, ("wf", _definition("ScheduleTrigger")))
        db.add(_schedule(
            "wf", active=True,
            next_run_at=datetime(2026, 9, 8, 9, 0),
            last_run_at=datetime(2026, 9, 7, 9, 0),
        ))
        await db.commit()

        item = (await _por_hash(db))["wf"]
        assert item.schedule is not None
        assert item.schedule.active is True
        assert item.schedule.next_run_at == datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)
        assert item.schedule.next_run_at.tzinfo is not None
        assert item.schedule.last_run_at == datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc)
        assert item.schedule.strategy == "cron"
        assert item.schedule.cron_expression == "0 6 * * *"
        assert item.schedule.timezone == "America/Cuiaba"

        # What the web receives: ISO WITH offset.
        json = item.model_dump(mode="json")["schedule"]
        assert json["next_run_at"].endswith(("Z", "+00:00")), json["next_run_at"]

    @pytest.mark.asyncio
    async def test_pausado(self, db):
        await _semear(db, ("wf", _definition("ScheduleTrigger")))
        db.add(_schedule("wf", active=False, next_run_at=None))
        await db.commit()

        schedule = (await _por_hash(db))["wf"].schedule
        assert schedule.active is False
        assert schedule.next_run_at is None

    @pytest.mark.asyncio
    async def test_ativo_sem_proxima_calculada(self, db):
        """Freshly created: the scheduler fills `next_run_at` on the next tick.
        The web shows "proxima: calculando…" (next: calculating…) — it must be
        told apart from paused."""
        await _semear(db, ("wf", _definition("ScheduleTrigger")))
        db.add(_schedule("wf", active=True, next_run_at=None))
        await db.commit()

        schedule = (await _por_hash(db))["wf"].schedule
        assert schedule.active is True
        assert schedule.next_run_at is None

    @pytest.mark.asyncio
    async def test_intervalo_leva_interval_e_unit(self, db):
        await _semear(db, ("wf", _definition("ScheduleTrigger")))
        db.add(_schedule("wf", strategy="interval", cron_expression=None, interval=15, unit="minutes"))
        await db.commit()

        schedule = (await _por_hash(db))["wf"].schedule
        assert (schedule.strategy, schedule.interval, schedule.unit) == ("interval", 15, "minutes")
        assert schedule.cron_expression is None

    @pytest.mark.asyncio
    async def test_dois_schedules_prefere_o_ativo_que_dispara_primeiro(self, db):
        await _semear(db, ("wf", _definition("ScheduleTrigger")))
        db.add_all([
            _schedule("wf", active=False, next_run_at=datetime(2026, 9, 8, 1, 0), cron_expression="0 1 * * *"),
            _schedule("wf", active=True, next_run_at=datetime(2026, 9, 8, 12, 0), cron_expression="0 12 * * *"),
            _schedule("wf", active=True, next_run_at=datetime(2026, 9, 8, 6, 0), cron_expression="0 6 * * *"),
            _schedule("wf", active=True, next_run_at=None, cron_expression="0 0 * * *"),
        ])
        await db.commit()

        schedule = (await _por_hash(db))["wf"].schedule
        assert schedule.active is True
        assert schedule.cron_expression == "0 6 * * *"
        assert schedule.next_run_at == datetime(2026, 9, 8, 6, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_dois_schedules_sem_nenhum_ativo_devolve_um_deles(self, db):
        await _semear(db, ("wf", _definition("ScheduleTrigger")))
        db.add_all([
            _schedule("wf", active=False, cron_expression="0 1 * * *"),
            _schedule("wf", active=False, cron_expression="0 2 * * *"),
        ])
        await db.commit()

        schedule = (await _por_hash(db))["wf"].schedule
        assert schedule is not None
        assert schedule.active is False
        assert schedule.cron_expression in {"0 1 * * *", "0 2 * * *"}

    @pytest.mark.asyncio
    async def test_schedule_de_um_workflow_nao_vaza_para_outro(self, db):
        await _semear(db, ("com", _definition("ScheduleTrigger")), ("sem", _definition("PythonScript")))
        db.add(_schedule("com", next_run_at=datetime(2026, 9, 8, 6, 0)))
        await db.commit()

        itens = await _por_hash(db)
        assert itens["com"].schedule is not None
        assert itens["sem"].schedule is None


# ── autoria ─────────────────────────────────────────────────────────────────

def _usuario(id_hash, username, status="active", deleted_at=None):
    return User(
        id_hash=id_hash, username=username, email=f"{username}@example.test",
        hashed_password="x", status=status, role="user", deleted_at=deleted_at,
    )


class TestAutoria:

    @pytest.mark.asyncio
    async def test_resolve_os_dois_nomes(self, db):
        db.add_all([_usuario("u-maria", "maria"), _usuario("u-joao", "joao")])
        await _semear(db, ("wf", _definition("PythonScript"),
                           {"created_by_id": "u-joao", "updated_by_id": "u-maria"}))

        item = (await _por_hash(db))["wf"]
        assert item.created_by_username == "joao"
        assert item.updated_by_username == "maria"
        # The ids are still returned — the web filters "mine" by them.
        assert (item.created_by_id, item.updated_by_id) == ("u-joao", "u-maria")

    @pytest.mark.asyncio
    async def test_id_sem_linha_em_users_vira_none(self, db):
        """`created_by_id`/`updated_by_id` have no FK: an id with no row in `users`
        is possible, and the web shows only "alterado ha X" (changed X ago)
        without making up a name."""
        await _semear(db, ("wf", _definition("PythonScript"),
                           {"created_by_id": "u-sumiu", "updated_by_id": "u-sumiu"}))

        item = (await _por_hash(db))["wf"]
        assert item.created_by_username is None
        assert item.updated_by_username is None

    @pytest.mark.asyncio
    async def test_usuario_excluido_soft_delete_mantem_o_nome(self, db):
        """"Excluir usuario" (delete user) in the admin is a soft delete
        (status='deleted', the row stays). The name IS STILL returned — the same
        attribution the History shows; we do not filter by status, on purpose."""
        db.add(_usuario("u-ex", "maria", status="deleted", deleted_at=datetime(2026, 1, 1)))
        await _semear(db, ("wf", _definition("PythonScript"),
                           {"created_by_id": "u-ex", "updated_by_id": "u-ex"}))

        item = (await _por_hash(db))["wf"]
        assert item.created_by_username == "maria"
        assert item.updated_by_username == "maria"

    @pytest.mark.asyncio
    async def test_sem_id_de_autor_nao_consulta_e_devolve_none(self, db):
        await _semear(db, ("wf", _definition("PythonScript")))

        item = (await _por_hash(db))["wf"]
        assert item.created_by_id is None
        assert item.created_by_username is None
        assert item.updated_by_username is None


# ── response shape ──────────────────────────────────────────────────────────

class TestForma:

    def test_deleted_at_saiu_do_schema(self):
        """The listing filters `deleted_at IS NULL`: the field was always null and
        only took up bytes. No consumer of the listing reads it."""
        assert "deleted_at" not in WorkflowListItem.model_fields

    @pytest.mark.asyncio
    async def test_payload_nao_carrega_deleted_at(self, db):
        await _semear(db, ("wf", _definition("PythonScript")))

        payload = (await _por_hash(db))["wf"].model_dump()
        assert "deleted_at" not in payload
        assert {"schedule", "created_by_username", "updated_by_username", *GATILHOS} <= set(payload)

    @pytest.mark.asyncio
    async def test_listagem_por_varios_workspaces_tem_a_mesma_mescla(self, db):
        """`GET /workflows` without `workspace_id` goes through `_by_ids`; the merge
        must be the same, otherwise the command palette and the list diverge."""
        db.add(_usuario("u-maria", "maria"))
        await _semear(db, ("a", _definition("ScheduleTrigger"), {"updated_by_id": "u-maria"}), workspace="ws-a")
        await _semear(db, ("b", _definition("WebhookTrigger")), workspace="ws-b")
        db.add(_schedule("a", next_run_at=datetime(2026, 9, 8, 6, 0)))
        await db.commit()

        itens = await WorkflowService(db).list_workflows_metadata_by_ids(["ws-a", "ws-b"])
        por_hash = {i["id_hash"]: WorkflowListItem.model_validate(i) for i in itens}
        assert set(por_hash) == {"a", "b"}
        assert por_hash["a"].schedule.next_run_at.tzinfo is not None
        assert por_hash["a"].updated_by_username == "maria"
        assert por_hash["b"].has_webhook_trigger is True
        assert por_hash["b"].schedule is None

    @pytest.mark.asyncio
    async def test_lista_vazia_nao_consulta_nada_alem_da_listagem(self, db, monkeypatch):
        """Without workflows, the merge short-circuits before touching `schedules`
        and `users` — the two extra `IN`s only exist when there is something to
        enrich."""
        import app.services.workflow_service as svc

        async def _proibido(*a, **k):
            raise AssertionError("nao deveria consultar schedules/users com a lista vazia")

        monkeypatch.setattr(svc, "_resumos_de_agendamento", _proibido)
        monkeypatch.setattr(svc, "_nomes_de_usuarios", _proibido)
        assert await WorkflowService(db).list_workflows_metadata(workspace_id="ws-vazio") == []

    @pytest.mark.asyncio
    async def test_excluido_nao_entra(self, db):
        await _semear(db, ("vivo", _definition("PythonScript")),
                      ("lixeira", _definition("PythonScript"), {"deleted_at": datetime(2026, 1, 1)}))

        assert set(await _por_hash(db)) == {"vivo"}


# ── origem (usuario | assistente) ─────────────────────────────────────────────

class TestOrigem:
    """Workflows from the Home assistant (`origem="assistente"`) are left out of
    listings by default; the "mostrar os do assistente" (show the assistant's)
    toggle brings them back."""

    @pytest.mark.asyncio
    async def test_do_assistente_some_por_padrao(self, db):
        await _semear(
            db,
            ("meu", _definition("PythonScript")),
            ("do_assistente", _definition("PythonScript"), {"origem": "assistente"}),
        )
        assert set(await _por_hash(db)) == {"meu"}

    @pytest.mark.asyncio
    async def test_com_interruptor_aparece(self, db):
        await _semear(
            db,
            ("meu", _definition("PythonScript")),
            ("do_assistente", _definition("PythonScript"), {"origem": "assistente"}),
        )
        itens = await WorkflowService(db).list_workflows_metadata(
            workspace_id=WS, incluir_do_assistente=True,
        )
        por_hash = {i["id_hash"]: WorkflowListItem.model_validate(i) for i in itens}
        assert set(por_hash) == {"meu", "do_assistente"}
        assert por_hash["do_assistente"].origem == "assistente"

    @pytest.mark.asyncio
    async def test_default_do_schema_e_usuario(self, db):
        await _semear(db, ("meu", _definition("PythonScript")))
        assert (await _por_hash(db))["meu"].origem == "usuario"

    @pytest.mark.asyncio
    async def test_filtro_tambem_na_listagem_por_ids(self, db):
        """The path without `workspace_id` (several workspaces) hides them the same way."""
        await _semear(
            db,
            ("meu", _definition("PythonScript")),
            ("do_assistente", _definition("PythonScript"), {"origem": "assistente"}),
        )
        escondido = await WorkflowService(db).list_workflows_metadata_by_ids([WS])
        assert {i["id_hash"] for i in escondido} == {"meu"}
        visivel = await WorkflowService(db).list_workflows_metadata_by_ids(
            [WS], incluir_do_assistente=True,
        )
        assert {i["id_hash"] for i in visivel} == {"meu", "do_assistente"}
