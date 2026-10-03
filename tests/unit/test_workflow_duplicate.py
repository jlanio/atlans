# tests/unit/test_workflow_duplicate.py
"""Workflow duplication.

The copy stays in the SAME workspace on purpose: `credential_id` in the
definition only resolves for someone with access to the workspace (see
credential_loader) and referenced sub-workflows need to live in it — copying to
another workspace would produce a workflow that looks intact and fails when
executed.

The schedule comes along TURNED OFF. Duplicating usually precedes an edit, and a
copy that is born triggering on its own doubles the load and the writes to the
Drive without anyone asking for it. It is turned off in the definition itself —
not only in the database — because `apply_schedule_if_needed` reads the node's
`active`: changing only the database would leave the canvas saying "active" and
the schedule off.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import WorkflowNameConflictError
from app.services.workflow_service import WorkflowService


WS = "ws-1"
# Who is duplicating. The author is mandatory: it is against them that the
# service checks the copy's credentials (SEG-12).
ACTOR = "usr-1"


def _definition(with_schedule=True, conn=None):
    nodes = [{"id": "n1", "name": "WFS", "type": "datasource",
              "properties": {"credential_id": "cred-1", **({"connectionString": conn} if conn else {})}}]
    if with_schedule:
        nodes.insert(0, {
            "id": "t1", "name": "ScheduleTrigger", "type": "trigger",
            "properties": {"strategy": "cron", "cron_expression": "0 6 * * *",
                           "timezone": "America/Cuiaba", "active": True},
        })
    return {"nodes": nodes, "edges": [{"source": "t1", "target": "n1"}]}


def _service(original, names_in_workspace=()):
    """Service with the CRUD stubbed; `create` returns what it received."""
    svc = WorkflowService(MagicMock())
    svc.crud = MagicMock()
    svc.crud.get_by_hash = AsyncMock(return_value=original)

    async def _create(name, definition, **kwargs):
        # `name` is a reserved MagicMock argument (it names the mock itself),
        # so it needs to be assigned afterwards.
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)

    resultado = MagicMock()
    resultado.all.return_value = [(n,) for n in names_in_workspace]
    svc.crud.db = MagicMock(execute=AsyncMock(return_value=resultado), rollback=AsyncMock())
    return svc


def _original(definition=None, **kw):
    base = {"id_hash": "wf-1", "workspace_id": WS,
            "definition": definition if definition is not None else _definition()}
    base.update(kw)
    m = MagicMock(**base)
    m.name = "Edificações"      # reserved in the MagicMock constructor
    return m


@pytest.fixture(autouse=True)
def _without_real_schedule():
    """`apply_schedule_if_needed` touches the database; the target here is the definition."""
    with patch("app.services.workflow_service.apply_schedule_if_needed",
               new=AsyncMock()) as m:
        yield m


@pytest.fixture(autouse=True)
def duplicator_credentials():
    """The credential guard (SEG-12) accepting: the target here is the copy, and
    the refusal is proven in test_workflow_credencial_guard.py. The query
    touches the credentials table, which the stubbed CRUD does not have."""
    with patch("app.services.workflow_service.assert_credentials_accessible",
               new=AsyncMock(return_value=None)) as m:
        yield m


# ── Nome ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_name_derived_from_the_original():
    copia = await _service(_original()).duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert copia.name == "Cópia de Edificações"


@pytest.mark.asyncio
async def test_disambiguates_when_the_copy_already_exists():
    """There is a UniqueConstraint(name, workspace_id): without this, duplicating
    twice returned 409 before the user saw the copy."""
    svc = _service(_original(), names_in_workspace=["Edificações", "Cópia de Edificações"])

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert copia.name == "Cópia de Edificações (2)"


@pytest.mark.asyncio
async def test_disambiguates_repeatedly():
    svc = _service(_original(), names_in_workspace=[
        "Cópia de Edificações", "Cópia de Edificações (2)", "Cópia de Edificações (3)",
    ])

    assert (await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)).name == "Cópia de Edificações (4)"


@pytest.mark.asyncio
async def test_explicit_name_prevails():
    copia = await _service(_original()).duplicate_workflow("wf-1", "Teste 2026", duplicated_by=ACTOR)

    assert copia.name == "Teste 2026"


@pytest.mark.asyncio
async def test_blank_name_falls_back_to_the_derived_one():
    copia = await _service(_original()).duplicate_workflow("wf-1", "   ", duplicated_by=ACTOR)

    assert copia.name == "Cópia de Edificações"


# ── Collision on INSERT ──────────────────────────────────────────────────────
#
# `_copy_name` READS the taken names and the INSERT comes afterwards: there
# is a window between the two. Two simultaneous duplications read the same set
# and propose the same name; the second one hits the constraint. No test made
# `crud.create` fail, so that path stayed uncovered until it became a 409 on
# the user's screen.
#
# `move` already handled the same race (workflow_move_service._apply); these
# tests pin down the equivalent handling in duplication.


def _conflict(nome: str) -> WorkflowNameConflictError:
    return WorkflowNameConflictError(f"Já existe um workflow chamado '{nome}' neste workspace.")


def _failing_service(original, falhas: int, names_in_workspace=()):
    """Like `_service`, but `crud.create` raises a conflict on the first `falhas` calls.

    The names already tried go into `names_in_workspace` on each failure — that
    is what the real database would do: the next read sees whoever caused the
    collision.
    """
    svc = _service(original, names_in_workspace=names_in_workspace)
    ocupados = list(names_in_workspace)
    tentativas: list[str] = []

    async def _create(name, definition, **kwargs):
        tentativas.append(name)
        if len(tentativas) <= falhas:
            ocupados.append(name)
            svc.crud.db.execute.return_value.all.return_value = [(n,) for n in ocupados]
            raise _conflict(name)
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)
    svc.tentativas = tentativas
    return svc


@pytest.mark.asyncio
async def test_insert_collision_is_resolved_by_recomputing_the_name():
    """Primeira aposta e recalcular: "(2)" e melhor nome que um hex aleatorio."""
    svc = _failing_service(_original(), falhas=1)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert svc.tentativas == ["Cópia de Edificações", "Cópia de Edificações (2)"]
    assert copia.name == "Cópia de Edificações (2)"


@pytest.mark.asyncio
async def test_persistent_collision_falls_back_to_unique_suffix():
    """Colliding twice indicates a real race — the hex competes with nobody."""
    svc = _failing_service(_original(), falhas=2)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert len(svc.tentativas) == 3
    assert copia.name.startswith("Cópia de Edificações (")
    # Random suffix, not the counter: 6 hex chars in parentheses.
    sufixo = copia.name.rsplit("(", 1)[1].rstrip(")")
    assert len(sufixo) == 6 and all(c in "0123456789abcdef" for c in sufixo)


@pytest.mark.asyncio
async def test_collision_on_all_three_attempts_becomes_readable_error():
    """Better a 409 with its own message than a raw IntegrityError turning into a 500."""
    svc = _failing_service(_original(), falhas=99)

    with pytest.raises(WorkflowNameConflictError, match="nome livre para a cópia"):
        await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert len(svc.tentativas) == 3


@pytest.mark.asyncio
async def test_explicit_name_is_not_renamed_on_collision():
    """Whoever typed the name deserves to know it collided.

    Renaming on our own would create "Meu Fluxo (2)" for someone who asked for
    "Meu Fluxo" — the collision here is an answer, not an accident of ours.
    """
    svc = _failing_service(_original(), falhas=1)

    with pytest.raises(WorkflowNameConflictError):
        await svc.duplicate_workflow("wf-1", "Meu Fluxo", duplicated_by=ACTOR)

    assert svc.tentativas == ["Meu Fluxo"]


class _ExpiringOriginal:
    """Stub with SQLAlchemy's expiration semantics.

    `MagicMock` responds to any attribute forever, so no test based on it sees
    the real problem of this retry: `create_workflow` calls `rollback()` on the
    collision, and the rollback expires EVERY object in the session —
    including `original`, which did not even take part in the write. In an
    AsyncSession, reading an expired attribute is not one more SELECT, it is
    `MissingGreenlet`: the retry would return a 500 instead of the 409 it exists
    to avoid.
    """

    def __init__(self, **campos):
        object.__setattr__(self, "_campos", campos)
        object.__setattr__(self, "_expirado", False)

    def expirar(self):
        object.__setattr__(self, "_expirado", True)

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        if object.__getattribute__(self, "_expirado"):
            raise RuntimeError(
                f"leitura de '{nome}' com a sessão expirada — em AsyncSession isto é "
                "MissingGreenlet. Capture os campos do original ANTES da primeira escrita."
            )
        return object.__getattribute__(self, "_campos")[nome]


@pytest.mark.asyncio
async def test_retry_does_not_read_the_original_after_the_rollback():
    """Regression: the retry read `original.name` and `original.workspace_id` again."""
    original = _ExpiringOriginal(
        id_hash="wf-1", workspace_id=WS, name="Edificações", definition=_definition(),
        description="d", params_schema={}, group_id=None, priority=0, notification_url=None,
        # The copy inherits the original's provenance — read BEFORE the first
        # write (in the capture block), like all the fields here.
        origem="usuario",
    )

    svc = _service(original)
    ocupados: list[str] = []
    tentativas: list[str] = []

    async def _create(name, definition, **kwargs):
        tentativas.append(name)
        if len(tentativas) == 1:
            ocupados.append(name)
            svc.crud.db.execute.return_value.all.return_value = [(n,) for n in ocupados]
            original.expirar()          # that is what SQLAlchemy's rollback does
            raise _conflict(name)
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert copia.name == "Cópia de Edificações (2)"
    assert copia.workspace_id == WS      # the workspace survived the expiration


@pytest.mark.asyncio
async def test_error_of_another_kind_is_not_swallowed_by_the_retry():
    """The retry exists for a NAME collision; everything else has to surface intact."""
    svc = _service(_original())
    svc.crud.create = AsyncMock(side_effect=RuntimeError("conexão caiu"))

    with pytest.raises(RuntimeError, match="conexão caiu"):
        await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert svc.crud.create.await_count == 1


# ── Autoria ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_copy_belongs_to_the_copier_and_credentials_are_checked_against_them(
    duplicator_credentials,
):
    svc = _service(_original())

    await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    kw = svc.crud.create.await_args.kwargs
    assert (kw["created_by_id"], kw["updated_by_id"]) == (ACTOR, ACTOR)
    _db, ids, usuario = duplicator_credentials.await_args.args
    assert (ids, usuario) == (["cred-1"], ACTOR)
    assert duplicator_credentials.await_args.kwargs == {"shared_workspace_id": WS}


# ── Workspace ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_copy_stays_in_the_same_workspace():
    copia = await _service(_original()).duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert copia.workspace_id == WS


# ── Agendamento ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schedule_comes_along_disabled():
    copia = await _service(_original()).duplicate_workflow("wf-1", duplicated_by=ACTOR)

    trigger = next(n for n in copia.definition["nodes"] if n["name"] == "ScheduleTrigger")
    assert trigger["properties"]["active"] is False
    # The rest of the configuration stays: the user turns it on without reconfiguring cron and time zone.
    assert trigger["properties"]["cron_expression"] == "0 6 * * *"
    assert trigger["properties"]["timezone"] == "America/Cuiaba"


@pytest.mark.asyncio
async def test_original_stays_scheduled():
    """Regression: the ORM definition is observed by SQLAlchemy — mutating it
    would mark the SOURCE workflow as dirty and turn off its schedule."""
    original = _original()

    await _service(original).duplicate_workflow("wf-1", duplicated_by=ACTOR)

    trigger = next(n for n in original.definition["nodes"] if n["name"] == "ScheduleTrigger")
    assert trigger["properties"]["active"] is True


@pytest.mark.asyncio
async def test_workflow_without_schedule_duplicates_normally():
    svc = _service(_original(definition=_definition(with_schedule=False)))

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert [n["name"] for n in copia.definition["nodes"]] == ["WFS"]


# ── Copied content ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_definition_is_copied_with_the_credentials():
    """No mesmo workspace o credential_id continua resolvendo."""
    copia = await _service(_original()).duplicate_workflow("wf-1", duplicated_by=ACTOR)

    no = next(n for n in copia.definition["nodes"] if n["name"] == "WFS")
    assert no["properties"]["credential_id"] == "cred-1"


@pytest.mark.asyncio
async def test_connection_string_arrives_encrypted_in_the_copy():
    """The cycle is decrypt on get, encrypt on create.

    `get_workflow_by_hash` returns the definition IN PLAIN TEXT (it decrypts the
    connectionString), and `create_workflow` re-encrypts it. The copy must not
    store the connection string in plain text in the database.
    """
    from app.core.utils.encryption import encrypt_string

    svc = _service(_original(definition=_definition(conn=encrypt_string("host=db user=x"))))

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    no = next(n for n in copia.definition["nodes"] if n["name"] == "WFS")
    assert no["properties"]["connectionString"].startswith("gAAAA")


@pytest.mark.asyncio
async def test_params_schema_comes_along():
    """Regression: `create_workflow` only received name/definition/workspace.

    It is the params_schema that makes the screen ask for the parameters before
    executing (handleRunClick in the front end). Without it, the copy triggers
    right away and silently, with an empty schema — behavior silently different
    from the original's.
    """
    esquema = {"ano": {"type": "number", "required": True}}
    svc = _service(_original(params_schema=esquema))

    await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    assert svc.crud.create.await_args.kwargs["params_schema"] == esquema


@pytest.mark.asyncio
async def test_workflow_configuration_comes_along():
    svc = _service(_original(
        description="Valida edificações", group_id="grp-1",
        priority=5, notification_url="https://hook",
    ))

    await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    kw = svc.crud.create.await_args.kwargs
    assert kw["description"] == "Valida edificações"
    assert kw["group_id"] == "grp-1"
    assert kw["priority"] == 5
    assert kw["notification_url"] == "https://hook"


@pytest.mark.asyncio
async def test_pins_and_portal_do_not_come_along():
    """`create_workflow` receives only name and definition — pins point to the
    original's runs and a published portal must not propagate without someone
    asking."""
    svc = _service(_original(pinned_outputs={"n1": "art-1"}, portal_access="public"))

    await svc.duplicate_workflow("wf-1", duplicated_by=ACTOR)

    _nome, _definition = svc.crud.create.await_args.args[:2]
    assert "pinned_outputs" not in svc.crud.create.await_args.kwargs
    assert "portal_access" not in svc.crud.create.await_args.kwargs
