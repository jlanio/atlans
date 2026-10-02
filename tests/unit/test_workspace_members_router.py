# tests/unit/test_workspace_members_router.py
"""Lista de membros do workspace: o dono aparece, e nao pode ser editado.

O dono nunca teve linha em `workspace_members` — `create_workspace` nao cria uma.
Ate agora isso significava que quem criou o workspace nao aparecia na propria
lista de membros: um workspace so com o dono exibia "Nenhum membro convidado
ainda", e um admin convidado nao tinha como descobrir com quem falar.

A linha do dono passou a ser sintetica, montada na leitura. Isso abre dois riscos
que estes testes fecham: ele aparecer DUAS vezes (quando tambem tem linha real,
possivel em dados antigos) e a UI oferecer editar/remover uma linha que nao
existe no banco — o que caia num 404 generico.
"""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.routers.workspace_router import _build_member_list


CRIADO_EM = datetime(2026, 1, 15, 10, 30)
ENTROU_EM = datetime(2026, 3, 20, 8, 0)


def _user(id_hash, username, email):
    return SimpleNamespace(id_hash=id_hash, username=username, email=email)


def _member(user_id, role, joined_at=ENTROU_EM):
    return SimpleNamespace(user_id=user_id, role=role, joined_at=joined_at)


# ── _build_member_list (puro, sem DB) ────────────────────────────────────────

def test_owner_vem_primeiro_com_role_owner():
    dono = _user("u-dono", "dona", "dona@ex.com")
    convidado = _user("u-1", "convidado", "c@ex.com")

    resultado = _build_member_list(
        "u-dono", dono, CRIADO_EM, [(_member("u-1", "editor"), convidado)],
    )

    assert [m.user_id for m in resultado] == ["u-dono", "u-1"]
    assert resultado[0].role == "owner"
    # O dono "entrou" quando criou o workspace — nao ha outro timestamp honesto.
    assert resultado[0].joined_at == CRIADO_EM.isoformat()
    assert resultado[1].role == "editor"


def test_owner_com_linha_real_nao_duplica():
    """Ate agora nada impedia convidar o proprio dono por e-mail."""
    dono = _user("u-dono", "dona", "dona@ex.com")

    resultado = _build_member_list(
        "u-dono", dono, CRIADO_EM, [(_member("u-dono", "admin"), dono)],
    )

    assert len(resultado) == 1
    # A linha sintetica vence: "admin" nao pode mascarar quem e o dono.
    assert resultado[0].role == "owner"


def test_sem_owner_id_retorna_so_os_membros():
    """`Workspace.owner_id` e nullable — nao inventar uma linha vazia."""
    convidado = _user("u-1", "convidado", "c@ex.com")

    resultado = _build_member_list(
        None, None, CRIADO_EM, [(_member("u-1", "viewer"), convidado)],
    )

    assert [m.user_id for m in resultado] == ["u-1"]


def test_owner_removido_da_plataforma_nao_gera_linha():
    """owner_id setado mas o User sumiu: sem username/email, nao ha o que exibir."""
    resultado = _build_member_list("u-dono", None, CRIADO_EM, [])
    assert resultado == []


# ── Guardas de escrita sobre o dono ──────────────────────────────────────────

@pytest.fixture
def ws_client_db(client, mock_current_user, monkeypatch):
    """client + db mockado, com o usuario autenticado como dono do workspace.

    `get_workspace_member_role` e trocado por um stub: com um db mockado, o
    `select(Workspace.owner_id)` dela devolveria a entidade inteira em vez do
    id, e a resolucao de role daria 403 antes de a guarda sob teste rodar. O
    stub vale nos dois lugares que a chamam: o proprio router (leitura) e
    `workflow_access`, de onde `exigir_papel_no_workspace` a chama (escrita).
    """
    from app.api.dependencies import get_db
    from app.api.routers import workspace_router
    from app.core.authorization import workflow_access
    from app.main import app

    workspace = SimpleNamespace(
        id_hash="ws-1",
        name="Workspace",
        owner_id=mock_current_user.id_hash,
        deleted_at=None,
        created_at=CRIADO_EM,
    )

    db = MagicMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()

    resultado = MagicMock()
    resultado.scalar_one_or_none.return_value = workspace
    db.execute = AsyncMock(return_value=resultado)

    for modulo in (workspace_router, workflow_access):
        monkeypatch.setattr(
            modulo, "get_workspace_member_role", AsyncMock(return_value="owner"),
        )

    async def _fake_db():
        yield db

    app.dependency_overrides[get_db] = _fake_db
    yield client, workspace
    app.dependency_overrides.pop(get_db, None)


async def test_remover_o_dono_e_400_e_nao_404(ws_client_db):
    """Vale tanto para admin removendo o dono quanto para o dono tentando sair."""
    client, ws = ws_client_db

    resp = await client.delete(f"/workspaces/ws-1/members/{ws.owner_id}")

    assert resp.status_code == 400
    # `http_exception_handler` remapeia `detail` para `message` na resposta.
    assert "dono" in resp.json()["message"].lower()


async def test_alterar_role_do_dono_e_400(ws_client_db):
    client, ws = ws_client_db

    resp = await client.put(
        f"/workspaces/ws-1/members/{ws.owner_id}", json={"role": "viewer"},
    )

    assert resp.status_code == 400
    # `http_exception_handler` remapeia `detail` para `message` na resposta.
    assert "dono" in resp.json()["message"].lower()
