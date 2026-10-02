# tests/unit/test_workflow_nome_unico_parcial.py
"""O nome do workflow e unico apenas entre os VIVOS.

O delete de workflow e soft (workflow_crud.soft_delete_by_hash grava deleted_at
e mantem a linha). Enquanto a restricao de nome era total, o nome de tudo que se
apagava ficava ocupado para sempre — e de forma invisivel, ja que nenhuma
listagem mostra soft-deletados. A pre-checagem
(workflow_move_service.nomes_no_workspace) sempre filtrou `deleted_at IS NULL`,
entao ela e o banco discordavam sobre o que e um nome ocupado.

O caso real: `Cópia de get-CAR` foi criado e excluido em 07/08; quase um mes
depois, duplicar `get-CAR` propunha esse mesmo nome (livre para a pre-checagem),
o INSERT batia na restricao e o usuario via "Ja existe um workflow com este nome
neste workspace" sem nenhum workflow com esse nome a vista.

Os unitarios de duplicacao dublam `db.execute` e nunca exercitam a restricao de
verdade — por isso este arquivo monta schema real.
"""
from datetime import datetime

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.workflow import Workflow


_EXCLUIDO_EM = datetime(2026, 8, 7, 22, 26, 32)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Workflow.metadata.create_all, tables=[Workflow.__table__])
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


def _wf(id_hash: str, nome: str, workspace: str = "ws-1", **kw) -> Workflow:
    return Workflow(id_hash=id_hash, name=nome, workspace_id=workspace,
                    definition={}, **kw)


async def _inserir(db, wf) -> bool:
    """True se o banco aceitou; False se recusou por unicidade."""
    db.add(wf)
    try:
        await db.commit()
        return True
    except IntegrityError:
        await db.rollback()
        return False


@pytest.mark.asyncio
async def test_o_predicado_chega_ao_ddl(db):
    """Sem o WHERE, o indice vira unico TOTAL e a regra volta a ser a antiga.

    Vale checar o DDL: o predicado e uma opcao por dialeto
    (`postgresql_where`/`sqlite_where`) e um dialeto sem ela cria o indice em
    silencio, sem erro nenhum — a regressao so apareceria em producao.
    """
    ddl = (await db.execute(sa.text(
        "SELECT sql FROM sqlite_master WHERE name = 'uq_workflow_name_workspace'"
    ))).scalar_one()

    assert "UNIQUE INDEX" in ddl.upper()
    assert "WHERE deleted_at IS NULL" in ddl


@pytest.mark.asyncio
async def test_dois_vivos_com_o_mesmo_nome_sao_recusados(db):
    """A regra que nao pode afrouxar."""
    assert await _inserir(db, _wf("a", "Edificações"))

    assert not await _inserir(db, _wf("b", "Edificações"))


@pytest.mark.asyncio
async def test_excluir_libera_o_nome(db):
    """O caso do 'Cópia de get-CAR': apagar devolve o nome ao workspace."""
    assert await _inserir(db, _wf("a", "get-CAR"))
    assert not await _inserir(db, _wf("b", "get-CAR"))

    alvo = (await db.execute(
        sa.select(Workflow).where(Workflow.id_hash == "a")
    )).scalars().first()
    alvo.deleted_at = _EXCLUIDO_EM
    alvo.flag_ative = False
    await db.commit()

    assert await _inserir(db, _wf("c", "get-CAR"))


@pytest.mark.asyncio
async def test_dois_excluidos_podem_repetir_o_nome(db):
    """Decorre do predicado — e e o que o downgrade da migration desempata."""
    assert await _inserir(db, _wf("a", "X", deleted_at=_EXCLUIDO_EM))

    assert await _inserir(db, _wf("b", "X", deleted_at=_EXCLUIDO_EM))


@pytest.mark.asyncio
async def test_escopo_por_workspace_continua_valendo(db):
    """Afrouxar por `deleted_at` nao pode afrouxar por workspace."""
    assert await _inserir(db, _wf("a", "Edificações", workspace="ws-1"))

    assert await _inserir(db, _wf("b", "Edificações", workspace="ws-2"))


@pytest.mark.asyncio
async def test_nome_liberado_volta_a_ser_exclusivo(db):
    """Reaproveitar o nome de um excluido nao deixa a porta aberta.

    Um segundo vivo com esse nome tem de ser recusado como qualquer outro.
    """
    assert await _inserir(db, _wf("a", "X", deleted_at=_EXCLUIDO_EM))
    assert await _inserir(db, _wf("b", "X"))

    assert not await _inserir(db, _wf("c", "X"))


@pytest.mark.asyncio
async def test_ler_atributo_apos_rollback_e_erro_de_sessao(db):
    """Fixa POR QUE as mensagens de conflito nao podem ler do objeto ORM.

    `crud.update` faz setattr e commita; o `except IntegrityError` chama
    `rollback()`, e o rollback EXPIRA todo objeto da sessao. Ler um atributo
    depois disso dispara refresh lazy — que numa AsyncSession nao e um SELECT a
    mais, e `MissingGreenlet`. Uma mensagem de erro que citasse `wf.name` ali
    trocaria o 409 legivel por um 500, justamente no caminho de erro.

    Por isso `create_workflow` cita o parametro `name` e `update_workflow`
    captura o nome ANTES do commit (`nome_tentado`).
    """
    assert await _inserir(db, _wf("a", "Edificações"))
    assert await _inserir(db, _wf("b", "Outro"))

    alvo = (await db.execute(
        sa.select(Workflow).where(Workflow.id_hash == "b")
    )).scalars().first()

    alvo.name = "Edificações"       # colide com o vivo "a"
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    with pytest.raises(Exception) as erro:
        _ = alvo.name
    assert "greenlet" in str(erro.value).lower()
