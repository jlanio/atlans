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
QUEM = "usr-1"


def _definition(com_schedule=True, conn=None):
    nodes = [{"id": "n1", "name": "WFS", "type": "datasource",
              "properties": {"credential_id": "cred-1", **({"connectionString": conn} if conn else {})}}]
    if com_schedule:
        nodes.insert(0, {
            "id": "t1", "name": "ScheduleTrigger", "type": "trigger",
            "properties": {"strategy": "cron", "cron_expression": "0 6 * * *",
                           "timezone": "America/Cuiaba", "active": True},
        })
    return {"nodes": nodes, "edges": [{"source": "t1", "target": "n1"}]}


def _servico(original, nomes_no_workspace=()):
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
    resultado.all.return_value = [(n,) for n in nomes_no_workspace]
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
def _sem_schedule_real():
    """`apply_schedule_if_needed` touches the database; the target here is the definition."""
    with patch("app.services.workflow_service.apply_schedule_if_needed",
               new=AsyncMock()) as m:
        yield m


@pytest.fixture(autouse=True)
def credenciais_de_quem_duplica():
    """The credential guard (SEG-12) accepting: the target here is the copy, and
    the refusal is proven in test_workflow_credencial_guard.py. The query
    touches the credentials table, which the stubbed CRUD does not have."""
    with patch("app.services.workflow_service.assert_credentials_accessible",
               new=AsyncMock(return_value=None)) as m:
        yield m


# ── Nome ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nome_derivado_do_original():
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações"


@pytest.mark.asyncio
async def test_desambigua_quando_a_copia_ja_existe():
    """There is a UniqueConstraint(name, workspace_id): without this, duplicating
    twice returned 409 before the user saw the copy."""
    svc = _servico(_original(), nomes_no_workspace=["Edificações", "Cópia de Edificações"])

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações (2)"


@pytest.mark.asyncio
async def test_desambigua_repetidamente():
    svc = _servico(_original(), nomes_no_workspace=[
        "Cópia de Edificações", "Cópia de Edificações (2)", "Cópia de Edificações (3)",
    ])

    assert (await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)).name == "Cópia de Edificações (4)"


@pytest.mark.asyncio
async def test_nome_explicito_prevalece():
    copia = await _servico(_original()).duplicate_workflow("wf-1", "Teste 2026", duplicated_by=QUEM)

    assert copia.name == "Teste 2026"


@pytest.mark.asyncio
async def test_nome_em_branco_cai_no_derivado():
    copia = await _servico(_original()).duplicate_workflow("wf-1", "   ", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações"


# ── Collision on INSERT ──────────────────────────────────────────────────────
#
# `_nome_de_copia` READS the taken names and the INSERT comes afterwards: there
# is a window between the two. Two simultaneous duplications read the same set
# and propose the same name; the second one hits the constraint. No test made
# `crud.create` fail, so that path stayed uncovered until it became a 409 on
# the user's screen.
#
# `move` already handled the same race (workflow_move_service._aplicar); these
# tests pin down the equivalent handling in duplication.


def _conflito(nome: str) -> WorkflowNameConflictError:
    return WorkflowNameConflictError(f"Já existe um workflow chamado '{nome}' neste workspace.")


def _servico_que_falha(original, falhas: int, nomes_no_workspace=()):
    """Like `_servico`, but `crud.create` raises a conflict on the first `falhas` calls.

    The names already tried go into `nomes_no_workspace` on each failure — that
    is what the real database would do: the next read sees whoever caused the
    collision.
    """
    svc = _servico(original, nomes_no_workspace=nomes_no_workspace)
    ocupados = list(nomes_no_workspace)
    tentativas: list[str] = []

    async def _create(name, definition, **kwargs):
        tentativas.append(name)
        if len(tentativas) <= falhas:
            ocupados.append(name)
            svc.crud.db.execute.return_value.all.return_value = [(n,) for n in ocupados]
            raise _conflito(name)
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)
    svc.tentativas = tentativas
    return svc


