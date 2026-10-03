# tests/unit/test_exclusao_conteudo_local.py
"""
Manual deletion from the web app when the content lives on an executor's disk.

Reading (download 409) and automatic retention were already covered. The MANUAL
deletion path was not, and it had two defects of opposite natures:

  ARTIFACT   `delete_artifact` skipped MinIO due to a null `s3_key` and deleted
             the row anyway. The file was left orphaned on the user's disk and
             the server lost its only record of it — for personal data, worse
             than not deleting, because nobody can even know there is something
             to delete.

  DRIVE      `delete_file` called `delete_strict_async(None)`. boto3 validates
             `Key=None` on the CLIENT and raises ParamValidationError, which is
             not a ClientError, escapes the `except` and became a 500 — the file
             could not be deleted at all.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ConteudoNoExecutorError
from app.services import drive_service


# ── Drive: registro catalogado e recusado ────────────────────────────────────

def _arquivo(**kw):
    base = dict(id_hash="h1", s3_key=None, content_location="executor",
                original_name="cadastro.gpkg", extension="gpkg", size=10,
                workspace_id="ws1")
    base.update(kw)
    return SimpleNamespace(**base)


def test_catalogado_e_recusado_com_saida_explicada():
    with pytest.raises(ConteudoNoExecutorError) as e:
        drive_service._recusar_se_catalogado(_arquivo())

    # The message has to say WHAT TO DO. "Nao permitido" (not allowed) alone leaves
    # the person with no action in the only place they are looking.
    msg = str(e.value).lower()
    assert "pasta sincronizada" in msg or "geosync" in msg


def test_recusa_e_409_e_nao_400():
    """Nothing is wrong with the request — the problem is the resource's STATE."""
    assert ConteudoNoExecutorError.status_code == 409


def test_arquivo_normal_passa():
    drive_service._recusar_se_catalogado(
        _arquivo(content_location="minio", s3_key="drive/ws1/x.gpkg")
    )


def test_ausencia_do_campo_nao_bloqueia():
    """An old object without `content_location` must not become a rejection."""
    drive_service._recusar_se_catalogado(SimpleNamespace(id_hash="h", s3_key="k"))


# ── Artifact: the row only goes away once the order was delivered ────────────
#
# The rule lives in `remocao_de_artefatos.remover_artefatos`, the same one used
# by the five deleting paths; the deletion routes call it with
# `agendar_pendentes`.

def _artefato(id_=1, **kw):
    base = dict(id=id_, id_hash=f"a{id_}", workspace_id="ws1", content_location="executor",
                executor_id="exec-1", local_path="ws/task/x.gpkg",
                expires_at=None, is_pinned=False, s3_key=None,
                is_published=False, workflow_hash=None, output_key="saida", size_bytes=0)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def entrega(monkeypatch):
    """Controla o que `_ordenar_remocao_local` considera entregue."""
    def instalar(ids_entregues):
        async def _fake(por_executor):
            return list(ids_entregues)
        import app.core.artifact_cleanup as ac
        monkeypatch.setattr(ac, "_ordenar_remocao_local", _fake)
    return instalar


async def _remover(itens):
    from app.services.remocao_de_artefatos import remover_artefatos

    return await remover_artefatos(MagicMock(execute=AsyncMock()), itens, agendar_pendentes=True)


@pytest.mark.asyncio
async def test_entregue_libera_a_linha(entrega):
    entrega([1])
    remocao = await _remover([_artefato(1)])

    assert [x.id for x in remocao.apagados] == [1]
    assert remocao.pendentes_local == []


@pytest.mark.asyncio
async def test_executor_OFFLINE_marca_para_purga_em_vez_de_apagar(entrega):
    # The bug's case: with no delivery, the row stayed and the file vanished from the system.
    entrega([])
    a = _artefato(1)
    remocao = await _remover([a])

    assert remocao.apagados == []
    assert [x.id for x in remocao.pendentes_local] == [1]
    assert a.expires_at is not None, "sem expires_at a retencao nunca pega este artefato"


@pytest.mark.asyncio
async def test_artefato_FIXADO_perde_o_pin_ao_ser_agendado(entrega):
    """`purge_expired_artifacts` ignores `is_pinned` — without clearing it, the
    artifact would be marked as expired and never purged: it disappears from the
    UI as "removing" and stays on disk forever."""
    entrega([])
    a = _artefato(1, is_pinned=True)
    await _remover([a])

    assert a.is_pinned is False


@pytest.mark.asyncio
async def test_sem_executor_id_a_linha_e_PRESERVADA(entrega):
    """Without a destination there is no one to send to. Deleting the row would
    leave the file orphaned and invisible — same decision as retention and purge."""
    entrega([])
    a = _artefato(1, executor_id=None)
    remocao = await _remover([a])

    assert remocao.apagados == []
    assert [x.id for x in remocao.sem_rastro] == [1]
    assert a.expires_at is not None


@pytest.mark.asyncio
async def test_lote_parcial_separa_entregues_de_pendentes(entrega):
    entrega([1, 3])
    remocao = await _remover([_artefato(1), _artefato(2), _artefato(3)])

    assert sorted(x.id for x in remocao.apagados) == [1, 3]
    assert [x.id for x in remocao.pendentes_local] == [2]


# ── The batch: commit even with nothing deleted, pending is not failure ──────

async def _excluir_em_lote(monkeypatch, itens):
    from app.api.routers import artifacts_router as R
    from app.core.authorization import workflow_access

    # Where `exigir_papel_no_workspace` looks up the role (the comparison stays real).
    monkeypatch.setattr(workflow_access, "get_workspace_member_role", AsyncMock(return_value="owner"))
    selecionados = MagicMock()
    selecionados.scalars.return_value.all.return_value = list(itens)
    db = MagicMock(execute=AsyncMock(return_value=selecionados), commit=AsyncMock())
    pedido = SimpleNamespace(json=AsyncMock(return_value={"id_hashes": [a.id_hash for a in itens]}))
    resposta = await R.batch_delete_artifacts(
        pedido, db=db, current_user=SimpleNamespace(id_hash="u-1"), workspace_ids=["ws1"],
    )
    return resposta, db


@pytest.mark.asyncio
async def test_commit_do_batch_NAO_depende_de_ter_apagado_algo(entrega, monkeypatch):
    """Regression: the commit was conditioned on what was deleted.

    With ALL artifacts local and the executor offline — the common case of this
    path — nothing is deleted, and the `expires_at` just set on the ORM objects
    died in the session rollback. The API answered "remocao pendente" (removal
    pending) and nothing was scheduled: the artifacts would never be purged and
    the file would stay on disk forever.
    """
    entrega([])
    a = _artefato(1)
    _, db = await _excluir_em_lote(monkeypatch, [a])

    db.commit.assert_awaited_once()
    assert a.expires_at is not None


@pytest.mark.asyncio
async def test_pendente_nao_e_contado_como_falha(entrega, monkeypatch):
    """`skipped` means "failed, try again"; pending will happen on its own.
    Counting it in both would make the UI add up the same artifact twice."""
    entrega([])
    resposta, _ = await _excluir_em_lote(monkeypatch, [_artefato(1), _artefato(2, executor_id=None)])

    assert resposta == {"deleted": 0, "skipped": 0, "pendentes_no_executor": 2}
