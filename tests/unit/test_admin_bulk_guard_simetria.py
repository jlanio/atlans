# tests/unit/test_admin_bulk_guard_simetria.py
"""
Symmetry of guards between the single and the bulk admin routes.

The six `/{id_hash}/...` routes call `_ensure_admin_can_modify_target`. The
three `/bulk/*` ones did not. Today that is harmless: the guard is a
documented no-op, awaiting the workspace_admin/global_admin hierarchy planned
in V04.

The problem is the day it stops being a no-op. At that moment, whoever wanted
to get around the jurisdiction would use the bulk route with a single id — and
the asymmetry would have been there for months, invisible, because no test
compared the two paths.

Here the triage became a single function (`_triar`), so the symmetry is
structural. These tests lock that in, and also lock what the consolidation
could NOT change: the three routes have different eligibility rules, and a
refusal from the guard must not take down the whole batch.
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
    """SEG-16: isolates these tests from executor revocation (its own queries)."""
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
        # The route records WHO suspended along with the reason.
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


# ── Behavior preserved per route ─────────────────────────────────────────────

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
    """The only one of the three without a self-action guard — the difference is intentional."""
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


# ── Batch semantics preserved ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recusa_do_guard_vira_erro_do_usuario_e_nao_derruba_o_lote():
    """The difference between single and bulk that the consolidation had to respect.

    In the single route, the guard raises and the request dies — correct, it
    is a single target. In the batch, taking everything down because of one
    user outside the jurisdiction would block the action on the others. This
    test anticipates V04: today the guard is a no-op, so without simulation
    there is nothing to check.
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


# ── The suspension reason stops vanishing ────────────────────────────────────
#
# The admin UI has a "Motivo (opcional)" (reason, optional) field with the
# placeholder "Ex: Violacao dos termos de uso"; `GisFlowService.suspendUser`
# sends it; `UserSuspendRequest` validates it (max_length=500). And the route
# discarded it. The admin wrote the justification, saw "Usuario suspenso" and
# the text vanished without a trace.

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
    """The field is optional in the UI — its absence must not break the suspension."""
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
    """The destination is the structured log, not `audit_events`, and that is deliberate.

    The `audit_events` table exists, is indexed and has documented retention —
    but its `workspace_id` is NOT NULL, and suspending a user is a PLATFORM
    action, with no workspace. Widening the column or stamping a sentinel is a
    product decision; until then the record stays where the other admin
    actions are already tracked.
    """
    import logging
    from app.services import admin_user_service

    class _U:
        id_hash = "alvo"  # the token revocation cascade reads the id_hash
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
