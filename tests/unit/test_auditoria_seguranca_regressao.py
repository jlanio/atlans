"""
Regressoes da auditoria de seguranca.

Um teste por achado corrigido. Cada um falha se a correcao for revertida —
varias delas sao de uma linha so, exatamente o tipo que volta sem querer num
merge. O que estes testes protegem:

C1  JinjaBranch avaliava a expressao do usuario num `Environment` comum.
C3  `WorkflowUpdate` aceitava `workspace_id`, permitindo mover o workflow de tenant.
C4  A `s3_key` do executor virava `Artifact.s3_key` sem validacao.
A3  Credencial com `owner_id` NULL era acessivel a qualquer autenticado.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError


# ── C1: sandbox do JinjaBranch ────────────────────────────────────────────────

# Cadeias classicas de escape de sandbox Jinja2. Todas RENDERIZAVAM antes da
# correcao; a do `cycler` chegava a executar comando no processo do executor.
_PAYLOADS_ESCAPE = [
    "{% set x = cycler.__init__.__globals__ %}{{ x }}",
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    "{{ ''|attr('__class__') }}",
    "{{ self.__init__.__globals__ }}",
]


@pytest.mark.parametrize("payload", _PAYLOADS_ESCAPE)
@pytest.mark.asyncio
async def test_c1_jinja_branch_bloqueia_escape_de_sandbox(payload):
    from flow.nodes.control.jinja_branch import JinjaBranchNode

    node = JinjaBranchNode.__new__(JinjaBranchNode)
    node.parameters = {"expression": payload}
    node.node_id = "n1"
    node.validate = lambda: None

    with pytest.raises((ValueError, RuntimeError)):
        await node.execute({})


@pytest.mark.parametrize(
    "expressao,inputs,esperado",
    [
        ("{{ inputs.count > 10 }}", {"count": 42}, True),
        ("{{ inputs.count > 10 }}", {"count": 3}, False),
        ("{{ value is not none }}", {"v": "x"}, True),
        ("True", {}, True),
    ],
)
@pytest.mark.asyncio
async def test_c1_jinja_branch_preserva_expressoes_legitimas(expressao, inputs, esperado):
    """A sandbox nao pode custar o uso normal do no — este e o outro lado do C1."""
    from flow.nodes.control.jinja_branch import JinjaBranchNode

    node = JinjaBranchNode.__new__(JinjaBranchNode)
    node.parameters = {"expression": expressao}
    node.node_id = "n1"
    node.validate = lambda: None

    resultado = await node.execute(inputs)
    assert resultado["branch"] is esperado


def test_c1_gate_de_prerenderizacao_reconhece_statements():
    """Param so com `{% %}` tem que passar pelo ExpressionService (sandboxed).

    O gate exigia `{{` E `}}`, entao statements escapavam da pre-renderizacao e
    chegavam crus ao no — que era justamente quem avaliava sem sandbox.
    """
    from flow.executor.rendering import render_node_parameters

    node = MagicMock()
    node.parameters = {"expression": "{% set x = 1 %}"}

    # Sem o reconhecimento de `{%`, o valor sairia identico ao de entrada.
    saida = render_node_parameters(node, "n1", {}, {"inputs": {}})
    assert saida["expression"] != "{% set x = 1 %}"


# ── C3: mass assignment de workspace_id ──────────────────────────────────────

@pytest.mark.parametrize("campo", ["workspace_id", "updated_by_id", "created_by_id", "id_hash"])
def test_c3_workflow_update_recusa_campos_nao_editaveis(campo):
    from app.schemas.workflow import WorkflowUpdate

    with pytest.raises(ValidationError) as exc:
        WorkflowUpdate(name="qualquer", **{campo: "valor-forjado"})
    assert exc.value.errors()[0]["type"] == "extra_forbidden"


def test_c3_workflow_update_aceita_campos_legitimos():
    from app.schemas.workflow import WorkflowUpdate

    u = WorkflowUpdate(name="novo", description="d", flag_ative=False)
    assert u.model_dump(exclude_unset=True) == {
        "name": "novo", "description": "d", "flag_ative": False,
    }


# ── C4: s3_key vinda do executor ─────────────────────────────────────────────

def test_c4_valida_s3_key_recusa_workspace_alheio():
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    with pytest.raises(HTTPException) as exc:
        _validate_agent_s3_key("drive/workspace-da-vitima/segredo.csv", ["meu-workspace"])
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "chave",
    [
        "drive/../../etc/passwd",       # traversal
        "/drive/ws-1/a.csv",            # absoluto
        "outro-prefixo/ws-1/a.csv",     # fora dos prefixos conhecidos
        "drive/ws-1/arq\x00.csv",       # NUL
    ],
)
def test_c4_valida_s3_key_recusa_chave_malformada(chave):
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    with pytest.raises(HTTPException):
        _validate_agent_s3_key(chave, ["ws-1"])


@pytest.mark.parametrize("valor", [123, True, {"a": 1}, ["x"], b"drive/ws-1/a.csv", None])
def test_c4_valida_s3_key_recusa_tipo_nao_string(valor):
    """O payload vem de JSON do executor — precisa rejeitar, nao estourar.

    As comparacoes internas levantavam TypeError/AttributeError para tipos que
    nao fossem str. Os callers capturam apenas HTTPException, entao o erro subia
    ate o handler generico e virava 500 em vez de rejeicao limpa.
    """
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    with pytest.raises(HTTPException) as exc:
        _validate_agent_s3_key(valor, ["ws-1"])
    assert exc.value.status_code == 400


def test_c4_valida_s3_key_aceita_chave_do_proprio_workspace():
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    _validate_agent_s3_key("drive/ws-1/pasta/arquivo.csv", ["ws-1"])  # nao levanta


def test_c4_webhook_response_aceita_do_proprio_workspace():
    """Body grande do ResponseNode: a key `webhook-responses/{ws}/{run}/...` deve
    passar quando o `{ws}` pertence ao escopo — o prefixo estava fora do allowlist
    e o `{run}` (segmento errado) reprovava a validação, então o body_ref >1MB
    dava 403 no upload, no readback e no registro do artefato."""
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    _validate_agent_s3_key("webhook-responses/ws-1/run-abc/deadbeef.bin", ["ws-1"])  # nao levanta


def test_c4_webhook_response_recusa_workspace_alheio():
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    with pytest.raises(HTTPException) as exc:
        _validate_agent_s3_key("webhook-responses/ws-da-vitima/run-abc/x.bin", ["meu-ws"])
    assert exc.value.status_code == 403


# ── A3: credencial sem dono ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a3_credencial_sem_dono_e_inacessivel():
    """owner_id NULL curto-circuitava a checagem e liberava a credencial a todos."""
    from unittest.mock import AsyncMock, patch

    from app.services.credential_service import get_credential_metadata
    from app.core.exceptions import CredentialAccessDeniedError

    cred = MagicMock(owner_id=None)
    with patch("app.services.credential_service.CredentialCRUD") as crud:
        crud.return_value.get = AsyncMock(return_value=cred)
        with pytest.raises(CredentialAccessDeniedError):
            await get_credential_metadata(MagicMock(), "cred-1", owner_id="usuario-qualquer")


@pytest.mark.asyncio
async def test_a3_dono_continua_acessando_a_propria_credencial():
    from unittest.mock import AsyncMock, patch

    from app.services.credential_service import get_credential_metadata

    cred = MagicMock(owner_id="usuario-1")
    with patch("app.services.credential_service.CredentialCRUD") as crud:
        crud.return_value.get = AsyncMock(return_value=cred)
        assert await get_credential_metadata(MagicMock(), "cred-1", owner_id="usuario-1") is cred


# ── A9: confinamento de caminho de arquivo ───────────────────────────────────

@pytest.mark.parametrize(
    "caminho",
    [
        "/data-secreto/roubo.shp",   # irmao com prefixo textual igual
        "/datax/y.shp",              # idem
        "/tmpfoo/z.shp",             # idem, sobre /tmp
        "/etc/passwd",               # fora de tudo
        "/data/../etc/passwd",       # traversal apos normalizacao
    ],
)
def test_a9_recusa_caminho_fora_da_hierarquia(caminho):
    """A checagem era `str(resolved).startswith(str(allowed_dir))`.

    Comparacao textual deixava passar diretorio IRMAO cujo nome comecasse
    igual: com `/data` permitido, `/data-secreto` era aceito. `is_relative_to`
    exige que o diretorio permitido seja ancestral de verdade.
    """
    from flow.utils.geo_helpers import validate_file_path

    with pytest.raises(ValueError):
        validate_file_path(caminho)


@pytest.mark.parametrize("caminho", ["/data/ok.shp", "/data/sub/dir/ok.shp", "/tmp/a.shp"])
def test_a9_aceita_caminho_dentro_da_hierarquia(caminho):
    from flow.utils.geo_helpers import validate_file_path

    validate_file_path(caminho)  # nao levanta
