"""Tenant isolation regressions from the 2026-08-28 audit.

One test per fixed finding. The first three are ONE-LINE fixes in the
`where` of a select — exactly the kind that comes back by accident in a merge,
and that breaks no functional test when it does (the route keeps responding
200; it just starts responding with someone else's data).

F3  workflow_groups linked a Workflow resolved only by id_hash (cross-tenant write).
F4  /executores/{id}/status and /workspaces accepted any JWT (cross-tenant read).
F5  GET /workspaces/{id}/executor did not check membership in the workspace.
F7  `OR workspace_id IS NULL` made a legacy row visible to every authenticated user.
F9  ResponseNode set Content-Type and arbitrary headers on the response.

The sweep test at the end (`test_varredura_*`) has the widest reach: instead of
one case per route, it asserts the INVARIANT over the code — no tenant query
may carry a NULL escape.
"""
import inspect
import re
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


# ── F3: escrita cross-tenant em workflow_groups ──────────────────────────────

@pytest.fixture
async def banco():
    """In-memory SQLite with the REAL workflow and group tables.

    A real database is worth the cost: the original failure did not change the
    status code (the route responded 204 in both cases, just writing to the wrong
    row), so only looking at the row after the commit can prove it.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.base import Base
    from app.models.models import Workflow, WorkflowGroup

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[Workflow.__table__, WorkflowGroup.__table__],
        )
    async with async_sessionmaker(engine, expire_on_commit=False)() as sessao:
        yield sessao
    await engine.dispose()


async def _seed(sessao):
    """Um grupo em ws-meu e um workflow em ws-alheio — o cenario do ataque."""
    from app.models.models import Workflow, WorkflowGroup

    grupo = WorkflowGroup(id_hash="grp-1", name="Meu grupo", workspace_id="ws-meu", position=0)
    alvo = Workflow(
        id_hash="wf-alheio", name="Da vítima", workspace_id="ws-alheio",
        definition={"nodes": []}, flag_ative=True,
    )
    meu = Workflow(
        id_hash="wf-meu", name="Meu", workspace_id="ws-meu",
        definition={"nodes": []}, flag_ative=True,
    )
    inativo = Workflow(
        id_hash="wf-inativo", name="Desativado", workspace_id="ws-meu",
        definition={"nodes": []}, flag_ative=False,
    )
    sessao.add_all([grupo, alvo, meu, inativo])
    await sessao.commit()
    return grupo


@pytest.mark.asyncio
async def test_f3_groupable_targets_rejects_workflow_from_another_workspace(banco):
    from sqlalchemy import select

    from app.api.routers.workflow_groups_router import _alvos_agrupaveis
    from app.models.models import Workflow

    grupo = await _seed(banco)

    achados = (await banco.execute(
        select(Workflow).where(*_alvos_agrupaveis(["wf-meu", "wf-alheio"], grupo))
    )).scalars().all()

    assert {w.id_hash for w in achados} == {"wf-meu"}, (
        "workflow de outro workspace entrou no conjunto agrupável — "
        "escrita cross-tenant reaberta"
    )


@pytest.mark.asyncio
async def test_f3_disabled_workflow_stays_groupable(banco):
    """Regression introduced in the first version of the fix: with
    `flag_ative.is_(True)` in the filter, a deactivated workflow that the user
    ticked in the list became "not found" and brought down the creation of the
    whole group. Grouping is organization, not execution."""
    from sqlalchemy import select

    from app.api.routers.workflow_groups_router import _alvos_agrupaveis
    from app.models.models import Workflow

    grupo = await _seed(banco)

    achados = (await banco.execute(
        select(Workflow).where(*_alvos_agrupaveis(["wf-inativo"], grupo))
    )).scalars().all()

    assert [w.id_hash for w in achados] == ["wf-inativo"]


@pytest.mark.asyncio
async def test_f3_trashed_workflow_is_not_groupable(banco):
    from sqlalchemy import select

    from app.api.routers.workflow_groups_router import _alvos_agrupaveis
    from app.core.utils.datetime_utils import utc_now_naive
    from app.models.models import Workflow

    grupo = await _seed(banco)
    (await banco.execute(select(Workflow).where(Workflow.id_hash == "wf-meu"))) \
        .scalar_one().deleted_at = utc_now_naive()
    await banco.commit()

    achados = (await banco.execute(
        select(Workflow).where(*_alvos_agrupaveis(["wf-meu"], grupo))
    )).scalars().all()

    assert achados == []


def test_f3_id_outside_group_is_rejected_with_404():
    from app.api.routers.workflow_groups_router import _reject_ids_outside_group

    encontrado = MagicMock(id_hash="wf-meu")
    with pytest.raises(HTTPException) as exc:
        _reject_ids_outside_group(["wf-meu", "wf-alheio"], [encontrado])

    assert exc.value.status_code == 404
    # Does not distinguish "does not exist" from "belongs to another tenant" — or it becomes an oracle.
    assert "wf-alheio" in exc.value.detail


def test_f3_all_known_ids_does_not_raise():
    from app.api.routers.workflow_groups_router import _reject_ids_outside_group

    _reject_ids_outside_group(["a"], [MagicMock(id_hash="a")])


_ROUTES_THAT_BIND_WORKFLOW = [
    "create_group",
    "update_group",
    "delete_group",
    "add_workflow_to_group",
    "remove_workflow_from_group",
]


@pytest.mark.parametrize("nome_rota", _ROUTES_THAT_BIND_WORKFLOW)
def test_f3_every_route_touching_group_id_matches_the_workspace(nome_rota):
    """Complements the database tests: ensures none of the five routes
    resolves `Workflow` outside the shared criterion.

    Accepts both forms (helper or literal filter) so as not to block a refactor
    that remains correct.
    """
    from app.api.routers import workflow_groups_router

    fonte = inspect.getsource(getattr(workflow_groups_router, nome_rota))

    assert (
        "_alvos_agrupaveis" in fonte
        or "Workflow.workspace_id == group.workspace_id" in fonte
    ), f"{nome_rota} resolve Workflow sem casar o workspace do grupo"


def test_f3_create_group_no_longer_uses_old_permissive_check():
    """`if wf.workspace_id and wf.workspace_id != ...` let NULL through.

    It was the only one of the five routes that validated, but the `and` short-circuited
    on a legacy workflow without a workspace — which was precisely the most exposed case.
    """
    from app.api.routers import workflow_groups_router

    fonte = inspect.getsource(workflow_groups_router.create_group)
    assert "if wf.workspace_id and" not in fonte


# ── F4: executor read by any account ─────────────────────────────────────────

def _who(*, executor_id=None, user_role=None, user_id="u-1"):
    from app.api.dependencies import ExecutorOuUsuario

    if executor_id is not None:
        return ExecutorOuUsuario(executor=MagicMock(id_hash=executor_id))
    return ExecutorOuUsuario(user=MagicMock(role=user_role, id_hash=user_id))


def _executor(id_hash="exec-1", created_by="dono-1"):
    return MagicMock(id_hash=id_hash, created_by=created_by)


def test_f4_regular_user_does_not_read_someone_elses_executor():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    with pytest.raises(HTTPException) as exc:
        _assert_pode_ler_executor(_who(user_role="user", user_id="intruso"), _executor())
    assert exc.value.status_code == 403


def test_f4_admin_reads_any_executor():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    _assert_pode_ler_executor(_who(user_role="admin", user_id="adm"), _executor())


def test_f4_owner_reads_own_executor():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    _assert_pode_ler_executor(
        _who(user_role="user", user_id="dono-1"), _executor(created_by="dono-1")
    )


def test_f4_executor_reads_itself():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    _assert_pode_ler_executor(_who(executor_id="exec-1"), _executor(id_hash="exec-1"))


def test_f4_executor_does_not_enumerate_the_fleet():
    """Any user can create and enroll a dedicated executor; without this
    guard, a compromised executor could read the status of all the others."""
    from app.api.routers.executores_router import _assert_pode_ler_executor

    with pytest.raises(HTTPException) as exc:
        _assert_pode_ler_executor(_who(executor_id="exec-9"), _executor(id_hash="exec-1"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_f4_revoked_token_is_rejected():
    """`agent_mtls_or_user_auth` used a bare `decode_token`: it skipped the blacklist and
    the User lookup, so a token from a session ended by /auth/logout — or from a
    suspended user — stayed valid until it expired on its own."""
    from unittest.mock import AsyncMock, patch

    from app.api import dependencies

    request = MagicMock()
    request.headers = {}

    with patch.object(dependencies, "resolve_access_token", AsyncMock(return_value=None)), \
         patch.object(dependencies, "HTTPBearer") as bearer:
        bearer.return_value = AsyncMock(return_value=MagicMock(credentials="tok"))
        with pytest.raises(HTTPException) as exc:
            await dependencies.agent_mtls_or_user_auth(request, MagicMock())

    assert exc.value.status_code == 401


@pytest.mark.parametrize("kwargs", [{}, {"executor": MagicMock(), "user": MagicMock()}])
def test_f4_ambiguous_identity_is_rejected_at_construction(kwargs):
    """Invalid state must not reach the authorization helper: there it would become
    `None.role` -> AttributeError -> 500, which neither denies nor grants access."""
    from app.api.dependencies import ExecutorOuUsuario

    with pytest.raises(ValueError):
        ExecutorOuUsuario(**kwargs)


def test_f4_executor_routes_call_the_gate():
    from app.api.routers import executores_router

    for nome in ("agent_status", "agent_workspaces_endpoint"):
        fonte = inspect.getsource(getattr(executores_router, nome))
        assert "_assert_pode_ler_executor" in fonte, f"{nome} voltou a autenticar sem autorizar"


# ── F5: GET /workspaces/{id}/executor ────────────────────────────────────────

def test_f5_get_workspace_executor_uses_visibility_gate():
    """Without `_get_visible_workspace`, the route returned the `target_executor_id` of
    any workspace and also distinguished 404 from 200 — an enumeration oracle."""
    from app.api.routers import workspace_router

    fonte = inspect.getsource(workspace_router.get_workspace_agent)
    assert "_get_visible_workspace" in fonte


# ── F7: tenant escape via NULL workspace_id ──────────────────────────────────

@pytest.mark.parametrize(
    "metodo",
    [
        "get_all_metadata",
        "get_all_metadata_by_workspace_ids",
    ],
)
def test_f7_workflow_listing_has_no_null_escape(metodo):
    from app.crud.workflow_crud import WorkflowCRUD

    fonte = inspect.getsource(getattr(WorkflowCRUD, metodo))
    assert "workspace_id.is_(None)" not in fonte


def test_f7_credential_usage_has_no_null_escape():
    from app.api.routers import credentials_router

    fonte = inspect.getsource(credentials_router.credential_usage)
    assert "workspace_id.is_(None)" not in fonte


@pytest.mark.parametrize("modelo", ["Workflow", "WorkflowRun"])
def test_f7_workspace_id_column_is_not_null(modelo):
    """The real guarantee: with the column NOT NULL, no future query
    needs (or can justify) the `OR workspace_id IS NULL`."""
    import app.models.models as m

    coluna = getattr(m, modelo).__table__.c.workspace_id
    assert coluna.nullable is False


def test_f7_workflow_create_requires_workspace():
    from pydantic import ValidationError

    from app.schemas.workflow import WorkflowCreate

    with pytest.raises(ValidationError):
        WorkflowCreate(name="x", definition={"nodes": []})

    wf = WorkflowCreate(name="x", definition={"nodes": []}, workspace_id="ws-1")
    assert wf.workspace_id == "ws-1"


# ── F9: ResponseNode response ────────────────────────────────────────────────

def _req():
    """Request minimo — so precisa de `.state` mutavel."""
    from types import SimpleNamespace

    return SimpleNamespace(state=SimpleNamespace())


@pytest.mark.parametrize(
    "tipo", ["image/svg+xml", "application/xhtml+xml", "text/x-python", "image/png"]
)
def test_f9_content_type_outside_allowlist_is_downgraded(tipo):
    from app.api.routers.webhook_router import _sanitize_node_response

    content_type, headers = _sanitize_node_response({"content_type": tipo}, _req())

    assert content_type.startswith("text/plain")
    assert headers["Content-Type"].startswith("text/plain")


@pytest.mark.parametrize(
    "tipo",
    [
        # The five the ResponseNode dropdown offers — downgrading any one of
        # them would silently break existing workflows.
        "application/json", "text/plain", "text/html", "application/xml", "text/csv",
        "application/geo+json",
    ],
)
def test_f9_content_type_announced_by_node_is_not_downgraded(tipo):
    """Regression: the first version of this allowlist did NOT include `text/html`, which
    is a selectable option on the canvas (flow/nodes/outputs/response_node.py). The
    effect was a silent downgrade — the page started arriving as text,
    with a warning only in the server log."""
    from app.api.routers.webhook_router import _sanitize_node_response

    content_type, _ = _sanitize_node_response({"content_type": tipo}, _req())
    assert content_type == tipo


@pytest.mark.parametrize("tipo", ["text/html", "text/html; charset=utf-8", "TEXT/HTML"])
def test_f9_html_marks_the_body_as_untrusted(tipo):
    """Preserves the feature and still kills the XSS: the middleware swaps the CSP for
    one with `sandbox` when this marker is present."""
    from app.api.routers.webhook_router import _sanitize_node_response

    request = _req()
    _sanitize_node_response({"content_type": tipo}, request)

    assert request.state.corpo_nao_confiavel is True


@pytest.mark.parametrize("tipo", ["application/json", "text/csv", "text/plain"])
def test_f9_non_renderable_type_does_not_harden_the_csp(tipo):
    """The restricted CSP must not leak into an ordinary integration response."""
    from app.api.routers.webhook_router import _sanitize_node_response

    request = _req()
    _sanitize_node_response({"content_type": tipo}, request)

    assert getattr(request.state, "corpo_nao_confiavel", False) is False


def test_f9_untrusted_body_csp_blocks_script():
    from app.main import _CSP_UNTRUSTED_BODY

    assert "sandbox" in _CSP_UNTRUSTED_BODY
    assert "default-src 'none'" in _CSP_UNTRUSTED_BODY
    assert "script-src" not in _CSP_UNTRUSTED_BODY
    assert "unsafe-inline" not in _CSP_UNTRUSTED_BODY.replace("style-src 'unsafe-inline'", "")


def test_f9_middleware_applies_strict_csp_end_to_end():
    """Behavioral, not source inspection: brings up the REAL middleware and compares
    the two responses.

    The marker goes through `request.state` because the middleware overwrites the
    `Content-Security-Policy` header of EVERY response — setting it in the handler
    would be discarded. This test is what proves the channel works.
    """
    from fastapi import FastAPI, Request
    from starlette.responses import Response
    from starlette.testclient import TestClient

    from app.main import SecurityHeadersMiddleware

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/normal")
    async def _normal():
        return {"ok": True}

    @app.get("/html")
    async def _html(request: Request):
        request.state.corpo_nao_confiavel = True
        return Response("<b>oi</b>", media_type="text/html")

    with TestClient(app) as c:
        csp_normal = c.get("/normal").headers["content-security-policy"]
        csp_html = c.get("/html").headers["content-security-policy"]

    # The ordinary route keeps the application's CSP (which allows its own scripts).
    assert "script-src 'self'" in csp_normal
    assert "sandbox" not in csp_normal

    # The untrusted-body route runs in an opaque origin, without scripts.
    assert csp_html.startswith("sandbox")
    assert "script-src" not in csp_html


@pytest.mark.parametrize(
    "cabecalho",
    [
        "Content-Security-Policy",
        "X-Frame-Options",
        "Strict-Transport-Security",
        "Set-Cookie",
        "Access-Control-Allow-Origin",
        "x-content-type-options",   # case does not matter
    ],
)
def test_f9_security_header_cannot_be_overridden(cabecalho):
    from app.api.routers.webhook_router import _sanitize_node_response

    _, headers = _sanitize_node_response(
        {"headers": {cabecalho: "valor-do-atacante"}}, _req()
    )

    assert cabecalho not in headers
    assert cabecalho.lower() not in {k.lower() for k in headers}


def test_f9_workflows_own_header_passes():
    """The allowlist must not cost legitimate use — integrations use their own
    headers to correlate the response."""
    from app.api.routers.webhook_router import _sanitize_node_response

    _, headers = _sanitize_node_response({"headers": {"X-Request-Id": "abc-123"}}, _req())

    assert headers["X-Request-Id"] == "abc-123"


@pytest.mark.parametrize("brutos", ["uma-string", ["a", "b"], 42, True])
def test_f9_non_dict_headers_do_not_break_the_handler(brutos):
    """`headers` is a free field of type `object` on the node and arrives as JSON from the
    executor. `.items()` on a string raised AttributeError, which the handler does not
    catch — it became a 500 instead of being ignored."""
    from app.api.routers.webhook_router import _sanitize_node_response

    _, headers = _sanitize_node_response({"headers": brutos}, _req())

    assert set(headers) == {"Content-Type"}


# ── Sweep: the invariant, not one more case per route ────────────────────────

_MODULES_WITH_TENANT_QUERY = [
    "app.api.routers.credentials_router",
    "app.api.routers.workflow_groups_router",
    "app.api.routers.workflows_router",
    "app.api.routers.artifacts_router",
    "app.api.routers.drive_router",
    # F5 split the monoliths: the NEW owners of the moved code join the
    # sweep too (the regression net must not shrink with a refactor).
    "app.api.routers.drive_admin_router",
    "app.api.routers.executor_drive_router",
    "app.crud.workflow_crud",
    "app.services.observability_service",
    "app.services.observability.agregados",
    "app.services.observability.escopo",
    "app.services.observability.estatisticas",
    "app.services.observability.frota",
    "app.services.observability.runs",
    "app.services.workflow_service",
]

# `Workspace.deleted_at.is_(None)` e legitimo (lixeira) — o padrao proibido e
# especificamente o escape por workspace NULO.
_NULL_ESCAPE = re.compile(r"workspace_id\s*\.\s*is_\(\s*None\s*\)")


@pytest.mark.parametrize("modulo", _MODULES_WITH_TENANT_QUERY)
def test_sweep_no_module_reintroduces_null_workspace_escape(modulo):
    """Asserts the INVARIANT, not a case.

    The audit's three isolation failures had the same signature. One test
    per route protects the routes that existed that day; this one also protects
    those yet to be written in these modules.
    """
    import importlib

    fonte = inspect.getsource(importlib.import_module(modulo))
    # Discards comments and one-line docstrings that QUOTE the pattern while
    # explaining why it was removed.
    codigo = "\n".join(
        linha for linha in fonte.splitlines() if not linha.lstrip().startswith("#")
    )

    achados = _NULL_ESCAPE.findall(codigo)
    assert not achados, (
        f"{modulo} voltou a usar `workspace_id.is_(None)`: isso torna a linha "
        "visivel a qualquer usuario autenticado, de qualquer tenant."
    )
