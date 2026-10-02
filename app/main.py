import os
import uvicorn
import logging
from collections.abc import Awaitable, Callable
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.db import engine
# Importa todos os modelos para que Base.metadata os registre antes do create_all
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


# Espera do banco na subida. O jitter importa mesmo aqui: com mais de uma
# replica da API subindo junto (deploy, restart do orquestrador), todas
# reconsultavam o banco no mesmo instante — justo quando ele esta se
# recuperando.
_DB_TENTATIVAS = 10
_DB_ESPERA_INICIAL_S = 2.0
_DB_ESPERA_MAX_S = 30.0


async def _wait_for_db() -> None:
    """
    Aguarda o banco ficar acessível (até 10 tentativas com backoff).
    Não cria tabelas — isso é responsabilidade do Alembic (`alembic upgrade head`).
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
    """As tarefas de fundo do lifespan, na ordem em que sobem: (nome, fábrica).

    Importadas aqui, na subida (como sempre foram), e não no topo do módulo. O
    lifespan sobe todas depois do Redis e, no shutdown, cancela e AGUARDA todas
    antes de fechar o banco e o Redis: uma tarefa só cancelada ainda roda o
    próprio encerramento com o pool já fechado, e o loop acaba com "Task was
    destroyed but it is pending!".
    """
    from app.core.run_result_consumer import run_consumer_loop
    from app.core.artifact_cleanup import run_cleanup_loop
    from app.core.storage_reconciliation import run_reconciliation_loop
    from app.core.fontes_catalogo import importar_catalogo_no_arranque, run_verificacao_loop
    from app.core.executor_connections import overdue_acks_monitor
    from app.api.routers.executor_ws_router import orphan_runs_watchdog

    return [
        # Consumer dos resultados que os executores publicam no Redis.
        ("Consumer de resultados", run_consumer_loop),
        ("Cleanup de artefatos", run_cleanup_loop),
        # Reconciliacao periodica do storage: preenche size_bytes NULL em Artifact,
        # apaga WorkspaceFile pending stale, aborta multipart abandonado, mede drift
        # DB vs MinIO. Lock Redis evita execucao duplicada com varios workers.
        ("Reconciliação do storage", run_reconciliation_loop),
        # Catálogo de fontes (WFS): importa a semente versionada (catalogo/geoservicos)
        # uma vez na subida — idempotente por hash, lock Redis entre workers — e
        # verifica os endpoints por período (um GetCapabilities por URL distinta).
        ("Importação do catálogo", importar_catalogo_no_arranque),
        ("Verificação de fontes", run_verificacao_loop),
        # Monitor de ACKs atrasados — loga quando um job sai do server mas o executor
        # não confirma enfileiramento. Ajuda a diagnosticar workflows "em voo".
        ("Monitor de ACKs", overdue_acks_monitor),
        # Watchdog de runs orfaos — rede de seguranca para quando o worker
        # uvicorn morre por SIGKILL/OOM e o cleanup do handler WS nunca roda.
        # Enumera periodicamente runs 'running' cujo executor perdeu presence
        # no Redis e marca como failed.
        ("Watchdog de runs órfãos", orphan_runs_watchdog),
        # As das extensões (app/extensoes), com o mesmo encerramento.
        *registro_das_extensoes().tarefas_de_fundo,
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.core.redis import init_redis, close_redis
    from app.core.async_scheduler import scheduler

    # Aguarda o banco ficar disponível (tabelas são criadas/migradas pelo Alembic)
    await _wait_for_db()

    # Pool Redis centralizado — inicializado uma vez e fechado no shutdown
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
    # Aviso, nunca erro: em dev o endpoint local e o esperado; em producao e o
    # sintoma de um .env esquecido, e a falha so apareceria como link quebrado.
    from app.core import storage as _storage
    if _storage.endpoint_externo_e_local():
        logger.warning(
            "MINIO_EXTERNAL_ENDPOINT=%s aponta para a rede local: URLs pré-assinadas "
            "(Drive, artefatos, MCP) não funcionam fora do Docker; em produção use o "
            "endereço público do S3 (ex.: https://s3.seu-dominio)",
            _storage.endpoint_externo(),
        )

    # Tarefas de fundo (ver `_tarefas_de_fundo`) e o scheduler de agendamentos
    tarefas = [
        (nome, asyncio.create_task(fabrica(), name=nome)) for nome, fabrica in _tarefas_de_fundo()
    ]
    await scheduler.start()

    # O gerenciador de sessoes do MCP precisa estar ativo enquanto a app atende:
    # e ele quem mantem o estado do transporte streamable HTTP. Entra depois do
    # `init_redis` (as cotas e o carimbo de uso do token dependem do pool) e sai
    # antes do `close_redis`, la embaixo.
    async with mcp_server.session_manager.run():
        yield

    # Shutdown limpo: cancela todas as tarefas de fundo e aguarda cada uma.
    for _, tarefa in tarefas:
        tarefa.cancel()
    resultados = await asyncio.gather(*(tarefa for _, tarefa in tarefas), return_exceptions=True)
    for (nome, _), resultado in zip(tarefas, resultados):
        if isinstance(resultado, BaseException):
            logger.debug("%s encerrada: %s", nome, resultado.__class__.__name__)

    # Cada desconexão de executor deixa uma task dormindo o grace period antes de
    # decidir se falha os runs órfãos (ver `_fail_orphan_runs_if_gone`). No
    # shutdown elas precisam ser canceladas explicitamente: sem isso o loop fecha
    # com tasks pendentes ("Task was destroyed but it is pending!") e, pior, uma
    # delas poderia acordar no meio do teardown e tentar falar com um pool de DB
    # já descartado. Cancelar é o comportamento correto — durante um shutdown do
    # servidor não se deve falhar run nenhum; o watchdog reavalia na volta.
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


# Instância da aplicação
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
app.include_router(me_router)                     # "Meu" — recortes por pessoa; hoje GET /me/schedules (JWT)
app.include_router(assistente_camadas_router)         # Home: camadas do globo — /assistente/camadas, /assistente/tiles (JWT, membro)
app.include_router(assistente_router)                 # Home: conversas do assistente — /assistente/conversa[s], /estado (JWT, SSE)
app.include_router(workspace_router.router)
app.include_router(workflow_groups_router)
app.include_router(health_router)
app.include_router(executores_router)
app.include_router(executor_ws_router)
app.include_router(portal_router)                # portal: publish, tiles, portal data (público)
app.include_router(artifacts_public_router)     # download público por id_hash (sem JWT)
app.include_router(artifacts_router)            # listagem, exclusão e config (JWT)
app.include_router(executor_drive_router)          # Drive: upload via executor (API key auth) — ANTES do drive_router para evitar captura por /drive/{id_hash}
app.include_router(drive_router)                # Drive: upload, listagem, download, delete (JWT)
app.include_router(drive_admin_router)          # Drive: configurações admin (JWT + role=admin)
app.include_router(admin_users_router)          # Admin: gestão de usuários (JWT + role=admin)
app.include_router(admin_nodes_router)          # Admin: habilita/desabilita nodes (JWT + role=admin)
app.include_router(admin_assistente_router)     # Admin: modelo do assistente (JWT + role=admin)
app.include_router(admin_workflows_router)      # Admin: desativa/ativa workflows (JWT + role=admin)
app.include_router(admin_workspaces_router)     # Admin: lixeira de workspaces — restore/purge (JWT + role=admin)
app.include_router(internal_email_router)       # Interno: envio de email via Resend (executor API key auth)
app.include_router(change_detector_router)      # Interno: hash store do node ChangeDetector (executor API key auth)
# As rotas das extensões (app/extensoes), depois das do núcleo.
for _rota_da_extensao in registro_das_extensoes().rotas:
    app.include_router(_rota_da_extensao)


# ── Servidor MCP (/mcp) ───────────────────────────────────────────────────────
# `add_route` e nao `app.mount`: a rota EXATA entrega o caminho intacto, e o app
# do SDK casa o proprio Route("/mcp") sobre o caminho completo da requisicao. Um
# mount consumiria o prefixo e repassaria "" — nenhuma rota de dentro casaria.
#
# As DUAS grafias sao registradas, e as duas apontam para o MESMO app ASGI. Sem
# a segunda, "/mcp/" nao casa rota nenhuma e o roteador responde 307 para
# "/mcp": o Location de um redirect e montado com o esquema que a app enxerga, e
# atras do Traefik o uvicorn roda sem `--proxy-headers`, entao o salto sairia em
# `http://` — um cliente que o seguisse reenviaria o token fora do TLS. Com as
# duas rotas nao ha salto a seguir, e o `PathPrefix(/mcp)` do Traefik ja entrega
# as duas ao mesmo processo. `_CaminhoSemBarraFinal` normaliza "/mcp/" para o
# "/mcp" que o app do SDK casa, sem duplicar transporte nem session manager.
#
# Fabrica, nunca singleton de modulo: `session_manager.run()` so pode ser
# entrado uma vez por instancia, e a instancia fica em `app.state` para o
# lifespan e os testes a alcancarem.
#
# A rota nao herda as dependencies globais da app (JWT/HMAC): a autenticacao
# aqui e o PAT, aplicado pelo middleware que embrulha o app do SDK.
from app.mcp import create_mcp_server, criar_app_mcp


class _CaminhoSemBarraFinal:
    """Delega ao app ASGI de dentro com a barra final do caminho removida.

    Objeto, e nao funcao: o `Route` do Starlette trata funcao como endpoint
    `f(request) -> response` e so chama como ASGI puro o que nao for funcao nem
    metodo. Corta a barra do fim em vez de escrever "/mcp" na mao para nao
    perder um eventual `root_path` no prefixo.
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
    """Endpoint mínimo para Docker healthcheck — sem auth, sem slowapi overhead."""
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


