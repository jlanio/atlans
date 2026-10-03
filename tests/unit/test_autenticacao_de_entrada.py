# tests/unit/test_autenticacao_de_entrada.py
"""
When the webhook trigger's token should authenticate the caller.

Clicking "Executar" (Run) on a workflow with WebhookTrigger + a token credential
responded 403 "Token invalido": the validator compared the request's
`Authorization` header with the credential's token, and on the editor button
that header carries the user's SESSION JWT, not the webhook token.

The token exists to authenticate an EXTERNAL CALL to the webhook endpoint. On the
administrative path the caller has already gone through the session and needs
the operator role — also requiring the token protected nothing, it only blocked
use.

The distinction is not "webhook vs manual": it is "does this validator
authenticate the caller?". Only the webhook one looks at the `request`; the other
five only check whether the credential is complete, and apply on any path.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.authorization.credential_validators import (
    _AUTENTICAM_A_REQUISICAO,
    validate_credential_by_type,
)
from app.services.workflow_execution_service import _validate_trigger_credentials_only

TOKEN = "token-do-webhook"
JWT_DA_SESSAO = "jwt.de.sessao.do.usuario"


def _requisicao(authorization: str | None) -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": authorization} if authorization else {}
    return req


def _cred_webhook(**extra) -> dict:
    return {"type": "webhook_token", "token": TOKEN, **extra}


def _definicao_com_gatilho(cred_id="cred-1") -> dict:
    return {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "WebhookTrigger",
             "properties": {"credential_id": cred_id}},
        ],
        "edges": [],
    }


# ── The registry knows who authenticates ─────────────────────────────────────

def test_so_o_webhook_autentica_a_requisicao():
    """If another type gets into this set by accident, it starts being skipped on
    manual triggering — and a credential check vanishes without anyone seeing."""
    assert _AUTENTICAM_A_REQUISICAO == {"webhook_token", "WebhookAuthToken"}


# ── The reported case ────────────────────────────────────────────────────────

class TestDisparoJaAutenticado:

    @pytest.mark.asyncio
    async def test_jwt_de_sessao_no_header_nao_e_mais_recusado(self):
        """The exact case: the header exists and carries the JWT, which obviously
        doesn't match the webhook token."""
        await validate_credential_by_type(
            _cred_webhook(), request=_requisicao(f"Bearer {JWT_DA_SESSAO}"),
            autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_sem_requisicao_nenhuma_tambem_passa(self):
        """The scheduler triggers without a `request`. Before, that gave 401 "Request
        HTTP e necessario" on every workflow that combined cron with a webhook trigger.
        """
        await validate_credential_by_type(
            _cred_webhook(), request=None, autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_credencial_vencida_nao_bloqueia_o_operador(self):
        """Accepted side effect: the expiry governs EXTERNAL access, not the operator
        who is already authenticated."""
        await validate_credential_by_type(
            _cred_webhook(expires_at="2020-01-01T00:00:00Z"),
            request=_requisicao(f"Bearer {JWT_DA_SESSAO}"),
            autenticar_entrada=False,
        )


# ── O endpoint de webhook continua fechado ───────────────────────────────────

class TestEndpointDeWebhook:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expires_at, status", [
        ("2020-01-01T00:00:00Z", 403), ("2020-01-01T00:00:00", 403), ("2099-01-01T00:00:00-03:00", None),
        ("lixo", 500),
    ])
    async def test_a_validade_e_a_mesma_regra_da_resolucao(self, expires_at, status):
        # `expires_at` stored without a time zone gave a TypeError (500) when compared
        # with a tz-aware `now`; now it is the `validade_da_credencial` rule.
        chamada = validate_credential_by_type(
            _cred_webhook(expires_at=expires_at), request=_requisicao(f"Bearer {TOKEN}"), autenticar_entrada=True,
        )
        if status is None:
            await chamada
            return
        with pytest.raises(HTTPException) as exc:
            await chamada
        assert exc.value.status_code == status

    @pytest.mark.asyncio
    async def test_token_errado_continua_recusado(self):
        with pytest.raises(HTTPException) as exc:
            await validate_credential_by_type(
                _cred_webhook(), request=_requisicao("Bearer token-errado"),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_sem_header_continua_recusado(self):
        with pytest.raises(HTTPException) as exc:
            await validate_credential_by_type(_cred_webhook(), request=_requisicao(None))
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_certo_passa(self):
        await validate_credential_by_type(
            _cred_webhook(), request=_requisicao(f"Bearer {TOKEN}"),
        )


# ── The other validators apply on every path ─────────────────────────────────

class TestValidadoresQueNaoAutenticam:

    @pytest.mark.asyncio
    async def test_credencial_de_banco_incompleta_barra_ate_no_disparo_manual(self):
        """Checking whether the credential is complete has nothing to do with
        authenticating the caller — skipping everything would have taken this check along."""
        with pytest.raises(HTTPException) as exc:
            await validate_credential_by_type(
                {"type": "postgresql"}, request=None, autenticar_entrada=False,
            )
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_credencial_de_banco_completa_passa(self):
        await validate_credential_by_type(
            {"type": "postgresql", "connectionString": "dsn://x"},
            request=None, autenticar_entrada=False,
        )


# ── Fail-closed resolution still applies on every path ───────────────────────

class TestCredencialAusente:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("autenticar", [True, False], ids=["webhook", "manual"])
    async def test_credencial_removida_barra_nos_dois_caminhos(self, autenticar):
        """It is what catches a deleted credential; it must not go down together with
        inbound authentication."""
        with pytest.raises(HTTPException) as exc:
            await _validate_trigger_credentials_only(
                _definicao_com_gatilho(), request=_requisicao(f"Bearer {TOKEN}"),
                pre_resolved={},  # the credential did not resolve
                autenticar_entrada=autenticar,
            )
        assert exc.value.status_code == 403
        assert "não pôde ser resolvida" in exc.value.detail


# ── End to end on the function the dispatch calls ────────────────────────────

class TestValidacaoDeTrigger:

    @pytest.mark.asyncio
    async def test_manual_passa_com_o_jwt_no_header(self):
        await _validate_trigger_credentials_only(
            _definicao_com_gatilho(),
            request=_requisicao(f"Bearer {JWT_DA_SESSAO}"),
            pre_resolved={"cred-1": _cred_webhook()},
            autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_webhook_recusa_o_mesmo_cenario(self):
        with pytest.raises(HTTPException) as exc:
            await _validate_trigger_credentials_only(
                _definicao_com_gatilho(),
                request=_requisicao(f"Bearer {JWT_DA_SESSAO}"),
                pre_resolved={"cred-1": _cred_webhook()},
                autenticar_entrada=True,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_o_padrao_e_autenticar(self):
        """A new caller that forgets the parameter requires the token, instead of opening
        the public endpoint without authentication."""
        with pytest.raises(HTTPException):
            await _validate_trigger_credentials_only(
                _definicao_com_gatilho(),
                request=_requisicao(f"Bearer {JWT_DA_SESSAO}"),
                pre_resolved={"cred-1": _cred_webhook()},
            )


# ── O padrao do start_analysis protege o endpoint publico ────────────────────

class TestPadraoDoDispatch:
    """The webhook_router does NOT pass `autenticar_entrada` — it relies on the default.

    If the default became `False`, the public endpoint would stop authenticating and
    anyone could trigger the workflow knowing only the URL. These tests exercise
    the real `start_analysis`, without mocking the validation under test.
    """

    def _servico(self, definicao, cred):
        from unittest.mock import AsyncMock
        from app.services.workflow_service import WorkflowService, DispatchResult

        wf = MagicMock()
        wf.id_hash, wf.workspace_id, wf.flag_ative = "wf-1", "ws-1", True
        wf.pinned_outputs = wf.pin_metadata = None
        wf.definition = definicao

        db = MagicMock()
        escala = MagicMock()
        escala.all = MagicMock(return_value=[])
        res = MagicMock()
        res.scalars = MagicMock(return_value=escala)
        db.execute = AsyncMock(return_value=res)

        service = WorkflowService(db)
        service.crud = MagicMock(db=db)
        service._load_workflow = AsyncMock(return_value=(wf, wf.definition))
        service._resolve_candidates = AsyncMock(return_value=[MagicMock()])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="task-1"))
        return service, cred

    async def _disparar(self, **kwargs):
        from unittest.mock import AsyncMock, patch

        service, cred = self._servico(_definicao_com_gatilho(), _cred_webhook())
        with (
            patch("app.services.disabled_nodes_service.disabled_names",
                  new=AsyncMock(return_value=set())),
            patch("app.services.workflow_service.resolve_credentials_from_ids",
                  new=AsyncMock(return_value={"cred-1": cred})),
        ):
            return await service.start_analysis("wf-1", inputs={}, **kwargs)

    @pytest.mark.asyncio
    async def test_sem_o_parametro_o_token_errado_e_recusado(self):
        """Exatamente como o webhook_router chama."""
        with pytest.raises(HTTPException) as exc:
            await self._disparar(request=_requisicao(f"Bearer {JWT_DA_SESSAO}"))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_sem_o_parametro_o_token_certo_passa(self):
        r = await self._disparar(request=_requisicao(f"Bearer {TOKEN}"))
        assert r.id == "task-1"

    @pytest.mark.asyncio
    async def test_com_autenticar_entrada_false_o_jwt_passa(self):
        """How the Run button calls it — the reported case."""
        r = await self._disparar(
            request=_requisicao(f"Bearer {JWT_DA_SESSAO}"), autenticar_entrada=False,
        )
        assert r.id == "task-1"

    @pytest.mark.asyncio
    async def test_agendador_dispara_sem_request(self):
        r = await self._disparar(autenticar_entrada=False)
        assert r.id == "task-1"


# ── The call sites that must OPT OUT of authentication ───────────────────────

class TestQuemDispensaOToken:
    """Without these, removing `autenticar_entrada=False` from a caller brings the
    defect back silently — the bug only reappears for whoever clicks Run.
    """

    @pytest.mark.asyncio
    async def test_botao_executar_dispensa(self):
        from unittest.mock import AsyncMock
        from starlette.requests import Request as RequisicaoReal
        from app.api.routers.workflows_router import ExecutePayload, execute_workflow

        service = MagicMock()
        service.start_analysis = AsyncMock(return_value=MagicMock(id="task-1"))
        wf = MagicMock()
        wf.id_hash = "wf-1"

        await execute_workflow(
            # `execute_workflow` has a rate limit: slowapi rejects anything that isn't
            # a real Request.
            request=RequisicaoReal({
                "type": "http", "method": "POST", "path": "/x",
                "headers": [], "client": ("127.0.0.1", 0), "query_string": b"",
            }),
            payload=ExecutePayload(),
            service=service,
            wf=wf,
            current_user=MagicMock(id_hash="user-x"),
            idempotency_key=None,
        )

        assert service.start_analysis.await_args.kwargs["autenticar_entrada"] is False
        # Scope D: the route passes who triggered it on to credential resolution.
        assert service.start_analysis.await_args.kwargs["triggered_by"] == "user-x"

    @pytest.mark.asyncio
    async def test_agendador_dispensa(self):
        from unittest.mock import AsyncMock, patch
        from app.core.async_scheduler import AsyncScheduler

        service = MagicMock()
        # The scheduled trigger loads the workflow once and passes it on to
        # start_analysis (like the webhook), instead of redoing the SELECT in there.
        service.get_workflow_by_hash = AsyncMock(return_value=MagicMock(id_hash="wf-1", workspace_id="ws-1"))
        service.start_analysis = AsyncMock(return_value=MagicMock(id="task-1"))
        sessao = MagicMock()
        sessao.__aenter__ = AsyncMock(return_value=sessao)
        sessao.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.core.async_scheduler.AsyncSessionLocal", return_value=sessao),
            patch("app.services.workflow_service.WorkflowService", return_value=service),
        ):
            await AsyncScheduler._fire_workflow(MagicMock(), "wf-1")

        assert service.start_analysis.await_args.kwargs["autenticar_entrada"] is False
