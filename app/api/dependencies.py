import asyncio
import os
from fastapi import Depends, HTTPException, Request, Security, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session_async
from app.services.workflow_service import WorkflowService
from app.services.schedule_service import ScheduleService
from app.models.user import User
from typing import AsyncGenerator, List
import jwt as _jwt
from app.core.rbac import require_role, Role
# As guardas puras moram em app.core.authorization.workflow_access (também
# consumidas pelo servidor MCP). Os nomes continuam exportados daqui: todo
# router que faz `from app.api.dependencies import verify_workspace_access`
# (ou get_workspace_member_role, _has_min_workspace_role) segue funcionando
# sem mudar.
from app.core.authorization.workflow_access import (  # noqa: F401
    _has_min_workspace_role,
    carregar_workflow_acessivel,
    exigir_papel,
    exigir_papel_no_workspace,
    get_workspace_member_role,
    listar_workspace_ids,
    verify_workspace_access,
)

# Corrige a forma de expor a sessão como dependência
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_async() as session:
        yield session

# Usa a dependência correta acima
async def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)

async def get_schedule_service(db: AsyncSession = Depends(get_db)) -> ScheduleService:
    return ScheduleService(db)


# ── Autenticação JWT ──────────────────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)

async def validate_access_token_claims(token: str) -> dict | None:
    """decode + audience(ACCESS) + `type == "access"` + blacklist (logout).

    Retorna os claims, ou None em qualquer falha. NÃO faz lookup de User — usado
    pelo portal, que autoriza pela própria claim. É a base de segurança comum
    (a checagem de blacklist já divergiu entre os caminhos no passado)."""
    # Import local (não o de topo) para que os testes que dão patch em
    # app.core.utils.jwt_utils.decode_token alcancem esta chamada.
    from app.core.utils.jwt_utils import AUDIENCE_ACCESS, decode_token, is_token_blacklisted
    try:
        claims = decode_token(token, expected_audience=AUDIENCE_ACCESS)
        if claims.get("type") != "access":
            return None
    except (_jwt.PyJWTError, ValueError):
        return None
    if await is_token_blacklisted(token):
        return None
    return claims


