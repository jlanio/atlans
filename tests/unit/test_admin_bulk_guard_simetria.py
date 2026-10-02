# tests/unit/test_admin_bulk_guard_simetria.py
"""
Simetria de guards entre as rotas single e as rotas bulk de admin.

As seis rotas `/{id_hash}/...` chamam `_ensure_admin_can_modify_target`. As tres
`/bulk/*` nao chamavam. Hoje isso e inocuo: o guard e um no-op documentado, a
espera da hierarquia workspace_admin/global_admin prevista no V04.

O problema e o dia em que ele deixar de ser no-op. Nesse momento, quem quisesse
contornar a jurisdicao usaria a rota bulk com um id so — e a assimetria estaria
la ha meses, invisivel, porque nenhum teste comparava os dois caminhos.

Aqui a triagem passou a ser uma funcao unica (`_triar`), entao a simetria e
estrutural. Estes testes travam isso e travam tambem o que a consolidacao NAO
podia mudar: as tres rotas tem regras de elegibilidade diferentes, e uma recusa
do guard nao pode derrubar o lote inteiro.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.routers import admin_users_router as mod

import pytest as _pytest_seg16
from unittest.mock import AsyncMock as _AsyncMock_seg16


@_pytest_seg16.fixture(autouse=True)
def _patch_revoga_executores(monkeypatch):
    """SEG-16: isola estes testes da revogacao de executores (consultas proprias)."""
    monkeypatch.setattr(
        "app.services.executor_service.revogar_executores_do_usuario",
        _AsyncMock_seg16(return_value=[]),
    )


RAIZ = Path(__file__).resolve().parents[2]
ROTAS_BULK = ("bulk_suspend", "bulk_reactivate", "bulk_delete")


class _Usuario:
    def __init__(self, id_hash="admin-1", status="active"):
        self.id_hash = id_hash
        self.status = status
        # A rota registra QUEM suspendeu junto com o motivo.
        self.username = id_hash


def _svc(users):
    return patch.object(
        mod.svc, "get_users_by_ids",
        new=AsyncMock(return_value={u.id_hash: u for u in users}),
    )


# ── Simetria estrutural ──────────────────────────────────────────────────────

@pytest.mark.parametrize("rota", ROTAS_BULK)
def test_toda_rota_bulk_passa_pela_triagem_unica(rota):
    fonte = inspect.getsource(getattr(mod, rota))
    assert "_triar(" in fonte, (
        f"{rota} deixou de usar _triar — a triagem voltou a ser copiada, e com "
        "ela some o guard de jurisdicao"
    )


def test_a_triagem_chama_o_guard_de_jurisdicao():
    fonte = inspect.getsource(mod._triar)
    assert "_ensure_admin_can_modify_target" in fonte, (
        "_triar deixou de chamar o guard que as rotas single chamam"
    )


def test_nenhuma_rota_bulk_reimplementa_o_laco():
    """Uma quarta rota bulk copiando o laco reabriria a assimetria."""
    arvore = ast.parse((RAIZ / "app/api/routers/admin_users_router.py").read_text("utf-8"))
    problemas = []
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not no.name.startswith("bulk_"):
            continue
        chamadas = {
            n.func.id for n in ast.walk(no)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        if "_triar" not in chamadas:
            problemas.append(no.name)
    assert not problemas, f"rota(s) bulk sem _triar: {problemas}"


# ── Comportamento preservado por rota ────────────────────────────────────────

@pytest.mark.asyncio
async def test_suspend_recusa_auto_acao_e_status_errado():
    admin = _Usuario("admin-1")
    ativo = _Usuario("u-ativo", "active")
    suspenso = _Usuario("u-suspenso", "suspended")

    with _svc([admin, ativo, suspenso]), \
            patch.object(mod.svc, "bulk_suspend", new=AsyncMock()) as acao:
        resp = await mod.bulk_suspend(
            payload=type("P", (), {"user_ids": ["admin-1", "u-ativo", "u-suspenso", "sumiu"]})(),
            db=None, current_user=admin,
        )

    assert resp.processed == 1
    assert [u.id_hash for u in acao.await_args.args[1]] == ["u-ativo"]
    erros = {e["user_id"]: e["error"] for e in resp.errors}
    assert "a si mesmo" in erros["admin-1"]
    assert "não pode ser suspenso" in erros["u-suspenso"]
    assert "não encontrado" in erros["sumiu"]


@pytest.mark.asyncio
async def test_reactivate_permite_auto_acao():
    """A unica das tres sem guarda de auto-acao — a diferenca e proposital."""
    admin = _Usuario("admin-1", "suspended")

    with _svc([admin]), patch.object(mod.svc, "bulk_reactivate", new=AsyncMock()):
        resp = await mod.bulk_reactivate(
            payload=type("P", (), {"user_ids": ["admin-1"]})(), db=None, current_user=admin,
        )

    assert resp.processed == 1 and resp.errors == []


@pytest.mark.asyncio
async def test_delete_recusa_quem_ja_esta_excluido():
    admin = _Usuario("admin-1")
    ja = _Usuario("u-ja", "deleted")

    with _svc([admin, ja]), patch.object(mod.svc, "bulk_soft_delete", new=AsyncMock()):
        resp = await mod.bulk_delete(
            payload=type("P", (), {"user_ids": ["u-ja"]})(), db=None, current_user=admin,
        )

    assert resp.processed == 0
    assert "já está excluído" in resp.errors[0]["error"]


# ── Semantica de lote preservada ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recusa_do_guard_vira_erro_do_usuario_e_nao_derruba_o_lote():
    """A diferenca entre single e bulk que a consolidacao tinha de respeitar.

    Na rota single, o guard levanta e a requisicao morre — correto, e um alvo
    so. No lote, derrubar tudo por causa de um usuario fora da jurisdicao
    impediria a acao sobre os outros. Este teste antecipa o V04: hoje o guard e
    no-op, entao sem simulacao nao ha o que verificar.
    """
    admin = _Usuario("admin-1")
    permitido = _Usuario("u-ok", "active")
    negado = _Usuario("u-fora", "active")

    async def _guard(_db, _admin, uid):
        if uid == "u-fora":
            raise HTTPException(status_code=403, detail="Fora da sua jurisdição.")

    with _svc([permitido, negado]), \
            patch.object(mod, "_ensure_admin_can_modify_target", new=_guard), \
            patch.object(mod.svc, "bulk_suspend", new=AsyncMock()) as acao:
        resp = await mod.bulk_suspend(
            payload=type("P", (), {"user_ids": ["u-ok", "u-fora"]})(),
            db=None, current_user=admin,
        )

    assert resp.processed == 1
    assert [u.id_hash for u in acao.await_args.args[1]] == ["u-ok"]
    assert resp.errors == [{"user_id": "u-fora", "error": "Fora da sua jurisdição."}]


# ── O motivo da suspensao para de sumir ──────────────────────────────────────
#
# A UI de admin tem um campo "Motivo (opcional)" com placeholder "Ex: Violacao
# dos termos de uso"; `GisFlowService.suspendUser` envia; `UserSuspendRequest`
# valida (max_length=500). E a rota descartava. O admin escrevia a
# justificativa, via "Usuario suspenso" e o texto sumia sem deixar rastro.

@pytest.mark.asyncio
async def test_bulk_suspend_repassa_o_motivo_e_o_autor():
    admin = _Usuario("admin-1")
    alvo = _Usuario("u-ativo", "active")

    with _svc([alvo]), patch.object(mod.svc, "bulk_suspend", new=AsyncMock()) as acao:
        await mod.bulk_suspend(
            payload=type("P", (), {"user_ids": ["u-ativo"], "reason": "Violacao dos termos"})(),
            db=None, current_user=admin,
        )

    assert acao.await_args.kwargs["motivo"] == "Violacao dos termos"
    assert acao.await_args.kwargs["por"] == "admin-1"


@pytest.mark.asyncio
async def test_suspend_sem_motivo_continua_funcionando():
    """O campo e opcional na UI — ausencia nao pode quebrar a suspensao."""
    admin = _Usuario("admin-1")
    alvo = _Usuario("u-ativo", "active")

    with _svc([alvo]), patch.object(mod.svc, "bulk_suspend", new=AsyncMock()) as acao:
        await mod.bulk_suspend(
            payload=type("P", (), {"user_ids": ["u-ativo"]})(),
            db=None, current_user=admin,
        )

    assert acao.await_args.kwargs["motivo"] is None


@pytest.mark.asyncio
async def test_o_servico_registra_motivo_e_autor_no_log(caplog):
    """O destino e o log estruturado, nao `audit_events`, e isso e deliberado.

    A tabela `audit_events` existe, esta indexada e tem retencao documentada —
    mas o `workspace_id` dela e NOT NULL, e suspender um usuario e acao de
    PLATAFORMA, sem workspace. Alargar a coluna ou carimbar um sentinela e
    decisao de produto; ate la o registro fica onde as demais acoes de admin ja
    sao rastreadas.
    """
    import logging
    from app.services import admin_user_service

    class _U:
        id_hash = "alvo"  # a cascata de revogacao de tokens le o id_hash
        username = "alvo"
        status = "active"
        suspended_at = None

    db = AsyncMock()
    with caplog.at_level(logging.INFO):
        await admin_user_service.suspend_user(
            db, _U(), motivo="Violacao dos termos", por="admin-1",
        )

    registro = " ".join(r.getMessage() for r in caplog.records)
    assert "Violacao dos termos" in registro
    assert "admin-1" in registro
