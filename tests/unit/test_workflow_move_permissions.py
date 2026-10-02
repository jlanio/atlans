# tests/unit/test_workflow_move_permissions.py
"""Autorizacao da rota de mover workflow entre workspaces.

Mover atravessa a fronteira de tenant: leva a definition — que traz
`credential_id` em texto puro e ids de arquivos do Drive — para dentro de outro
workspace, e passa a produzir dados la. Por isso exige admin/owner nos DOIS
lados, e nao o `editor` que basta para criar e duplicar dentro do proprio
workspace.

E a lacuna que `app/schemas/workflow.py` descreve ao recusar `workspace_id` no
PUT: la a autorizacao seria resolvida contra o workspace ANTERIOR a mudanca.

As duas guardas sao as de verdade, sem subir a aplicacao: a da ORIGEM e a
dependencia `workflow_com_papel` declarada na propria rota (lida do router), e
a do DESTINO roda em `_move`, com o papel vindo de `get_workspace_member_role`.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routers import workflows_router as WR
from app.schemas.workflow import WorkflowMove, WorkflowUpdate

_ORIGEM = "Requer role 'admin' ou 'owner' no workspace de origem para mover workflows."
_DESTINO = "Requer role 'admin' ou 'owner' no workspace de destino para mover workflows."

_ROTAS_DE_MOVER = ["/workflows/{id_hash}/move", "/workflows/{id_hash}/move/preview"]


def _guarda_da_origem(caminho: str):
    """A dependencia de papel que a rota declara — a que roda em producao."""
    (rota,) = [r for r in WR.router.routes if r.path == caminho]
    (guarda,) = [d.call for d in rota.dependant.dependencies if hasattr(d.call, "papel_minimo")]
    return guarda


async def _origem(papel, caminho=_ROTAS_DE_MOVER[0]):
    wf = SimpleNamespace(id_hash="wf-1", workspace_id="ws-origem")
    return await _guarda_da_origem(caminho)((wf, papel))


async def _mover(papel_no_destino):
    """`_move` com o papel no destino decidido pelo teste; devolve o service."""
    service = SimpleNamespace(move_workflow=AsyncMock(return_value={
        "id": "wf-1", "name": "Fluxo", "renamed": False, "from_workspace_id": "ws-origem",
        "to_workspace_id": "ws-destino", "dry_run": True, "warnings": [],
    }))
    with patch(
        "app.core.authorization.workflow_access.get_workspace_member_role",
        new=AsyncMock(return_value=papel_no_destino),
    ):
        await WR._move(
            WorkflowMove(target_workspace_id="ws-destino"), service,
            SimpleNamespace(id_hash="wf-1"), db=None,
            current_user=SimpleNamespace(id_hash="u-1"), dry_run=True,
        )
    return service


# ── Casos negados ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("caminho", _ROTAS_DE_MOVER)
@pytest.mark.parametrize("origem", ["viewer", "editor", "operator"])
async def test_403_quando_o_papel_na_origem_e_insuficiente(origem, caminho):
    """O move e o preview declaram a MESMA guarda: o preview sem ela viraria um
    oraculo sobre o conteudo de workspaces alheios."""
    with pytest.raises(HTTPException) as exc:
        await _origem(origem, caminho)

    assert exc.value.status_code == 403
    assert exc.value.detail == _ORIGEM


@pytest.mark.parametrize("destino", ["viewer", "editor", "operator"])
async def test_403_quando_o_papel_no_destino_e_insuficiente(destino):
    with pytest.raises(HTTPException) as exc:
        await _mover(destino)

    assert exc.value.status_code == 403
    assert exc.value.detail == _DESTINO


async def test_403_quando_admin_apenas_na_origem():
    await _origem("admin")                      # a origem passa...
    with pytest.raises(HTTPException) as exc:   # ...e o destino barra
        await _mover(None)
    assert exc.value.status_code == 403


async def test_403_quando_admin_apenas_no_destino():
    with pytest.raises(HTTPException) as exc:
        await _origem(None)
    assert exc.value.status_code == 403


async def test_nao_membro_e_workspace_inexistente_dao_a_mesma_resposta():
    """`get_workspace_member_role` devolve None para nao-membro, workspace
    inexistente e workspace na lixeira. Distinguir permitiria enumerar
    workspaces alheios chutando ids."""
    with pytest.raises(HTTPException) as nao_membro:
        await _mover(None)

    assert nao_membro.value.status_code == 403
    assert nao_membro.value.detail == _DESTINO


async def test_destino_insuficiente_nao_chega_ao_service():
    service = SimpleNamespace(move_workflow=AsyncMock())
    with patch(
        "app.core.authorization.workflow_access.get_workspace_member_role",
        new=AsyncMock(return_value="editor"),
    ), pytest.raises(HTTPException):
        await WR._move(
            WorkflowMove(target_workspace_id="ws-destino"), service,
            SimpleNamespace(id_hash="wf-1"), db=None,
            current_user=SimpleNamespace(id_hash="u-1"), dry_run=False,
        )
    service.move_workflow.assert_not_awaited()


# ── Casos permitidos ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("origem", ["admin", "owner"])
@pytest.mark.parametrize("destino", ["admin", "owner"])
async def test_admin_ou_owner_nos_dois_lados_passa(origem, destino):
    """`owner` esta acima de `admin` em WORKSPACE_ROLE_ORDER, entao a checagem
    de minimo ja o cobre — nao ha ramo especial para dono."""
    await _origem(origem)
    service = await _mover(destino)
    service.move_workflow.assert_awaited_once()


# ── Regressao: o PUT continua sem poder trocar de tenant ─────────────────────

def test_workspace_id_continua_proibido_no_update():
    """Esta rota existe justamente para que o PUT nao precise aceitar o campo.
    Se `extra="forbid"` cair, o buraco de IDOR volta pela porta antiga."""
    with pytest.raises(ValidationError):
        WorkflowUpdate(name="x", workspace_id="ws-alheio")
