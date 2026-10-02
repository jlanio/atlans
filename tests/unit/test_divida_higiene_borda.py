# tests/unit/test_divida_higiene_borda.py
"""Higiene de borda: o que aceitava o que não devia, ou escondia o que devia dizer.

Itens registrados como pendência nos PRs #96 e #97. Nenhum muda o
comportamento de quem já usa a API corretamente — mudam o que acontece com a
entrada torta, com o papel que faltava e com a falha silenciosa.

(O item #99.4 — `UploadUrlRequest` de `POST /drive/upload-url` — saiu junto
com a rota, removida na F1 da simplificação por não ter consumidor.)
"""
import pytest
from pydantic import ValidationError

from app.schemas.workflow import WorkflowDuplicate, WorkflowMove


# ── #96.5: WorkflowDuplicate sem extra="forbid" ───────────────────────────────


class TestWorkflowDuplicate:

    def test_nome_opcional_continua_opcional(self):
        assert WorkflowDuplicate().name is None
        assert WorkflowDuplicate(name="Cópia").name == "Cópia"

    def test_campo_desconhecido_e_recusado(self):
        """`workspace_id` era descartado em silêncio — e a cópia fica no mesmo
        workspace do original, então quem o mandou achava que mudou de lugar."""
        with pytest.raises(ValidationError):
            WorkflowDuplicate(name="Cópia", workspace_id="ws-outro")

    def test_alinhado_com_o_irmao_WorkflowMove(self):
        """O irmão já era estrito; a divergência é que estava registrada."""
        assert WorkflowDuplicate.model_config.get("extra") == "forbid"
        assert WorkflowMove.model_config.get("extra") == "forbid"


# ── #97.3: GET /pins era a única das três rotas de pin sem papel ──────────────


def test_a_rota_de_listar_pins_exige_papel():
    """As irmãs `PUT`/`DELETE` pedem `editor`; esta não pedia nada.

    E a tool `list_pins` do MCP já exigia `viewer` (`app/mcp/guardas.py`), então
    a MESMA leitura respondia com duas réguas conforme a porta de entrada.

    O papel é declarado na dependência da rota (`workflow_com_papel`), e é essa
    declaração que se prende aqui — lida da rota registrada, sem montar a app.
    O 403 de cada papel abaixo do mínimo é exercitado pela matriz de
    `test_papel_minimo_das_rotas.py`.
    """
    from app.api.routers import workflows_router

    (rota,) = [
        r for r in workflows_router.router.routes
        if r.path == "/workflows/{id_hash}/pins" and "GET" in r.methods
    ]
    papeis = [
        d.call.papel_minimo for d in rota.dependant.dependencies
        if hasattr(d.call, "papel_minimo")
    ]
    assert papeis == ["viewer"], "sem o papel declarado não há o que checar"


def test_a_regua_da_rota_e_a_mesma_da_tool():
    """Divergir aqui é o defeito original, não uma escolha."""
    from app.mcp.guardas import GUARDAS

    assert GUARDAS["list_pins"].papel == "viewer"


# ── #96.2: a cópia nascia sem dono ───────────────────────────────────────────


def test_duplicar_exige_a_autoria_de_quem_copiou():
    """`duplicated_by` existe para a REST parar de criar fluxo órfão.

    A tool MCP já carimbava à mão; agora as duas portas usam o mesmo parâmetro,
    e o carimbo mora num lugar só. Era opcional "para chamador interno sem
    usuário" — que nunca existiu —, e sem ele a cópia também pulava a guarda de
    credenciais (SEG-12). Passou a ser obrigatório; a regra das quatro escritas
    está em test_workflow_credencial_guard.py.
    """
    import inspect

    from app.services.workflow_service import WorkflowService

    parametro = inspect.signature(WorkflowService.duplicate_workflow).parameters["duplicated_by"]
    assert parametro.kind is inspect.Parameter.KEYWORD_ONLY
    assert parametro.default is inspect.Parameter.empty


# ── #96.4: restore_version engolia falha de agendamento ──────────────────────


def test_restaurar_versao_devolve_os_avisos_de_agendamento():
    """Sem isto, restaurar uma versão com cron quebrado parecia sucesso.

    O sintoma de agendamento que não sincronizou é o SILÊNCIO: nada falha, a
    rotina só deixa de acontecer. `update_workflow` já devolvia
    `schedule_notices`; `restore_version` não.
    """
    import inspect

    from app.services import workflow_version_service

    fonte = inspect.getsource(workflow_version_service.restore_version)
    assert "schedule_notices" in fonte
    assert "wf.schedule_notices" in fonte, "o atributo transiente precisa chegar ao objeto"
