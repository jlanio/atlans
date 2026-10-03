# tests/unit/test_workflow_move.py
"""Moving a workflow between workspaces.

The feature's contract is that the operation does NOT fail because of a broken
dependency: whatever stops working at the destination comes out as a warning.
Whatever is a deterministic consequence of the tenant change (schedule turned
off, portal deactivated, group and pins cleared) is applied without asking, by
the same rationale already written in `duplicate_workflow`.

The most important test here is `test_connection_string_e_gravada_cifrada`: the
route's dependency decrypts the definition on the SAME session object, and move
is the first path that rewrites that column.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import workflow_move_service as move_svc


ORIGEM = "ws-origem"
DESTINO = "ws-destino"


def _definition(com_schedule=True, conn=None):
    nodes = [{
        "id": "n1", "name": "WFS", "type": "datasource",
        "properties": {"credential_id": "cred-1", **({"connectionString": conn} if conn else {})},
    }]
    if com_schedule:
        nodes.insert(0, {
            "id": "t1", "name": "ScheduleTrigger", "type": "trigger",
            "properties": {"strategy": "cron", "cron_expression": "0 6 * * *",
                           "timezone": "America/Cuiaba", "active": True},
        })
    return {"nodes": nodes, "edges": [{"source": "t1", "target": "n1"}]}


def _workflow(definition=None, **kw):
    base = {
        "id_hash": "wf-1", "workspace_id": ORIGEM, "group_id": "grp-1",
        "portal_access": "public", "portal_shared_with": ["alguem"],
        "pinned_outputs": None, "pin_metadata": None, "notification_url": None,
        "updated_by_id": None,
        "definition": definition if definition is not None else _definition(),
    }
    base.update(kw)
    m = MagicMock(**base)
    m.name = kw.get("name", "Edificações")   # `name` is reserved in the constructor
    return m


def _crud(wf, nomes_no_destino=()):
    """Stubbed CRUD; `db.execute` returns the names already present at the destination."""
    crud = MagicMock()
    crud.get_by_hash = AsyncMock(return_value=wf)
    crud.create_version = AsyncMock()

    resultado = MagicMock()
    resultado.all.return_value = [(n,) for n in nomes_no_destino]
    crud.db = MagicMock(
        execute=AsyncMock(return_value=resultado),
        commit=AsyncMock(), rollback=AsyncMock(), refresh=AsyncMock(),
    )
    return crud


@pytest.fixture(autouse=True)
def _sem_relatorio():
    """The report has its own database; here the target is the mutations."""
    with patch.object(move_svc, "collect_warnings", new=AsyncMock(return_value=[])) as m:
        yield m


@pytest.fixture(autouse=True)
def _sem_minio():
    with patch.object(move_svc, "_apagar_pins", new=AsyncMock()) as m:
        yield m


async def _mover(wf, nomes_no_destino=(), **kw):
    crud = _crud(wf, nomes_no_destino)
    resultado = await move_svc.move_workflow(crud, "wf-1", DESTINO, **kw)
    return resultado, crud


# ── Destino ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recusa_mover_para_o_proprio_workspace():
    """It would not be a no-op: it would create a version, turn off the schedule,
    delete the pins and deactivate the portal. The guard lives in the service so
    that any caller inherits it, not only the HTTP route."""
    from app.core.exceptions import WorkflowMoveTargetError

    wf = _workflow()
    crud = _crud(wf)

    with pytest.raises(WorkflowMoveTargetError):
        await move_svc.move_workflow(crud, "wf-1", ORIGEM)

    assert wf.workspace_id == ORIGEM
    assert wf.portal_access == "public"
    crud.create_version.assert_not_awaited()
    crud.db.commit.assert_not_awaited()


# ── Mutacoes ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workspace_muda_para_o_destino():
    wf = _workflow()
    resultado, _ = await _mover(wf)

    assert wf.workspace_id == DESTINO
    assert resultado["from_workspace_id"] == ORIGEM
    assert resultado["to_workspace_id"] == DESTINO


@pytest.mark.asyncio
async def test_id_hash_nao_muda():
    """Move preserva a identidade: URLs de webhook e links continuam validos."""
    wf = _workflow()
    resultado, _ = await _mover(wf)

    assert resultado["id"] == "wf-1"


@pytest.mark.asyncio
async def test_grupo_e_limpo():
    """WorkflowGroup tem workspace_id proprio — o grupo ficaria invisivel."""
    wf = _workflow()
    await _mover(wf)

    assert wf.group_id is None


@pytest.mark.asyncio
async def test_portal_volta_para_disabled():
    """portal_shared_with lists members of the old tenant and is not revalidated."""
    wf = _workflow()
    await _mover(wf)

    assert wf.portal_access == "disabled"
    assert wf.portal_shared_with is None


@pytest.mark.asyncio
async def test_pins_sao_limpos():
    """The s3_keys point to pin-cache/{ws_origem}/... — unreadable at the destination."""
    wf = _workflow(
        pinned_outputs={"n1": {"__pin_s3_key__": f"pin-cache/{ORIGEM}/run-1/n1_pin.json"}},
        pin_metadata={"n1": {"pinned_at": "2026-01-01T00:00:00"}},
    )
    await _mover(wf)

    assert wf.pinned_outputs is None
    assert wf.pin_metadata is None


@pytest.mark.asyncio
async def test_objetos_de_pin_sao_apagados_do_storage(_sem_minio):
    wf = _workflow(
        pinned_outputs={"n1": {"__pin_s3_key__": f"pin-cache/{ORIGEM}/run-1/n1_pin.json"}},
    )
    await _mover(wf)

    _sem_minio.assert_awaited_once()
    assert _sem_minio.await_args.args[0] == [f"pin-cache/{ORIGEM}/run-1/n1_pin.json"]


@pytest.mark.asyncio
async def test_autoria_e_carimbada():
    wf = _workflow()
    await _mover(wf, moved_by_id="usr-9")

    assert wf.updated_by_id == "usr-9"


# ── Agendamento ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agendamento_chega_desligado_na_definition():
    """The canvas reads the node's `active`; turning it off only in the database would leave the screen lying."""
    from app.core.utils.encryption import decrypt_workflow_connections

    wf = _workflow()
    await _mover(wf)

    gravada = decrypt_workflow_connections(wf.definition)
    node = next(n for n in gravada["nodes"] if n["name"] == "ScheduleTrigger")
    assert node["properties"]["active"] is False
    # The rest of the configuration survives — reactivating must not require rebuilding the node.
    assert node["properties"]["cron_expression"] == "0 6 * * *"
    assert node["properties"]["timezone"] == "America/Cuiaba"


