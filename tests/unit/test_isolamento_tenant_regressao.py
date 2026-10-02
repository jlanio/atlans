"""Regressoes de isolamento de inquilino da auditoria de 28/08/2026.

Um teste por achado corrigido. Os tres primeiros sao correcoes de UMA LINHA no
`where` de um select — exatamente o tipo que volta sem querer num merge, e que
nao quebra nenhum teste funcional quando volta (a rota continua respondendo
200; so passa a responder com dado alheio).

F3  workflow_groups vinculava Workflow resolvido so por id_hash (escrita cross-tenant).
F4  /executores/{id}/status e /workspaces aceitavam qualquer JWT (leitura cross-tenant).
F5  GET /workspaces/{id}/executor nao checava associacao ao workspace.
F7  `OR workspace_id IS NULL` tornava linha legada visivel a todo autenticado.
F9  ResponseNode definia Content-Type e cabecalhos arbitrarios na resposta.

O teste de varredura no fim (`test_varredura_*`) e o de maior alcance: em vez de
um caso por rota, ele afirma a INVARIANTE sobre o codigo — nenhuma consulta de
tenant pode carregar um escape por NULL.
"""
import inspect
import re
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


# ── F3: escrita cross-tenant em workflow_groups ──────────────────────────────

@pytest.fixture
async def banco():
    """SQLite em memoria com as tabelas REAIS de workflows e grupos.

    Vale o custo de um banco de verdade: a falha original nao mudava o codigo de
    status (a rota respondia 204 nos dois casos, so que gravando na linha
    errada), entao so olhando a linha depois do commit da para prova-la.
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


async def _semear(sessao):
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
async def test_f3_alvos_agrupaveis_recusa_workflow_de_outro_workspace(banco):
    from sqlalchemy import select

    from app.api.routers.workflow_groups_router import _alvos_agrupaveis
    from app.models.models import Workflow

    grupo = await _semear(banco)

    achados = (await banco.execute(
        select(Workflow).where(*_alvos_agrupaveis(["wf-meu", "wf-alheio"], grupo))
    )).scalars().all()

    assert {w.id_hash for w in achados} == {"wf-meu"}, (
        "workflow de outro workspace entrou no conjunto agrupável — "
        "escrita cross-tenant reaberta"
    )


@pytest.mark.asyncio
async def test_f3_workflow_desativado_continua_agrupavel(banco):
    """Regressao introduzida na primeira versao da correcao: com
    `flag_ative.is_(True)` no filtro, um workflow desativado que o usuario
    marcou na lista virava "nao encontrado" e derrubava a criacao do grupo
    inteira. Agrupar e organizacao, nao execucao."""
    from sqlalchemy import select

    from app.api.routers.workflow_groups_router import _alvos_agrupaveis
    from app.models.models import Workflow

    grupo = await _semear(banco)

    achados = (await banco.execute(
        select(Workflow).where(*_alvos_agrupaveis(["wf-inativo"], grupo))
    )).scalars().all()

    assert [w.id_hash for w in achados] == ["wf-inativo"]


@pytest.mark.asyncio
async def test_f3_workflow_na_lixeira_nao_e_agrupavel(banco):
    from sqlalchemy import select

    from app.api.routers.workflow_groups_router import _alvos_agrupaveis
    from app.core.utils.datetime_utils import utc_now_naive
    from app.models.models import Workflow

    grupo = await _semear(banco)
    (await banco.execute(select(Workflow).where(Workflow.id_hash == "wf-meu"))) \
        .scalar_one().deleted_at = utc_now_naive()
    await banco.commit()

    achados = (await banco.execute(
        select(Workflow).where(*_alvos_agrupaveis(["wf-meu"], grupo))
    )).scalars().all()

    assert achados == []


def test_f3_id_fora_do_grupo_e_recusado_com_404():
    from app.api.routers.workflow_groups_router import _recusar_ids_fora_do_grupo

    encontrado = MagicMock(id_hash="wf-meu")
    with pytest.raises(HTTPException) as exc:
        _recusar_ids_fora_do_grupo(["wf-meu", "wf-alheio"], [encontrado])

    assert exc.value.status_code == 404
    # Nao distingue "nao existe" de "e de outro tenant" — senao vira oraculo.
    assert "wf-alheio" in exc.value.detail


def test_f3_todos_os_ids_conhecidos_nao_levanta():
    from app.api.routers.workflow_groups_router import _recusar_ids_fora_do_grupo

    _recusar_ids_fora_do_grupo(["a"], [MagicMock(id_hash="a")])


_ROTAS_QUE_VINCULAM_WORKFLOW = [
    "create_group",
    "update_group",
    "delete_group",
    "add_workflow_to_group",
    "remove_workflow_from_group",
]


@pytest.mark.parametrize("nome_rota", _ROTAS_QUE_VINCULAM_WORKFLOW)
def test_f3_toda_rota_que_mexe_em_group_id_casa_o_workspace(nome_rota):
    """Complementa os testes de banco: garante que nenhuma das cinco rotas
    resolva `Workflow` por fora do criterio compartilhado.

    Aceita as duas formas (helper ou filtro literal) para nao travar refatoracao
    que continue correta.
    """
    from app.api.routers import workflow_groups_router

    fonte = inspect.getsource(getattr(workflow_groups_router, nome_rota))

    assert (
        "_alvos_agrupaveis" in fonte
        or "Workflow.workspace_id == group.workspace_id" in fonte
    ), f"{nome_rota} resolve Workflow sem casar o workspace do grupo"


def test_f3_create_group_nao_usa_mais_a_checagem_permissiva_antiga():
    """`if wf.workspace_id and wf.workspace_id != ...` deixava passar NULL.

    Era a unica das cinco rotas que validava, mas o `and` curto-circuitava em
    workflow legado sem workspace — que era justamente o caso mais exposto.
    """
    from app.api.routers import workflow_groups_router

    fonte = inspect.getsource(workflow_groups_router.create_group)
    assert "if wf.workspace_id and" not in fonte


# ── F4: leitura de executor por qualquer conta ───────────────────────────────

def _quem(*, executor_id=None, user_role=None, user_id="u-1"):
    from app.api.dependencies import ExecutorOuUsuario

    if executor_id is not None:
        return ExecutorOuUsuario(executor=MagicMock(id_hash=executor_id))
    return ExecutorOuUsuario(user=MagicMock(role=user_role, id_hash=user_id))


def _executor(id_hash="exec-1", created_by="dono-1"):
    return MagicMock(id_hash=id_hash, created_by=created_by)


def test_f4_usuario_comum_nao_le_executor_alheio():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    with pytest.raises(HTTPException) as exc:
        _assert_pode_ler_executor(_quem(user_role="user", user_id="intruso"), _executor())
    assert exc.value.status_code == 403


def test_f4_admin_le_qualquer_executor():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    _assert_pode_ler_executor(_quem(user_role="admin", user_id="adm"), _executor())


def test_f4_dono_le_o_proprio_executor():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    _assert_pode_ler_executor(
        _quem(user_role="user", user_id="dono-1"), _executor(created_by="dono-1")
    )


def test_f4_executor_le_a_si_mesmo():
    from app.api.routers.executores_router import _assert_pode_ler_executor

    _assert_pode_ler_executor(_quem(executor_id="exec-1"), _executor(id_hash="exec-1"))


def test_f4_executor_nao_enumera_a_frota():
    """Qualquer usuario pode criar e enrolar um executor dedicado; sem esta
    guarda, um executor comprometido lia o status de todos os outros."""
    from app.api.routers.executores_router import _assert_pode_ler_executor

    with pytest.raises(HTTPException) as exc:
        _assert_pode_ler_executor(_quem(executor_id="exec-9"), _executor(id_hash="exec-1"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_f4_token_revogado_e_recusado():
    """`agent_mtls_or_user_auth` usava `decode_token` solto: pulava a blacklist e
    o lookup do User, entao token de sessao encerrada por /auth/logout — ou de
    usuario suspenso — seguia valendo ate expirar sozinho."""
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
def test_f4_identidade_ambigua_e_recusada_na_construcao(kwargs):
    """Estado invalido nao pode chegar ao helper de autorizacao: la ele viraria
    `None.role` -> AttributeError -> 500, que nao nega nem concede acesso."""
    from app.api.dependencies import ExecutorOuUsuario

    with pytest.raises(ValueError):
        ExecutorOuUsuario(**kwargs)


def test_f4_rotas_de_executor_chamam_o_gate():
    from app.api.routers import executores_router

    for nome in ("agent_status", "agent_workspaces_endpoint"):
        fonte = inspect.getsource(getattr(executores_router, nome))
        assert "_assert_pode_ler_executor" in fonte, f"{nome} voltou a autenticar sem autorizar"


# ── F5: GET /workspaces/{id}/executor ────────────────────────────────────────

def test_f5_get_executor_do_workspace_usa_o_gate_de_visibilidade():
    """Sem `_get_visible_workspace`, a rota devolvia `target_executor_id` de
    qualquer workspace e ainda distinguia 404 de 200 — oraculo de enumeracao."""
    from app.api.routers import workspace_router

    fonte = inspect.getsource(workspace_router.get_workspace_agent)
    assert "_get_visible_workspace" in fonte


# ── F7: escape de tenant por workspace_id NULL ───────────────────────────────

@pytest.mark.parametrize(
    "metodo",
    [
        "get_all_metadata",
        "get_all_metadata_by_workspace_ids",
    ],
)
def test_f7_listagem_de_workflows_nao_tem_escape_por_nulo(metodo):
    from app.crud.workflow_crud import WorkflowCRUD

    fonte = inspect.getsource(getattr(WorkflowCRUD, metodo))
    assert "workspace_id.is_(None)" not in fonte


def test_f7_credential_usage_nao_tem_escape_por_nulo():
    from app.api.routers import credentials_router

    fonte = inspect.getsource(credentials_router.credential_usage)
    assert "workspace_id.is_(None)" not in fonte


@pytest.mark.parametrize("modelo", ["Workflow", "WorkflowRun"])
def test_f7_coluna_workspace_id_e_not_null(modelo):
    """A garantia de verdade: com a coluna NOT NULL, nenhuma consulta futura
    precisa (nem consegue justificar) o `OR workspace_id IS NULL`."""
    import app.models.models as m

    coluna = getattr(m, modelo).__table__.c.workspace_id
    assert coluna.nullable is False


def test_f7_workflow_create_exige_workspace():
    from pydantic import ValidationError

    from app.schemas.workflow import WorkflowCreate

    with pytest.raises(ValidationError):
        WorkflowCreate(name="x", definition={"nodes": []})

    wf = WorkflowCreate(name="x", definition={"nodes": []}, workspace_id="ws-1")
    assert wf.workspace_id == "ws-1"


# ── F9: resposta do ResponseNode ─────────────────────────────────────────────

def _req():
    """Request minimo — so precisa de `.state` mutavel."""
    from types import SimpleNamespace

    return SimpleNamespace(state=SimpleNamespace())


@pytest.mark.parametrize(
    "tipo", ["image/svg+xml", "application/xhtml+xml", "text/x-python", "image/png"]
)
def test_f9_content_type_fora_da_allowlist_e_rebaixado(tipo):
    from app.api.routers.webhook_router import _sanear_resposta_do_node

    content_type, headers = _sanear_resposta_do_node({"content_type": tipo}, _req())

    assert content_type.startswith("text/plain")
    assert headers["Content-Type"].startswith("text/plain")


@pytest.mark.parametrize(
    "tipo",
    [
        # Os cinco que o dropdown do ResponseNode oferece — rebaixar qualquer um
        # deles quebraria workflows existentes em silencio.
        "application/json", "text/plain", "text/html", "application/xml", "text/csv",
        "application/geo+json",
    ],
)
def test_f9_content_type_anunciado_pelo_node_nao_e_rebaixado(tipo):
    """Regressao: a primeira versao desta allowlist NAO incluia `text/html`, que
    e opcao selecionavel no canvas (flow/nodes/outputs/response_node.py). O
    efeito era um downgrade silencioso — a pagina passava a chegar como texto,
    com aviso so no log do servidor."""
    from app.api.routers.webhook_router import _sanear_resposta_do_node

    content_type, _ = _sanear_resposta_do_node({"content_type": tipo}, _req())
    assert content_type == tipo


@pytest.mark.parametrize("tipo", ["text/html", "text/html; charset=utf-8", "TEXT/HTML"])
def test_f9_html_marca_o_corpo_como_nao_confiavel(tipo):
    """Preserva o recurso e ainda mata o XSS: o middleware troca a CSP por uma
    com `sandbox` quando esta marca esta presente."""
    from app.api.routers.webhook_router import _sanear_resposta_do_node

    request = _req()
    _sanear_resposta_do_node({"content_type": tipo}, request)

    assert request.state.corpo_nao_confiavel is True


@pytest.mark.parametrize("tipo", ["application/json", "text/csv", "text/plain"])
def test_f9_tipo_nao_renderizavel_nao_endurece_a_csp(tipo):
    """A CSP restrita nao pode vazar para resposta comum de integracao."""
    from app.api.routers.webhook_router import _sanear_resposta_do_node

    request = _req()
    _sanear_resposta_do_node({"content_type": tipo}, request)

    assert getattr(request.state, "corpo_nao_confiavel", False) is False


def test_f9_csp_de_corpo_nao_confiavel_bloqueia_script():
    from app.main import _CSP_CORPO_NAO_CONFIAVEL

    assert "sandbox" in _CSP_CORPO_NAO_CONFIAVEL
    assert "default-src 'none'" in _CSP_CORPO_NAO_CONFIAVEL
    assert "script-src" not in _CSP_CORPO_NAO_CONFIAVEL
    assert "unsafe-inline" not in _CSP_CORPO_NAO_CONFIAVEL.replace("style-src 'unsafe-inline'", "")


def test_f9_middleware_aplica_csp_restrita_de_ponta_a_ponta():
    """Comportamental, e nao inspecao de fonte: sobe o middleware REAL e compara
    as duas respostas.

    A marca vai por `request.state` porque o middleware sobrescreve o header
    `Content-Security-Policy` de TODA resposta — defini-lo no handler seria
    descartado. Este teste e o que prova que o canal funciona.
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

    # A rota comum mantem a CSP da aplicacao (que permite script proprio).
    assert "script-src 'self'" in csp_normal
    assert "sandbox" not in csp_normal

    # A rota de corpo nao confiavel roda em origem opaca, sem script.
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
        "x-content-type-options",   # caixa nao importa
    ],
)
def test_f9_cabecalho_de_seguranca_nao_pode_ser_sobrescrito(cabecalho):
    from app.api.routers.webhook_router import _sanear_resposta_do_node

    _, headers = _sanear_resposta_do_node(
        {"headers": {cabecalho: "valor-do-atacante"}}, _req()
    )

    assert cabecalho not in headers
    assert cabecalho.lower() not in {k.lower() for k in headers}


