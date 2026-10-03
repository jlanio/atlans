# tests/unit/test_policy_routing.py
"""
Policy-based routing (spec docs/specs/executor-isolation-routing.md, §5 and §11).

  - GOLDEN: with the backfill data (tier 1 = {dedicado}, terminal pool), the
    chain with the flag `on` is IDENTICAL to the legacy list with `off`. It is
    the proof that turning the flag on changes nothing for anyone.
  - Isolated + everything down ⇒ 503 with its own category and ZERO send_job to the pool.
  - Fallback: the pool only comes in after the tiers are exhausted; tier 2 before the pool.
  - The `no_pool` floor ignores `fallback_terminal='pool'` from the database.
  - §5.3 barrier: a candidate outside the allowed set ⇒ run failed, the job does
    not go out, `dispatch_event` records `isolation_violation`.
  - `dispatch_tier` written in the INSERT and rewritten on failover.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NoExecutorAvailableError
from app.services import workflow_execution_service as svc
from app.services import workspace_executor_service as politica


def _executor(id_hash, *, is_default=False):
    e = MagicMock()
    e.id_hash = id_hash
    e.name = id_hash
    e.is_default = is_default
    e.status = "active"
    e.public_key = "pem"
    e.executor_type = "default" if is_default else "dedicated"
    return e


def _wf(workspace_id="ws-1"):
    wf = MagicMock()
    wf.id_hash = "wf-1"
    wf.workspace_id = workspace_id
    wf.pinned_outputs = None
    wf.pin_metadata = None
    return wf


def _registry(*, offline=(), unknown=()):
    """presence_or_unknown per executor; no declared capacity."""
    reg = MagicMock()

    async def _presence(executor_id):
        if executor_id in offline:
            return False
        if executor_id in unknown:
            return None
        return True

    reg.presence_or_unknown = AsyncMock(side_effect=_presence)
    reg.get = MagicMock(return_value=None)
    reg.read_capacities = AsyncMock(return_value={})
    reg.send_job = AsyncMock(return_value=True)
    reg.send_json = AsyncMock(return_value=True)
    return reg


def _db_legado(dedicado):
    """db.execute for the legacy path: the workspace→executor JOIN returns `dedicado`;
    the count of in-flight runs (`_contadas_pelo_servidor`, on the session's
    connection, inside a savepoint) comes back empty."""
    res = MagicMock()
    res.scalar_one_or_none = MagicMock(return_value=dedicado)
    conexao = MagicMock()
    conexao.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db = MagicMock()
    db.execute = AsyncMock(return_value=res)
    db.connection = AsyncMock(return_value=conexao)
    return db


def _db():
    """Session for the policy path: reading the policy and the pool come from the
    patches; all that reaches the database is the in-flight run count, empty."""
    return _db_legado(None)


def _policy(primary=(), fallback=(), terminal="fail", floor="none"):
    return politica.WorkspacePolicy(
        workspace_id="ws-1", primary=list(primary), fallback=list(fallback),
        terminal_configured=terminal, floor=floor,
    )


def _espiar_evento():
    """Spy on `dispatch_event` (the JSON line per decision), without silencing it."""
    return patch.object(svc, "_log_dispatch_event", wraps=svc._log_dispatch_event)


def _desfecho(evento) -> dict:
    """Policy, tier and outcome of the SINGLE `dispatch_event` emitted."""
    evento.assert_called_once()
    return {chave: evento.call_args.kwargs[chave] for chave in ("mode", "tier", "outcome")}


@pytest.fixture(autouse=True)
def _desempate_estavel():
    """Ties broken by input order. The golden test compares TWO lists, and random
    choice among equally busy executors would make them differ with nothing wrong."""
    with patch.object(svc, "_desempate", lambda: 0.0):
        yield


# ══════════════════════════════════════════════════════════════════════════════
# Candidate resolution
# ══════════════════════════════════════════════════════════════════════════════

class TestDourado:
    @pytest.mark.asyncio
    async def test_flag_on_com_backfill_e_identica_ao_legado(self):
        ded = _executor("geo-01")
        pool = [_executor("pool-a", is_default=True), _executor("pool-b", is_default=True)]
        reg = _registry()

        with patch.object(svc, "executor_registry", reg), \
             patch.object(svc, "get_default_agents", AsyncMock(return_value=pool)), \
             patch("app.services.user_executor_service.get_default_agents", AsyncMock(return_value=pool)):
            with patch.object(svc, "policy_routing_enabled", lambda: False):
                legado = await svc._resolve_candidates(_db_legado(ded), _wf())
            with patch.object(svc, "policy_routing_enabled", lambda: True), \
                 patch.object(svc.politica, "load_policy_by_id",
                              AsyncMock(return_value=_policy(primary=[ded], terminal="pool"))):
                novo = await svc._resolve_candidates(_db(), _wf())

        assert [e.id_hash for e in legado] == [e.id_hash for e in novo] == ["geo-01", "pool-a", "pool-b"]
        assert legado.tiers == novo.tiers == {"geo-01": "primary", "pool-a": "pool", "pool-b": "pool"}

    @pytest.mark.asyncio
    async def test_modo_pool_inalterado(self):
        pool = [_executor("pool-a", is_default=True)]
        with patch.object(svc, "executor_registry", _registry()), \
             patch.object(svc, "get_default_agents", AsyncMock(return_value=pool)), \
             patch("app.services.user_executor_service.get_default_agents", AsyncMock(return_value=pool)), \
             patch.object(svc, "policy_routing_enabled", lambda: True), \
             patch.object(svc.politica, "load_policy_by_id", AsyncMock(return_value=_policy())):
            cadeia = await svc._resolve_candidates(_db(), _wf())
        assert [e.id_hash for e in cadeia] == ["pool-a"] and cadeia.mode == "pool"


class TestContratoPorPolitica:
    @pytest.mark.asyncio
    async def test_isolado_com_grupo_fora_falha_sem_tocar_o_pool(self):
        ded = [_executor("geo-01"), _executor("geo-02")]
        pool = [_executor("pool-a", is_default=True)]
        reg = _registry(offline=("geo-01", "geo-02"))
        with patch.object(svc, "executor_registry", reg), \
             patch.object(svc, "get_default_agents", AsyncMock(return_value=pool)) as pool_lookup, \
             patch.object(svc, "policy_routing_enabled", lambda: True), \
             patch.object(svc.politica, "load_policy_by_id", AsyncMock(return_value=_policy(primary=ded))), \
             _espiar_evento() as evento:
            with pytest.raises(NoExecutorAvailableError) as exc:
                await svc._resolve_candidates(_db(), _wf())
        assert exc.value.category == "no_dedicated_executor"
        assert "NÃO foi enviado ao pool" in exc.value.detail
        pool_lookup.assert_not_awaited()        # the pool was not even queried
        reg.send_job.assert_not_awaited()
        assert _desfecho(evento) == {"mode": "isolated", "tier": None, "outcome": "no_candidates"}

    @pytest.mark.asyncio
    async def test_fallback_nivel_2_antes_do_pool_e_pool_por_ultimo(self):
        p1 = _executor("lic-01"); p2 = _executor("lic-02")
        pool = [_executor("pool-a", is_default=True)]
        with patch.object(svc, "executor_registry", _registry()), \
             patch.object(svc, "get_default_agents", AsyncMock(return_value=pool)), \
             patch("app.services.user_executor_service.get_default_agents", AsyncMock(return_value=pool)), \
             patch.object(svc, "policy_routing_enabled", lambda: True), \
             patch.object(svc.politica, "load_policy_by_id",
                          AsyncMock(return_value=_policy(primary=[p1], fallback=[p2], terminal="pool"))):
            cadeia = await svc._resolve_candidates(_db(), _wf())
        assert [e.id_hash for e in cadeia] == ["lic-01", "lic-02", "pool-a"]
        assert cadeia.tiers == {"lic-01": "primary", "lic-02": "fallback", "pool-a": "pool"}
        assert cadeia.mode == "dedicated_pool"
        assert cadeia.allowed == {"lic-01", "lic-02", "pool-a"}

    @pytest.mark.asyncio
    async def test_piso_no_pool_ignora_terminal_pool_do_banco(self):
        ded = _executor("geo-01")
        pool = [_executor("pool-a", is_default=True)]
        reg = _registry(offline=("geo-01",))
        with patch.object(svc, "executor_registry", reg), \
             patch.object(svc, "get_default_agents", AsyncMock(return_value=pool)), \
             patch.object(svc, "policy_routing_enabled", lambda: True), \
             patch.object(svc.politica, "load_policy_by_id",
                          AsyncMock(return_value=_policy(primary=[ded], terminal="pool", floor="no_pool"))):
            with pytest.raises(NoExecutorAvailableError) as exc:
                await svc._resolve_candidates(_db(), _wf())
        assert exc.value.category == "no_dedicated_executor"

    @pytest.mark.asyncio
    async def test_presenca_desconhecida_mantem_o_candidato(self):
        """Redis blip or reconnection in progress: the executor is TRIED (spec §5.1)."""
        ded = _executor("geo-01")
        with patch.object(svc, "executor_registry", _registry(unknown=("geo-01",))), \
             patch.object(svc, "get_default_agents", AsyncMock(return_value=[])), \
             patch("app.services.user_executor_service.get_default_agents", AsyncMock(return_value=[])), \
             patch.object(svc, "policy_routing_enabled", lambda: True), \
             patch.object(svc.politica, "load_policy_by_id", AsyncMock(return_value=_policy(primary=[ded]))):
            cadeia = await svc._resolve_candidates(_db(), _wf())
        assert [e.id_hash for e in cadeia] == ["geo-01"]


# ══════════════════════════════════════════════════════════════════════════════
# Dispatch: dispatch_tier e barreira do isolamento
# ══════════════════════════════════════════════════════════════════════════════

def _db_dispatch(rowcount=1):
    """INSERT/commit + o UPDATE pending→running (rowcount)."""
    atualizado = MagicMock(); atualizado.rowcount = rowcount
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=atualizado)
    return db


def _definition():
    return {"nodes": [{"id": "t", "name": "WebhookTrigger"}], "edges": []}


class TestDispatchTierEBarreira:
    @pytest.mark.asyncio
    async def test_grava_dispatch_tier_no_insert_e_reescreve_no_failover(self):
        p1 = _executor("lic-01"); pool = _executor("pool-a", is_default=True)
        cadeia = svc.CandidateList([p1, pool], tiers={"lic-01": "primary", "pool-a": "pool"},
                                   allowed={"lic-01", "pool-a"}, mode="dedicated_pool")
        reg = _registry()
        reg.send_job = AsyncMock(side_effect=[False, True])  # lic-01 recusa, pool-a aceita
        db = _db_dispatch()
        with patch.object(svc, "executor_registry", reg), \
             patch.object(svc, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d)), \
             patch.object(svc, "build_job_message", MagicMock(return_value={"envelope": {}})), \
             patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()), \
             _espiar_evento() as evento:
            result = await svc._dispatch_job(_wf(), _definition(), cadeia, {}, False, db=db)
        run = db.add.call_args.args[0]
        assert result.id == run.task_id
        assert run.host == "executor:pool-a"
        assert run.dispatch_tier == "pool"          # rewritten on failover
        assert _desfecho(evento) == {"mode": "dedicated_pool", "tier": "pool", "outcome": "dispatched"}

    @pytest.mark.asyncio
    async def test_candidato_fora_do_conjunto_permitido_nao_sai(self):
        intruso = _executor("pool-a", is_default=True)
        cadeia = svc.CandidateList([intruso], tiers={"pool-a": "pool"}, allowed={"geo-01"}, mode="isolated")
        reg = _registry()
        db = _db_dispatch()
        cifra = MagicMock(return_value={"envelope": {}})
        with patch.object(svc, "executor_registry", reg), \
             patch.object(svc, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d)), \
             patch.object(svc, "build_job_message", cifra), \
             patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()) as fechar, \
             _espiar_evento() as evento:
            with pytest.raises(NoExecutorAvailableError) as exc:
                await svc._dispatch_job(_wf(), _definition(), cadeia, {}, False, db=db)
        assert exc.value.category == "isolation_violation"
        cifra.assert_not_called()                  # never encrypted for the intruder's key
        reg.send_job.assert_not_awaited()
        run = db.add.call_args.args[0]
        assert run.status == "failed" and "isolamento" in run.error_message
        fechar.assert_awaited_once()
        assert _desfecho(evento) == {"mode": "isolated", "tier": "pool", "outcome": "isolation_violation"}

    @pytest.mark.asyncio
    async def test_todos_recusam_usa_a_mensagem_da_politica(self):
        ded = _executor("geo-01")
        cadeia = svc.CandidateList([ded], tiers={"geo-01": "primary"}, allowed={"geo-01"}, mode="isolated",
                                   exhausted_message="Workspace isolado: nenhum dos 1 executores dedicados está disponível. O job NÃO foi enviado ao pool compartilhado.",
                                   exhausted_category="no_dedicated_executor")
        reg = _registry(); reg.send_job = AsyncMock(return_value=False)
        db = _db_dispatch()
        with patch.object(svc, "executor_registry", reg), \
             patch.object(svc, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d)), \
             patch.object(svc, "build_job_message", MagicMock(return_value={"envelope": {}})), \
             patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()):
            with pytest.raises(NoExecutorAvailableError) as exc:
                await svc._dispatch_job(_wf(), _definition(), cadeia, {}, False, db=db)
        assert exc.value.category == "no_dedicated_executor"
        run = db.add.call_args.args[0]
        assert run.status == "failed" and run.error_message.startswith("Workspace isolado")

    @pytest.mark.asyncio
    async def test_lista_crua_sem_politica_continua_funcionando(self):
        """Compatibility: whoever passes a plain `list` (old tests, legacy path without
        annotations) does not break — no tier, no barrier."""
        ag = _executor("ag-1")
        reg = _registry()
        db = _db_dispatch()
        with patch.object(svc, "executor_registry", reg), \
             patch.object(svc, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d)), \
             patch.object(svc, "build_job_message", MagicMock(return_value={"envelope": {}})), \
             patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()):
            result = await svc._dispatch_job(_wf(), _definition(), [ag], {}, False, db=db)
        run = db.add.call_args.args[0]
        assert result.id == run.task_id and run.dispatch_tier is None