# Content-Security-Policy: bloqueia XSS ativo (script injection via nome de
# workflow, label de no, etc). 'unsafe-inline' em script/style e obrigatorio
# pra Next.js — sem isso, styled-jsx e chunks do App Router quebram. Se um
# dia migrar pra nonce/hash, remover.
# connect-src permite HTTPS/WSS pra API + WebSockets do Redis pub/sub.
# frame-ancestors 'none' bloqueia iframe em qualquer origem (defense-in-
# depth junto do X-Frame-Options: DENY).
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


# CSP para resposta cujo CORPO e controlado por usuario e renderizavel pelo
# navegador — hoje so o ResponseNode do webhook devolvendo `text/html`.
#
# `sandbox` sem tokens poe o documento numa origem opaca e bloqueia script,
# formulario, popup e plugin. O HTML ainda renderiza (com estilo e imagem), mas
# um `<script>` vindo do corpo nao executa. Assim `text/html` continua sendo a
# opcao que o no anuncia, sem virar XSS refletido na origem da API.
#
# Rebaixar o Content-Type seria a alternativa, mas quebraria em silencio todo
# workflow que hoje escolhe "HTML (text/html)" no canvas.
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
        # O handler marca em `request.state` quando o corpo veio do usuario — o
        # header nao serve como canal porque esta linha sobrescreve a CSP de
        # qualquer resposta.
        if getattr(request.state, "corpo_nao_confiavel", False):
            response.headers["Content-Security-Policy"] = _CSP_CORPO_NAO_CONFIAVEL
        else:
            response.headers["Content-Security-Policy"] = _CSP
        # HSTS — apenas quando origens explícitas configuradas (não em dev local)
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
