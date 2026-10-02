# tests/unit/test_workflow_move.py
"""Movimentacao de workflow entre workspaces.

O contrato do recurso e que a operacao NAO falha por dependencia quebrada: o que
deixa de funcionar no destino sai como aviso. O que e consequencia
deterministica da troca de tenant (agendamento desligado, portal desativado,
grupo e pins limpos) e aplicado sem perguntar, pelo mesmo racional ja escrito em
`duplicate_workflow`.

O teste mais importante daqui e `test_connection_string_e_gravada_cifrada`: a
dependency da rota descriptografa a definition no MESMO objeto da sessao, e o
move e o primeiro caminho que reescreve essa coluna.
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
    m.name = kw.get("name", "Edificações")   # `name` e reservado no construtor
    return m


def _crud(wf, nomes_no_destino=()):
    """CRUD dublado; `db.execute` devolve os nomes ja existentes no destino."""
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
    """O relatorio tem banco proprio; aqui o alvo sao as mutacoes."""
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
    """Nao seria um no-op: geraria versao, desligaria o agendamento, apagaria os
    pins e desativaria o portal. A guarda fica no service para que qualquer
    chamador a herde, e nao so a rota HTTP."""
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
    """portal_shared_with lista membros do tenant antigo e nao e revalidado."""
    wf = _workflow()
    await _mover(wf)

    assert wf.portal_access == "disabled"
    assert wf.portal_shared_with is None


@pytest.mark.asyncio
async def test_pins_sao_limpos():
    """As s3_keys apontam para pin-cache/{ws_origem}/... — ilegiveis no destino."""
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
    """O canvas le o `active` do no; desligar so no banco deixaria a tela mentindo."""
    from app.core.utils.encryption import decrypt_workflow_connections

    wf = _workflow()
    await _mover(wf)

    gravada = decrypt_workflow_connections(wf.definition)
    node = next(n for n in gravada["nodes"] if n["name"] == "ScheduleTrigger")
    assert node["properties"]["active"] is False
    # O resto da configuracao sobrevive — reativar nao deve exigir remontar o no.
    assert node["properties"]["cron_expression"] == "0 6 * * *"
    assert node["properties"]["timezone"] == "America/Cuiaba"


@pytest.mark.asyncio
async def test_schedules_do_banco_sao_desativados():
    """O AsyncScheduler tica sobre Schedule.active — sem este UPDATE o workflow
    continuaria disparando sozinho, agora no workspace novo."""
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


# ── Regressoes de criptografia ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connection_string_e_gravada_cifrada():
    """REGRESSAO: a definition chega em claro na sessao.

    `get_accessible_workflow_with_role` chama `get_workflow_by_hash`, que faz
    `decrypt_workflow_connections` mutando o dict IN PLACE. Como a sessao do
    router e a do service sao a mesma, o objeto que o move recebe ja esta em
    claro. Este e o primeiro caminho que reescreve a coluna — sem passar por
    `encrypt_workflow_connections`, a connectionString iria em texto puro para o
    banco.
    """
    wf = _workflow(definition=_definition(conn="postgresql://user:senha@host/db"))
    await _mover(wf)

    node = next(n for n in wf.definition["nodes"] if n["name"] == "WFS")
    assert node["properties"]["connectionString"].startswith("gAAAA")


@pytest.mark.asyncio
async def test_snapshot_de_versao_tambem_vai_cifrado():
    """workflow_versions e tabela persistida como outra qualquer."""
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
    """Ha UniqueConstraint(name, workspace_id) e o move nao pode falhar."""
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


# ── Corrida no nome ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_colisao_em_corrida_e_resolvida_com_sufixo_aleatorio():
    """Entre a checagem de nomes livres e o commit, outra sessao pode criar um
    workflow homonimo no destino. A constraint pega, e a operacao — que prometeu
    nao falhar — tenta de novo em vez de devolver 409."""
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
    """REGRESSAO: `create_version` so faz flush e o UPDATE em schedules e DML na
    mesma transacao — o rollback desfaz os dois. Se o retry so renomeasse, o
    workflow acabaria movido sem snapshot e com o agendamento ATIVO apontando
    para o novo workspace."""
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
    """So a colisao de nome tem retry; qualquer outra violacao e um bug real e
    nao pode ser mascarada por um rename."""
    from sqlalchemy.exc import IntegrityError

    crud = _crud(_workflow())
    erro = IntegrityError("stmt", {}, Exception("outra_constraint_qualquer"))
    crud.db.commit = AsyncMock(side_effect=erro)

    with pytest.raises(IntegrityError):
        await move_svc.move_workflow(crud, "wf-1", DESTINO)


@pytest.mark.asyncio
async def test_segunda_colisao_vira_conflito_legivel():
    """Improvavel com sufixo aleatorio, mas 409 e melhor do que 500."""
    from sqlalchemy.exc import IntegrityError
    from app.core.exceptions import WorkflowNameConflictError

    crud = _crud(_workflow())
    erro = IntegrityError("stmt", {}, Exception("uq_workflow_name_workspace"))
    crud.db.commit = AsyncMock(side_effect=[erro, erro])

    with pytest.raises(WorkflowNameConflictError):
        await move_svc.move_workflow(crud, "wf-1", DESTINO)


@pytest.mark.asyncio
async def test_segunda_violacao_de_OUTRA_causa_nao_vira_mensagem_de_nome():
    """O rotulo do segundo nivel mentia: QUALQUER IntegrityError virava
    "nao ha nome livre no destino".

    O primeiro `except` sempre filtrou pelo nome da constraint; o segundo nao
    filtrava nada. Entao uma colisao de `version_number` na segunda tentativa —
    outra constraint, outra causa, outro conserto — chegava ao usuario como
    problema de nome, mandando investigar o lugar errado.

    Isto ficou MAIS necessario agora que `create_version` reconverge sozinho:
    uma violacao que chegue ate aqui passou a ser genuinamente inesperada, e
    rotula-la como conflito de nome esconderia justamente o caso novo.
    """
    from sqlalchemy.exc import IntegrityError
    from app.core.exceptions import WorkflowNameConflictError

    crud = _crud(_workflow())
    colisao_de_nome = IntegrityError("stmt", {}, Exception("uq_workflow_name_workspace"))
    outra_causa = IntegrityError("stmt", {}, Exception("uq_workflow_version"))
    crud.db.commit = AsyncMock(side_effect=[colisao_de_nome, outra_causa])

    # `WorkflowNameConflictError` NAO e subclasse de `IntegrityError`: exigir
    # `IntegrityError` aqui e, ao mesmo tempo, exigir que a conversao errada nao
    # aconteca. Contra o codigo de hoje este `raises` falha, porque o que sobe e
    # o conflito de nome.
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


# ── Helper de nome livre ─────────────────────────────────────────────────────

def test_nome_livre_devolve_a_base_quando_esta_livre():
    assert move_svc.nome_livre("X", set()) == "X"


def test_nome_livre_pula_os_ocupados():
    assert move_svc.nome_livre("X", {"X", "X (2)"}) == "X (3)"


def test_nome_livre_cai_no_sufixo_aleatorio_no_teto():
    """Preferivel um nome feio a estourar 409 numa operacao que prometeu nao falhar."""
    ocupados = {"X"} | {f"X ({i})" for i in range(2, 100)}
    livre = move_svc.nome_livre("X", ocupados)

    assert livre.startswith("X (") and livre not in ocupados


def test_nome_livre_respeita_o_limite_da_coluna():
    """`workflows.name` e String(255). Um sufixo sobre um nome ja no limite
    estouraria a coluna, e DataError nao e IntegrityError — escaparia do retry
    como 500."""
    longo = "N" * 255

    assert len(move_svc.nome_livre(longo, set())) <= 255
    assert len(move_svc.nome_livre(longo, {longo})) <= 255
    assert len(move_svc.nome_livre("N" * 300, set())) <= 255


def test_nome_livre_truncado_ainda_desambigua():
    longo = "N" * 255
    livre = move_svc.nome_livre(longo, {longo})

    assert livre != longo and livre.endswith("(2)")


# ── Artefatos de pin ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_linhas_de_artefato_do_pin_sao_removidas():
    """Ficariam como download morto para a origem, e `_upsert_pin_artifact`
    (que busca por workflow_hash + node_id, sem filtrar tenant) reaproveitaria a
    linha num pin futuro no destino, repontando-a sem trocar o workspace_id."""
    wf = _workflow(
        pinned_outputs={"n1": {"__pin_s3_key__": f"pin-cache/{ORIGEM}/run-1/n1_pin.json"}},
    )
    _, crud = await _mover(wf)

    deletes = [
        c.args[0] for c in crud.db.execute.await_args_list
        if "DELETE FROM artifacts" in str(c.args[0])
    ]
    assert deletes, "as linhas de Artifact do pin nao foram removidas"
