"""
Testes de app.services.storage_purge_service.

Codigo destrutivo: remove objetos do MinIO e linhas do banco. O invariante mais
importante e o mesmo de artifact_cleanup.purge_expired_artifacts — se o S3
falhar por motivo diferente de "not found", a linha do banco PRECISA sobreviver,
senao o objeto vira orfao invisivel (ocupa disco e ninguem mais sabe que existe).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _db_com(artifacts=(), files=(), workflows=(), scope="all"):  # noqa: ARG001 — scope mantido por clareza nos testes
    """Sessao fake que despacha pelo SQL, nao pela ordem das chamadas.

    A sequencia de `execute` varia com o escopo e com o conteudo (o DELETE de
    portal_layer so acontece para artefato publicado), entao um `side_effect`
    posicional entrega o resultado errado assim que o caminho muda — foi o que
    fez a primeira versao destes testes falhar sem que houvesse bug no codigo.
    """
    db = MagicMock()
    art_res = MagicMock()
    art_res.scalars.return_value.all.return_value = list(artifacts)
    file_res = MagicMock()
    file_res.scalars.return_value.all.return_value = list(files)
    wf_res = MagicMock()
    wf_res.scalars.return_value = list(workflows)

    async def _execute(stmt, *a, **kw):
        sql = str(stmt).lower()
        if sql.lstrip().startswith("select"):
            if "workspace_files" in sql:
                return file_res
            if "from workflows" in sql:
                return wf_res
            if "artifacts" in sql:
                return art_res
        return MagicMock()

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    return db


def _artifact(**kw):
    base = dict(id=1, s3_key="artifacts/ws-1/run/a.geojson", size_bytes=100,
                is_published=False, workflow_hash=None, output_key="out")
    base.update(kw)
    return MagicMock(**base)


def _file(**kw):
    base = dict(id=1, s3_key="drive/ws-1/x.csv", size=50)
    base.update(kw)
    return MagicMock(**base)


# ── Caminho feliz ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_purga_artefatos_e_drive_somando_bytes(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artifact(size_bytes=100), _artifact(id=2, size_bytes=250)],
                 files=[_file(size=50)])

    r = await mod.purge_workspace_storage(db, "ws-1", scope="all")

    assert r["artifacts"] == 2 and r["artifact_bytes"] == 350
    assert r["drive_files"] == 1 and r["drive_bytes"] == 50
    assert r["skipped_s3_errors"] == 0
    assert mock_del.call_count == 3
    db.commit.assert_awaited()


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_purga_zera_refs_de_pin_dos_workflows(mock_del):
    """Os objetos do pin-cache caem com os demais artefatos; a ref no workflow
    precisa ser ZERADA junto — pendurada, ela era 404 permanente em toda run
    (o auto-pin so dispara com a ref vazia). pin_metadata fica: a intencao de
    pin sobrevive e a proxima execucao regrava o cache."""
    from app.services import storage_purge_service as mod

    wf = MagicMock()
    wf.pinned_outputs = {
        "n1": {"__pin_s3_key__": "pin-cache/ws-1/t1/n1_pin.parquet",
               "__pin_format__": "parquet"},
        "n2": {},          # pin aguardando regravacao — ja esta como deve ficar
    }
    wf_sem_pins = MagicMock()
    wf_sem_pins.pinned_outputs = None
    pin_art = _artifact(id=7, s3_key="pin-cache/ws-1/t1/n1_pin.parquet")
    db = _db_com(artifacts=[pin_art], workflows=[wf, wf_sem_pins])

    with patch("sqlalchemy.orm.attributes.flag_modified") as mock_flag:
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["pins_resetados"] == 1
    assert wf.pinned_outputs == {"n1": {}, "n2": {}}
    assert wf_sem_pins.pinned_outputs is None
    mock_flag.assert_called_once_with(wf, "pinned_outputs")
    mock_del.assert_called()          # objeto do pin saiu do MinIO


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_scope_drive_nao_toca_artefatos(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artifact()], files=[_file()], scope="drive")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="drive")

    assert r["artifacts"] == 0
    assert r["drive_files"] == 1
    mock_del.assert_called_once_with("drive/ws-1/x.csv", allow_missing=True)


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_scope_artifacts_nao_toca_drive(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artifact()], files=[_file()], scope="artifacts")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 1
    assert r["drive_files"] == 0


# ── Invariantes de seguranca ─────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.core.storage.delete_strict", side_effect=Exception("MinIO down"))
async def test_falha_no_s3_preserva_a_linha_no_banco(mock_del):
    """Nunca apagar do banco antes de confirmar a remocao no storage."""
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artifact()], files=[], scope="artifacts")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 0, "artefato nao pode contar como removido"
    assert r["skipped_s3_errors"] == 1


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_s3_key_local_do_executor_nao_vai_ao_minio(mock_del):
    """Fallback local (s3_key comecando com '/') nao existe no MinIO."""
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artifact(s3_key="/data/artifacts/ws/run/a.json")], files=[], scope="artifacts")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    mock_del.assert_not_called()
    assert r["artifacts"] == 1, "a linha orfa ainda deve sair do banco"


@pytest.mark.asyncio
async def test_scope_invalido_e_recusado():
    from app.services import storage_purge_service as mod

    with pytest.raises(ValueError):
        await mod.purge_workspace_storage(MagicMock(), "ws-1", scope="tudo")


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_artefato_publicado_remove_a_camada_do_portal(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artifact(is_published=True, workflow_hash="wf-1")], files=[], scope="artifacts")
    await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    # SELECT artifacts, DELETE portal_layer, DELETE artifacts
    assert db.execute.await_count >= 3


# ── Autorizacao dos endpoints (/admin/storage/.../purge) ─────────────────────
#
# A purga apaga dados de QUALQUER workspace da plataforma, inclusive de outros
# usuarios. A garantia vem do router (`dependencies=[Depends(require_admin)]`),
# nao de codigo no handler — e por isso e fragil: basta alguem mover o endpoint
# para outro router, ou criar um router novo sem a dependency, para abrir tudo.
# Estes testes falham no instante em que isso acontecer.

@pytest.mark.asyncio
async def test_purge_negado_para_usuario_comum(client):
    """client autentica com role='user' (ver conftest)."""
    resp = await client.post(
        "/admin/storage/workspaces/ws-test-001/purge",
        json={"scope": "all", "confirm": "ws-test-001"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_purge_permitido_para_admin(client, mock_current_user):
    from app.api.dependencies import get_db
    from app.main import app

    mock_current_user.role = "admin"
    mock_current_user.username = "admin-test"

    async def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with patch(
            "app.services.storage_purge_service.purge_workspace_storage",
            new=AsyncMock(return_value={
                "workspace_id": "ws-test-001", "scope": "all",
                "artifacts": 2, "artifact_bytes": 10,
                "drive_files": 1, "drive_bytes": 5, "skipped_s3_errors": 0,
            }),
        ):
            resp = await client.post(
                "/admin/storage/workspaces/ws-test-001/purge",
                json={"scope": "all", "confirm": "ws-test-001"},
            )
        assert resp.status_code == 200
        assert resp.json()["artifacts"] == 2
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_admin_com_confirm_divergente_recebe_400(client, mock_current_user):
    """Guarda contra clique na linha errada: o corpo tem de repetir o workspace_id."""
    from app.api.dependencies import get_db
    from app.main import app

    mock_current_user.role = "admin"
    mock_current_user.username = "admin-test"

    async def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with patch(
            "app.services.storage_purge_service.purge_workspace_storage",
            new=AsyncMock(),
        ) as purge_mock:
            resp = await client.post(
                "/admin/storage/workspaces/ws-alvo/purge",
                json={"scope": "all", "confirm": "ws-vizinho"},
            )
        assert resp.status_code == 400
        purge_mock.assert_not_awaited()
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Conteudo que vive no disco do executor ────────────────────────────────────
#
# A purga nao conhecia `content_location`. Um artefato local tem `s3_key` NULL:
# o `if` do MinIO nao entrava, o `continue` nao disparava, e a linha era apagada
# SEM ordenar a remocao — arquivo retido e invisivel no disco do usuario, que e
# o pior desfecho possivel para dado pessoal. Estes testes travam as duas
# politicas, que sao deliberadamente DIFERENTES entre artefato e Drive.


def _artefato_local(**kw):
    base = dict(id=10, id_hash="art-local", s3_key=None, size_bytes=700,
                is_published=False, workflow_hash=None, output_key="out",
                content_location="executor", executor_id="exec-1",
                local_path="ws-1/run/a.geojson")
    base.update(kw)
    return MagicMock(**base)


@pytest.mark.asyncio
async def test_artefato_local_so_e_apagado_depois_da_ordem_entregue():
    """Executor ONLINE: ordem entregue, entao a linha pode cair."""
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artefato_local()])

    async def _entrega_tudo(por_executor):
        return [i["_id"] for itens in por_executor.values() for i in itens]

    with patch("app.core.artifact_cleanup._ordenar_remocao_local", new=_entrega_tudo):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 1
    assert r["artifact_bytes"] == 700
    assert r["pending_executor"] == 0


@pytest.mark.asyncio
async def test_executor_OFFLINE_mantem_a_linha_em_vez_de_apagar():
    """A regressao central: sem entrega, a linha FICA e a proxima passada tenta de novo."""
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artefato_local()])

    async def _nao_entrega(_por_executor):
        return []

    with patch("app.core.artifact_cleanup._ordenar_remocao_local", new=_nao_entrega):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 0, "linha nao pode ser contada como removida"
    assert r["pending_executor"] == 1

    # E, sobretudo, nenhum DELETE de artifacts pode ter sido emitido.
    deletes = [
        str(c.args[0]).lower() for c in db.execute.await_args_list
        if str(c.args[0]).lower().lstrip().startswith("delete")
        and "artifacts" in str(c.args[0]).lower()
    ]
    assert deletes == [], f"DELETE emitido sem ordem entregue: {deletes}"


@pytest.mark.asyncio
async def test_artefato_local_sem_rastro_e_preservado():
    """Sem executor_id/local_path nao ha para quem mandar — manter o registro."""
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artefato_local(executor_id=None)])

    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 0
    assert r["skipped_sem_rastro"] == 1


@pytest.mark.asyncio
async def test_artefato_local_publicado_remove_a_portal_layer_junto():
    from app.services import storage_purge_service as mod

    db = _db_com(artifacts=[_artefato_local(is_published=True, workflow_hash="wf-1")])

    async def _entrega_tudo(por_executor):
        return [i["_id"] for itens in por_executor.values() for i in itens]

    with patch("app.core.artifact_cleanup._ordenar_remocao_local", new=_entrega_tudo):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 1
    sqls = [str(c.args[0]).lower() for c in db.execute.await_args_list]
    assert any(s.lstrip().startswith("delete") and "portal_layer" in s for s in sqls)


@pytest.mark.asyncio
async def test_drive_catalogado_e_PRESERVADO_nao_apagado():
    """Politica oposta a do artefato, e deliberada.

    Um arquivo catalogado e do proprio usuario, na pasta que ele escolheu
    sincronizar; a plataforma nunca teve os bytes e ele nao ocupa armazenamento
    dela. `drive_service._recusar_se_catalogado` recusa apaga-lo na exclusao
    avulsa — a purga apagava a ficha em silencio, contradizendo aquela politica.

    Tambem nao adianta mandar `purge_artifacts`: o executor resolve o caminho
    sob `artifacts_root()`, entao a ordem nao acharia o arquivo de Drive e ainda
    assim contaria como entregue.
    """
    from app.services import storage_purge_service as mod

    db = _db_com(files=[_file(content_location="executor", s3_key=None, size=0)])

    r = await mod.purge_workspace_storage(db, "ws-1", scope="drive")

    assert r["drive_files"] == 0
    assert r["skipped_catalogados"] == 1
    deletes = [
        str(c.args[0]).lower() for c in db.execute.await_args_list
        if str(c.args[0]).lower().lstrip().startswith("delete")
    ]
    assert deletes == [], f"arquivo catalogado nao pode ser apagado: {deletes}"


@pytest.mark.asyncio
async def test_drive_normal_continua_sendo_purgado():
    """A guarda acima nao pode paralisar a purga do Drive que vive no MinIO."""
    from app.services import storage_purge_service as mod

    db = _db_com(files=[_file(content_location="minio", size=50)])

    with patch("app.core.storage.delete_strict"):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="drive")

    assert r["drive_files"] == 1 and r["drive_bytes"] == 50
    assert r["skipped_catalogados"] == 0
