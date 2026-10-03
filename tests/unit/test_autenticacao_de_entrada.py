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
    _AUTHENTICATE_REQUEST,
    validate_credential_by_type,
)
from app.services.workflow_execution_service import _validate_trigger_credentials_only

TOKEN = "token-do-webhook"
SESSION_JWT = "jwt.de.sessao.do.usuario"


def _request(authorization: str | None) -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": authorization} if authorization else {}
    return req


def _cred_webhook(**extra) -> dict:
    return {"type": "webhook_token", "token": TOKEN, **extra}


def _definition_with_trigger(cred_id="cred-1") -> dict:
    return {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "WebhookTrigger",
             "properties": {"credential_id": cred_id}},
        ],
        "edges": [],
    }


# ── The registry knows who authenticates ─────────────────────────────────────

def test_only_the_webhook_authenticates_the_request():
    """If another type gets into this set by accident, it starts being skipped on
    manual triggering — and a credential check vanishes without anyone seeing."""
    assert _AUTHENTICATE_REQUEST == {"webhook_token", "WebhookAuthToken"}


# ── The reported case ────────────────────────────────────────────────────────

class TestAlreadyAuthenticatedTrigger:

    @pytest.mark.asyncio
    async def test_session_jwt_in_header_is_no_longer_rejected(self):
        """The exact case: the header exists and carries the JWT, which obviously
        doesn't match the webhook token."""
        await validate_credential_by_type(
            _cred_webhook(), request=_request(f"Bearer {SESSION_JWT}"),
            autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_without_any_request_also_passes(self):
        """The scheduler triggers without a `request`. Before, that gave 401 "Request
        HTTP e necessario" on every workflow that combined cron with a webhook trigger.
        """
        await validate_credential_by_type(
            _cred_webhook(), request=None, autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_expired_credential_does_not_block_the_operator(self):
        """Accepted side effect: the expiry governs EXTERNAL access, not the operator
        who is already authenticated."""
        await validate_credential_by_type(
            _cred_webhook(expires_at="2020-01-01T00:00:00Z"),
            request=_request(f"Bearer {SESSION_JWT}"),
            autenticar_entrada=False,
        )


# ── O endpoint de webhook continua fechado ───────────────────────────────────

class TestEndpointDeWebhook:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expires_at, status", [
        ("2020-01-01T00:00:00Z", 403), ("2020-01-01T00:00:00", 403), ("2099-01-01T00:00:00-03:00", None),
        ("lixo", 500),
    ])
    async def test_validity_is_the_same_rule_as_resolution(self, expires_at, status):
        # `expires_at` stored without a time zone gave a TypeError (500) when compared
        # with a tz-aware `now`; now it is the `credential_validity` rule.
        chamada = validate_credential_by_type(
            _cred_webhook(expires_at=expires_at), request=_request(f"Bearer {TOKEN}"), autenticar_entrada=True,
        )
        if status is None:
            await chamada
            return
        with pytest.raises(HTTPException) as exc:
            await chamada
        assert exc.value.status_code == status

    @pytest.mark.asyncio
    async def test_wrong_token_is_still_rejected(self):
        with pytest.raises(HTTPException) as exc:
            await validate_credential_by_type(
                _cred_webhook(), request=_request("Bearer token-errado"),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_without_header_is_still_rejected(self):
        with pytest.raises(HTTPException) as exc:
            await validate_credential_by_type(_cred_webhook(), request=_request(None))
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_right_token_passes(self):
        await validate_credential_by_type(
            _cred_webhook(), request=_request(f"Bearer {TOKEN}"),
        )


# ── The other validators apply on every path ─────────────────────────────────

class TestValidatorsThatDoNotAuthenticate:

    @pytest.mark.asyncio
    async def test_incomplete_db_credential_blocks_even_on_manual_trigger(self):
        """Checking whether the credential is complete has nothing to do with
        authenticating the caller — skipping everything would have taken this check along."""
        with pytest.raises(HTTPException) as exc:
            await validate_credential_by_type(
                {"type": "postgresql"}, request=None, autenticar_entrada=False,
            )
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_complete_db_credential_passes(self):
        await validate_credential_by_type(
            {"type": "postgresql", "connectionString": "dsn://x"},
            request=None, autenticar_entrada=False,
        )


# ── Fail-closed resolution still applies on every path ───────────────────────

class TestMissingCredential:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("autenticar", [True, False], ids=["webhook", "manual"])
    async def test_removed_credential_blocks_on_both_paths(self, autenticar):
        """It is what catches a deleted credential; it must not go down together with
        inbound authentication."""
        with pytest.raises(HTTPException) as exc:
            await _validate_trigger_credentials_only(
                _definition_with_trigger(), request=_request(f"Bearer {TOKEN}"),
                pre_resolved={},  # the credential did not resolve
                autenticar_entrada=autenticar,
            )
        assert exc.value.status_code == 403
        assert "não pôde ser resolvida" in exc.value.detail


# ── End to end on the function the dispatch calls ────────────────────────────

class TestTriggerValidation:

    @pytest.mark.asyncio
    async def test_manual_passes_with_the_jwt_in_header(self):
        await _validate_trigger_credentials_only(
            _definition_with_trigger(),
            request=_request(f"Bearer {SESSION_JWT}"),
            pre_resolved={"cred-1": _cred_webhook()},
            autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_webhook_rejects_the_same_scenario(self):
        with pytest.raises(HTTPException) as exc:
            await _validate_trigger_credentials_only(
                _definition_with_trigger(),
                request=_request(f"Bearer {SESSION_JWT}"),
                pre_resolved={"cred-1": _cred_webhook()},
                autenticar_entrada=True,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_the_default_is_to_authenticate(self):
        """A new caller that forgets the parameter requires the token, instead of opening
        the public endpoint without authentication."""
        with pytest.raises(HTTPException):
            await _validate_trigger_credentials_only(
                _definition_with_trigger(),
                request=_request(f"Bearer {SESSION_JWT}"),
                pre_resolved={"cred-1": _cred_webhook()},
            )


# ── O padrao do start_analysis protege o endpoint publico ────────────────────

class TestDispatchDefault:
    """The webhook_router does NOT pass `autenticar_entrada` — it relies on the default.

    If the default became `False`, the public endpoint would stop authenticating and
    anyone could trigger the workflow knowing only the URL. These tests exercise
    the real `start_analysis`, without mocking the validation under test.
    """

    def _service(self, definicao, cred):
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

        service, cred = self._service(_definition_with_trigger(), _cred_webhook())
        with (
            patch("app.services.disabled_nodes_service.disabled_names",
                  new=AsyncMock(return_value=set())),
            patch("app.services.workflow_service.resolve_credentials_from_ids",
                  new=AsyncMock(return_value={"cred-1": cred})),
        ):
            return await service.start_analysis("wf-1", inputs={}, **kwargs)

    @pytest.mark.asyncio
    async def test_without_the_parameter_the_wrong_token_is_rejected(self):
        """Exatamente como o webhook_router chama."""
        with pytest.raises(HTTPException) as exc:
            await self._disparar(request=_request(f"Bearer {SESSION_JWT}"))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_without_the_parameter_the_right_token_passes(self):
        r = await self._disparar(request=_request(f"Bearer {TOKEN}"))
        assert r.id == "task-1"

    @pytest.mark.asyncio
    async def test_with_authenticate_input_false_the_jwt_passes(self):
        """How the Run button calls it — the reported case."""
        r = await self._disparar(
            request=_request(f"Bearer {SESSION_JWT}"), autenticar_entrada=False,
        )
        assert r.id == "task-1"

    @pytest.mark.asyncio
    async def test_scheduler_triggers_without_request(self):
        r = await self._disparar(autenticar_entrada=False)
        assert r.id == "task-1"


# ── The call sites that must OPT OUT of authentication ───────────────────────

class TestWhoSkipsTheToken:
    """Without these, removing `autenticar_entrada=False` from a caller brings the
    defect back silently — the bug only reappears for whoever clicks Run.
    """

    @pytest.mark.asyncio
    async def test_run_button_skips(self):
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
    async def test_scheduler_skips(self):
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
