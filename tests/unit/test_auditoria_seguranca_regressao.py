"""
Security audit regressions.

One test per fixed finding. Each one fails if the fix is reverted — several of
them are one-liners, exactly the kind that comes back by accident in a merge.
What these tests protect:

C1  JinjaBranch evaluated the user's expression in a plain `Environment`.
C3  `WorkflowUpdate` accepted `workspace_id`, allowing the workflow to be moved across tenants.
C4  The executor's `s3_key` became `Artifact.s3_key` without validation.
A3  A credential with a NULL `owner_id` was accessible to any authenticated user.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError


# ── C1: JinjaBranch sandbox ───────────────────────────────────────────────────

# Classic Jinja2 sandbox escape chains. All of them RENDERED before the fix;
# the `cycler` one even executed a command in the executor process.
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
    """The sandbox must not cost the node's normal use — this is the other side of C1."""
    from flow.nodes.control.jinja_branch import JinjaBranchNode

    node = JinjaBranchNode.__new__(JinjaBranchNode)
    node.parameters = {"expression": expressao}
    node.node_id = "n1"
    node.validate = lambda: None

    resultado = await node.execute(inputs)
    assert resultado["branch"] is esperado


def test_c1_gate_de_prerenderizacao_reconhece_statements():
    """A param with only `{% %}` has to go through ExpressionService (sandboxed).

    The gate required `{{` AND `}}`, so statements escaped pre-rendering and
    reached the node raw — which was precisely what evaluated without a sandbox.
    """
    from flow.executor.rendering import render_node_parameters

    node = MagicMock()
    node.parameters = {"expression": "{% set x = 1 %}"}

    # Without recognizing `{%`, the value would come out identical to the input.
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
        "outro-prefixo/ws-1/a.csv",     # outside the known prefixes
        "drive/ws-1/arq\x00.csv",       # NUL
    ],
)
def test_c4_valida_s3_key_recusa_chave_malformada(chave):
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    with pytest.raises(HTTPException):
        _validate_agent_s3_key(chave, ["ws-1"])


@pytest.mark.parametrize("valor", [123, True, {"a": 1}, ["x"], b"drive/ws-1/a.csv", None])
def test_c4_valida_s3_key_recusa_tipo_nao_string(valor):
    """The payload comes from the executor's JSON — it must reject, not blow up.

    The internal comparisons raised TypeError/AttributeError for types that
    weren't str. The callers only catch HTTPException, so the error propagated
    up to the generic handler and became a 500 instead of a clean rejection.
    """
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    with pytest.raises(HTTPException) as exc:
        _validate_agent_s3_key(valor, ["ws-1"])
    assert exc.value.status_code == 400


def test_c4_valida_s3_key_aceita_chave_do_proprio_workspace():
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    _validate_agent_s3_key("drive/ws-1/pasta/arquivo.csv", ["ws-1"])  # does not raise


def test_c4_webhook_response_aceita_do_proprio_workspace():
    """Large ResponseNode body: the key `webhook-responses/{ws}/{run}/...` must
    pass when `{ws}` belongs to the scope — the prefix was outside the allowlist
    and `{run}` (wrong segment) failed validation, so a body_ref >1MB got a 403
    on upload, on readback and on artifact registration."""
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    _validate_agent_s3_key("webhook-responses/ws-1/run-abc/deadbeef.bin", ["ws-1"])  # does not raise


def test_c4_webhook_response_recusa_workspace_alheio():
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    with pytest.raises(HTTPException) as exc:
        _validate_agent_s3_key("webhook-responses/ws-da-vitima/run-abc/x.bin", ["meu-ws"])
    assert exc.value.status_code == 403


# ── A3: ownerless credential ─────────────────────────────────────────────────

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


# ── A9: file path confinement ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "caminho",
    [
        "/data-secreto/roubo.shp",   # sibling with the same textual prefix
        "/datax/y.shp",              # idem
        "/tmpfoo/z.shp",             # same, under /tmp
        "/etc/passwd",               # outside everything
        "/data/../etc/passwd",       # traversal apos normalizacao
    ],
)
def test_a9_recusa_caminho_fora_da_hierarquia(caminho):
    """The check was `str(resolved).startswith(str(allowed_dir))`.

    Textual comparison let through a SIBLING directory whose name started the
    same: with `/data` allowed, `/data-secreto` was accepted. `is_relative_to`
    requires the allowed directory to be a real ancestor.
    """
    from flow.utils.geo_helpers import validate_file_path

    with pytest.raises(ValueError):
        validate_file_path(caminho)


@pytest.mark.parametrize("caminho", ["/data/ok.shp", "/data/sub/dir/ok.shp", "/tmp/a.shp"])
def test_a9_aceita_caminho_dentro_da_hierarquia(caminho):
    from flow.utils.geo_helpers import validate_file_path

    validate_file_path(caminho)  # does not raise