@pytest.mark.asyncio
async def test_schedules_do_banco_sao_desativados():
    """The AsyncScheduler ticks over Schedule.active — without this UPDATE the
    workflow would keep triggering on its own, now in the new workspace."""
    wf = _workflow()
    _, crud = await _mover(wf)

    updates = [
        c.args[0] for c in crud.db.execute.await_args_list
        if "UPDATE schedules" in str(c.args[0])
    ]
    assert updates, "nenhum UPDATE em schedules foi emitido"
    params = updates[0].compile().params
    assert params["active"] is False
    assert params["workspace_id"] == DESTINO


@pytest.mark.asyncio
async def test_workflow_sem_schedule_nao_quebra():
    wf = _workflow(definition=_definition(com_schedule=False))
    resultado, _ = await _mover(wf)

    assert resultado["to_workspace_id"] == DESTINO


# ── Encryption regressions ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connection_string_e_gravada_cifrada():
    """REGRESSION: the definition arrives in plain text in the session.

    `get_accessible_workflow_with_role` calls `get_workflow_by_hash`, which does
    `decrypt_workflow_connections`, mutating the dict IN PLACE. Since the
    router's session and the service's are the same, the object move receives
    is already in plain text. This is the first path that rewrites the column —
    without going through `encrypt_workflow_connections`, the connectionString
    would go to the database in plain text.
    """
    wf = _workflow(definition=_definition(conn="postgresql://user:senha@host/db"))
    await _mover(wf)

    node = next(n for n in wf.definition["nodes"] if n["name"] == "WFS")
    assert node["properties"]["connectionString"].startswith("gAAAA")


@pytest.mark.asyncio
async def test_snapshot_de_versao_tambem_vai_cifrado():
    """workflow_versions is a persisted table like any other."""
    wf = _workflow(definition=_definition(conn="postgresql://user:senha@host/db"))
    _, crud = await _mover(wf)

    crud.create_version.assert_awaited_once()
    snapshot = crud.create_version.await_args.kwargs["definition"]
    node = next(n for n in snapshot["nodes"] if n["name"] == "WFS")
    assert node["properties"]["connectionString"].startswith("gAAAA")


@pytest.mark.asyncio
async def test_snapshot_registra_a_origem_e_o_destino():
    wf = _workflow()
    _, crud = await _mover(wf)

    nota = crud.create_version.await_args.kwargs["change_note"]
    assert ORIGEM in nota and DESTINO in nota


