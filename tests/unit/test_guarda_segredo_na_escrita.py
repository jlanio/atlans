"""A secret does not get into the definition through the REST write edges.

A credential lives in `credentials`, encrypted; the definition stores the `credential_id`
and the server injects the value into a COPY on dispatch. A secret written into the
definition would be encrypted in the database, but would already have traveled through
transport and logs — and output redaction would erase it afterwards, giving the false
impression that it is not there.

The MCP server already refused it in its three construction tools
(`app/mcp/tools/construcao.py`); the REST API, which is what the editor saves through, did not. A
survey in production (2026-09-14) measured 286 nodes, 56 with `credential_id` and
ZERO stored secrets: the refusal makes invariant a state that was already true
by convention, without refusing anything that exists.

The tests call the route functions directly, with no HTTP client: what is proven
here is the guard, and the dependencies (role, session) would only get in the way.
"""
import pytest
from fastapi import HTTPException

from app.api.routers import workflows_router as WR

SEGREDO = "postgresql://usuario:senha-secretissima@host:5432/base"  # pragma: allowlist secret
TOKEN = "sk-ZmFrZS10b2tlbi1wYXJhLXRlc3RlLTEyMzQ1Ng"  # pragma: allowlist secret


def _no(props: dict) -> dict:
    return {"nodes": [{"id": "n1", "name": "DatabaseQuery", "properties": props}]}


# ── A recusa ────────────────────────────────────────────────────────────────

def test_connection_string_literal_e_recusada():
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no({"connectionString": SEGREDO}))

    assert exc.value.status_code == 422
    assert "credential_id" in exc.value.detail


def test_cabecalho_de_autorizacao_tambem_e_recusado():
    """Explicit decision by the owner: a free-form header is included in the refusal.

    Whoever needs to send a token in a header creates a credential. There is no exception
    and no "warn only" mode — and the credential path already exists (`http_auth`).
    """
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no({"headers": {"Authorization": f"Bearer {TOKEN}"}}))

    assert exc.value.status_code == 422


def test_a_recusa_cita_o_caminho_e_nunca_o_valor():
    """The refusal message must not be the leak it prevents."""
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no({"connectionString": SEGREDO}))

    detalhe = str(exc.value.detail)
    assert "connectionString" in detalhe          # o caminho, para o usuario achar
    assert SEGREDO not in detalhe                 # the value, never
    assert "senha-secretissima" not in detalhe


# ── What must NOT be refused ────────────────────────────────────────────────

def test_expressao_pura_passa():
    """`{{ ... }}` e referencia resolvida em runtime, nao segredo gravado."""
    WR._recusar_segredo(_no({"connectionString": "{{ inputs.dsn }}"}))


def test_so_o_esquema_de_autenticacao_passa():
    """"Bearer {{ $Cred.token }}" nao grava nada — sobra so o esquema."""
    WR._recusar_segredo(_no({"headers": {"Authorization": "Bearer {{ $Cred.token }}"}}))


def test_referencia_por_credential_id_passa():
    """O caminho pretendido: a definition guarda a referencia, nao o valor."""
    WR._recusar_segredo(_no({
        "credential_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
        "query": "SELECT * FROM lotes",
    }))


def test_definition_vazia_passa():
    WR._recusar_segredo({})
    WR._recusar_segredo(None)


# ── The route wiring ────────────────────────────────────────────────────────

async def test_update_sem_definition_nao_dispara_a_guarda(monkeypatch):
    """The most likely regression: `WorkflowUpdate` is PARTIAL.

    A missing `definition` means "don't touch it". A careless guard, one that
    checked without testing for absence, would block even renaming a workflow — and the
    symptom (I can't save the name) would not point to any secret.
    """
    from app.schemas.workflow import WorkflowUpdate

    chamado = []
    monkeypatch.setattr(WR, "_recusar_segredo", lambda d: chamado.append(d))

    gravado = {}

    class _Service:
        async def update_workflow(self, id_hash, workflow_in, **kw):
            gravado["nome"] = workflow_in.name
            return {"id_hash": id_hash}

    class _Wf:
        id_hash = "wf-1"
        workspace_id = "ws-1"

    # The role is checked by the route's dependency (`workflow_com_papel`), which
    # the direct call does not go through; here only the limiter gets in the way.
    monkeypatch.setattr(WR.limiter, "enabled", False)

    class _User:
        id_hash = "u-1"

    await WR.update_workflow(
        request=None,
        workflow_in=WorkflowUpdate(name="nome novo"),
        service=_Service(),
        wf=_Wf(),
        db=None,
        current_user=_User(),
    )

    assert chamado == []                 # guard was not consulted
    assert gravado["nome"] == "nome novo"  # e a edicao passou


