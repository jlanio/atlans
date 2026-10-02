# tests/unit/test_workspace_delete_cascade.py
"""Nenhum workflow sobrevive ativo ao delete do seu workspace.

Regressao: o DELETE do workspace nao tocava em workflows nem schedules. O
workflow sumia da UI (listagem e por workspace acessivel) mas o AsyncScheduler
continuava disparando — o tick filtra apenas por Schedule.active.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.workflow_service import (
    restore_workspace_workflows,
    soft_delete_workspace_workflows,
)

# Timestamp compartilhado entre Workspace.deleted_at e os workflows da cascata.
_DELETED_AT = datetime(2026, 8, 3, 10, 5, 44)


def _rows_result(rows: list[tuple]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def _update_result(rowcount: int = 0) -> MagicMock:
    result = MagicMock()
    result.rowcount = rowcount
    return result


async def test_workspace_sem_workflows_nao_dispara_updates():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_rows_result([]))

    out = await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert out == {"workflows": 0, "schedules": 0}
    assert db.execute.await_count == 1  # apenas o SELECT


async def test_soft_deleta_pendentes_e_desativa_schedules():
    ativo_a, ativo_b, ja_deletado = str(uuid4()), str(uuid4()), str(uuid4())
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([
            (ativo_a, None),
            (ativo_b, None),
            (ja_deletado, datetime(2026, 7, 27, 14, 20)),
        ]),
        _update_result(),   # UPDATE workflows
        _update_result(2),  # UPDATE schedules
    ])

    with patch(
        "app.services.workflow_service._cleanup_change_detector_keys",
        new=AsyncMock(return_value=0),
    ) as cleanup:
        out = await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert out == {"workflows": 2, "schedules": 2}

    stmts = [call.args[0] for call in db.execute.await_args_list]
    wf_update, sched_update = stmts[1], stmts[2]

    assert wf_update.table.name == "workflows"
    wf_params = wf_update.compile().params
    assert wf_params["flag_ative"] is False
    # Mesmo timestamp do workspace — e a marca que o restore usa
    assert wf_params["deleted_at"] == _DELETED_AT

    assert sched_update.table.name == "schedules"
    assert sched_update.compile().params["active"] is False

    # ChangeDetector so e limpo para quem foi soft-deletado agora
    assert {c.args[0] for c in cleanup.await_args_list} == {ativo_a, ativo_b}


async def test_desativa_schedule_de_workflow_ja_soft_deletado():
    """Schedule ativo de workflow ja deletado tambem cai — o cascade cobre todos."""
    wf_id = str(uuid4())
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([(wf_id, datetime(2026, 4, 9, 13, 43))]),
        _update_result(1),  # UPDATE schedules — sem UPDATE de workflows
    ])

    with patch(
        "app.services.workflow_service._cleanup_change_detector_keys",
        new=AsyncMock(return_value=0),
    ) as cleanup:
        out = await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert out == {"workflows": 0, "schedules": 1}
    assert db.execute.await_count == 2
    cleanup.assert_not_awaited()


async def test_nao_commita_por_conta_propria():
    """Quem commita e o delete_workspace.

    Sem garantia de atomicidade end-to-end, porem: o router chama
    `schedule_workspace_data_expiry` logo depois, e ela commita por dentro. Por
    isso o router marca Workspace.deleted_at ANTES desta funcao — ver
    test_delete_marca_workspace_antes_do_helper_que_commita.
    """
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([(str(uuid4()), None)]),
        _update_result(),
        _update_result(0),
    ])

    with patch(
        "app.services.workflow_service._cleanup_change_detector_keys",
        new=AsyncMock(return_value=0),
    ):
        await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    db.commit.assert_not_awaited()


async def test_delete_marca_workspace_antes_do_helper_que_commita(client, mock_current_user):
    """A ordem no router e o que garante a atomicidade — nao a ausencia de commit.

    `schedule_workspace_data_expiry` commita por dentro (via
    purge_workspace_storage). Se o router marcasse Workspace.deleted_at depois
    dela, esse commit confirmaria os workflows ja soft-deletados com o workspace
    ainda vivo. Esse estado nao aparece na lixeira (o filtro e
    `deleted_at IS NOT NULL`), entao nem o dono nem o admin o desfazem pela UI.
    """
    from app.api.dependencies import get_db
    from app.main import app

    ws = MagicMock()
    ws.id_hash = "ws-test-001"
    ws.is_default = False
    ws.owner_id = mock_current_user.id_hash
    ws.deleted_at = None

    db = MagicMock()
    db.commit = AsyncMock()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = ws
    db.execute = AsyncMock(return_value=select_result)

    async def _fake_db():
        yield db

    app.dependency_overrides[get_db] = _fake_db

    visto: dict = {}

    async def _fake_cascade(_db, _ws_id, when):
        visto["ws_deleted_at_no_cascade"] = ws.deleted_at
        return {"workflows": 1, "schedules": 1}

    async def _fake_expiry(_db, _ws_id):
        # Ponto do commit interno: o que estiver sujo aqui é confirmado junto.
        visto["ws_deleted_at_no_commit_interno"] = ws.deleted_at
        return {"artifacts": 0, "drive_files": 0}

    try:
        with patch(
            "app.services.workflow_service.soft_delete_workspace_workflows", new=_fake_cascade,
        ), patch(
            "app.services.storage_purge_service.schedule_workspace_data_expiry", new=_fake_expiry,
        ):
            resp = await client.delete("/workspaces/ws-test-001")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 204
    assert visto["ws_deleted_at_no_cascade"] is not None
    assert visto["ws_deleted_at_no_commit_interno"] is not None


# ── Restore ───────────────────────────────────────────────────────────────────

async def test_restore_devolve_apenas_workflows_do_mesmo_delete():
    """Workflow deletado individualmente antes nao volta junto com o workspace."""
    ws_id = str(uuid4())
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_update_result(2))

    restored = await restore_workspace_workflows(db, ws_id, _DELETED_AT)

    assert restored == 2
    stmt = db.execute.await_args.args[0]
    assert stmt.table.name == "workflows"

    params = stmt.compile().params
    assert params["deleted_at"] is None
    # O WHERE casa workspace + o timestamp exato do delete em cascata
    assert _DELETED_AT in params.values()
    assert ws_id in params.values()

    db.commit.assert_not_awaited()


async def test_restore_nao_reativa_workflow():
    """Regressao: reativar em bloco ressuscitava o que o dono tinha desligado.

    O cascade zera `flag_ative` de todos, entao no restore nao ha como saber
    quem ja estava desativado de proposito. Devolver desativado e a unica
    leitura honesta — e `flag_ative` segue sendo a trava que portal_router,
    webhook_router e schedule_service checam.
    """
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_update_result(1))

    await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    params = db.execute.await_args.args[0].compile().params
    assert "flag_ative" not in params


async def test_restore_nao_reativa_schedules():
    """Religar cron sozinho e o lado perigoso — restore mexe so em workflows."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_update_result(1))

    await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    # Contar chamadas nao serve de prova aqui: o restore tambem LE os nomes que
    # voltam, para desviar de nome reocupado enquanto o workspace esteve na
    # lixeira (o indice de nome e parcial em `deleted_at IS NULL`). Ler nao e
    # reativar — o que nao pode acontecer e uma escrita em `schedules`.
    emitidas = [str(c.args[0]) for c in db.execute.await_args_list]
    assert not any("schedules" in sql for sql in emitidas), emitidas
    assert db.execute.await_args.args[0].table.name == "workflows"


