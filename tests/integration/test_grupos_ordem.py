# tests/integration/test_grupos_ordem.py
"""
Order of workflow groups.

`GET /workflow-groups/` had no `order_by` at all: the order came undefined
from the database and could change between two loads of the same page. There
was not even a stable order, let alone one chosen by the user.

The tests call the route functions directly, with an in-memory SQLite
session — what matters here is the query and the write, not the HTTP layer.
"""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.requests import Request

from app.api.routers import workflow_groups_router as rota
from app.models.models import Workflow, WorkflowGroup
from app.schemas.workflow_group import WorkflowGroupCreate, WorkflowGroupReorder

WS = "ws-1"


class _Usuario:
    id_hash = "user-1"


def _requisicao() -> Request:
    """Minimal Request: `create_group` has a rate limit, and slowapi rejects
    anything that is not a real Request."""
    return Request({
        "type": "http", "method": "POST", "path": "/workflow-groups",
        "headers": [], "client": ("127.0.0.1", 0), "query_string": b"",
    })


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            WorkflowGroup.metadata.create_all,
            tables=[WorkflowGroup.__table__, Workflow.__table__],
        )
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


async def _grupos(db, *nomes_e_posicoes, workspace=WS):
    for nome, pos in nomes_e_posicoes:
        db.add(WorkflowGroup(name=nome, position=pos, workspace_id=workspace))
    await db.commit()
    resultado = {}
    for g in (await rota.list_groups(workspace_id=None, db=db, workspace_ids=[workspace])):
        resultado[g.name] = g
    return resultado


async def _nomes_em_ordem(db, workspace_ids=(WS,)):
    saida = await rota.list_groups(
        workspace_id=None, db=db, workspace_ids=list(workspace_ids)
    )
    return [g.name for g in saida]


# Where `exigir_papel_no_workspace` looks up the role: swapping it here keeps
# the real comparison running, just without the members table.
_PAPEL = "app.core.authorization.workflow_access.get_workspace_member_role"


def _editor():
    """Editor role in the workspace, without needing the members table."""
    return patch(_PAPEL, new=AsyncMock(return_value="editor"))


# ── listagem ────────────────────────────────────────────────────────────────

class TestOrdemDaListagem:

    @pytest.mark.asyncio
    async def test_ordena_pela_posicao_e_nao_pelo_nome(self, db):
        await _grupos(db, ("Zebra", 0), ("Abacate", 1))
        assert await _nomes_em_ordem(db) == ["Zebra", "Abacate"]

    @pytest.mark.asyncio
    async def test_nome_desempata_posicoes_iguais(self, db):
        # Groups created before the column existed, or an interrupted
        # reordering: without the tiebreaker the order becomes undefined again.
        await _grupos(db, ("Beta", 0), ("Alfa", 0), ("Gama", 0))
        assert await _nomes_em_ordem(db) == ["Alfa", "Beta", "Gama"]


# ── reordenacao ─────────────────────────────────────────────────────────────

class TestReordenar:

    @pytest.mark.asyncio
    async def test_grava_a_ordem_recebida(self, db):
        criados = await _grupos(db, ("A", 0), ("B", 1), ("C", 2))
        nova = [criados["C"].id_hash, criados["A"].id_hash, criados["B"].id_hash]

        with _editor():
            await rota.reorder_groups(
                payload=WorkflowGroupReorder(group_ids=nova),
                db=db, current_user=_Usuario(),
            )

        assert await _nomes_em_ordem(db) == ["C", "A", "B"]

    @pytest.mark.asyncio
    async def test_id_desconhecido_e_recusado(self, db):
        """Silently ignoring it would leave the database and the screen with
        different lists — and the next reordering would write over the
        divergence."""
        criados = await _grupos(db, ("A", 0))

        with _editor(), pytest.raises(HTTPException) as exc:
            await rota.reorder_groups(
                payload=WorkflowGroupReorder(group_ids=[criados["A"].id_hash, "nao-existe"]),
                db=db, current_user=_Usuario(),
            )
        assert exc.value.status_code == 404
        assert "nao-existe" in exc.value.detail

    @pytest.mark.asyncio
    async def test_recusa_misturar_workspaces(self, db):
        aqui = await _grupos(db, ("A", 0))
        outro = await _grupos(db, ("X", 0), workspace="ws-2")

        with _editor(), pytest.raises(HTTPException) as exc:
            await rota.reorder_groups(
                payload=WorkflowGroupReorder(group_ids=[aqui["A"].id_hash, outro["X"].id_hash]),
                db=db, current_user=_Usuario(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_exige_papel_de_editor(self, db):
        criados = await _grupos(db, ("A", 0))

        with patch(_PAPEL, new=AsyncMock(return_value="viewer")):
            with pytest.raises(HTTPException) as exc:
                await rota.reorder_groups(
                    payload=WorkflowGroupReorder(group_ids=[criados["A"].id_hash]),
                    db=db, current_user=_Usuario(),
                )
        assert exc.value.status_code == 403


# ── route registration ──────────────────────────────────────────────────────

def test_reorder_e_registrada_antes_do_path_variavel():
    """`PUT /reorder` must come BEFORE `PUT /{group_id}`.

    FastAPI matches routes in registration order: with the variable path
    first, "reorder" would arrive as if it were a group id, and the response
    would be a nonexistent-group 404 — an error that in no way hints at the
    real cause.
    """
    caminhos = [r.path for r in rota.router.routes if "PUT" in (r.methods or set())]
    assert caminhos.index("/workflow-groups/reorder") < caminhos.index(
        "/workflow-groups/{group_id}"
    )


# ── criacao ─────────────────────────────────────────────────────────────────

class TestGrupoNovoVaiParaOFim:

    @pytest.mark.asyncio
    async def test_nao_nasce_empatado_em_zero(self, db):
        """With a fixed `position=0`, every new group ties with the existing ones and
        the order among them goes back to depending on the name tiebreaker."""
        await _grupos(db, ("A", 0), ("B", 1))

        with _editor():
            novo = await rota.create_group(
                request=_requisicao(),
                payload=WorkflowGroupCreate(name="Aaa", workspace_id=WS),
                db=db, current_user=_Usuario(),
            )

        assert novo.position == 2
        # The name would come first alphabetically; the position is what decides.
        assert await _nomes_em_ordem(db) == ["A", "B", "Aaa"]

    @pytest.mark.asyncio
    async def test_primeiro_grupo_do_workspace(self, db):
        with _editor():
            novo = await rota.create_group(
                request=_requisicao(),
                payload=WorkflowGroupCreate(name="Primeiro", workspace_id=WS),
                db=db, current_user=_Usuario(),
            )
        assert novo.position == 1