@pytest.mark.asyncio
async def test_colisao_no_insert_e_resolvida_recalculando_o_nome():
    """Primeira aposta e recalcular: "(2)" e melhor nome que um hex aleatorio."""
    svc = _servico_que_falha(_original(), falhas=1)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert svc.tentativas == ["Cópia de Edificações", "Cópia de Edificações (2)"]
    assert copia.name == "Cópia de Edificações (2)"


@pytest.mark.asyncio
async def test_colisao_persistente_cai_no_sufixo_unico():
    """Colliding twice indicates a real race — the hex competes with nobody."""
    svc = _servico_que_falha(_original(), falhas=2)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert len(svc.tentativas) == 3
    assert copia.name.startswith("Cópia de Edificações (")
    # Random suffix, not the counter: 6 hex chars in parentheses.
    sufixo = copia.name.rsplit("(", 1)[1].rstrip(")")
    assert len(sufixo) == 6 and all(c in "0123456789abcdef" for c in sufixo)


@pytest.mark.asyncio
async def test_colisao_nas_tres_tentativas_vira_erro_legivel():
    """Better a 409 with its own message than a raw IntegrityError turning into a 500."""
    svc = _servico_que_falha(_original(), falhas=99)

    with pytest.raises(WorkflowNameConflictError, match="nome livre para a cópia"):
        await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert len(svc.tentativas) == 3


@pytest.mark.asyncio
async def test_nome_explicito_nao_e_renomeado_na_colisao():
    """Whoever typed the name deserves to know it collided.

    Renaming on our own would create "Meu Fluxo (2)" for someone who asked for
    "Meu Fluxo" — the collision here is an answer, not an accident of ours.
    """
    svc = _servico_que_falha(_original(), falhas=1)

    with pytest.raises(WorkflowNameConflictError):
        await svc.duplicate_workflow("wf-1", "Meu Fluxo", duplicated_by=QUEM)

    assert svc.tentativas == ["Meu Fluxo"]


class _OriginalQueExpira:
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
async def test_retentativa_nao_le_o_original_depois_do_rollback():
    """Regression: the retry read `original.name` and `original.workspace_id` again."""
    original = _OriginalQueExpira(
        id_hash="wf-1", workspace_id=WS, name="Edificações", definition=_definition(),
        description="d", params_schema={}, group_id=None, priority=0, notification_url=None,
        # The copy inherits the original's provenance — read BEFORE the first
        # write (in the capture block), like all the fields here.
        origem="usuario",
    )

    svc = _servico(original)
    ocupados: list[str] = []
    tentativas: list[str] = []

    async def _create(name, definition, **kwargs):
        tentativas.append(name)
        if len(tentativas) == 1:
            ocupados.append(name)
            svc.crud.db.execute.return_value.all.return_value = [(n,) for n in ocupados]
            original.expirar()          # that is what SQLAlchemy's rollback does
            raise _conflito(name)
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações (2)"
    assert copia.workspace_id == WS      # the workspace survived the expiration


@pytest.mark.asyncio
async def test_erro_de_outra_natureza_nao_e_engolido_pelo_retry():
    """The retry exists for a NAME collision; everything else has to surface intact."""
    svc = _servico(_original())
    svc.crud.create = AsyncMock(side_effect=RuntimeError("conexão caiu"))

    with pytest.raises(RuntimeError, match="conexão caiu"):
        await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert svc.crud.create.await_count == 1


# ── Autoria ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_copia_e_de_quem_copiou_e_as_credenciais_sao_conferidas_contra_ele(
    credenciais_de_quem_duplica,
):
    svc = _servico(_original())

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    kw = svc.crud.create.await_args.kwargs
    assert (kw["created_by_id"], kw["updated_by_id"]) == (QUEM, QUEM)
    _db, ids, usuario = credenciais_de_quem_duplica.await_args.args
    assert (ids, usuario) == (["cred-1"], QUEM)
    assert credenciais_de_quem_duplica.await_args.kwargs == {"shared_workspace_id": WS}


