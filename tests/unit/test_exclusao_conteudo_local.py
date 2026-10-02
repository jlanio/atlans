# tests/unit/test_exclusao_conteudo_local.py
"""
Exclusao manual pelo web quando o conteudo vive no disco de um executor.

A leitura (download 409) e a retencao automatica ja estavam cobertas. O caminho
de exclusao MANUAL nao estava, e tinha dois defeitos de naturezas opostas:

  ARTEFATO   `delete_artifact` pulava o MinIO por `s3_key` nula e apagava a
             linha assim mesmo. O arquivo ficava orfao no disco do usuario e o
             servidor perdia o unico registro dele — para dado pessoal, pior que
             nao ter apagado, porque ninguem consegue nem saber que ha o que
             apagar.

  DRIVE      `delete_file` chamava `delete_strict_async(None)`. O boto3 valida
             `Key=None` no CLIENTE e levanta ParamValidationError, que nao e
             ClientError, escapa do `except` e virava 500 — o arquivo nao podia
             ser excluido de jeito nenhum.
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

    # A mensagem precisa dizer O QUE FAZER. "Nao permitido" sozinho deixa a
    # pessoa sem acao no unico lugar onde ela esta olhando.
    msg = str(e.value).lower()
    assert "pasta sincronizada" in msg or "geosync" in msg


def test_recusa_e_409_e_nao_400():
    """Nao ha nada errado no pedido — o problema e o ESTADO do recurso."""
    assert ConteudoNoExecutorError.status_code == 409


def test_arquivo_normal_passa():
    drive_service._recusar_se_catalogado(
        _arquivo(content_location="minio", s3_key="drive/ws1/x.gpkg")
    )


def test_ausencia_do_campo_nao_bloqueia():
    """Objeto antigo sem `content_location` nao pode virar recusa."""
    drive_service._recusar_se_catalogado(SimpleNamespace(id_hash="h", s3_key="k"))


# ── Artefato: a linha so cai quando a ordem foi entregue ─────────────────────
#
# A regra mora em `remocao_de_artefatos.remover_artefatos`, a mesma dos cinco
# caminhos que apagam; as rotas de exclusao a chamam com `agendar_pendentes`.

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
    # O caso do bug: sem entrega, a linha ficava e o arquivo sumia do sistema.
    entrega([])
    a = _artefato(1)
    remocao = await _remover([a])

    assert remocao.apagados == []
    assert [x.id for x in remocao.pendentes_local] == [1]
    assert a.expires_at is not None, "sem expires_at a retencao nunca pega este artefato"


@pytest.mark.asyncio
async def test_artefato_FIXADO_perde_o_pin_ao_ser_agendado(entrega):
    """`purge_expired_artifacts` ignora `is_pinned` — sem zerar, o artefato
    ficaria marcado como vencido e nunca purgado: some da UI como "removendo" e
    permanece no disco para sempre."""
    entrega([])
    a = _artefato(1, is_pinned=True)
    await _remover([a])

    assert a.is_pinned is False


@pytest.mark.asyncio
async def test_sem_executor_id_a_linha_e_PRESERVADA(entrega):
    """Sem destino nao ha para quem mandar. Apagar a linha deixaria o arquivo
    orfao e invisivel — mesma decisao da retencao e da purga."""
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


# ── O lote: commit mesmo sem nada apagado, pendente nao e falha ──────────────

async def _excluir_em_lote(monkeypatch, itens):
    from app.api.routers import artifacts_router as R
    from app.core.authorization import workflow_access

    # Onde `exigir_papel_no_workspace` busca o papel (a comparação segue real).
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
    """Regressao: o commit era condicionado ao que foi apagado.

    Com TODOS os artefatos locais e o executor offline — o caso comum deste
    caminho — nada e apagado, e o `expires_at` que acabara de ser posto nos
    objetos ORM morria no rollback da sessao. A API respondia "remocao
    pendente" e nada era agendado: os artefatos nunca seriam purgados e o
    arquivo ficaria no disco para sempre.
    """
    entrega([])
    a = _artefato(1)
    _, db = await _excluir_em_lote(monkeypatch, [a])

    db.commit.assert_awaited_once()
    assert a.expires_at is not None


@pytest.mark.asyncio
async def test_pendente_nao_e_contado_como_falha(entrega, monkeypatch):
    """`skipped` significa "falhou, tente de novo"; pendente vai acontecer
    sozinho. Contar nos dois faria a UI somar o mesmo artefato duas vezes."""
    entrega([])
    resposta, _ = await _excluir_em_lote(monkeypatch, [_artefato(1), _artefato(2, executor_id=None)])

    assert resposta == {"deleted": 0, "skipped": 0, "pendentes_no_executor": 2}
