# tests/unit/test_autenticacao_de_entrada.py
"""
Quando o token do gatilho de webhook deve autenticar quem chamou.

Clicar em "Executar" num fluxo com WebhookTrigger + credencial de token
respondia 403 "Token invalido": o validador comparava o header `Authorization`
da requisicao com o token da credencial, e no botao do editor esse header leva
o JWT de SESSAO do usuario, nao o token do webhook.

O token existe para autenticar CHAMADA EXTERNA ao endpoint de webhook. No
caminho administrativo quem chama ja passou pela sessao e precisa de papel de
operator — exigir tambem o token nao protegia nada, so impedia o uso.

A distincao nao e "webhook x manual": e "este validador autentica quem chamou?".
So o do webhook olha o `request`; os outros cinco apenas conferem se a
credencial esta completa, e valem em qualquer caminho.
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


# ── O registro sabe quem autentica ───────────────────────────────────────────

def test_so_o_webhook_autentica_a_requisicao():
    """Se outro tipo entrar nesse conjunto sem querer, ele passa a ser pulado
    no disparo manual — e uma checagem de credencial some sem ninguem ver."""
    assert _AUTENTICAM_A_REQUISICAO == {"webhook_token", "WebhookAuthToken"}


# ── O caso do relato ─────────────────────────────────────────────────────────

class TestDisparoJaAutenticado:

    @pytest.mark.asyncio
    async def test_jwt_de_sessao_no_header_nao_e_mais_recusado(self):
        """O caso exato: o header existe e leva o JWT, que obviamente nao bate
        com o token do webhook."""
        await validate_credential_by_type(
            _cred_webhook(), request=_requisicao(f"Bearer {JWT_DA_SESSAO}"),
            autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_sem_requisicao_nenhuma_tambem_passa(self):
        """O agendador dispara sem `request`. Antes isso dava 401 "Request HTTP
        e necessario" em todo fluxo que combinasse cron com gatilho de webhook.
        """
        await validate_credential_by_type(
            _cred_webhook(), request=None, autenticar_entrada=False,
        )

    @pytest.mark.asyncio
    async def test_credencial_vencida_nao_bloqueia_o_operador(self):
        """Colateral aceito: a validade governa o acesso EXTERNO, nao o operador
        que ja esta autenticado."""
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
        # `expires_at` gravado sem fuso dava TypeError (500) na comparação com
        # um `now` com fuso; agora é a regra de `validade_da_credencial`.
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


# ── Os outros validadores valem em todo caminho ──────────────────────────────

class TestValidadoresQueNaoAutenticam:

    @pytest.mark.asyncio
    async def test_credencial_de_banco_incompleta_barra_ate_no_disparo_manual(self):
        """Conferir se a credencial esta completa nao tem nada a ver com
        autenticar quem chamou — pular tudo teria levado esta checagem junto."""
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


# ── A resolucao fail-closed continua em todos os caminhos ────────────────────

class TestCredencialAusente:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("autenticar", [True, False], ids=["webhook", "manual"])
    async def test_credencial_removida_barra_nos_dois_caminhos(self, autenticar):
        """E ela que pega credencial apagada; nao pode cair junto com a
        autenticacao de entrada."""
        with pytest.raises(HTTPException) as exc:
            await _validate_trigger_credentials_only(
                _definicao_com_gatilho(), request=_requisicao(f"Bearer {TOKEN}"),
                pre_resolved={},  # a credencial nao resolveu
                autenticar_entrada=autenticar,
            )
        assert exc.value.status_code == 403
        assert "não pôde ser resolvida" in exc.value.detail


# ── Ponta a ponta na funcao que o dispatch chama ─────────────────────────────

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
        """Chamador novo que esqueca o parametro exige o token, em vez de abrir
        o endpoint publico sem autenticacao."""
        with pytest.raises(HTTPException):
            await _validate_trigger_credentials_only(
                _definicao_com_gatilho(),
                request=_requisicao(f"Bearer {JWT_DA_SESSAO}"),
                pre_resolved={"cred-1": _cred_webhook()},
            )


# ── O padrao do start_analysis protege o endpoint publico ────────────────────

class TestPadraoDoDispatch:
    """O webhook_router NAO passa `autenticar_entrada` — ele conta com o padrao.

    Se o padrao virasse `False`, o endpoint publico pararia de autenticar e
    qualquer um dispararia o fluxo sabendo so a URL. Estes testes exercitam o
    `start_analysis` de verdade, sem mockar a validacao que esta sob teste.
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
        """Como o botao Executar chama — o caso do relato."""
        r = await self._disparar(
            request=_requisicao(f"Bearer {JWT_DA_SESSAO}"), autenticar_entrada=False,
        )
        assert r.id == "task-1"

    @pytest.mark.asyncio
    async def test_agendador_dispara_sem_request(self):
        r = await self._disparar(autenticar_entrada=False)
        assert r.id == "task-1"


# ── Os pontos de chamada que precisam SAIR da autenticacao ───────────────────

class TestQuemDispensaOToken:
    """Sem estes, remover o `autenticar_entrada=False` de um chamador traz o
    defeito de volta em silencio — o bug so reaparece para quem clica Executar.
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
            # `execute_workflow` tem rate limit: o slowapi recusa o que nao for
            # uma Request de verdade.
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
        # Escopo D: a rota repassa quem disparou para a resolução de credenciais.
        assert service.start_analysis.await_args.kwargs["triggered_by"] == "user-x"

    @pytest.mark.asyncio
    async def test_agendador_dispensa(self):
        from unittest.mock import AsyncMock, patch
        from app.core.async_scheduler import AsyncScheduler

        service = MagicMock()
        # O disparo agendado carrega o workflow uma vez e o repassa ao
        # start_analysis (como o webhook), em vez de refazer o SELECT lá dentro.
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