def test_paridade_com_a_borda_do_mcp():
    """The REST API must not be more permissive than the MCP server.

    Both call `definition_contem_segredo`; this test breaks if someone
    creates a second list of keys for one of the sides.
    """
    from app.mcp.tools.construcao import _recusar_segredo as mcp_recusa

    definicao = _no({"headers": {"Authorization": f"Bearer {TOKEN}"}})

    with pytest.raises(HTTPException):
        WR._recusar_segredo(definicao)
    with pytest.raises(Exception):           # o MCP levanta ToolError, nao HTTP
        mcp_recusa(definicao)


# ── The guard is WIRED INTO the routes ──────────────────────────────────────
#
# Without these, the whole feature could be removed from the routes and the suite
# stayed green: the tests above exercise the helper, not the wiring. That is
# exactly what a review measured — deleting the calls (there were three; the one in
# /workflows/validate went away with the route) did not change a single name in the suite.

class _Usuario:
    id_hash = "u-1"


class _Wf:
    id_hash = "wf-1"
    workspace_id = "ws-1"


@pytest.fixture
def rota_liberada(monkeypatch):
    """Gets what is not the subject out of the way: limiter and role.

    On the `/{id_hash}` routes the role comes from the dependency (`workflow_com_papel`),
    which the direct call does not go through; on POST it is checked in the route body, and
    here the person is `editor` — the comparison really runs.
    """
    from app.core.authorization import workflow_access

    async def _papel(db, ws_id, uid):
        return "editor"

    monkeypatch.setattr(WR.limiter, "enabled", False)
    monkeypatch.setattr(workflow_access, "get_workspace_member_role", _papel)


async def test_rota_de_criacao_recusa(rota_liberada):
    from app.schemas.workflow import WorkflowCreate

    payload = WorkflowCreate(
        name="fluxo", workspace_id="ws-1", definition=_no({"connectionString": SEGREDO}),
    )

    with pytest.raises(HTTPException) as exc:
        await WR.create_workflow(
            request=None, payload=payload, service=None, current_user=_Usuario(), db=None,
        )
    assert exc.value.status_code == 422
    assert SEGREDO not in str(exc.value.detail)


async def test_rota_de_atualizacao_recusa(rota_liberada):
    from app.schemas.workflow import WorkflowUpdate

    with pytest.raises(HTTPException) as exc:
        await WR.update_workflow(
            request=None,
            workflow_in=WorkflowUpdate(definition=_no({"connectionString": SEGREDO})),
            service=None,
            wf=_Wf(),
            db=None,
            current_user=_Usuario(),
        )
    assert exc.value.status_code == 422


async def test_params_schema_tambem_e_guardado(rota_liberada):
    """Sibling column, writable in the same body, and NOT encrypted in the database."""
    from app.schemas.workflow import WorkflowUpdate

    with pytest.raises(HTTPException) as exc:
        await WR.update_workflow(
            request=None,
            workflow_in=WorkflowUpdate(params_schema={"token": {"type": "string", "default": TOKEN}}),
            service=None,
            wf=_Wf(),
            db=None,
            current_user=_Usuario(),
        )
    assert exc.value.status_code == 422
    assert TOKEN not in str(exc.value.detail)


# ── The ACCEPTED false positives ────────────────────────────────────────────

@pytest.mark.parametrize("caso,props", [
    ("bind :token numa query SQL",
     {"query": "SELECT * FROM t WHERE x = :token", "queryParams": {"token": "abc123"}}),
    ("renomear uma COLUNA chamada senha",
     {"renameFields": {"senha": "senha_hash"}}),
    ("webhook declarando o formato do payload",
     {"payload_schema": {"token": "string", "valor": "number"}}),
    ("token de paginacao num body JSON",
     {"body": {"pagina": 2, "token": "eyJhbGciOiJIUzI1NiJ9"}}),
])
def test_recusas_deliberadas_em_mapas_de_dado_do_usuario(caso, props):
    """Four LEGITIMATE patterns the guard refuses — and that was decided.

    The rule matches by KEY NAME, and in these maps the key is user data:
    bind name, column name, payload field name. A review measured
    30 realistic definitions and found exactly these four.

    The alternative — exempting `queryParams`, `renameFields`, `payload_schema` and
    `body` from the by-name rule — was considered and REJECTED: a real token
    pasted there would pass silently, and detection would become narrower than
    redaction, which keeps redacting those paths. `redacao.py` forbids this in
    writing: "the edge accepts what delivery later erases".

    This test exists so that the next person who runs into one of these 422s
    knows it is not a bug. The way out is to use `credential_id`. If you came here to
    make the test pass by loosening the rule, that is a product decision — not
    a fix.
    """
    with pytest.raises(HTTPException) as exc:
        WR._recusar_segredo(_no(props))
    assert exc.value.status_code == 422
