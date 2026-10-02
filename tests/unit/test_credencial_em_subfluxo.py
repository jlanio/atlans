"""
Credencial de banco usada DENTRO de um sub-fluxo.

O executor não tem DB: o servidor troca `credential_id` pelo DSN ao montar o
envelope e remove o id. Isso só acontecia na definition raiz — a cadeia de
sub-fluxos viajava crua no mesmo envelope. Um nó de banco dentro de um
sub-fluxo chegava ao executor com o id e sem conexão, e morria com
"'connectionString' é obrigatório (deve ser resolvido antes da execução)":
uma frase que descreve um problema do servidor como se fosse configuração do nó.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.workflow_execution_service import (
    _collect_credential_ids,
    _dispatch_job,
)
from app.services.workflow_service import WorkflowService, DispatchResult
from flow.utils.credencial import obter_conexao

CRED_PAI = "cred-do-pai"
CRED_FILHO = "cred-do-filho"


def _def_pai(child_hash="child-1"):
    return {
        "nodes": [
            {"id": "trigger-1", "name": "WebhookTrigger", "properties": {}},
            {"id": "sub-1", "name": "SubWorkflow",
             "properties": {"workflowHash": child_hash, "inputsMapping": {}}},
        ],
        "edges": [],
    }


def _def_filho():
    return {
        "nodes": [
            {"id": "in", "name": "SubWorkflowInput"},
            {"id": "db", "name": "DatabaseSpatialQuery",
             "properties": {"credential_id": CRED_FILHO, "query": "SELECT 1"}},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }


# ── coleta dos ids ──────────────────────────────────────────────────────────

class TestColetaDeIds:

    def test_junta_as_credenciais_do_pai_e_do_filho(self):
        pai = _def_pai()
        pai["nodes"].append(
            {"id": "db-pai", "name": "DatabaseQuery",
             "properties": {"credential_id": CRED_PAI}}
        )
        ids = _collect_credential_ids(pai, _def_filho())
        assert set(ids) == {CRED_PAI, CRED_FILHO}

    def test_so_a_raiz_continua_funcionando(self):
        # A assinatura passou a aceitar várias definitions; a chamada com uma só
        # é a de todo o resto do código.
        assert _collect_credential_ids(_def_filho()) == [CRED_FILHO]

    def test_tolera_definition_vazia_ou_nula(self):
        assert _collect_credential_ids({}, None, _def_filho()) == [CRED_FILHO]


# ── resolução no dispatch ───────────────────────────────────────────────────

class TestResolucaoNoDispatch:

    @pytest.mark.asyncio
    async def test_a_credencial_do_filho_e_resolvida(self):
        """Sem isto, `pre_resolved` não continha a credencial do filho e a
        injeção não tinha o que injetar, mesmo depois de passar a percorrer
        os sub-fluxos."""
        pai = MagicMock()
        pai.id_hash, pai.workspace_id, pai.flag_ative = "parent-A", "ws-test", True
        pai.pinned_outputs = pai.pin_metadata = None
        pai.definition = _def_pai()

        filho = MagicMock()
        filho.id_hash, filho.workspace_id, filho.flag_ative = "child-1", "ws-test", True
        filho.definition = _def_filho()

        scalars = MagicMock()
        scalars.all = MagicMock(return_value=[filho])
        res = MagicMock()
        res.scalars = MagicMock(return_value=scalars)
        db = MagicMock()
        db.execute = AsyncMock(return_value=res)

        service = WorkflowService(db)
        service.crud = MagicMock(db=db)
        service._load_workflow = AsyncMock(return_value=(pai, pai.definition))
        service._resolve_candidates = AsyncMock(return_value=[MagicMock()])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="task-1"))

        resolver = AsyncMock(return_value={CRED_FILHO: {"connectionString": "dsn://x"}})
        with (
            patch("app.services.disabled_nodes_service.disabled_names",
                  new=AsyncMock(return_value=set())),
            patch("app.services.workflow_service.resolve_credentials_from_ids", new=resolver),
            patch("app.services.workflow_service._validate_trigger_credentials_only",
                  new=AsyncMock()),
        ):
            await service.start_analysis(pai.id_hash, inputs={})

        resolver.assert_awaited()
        pedidos = resolver.await_args.args[0]
        assert CRED_FILHO in pedidos, (
            f"a credencial do sub-fluxo não foi pedida ao resolver: {pedidos}"
        )

    @pytest.mark.asyncio
    async def test_o_envelope_leva_o_dsn_dentro_do_subfluxo(self):
        """O que o executor de fato recebe: `connectionString` no nó do filho,
        e `credential_id` removido."""
        wf = MagicMock()
        wf.id_hash, wf.workspace_id = "parent-A", "ws-test"
        wf.pinned_outputs = wf.pin_metadata = None

        # O UPDATE pending->running e construido com o modelo real, entao ele
        # nao pode ser trocado por mock; `db` inteiro e de mentira e nada chega
        # ao banco.
        transicao = MagicMock()
        transicao.rowcount = 1
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock(return_value=transicao)
        capturado: dict = {}

        def _capturar(**kwargs):
            # O payload chega ja serializado: o dispatch faz o json.dumps uma
            # vez so, fora do laco de candidatos.
            import json as _json
            capturado.update(_json.loads(kwargs["payload"]))
            return {"job": "cifrado"}

        agente = MagicMock()
        agente.id_hash = "exec-1"
        agente.name = "exec"
        agente.public_key = "pk"

        with (
            patch("app.services.workflow_execution_service.inject_credentials",
                  new=AsyncMock(side_effect=_injetar_falso)),
            patch("app.services.workflow_execution_service.build_job_message",
                  new=MagicMock(side_effect=_capturar)),
            patch("app.services.workflow_execution_service.executor_registry.send_job",
                  new=AsyncMock(return_value=True)),
        ):
            await _dispatch_job(
                wf, _def_pai(), [agente], None, False, db=db,
                pre_resolved={CRED_FILHO: {"connectionString": "dsn://filho"}},
                subworkflow_definitions={"child-1": _def_filho()},
            )

        no_db = capturado["subworkflow_definitions"]["child-1"]["nodes"][1]
        props = no_db["properties"]
        assert props.get("connectionString") == "dsn://filho", (
            "o sub-fluxo foi para o envelope sem a conexão resolvida"
        )
        assert "credential_id" not in props, (
            "o id da credencial não deveria viajar junto do DSN"
        )


async def _injetar_falso(definition, pre_resolved=None, **_):
    """Mesmo contrato de `inject_credentials`, sem tocar o banco."""
    from app.services.credential_resolver import inject_credentials
    return await inject_credentials(definition, pre_resolved=pre_resolved or {})


# ── a mensagem que o operador lê ────────────────────────────────────────────

class TestMensagemDoNo:

    def test_devolve_o_dsn_quando_resolvido(self):
        assert obter_conexao({"connectionString": " dsn://x "}) == "dsn://x"

    def test_credencial_escolhida_mas_nao_resolvida_culpa_o_servidor(self):
        # `credential_id` sobrevivendo é o rastro: `inject_credentials` o remove
        # justamente ao injetar o DSN.
        with pytest.raises(ValueError) as exc:
            obter_conexao({"credential_id": CRED_FILHO})
        msg = str(exc.value)
        assert "servidor não a resolveu" in msg
        assert "Escolha uma" not in msg, "manda configurar algo que já está configurado"

    def test_sem_credencial_nenhuma_manda_configurar_o_no(self):
        with pytest.raises(ValueError) as exc:
            obter_conexao({})
        msg = str(exc.value)
        assert "Nenhuma credencial" in msg and "Credencial" in msg
        assert "servidor" not in msg, "acusa o servidor de um erro de configuração"

    def test_string_em_branco_conta_como_ausente(self):
        with pytest.raises(ValueError, match="Nenhuma credencial"):
            obter_conexao({"connectionString": "   ", "credential_id": "  "})