def test_f9_cabecalho_proprio_do_workflow_passa():
    """A allowlist nao pode custar o uso legitimo — integracoes usam headers
    proprios para correlacionar a resposta."""
    from app.api.routers.webhook_router import _sanear_resposta_do_node

    _, headers = _sanear_resposta_do_node({"headers": {"X-Request-Id": "abc-123"}}, _req())

    assert headers["X-Request-Id"] == "abc-123"


@pytest.mark.parametrize("brutos", ["uma-string", ["a", "b"], 42, True])
def test_f9_headers_nao_dict_nao_derruba_o_handler(brutos):
    """`headers` e campo livre do tipo `object` no no e chega como JSON do
    executor. `.items()` numa string levantava AttributeError, que o handler nao
    captura — virava 500 em vez de ser ignorado."""
    from app.api.routers.webhook_router import _sanear_resposta_do_node

    _, headers = _sanear_resposta_do_node({"headers": brutos}, _req())

    assert set(headers) == {"Content-Type"}


# ── Varredura: a invariante, e nao mais um caso por rota ─────────────────────

_MODULOS_COM_CONSULTA_DE_TENANT = [
    "app.api.routers.credentials_router",
    "app.api.routers.workflow_groups_router",
    "app.api.routers.workflows_router",
    "app.api.routers.artifacts_router",
    "app.api.routers.drive_router",
    # F5 fatiou os monolitos: os NOVOS donos do codigo movido entram na
    # varredura junto (a rede de regressao nao pode encolher com refactor).
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
_ESCAPE_POR_NULO = re.compile(r"workspace_id\s*\.\s*is_\(\s*None\s*\)")


@pytest.mark.parametrize("modulo", _MODULOS_COM_CONSULTA_DE_TENANT)
def test_varredura_nenhum_modulo_reintroduz_escape_por_workspace_nulo(modulo):
    """Afirma a INVARIANTE, nao um caso.

    As tres falhas de isolamento da auditoria tinham a mesma assinatura. Um
    teste por rota protege as rotas que existiam naquele dia; este protege
    tambem as que ainda vao ser escritas nesses modulos.
    """
    import importlib

    fonte = inspect.getsource(importlib.import_module(modulo))
    # Descarta comentarios e docstrings de uma linha que CITAM o padrao ao
    # explicar por que ele foi removido.
    codigo = "\n".join(
        linha for linha in fonte.splitlines() if not linha.lstrip().startswith("#")
    )

    achados = _ESCAPE_POR_NULO.findall(codigo)
    assert not achados, (
        f"{modulo} voltou a usar `workspace_id.is_(None)`: isso torna a linha "
        "visivel a qualquer usuario autenticado, de qualquer tenant."
    )
