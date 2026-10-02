# tests/unit/test_dispatch_bordas_srv.py
"""
Bordas do despacho que as otimizacoes de latencia expuseram.

Tres invariantes que nenhum teste cobria:

A14 — o fail-fast de "nenhum executor disponivel" (503) NAO pode preceder a
      autenticacao do chamador de webhook: um anonimo passaria a sondar o estado
      da frota de execucao do tenant antes de qualquer 401/403.

A15 — 'pending' nao prova que o job nao saiu. Se o worker que despachou morre
      entre o `send_job` e o commit de pending->running, o run fica 'pending'
      com o executor rodando o fluxo de verdade; cancelar tem de avisar o host
      gravado, senao a API responde "cancelado" e o fluxo termina mandando
      e-mails e gravando dados.

A40 — o cache de nodes desabilitados e por PROCESSO e a producao roda 4 workers:
      sem a epoca no Redis, um node desabilitado pelo admin continua sendo
      despachado pelos outros workers (e vai no envelope do job) ate o TTL vencer.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import NoExecutorAvailableError

TOKEN = "token-do-webhook"


# ══════════════════════════════════════════════════════════════════════════════
# A14 — precedencia: autenticar antes de falar sobre a frota
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
    """WorkflowService cujo pool de executores esta vazio (503 garantido)."""
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
        # O dispatch importa dentro da funcao — o patch tem de ser na origem.
        patch("flow.utils.workflow_contract.collect_subworkflow_definitions_recursive",
              new=AsyncMock(return_value={})),
        patch("app.services.workflow_service.resolve_credentials_from_ids",
              new=resolver_credenciais),
    ):
        return await service.start_analysis("wf-1", inputs={}, **kwargs)


class TestOrdemAutenticacaoAntesDoFailFast:

    @pytest.mark.asyncio
    async def test_anonimo_recebe_401_e_nao_sonda_a_frota(self):
        """Sem header nenhum: 401 do token, e `_resolve_candidates` nem roda.

        Antes o mesmo chamador levava 503 com a mensagem literal sobre o pool
        de executores — oraculo sobre a infraestrutura do tenant.
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
        """O fail-fast nao foi removido — so reposicionado depois do token."""
        service = _servico_sem_executor()
        resolver = AsyncMock(return_value={"cred-1": {"type": "webhook_token", "token": TOKEN}})

        with pytest.raises(NoExecutorAvailableError):
            await _disparar_sem_executor(
                service, resolver, request=_requisicao(f"Bearer {TOKEN}"),
            )

        assert service._resolve_candidates.await_count == 1
        # E antes do despacho, obviamente.
        assert service._dispatch_job.await_count == 0

    @pytest.mark.asyncio
    async def test_disparo_ja_autenticado_aborta_antes_de_resolver_credenciais(self):
        """O ganho de latencia preservado: quem ja se autenticou (botao
        Executar, retry, cron) recebe o 503 sem o servidor colecionar sub-fluxos
        nem decifrar credencial nenhuma."""
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
        """O cenario do worker morto entre `send_job` e o commit: o executor JA
        tem o job, o run ficou 'pending' para sempre. Sem este aviso a API
        responde "cancelado" e o fluxo roda ate o fim."""
        from app.services import workflow_execution_service as svc

        run = _run()
        db = _db_para_cancelamento(run)
        registry = MagicMock()
        registry.send_json = AsyncMock(return_value=True)

        with (
            patch.object(svc, "executor_registry", registry),
            patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()),
        ):
            # `como_admin=True` não é atalho preguiçoso: estes casos são sobre a MECÂNICA
            # do cancelamento (pendente × entregue, corrida com o dispatch), e montar
            # associação de workspace em cada um só afastaria o teste do que ele mede.
            # A autorização tem cobertura própria em test_fixes_seguranca_opcao_c.py.
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
        """O aviso e best-effort: o run ja foi fechado no banco e o usuario
        precisa da confirmacao mesmo com o executor fora do ar."""
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
        """rowcount 0: o run virou 'running' no meio. Vale o pedido ao executor,
        que responde "requested"."""
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
# A40 — invalidacao do cache de nodes desabilitados entre workers
# ══════════════════════════════════════════════════════════════════════════════

class _RedisFake:
    """So o par GET/INCR da chave de epoca."""

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
        """O ganho que motivou o cache: nada muda, nenhum SELECT novo."""
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
        """O caso que importa: o admin desabilitou pelo worker 1; este processo
        tem cache quente e TTL longe de vencer. Sem a epoca, ele seguiria
        despachando o node (e mandando a lista velha no envelope do job)."""
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
        """Redis indisponivel nao pode derrubar o dispatch: volta a valer o teto
        de defasagem antigo, sem SELECT por disparo."""
        from app.services import disabled_nodes_service as svc

        leitura = AsyncMock(return_value={})
        with (
            patch.object(svc, "_redis", side_effect=RuntimeError("Redis pool não inicializado")),
            patch.object(svc, "get_config", new=leitura),
        ):
            await svc.list_disabled(MagicMock())
            await svc.list_disabled(MagicMock())

        assert leitura.await_count == 1