async def resolve_access_token(token: str, db: AsyncSession) -> User | None:
    """Ponto ÚNICO de validação de JWT de acesso → User ativo.

    validate_access_token_claims + User existente e ativo. Retorna o User, ou
    None em qualquer falha — o caller decide a resposta (HTTP 401, WS close, bool).
    Usado por get_current_user, ws_authenticate e _jwt_has_workspace_access."""
    claims = await validate_access_token_claims(token)
    if claims is None:
        return None
    result = await db.execute(select(User).where(User.id_hash == claims["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Extrai e valida o Bearer token JWT.
    Retorna o User autenticado ou lança HTTP 401.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Token de autenticação não informado.")
    user = await resolve_access_token(credentials.credentials, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return user


# Alias mantido para compatibilidade com routers existentes.
# Internamente delega ao require_role do rbac.py, eliminando a checagem duplicada.
require_admin = require_role(Role.ADMIN)


async def get_user_workspace_ids(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[str]:
    """
    Retorna a lista de id_hash de workspaces acessíveis ao usuário:
    - Workspaces criados pelo usuário (owner_id)
    - Workspaces dos quais o usuário é membro (WorkspaceMember)

    A query mora em `workflow_access.listar_workspace_ids` (uma só, dono OU
    membro, sem workspaces na lixeira); aqui é só o encaixe FastAPI.
    """
    return await listar_workspace_ids(db, current_user.id_hash)


# `verify_workspace_access` vive em app.core.authorization.workflow_access e é
# re-exportada no topo deste módulo (mesmo nome, mesmas mensagens).


_WS_AUTH_TIMEOUT = float(os.getenv("WS_AUTH_TIMEOUT", "5"))


async def _ws_safe_close(ws: WebSocket, code: int, reason: str) -> None:
    """Fecha o WS sem levantar se já estiver desconectado (evita double-close no ASGI)."""
    if ws.client_state != WebSocketState.DISCONNECTED:
        try:
            await ws.close(code=code, reason=reason)
        except Exception:
            pass


def _ws_endpoint_scope(ws: WebSocket) -> str:
    """Escopo derivado da rota, para os callers que nao passam um explicito.

    Usa o nome do endpoint casado pelo router, NUNCA o path cru: o path de
    /ws/workflow/{run_id} carrega o run_id e daria um balde por execucao — ou
    seja, limite nenhum na pratica.
    """
    endpoint = ws.scope.get("endpoint")
    return getattr(endpoint, "__name__", None) or "ws"


def _ws_rate_key(
    ws: WebSocket, *, prefix: str, scope: str | None, identity: str | None
) -> str:
    """Chave do balde de rate limit de WebSocket.

    Fecha dois furos que faziam o painel de execucao ser recusado com close 1013
    em uso normal, com pouquissimos usuarios:

      - `ws.client.host` cru: atras do Traefik e o IP do proxy para TODOS os
        clientes, entao o balde era um contador GLOBAL da plataforma.
        `get_client_ip` so aceita o X-Forwarded-For quando o peer e um proxy
        confiavel (senao o proprio cliente forjaria uma identidade nova a cada
        conexao e anularia o limite).
      - chave sem namespace de endpoint: /ws/workflow e /ws/telemetry dividiam o
        MESMO balde — e o TTL era o do primeiro que incrementasse —, logo abrir
        o painel de execucao gastava a cota da telemetria e vice-versa.

    `identity` (ex.: user_id_hash, quando a autenticacao ja rodou) e preferido
    ao IP por ser imune a NAT e ao proxy.
    """
    if identity:
        who = f"u:{identity}"
    else:
        from app.core.trusted_proxy import get_client_ip
        who = get_client_ip(
            ws.client.host if ws.client else None,
            ws.headers.get("x-forwarded-for"),
        )
    return f"{prefix}:{scope or _ws_endpoint_scope(ws)}:{who}"


async def _ws_pre_accept_rate_check(
    ws: WebSocket, *, scope: str | None = None, limit: int = 30, period: int = 60
) -> bool:
    """Rate limit por IP ANTES do accept — defesa anti-DoS contra abrir
    centenas de sockets sem fornecer token (cada um custaria _WS_AUTH_TIMEOUT
    de buffers alocados no servidor).

    Sem accept previo, `ws.close()` envia 403 + close handshake. Cliente
    bem comportado interpreta; clientes maliciosos veem TCP RST.

    Redis indisponivel -> permite (degradacao graciosa, alinhado com
    check_ws_rate_limit pos-accept).
    """
    try:
        from app.core.redis import contar_na_janela
        key = _ws_rate_key(ws, prefix="ratelimit:ws_open", scope=scope, identity=None)
        count, _ = await contar_na_janela(key, period)
        if count > limit:
            # Pre-accept close: nao chama accept(); fecha o handshake imediato.
            try:
                await ws.close(code=1013, reason="Too many open WS")
            except Exception:
                pass
            return False
    except Exception as exc:
        from app.core.utils.logger import get_logger as _gl
        _gl("app.api.dependencies.ws").warning("Rate limit WS pre-accept indisponivel (Redis): %s", exc)
    return True


async def ws_authenticate(
    ws: WebSocket, *, scope: str | None = None, require_role: str | None = None
) -> User | None:
    """
    Autentica uma conexão WebSocket pela PRIMEIRA mensagem (frame de texto com o JWT).

    Mais seguro que query param: o token nunca aparece em logs de proxy/servidor
    (a query string vai para access logs; o corpo de mensagens WS, não).

    Antes do accept: aplica rate limit por IP (30 abre/min), num balde proprio
    do endpoint. `scope` nomeia esse balde; sem ele, o nome do endpoint da rota
    e usado — o que importa e que rotas distintas nao compartilhem contador.

    Apos accept: aguarda o token por _WS_AUTH_TIMEOUT segundos — o timeout
    fecha a janela de socket aberto não-autenticado (anti-DoS pos-accept).

    require_role: se setado, exige user.role == require_role (ex.: "admin").

    Retorna o User autenticado, ou None com a conexão JÁ FECHADA (o caller deve
    apenas `return` quando receber None).
    """
    # Defesa anti-DoS: bloqueia IP que abre WS em rajada antes mesmo do accept.
    if not await _ws_pre_accept_rate_check(ws, scope=scope, limit=30, period=60):
        return None

    await ws.accept()

    try:
        token = await asyncio.wait_for(ws.receive_text(), timeout=_WS_AUTH_TIMEOUT)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await _ws_safe_close(ws, 4401, "Token não enviado.")
        return None
    except Exception as exc:
        # Catch-all: cliente fechou no meio do receive (ex: React StrictMode
        # remonta e descarta a 1a conexao -> Starlette levanta RuntimeError, nao
        # WebSocketDisconnect). Sem isso, a excecao propaga e o cliente ve 1006.
        from app.core.utils.logger import get_logger as _gl
        _gl("app.api.dependencies.ws").debug("Falha ao receber token WS: %s", exc)
        await _ws_safe_close(ws, 4401, "Token não recebido.")
        return None

    # Mesma validação do HTTP (decode + audience + type + blacklist + user ativo),
    # via o ponto único resolve_access_token — o WS antes NÃO checava blacklist.
    async with get_session_async() as db:
        user = await resolve_access_token(token, db)
        # Extrai role dentro da sessão e destaca o objeto (os atributos já
        # carregados permanecem acessíveis fora da sessão, sem DetachedInstanceError).
        role = user.role if user is not None else None
        if user is not None:
            db.expunge(user)

    if user is None:
        await _ws_safe_close(ws, 4401, "Token inválido ou expirado.")
        return None
    if require_role is not None and role != require_role:
        await _ws_safe_close(ws, 4403, f"Acesso restrito a {require_role}.")
        return None
    return user


async def check_ws_rate_limit(
    ws: WebSocket,
    *,
    limit: int,
    period: int,
    scope: str | None = None,
    identity: str | None = None,
) -> bool:
    """
    Rate limit via Redis, chamado APÓS o accept (para que ws.close funcione).
    Fecha a conexão e retorna False se exceder. Redis indisponível = degrada
    graciosamente (permite a conexão). Retorna True se dentro do limite.

    `scope` separa o balde por endpoint; `identity` (user_id_hash, quando a
    autenticação já rodou) troca o IP por uma chave que o NAT e o proxy não
    colapsam. Ver `_ws_rate_key`.
    """
    try:
        from app.core.redis import contar_na_janela
        key = _ws_rate_key(ws, prefix="ratelimit:ws", scope=scope, identity=identity)
        count, _ = await contar_na_janela(key, period)
        if count > limit:
            await _ws_safe_close(ws, 1013, "Rate limit excedido.")
            return False
    except Exception as exc:
        from app.core.utils.logger import get_logger as _gl
        _gl("app.api.dependencies.ws").warning("Rate limit WS indisponível (Redis): %s", exc)
    return True


import re as _re
import urllib.parse as _urllib_parse


# Traefik passTLSClientCert injeta um header com Subject, Issuer, SerialNumber etc.
# Formato observado (URL-encoded): Subject="CN=executor-abc";SerialNumber="123456789..."
# Aspas em torno do valor sao opcionais. SerialNumber vem em DECIMAL.
#
# O CN e extraido de dentro do campo Subject=... especificamente — buscar
# `CN=` no header inteiro faria um CN vindo de Issuer (se algum dia habilitado
# no middleware) ser aceito como identidade do executor.
#
# As aspas sao OPCIONAIS aqui, igual ao _SERIAL_RE: exigir `Subject="..."`
# quebraria todos os executores de uma vez caso o Traefik emita sem aspas.
_SUBJECT_RE = _re.compile(r'Subject=(?:"([^"]*)"|([^;]*))')
_CN_RE      = _re.compile(r'CN=([^,";]+)')
_SERIAL_RE  = _re.compile(r'SerialNumber=(?:"([^"]+)"|([0-9a-fA-F]+))')


def _serial_to_int(serial_str: str | None, *, source: str) -> int | None:
    """
    Converte serial em string para int com base explicita.

    `source` (obrigatório):
      - "db"     : serial vindo do DB (armazenado em hex, ex:
                   '2acb673f0a8341df762af990ff29e76b').  # pragma: allowlist secret
      - "header" : serial vindo do header Traefik (decimal, ex:
                   '56883706168065981647801696766709589867').

    A base explícita evita o bug histórico da heurística "auto" (um serial hex
    com só dígitos 0-9 era lido como decimal → nunca casava com o header decimal
    → executor rejeitado indefinidamente). `source` é sempre conhecido nos
    call sites (validate_executor_mtls).
    """
    if not serial_str:
        return None
    s = serial_str.strip().strip('"').strip("'").lower()
    if not s:
        return None
    if s.startswith("0x"):
        s = s[2:]

    base = 16 if source == "db" else 10
    try:
        return int(s, base)
    except ValueError:
        return None


def _parse_traefik_client_cert(header_value: str) -> tuple[str | None, str | None]:
    """Extrai (cn, serial_str) do header `X-Forwarded-Tls-Client-Cert-Info` de Traefik."""
    if not header_value:
        return None, None
    decoded = _urllib_parse.unquote(header_value)

    # CN so vale se estiver dentro de Subject=... — nunca de outro campo.
    subject_match = _SUBJECT_RE.search(decoded)
    cn = None
    if subject_match:
        subject = subject_match.group(1) or subject_match.group(2) or ""
        cn_match = _CN_RE.search(subject)
        cn = cn_match.group(1).strip().strip('"') if cn_match else None

    sn_match = _SERIAL_RE.search(decoded)
    # SERIAL_RE tem 2 grupos alternativos (com aspas / sem aspas) — pega o que matched.
    serial = None
    if sn_match:
        serial = sn_match.group(1) or sn_match.group(2)
    return cn, serial


def assert_request_from_trusted_proxy(client_host: str | None, path: str) -> None:
    """
    Fail-closed: o header de cert mTLS so vale se a conexao veio do proxy.

    Camada 2 da defesa contra spoofing de `X-Forwarded-Tls-Client-Cert-Info`
    (camada 1 e o middleware `strip-executor-cert-header@file` no Traefik).
    Necessaria porque o `passTLSClientCert` do Traefik apenas sobrescreve o
    header quando ha client cert — ele nunca remove um header ja presente.
    """
    from app.core.trusted_proxy import is_trusted_proxy
    if is_trusted_proxy(client_host):
        return
    from app.core.utils.logger import get_logger as _gl
    _gl("app.api.dependencies.mtls").warning(
        "Header de cert mTLS recebido de origem NAO confiavel (%s) em %s — "
        "possivel tentativa de spoofing. Rejeitado.",
        client_host, path,
    )
    raise HTTPException(status_code=401, detail="Cert mTLS ausente ou invalido.")


class ExecutorMtlsError(Exception):
    """Falha na autenticação mTLS de executor. `reason` mapeia para o status
    específico de cada camada (HTTP 4xx via _MTLS_HTTP_STATUS, WS close 44xx via
    _MTLS_WS_CODE)."""
    def __init__(self, reason: str, detail: str):
        self.reason = reason
        self.detail = detail
        super().__init__(detail)


# Mapeia motivo → status. Preserva EXATAMENTE o comportamento anterior de cada
# camada (que divergia: ex. revogado era 401 no HTTP e 4403 no WS).
_MTLS_HTTP_STATUS = {
    "missing_cert": 401, "not_found": 401, "inactive": 403,
    "serial_mismatch": 401, "expired": 401, "revoked": 401,
}
_MTLS_WS_CODE = {
    "missing_cert": 4401, "wrong_executor": 4403, "not_found": 4404,
    "inactive": 4403, "no_public_key": 4403, "serial_mismatch": 4401,
    "expired": 4401, "revoked": 4403,
}


async def validate_executor_mtls(
    *,
    header_value: str,
    client_host: str | None,
    url_path: str,
    db: AsyncSession,
    expected_executor_id: str | None = None,
    require_public_key: bool = False,
) -> "Executor":  # noqa: F821
    """Pipeline ÚNICO de autenticação mTLS de executor (HTTP e WebSocket).

    Traefik valida o cert contra a CA interna e injeta o header
    X-Forwarded-Tls-Client-Cert-Info. Aqui: valida proxy confiável → parse do
    CN(`executor-{id}`)/serial → executor ativo no DB → serial confere → cert
    não expirado → não revogado. Levanta ExecutorMtlsError(reason, detail); cada
    camada traduz `reason` para HTTP/WS. `expected_executor_id` (WS) exige que o
    CN bata com o id da URL; `require_public_key` (WS) exige chave pública.
    """
    from app.services import executor_enrollment_service
    from app.models.executor import Executor
    from app.core.utils.datetime_utils import utc_now_naive

    if header_value:
        try:
            assert_request_from_trusted_proxy(client_host, url_path)
        except Exception:
            raise ExecutorMtlsError("missing_cert", "Cert mTLS ausente ou invalido.")
    cn, serial = _parse_traefik_client_cert(header_value)
    if not cn or not cn.startswith("executor-") or not serial:
        raise ExecutorMtlsError("missing_cert", "Cert mTLS ausente ou invalido.")

    executor_id = cn.removeprefix("executor-")
    if expected_executor_id is not None and executor_id != expected_executor_id:
        raise ExecutorMtlsError("wrong_executor", "Cert nao pertence a este executor.")

    result = await db.execute(select(Executor).where(Executor.id_hash == executor_id))
    ag = result.scalar_one_or_none()
    if ag is None or ag.deleted_at is not None:
        raise ExecutorMtlsError("not_found", "Executor nao encontrado.")
    if ag.status != "active":
        raise ExecutorMtlsError("inactive", f"Executor com status '{ag.status}'.")
    if require_public_key and not ag.public_key:
        raise ExecutorMtlsError("no_public_key", "Executor sem chave publica registrada.")

    # Defesa em profundidade: Traefik já valida o cert no handshake, mas checamos
    # validade e serial contra o banco aqui também.
    if ag.cert_expires_at is not None and ag.cert_expires_at < utc_now_naive():
        raise ExecutorMtlsError("expired", "Cert mTLS expirado.")

    # Normaliza ambos serials para int — Traefik manda em decimal, DB tem em hex.
    db_serial_int     = _serial_to_int(ag.cert_serial, source="db")
    header_serial_int = _serial_to_int(serial, source="header")
    if db_serial_int is None or header_serial_int is None or db_serial_int != header_serial_int:
        raise ExecutorMtlsError("serial_mismatch", "Cert mTLS nao corresponde ao registrado.")

    if await executor_enrollment_service.is_cert_revoked(ag.cert_serial):
        raise ExecutorMtlsError("revoked", "Cert mTLS revogado.")

    return ag


async def get_agent_from_mtls(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Dependency HTTP que autentica o executor via cert mTLS (ver
    validate_executor_mtls). Sem fallback para X-Api-Key — 401/403 em falha."""
    header_value = request.headers.get("X-Forwarded-Tls-Client-Cert-Info", "")
    try:
        return await validate_executor_mtls(
            header_value=header_value,
            client_host=request.client.host if request.client else None,
            url_path=request.url.path,
            db=db,
        )
    except ExecutorMtlsError as exc:
        if exc.reason == "missing_cert":
            from app.core.utils.logger import get_logger as _gl
            _log = _gl("app.api.dependencies.mtls")
            if _log.isEnabledFor(10):  # logging.DEBUG
                _log.debug(
                    "Cert mTLS ausente/invalido em %s %s | header_present=%s",
                    request.method, request.url.path, bool(header_value),
                )
        raise HTTPException(status_code=_MTLS_HTTP_STATUS.get(exc.reason, 401), detail=exc.detail)


class ExecutorOuUsuario:
    """Quem autenticou numa rota que aceita as duas identidades.

    Exatamente um dos dois vem preenchido. Existe porque `agent_mtls_or_user_auth`
    antes devolvia `None`: o handler sabia que ALGUEM se autenticou, mas nao quem
    — e por isso nao tinha como decidir se aquele chamador podia ver AQUELE
    recurso. As rotas de leitura de executor ficaram abertas a qualquer conta
    justamente por causa disso.
    """

    __slots__ = ("executor", "user")

    def __init__(self, *, executor=None, user: User | None = None):
        # Sem esta guarda, um `ExecutorOuUsuario()` vazio chegaria aos helpers de
        # autorizacao e estouraria em `None.role` — AttributeError vira 500 no
        # handler generico, que e o pior desfecho possivel numa checagem de
        # acesso (nao nega, nao concede, so quebra).
        if (executor is None) == (user is None):
            raise ValueError("ExecutorOuUsuario exige exatamente um entre executor e user.")
        self.executor = executor
        self.user = user

    @property
    def is_executor(self) -> bool:
        return self.executor is not None


async def agent_mtls_or_user_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ExecutorOuUsuario:
    """
    Aceita autenticacao por cert mTLS (executor) ou Bearer JWT (usuario).
    Substituto do antigo `agent_or_user_auth` (X-Api-Key) — sem retrocompat.

    Devolve `ExecutorOuUsuario` com a identidade resolvida. AUTENTICA apenas: a
    autorizacao (qual executor/workspace aquele chamador alcanca) e do handler.
    """
    # Tenta mTLS primeiro
    header_value = request.headers.get("X-Forwarded-Tls-Client-Cert-Info", "")
    if header_value:
        try:
            executor = await get_agent_from_mtls(request, db)
            return ExecutorOuUsuario(executor=executor)
        except HTTPException:
            # Cai para Bearer JWT — pode ser um humano usando navegador.
            pass

    # Tenta Bearer JWT. `resolve_access_token` e o ponto unico: decode +
    # audience + type + BLACKLIST + usuario existente e ativo. O `decode_token`
    # solto que existia aqui pulava a blacklist e o lookup do User, entao um
    # token de sessao ja encerrada por /auth/logout — ou de usuario suspenso —
    # seguia valendo nestas rotas ate expirar sozinho.
    _bearer_scheme = HTTPBearer(auto_error=False)
    credentials = await _bearer_scheme(request)
    if not credentials:
        raise HTTPException(status_code=401, detail="Autenticacao necessaria.")
    user = await resolve_access_token(credentials.credentials, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Token invalido.")
    return ExecutorOuUsuario(user=user)


async def get_agent_or_404(
    executor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency reutilizável: busca executor por id_hash.
    Lança HTTP 404 se não encontrado ou deletado.
    """
    from app.services import executor_service
    ag = await executor_service.get_agent(db, executor_id)
    if ag is None:
        raise HTTPException(status_code=404, detail="Executor não encontrado.")
    return ag


# ── RBAC de workspace member ──────────────────────────────────────────────────

# `WORKSPACE_ROLE_ORDER`, `_has_min_workspace_role` e `get_workspace_member_role`
# vivem em app.core.authorization.workflow_access (os dois últimos re-exportados
# no topo).


async def get_accessible_workflow_with_role(
    id_hash: str,
    service: WorkflowService = Depends(get_workflow_service),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retorna (workflow, role_str), ou (workflow, None) para o membro de um
    workspace sem dono, que lê mas não age (ver `carregar_workflow_acessivel`).
    Lança 404 se não encontrado/inativo, 403 se sem acesso ao workspace.
    A regra mora em `workflow_access.carregar_workflow_acessivel`.

    As rotas não a pedem direto: pedem `workflow_com_papel`, que a usa e já
    compara o papel. Continua sendo o ponto de `dependency_overrides` dos
    testes — trocá-la troca o (workflow, papel) e a comparação segue valendo.
    """
    return await carregar_workflow_acessivel(
        service, db, id_hash, current_user.id_hash, aceitar_sem_papel=True,
    )


def workflow_com_papel(minimo: str | None, mensagem: str | None = None):
    """Dependency das rotas `/workflows/{id_hash}...`: o workflow do path, já
    autorizado. `wf = Depends(workflow_com_papel(ROLE_EDITOR))`.

    404 se não existe ou está na lixeira, 403 se o usuário não é do workspace
    (`carregar_workflow_acessivel`, nessa ordem) e 403 se o papel dele não
    alcança `minimo` — com `mensagem` quando a rota tem uma própria, ou a padrão
    de `exigir_papel`. `minimo=None` é leitura: basta pertencer ao workspace.

    O papel mínimo fica DECLARADO na assinatura da rota, e não numa linha do
    corpo que pode ser esquecida — foi o que aconteceu com `GET /pins` e com o
    `PUT` de agendamento. A declaração fica exposta em `papel_minimo`, e
    `tests/unit/test_papel_minimo_das_rotas.py` a confere rota a rota.

    Como a guarda roda na resolução das dependências, ela responde ANTES da
    validação do corpo: quem não tem o papel recebe o 403 mesmo mandando um
    corpo inválido — o 422 fica para quem pode usar a rota.
    """

    async def _workflow_com_papel(
        wf_com_papel=Depends(get_accessible_workflow_with_role),
    ):
        wf, papel = wf_com_papel
        if minimo is not None:
            if papel is None:
                # Membro de workspace sem dono: lê, mas não age. É o 403 de quem
                # não está no workspace, o mesmo de antes da guarda única.
                raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
            exigir_papel(papel, minimo, mensagem)
        return wf

    _workflow_com_papel.papel_minimo = minimo
    _workflow_com_papel.mensagem = mensagem
    return _workflow_com_papel