# ── Nome ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mantem_o_nome_quando_nao_ha_colisao():
    wf = _workflow()
    resultado, _ = await _mover(wf)

    assert resultado["name"] == "Edificações"
    assert resultado["renamed"] is False


@pytest.mark.asyncio
async def test_desambigua_quando_o_nome_ja_existe_no_destino():
    """There is a UniqueConstraint(name, workspace_id) and move must not fail."""
    wf = _workflow()
    resultado, _ = await _mover(wf, nomes_no_destino=["Edificações"])

    assert resultado["name"] == "Edificações (2)"
    assert resultado["renamed"] is True
    assert any(a["code"] == "name_conflict" for a in resultado["warnings"])


@pytest.mark.asyncio
async def test_desambigua_repetidamente():
    wf = _workflow()
    resultado, _ = await _mover(
        wf, nomes_no_destino=["Edificações", "Edificações (2)", "Edificações (3)"],
    )

    assert resultado["name"] == "Edificações (4)"


@pytest.mark.asyncio
async def test_nome_explicito_prevalece():
    wf = _workflow()
    resultado, _ = await _mover(wf, new_name="Cadastro 2026")

    assert resultado["name"] == "Cadastro 2026"
    assert wf.name == "Cadastro 2026"


@pytest.mark.asyncio
async def test_nome_em_branco_mantem_o_atual():
    wf = _workflow()
    resultado, _ = await _mover(wf, new_name="   ")

    assert resultado["name"] == "Edificações"


# ── Preview (dry_run) ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dry_run_nao_grava_nada():
    wf = _workflow()
    resultado, crud = await _mover(wf, dry_run=True)

    assert resultado["dry_run"] is True
    assert wf.workspace_id == ORIGEM          # intacto
    assert wf.portal_access == "public"
    assert wf.group_id == "grp-1"
    crud.db.commit.assert_not_awaited()
    crud.create_version.assert_not_awaited()


@pytest.mark.asyncio
async def test_dry_run_ainda_reporta_a_colisao_de_nome():
    wf = _workflow()
    resultado, _ = await _mover(wf, nomes_no_destino=["Edificações"], dry_run=True)

    assert resultado["name"] == "Edificações (2)"


# ── Race on the name ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_colisao_em_corrida_e_resolvida_com_sufixo_aleatorio():
    """Between the free-name check and the commit, another session may create a
    workflow with the same name at the destination. The constraint catches it,
    and the operation — which promised not to fail — tries again instead of
    returning 409."""
    from sqlalchemy.exc import IntegrityError

    wf = _workflow()
    crud = _crud(wf)
    erro = IntegrityError("stmt", {}, Exception("uq_workflow_name_workspace"))
    crud.db.commit = AsyncMock(side_effect=[erro, None])

    resultado = await move_svc.move_workflow(crud, "wf-1", DESTINO)

    assert resultado["renamed"] is True
    assert resultado["name"].startswith("Edificações (")
    assert resultado["name"] != "Edificações"
    crud.db.rollback.assert_awaited_once()
    assert wf.workspace_id == DESTINO


@pytest.mark.asyncio
async def test_retry_refaz_snapshot_e_desativacao_dos_schedules():
    """REGRESSION: `create_version` only flushes and the UPDATE on schedules is
    DML in the same transaction — the rollback undoes both. If the retry only
    renamed, the workflow would end up moved without a snapshot and with the
    schedule ACTIVE, pointing at the new workspace."""
    from sqlalchemy.exc import IntegrityError

    wf = _workflow()
    crud = _crud(wf)
    erro = IntegrityError("stmt", {}, Exception("uq_workflow_name_workspace"))
    crud.db.commit = AsyncMock(side_effect=[erro, None])

    await move_svc.move_workflow(crud, "wf-1", DESTINO)

    assert crud.create_version.await_count == 2
    updates = [
        c.args[0] for c in crud.db.execute.await_args_list
        if "UPDATE schedules" in str(c.args[0])
    ]
    assert len(updates) == 2


@pytest.mark.asyncio
async def test_integrity_error_de_outra_causa_propaga():
    """Only the name collision is retried; any other violation is a real bug and
    must not be masked by a rename."""
    from sqlalchemy.exc import IntegrityError

    crud = _crud(_workflow())
    erro = IntegrityError("stmt", {}, Exception("outra_constraint_qualquer"))
    crud.db.commit = AsyncMock(side_effect=erro)

    with pytest.raises(IntegrityError):
        await move_svc.move_workflow(crud, "wf-1", DESTINO)


