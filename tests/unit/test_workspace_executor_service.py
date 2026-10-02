# tests/unit/test_workspace_executor_service.py
"""
Política de execução por workspace (spec docs/specs/executor-isolation-routing.md).

Regras que NÃO podem regredir em silêncio:
  - o piso `no_pool` vence qualquer `fallback_terminal` (calculado, não gravado);
  - executor do pool (is_default) nunca entra num nível (Q3);
  - nível 2 exige nível 1; esvaziar o principal apaga o fallback;
  - revogar/promover um executor que esvaziaria um nível principal é 409 sem `force`.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import (
    WorkspaceAccessDeniedError, WorkspacePolicyConflictError, WorkspacePolicyError,
    WorkspacePolicyFloorError,
)
from app.services import workspace_executor_service as svc


def _executor(id_hash="ex-1", *, is_default=False, status="active", public_key="pem", name=None):
    e = MagicMock()
    e.id_hash = id_hash
    e.name = name or id_hash
    e.is_default = is_default
    e.status = status
    e.public_key = public_key
    e.executor_type = "default" if is_default else "dedicated"
    return e


def _workspace(id_hash="ws-1", terminal="fail", floor="none"):
    ws = MagicMock()
    ws.id_hash = id_hash
    ws.name = "Bacia"
    ws.owner_id = "u-1"
    ws.fallback_terminal = terminal
    ws.isolation_floor = floor
    return ws


def _row(executor_id, tier, id_=None):
    r = MagicMock()
    r.id = id_ or f"row-{executor_id}"
    r.executor_id = executor_id
    r.tier = tier
    return r


def _db_returning(*results):
    """db.execute devolve, em ordem, objetos com scalar_one_or_none/scalars().all()/all()."""
    db = MagicMock()
    fila = list(results)

    async def _execute(*_a, **_k):
        valor = fila.pop(0)
        res = MagicMock()
        res.scalar_one_or_none = MagicMock(return_value=valor)
        scalars = MagicMock()
        scalars.all = MagicMock(return_value=valor if isinstance(valor, list) else [])
        res.scalars = MagicMock(return_value=scalars)
        res.all = MagicMock(return_value=valor if isinstance(valor, list) else [])
        return res

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


# ── terminal efetivo e modo ───────────────────────────────────────────────────

class TestTerminalEfetivo:
    def test_piso_no_pool_vence_o_terminal_pool(self):
        assert svc.effective_terminal_of("no_pool", "pool") == "fail"

    def test_sem_piso_vale_o_configurado(self):
        assert svc.effective_terminal_of("none", "pool") == "pool"
        assert svc.effective_terminal_of("none", "fail") == "fail"

    def test_valor_desconhecido_cai_para_fail(self):
        assert svc.effective_terminal_of(None, "banana") == "fail"
        assert svc.effective_terminal_of(None, None) == "fail"

    def test_modo_derivado(self):
        p = svc.WorkspacePolicy(workspace_id="ws")
        assert p.mode == svc.MODE_POOL and p.allows_pool
        p.primary = [_executor()]
        assert p.mode == svc.MODE_ISOLATED and not p.allows_pool
        p.terminal_configured = "pool"
        assert p.mode == svc.MODE_DEDICATED_POOL and p.allows_pool
        p.floor = "no_pool"
        assert p.mode == svc.MODE_ISOLATED and not p.allows_pool


# ── inclusão em nível ─────────────────────────────────────────────────────────

class TestModeOf:
    def test_a_mesma_conta_da_dataclass(self):
        assert svc.mode_of(False, "none", "fail") == svc.MODE_POOL
        assert svc.mode_of(False, "no_pool", "pool") == svc.MODE_ISOLATED
        assert svc.mode_of(True, "none", "fail") == svc.MODE_ISOLATED
        assert svc.mode_of(True, "none", "pool") == svc.MODE_DEDICATED_POOL
        assert svc.mode_of(True, "no_pool", "pool") == svc.MODE_ISOLATED


class TestPisoSemPrincipal:
    def test_piso_no_pool_sem_principal_e_isolado_e_nunca_pool(self):
        p = svc.WorkspacePolicy(workspace_id="ws", floor="no_pool", terminal_configured="pool")
        assert p.mode == svc.MODE_ISOLATED
        assert not p.allows_pool
        assert p.terminal_effective == "fail"

    def test_sem_piso_e_sem_principal_e_pool(self):
        p = svc.WorkspacePolicy(workspace_id="ws")
        assert p.mode == svc.MODE_POOL and p.allows_pool


class TestReplacePrimaryLegado:
    """Endpoint legado `PUT /workspaces/{id}/executor` (dual-write)."""

    @pytest.mark.asyncio
    async def test_executor_do_pool_limpa_os_niveis_e_o_terminal(self):
        ws = _workspace(terminal="pool")
        rows = [_row("ex-1", 1), _row("ex-2", 2)]
        db = _db_returning(rows, _executor("pool-a", is_default=True), None)
        await svc.replace_primary(db, ws, "pool-a", actor_id="u")
        # rows + executor + DELETE de todos os níveis
        assert db.execute.await_count == 3
        assert ws.fallback_terminal == "fail"
        assert any(c.args[0].action == "workspace.executor_policy.cleared" for c in db.add.call_args_list)

    @pytest.mark.asyncio
    async def test_nulo_limpa_e_reseta_terminal(self):
        ws = _workspace(terminal="pool")
        db = _db_returning([_row("ex-1", 1)], None)
        await svc.replace_primary(db, ws, None, actor_id="u")
        assert ws.fallback_terminal == "fail"

    @pytest.mark.asyncio
    async def test_nivel_1_nascendo_do_vazio_reproduz_o_legado_com_terminal_pool(self):
        # Hoje esse workspace transborda para o pool quando o dedicado cai; a
        # política precisa nascer igual para a virada da flag não mudar nada.
        ws = _workspace(terminal="fail")
        db = _db_returning([], _executor("ex-1"), None, None)
        await svc.replace_primary(db, ws, "ex-1", actor_id="u")
        assert ws.fallback_terminal == "pool"
        assert any(type(c.args[0]).__name__ == "WorkspaceExecutor" for c in db.add.call_args_list)

    @pytest.mark.asyncio
    async def test_nivel_1_nascendo_sob_piso_fica_fail(self):
        ws = _workspace(terminal="fail", floor="no_pool")
        db = _db_returning([], _executor("ex-1"), None, None)
        await svc.replace_primary(db, ws, "ex-1", actor_id="u")
        assert ws.fallback_terminal == "fail"

    @pytest.mark.asyncio
    async def test_trocar_o_principal_existente_mantem_o_terminal_escolhido(self):
        ws = _workspace(terminal="fail")
        db = _db_returning([_row("ex-1", 1)], _executor("ex-2"), None, None)
        await svc.replace_primary(db, ws, "ex-2", actor_id="u")
        assert ws.fallback_terminal == "fail"


class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_esvaziar_o_principal_apaga_a_reserva_e_reseta_o_terminal(self, monkeypatch):
        monkeypatch.setattr(svc, "_notify_executor", AsyncMock())
        ws = _workspace(terminal="pool")
        rows = [_row("ex-1", 1), _row("ex-2", 2)]
        db = _db_returning(rows, None, None)
        await svc.remove_member(db, ws, "ex-1", actor_id="u")
        assert db.execute.await_count == 3  # rows + delete do alvo + delete da reserva
        assert ws.fallback_terminal == "fail"

    @pytest.mark.asyncio
    async def test_remover_reserva_mantem_o_terminal(self, monkeypatch):
        monkeypatch.setattr(svc, "_notify_executor", AsyncMock())
        ws = _workspace(terminal="pool")
        db = _db_returning([_row("ex-1", 1), _row("ex-2", 2)], None)
        await svc.remove_member(db, ws, "ex-2", actor_id="u")
        assert ws.fallback_terminal == "pool"


class TestUniaoLegadoENiveis:
    @pytest.mark.asyncio
    async def test_workspace_ids_for_executor_une_ponteiro_e_niveis(self):
        db = _db_returning(["ws-legado"], ["ws-nivel", "ws-legado"])
        assert await svc.workspace_ids_for_executor(db, "ex-1") == {"ws-legado", "ws-nivel"}

    @pytest.mark.asyncio
    async def test_executor_ids_for_workspaces_vazio_nao_consulta(self):
        db = _db_returning()
        assert await svc.executor_ids_for_workspaces(db, []) == set()
        db.execute.assert_not_awaited()


class TestAddMember:
    @pytest.mark.asyncio
    async def test_recusa_executor_do_pool(self):
        db = _db_returning(_executor(is_default=True))
        with pytest.raises(WorkspacePolicyError, match="pool compartilhado"):
            await svc.add_member(db, _workspace(), "ex-1", 1, actor_id="u-1")

    @pytest.mark.asyncio
    async def test_recusa_inativo_e_sem_chave(self):
        db = _db_returning(_executor(status="pending"))
        with pytest.raises(WorkspacePolicyError, match="não está ativo"):
            await svc.add_member(db, _workspace(), "ex-1", 1, actor_id="u-1")
        db = _db_returning(_executor(public_key=None))
        with pytest.raises(WorkspacePolicyError, match="chave pública"):
            await svc.add_member(db, _workspace(), "ex-1", 1, actor_id="u-1")

    @pytest.mark.asyncio
    async def test_nivel_2_exige_nivel_1(self):
        db = _db_returning(_executor(), [])  # executor ok; nenhuma linha ainda
        with pytest.raises(WorkspacePolicyError, match="nível principal"):
            await svc.add_member(db, _workspace(), "ex-1", 2, actor_id="u-1")

    @pytest.mark.asyncio
    async def test_um_executor_nao_fica_em_dois_niveis(self):
        db = _db_returning(_executor(), [_row("ex-1", 1)])
        with pytest.raises(WorkspacePolicyError, match="um nível só"):
            await svc.add_member(db, _workspace(), "ex-1", 2, actor_id="u-1")

    @pytest.mark.asyncio
    async def test_sem_acesso_ao_executor(self):
        db = _db_returning(_executor())
        with pytest.raises(WorkspaceAccessDeniedError, match="acesso"):
            await svc.add_member(db, _workspace(), "ex-1", 1, actor_id="u-1", accessible_ids={"outro"})

    @pytest.mark.asyncio
    async def test_inclusao_valida_grava_e_audita(self, monkeypatch):
        monkeypatch.setattr(svc, "_notify_executor", AsyncMock())
        db = _db_returning(_executor(), [])
        row = await svc.add_member(db, _workspace(), "ex-1", 1, actor_id="u-1", accessible_ids={"ex-1"})
        assert row.tier == 1 and row.executor_id == "ex-1"
        adicionados = [c.args[0] for c in db.add.call_args_list]
        assert any(type(a).__name__ == "WorkspaceExecutor" for a in adicionados)
        assert any(type(a).__name__ == "AuditEvent" and a.action.endswith("member_added") for a in adicionados)
        db.commit.assert_awaited()


# ── terminal e piso ───────────────────────────────────────────────────────────

class TestTerminalEPiso:
    @pytest.mark.asyncio
    async def test_pool_recusado_sob_piso(self):
        db = _db_returning()
        with pytest.raises(WorkspacePolicyFloorError):
            await svc.set_terminal(db, _workspace(floor="no_pool"), "pool", actor_id="u-1")

    @pytest.mark.asyncio
    async def test_terminal_invalido(self):
        with pytest.raises(WorkspacePolicyError):
            await svc.set_terminal(_db_returning(), _workspace(), "esperar", actor_id="u-1")

    @pytest.mark.asyncio
    async def test_piso_no_pool_forca_terminal_fail_e_avisa(self):
        db = _db_returning()
        ws = _workspace(terminal="pool")
        forcou = await svc.set_floor(db, ws, "no_pool", actor_id="admin")
        assert forcou is True
        assert ws.fallback_terminal == "fail" and ws.isolation_floor == "no_pool"
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_piso_no_pool_sem_forcar_quando_ja_era_fail(self):
        ws = _workspace(terminal="fail")
        assert await svc.set_floor(_db_returning(), ws, "no_pool", actor_id="admin") is False


# ── cascatas ──────────────────────────────────────────────────────────────────

class TestDetach:
    @pytest.mark.asyncio
    async def test_esvaziar_principal_sem_force_e_409(self, monkeypatch):
        deps = [{"workspace_id": "ws-1", "workspace_name": "Bacia", "owner_id": "u-1",
                 "tier": 1, "primary_count": 1, "would_empty_primary": True}]
        monkeypatch.setattr(svc, "workspaces_depending_on", AsyncMock(return_value=deps))
        db = _db_returning()
        with pytest.raises(WorkspacePolicyConflictError) as exc:
            await svc.detach_executor(db, "ex-1", force=False, actor_id="a", reason="revoked")
        assert "Bacia" in exc.value.detail
        assert exc.value.workspaces == deps
        db.execute.assert_not_awaited()  # nada apagado

    @pytest.mark.asyncio
    async def test_force_apaga_e_limpa_fallback_do_esvaziado(self, monkeypatch):
        deps = [{"workspace_id": "ws-1", "workspace_name": "Bacia", "owner_id": "u-1",
                 "tier": 1, "primary_count": 1, "would_empty_primary": True}]
        monkeypatch.setattr(svc, "workspaces_depending_on", AsyncMock(return_value=deps))
        ws = _workspace(terminal="pool")
        db = _db_returning(None, None, ws)
        out = await svc.detach_executor(db, "ex-1", force=True, actor_id="a", reason="revoked")
        assert out == deps
        # delete do executor + delete do fallback de ws-1 + leitura de ws-1 (terminal)
        assert db.execute.await_count == 3
        # Sem principal, "pool como último recurso" não sobrevive escondido.
        assert ws.fallback_terminal == "fail"
        assert any(type(c.args[0]).__name__ == "AuditEvent" for c in db.add.call_args_list)

    @pytest.mark.asyncio
    async def test_sem_dependente_vivo_ainda_apaga_linhas_de_lixeira(self, monkeypatch):
        # Workspace na lixeira com o executor no nível 1: restaurado depois, não
        # pode voltar com um executor revogado no principal.
        monkeypatch.setattr(svc, "workspaces_depending_on", AsyncMock(return_value=[]))
        db = _db_returning(None)
        out = await svc.detach_executor(db, "ex-1", force=False, actor_id="a", reason="revoked")
        assert out == [] and db.execute.await_count == 1

    @pytest.mark.asyncio
    async def test_sem_esvaziar_nao_bloqueia(self, monkeypatch):
        deps = [{"workspace_id": "ws-1", "workspace_name": "Bacia", "owner_id": "u-1",
                 "tier": 2, "primary_count": 2, "would_empty_primary": False}]
        monkeypatch.setattr(svc, "workspaces_depending_on", AsyncMock(return_value=deps))
        db = _db_returning(None)
        out = await svc.detach_executor(db, "ex-1", force=False, actor_id="a", reason="deleted")
        assert out == deps and db.execute.await_count == 1
