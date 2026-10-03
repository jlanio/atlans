import os
import uvicorn
import logging
from collections.abc import Awaitable, Callable
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.db import engine
# Imports all models so Base.metadata registers them before create_all
from app.models import models, user, workspace, credential, system_config, workspace_member, artifact, executor, portal_layer, portal_feature, run_metrics  # noqa: F401

from app.core.utils.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    rate_limit_exceeded_global_handler,
    atlas_domain_error_handler,
)
from app.core.exceptions import AtlasBaseError
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded

from app.api.routers import (
    webhook_router,
    workflows_router,
    schedules_router,
    nodes_router,
    log_workflows_router,
    telemetry_router,
    credentials_router,
    observability_router,
)
from app.api.routers import auth_router, workspace_router, api_tokens_router, assistente_editor_router
from app.api.routers.me_router import router as me_router
from app.api.routers.assistente_camadas_router import router as assistente_camadas_router
from app.api.routers.assistente_router import router as assistente_router
from app.api.routers.workflow_groups_router import router as workflow_groups_router
from app.api.routers.health_router import router as health_router
from app.api.routers.executores_router import router as executores_router
from app.api.routers.executor_ws_router import router as executor_ws_router
from app.api.routers.artifacts_router import router as artifacts_router, public_router as artifacts_public_router
from app.api.routers.portal_router import router as portal_router
from app.api.routers.drive_router import router as drive_router
from app.api.routers.drive_admin_router import router as drive_admin_router
from app.api.routers.executor_drive_router import router as executor_drive_router
from app.api.routers.admin_users_router import router as admin_users_router
from app.api.routers.admin_assistente_router import router as admin_assistente_router
from app.api.routers.admin_nodes_router import router as admin_nodes_router
from app.api.routers.admin_workflows_router import router as admin_workflows_router
from app.api.routers.admin_workspaces_router import router as admin_workspaces_router
from app.api.routers.internal_email_router import router as internal_email_router
from app.api.routers.change_detector_router import router as change_detector_router
from app.core.rate_limiter import limiter
from app.extensoes import registro as registro_das_extensoes
from app.core.config import ALLOWED_ORIGINS
from app.core.constants import HSTS_MAX_AGE

logger = logging.getLogger("uvicorn.error")


# Waiting for the database at startup. Jitter matters even here: with more than
# one API replica starting together (deploy, orchestrator restart), all of them
# re-queried the database at the same instant — precisely when it is
# recovering.
_DB_TENTATIVAS = 10
_DB_ESPERA_INICIAL_S = 2.0
_DB_ESPERA_MAX_S = 30.0