@pytest.mark.asyncio
async def test_segunda_colisao_vira_conflito_legivel():
    """Unlikely with a random suffix, but 409 is better than 500."""
    from sqlalchemy.exc import IntegrityError
    from app.core.exceptions import WorkflowNameConflictError

    crud = _crud(_workflow())
    erro = IntegrityError("stmt", {}, Exception("uq_workflow_name_workspace"))
    crud.db.commit = AsyncMock(side_effect=[erro, erro])

    with pytest.raises(WorkflowNameConflictError):
        await move_svc.move_workflow(crud, "wf-1", DESTINO)


@pytest.mark.asyncio
async def test_segunda_violacao_de_OUTRA_causa_nao_vira_mensagem_de_nome():
    """The second level's label lied: ANY IntegrityError became
    "nao ha nome livre no destino" (no free name at the destination).

    The first `except` always filtered by the constraint name; the second
    filtered nothing. So a `version_number` collision on the second attempt —
    another constraint, another cause, another fix — reached the user as a name
    problem, sending them to investigate the wrong place.

    This became MORE necessary now that `create_version` reconverges on its own:
    a violation that gets this far is now genuinely unexpected, and labeling it
    as a name conflict would hide precisely the new case.
    """
    from sqlalchemy.exc import IntegrityError
    from app.core.exceptions import WorkflowNameConflictError

    crud = _crud(_workflow())
    colisao_de_nome = IntegrityError("stmt", {}, Exception("uq_workflow_name_workspace"))
    outra_causa = IntegrityError("stmt", {}, Exception("uq_workflow_version"))
    crud.db.commit = AsyncMock(side_effect=[colisao_de_nome, outra_causa])

    # `WorkflowNameConflictError` is NOT a subclass of `IntegrityError`: requiring
    # `IntegrityError` here is, at the same time, requiring that the wrong
    # conversion does not happen. Against today's code this `raises` fails,
    # because what surfaces is the name conflict.
    with pytest.raises(IntegrityError) as capturado:
        await move_svc.move_workflow(crud, "wf-1", DESTINO)

    assert not isinstance(capturado.value, WorkflowNameConflictError)
    assert "nome livre" not in str(capturado.value)


# ── Workflow inexistente ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workflow_inexistente():
    from app.core.exceptions import WorkflowNotFoundError

    crud = _crud(None)
    with pytest.raises(WorkflowNotFoundError):
        await move_svc.move_workflow(crud, "wf-x", DESTINO)


# ── Free-name helper ─────────────────────────────────────────────────────────

def test_nome_livre_devolve_a_base_quando_esta_livre():
    assert move_svc.nome_livre("X", set()) == "X"


def test_nome_livre_pula_os_ocupados():
    assert move_svc.nome_livre("X", {"X", "X (2)"}) == "X (3)"


def test_nome_livre_cai_no_sufixo_aleatorio_no_teto():
    """An ugly name is preferable to blowing up with 409 in an operation that promised not to fail."""
    ocupados = {"X"} | {f"X ({i})" for i in range(2, 100)}
    livre = move_svc.nome_livre("X", ocupados)

    assert livre.startswith("X (") and livre not in ocupados


def test_nome_livre_respeita_o_limite_da_coluna():
    """`workflows.name` is String(255). A suffix on a name already at the limit
    would overflow the column, and DataError is not IntegrityError — it would
    escape the retry as a 500."""
    longo = "N" * 255

    assert len(move_svc.nome_livre(longo, set())) <= 255
    assert len(move_svc.nome_livre(longo, {longo})) <= 255
    assert len(move_svc.nome_livre("N" * 300, set())) <= 255


def test_nome_livre_truncado_ainda_desambigua():
    longo = "N" * 255
    livre = move_svc.nome_livre(longo, {longo})

    assert livre != longo and livre.endswith("(2)")


# ── Pin artifacts ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_linhas_de_artefato_do_pin_sao_removidas():
    """They would remain as a dead download for the source, and
    `_upsert_pin_artifact` (which looks up by workflow_hash + node_id, without
    filtering by tenant) would reuse the row in a future pin at the destination,
    repointing it without changing the workspace_id."""
    wf = _workflow(
        pinned_outputs={"n1": {"__pin_s3_key__": f"pin-cache/{ORIGEM}/run-1/n1_pin.json"}},
    )
    _, crud = await _mover(wf)

    deletes = [
        c.args[0] for c in crud.db.execute.await_args_list
        if "DELETE FROM artifacts" in str(c.args[0])
    ]
    assert deletes, "as linhas de Artifact do pin nao foram removidas"
