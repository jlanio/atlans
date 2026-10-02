# tests/unit/test_workflow_groups_contagem.py
"""
Contagem dos grupos de workflows.

`workflow_count` contava so os ATIVOS: um grupo de tres workflows com um
desativado dizia "2 workflows" — e o inativo continuava ali na lista. Passa a
contar todos os nao excluidos, e `active_count` (novo) diz quantos estao
ativos: "3 workflows · 2 ativos".

Os tres pontos que devolvem um grupo (criar, listar, atualizar) passam pela
mesma agregacao. Os testes chamam as funcoes de rota diretamente, com uma
sessao SQLite de memoria — mesmo molde de test_grupos_ordem.py.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.requests import Request

from app.api.routers import workflow_groups_router as rota
from app.models.models import Workflow, WorkflowGroup
from app.schemas.workflow_group import WorkflowGroupCreate, WorkflowGroupRead, WorkflowGroupUpdate

WS = "ws-1"


class _Usuario:
    id_hash = "user-1"


def _requisicao() -> Request:
    """`create_group` tem rate limit, e o slowapi recusa qualquer coisa que
    nao seja uma Request de verdade."""
    return Request({
        "type": "http", "method": "POST", "path": "/workflow-groups",
        "headers": [], "client": ("127.0.0.1", 0), "query_string": b"",
    })


def _editor():
    # Onde `exigir_papel_no_workspace` busca o papel (a comparação segue real).
    return patch(
        "app.core.authorization.workflow_access.get_workspace_member_role",
        new=AsyncMock(return_value="editor"),
    )


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


def _workflow(id_hash, *, group_id=None, ativo=True, excluido=False, workspace=WS):
    return Workflow(
        id_hash=id_hash, name=id_hash, definition={"nodes": [], "edges": []},
        flag_ative=ativo, workspace_id=workspace, group_id=group_id,
        deleted_at=datetime(2026, 1, 1) if excluido else None,
    )


GRUPO = "grp-1"


async def _grupo_com_mistura(db) -> str:
    """Um grupo com dois ativos, um inativo e um na lixeira — o cenario que
    exercita as duas contagens de uma vez: (3 workflows, 2 ativos).

    Devolve o id_hash, e nao a entidade: depois do commit a sessao expira o
    objeto, e ler um atributo fora de um `await` dispara um refresh sincrono
    que o driver assincrono recusa.
    """
    db.add_all([
        WorkflowGroup(id_hash=GRUPO, name="Hidrologia", position=0, workspace_id=WS),
        _workflow("a", group_id=GRUPO, ativo=True),
        _workflow("b", group_id=GRUPO, ativo=True),
        _workflow("c", group_id=GRUPO, ativo=False),
        _workflow("lixo", group_id=GRUPO, ativo=False, excluido=True),
        # Fora do grupo: nao pode contar.
        _workflow("solto", ativo=True),
    ])
    await db.commit()
    return GRUPO


def _contagem(item: WorkflowGroupRead) -> tuple[int, int]:
    return item.workflow_count, item.active_count


# ── schema ──────────────────────────────────────────────────────────────────

def test_active_count_tem_default_zero():
    """Grupo vazio e a listagem antiga (sem o campo) continuam validos."""
    assert WorkflowGroupRead.model_fields["active_count"].default == 0


# ── listagem ────────────────────────────────────────────────────────────────

class TestListar:

    @pytest.mark.asyncio
    async def test_conta_inativo_e_ignora_excluido(self, db):
        await _grupo_com_mistura(db)

        [item] = await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])
        assert _contagem(item) == (3, 2)

    @pytest.mark.asyncio
    async def test_grupo_vazio_e_zero_zero(self, db):
        db.add(WorkflowGroup(id_hash="grp-vazio", name="Rascunhos", position=0, workspace_id=WS))
        await db.commit()

        [item] = await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])
        assert _contagem(item) == (0, 0)

    @pytest.mark.asyncio
    async def test_todos_inativos(self, db):
        """"2 workflows · 0 ativos" — antes saia "0 workflows", como se o
        grupo estivesse vazio."""
        db.add_all([
            WorkflowGroup(id_hash="grp-1", name="Parados", position=0, workspace_id=WS),
            _workflow("a", group_id="grp-1", ativo=False),
            _workflow("b", group_id="grp-1", ativo=False),
        ])
        await db.commit()

        [item] = await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])
        assert _contagem(item) == (2, 0)

    @pytest.mark.asyncio
    async def test_varios_grupos_numa_query_so(self, db):
        db.add_all([
            WorkflowGroup(id_hash="grp-1", name="A", position=0, workspace_id=WS),
            WorkflowGroup(id_hash="grp-2", name="B", position=1, workspace_id=WS),
            WorkflowGroup(id_hash="grp-3", name="C", position=2, workspace_id=WS),
            _workflow("a1", group_id="grp-1", ativo=True),
            _workflow("a2", group_id="grp-1", ativo=False),
            _workflow("b1", group_id="grp-2", ativo=True),
        ])
        await db.commit()

        itens = {g.name: _contagem(g) for g in await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])}
        assert itens == {"A": (2, 1), "B": (1, 1), "C": (0, 0)}

    @pytest.mark.asyncio
    async def test_sem_grupo_nenhum_nao_quebra(self, db):
        assert await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS]) == []


# ── criar ───────────────────────────────────────────────────────────────────

class TestCriar:

    @pytest.mark.asyncio
    async def test_conta_o_inativo_que_acabou_de_entrar(self, db):
        """Criar o grupo ja com um inativo dentro devolvia "1 workflow" para
        dois vinculados — a tela recem-criada ja nascia errada."""
        db.add_all([_workflow("ativo", ativo=True), _workflow("inativo", ativo=False)])
        await db.commit()

        with _editor():
            novo = await rota.create_group(
                request=_requisicao(),
                payload=WorkflowGroupCreate(name="Novo", workspace_id=WS, workflow_ids=["ativo", "inativo"]),
                db=db, current_user=_Usuario(),
            )

        assert _contagem(novo) == (2, 1)

    @pytest.mark.asyncio
    async def test_sem_workflows_e_zero_zero(self, db):
        with _editor():
            novo = await rota.create_group(
                request=_requisicao(),
                payload=WorkflowGroupCreate(name="Vazio", workspace_id=WS),
                db=db, current_user=_Usuario(),
            )
        assert _contagem(novo) == (0, 0)


# ── atualizar ───────────────────────────────────────────────────────────────

class TestAtualizar:

    @pytest.mark.asyncio
    async def test_recontagem_apos_trocar_os_membros(self, db):
        grupo = await _grupo_com_mistura(db)

        with _editor():
            item = await rota.update_group(
                group_id=grupo,
                payload=WorkflowGroupUpdate(workflow_ids=["c", "solto"]),
                db=db, current_user=_Usuario(),
            )

        # "c" e inativo, "solto" e ativo: os dois contam, um ativo.
        assert _contagem(item) == (2, 1)

    @pytest.mark.asyncio
    async def test_renomear_sem_mexer_nos_membros_mantem_a_contagem(self, db):
        grupo = await _grupo_com_mistura(db)

        with _editor():
            item = await rota.update_group(
                group_id=grupo,
                payload=WorkflowGroupUpdate(name="Outro nome"),
                db=db, current_user=_Usuario(),
            )

        assert item.name == "Outro nome"
        assert _contagem(item) == (3, 2)


# ── invariante ──────────────────────────────────────────────────────────────

def test_os_tres_pontos_passam_pela_mesma_agregacao():
    """Se uma das rotas voltar a contar por conta propria, a divergencia
    reaparece so naquela tela. O helper e o unico lugar que sabe contar."""
    import inspect

    for nome in ("create_group", "list_groups", "update_group"):
        fonte = inspect.getsource(getattr(rota, nome))
        assert "_contagens_por_grupo" in fonte or "_ler_grupo" in fonte, nome
        assert "func.count()" not in fonte, f"{nome} conta por fora do helper"