async def test_restore_desvia_de_nome_reocupado():
    """O nome de quem esta na lixeira pode ter sido tomado enquanto isso.

    O indice de nome e PARCIAL (`deleted_at IS NULL`), entao soft-deletar libera
    o nome. Se alguem criar um workflow com o nome de um dos que cairam, o
    UPDATE em lote do restore falharia INTEIRO por violacao de unicidade e
    derrubaria junto o restore do workspace. Renomear quem volta devolve o
    workspace; recusar nao devolveria nada.
    """
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([("wf-a", "Edificações")]),   # os que voltam
        _rows_result([("Edificações",)]),          # nomes ja ocupados por vivos
        _update_result(1),                         # UPDATE do rename
        _update_result(1),                         # UPDATE que zera deleted_at
    ])

    devolvidos = await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert devolvidos == 1
    rename = db.execute.await_args_list[2].args[0]
    assert rename.compile().params["name"] == "Edificações (2)"


async def test_restore_preserva_o_nome_quando_ninguem_o_tomou():
    """Caso normal: sem colisao, o workflow volta com o nome que tinha."""
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([("wf-a", "Edificações")]),   # os que voltam
        _rows_result([]),                          # nada ocupado
        _update_result(1),                         # UPDATE que zera deleted_at
    ])

    devolvidos = await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert devolvidos == 1
    # Sem rename: a unica escrita e a que zera `deleted_at`.
    assert db.execute.await_count == 3
    assert "name" not in db.execute.await_args.args[0].compile().params