async def _wait_for_db() -> None:
    """
    Waits for the database to become reachable (up to 10 attempts with backoff).
    Does not create tables — that is Alembic's responsibility (`alembic upgrade head`).
    """
    import asyncio
    from flow.utils.backoff import espera_exponencial

    for attempt in range(1, _DB_TENTATIVAS + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            return
        except Exception as exc:
            if attempt == _DB_TENTATIVAS:
                raise
            espera = espera_exponencial(
                attempt - 1, inicial=_DB_ESPERA_INICIAL_S, teto=_DB_ESPERA_MAX_S
            )
            logger.warning(
                "Banco indisponível (tentativa %d/%d): %s — aguardando %.1fs...",
                attempt, _DB_TENTATIVAS, exc, espera,
            )
            await asyncio.sleep(espera)


def _tarefas_de_fundo() -> list[tuple[str, Callable[[], Awaitable[object]]]]:
    """The lifespan's background tasks, in the order they start: (name, factory).

    Imported here, at startup (as they always were), and not at the top of the
    module. The lifespan starts all of them after Redis and, on shutdown,
    cancels and AWAITS all of them before closing the database and Redis: a
    task that is only canceled still runs its own teardown with the pool
    already closed, and the loop ends with "Task was destroyed but it is
    pending!".
    """
    from app.core.run_result_consumer import run_consumer_loop
    from app.core.artifact_cleanup import run_cleanup_loop
    from app.core.storage_reconciliation import run_reconciliation_loop
    from app.core.fontes_catalogo import importar_catalogo_no_arranque, run_verificacao_loop
    from app.core.executor_connections import overdue_acks_monitor
    from app.api.routers.executor_ws_router import orphan_runs_watchdog

    return [
        # Consumer of the results the executors publish to Redis.
        ("Consumer de resultados", run_consumer_loop),
        ("Cleanup de artefatos", run_cleanup_loop),
        # Periodic storage reconciliation: fills NULL size_bytes in Artifact,
        # deletes stale pending WorkspaceFile, aborts abandoned multipart, measures
        # DB vs MinIO drift. A Redis lock prevents duplicate execution with several workers.
        ("Reconciliação do storage", run_reconciliation_loop),
        # Source catalog (WFS): imports the versioned seed (catalogo/geoservicos)
        # once at startup — idempotent by hash, Redis lock across workers — and
        # checks the endpoints periodically (one GetCapabilities per distinct URL).
        ("Importação do catálogo", importar_catalogo_no_arranque),
        ("Verificação de fontes", run_verificacao_loop),
        # Monitor for late ACKs — logs when a job leaves the server but the executor
        # does not confirm enqueueing. Helps diagnose "in-flight" workflows.
        ("Monitor de ACKs", overdue_acks_monitor),
        # Orphan run watchdog — a safety net for when the uvicorn worker
        # dies from SIGKILL/OOM and the WS handler's cleanup never runs.
        # Periodically enumerates 'running' runs whose executor lost presence
        # in Redis and marks them as failed.
        ("Watchdog de runs órfãos", orphan_runs_watchdog),
        # The extensions' ones (app/extensoes), with the same teardown.
        *registro_das_extensoes().tarefas_de_fundo,
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.core.redis import init_redis, close_redis
    from app.core.async_scheduler import scheduler

    # Waits for the database to become available (tables are created/migrated by Alembic)
    await _wait_for_db()

    # Centralized Redis pool — initialized once and closed on shutdown
    app.state.redis = await init_redis()

    try:
        await app.state.redis.ping()
        logger.info("Redis conectado com sucesso.")
    except Exception as e:
        logger.error("Falha ao conectar no Redis: %s", e)

    # MinIO: garante que o bucket existe
    try:
        from app.core.storage import ensure_bucket
        ensure_bucket()
    except Exception as e:
        logger.warning("MinIO indisponivel no startup: %s", e)
    # A warning, never an error: in dev the local endpoint is what is expected; in
    # production it is the symptom of a forgotten .env, and the failure would only show up as a broken link.
    from app.core import storage as _storage
    if _storage.endpoint_externo_e_local():
        logger.warning(
            "MINIO_EXTERNAL_ENDPOINT=%s aponta para a rede local: URLs pré-assinadas "
            "(Drive, artefatos, MCP) não funcionam fora do Docker; em produção use o "
            "endereço público do S3 (ex.: https://s3.seu-dominio)",
            _storage.endpoint_externo(),
        )

    # Background tasks (see `_tarefas_de_fundo`) and the schedule scheduler
    tarefas = [
        (nome, asyncio.create_task(fabrica(), name=nome)) for nome, fabrica in _tarefas_de_fundo()
    ]
    await scheduler.start()

    # The MCP session manager must be active while the app is serving: it is
    # what keeps the streamable HTTP transport's state. It enters after
    # `init_redis` (the quotas and the token usage stamp depend on the pool) and
    # exits before `close_redis`, down below.
    async with mcp_server.session_manager.run():
        yield

    # Clean shutdown: cancels all background tasks and awaits each one.
    for _, tarefa in tarefas:
        tarefa.cancel()
    resultados = await asyncio.gather(*(tarefa for _, tarefa in tarefas), return_exceptions=True)
    for (nome, _), resultado in zip(tarefas, resultados):
        if isinstance(resultado, BaseException):
            logger.debug("%s encerrada: %s", nome, resultado.__class__.__name__)

    # Each executor disconnection leaves a task sleeping through the grace period
    # before deciding whether to fail the orphan runs (see
    # `_fail_orphan_runs_if_gone`). On shutdown they must be canceled explicitly:
    # without that the loop closes with pending tasks ("Task was destroyed but it
    # is pending!") and, worse, one of them could wake up in the middle of the
    # teardown and try to talk to an already-disposed DB pool. Canceling is the
    # correct behavior — during a server shutdown no run should be failed; the
    # watchdog re-evaluates on the way back.
    from app.api.routers.executor_ws_router import _orphan_check_tasks
    pendentes = list(_orphan_check_tasks)
    for t in pendentes:
        t.cancel()
    if pendentes:
        await asyncio.gather(*pendentes, return_exceptions=True)
        logger.debug("%d verificação(ões) de órfãos canceladas no shutdown.", len(pendentes))
    await scheduler.stop()
    await engine.dispose()
    await close_redis()


# Application instance
app = FastAPI(
    title="Atlas Studio API",
    lifespan=lifespan,
)

# Rate Limiting
app.state.limiter = limiter

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(webhook_router.router)
app.include_router(workflows_router.router)
app.include_router(schedules_router.router)
app.include_router(nodes_router.router)
app.include_router(log_workflows_router.router)
app.include_router(telemetry_router.router)
app.include_router(credentials_router.router)
app.include_router(observability_router.router)
app.include_router(auth_router.router)
app.include_router(api_tokens_router.router)      # Tokens pessoais de acesso (PAT) — /auth/tokens (JWT)
app.include_router(assistente_editor_router.router)        # Assistente do editor — /assistente/editor (JWT), responde em SSE
app.include_router(me_router)                     # "Me" — per-person slices; today GET /me/schedules (JWT)
app.include_router(assistente_camadas_router)         # Home: camadas do globo — /assistente/camadas, /assistente/tiles (JWT, membro)
app.include_router(assistente_router)                 # Home: conversas do assistente — /assistente/conversa[s], /estado (JWT, SSE)
app.include_router(workspace_router.router)
app.include_router(workflow_groups_router)
app.include_router(health_router)
app.include_router(executores_router)
app.include_router(executor_ws_router)
app.include_router(portal_router)                # portal: publish, tiles, portal data (public)
app.include_router(artifacts_public_router)     # public download by id_hash (no JWT)
app.include_router(artifacts_router)            # listing, deletion and config (JWT)
app.include_router(executor_drive_router)          # Drive: upload via executor (API key auth) — BEFORE drive_router to avoid capture by /drive/{id_hash}
app.include_router(drive_router)                # Drive: upload, listagem, download, delete (JWT)
app.include_router(drive_admin_router)          # Drive: admin settings (JWT + role=admin)
app.include_router(admin_users_router)          # Admin: user management (JWT + role=admin)
app.include_router(admin_nodes_router)          # Admin: habilita/desabilita nodes (JWT + role=admin)
app.include_router(admin_assistente_router)     # Admin: modelo do assistente (JWT + role=admin)
app.include_router(admin_workflows_router)      # Admin: desativa/ativa workflows (JWT + role=admin)
app.include_router(admin_workspaces_router)     # Admin: lixeira de workspaces — restore/purge (JWT + role=admin)
app.include_router(internal_email_router)       # Interno: envio de email via Resend (executor API key auth)
app.include_router(change_detector_router)      # Interno: hash store do node ChangeDetector (executor API key auth)
# The extensions' routes (app/extensoes), after the core's.
for _rota_da_extensao in registro_das_extensoes().rotas:
    app.include_router(_rota_da_extensao)


# ── MCP server (/mcp) ─────────────────────────────────────────────────────────
# `add_route` and not `app.mount`: the EXACT route delivers the path intact, and
# the SDK app matches its own Route("/mcp") against the request's full path. A
# mount would consume the prefix and pass on "" — no inner route would match.
#
# BOTH spellings are registered, and both point to the SAME ASGI app. Without
# the second, "/mcp/" matches no route and the router answers 307 to "/mcp":
# a redirect's Location is built with the scheme the app sees, and behind
# Traefik uvicorn runs without `--proxy-headers`, so the hop would go out as
# `http://` — a client following it would resend the token outside TLS. With
# both routes there is no hop to follow, and Traefik's `PathPrefix(/mcp)`
# already delivers both to the same process. `_CaminhoSemBarraFinal` normalizes
# "/mcp/" to the "/mcp" the SDK app matches, without duplicating transport or
# session manager.
#
# Factory, never a module singleton: `session_manager.run()` can only be
# entered once per instance, and the instance lives in `app.state` so the
# lifespan and the tests can reach it.
#
# The route does not inherit the app's global dependencies (JWT/HMAC): the
# authentication here is the PAT, applied by the middleware that wraps the SDK app.
from app.mcp import create_mcp_server, criar_app_mcp


class _CaminhoSemBarraFinal:
    """Delegates to the inner ASGI app with the path's trailing slash removed.

    An object, not a function: Starlette's `Route` treats a function as an
    endpoint `f(request) -> response` and only calls as pure ASGI what is
    neither a function nor a method. Strips the trailing slash instead of
    writing "/mcp" by hand so as not to lose a possible `root_path` in the prefix.
    """

    def __init__(self, app_asgi):
        self._app = app_asgi

    async def __call__(self, scope, receive, send):
        caminho = scope.get("path") or ""
        if len(caminho) > 1 and caminho.endswith("/"):
            scope = dict(scope)
            scope["path"] = caminho[:-1]
            bruto = scope.get("raw_path")
            if bruto and len(bruto) > 1 and bruto.endswith(b"/"):
                scope["raw_path"] = bruto[:-1]
        await self._app(scope, receive, send)


mcp_server = create_mcp_server()
app.state.mcp_server = mcp_server
_app_mcp = criar_app_mcp(mcp_server)
app.add_route("/mcp", _app_mcp, include_in_schema=False)
app.add_route("/mcp/", _CaminhoSemBarraFinal(_app_mcp), include_in_schema=False)


@app.get("/ping", include_in_schema=False, tags=["health"])
async def ping():
    """Minimal endpoint for the Docker healthcheck — no auth, no slowapi overhead."""
    return {"status": "ok"}


# ── CORS ──────────────────────────────────────────────────────────────────────
_allow_credentials = ALLOWED_ORIGINS != ["*"]
if ALLOWED_ORIGINS == ["*"]:
    logger.warning("CORS allow_origins=['*']. Em producao, defina ALLOWED_ORIGINS.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Idempotency-Key"],
)

# ── Security Headers ─────────────────────────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse


# Content-Security-Policy: blocks active XSS (script injection via workflow
# name, node label, etc). 'unsafe-inline' in script/style is mandatory
# for Next.js — without it, styled-jsx and App Router chunks break. If we
# ever migrate to nonce/hash, remove it.
# connect-src allows HTTPS/WSS to the API + Redis pub/sub WebSockets.
# frame-ancestors 'none' blocks iframes on any origin (defense-in-
# depth together with X-Frame-Options: DENY).
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https: wss:; "
    "media-src 'self' blob:; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


# CSP for a response whose BODY is user-controlled and renderable by the
# browser — today only the webhook's ResponseNode returning `text/html`.
#
# `sandbox` without tokens puts the document in an opaque origin and blocks
# scripts, forms, popups and plugins. The HTML still renders (with styles and
# images), but a `<script>` coming from the body does not run. That way
# `text/html` remains an option the node advertises, without becoming reflected
# XSS on the API's origin.
#
# Downgrading the Content-Type would be the alternative, but it would silently
# break every workflow that today picks "HTML (text/html)" on the canvas.
_CSP_CORPO_NAO_CONFIAVEL = (
    "sandbox; "
    "default-src 'none'; "
    "style-src 'unsafe-inline'; "
    "img-src data: https:; "
    "font-src data:"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response: StarletteResponse = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # The handler marks in `request.state` when the body came from the user — the
        # header does not work as a channel because this line overwrites the CSP of
        # any response.
        if getattr(request.state, "corpo_nao_confiavel", False):
            response.headers["Content-Security-Policy"] = _CSP_CORPO_NAO_CONFIAVEL
        else:
            response.headers["Content-Security-Policy"] = _CSP
        # HSTS — only when explicit origins are configured (not in local dev)
        if ALLOWED_ORIGINS != ["*"]:
            response.headers["Strict-Transport-Security"] = f"max-age={HSTS_MAX_AGE}; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# ── GZip — comprime respostas > 1KB automaticamente ──────────────────────────
# PERF: GZip comprime respostas > 1 KB — reduz ~70% em JSON/GeoJSON grandes.
# Ativado para observabilidade, portal e artefatos.
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(AtlasBaseError, atlas_domain_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_global_handler)
app.add_exception_handler(Exception, generic_exception_handler)

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run("app.main:app", host=host, port=port, ws_max_size=16 * 1024 * 1024)
