# tests/integration/test_grupos_ordem.py
"""
Ordem dos grupos de workflows.

O `GET /workflow-groups/` nao tinha `order_by` nenhum: a ordem vinha indefinida
do banco e podia mudar entre dois carregamentos da mesma pagina. Nao havia nem
ordem estavel, quanto mais escolhida pelo usuario.

Os testes chamam as funcoes de rota diretamente, com uma sessao SQLite de
memoria — o que interessa aqui e a consulta e a gravacao, nao a camada HTTP.
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
    """Request minima: `create_group` tem rate limit, e o slowapi recusa
    qualquer coisa que nao seja uma Request de verdade."""
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


# Onde `exigir_papel_no_workspace` busca o papel: trocar aqui mantém a
# comparação de verdade rodando, só sem a tabela de membros.
_PAPEL = "app.core.authorization.workflow_access.get_workspace_member_role"


def _editor():
    """Papel de editor no workspace, sem precisar da tabela de membros."""
    return patch(_PAPEL, new=AsyncMock(return_value="editor"))


# ── listagem ────────────────────────────────────────────────────────────────

class TestOrdemDaListagem:

    @pytest.mark.asyncio
    async def test_ordena_pela_posicao_e_nao_pelo_nome(self, db):
        await _grupos(db, ("Zebra", 0), ("Abacate", 1))
        assert await _nomes_em_ordem(db) == ["Zebra", "Abacate"]

    @pytest.mark.asyncio
    async def test_nome_desempata_posicoes_iguais(self, db):
        # Grupos criados antes da coluna existir, ou uma reordenacao
        # interrompida: sem o desempate a ordem volta a ser indefinida.
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
        """Ignorar em silencio deixaria banco e tela com listas diferentes —
        e a proxima reordenacao gravaria por cima da divergencia."""
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


# ── registro das rotas ──────────────────────────────────────────────────────

def test_reorder_e_registrada_antes_do_path_variavel():
    """`PUT /reorder` tem de vir ANTES de `PUT /{group_id}`.

    O FastAPI casa as rotas na ordem de registro: com o path variavel primeiro,
    "reorder" chegaria como se fosse um id de grupo, e a resposta seria um 404
    de grupo inexistente — um erro que nao sugere em nada a causa real.
    """
    caminhos = [r.path for r in rota.router.routes if "PUT" in (r.methods or set())]
    assert caminhos.index("/workflow-groups/reorder") < caminhos.index(
        "/workflow-groups/{group_id}"
    )


# ── criacao ─────────────────────────────────────────────────────────────────

class TestGrupoNovoVaiParaOFim:

    @pytest.mark.asyncio
    async def test_nao_nasce_empatado_em_zero(self, db):
        """Com `position=0` fixo, todo grupo novo empata com os existentes e a
        ordem entre eles volta a depender do desempate por nome."""
        await _grupos(db, ("A", 0), ("B", 1))

        with _editor():
            novo = await rota.create_group(
                request=_requisicao(),
                payload=WorkflowGroupCreate(name="Aaa", workspace_id=WS),
                db=db, current_user=_Usuario(),
            )

        assert novo.position == 2
        # O nome viria primeiro no alfabeto; a posicao e que manda.
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
