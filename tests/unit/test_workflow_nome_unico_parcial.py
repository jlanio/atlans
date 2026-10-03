# tests/unit/test_workflow_nome_unico_parcial.py
"""The workflow name is unique only among the LIVE ones.

Workflow delete is soft (workflow_crud.soft_delete_by_hash writes deleted_at
and keeps the row). While the name constraint was total, the name of everything
that got deleted stayed taken forever — and invisibly, since no listing shows
soft-deleted ones. The pre-check (workflow_move_service.nomes_no_workspace)
always filtered `deleted_at IS NULL`, so it and the database disagreed about
what a taken name is.

The real case: `Cópia de get-CAR` was created and deleted on August 7; almost a
month later, duplicating `get-CAR` proposed that same name (free according to
the pre-check), the INSERT hit the constraint and the user saw "Ja existe um
workflow com este nome neste workspace" (a workflow with this name already
exists in this workspace) with no workflow by that name in sight.

The duplication unit tests stub `db.execute` and never exercise the real
constraint — which is why this file builds a real schema.
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
    """True if the database accepted; False if it refused on uniqueness."""
    db.add(wf)
    try:
        await db.commit()
        return True
    except IntegrityError:
        await db.rollback()
        return False


@pytest.mark.asyncio
async def test_o_predicado_chega_ao_ddl(db):
    """Without the WHERE, the index becomes TOTALLY unique and the rule reverts to the old one.

    Checking the DDL is worth it: the predicate is a per-dialect option
    (`postgresql_where`/`sqlite_where`) and a dialect without it silently
    creates the index, with no error at all — the regression would only show up
    in production.
    """
    ddl = (await db.execute(sa.text(
        "SELECT sql FROM sqlite_master WHERE name = 'uq_workflow_name_workspace'"
    ))).scalar_one()

    assert "UNIQUE INDEX" in ddl.upper()
    assert "WHERE deleted_at IS NULL" in ddl


@pytest.mark.asyncio
async def test_dois_vivos_com_o_mesmo_nome_sao_recusados(db):
    """The rule that must not loosen."""
    assert await _inserir(db, _wf("a", "Edificações"))

    assert not await _inserir(db, _wf("b", "Edificações"))


@pytest.mark.asyncio
async def test_excluir_libera_o_nome(db):
    """The 'Cópia de get-CAR' case: deleting gives the name back to the workspace."""
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
    """Follows from the predicate — and it is what the migration's downgrade breaks ties on."""
    assert await _inserir(db, _wf("a", "X", deleted_at=_EXCLUIDO_EM))

    assert await _inserir(db, _wf("b", "X", deleted_at=_EXCLUIDO_EM))


@pytest.mark.asyncio
async def test_escopo_por_workspace_continua_valendo(db):
    """Loosening by `deleted_at` must not loosen by workspace."""
    assert await _inserir(db, _wf("a", "Edificações", workspace="ws-1"))

    assert await _inserir(db, _wf("b", "Edificações", workspace="ws-2"))


@pytest.mark.asyncio
async def test_nome_liberado_volta_a_ser_exclusivo(db):
    """Reusing a deleted workflow's name does not leave the door open.

    A second live one with that name has to be refused like any other.
    """
    assert await _inserir(db, _wf("a", "X", deleted_at=_EXCLUIDO_EM))
    assert await _inserir(db, _wf("b", "X"))

    assert not await _inserir(db, _wf("c", "X"))


@pytest.mark.asyncio
async def test_ler_atributo_apos_rollback_e_erro_de_sessao(db):
    """Pins down WHY the conflict messages cannot read from the ORM object.

    `crud.update` does setattr and commits; the `except IntegrityError` calls
    `rollback()`, and the rollback EXPIRES every object in the session. Reading
    an attribute after that triggers a lazy refresh — which in an AsyncSession
    is not one more SELECT, it is `MissingGreenlet`. An error message that cited
    `wf.name` there would swap the readable 409 for a 500, precisely on the
    error path.

    That is why `create_workflow` cites the `name` parameter and
    `update_workflow` captures the name BEFORE the commit (`nome_tentado`).
    """
    assert await _inserir(db, _wf("a", "Edificações"))
    assert await _inserir(db, _wf("b", "Outro"))

    alvo = (await db.execute(
        sa.select(Workflow).where(Workflow.id_hash == "b")
    )).scalars().first()

    alvo.name = "Edificações"       # collides with the live "a"
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    with pytest.raises(Exception) as erro:
        _ = alvo.name
    assert "greenlet" in str(erro.value).lower()
