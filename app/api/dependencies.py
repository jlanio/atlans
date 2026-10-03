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
# The pure guards live in app.core.authorization.workflow_access (also
# consumed by the MCP server). The names are still exported from here: every
# router that does `from app.api.dependencies import verify_workspace_access`
# (or get_workspace_member_role, _has_min_workspace_role) keeps working
# unchanged.
from app.core.authorization.workflow_access import (  # noqa: F401
    _has_min_workspace_role,
    load_accessible_workflow,
    exigir_papel,
    require_workspace_role,
    get_workspace_member_role,
    listar_workspace_ids,
    verify_workspace_access,
)

# Fixes the way the session is exposed as a dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_async() as session:
        yield session

# Uses the correct dependency above
async def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)

async def get_schedule_service(db: AsyncSession = Depends(get_db)) -> ScheduleService:
    return ScheduleService(db)


# ── JWT authentication ────────────────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)

async def validate_access_token_claims(token: str) -> dict | None:
    """decode + audience(ACCESS) + `type == "access"` + blacklist (logout).

    Returns the claims, or None on any failure. Does NOT look up the User — used
    by the portal, which authorizes by the claim itself. It is the common security
    base (the blacklist check has diverged between the paths in the past)."""
    # Local import (not the top-level one) so that tests patching
    # app.core.utils.jwt_utils.decode_token reach this call.
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
    """SINGLE point of access-JWT validation → active User.

    validate_access_token_claims + existing, active User. Returns the User, or
    None on any failure — the caller decides the response (HTTP 401, WS close, bool).
    Used by get_current_user, ws_authenticate and _jwt_has_workspace_access."""
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
    Extracts and validates the JWT Bearer token.
    Returns the authenticated User or raises HTTP 401.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Token de autenticação não informado.")
    user = await resolve_access_token(credentials.credentials, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return user


# Alias kept for compatibility with existing routers.
# Internally delegates to rbac.py's require_role, eliminating the duplicated check.
require_admin = require_role(Role.ADMIN)


async def get_user_workspace_ids(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[str]:
    """
    Returns the list of id_hash of the workspaces accessible to the user:
    - Workspaces created by the user (owner_id)
    - Workspaces the user is a member of (WorkspaceMember)

    The query lives in `workflow_access.listar_workspace_ids` (a single one, owner OR
    member, excluding workspaces in the trash); this is just the FastAPI plumbing.
    """
    return await listar_workspace_ids(db, current_user.id_hash)


# `verify_workspace_access` lives in app.core.authorization.workflow_access and is
# re-exported at the top of this module (same name, same messages).


_WS_AUTH_TIMEOUT = float(os.getenv("WS_AUTH_TIMEOUT", "5"))


async def _ws_safe_close(ws: WebSocket, code: int, reason: str) -> None:
    """Closes the WS without raising if it is already disconnected (avoids double-close in ASGI)."""
    if ws.client_state != WebSocketState.DISCONNECTED:
        try:
            await ws.close(code=code, reason=reason)
        except Exception:
            pass


def _ws_endpoint_scope(ws: WebSocket) -> str:
    """Scope derived from the route, for callers that do not pass an explicit one.

    Uses the endpoint name matched by the router, NEVER the raw path: the path of
    /ws/workflow/{run_id} carries the run_id and would give one bucket per run — that
    is, no limit at all in practice.
    """
    endpoint = ws.scope.get("endpoint")
    return getattr(endpoint, "__name__", None) or "ws"


def _ws_rate_key(
    ws: WebSocket, *, prefix: str, scope: str | None, identity: str | None
) -> str:
    """WebSocket rate limit bucket key.

    Closes two holes that made the run panel get refused with close 1013
    under normal use, with very few users:

      - raw `ws.client.host`: behind Traefik it is the proxy's IP for ALL
        clients, so the bucket was a GLOBAL counter for the platform.
        `get_client_ip` only accepts X-Forwarded-For when the peer is a trusted
        proxy (otherwise the client itself would forge a new identity on each
        connection and nullify the limit).
      - key without an endpoint namespace: /ws/workflow and /ws/telemetry shared
        the SAME bucket — and the TTL was that of whichever incremented first —,
        so opening the run panel spent the telemetry quota and vice versa.

    `identity` (e.g.: user_id_hash, when authentication has already run) is preferred
    over the IP because it is immune to NAT and to the proxy.
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
    """Per-IP rate limit BEFORE the accept — anti-DoS defense against opening
    hundreds of sockets without providing a token (each would cost _WS_AUTH_TIMEOUT
    of buffers allocated on the server).

    Without a prior accept, `ws.close()` sends 403 + close handshake. A
    well-behaved client interprets it; malicious clients see a TCP RST.

    Redis unavailable -> allow (graceful degradation, aligned with
    the post-accept check_ws_rate_limit).
    """
    try:
        from app.core.redis import count_in_window
        key = _ws_rate_key(ws, prefix="ratelimit:ws_open", scope=scope, identity=None)
        count, _ = await count_in_window(key, period)
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
    Authenticates a WebSocket connection by its FIRST message (a text frame with the JWT).

    Safer than a query param: the token never appears in proxy/server logs
    (the query string goes to access logs; the body of WS messages does not).

    Before the accept: applies a per-IP rate limit (30 opens/min), in the
    endpoint's own bucket. `scope` names that bucket; without it, the route's
    endpoint name is used — what matters is that distinct routes do not share a counter.

    After the accept: waits for the token for _WS_AUTH_TIMEOUT seconds — the timeout
    closes the window of an open unauthenticated socket (post-accept anti-DoS).

    require_role: if set, requires user.role == require_role (e.g.: "admin").

    Returns the authenticated User, or None with the connection ALREADY CLOSED (the
    caller should just `return` when it gets None).
    """
    # Anti-DoS defense: blocks an IP that opens WS in bursts even before the accept.
    if not await _ws_pre_accept_rate_check(ws, scope=scope, limit=30, period=60):
        return None

    await ws.accept()

    try:
        token = await asyncio.wait_for(ws.receive_text(), timeout=_WS_AUTH_TIMEOUT)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await _ws_safe_close(ws, 4401, "Token não enviado.")
        return None
    except Exception as exc:
        # Catch-all: the client closed in the middle of the receive (e.g.: React StrictMode
        # remounts and discards the 1st connection -> Starlette raises RuntimeError, not
        # WebSocketDisconnect). Without this, the exception propagates and the client sees 1006.
        from app.core.utils.logger import get_logger as _gl
        _gl("app.api.dependencies.ws").debug("Falha ao receber token WS: %s", exc)
        await _ws_safe_close(ws, 4401, "Token não recebido.")
        return None

    # Same validation as HTTP (decode + audience + type + blacklist + active user),
    # via the single point resolve_access_token — the WS used NOT to check the blacklist.
    async with get_session_async() as db:
        user = await resolve_access_token(token, db)
        # Extract the role inside the session and detach the object (the already loaded
        # attributes remain accessible outside the session, without DetachedInstanceError).
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
    Rate limit via Redis, called AFTER the accept (so that ws.close works).
    Closes the connection and returns False if exceeded. Redis unavailable = degrades
    gracefully (allows the connection). Returns True if within the limit.

    `scope` separates the bucket per endpoint; `identity` (user_id_hash, when
    authentication has already run) swaps the IP for a key that NAT and the proxy
    do not collapse. See `_ws_rate_key`.
    """
    try:
        from app.core.redis import count_in_window
        key = _ws_rate_key(ws, prefix="ratelimit:ws", scope=scope, identity=identity)
        count, _ = await count_in_window(key, period)
        if count > limit:
            await _ws_safe_close(ws, 1013, "Rate limit excedido.")
            return False
    except Exception as exc:
        from app.core.utils.logger import get_logger as _gl
        _gl("app.api.dependencies.ws").warning("Rate limit WS indisponível (Redis): %s", exc)
    return True


import re as _re
import urllib.parse as _urllib_parse


# Traefik passTLSClientCert injects a header with Subject, Issuer, SerialNumber etc.
# Observed format (URL-encoded): Subject="CN=executor-abc";SerialNumber="123456789..."
# Quotes around the value are optional. SerialNumber comes in DECIMAL.
#
# The CN is extracted specifically from inside the Subject=... field — searching for
# `CN=` in the whole header would let a CN coming from Issuer (if it is ever enabled
# in the middleware) be accepted as the executor's identity.
#
# The quotes are OPTIONAL here, same as _SERIAL_RE: requiring `Subject="..."`
# would break every executor at once if Traefik emits it without quotes.
_SUBJECT_RE = _re.compile(r'Subject=(?:"([^"]*)"|([^;]*))')
_CN_RE      = _re.compile(r'CN=([^,";]+)')
_SERIAL_RE  = _re.compile(r'SerialNumber=(?:"([^"]+)"|([0-9a-fA-F]+))')


def _serial_to_int(serial_str: str | None, *, source: str) -> int | None:
    """
    Converts a serial in string form to int with an explicit base.

    `source` (required):
      - "db"     : serial coming from the DB (stored in hex, e.g.:
                   '2acb673f0a8341df762af990ff29e76b').  # pragma: allowlist secret
      - "header" : serial coming from the Traefik header (decimal, e.g.:
                   '56883706168065981647801696766709589867').

    The explicit base avoids the historical bug of the "auto" heuristic (a hex serial
    with only digits 0-9 was read as decimal → never matched the decimal header
    → executor rejected indefinitely). `source` is always known at the
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
    """Extracts (cn, serial_str) from Traefik's `X-Forwarded-Tls-Client-Cert-Info` header."""
    if not header_value:
        return None, None
    decoded = _urllib_parse.unquote(header_value)

    # The CN only counts if it is inside Subject=... — never from another field.
    subject_match = _SUBJECT_RE.search(decoded)
    cn = None
    if subject_match:
        subject = subject_match.group(1) or subject_match.group(2) or ""
        cn_match = _CN_RE.search(subject)
        cn = cn_match.group(1).strip().strip('"') if cn_match else None

    sn_match = _SERIAL_RE.search(decoded)
    # SERIAL_RE has 2 alternative groups (with quotes / without quotes) — take whichever matched.
    serial = None
    if sn_match:
        serial = sn_match.group(1) or sn_match.group(2)
    return cn, serial


def assert_request_from_trusted_proxy(client_host: str | None, path: str) -> None:
    """
    Fail-closed: the mTLS cert header only counts if the connection came from the proxy.

    Layer 2 of the defense against spoofing of `X-Forwarded-Tls-Client-Cert-Info`
    (layer 1 is the `strip-executor-cert-header@file` middleware in Traefik).
    Needed because Traefik's `passTLSClientCert` only overwrites the
    header when there is a client cert — it never removes a header already present.
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
    """Executor mTLS authentication failure. `reason` maps to the specific status
    of each layer (HTTP 4xx via _MTLS_HTTP_STATUS, WS close 44xx via
    _MTLS_WS_CODE)."""
    def __init__(self, reason: str, detail: str):
        self.reason = reason
        self.detail = detail
        super().__init__(detail)


# Maps reason → status. Preserves EXACTLY each layer's previous behavior
# (which diverged: e.g. revoked was 401 on HTTP and 4403 on WS).
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
    """SINGLE executor mTLS authentication pipeline (HTTP and WebSocket).

    Traefik validates the cert against the internal CA and injects the
    X-Forwarded-Tls-Client-Cert-Info header. Here: validate trusted proxy → parse the
    CN(`executor-{id}`)/serial → executor active in the DB → serial matches → cert
    not expired → not revoked. Raises ExecutorMtlsError(reason, detail); each
    layer translates `reason` to HTTP/WS. `expected_executor_id` (WS) requires the
    CN to match the id in the URL; `require_public_key` (WS) requires a public key.
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

    # Defense in depth: Traefik already validates the cert in the handshake, but we
    # check validity and serial against the database here too.
    if ag.cert_expires_at is not None and ag.cert_expires_at < utc_now_naive():
        raise ExecutorMtlsError("expired", "Cert mTLS expirado.")

    # Normalize both serials to int — Traefik sends decimal, the DB has hex.
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
    """HTTP dependency that authenticates the executor via mTLS cert (see
    validate_executor_mtls). No fallback to X-Api-Key — 401/403 on failure."""
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
    """Who authenticated on a route that accepts both identities.

    Exactly one of the two is filled in. It exists because `agent_mtls_or_user_auth`
    used to return `None`: the handler knew that SOMEONE had authenticated, but not who
    — and so it had no way to decide whether that caller could see THAT
    resource. The executor read routes were left open to any account
    precisely because of that.
    """

    __slots__ = ("executor", "user")

    def __init__(self, *, executor=None, user: User | None = None):
        # Without this guard, an empty `ExecutorOuUsuario()` would reach the
        # authorization helpers and blow up on `None.role` — AttributeError becomes a 500 in
        # the generic handler, which is the worst possible outcome for an access
        # check (it does not deny, does not grant, it just breaks).
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
    Accepts authentication by mTLS cert (executor) or Bearer JWT (user).
    Replacement for the old `agent_or_user_auth` (X-Api-Key) — no backward compatibility.

    Returns `ExecutorOuUsuario` with the resolved identity. It only AUTHENTICATES:
    authorization (which executor/workspace that caller can reach) is the handler's job.
    """
    # Tenta mTLS primeiro
    header_value = request.headers.get("X-Forwarded-Tls-Client-Cert-Info", "")
    if header_value:
        try:
            executor = await get_agent_from_mtls(request, db)
            return ExecutorOuUsuario(executor=executor)
        except HTTPException:
            # Fall back to Bearer JWT — it may be a human using a browser.
            pass

    # Try Bearer JWT. `resolve_access_token` is the single point: decode +
    # audience + type + BLACKLIST + existing, active user. The standalone
    # `decode_token` that used to be here skipped the blacklist and the User lookup, so a
    # token from a session already ended by /auth/logout — or from a suspended user —
    # kept working on these routes until it expired on its own.
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
    Reusable dependency: fetches an executor by id_hash.
    Raises HTTP 404 if not found or deleted.
    """
    from app.services import executor_service
    ag = await executor_service.get_agent(db, executor_id)
    if ag is None:
        raise HTTPException(status_code=404, detail="Executor não encontrado.")
    return ag


# ── Workspace member RBAC ─────────────────────────────────────────────────────

# `WORKSPACE_ROLE_ORDER`, `_has_min_workspace_role` and `get_workspace_member_role`
# live in app.core.authorization.workflow_access (the last two re-exported
# at the top).


async def get_accessible_workflow_with_role(
    id_hash: str,
    service: WorkflowService = Depends(get_workflow_service),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns (workflow, role_str), or (workflow, None) for the member of a
    workspace without an owner, who reads but does not act (see `load_accessible_workflow`).
    Raises 404 if not found/inactive, 403 if there is no access to the workspace.
    The rule lives in `workflow_access.load_accessible_workflow`.

    Routes do not request it directly: they request `workflow_com_papel`, which uses it and
    already compares the role. It remains the `dependency_overrides` point for the
    tests — replacing it replaces the (workflow, role) and the comparison still applies.
    """
    return await load_accessible_workflow(
        service, db, id_hash, current_user.id_hash, accept_without_role=True,
    )


def workflow_com_papel(minimo: str | None, mensagem: str | None = None):
    """Dependency for the `/workflows/{id_hash}...` routes: the workflow from the path, already
    authorized. `wf = Depends(workflow_com_papel(ROLE_EDITOR))`.

    404 if it does not exist or is in the trash, 403 if the user is not in the workspace
    (`load_accessible_workflow`, in that order) and 403 if their role does not
    reach `minimo` — with `mensagem` when the route has its own, or the default
    from `exigir_papel`. `minimo=None` is read access: belonging to the workspace is enough.

    The minimum role is DECLARED in the route signature, not in a line of the
    body that can be forgotten — which is what happened with `GET /pins` and with the
    schedule `PUT`. The declaration is exposed in `papel_minimo`, and
    `tests/unit/test_papel_minimo_das_rotas.py` checks it route by route.

    Since the guard runs during dependency resolution, it responds BEFORE body
    validation: whoever lacks the role gets the 403 even when sending an
    invalid body — the 422 is for those who can use the route.
    """

    async def _workflow_with_role(
        wf_with_role=Depends(get_accessible_workflow_with_role),
    ):
        wf, papel = wf_with_role
        if minimo is not None:
            if papel is None:
                # Member of a workspace without an owner: reads, but does not act. It is the 403 of
                # someone not in the workspace, the same as before the single guard.
                raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
            exigir_papel(papel, minimo, mensagem)
        return wf

    _workflow_with_role.papel_minimo = minimo
    _workflow_with_role.mensagem = mensagem
    return _workflow_with_role
