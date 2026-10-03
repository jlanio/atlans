# tests/unit/test_papel_minimo_das_rotas.py
"""
Minimum role for each workspace route — a matrix, read from the route itself.

The role check was hand-written in ~25 routes: load the role
(`get_accessible_workflow_with_role` or `get_workspace_member_role`) and, on the
next line, `if not _has_min_workspace_role(...): raise HTTPException(403)`.
The defect this repetition already produced is the route that FORGETS the second
line: `GET /workflows/{id}/pins` answered with no role at all (its siblings
required `editor`), and the schedule `PUT` let a `viewer` reconfigure triggers.
No test caught it, because each route had its own — or none.

Two halves:

1. **Workflow routes** (`/workflows/{id_hash}...`). The minimum role is
   DECLARED in the dependency, `workflow_com_papel(minimo, mensagem)`, and this
   test reads it from the registered route. A new route that loads the workflow
   from the path without declaring a role fails here; so does a route that
   declares a role different from the one registered in
   `PAPEL_DAS_ROTAS_DE_WORKFLOW` — lowering a route's role becomes a diff line
   in this file, not a side effect.
2. **Workspace routes** (groups, members, artifacts, Drive, workflow
   creation). The workspace comes from the body or the resource, so the check
   runs in the handler (`exigir_papel_no_workspace`). Every write route of these
   routers must be in `ROTAS_DE_WORKSPACE` — or in `SEM_PAPEL_DE_WORKSPACE`,
   with the reason.

In both, the matrix sends the request with EACH role below the minimum and
checks the 403 with the route's message: through the real app, with the role
coming from `workspace_members` in a real SQLite, not from a role double.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.authorization.workflow_access import WORKSPACE_ROLE_ORDER
from tests.unit._mcp_harness import TABELAS
from tests.unit._rotas import rotas_efetivas

WS = "ws-a"
WF = "wf-a"
WF_APAGADO = "wf-apagado"
GRUPO = "grupo-a"
ARTEFATO = "art-a"
ARQUIVO = "arq-a"

# One user per role in workspace `ws-a`; `u-owner` is the owner (no row in
# `workspace_members`, as in production). `u-fora` is nowhere and `u-alvo` is
# the member the member routes act on.
USUARIO_DO_PAPEL = {
    "owner": "u-owner",
    "admin": "u-admin",
    "operator": "u-operator",
    "editor": "u-editor",
    "viewer": "u-viewer",
}
FORA = "u-fora"
ALVO = "u-alvo"

_EDITOR = "Requer role 'editor' ou superior."
_ADMIN_DO_WORKSPACE = "Requer role 'admin' ou superior neste workspace."
_SO_O_DONO = "Apenas o dono pode gerenciar este workspace."
_NAO_MEMBRO = "Acesso negado a este recurso."


def _abaixo_de(minimo: str | None) -> list[str]:
    """The roles that do NOT reach `minimo` — the ones the route must refuse."""
    if minimo is None:
        return []
    return WORKSPACE_ROLE_ORDER[: WORKSPACE_ROLE_ORDER.index(minimo)]


# ══════════════════════════════════════════════════════════════════════════════
# A matriz
# ══════════════════════════════════════════════════════════════════════════════

#: (method, registered path) → (minimum role, 403 message). Role `None`
#: is read access: belonging to the workspace is enough, and outsiders get the
#: membership 403.
PAPEL_DAS_ROTAS_DE_WORKFLOW: dict[tuple[str, str], tuple[str | None, str | None]] = {
    ("GET", "/workflows/{id_hash}"): (None, None),
    ("GET", "/workflows/{id_hash}/contract"): (None, None),
    ("GET", "/workflows/{id_hash}/versions"): (None, None),
    ("GET", "/workflows/{id_hash}/pins"): (
        "viewer", "Requer role 'viewer' ou superior para ver os pins.",
    ),
    ("DELETE", "/workflows/{id_hash}"): ("editor", _EDITOR),
    ("PUT", "/workflows/{id_hash}"): ("editor", _EDITOR),
    ("POST", "/workflows/{id_hash}/duplicate"): (
        "editor", "Requer role 'editor' ou superior para duplicar workflows.",
    ),
    ("POST", "/workflows/{id_hash}/versions/{version_number}/restore"): ("editor", _EDITOR),
    ("PATCH", "/workflows/{id_hash}/portal"): ("editor", _EDITOR),
    ("PUT", "/workflows/{id_hash}/pin/{node_id}"): ("editor", _EDITOR),
    ("DELETE", "/workflows/{id_hash}/pin/{node_id}"): ("editor", _EDITOR),
    ("POST", "/workflows/{id_hash}/execute"): (
        "operator", "Requer role 'operator' ou superior para executar workflows.",
    ),
    ("POST", "/workflows/{id_hash}/runs/{run_id}/retry"): (
        "operator", "Requer role 'operator' ou superior para executar workflows.",
    ),
    ("PUT", "/workflows/{id_hash}/schedules/{job_id}"): (
        "operator", "Requer role 'operator' ou superior para gerenciar agendamentos.",
    ),
    ("POST", "/workflows/{id_hash}/move"): (
        "admin", "Requer role 'admin' ou 'owner' no workspace de origem para mover workflows.",
    ),
    ("POST", "/workflows/{id_hash}/move/preview"): (
        "admin", "Requer role 'admin' ou 'owner' no workspace de origem para mover workflows.",
    ),
}


@dataclass(frozen=True)
class RotaDeWorkspace:
    """A route whose workspace comes from the body or the resource.

    `url`/`json`/`arquivo` build a VALID request: here the check runs in the
    handler, after body validation, and an invalid body would stop at the
    422 without reaching the guard. `mensagem_fora` is what a non-member gets
    when the route checks membership before the role (None: same as the role's).
    """

    metodo: str
    caminho: str
    url: str
    minimo: str
    mensagem: str
    json: dict | None = None
    arquivo: bool = False
    mensagem_fora: str | None = None


ROTAS_DE_WORKSPACE: list[RotaDeWorkspace] = [
    RotaDeWorkspace(
        "POST", "/workflows", "/workflows", "editor",
        "Requer role 'editor' ou superior para criar workflows.",
        json={"name": "Novo", "workspace_id": WS, "definition": {"nodes": [], "edges": []}},
    ),
    # Grupos
    RotaDeWorkspace(
        "POST", "/workflow-groups", "/workflow-groups", "editor", _EDITOR,
        json={"name": "Novo", "workspace_id": WS},
    ),
    RotaDeWorkspace(
        "PUT", "/workflow-groups/reorder", "/workflow-groups/reorder", "editor", _EDITOR,
        json={"group_ids": [GRUPO]},
    ),
    RotaDeWorkspace(
        "PUT", "/workflow-groups/{group_id}", f"/workflow-groups/{GRUPO}", "editor", _EDITOR,
        json={"name": "Outro"},
    ),
    RotaDeWorkspace("DELETE", "/workflow-groups/{group_id}", f"/workflow-groups/{GRUPO}", "editor", _EDITOR),
    RotaDeWorkspace(
        "POST", "/workflow-groups/{group_id}/workflows/{workflow_id}",
        f"/workflow-groups/{GRUPO}/workflows/{WF}", "editor", _EDITOR,
    ),
    RotaDeWorkspace(
        "DELETE", "/workflow-groups/{group_id}/workflows/{workflow_id}",
        f"/workflow-groups/{GRUPO}/workflows/{WF}", "editor", _EDITOR,
    ),
    # Workspace e membros
    RotaDeWorkspace(
        "PUT", "/workspaces/{id_hash}", f"/workspaces/{WS}", "owner", _SO_O_DONO,
        json={"name": "Outro"},
    ),
    RotaDeWorkspace("DELETE", "/workspaces/{id_hash}", f"/workspaces/{WS}", "owner", _SO_O_DONO),
    RotaDeWorkspace(
        "POST", "/workspaces/{id_hash}/members", f"/workspaces/{WS}/members", "admin",
        _ADMIN_DO_WORKSPACE, json={"email": "novo@teste", "role": "viewer"},
    ),
    RotaDeWorkspace(
        "PUT", "/workspaces/{id_hash}/members/{user_id}", f"/workspaces/{WS}/members/{ALVO}",
        "admin", _ADMIN_DO_WORKSPACE, json={"role": "editor"},
    ),
    # Removing ANOTHER member. Leaving on your own does not require a role (see
    # `remove_member`), which is why the target here is never the requester.
    RotaDeWorkspace(
        "DELETE", "/workspaces/{id_hash}/members/{user_id}", f"/workspaces/{WS}/members/{ALVO}",
        "admin", "Requer role 'admin' ou superior para remover membros.",
    ),
    RotaDeWorkspace(
        "PUT", "/workspaces/{id_hash}/executor", f"/workspaces/{WS}/executor", "admin",
        _ADMIN_DO_WORKSPACE, json={"target_executor_id": None},
    ),
    RotaDeWorkspace(
        "POST", "/workspaces/{id_hash}/executors/{executor_id}",
        f"/workspaces/{WS}/executors/ex-1?tier=1", "admin", _ADMIN_DO_WORKSPACE,
    ),
    RotaDeWorkspace(
        "DELETE", "/workspaces/{id_hash}/executors/{executor_id}",
        f"/workspaces/{WS}/executors/ex-1", "admin", _ADMIN_DO_WORKSPACE,
    ),
    RotaDeWorkspace(
        "PUT", "/workspaces/{id_hash}/fallback", f"/workspaces/{WS}/fallback", "admin",
        _ADMIN_DO_WORKSPACE, json={"terminal": "fail"},
    ),
    RotaDeWorkspace(
        "PUT", "/workspaces/{id_hash}/notifications", f"/workspaces/{WS}/notifications", "admin",
        _ADMIN_DO_WORKSPACE, json={"allowlist": []},
    ),
    # Artefatos
    RotaDeWorkspace(
        "DELETE", "/artifacts/{id_hash}", f"/artifacts/{ARTEFATO}", "editor",
        "Requer role 'editor' ou superior para excluir artefatos.", mensagem_fora=_NAO_MEMBRO,
    ),
    RotaDeWorkspace(
        "POST", "/artifacts/batch-delete", "/artifacts/batch-delete", "editor",
        "Requer role 'editor' ou superior para excluir artefatos.",
        json={"id_hashes": [ARTEFATO]}, mensagem_fora=f"Acesso negado ao artefato {ARTEFATO}.",
    ),
    # Drive
    RotaDeWorkspace(
        "POST", "/drive/upload", f"/drive/upload?workspace_id={WS}", "editor", _EDITOR,
        arquivo=True, mensagem_fora=_NAO_MEMBRO,
    ),
    RotaDeWorkspace("DELETE", "/drive/{id_hash}", f"/drive/{ARQUIVO}", "editor", _EDITOR, mensagem_fora=_NAO_MEMBRO),
]

#: Write routes of these routers that do NOT require a workspace role — each one
#: with the reason. A new route with no reason here nor a line above fails.
SEM_PAPEL_DE_WORKSPACE: dict[tuple[str, str], str] = {
    ("POST", "/workflows/runs/{run_id}/cancel"): (
        "a guarda (operator no workspace DO RUN, com atalho de admin da plataforma) "
        "mora em `workflow_execution_service.cancel_run`, e é testada lá"
    ),
    ("POST", "/workspaces"): "criar o próprio workspace não pede papel em workspace nenhum",
    ("PUT", "/artifacts/admin/settings"): (
        "configuração da plataforma: `require_admin` (papel global), não papel de workspace"
    ),
    ("POST", "/drive/batch-delete"): (
        "o lote FILTRA por papel no serviço (pula o que não pode apagar) em vez de "
        "recusar o lote inteiro — ver test_guarda_de_tenant_unica"
    ),
}

_ROUTERS = {
    "workflows_router", "schedules_router", "workflow_groups_router",
    "workspace_router", "artifacts_router", "drive_router",
}
_ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}


# ══════════════════════════════════════════════════════════════════════════════
# Reading the registered routes
# ══════════════════════════════════════════════════════════════════════════════

def _rotas() -> list[APIRoute]:
    """The app's HTTP routes, including those of the included routers.

    Via `rotas_efetivas`: since FastAPI 0.141 `app.routes` keeps one node
    per included router, without its routes, and the matrix would see none
    (see `tests/unit/_rotas.py`). `dependant` and `methods` separate the API
    routes from the OpenAPI ones (no `dependant`) and the WebSocket ones (no `methods`).
    """
    from app.main import app

    return [
        r for r in rotas_efetivas(app)
        if getattr(r, "dependant", None) is not None and getattr(r, "methods", None)
    ]


def _e_rota_de_workflow(rota: APIRoute) -> bool:
    return rota.path.startswith("/workflows/{id_hash}")


def _rotas_de_workflow() -> dict[tuple[str, str], APIRoute]:
    return {
        (metodo, rota.path): rota
        for rota in _rotas() if _e_rota_de_workflow(rota)
        for metodo in rota.methods
    }


def _papel_declarado(rota: APIRoute):
    """The route's `workflow_com_papel` dependency, or None if it declares no role."""
    for dependencia in rota.dependant.dependencies:
        if hasattr(dependencia.call, "papel_minimo"):
            return dependencia.call
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Harness: app real, SQLite, papel vindo de `workspace_members`
# ══════════════════════════════════════════════════════════════════════════════

async def _semear(db) -> None:
    from app.models.artifact import Artifact
    from app.models.user import User
    from app.models.workflow import Workflow
    from app.models.workflow_group import WorkflowGroup
    from app.models.workspace import Workspace
    from app.models.workspace_file import WorkspaceFile
    from app.models.workspace_member import WorkspaceMember

    usuarios = [*USUARIO_DO_PAPEL.values(), FORA, ALVO]
    db.add_all([
        User(id_hash=u, username=u, email=f"{u}@teste", hashed_password="x") for u in usuarios
    ])
    db.add(Workspace(id_hash=WS, name="A", owner_id=USUARIO_DO_PAPEL["owner"]))
    db.add_all([
        WorkspaceMember(workspace_id=WS, user_id=USUARIO_DO_PAPEL[papel], role=papel)
        for papel in ("admin", "operator", "editor", "viewer")
    ])
    db.add(WorkspaceMember(workspace_id=WS, user_id=ALVO, role="viewer"))
    vazio = {"nodes": [], "edges": []}
    db.add(Workflow(id_hash=WF, name="Fluxo", workspace_id=WS, definition=vazio, flag_ative=True))
    db.add(Workflow(
        id_hash=WF_APAGADO, name="Apagado", workspace_id=WS, definition=vazio,
        flag_ative=True, deleted_at=datetime(2026, 9, 1),
    ))
    db.add(WorkflowGroup(id_hash=GRUPO, name="Grupo", workspace_id=WS))
    db.add(Artifact(id_hash=ARTEFATO, workspace_id=WS, output_key="saida", filename="a.geojson"))
    db.add(WorkspaceFile(
        id_hash=ARQUIVO, workspace_id=WS, original_name="a.csv", extension="csv",
        s3_key=f"drive/{WS}/a.csv",
    ))
    await db.commit()


@pytest.fixture
async def cliente(client, monkeypatch):
    """The real app, with the database swapped for SQLite and the user chosen by header.

    Depends on the conftest `client` for the infrastructure patches (and for
    cleaning up the overrides at the end), but talks through its own client with
    `raise_app_exceptions=False`: a route that forgot the guard would proceed
    to the handler, and the test must fail with the status it returned, not
    with the exception of a storage that does not exist here.
    """
    from app.api.dependencies import get_current_user, get_db, get_user_workspace_ids
    from app.core.rate_limiter import limiter
    from app.main import app
    from app.models.base import Base
    from app.models.workflow_group import WorkflowGroup

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[*TABELAS, WorkflowGroup.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as db:
        await _semear(db)

    async def _db():
        async with fabrica() as sessao:
            yield sessao

    async def _quem(request: Request):
        uid = request.headers["x-usuario"]
        return SimpleNamespace(
            id_hash=uid, username=uid, email=f"{uid}@teste", role="user", is_active=True,
        )

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _quem
    # The conftest `client` pins the workspaces to a fake value; here they
    # come from the members table, as in production.
    app.dependency_overrides.pop(get_user_workspace_ids, None)
    monkeypatch.setattr(limiter, "enabled", False)

    transporte = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transporte, base_url="http://teste") as ac:
        yield ac
    await engine.dispose()


def _como(usuario: str) -> dict[str, str]:
    return {"x-usuario": usuario}


def _url(caminho: str, id_hash: str) -> str:
    """The registered path with the parameters filled in."""
    return (
        caminho.replace("{id_hash}", id_hash)
        .replace("{version_number}", "1")
        .replace("{run_id}", "run-1")
        .replace("{node_id}", "n1")
        .replace("{job_id}", "job-1")
    )


def _status_e_mensagem(resposta) -> tuple[int, object]:
    """`http_exception_handler` devolve o `detail` em `message`."""
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = resposta.text
    return resposta.status_code, corpo.get("message") if isinstance(corpo, dict) else corpo


# ══════════════════════════════════════════════════════════════════════════════
# 1. Workflow routes: the role is declared in the dependency
# ══════════════════════════════════════════════════════════════════════════════

def test_toda_rota_de_workflow_declara_o_papel_na_dependencia():
    """A route that loads the workflow from the path without `workflow_com_papel` is
    the route that can forget the check — that is what happened with pins and scheduling."""
    sem_papel = sorted(
        f"{metodo} {caminho}"
        for (metodo, caminho), rota in _rotas_de_workflow().items()
        if _papel_declarado(rota) is None
    )
    assert not sem_papel, (
        "rota de workflow sem papel declarado na dependência — use "
        "`Depends(workflow_com_papel(minimo))` (None = basta pertencer):\n  "
        + "\n  ".join(sem_papel)
    )


def test_o_papel_declarado_e_o_da_matriz():
    rotas = _rotas_de_workflow()
    fora_da_matriz = sorted(f"{m} {p}" for m, p in set(rotas) - set(PAPEL_DAS_ROTAS_DE_WORKFLOW))
    sumidas = sorted(f"{m} {p}" for m, p in set(PAPEL_DAS_ROTAS_DE_WORKFLOW) - set(rotas))
    assert not fora_da_matriz, (
        "rota de workflow nova: registre o papel mínimo dela em "
        "PAPEL_DAS_ROTAS_DE_WORKFLOW:\n  " + "\n  ".join(fora_da_matriz)
    )
    assert not sumidas, "rota saiu da app — tire a linha da matriz:\n  " + "\n  ".join(sumidas)

    divergentes = []
    for chave, rota in sorted(rotas.items()):
        dependencia = _papel_declarado(rota)
        esperado = PAPEL_DAS_ROTAS_DE_WORKFLOW[chave][0]
        if dependencia is not None and dependencia.papel_minimo != esperado:
            divergentes.append(f"{chave}: declara {dependencia.papel_minimo!r}, a matriz diz {esperado!r}")
    assert not divergentes, "\n".join(divergentes)


@pytest.mark.parametrize("chave", list(PAPEL_DAS_ROTAS_DE_WORKFLOW), ids=" ".join)
async def test_a_dependencia_deixa_passar_do_minimo_para_cima(chave):
    """The other side of the matrix: the guard must not refuse those who have the role."""
    minimo = PAPEL_DAS_ROTAS_DE_WORKFLOW[chave][0]
    dependencia = _papel_declarado(_rotas_de_workflow()[chave])
    assert dependencia is not None, f"{chave} não declara papel"
    wf = object()
    inicio = 0 if minimo is None else WORKSPACE_ROLE_ORDER.index(minimo)
    for papel in WORKSPACE_ROLE_ORDER[inicio:]:
        assert await dependencia((wf, papel)) is wf, papel


_CASOS_DE_WORKFLOW = [
    pytest.param(metodo, caminho, papel, id=f"{metodo} {caminho} como {papel}")
    for (metodo, caminho), (minimo, _) in PAPEL_DAS_ROTAS_DE_WORKFLOW.items()
    for papel in _abaixo_de(minimo)
]


@pytest.mark.parametrize("metodo, caminho, papel", _CASOS_DE_WORKFLOW)
async def test_rota_de_workflow_recusa_papel_abaixo_do_minimo(cliente, metodo, caminho, papel):
    """No body on purpose: the guard is in the dependency and answers before
    body validation, so the matrix does not need to know how to build each one."""
    mensagem = PAPEL_DAS_ROTAS_DE_WORKFLOW[(metodo, caminho)][1]
    resposta = await cliente.request(metodo, _url(caminho, WF), headers=_como(USUARIO_DO_PAPEL[papel]))
    assert _status_e_mensagem(resposta) == (403, mensagem)


@pytest.mark.parametrize("metodo, caminho", list(PAPEL_DAS_ROTAS_DE_WORKFLOW), ids=" ".join)
async def test_rota_de_workflow_404_antes_de_403(cliente, metodo, caminho):
    """From outside the workspace: membership 403. Nonexistent workflow or one in
    the trash: 404 — for outsiders AND for those without the role."""
    resposta = await cliente.request(metodo, _url(caminho, WF), headers=_como(FORA))
    assert _status_e_mensagem(resposta) == (403, _NAO_MEMBRO)

    for sumido in ("wf-nao-existe", WF_APAGADO):
        for usuario in (FORA, USUARIO_DO_PAPEL["viewer"]):
            resposta = await cliente.request(metodo, _url(caminho, sumido), headers=_como(usuario))
            assert _status_e_mensagem(resposta) == (404, f"Workflow '{sumido}' não encontrado"), (
                sumido, usuario,
            )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Workspace routes: the check runs in the handler
# ══════════════════════════════════════════════════════════════════════════════

def test_toda_rota_de_escrita_de_workspace_esta_na_matriz():
    """A new write route in one of these routers must state the role it requires
    — or, in `SEM_PAPEL_DE_WORKSPACE`, why it requires none."""
    registradas = {(r.metodo, r.caminho) for r in ROTAS_DE_WORKSPACE} | set(SEM_PAPEL_DE_WORKSPACE)
    existentes = set()
    for rota in _rotas():
        if rota.endpoint.__module__.rsplit(".", 1)[-1] not in _ROUTERS or _e_rota_de_workflow(rota):
            continue
        existentes |= {(metodo, rota.path) for metodo in rota.methods & _ESCRITA}

    faltando = sorted(f"{m} {p}" for m, p in existentes - registradas)
    sumidas = sorted(f"{m} {p}" for m, p in registradas - existentes)
    assert not faltando, (
        "rota de escrita sem papel registrado — acrescente-a em ROTAS_DE_WORKSPACE "
        "(ou em SEM_PAPEL_DE_WORKSPACE, com o motivo):\n  " + "\n  ".join(faltando)
    )
    assert not sumidas, "rota saiu da app — tire a linha da matriz:\n  " + "\n  ".join(sumidas)


_CASOS_DE_WORKSPACE = [
    pytest.param(rota, papel, id=f"{rota.metodo} {rota.caminho} como {papel or 'de fora'}")
    for rota in ROTAS_DE_WORKSPACE
    for papel in [*_abaixo_de(rota.minimo), None]
]


@pytest.mark.parametrize("rota, papel", _CASOS_DE_WORKSPACE)
async def test_rota_de_workspace_recusa_papel_abaixo_do_minimo(cliente, rota, papel):
    usuario = USUARIO_DO_PAPEL[papel] if papel else FORA
    esperado = rota.mensagem if papel else (rota.mensagem_fora or rota.mensagem)
    extras: dict = {}
    if rota.json is not None:
        extras["json"] = rota.json
    if rota.arquivo:
        extras["files"] = {"file": ("dados.csv", b"a,b\n1,2\n", "text/csv")}
    resposta = await cliente.request(rota.metodo, rota.url, headers=_como(usuario), **extras)
    assert _status_e_mensagem(resposta) == (403, esperado)
