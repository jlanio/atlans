# tests/unit/test_dispatch_bordas_srv.py
"""
Dispatch edge cases that the latency optimizations exposed.

Three invariants no test covered:

A14 — the "no executor available" fail-fast (503) must NOT precede the
      authentication of the webhook caller: an anonymous caller could probe the
      state of the tenant's execution fleet before any 401/403.

A15 — 'pending' does not prove the job did not go out. If the worker that
      dispatched dies between `send_job` and the pending->running commit, the run
      stays 'pending' with the executor really running the workflow; canceling
      has to notify the stored host, otherwise the API answers "cancelado"
      (canceled) and the workflow finishes sending e-mails and writing data.

A40 — the disabled-nodes cache is per PROCESS and production runs 4 workers:
      without the epoch in Redis, a node disabled by the admin keeps being
      dispatched by the other workers (and goes in the job envelope) until the TTL expires.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import NoExecutorAvailableError

TOKEN = "token-do-webhook"


# ══════════════════════════════════════════════════════════════════════════════
# A14 — precedence: authenticate before talking about the fleet
# ══════════════════════════════════════════════════════════════════════════════

def _requisicao(authorization: str | None) -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": authorization} if authorization else {}
    return req


def _definicao_com_gatilho_protegido() -> dict:
    return {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "WebhookTrigger",
             "properties": {"credential_id": "cred-1"}},
        ],
        "edges": [],
    }


def _servico_sem_executor():
    """WorkflowService whose executor pool is empty (503 guaranteed)."""
    from app.services.workflow_service import WorkflowService

    wf = MagicMock()
    wf.id_hash, wf.workspace_id, wf.flag_ative = "wf-1", "ws-1", True
    wf.pinned_outputs = wf.pin_metadata = None
    wf.definition = _definicao_com_gatilho_protegido()

    db = MagicMock()
    service = WorkflowService(db)
    service.crud = MagicMock(db=db)
    service._load_workflow = AsyncMock(return_value=(wf, wf.definition))
    service._resolve_candidates = AsyncMock(
        side_effect=NoExecutorAvailableError(
            "Nenhum executor disponível (pool padrão vazio ou todos offline). "
            "Contate o administrador."
        )
    )
    service._dispatch_job = AsyncMock()
    return service


async def _disparar_sem_executor(service, resolver_credenciais, **kwargs):
    with (
        patch("app.services.disabled_nodes_service.disabled_names",
              new=AsyncMock(return_value=set())),
        # The dispatch imports inside the function — the patch has to be at the source.
        patch("flow.utils.workflow_contract.collect_subworkflow_definitions_recursive",
              new=AsyncMock(return_value={})),
        patch("app.services.workflow_service.resolve_credentials_from_ids",
              new=resolver_credenciais),
    ):
        return await service.start_analysis("wf-1", inputs={}, **kwargs)


class TestOrdemAutenticacaoAntesDoFailFast:

    @pytest.mark.asyncio
    async def test_anonimo_recebe_401_e_nao_sonda_a_frota(self):
        """No header at all: 401 from the token, and `_resolve_candidates` does not even run.

        Before, the same caller got a 503 with the literal message about the
        executor pool — an oracle on the tenant's infrastructure.
        """
        service = _servico_sem_executor()
        resolver = AsyncMock(return_value={"cred-1": {"type": "webhook_token", "token": TOKEN}})

        with pytest.raises(HTTPException) as exc:
            await _disparar_sem_executor(service, resolver, request=_requisicao(None))

        assert exc.value.status_code == 401
        assert service._resolve_candidates.await_count == 0

    @pytest.mark.asyncio
    async def test_token_errado_recebe_403_e_nao_sonda_a_frota(self):
        service = _servico_sem_executor()
        resolver = AsyncMock(return_value={"cred-1": {"type": "webhook_token", "token": TOKEN}})

        with pytest.raises(HTTPException) as exc:
            await _disparar_sem_executor(
                service, resolver, request=_requisicao("Bearer token-errado"),
            )

        assert exc.value.status_code == 403
        assert service._resolve_candidates.await_count == 0

    @pytest.mark.asyncio
    async def test_token_certo_continua_recebendo_o_fail_fast(self):
        """The fail-fast was not removed — only moved after the token."""
        service = _servico_sem_executor()
        resolver = AsyncMock(return_value={"cred-1": {"type": "webhook_token", "token": TOKEN}})

        with pytest.raises(NoExecutorAvailableError):
            await _disparar_sem_executor(
                service, resolver, request=_requisicao(f"Bearer {TOKEN}"),
            )

        assert service._resolve_candidates.await_count == 1
        # And before the dispatch, obviously.
        assert service._dispatch_job.await_count == 0

    @pytest.mark.asyncio
    async def test_disparo_ja_autenticado_aborta_antes_de_resolver_credenciais(self):
        """The latency gain preserved: whoever has already authenticated (Executar
        button, retry, cron) gets the 503 without the server collecting
        sub-workflows or decrypting any credential."""
        service = _servico_sem_executor()
        resolver = AsyncMock(return_value={})

        with pytest.raises(NoExecutorAvailableError):
            await _disparar_sem_executor(
                service, resolver,
                request=_requisicao("Bearer jwt.de.sessao"),
                autenticar_entrada=False,
            )

        assert service._resolve_candidates.await_count == 1
        assert resolver.await_count == 0


# ══════════════════════════════════════════════════════════════════════════════
# A15 — cancelar 'pending' avisa o host gravado
# ══════════════════════════════════════════════════════════════════════════════

def _run(status="pending", host="executor:ag-1"):
    from app.models.models import WorkflowRun

    return WorkflowRun(
        task_id="job-1", workflow_hash="wf-1", workspace_id="ws-1",
        status=status, node_stats={}, host=host,
    )


def _db_para_cancelamento(run, rowcount=1):
    """db.execute: 1o SELECT devolve o run; 2o UPDATE devolve o rowcount."""
    selecionado = MagicMock()
    selecionado.scalar_one_or_none = MagicMock(return_value=run)
    atualizado = MagicMock()
    atualizado.rowcount = rowcount

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[selecionado, atualizado])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


class TestCancelarRunPendente:

    @pytest.mark.asyncio
    async def test_pendente_com_host_avisa_o_executor(self):
        """The scenario of the worker dying between `send_job` and the commit: the
        executor ALREADY has the job, the run stayed 'pending' forever. Without
        this notice the API answers "cancelado" and the workflow runs to the end."""
        from app.services import workflow_execution_service as svc

        run = _run()
        db = _db_para_cancelamento(run)
        registry = MagicMock()
        registry.send_json = AsyncMock(return_value=True)

        with (
            patch.object(svc, "executor_registry", registry),
            patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()),
        ):
            # `como_admin=True` is not a lazy shortcut: these cases are about the MECHANICS
            # of cancellation (pending × delivered, race with the dispatch), and
            # building a workspace association in each one would only pull the test
            # away from what it measures. Authorization has its own coverage in
            # test_fixes_seguranca_opcao_c.py.
            outcome = await svc.cancel_run(db, "job-1", user_id="irrelevante", como_admin=True)

        assert outcome == "cancelled"
        registry.send_json.assert_awaited_once_with(
            "ag-1", {"type": "cancel", "job_id": "job-1"},
        )
        assert run.status == "cancelled"

    @pytest.mark.asyncio
    async def test_pendente_sem_host_nao_tenta_falar_com_ninguem(self):
        from app.services import workflow_execution_service as svc

        run = _run(host=None)
        db = _db_para_cancelamento(run)
        registry = MagicMock()
        registry.send_json = AsyncMock(return_value=True)

        with (
            patch.object(svc, "executor_registry", registry),
            patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()),
        ):
            outcome = await svc.cancel_run(db, "job-1", user_id="irrelevante", como_admin=True)

        assert outcome == "cancelled"
        registry.send_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_executor_offline_nao_desfaz_o_cancelamento_local(self):
        """The notice is best-effort: the run was already closed in the database and
        the user needs the confirmation even with the executor offline."""
        from app.services import workflow_execution_service as svc

        run = _run()
        db = _db_para_cancelamento(run)
        registry = MagicMock()
        registry.send_json = AsyncMock(side_effect=RuntimeError("socket fechado"))

        with (
            patch.object(svc, "executor_registry", registry),
            patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()),
        ):
            outcome = await svc.cancel_run(db, "job-1", user_id="irrelevante", como_admin=True)

        assert outcome == "cancelled"
        assert run.status == "cancelled"

    @pytest.mark.asyncio
    async def test_dispatch_venceu_a_corrida_segue_pelo_caminho_normal(self):
        """rowcount 0: the run became 'running' in the meantime. The request to the
        executor applies, which answers "requested"."""
        from app.services import workflow_execution_service as svc

        run = _run()
        db = _db_para_cancelamento(run, rowcount=0)

        async def _refresh(_obj):
            run.status = "running"

        db.refresh = AsyncMock(side_effect=_refresh)
        registry = MagicMock()
        registry.send_json = AsyncMock(return_value=True)

        with (
            patch.object(svc, "executor_registry", registry),
            patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()),
        ):
            outcome = await svc.cancel_run(db, "job-1", user_id="irrelevante", como_admin=True)

        assert outcome == "requested"
        registry.send_json.assert_awaited_once_with(
            "ag-1", {"type": "cancel", "job_id": "job-1"},
        )


# ══════════════════════════════════════════════════════════════════════════════
# A40 — invalidation of the disabled-nodes cache across workers
# ══════════════════════════════════════════════════════════════════════════════

class _RedisFake:
    """Only the GET/INCR pair of the epoch key."""

    def __init__(self, epoca: str | None = None):
        self.epoca = epoca
        self.incrs = 0

    async def get(self, _key):
        return self.epoca

    async def incr(self, _key):
        self.incrs += 1
        self.epoca = str(int(self.epoca or "0") + 1)
        return int(self.epoca)


@pytest.fixture(autouse=True)
def _cache_limpo():
    from app.services import disabled_nodes_service as svc

    svc.invalidate_cache()
    yield
    svc.invalidate_cache()


class TestInvalidacaoEntreWorkers:

    @pytest.mark.asyncio
    async def test_epoca_estavel_nao_volta_ao_banco(self):
        """The gain that motivated the cache: nothing changes, no new SELECT."""
        from app.services import disabled_nodes_service as svc

        redis = _RedisFake("7")
        leitura = AsyncMock(return_value={})
        with (
            patch.object(svc, "_redis", return_value=redis),
            patch.object(svc, "get_config", new=leitura),
        ):
            await svc.list_disabled(MagicMock())
            await svc.list_disabled(MagicMock())

        assert leitura.await_count == 1

    @pytest.mark.asyncio
    async def test_node_desabilitado_em_outro_worker_aparece_na_leitura_seguinte(self):
        """The case that matters: the admin disabled it through worker 1; this process
        has a warm cache and a TTL far from expiring. Without the epoch, it would
        keep dispatching the node (and sending the old list in the job envelope)."""
        from app.services import disabled_nodes_service as svc

        redis = _RedisFake("7")
        mapa = {"valor": {}}

        async def _get_config(_db, _key, default=None):
            return mapa["valor"]

        with (
            patch.object(svc, "_redis", return_value=redis),
            patch.object(svc, "get_config", new=_get_config),
        ):
            assert await svc.disabled_names(MagicMock()) == set()

            # Outro worker gravou e incrementou a epoca.
            mapa["valor"] = {"SendEmail": {"reason": "incidente"}}
            redis.epoca = "8"

            assert await svc.disabled_names(MagicMock()) == {"SendEmail"}

    @pytest.mark.asyncio
    async def test_reabilitar_em_outro_worker_tambem_propaga(self):
        from app.services import disabled_nodes_service as svc

        redis = _RedisFake("1")
        mapa = {"valor": {"SendEmail": {"reason": "x"}}}

        async def _get_config(_db, _key, default=None):
            return mapa["valor"]

        with (
            patch.object(svc, "_redis", return_value=redis),
            patch.object(svc, "get_config", new=_get_config),
        ):
            assert await svc.disabled_names(MagicMock()) == {"SendEmail"}
            mapa["valor"] = {}
            redis.epoca = "2"
            assert await svc.disabled_names(MagicMock()) == set()

    @pytest.mark.asyncio
    async def test_escrita_publica_a_epoca_depois_do_commit(self):
        from app.services import disabled_nodes_service as svc

        redis = _RedisFake("3")
        gravado: dict = {}

        async def _set_config(_db, _key, value):
            gravado["value"] = value

        async def _get_config(_db, _key, default=None):
            return gravado.get("value", {})

        with (
            patch.object(svc, "_redis", return_value=redis),
            patch.object(svc, "get_config", new=_get_config),
            patch.object(svc, "set_config", new=_set_config),
        ):
            await svc.set_disabled(MagicMock(), "SendEmail", by="u1", reason="incidente")
            assert redis.incrs == 1

            await svc.set_enabled(MagicMock(), "SendEmail")
            assert redis.incrs == 2

    @pytest.mark.asyncio
    async def test_redis_fora_do_ar_degrada_para_o_ttl_local(self):
        """Redis being unavailable must not take down the dispatch: the old staleness
        ceiling applies again, with no SELECT per trigger."""
        from app.services import disabled_nodes_service as svc

        leitura = AsyncMock(return_value={})
        with (
            patch.object(svc, "_redis", side_effect=RuntimeError("Redis pool não inicializado")),
            patch.object(svc, "get_config", new=leitura),
        ):
            await svc.list_disabled(MagicMock())
            await svc.list_disabled(MagicMock())

        assert leitura.await_count == 1