# ── Workspace ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_copia_fica_no_mesmo_workspace():
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.workspace_id == WS


# ── Agendamento ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agendamento_acompanha_desligado():
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    trigger = next(n for n in copia.definition["nodes"] if n["name"] == "ScheduleTrigger")
    assert trigger["properties"]["active"] is False
    # The rest of the configuration stays: the user turns it on without reconfiguring cron and time zone.
    assert trigger["properties"]["cron_expression"] == "0 6 * * *"
    assert trigger["properties"]["timezone"] == "America/Cuiaba"


@pytest.mark.asyncio
async def test_original_continua_agendado():
    """Regression: the ORM definition is observed by SQLAlchemy — mutating it
    would mark the SOURCE workflow as dirty and turn off its schedule."""
    original = _original()

    await _servico(original).duplicate_workflow("wf-1", duplicated_by=QUEM)

    trigger = next(n for n in original.definition["nodes"] if n["name"] == "ScheduleTrigger")
    assert trigger["properties"]["active"] is True


@pytest.mark.asyncio
async def test_workflow_sem_agendamento_duplica_normalmente():
    svc = _servico(_original(definition=_definition(com_schedule=False)))

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert [n["name"] for n in copia.definition["nodes"]] == ["WFS"]


# ── Copied content ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_definition_e_copiada_com_as_credenciais():
    """No mesmo workspace o credential_id continua resolvendo."""
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    no = next(n for n in copia.definition["nodes"] if n["name"] == "WFS")
    assert no["properties"]["credential_id"] == "cred-1"


@pytest.mark.asyncio
async def test_connection_string_chega_cifrada_na_copia():
    """The cycle is decrypt on get, encrypt on create.

    `get_workflow_by_hash` returns the definition IN PLAIN TEXT (it decrypts the
    connectionString), and `create_workflow` re-encrypts it. The copy must not
    store the connection string in plain text in the database.
    """
    from app.core.utils.encryption import encrypt_string

    svc = _servico(_original(definition=_definition(conn=encrypt_string("host=db user=x"))))

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    no = next(n for n in copia.definition["nodes"] if n["name"] == "WFS")
    assert no["properties"]["connectionString"].startswith("gAAAA")


@pytest.mark.asyncio
async def test_params_schema_acompanha():
    """Regression: `create_workflow` only received name/definition/workspace.

    It is the params_schema that makes the screen ask for the parameters before
    executing (handleRunClick in the front end). Without it, the copy triggers
    right away and silently, with an empty schema — behavior silently different
    from the original's.
    """
    esquema = {"ano": {"type": "number", "required": True}}
    svc = _servico(_original(params_schema=esquema))

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert svc.crud.create.await_args.kwargs["params_schema"] == esquema


@pytest.mark.asyncio
async def test_configuracao_do_workflow_acompanha():
    svc = _servico(_original(
        description="Valida edificações", group_id="grp-1",
        priority=5, notification_url="https://hook",
    ))

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    kw = svc.crud.create.await_args.kwargs
    assert kw["description"] == "Valida edificações"
    assert kw["group_id"] == "grp-1"
    assert kw["priority"] == 5
    assert kw["notification_url"] == "https://hook"


@pytest.mark.asyncio
async def test_pins_e_portal_nao_acompanham():
    """`create_workflow` receives only name and definition — pins point to the
    original's runs and a published portal must not propagate without someone
    asking."""
    svc = _servico(_original(pinned_outputs={"n1": "art-1"}, portal_access="public"))

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    _nome, _definition = svc.crud.create.await_args.args[:2]
    assert "pinned_outputs" not in svc.crud.create.await_args.kwargs
    assert "portal_access" not in svc.crud.create.await_args.kwargs
