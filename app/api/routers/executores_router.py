# app/api/routers/executores_router.py
"""
REST endpoints for managing external Executors.

Usage flow (mTLS + Bootstrap OTP):
  1. Admin   → POST /executores/                  → creates executor with status=pending
  2. Admin   → POST /executores/{id}/enroll-otp   → generates a single-use OTP (24h)
  3. Operator hands the OTP to the executor over a secure channel
  4. Executor   → POST /executores/enroll            → Bearer OTP + CSR, receives mTLS cert
  5. Executor   → WS   /ws/executores/{id}           → connects via mTLS (see executor_ws_router.py)
  6. Executor   → POST /executores/renew-cert        → mTLS, renews cert before expiry

Administrative endpoints (require a user JWT with role=admin):
  GET    /executores/                          — lists executors
  DELETE /executores/{id}                      — revokes executor + cert
  DELETE /executores/{id}/permanent            — soft-delete (only if status=revoked)
  DELETE /admin/executores/{id}/cert       — revokes only the current cert
  POST   /executores/{id}/enroll-otp           — generates OTP for enrollment
  GET    /executores/server-public-key         — server's Ed25519 public key
"""
import re
from datetime import datetime, timezone

import httpx

from app.core.utils.logger import get_logger

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace

from app.api.dependencies import (
    get_db, get_agent_or_404, agent_mtls_or_user_auth, require_admin,
    get_current_user, get_agent_from_mtls, ExecutorOuUsuario, _parse_traefik_client_cert,
)
from app.core.executor_connections import executor_registry
from app.api.routers.executor_ws.protocolo import _coerce_count, _coerce_gauge
from app.core.rate_limiter import _client_key, limiter
from app.core.job_crypto import get_server_signing_public_key_b64
from app.schemas.executor_enrollment import (
    EnrollmentOTPResponse, EnrollRequest, EnrollResponse, RenewRequest,
)
from app.services import executor_service, executor_enrollment_service
from app.services import user_executor_service

logger = get_logger(__name__)

router = APIRouter(prefix="/executores", tags=["executores"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ExecutorCreate(BaseModel):
    name:                str        = Field(..., min_length=2, max_length=100)
    description:         str | None = None
    capabilities:        list[str]  = Field(default_factory=list)
    max_concurrent_jobs: int        = Field(default=4, ge=1, le=32)
    max_queue_size:      int        = Field(default=50, ge=1, le=500)
    executor_type:          str        = Field(default="dedicated", pattern="^(default|dedicated)$")


class ExecutorUpdate(BaseModel):
    name:        str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)


class SetDefaultRequest(BaseModel):
    executor_id: str = Field(..., description="id_hash do executor a definir como padrão")
    force: bool = False


class ExecutorOut(BaseModel):
    id_hash:             str
    name:                str
    description:         str | None
    status:              str
    executor_type:          str
    is_default:          bool
    capabilities:        list
    max_concurrent_jobs: int
    max_queue_size:      int
    executor_version:       str | None
    system_info:         dict | None
    last_seen_at:        str | None
    created_at:          str
    created_by:          str | None

    @classmethod
    def from_model(cls, ag) -> "ExecutorOut":
        return cls(
            id_hash=ag.id_hash,
            name=ag.name,
            description=ag.description,
            status=ag.status,
            executor_type=ag.executor_type,
            is_default=ag.is_default,
            capabilities=ag.capabilities or [],
            max_concurrent_jobs=ag.max_concurrent_jobs,
            max_queue_size=ag.max_queue_size,
            executor_version=ag.executor_version,
            system_info=ag.system_info,
            last_seen_at=ag.last_seen_at.isoformat() if ag.last_seen_at else None,
            created_at=ag.created_at.isoformat(),
            created_by=ag.created_by,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_executor_owner_or_admin(current_user, ag) -> None:
    """Raises 403 if the user is neither a global admin nor the owner (created_by) of the executor."""
    if current_user.role != "admin" and ag.created_by != current_user.id_hash:
        raise HTTPException(status_code=403, detail="Acesso negado a este executor.")


def _assert_can_manage_executor(current_user, ag) -> None:
    """Like `_assert_executor_owner_or_admin`, but for MANAGEMENT operations
    (generating an enrollment OTP, revoking): audit SEG-94.

    An executor promoted to the default pool (`is_default`) serves ALL
    tenants. The original owner can no longer generate an OTP or revoke it — only
    a platform admin can. READING the executor itself is still allowed for the
    owner (`_assert_executor_owner_or_admin`); only management is restricted.
    """
    if current_user.role == "admin":
        return
    if getattr(ag, "is_default", False):
        raise HTTPException(
            status_code=403,
            detail="Executor no pool padrão: apenas um administrador pode gerenciá-lo.",
        )
    _assert_executor_owner_or_admin(current_user, ag)


def _assert_pode_ler_executor(quem: "ExecutorOuUsuario", ag) -> None:
    """Authorizes reading ONE executor via the executor's own mTLS or by
    admin/owner.

    These routes depended only on `agent_mtls_or_user_auth`, which only authenticates —
    any active account could read the status and, worse, the workspace list (id_hash +
    name) of any executor on the platform, while the sibling routes
    (`GET /executores/{id}` and `/{id}/users`) already required admin.

    Pure function, testable without starting the application — same pattern as
    `_assert_executor_owner_or_admin`.
    """
    if quem.is_executor:
        # An executor only talks about itself. Without this, an enrolled executor
        # (any user can create one) could enumerate the entire fleet.
        if quem.executor.id_hash != ag.id_hash:
            raise HTTPException(status_code=403, detail="Acesso negado a este executor.")
        return
    _assert_executor_owner_or_admin(quem.user, ag)


# The LIVE state of an executor — online, capacity, since when it has been
# connected — only exists in full in the API worker holding its WebSocket.
# The screen read `executor_registry.get(id)`, which is LOCAL: with `--workers 4`,
# 3 out of 4 refreshes (the list re-queries every 15 s) showed a fully loaded
# executor as idle ("0/4") and one connected for days as "seen 2 days ago".
# Here every piece of data comes from where all workers can see it — Redis and
# the database — including in the WebSocket worker: its memory has values a few
# seconds newer, and mixing them made the response change depending on the worker.

_CAPACITY_COUNTERS = ("queued", "running", "max_concurrent", "max_queue")
_CAPACITY_MEASURES = ("disk_free_gb", "ram_available_gb")


def _capacity_for_screen(cap) -> dict | None:
    """The Redis copy, revalidated against the format the WebSocket worker writes
    (`_sanitize_capacity`): only the contract fields, with the right type. This
    module does not trust what it reads from Redis (the relay is signed for the
    same reason), and the value goes to every user's screen. An invalid counter
    discards the whole capacity; an invalid measurement becomes None."""
    if not isinstance(cap, dict):
        return None
    erros: list[str] = []
    saida = {campo: _coerce_count(cap.get(campo), campo, erros) for campo in _CAPACITY_COUNTERS}
    if erros:
        return None
    saida.update({campo: _coerce_gauge(cap.get(campo)) for campo in _CAPACITY_MEASURES})
    return saida


async def _live_state(ids: list[str]) -> tuple[dict[str, bool], dict[str, dict | None]]:
    """(online per executor, capacity of the online ones), from the same Redis
    snapshot in any worker (see `read_presence_and_capacities`), with the capacity
    revalidated (`_capacity_for_screen`)."""
    online, publicadas = await executor_registry.read_presence_and_capacities(ids)
    return online, {i: _capacity_for_screen(cap) for i, cap in publicadas.items()}


def _connected_since(online: bool, last_seen_at) -> str | None:
    """Start of the current WebSocket session, in ISO with time zone. Offline has no session.

    It is the database's `last_seen_at`: written on each session's handshake and, at
    its end, only if the last contact is later (`registrar_fim_da_sessao`) — the
    end of a replaced session does not erase the start of the new one. Cert
    renewal does not touch it. The connection's `connected_at` would say the same,
    milliseconds apart, but only in the WebSocket worker."""
    if not online or not last_seen_at:
        return None
    if isinstance(last_seen_at, str):
        last_seen_at = datetime.fromisoformat(last_seen_at)
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)  # UTC column without time zone
    return last_seen_at.isoformat()


def _serialize_agent(ag, *, online: bool, capacidade: dict | None) -> dict:
    """Serializes an executor with online status, live capacity and system_info.

    `online` and `capacidade` come from `_live_state`, which reads from where
    all workers can see (see above)."""
    data = {
        **ExecutorOut.from_model(ag).model_dump(),
        "online":       online,
        "capacity":     capacidade,
        "connected_at": _connected_since(online, ag.last_seen_at),
    }
    # Merges the static system_info (from the database, written on the connection's
    # first handshake) with the dynamic capacity metrics.
    base_info = ag.system_info or {}
    if base_info:
        dynamic = {
            chave: capacidade[chave]
            for chave in ("disk_free_gb", "ram_available_gb")
            if capacidade and capacidade.get(chave) is not None
        }
        data["system_info"] = {**base_info, **dynamic}
    return data


# ── Endpoints Admin ───────────────────────────────────────────────────────────

@router.post("", status_code=201, summary="Criar novo executor")
async def create_executor(
    payload: ExecutorCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Creates an executor with status=pending.

    A global admin creates any type (default/dedicated) without restriction. A
    regular user creates only dedicated executors, limited by their individual quota
    (User.agent_quota); the executor is automatically linked to them.

    To finish enrollment, generate an OTP via
    POST /executores/{executor_id}/enroll-otp and hand it to the operator.
    """
    try:
        if current_user.role == "admin":
            ag = await executor_service.create_executor(
                db=db,
                name=payload.name,
                created_by=current_user.id_hash,
                description=payload.description,
                capabilities=payload.capabilities,
                max_concurrent_jobs=payload.max_concurrent_jobs,
                max_queue_size=payload.max_queue_size,
                executor_type=payload.executor_type,
                is_default=(payload.executor_type == "default"),
            )
        else:
            ag = await executor_service.create_dedicated_for_user(
                db=db,
                user=current_user,
                name=payload.name,
                description=payload.description,
                capabilities=payload.capabilities,
                max_concurrent_jobs=payload.max_concurrent_jobs,
                max_queue_size=payload.max_queue_size,
            )
    except executor_service.ExecutorQuotaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except ValueError as exc:
        logger.warning("Erro ao criar executor: %s", exc)
        raise HTTPException(status_code=422, detail="Não foi possível criar o executor.")
    logger.info("Usuario '%s' criou executor '%s' (%s).", current_user.username, ag.name, ag.id_hash)
    return {
        "executor_id": ag.id_hash,
        "status":   ag.status,
        "next_step": "Gere um OTP via POST /executores/{id}/enroll-otp e entregue ao operador.",
    }


@router.get("/pending-acks", summary="[Admin] Jobs enviados aguardando ACK do executor")
async def list_pending_acks(_=Depends(require_admin)):
    """Full list of in-flight jobs — includes recent ones (<15s) that may still
    receive an ACK. Useful for a real-time view of what the server dispatched
    and the executor has not yet confirmed.
    """
    items = await executor_registry.list_pending_acks()
    return {
        "count": len(items),
        "threshold_overdue_seconds": executor_registry.JOB_ACK_WARN_SECONDS,
        "items": items,
    }


@router.get("/overdue-acks", summary="[Admin] Jobs em voo sem ACK além do limiar")
async def list_overdue_acks(
    min_elapsed_seconds: float = 15.0,
    _=Depends(require_admin),
):
    """Returns only jobs whose ACK exceeded the threshold (default 15s).

    Useful for diagnosis when a workflow stays "running" with no progress:
    shows whether the job left the server but never reached the executor (lost
    TCP frame, executor crashed after receiving, relay with no active listener).
    """
    items = await executor_registry.overdue_acks()
    filtered = [
        {"job_id": jid, "executor_id": aid, "elapsed_seconds": round(elapsed, 2)}
        for jid, aid, elapsed in items
        if elapsed >= min_elapsed_seconds
    ]
    return {
        "threshold_seconds": min_elapsed_seconds,
        "count": len(filtered),
        "items": filtered,
    }


@router.get("/server-public-key", summary="Chave pública Ed25519 do servidor (pública)")
async def server_public_key():
    pub = get_server_signing_public_key_b64()
    if pub is None:
        raise HTTPException(
            status_code=503,
            detail="EXECUTOR_SIGNING_KEY não configurada no servidor.",
        )
    return {"ed25519_public_key_b64": pub}


@router.get("/ca-bundle", summary="Root cert da CA interna (publico)",
            response_class=Response)
@limiter.limit("60/minute")
async def ca_bundle(request: Request):
    """
    Returns the internal CA's (step-ca) root cert in PEM format.

    Public endpoint — the root cert is public info by design. Every executor
    needs it to validate the TLS chain of the executors host (signed
    by the private CA).

    Used by the `install.sh` script during onboarding: a new executor downloads
    the root from here and adds it to the local trust store before enrolling.
    """
    from app.core.config import STEPCA_ROOT_CERT_PATH
    try:
        with open(STEPCA_ROOT_CERT_PATH, "rb") as f:
            content = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="CA bundle indisponivel.")
    return Response(
        content=content,
        media_type="application/x-pem-file",
        headers={"Cache-Control": "public, max-age=300"},
    )


_CA_PIN_LINE = 'CA_SHA256_PIN="${ATLANS_CA_SHA256:-}"'


_RE_FINGERPRINT = "0123456789abcdef"


def _normalize_fingerprint(bruto: str) -> str:
    """Lowercase hex, without ':' or spaces — the format install.sh compares.

    `step certificate fingerprint` returns plain hex and `openssl x509 -fingerprint`
    returns it with ':'. The operator pastes whatever they have at hand.

    Accepts SEVERAL comma-separated fingerprints and returns the normalized
    list, also comma-separated. Without this, the rotation value the
    documentation prescribes (`<fp_antigo>,<new_fp>`) was rejected by the
    length validation and install.sh ran WITHOUT pinning — pure TOFU exactly
    in the window when the CA is being swapped.
    """
    partes = [
        "".join(p.split()).replace(":", "").lower()
        for p in bruto.replace(";", ",").split(",")
    ]
    return ",".join(p for p in partes if p)


def _inject_ca_fingerprint(script: str) -> str:
    """Publishes STEPCA_ROOT_FINGERPRINT as the default in the served install.sh.

    Without this, `STEPCA_ROOT_FINGERPRINT` was read from config and never used: the
    executor supports pinning (`ATLANS_CA_SHA256`, see
    executor/_ca_bootstrap.py), but the script was served static and never
    set it. The ca-bundle download stayed TOFU, while docs/
    mtls-bootstrap.md claimed the backend used the value "when building
    install.sh". This is the code that makes that sentence true.

    Empty config returns the script untouched — the client warns and proceeds
    without pinning, which is the previous behavior.
    """
    from app.core.config import STEPCA_ROOT_FINGERPRINT

    fp = _normalize_fingerprint(STEPCA_ROOT_FINGERPRINT or "")
    if not fp:
        return script

    # A value that is not 32-byte hex is not a SHA-256 fingerprint; injecting it
    # would only make the installer abort with a comparison that never matches.
    # Each fingerprint in the list is validated separately.
    invalidos = [
        p for p in fp.split(",")
        if len(p) != 64 or any(c not in _RE_FINGERPRINT for c in p)
    ]
    if invalidos:
        logger.error(
            "STEPCA_ROOT_FINGERPRINT tem %d entrada(s) que nao parecem SHA-256 — "
            "install.sh sera servido sem pinning.", len(invalidos),
        )
        return script

    if _CA_PIN_LINE not in script:
        logger.error(
            "install.sh nao contem a linha de pinning esperada — servido sem "
            "fingerprint. Verifique static/install.sh.",
        )
        return script

    return script.replace(_CA_PIN_LINE, f'CA_SHA256_PIN="${{ATLANS_CA_SHA256:-{fp}}}"', 1)


# The addresses the served install.sh carries as defaults. One line for each
# (`SERVER=""` etc., at the start of the line) is replaced by this
# installation's value; the file in the repository points to none.
_SAFE_ADDRESS = re.compile(r"(?:https?|wss?)://[A-Za-z0-9.-]+(?::[0-9]{1,5})?(?:/[A-Za-z0-9._~/-]*)?")


def _inject_addresses(script: str) -> str:
    """Fills SERVER, PUBLIC_SERVER and REPO_URL with this server's config.

    Only a value that is a plain URL gets in (scheme, host, port and path, no
    quotes, `$` or spaces): it goes inside double quotes in a script the
    operator runs with `bash`. Any other value, or an empty one, leaves the line
    empty, and the script asks for the flag.
    """
    from app.core.config import AGENTS_URL, EXECUTOR_REPO_URL, FRONTEND_URL

    agentes = AGENTS_URL
    if agentes.startswith("https://"):
        agentes = "wss://" + agentes[len("https://"):]
    elif agentes.startswith("http://"):
        agentes = "ws://" + agentes[len("http://"):]

    for var, valor in (
        ("SERVER", agentes),
        ("PUBLIC_SERVER", FRONTEND_URL.rstrip("/")),
        ("REPO_URL", EXECUTOR_REPO_URL),
    ):
        if not valor:
            continue
        if not _SAFE_ADDRESS.fullmatch(valor):
            logger.error("install.sh: %s com valor fora do formato de URL — servido sem padrao.", var)
            continue
        script, n = re.subn(rf'^{var}=""$', f'{var}="{valor}"', script, count=1, flags=re.MULTILINE)
        if not n:
            logger.error("install.sh nao contem a linha %s=\"\" — servido sem esse padrao.", var)
    return script


@router.get("/install", summary="Script install.sh para onboarding de executor (publico)",
            response_class=Response)
@limiter.limit("60/minute")
async def install_script(request: Request):
    """
    Returns the executor's bash installation script (self-contained).

    Operator usage (the ready-made command comes from the enrollment screen):
        curl -fsSL https://<site>/executores/install | bash -s -- \\
            --executor-id=<ID> --otp=<OTP>

    The script:
      1. Checks docker + git
      2. Clones the repo (if missing) into ~/atlans-executor
      3. Downloads the root cert via /executores/ca-bundle
      4. Builds the image + runs enroll + starts the service

    The script itself has no secrets; it is the same thing the operator
    would assemble by hand following the README. The CA fingerprint injected
    below is not a secret either — it is the hash of a public certificate, and
    it lets the client detect that it downloaded the WRONG CA.
    """
    from pathlib import Path
    script_path = Path(__file__).resolve().parent.parent.parent.parent / "static" / "install.sh"
    try:
        content = script_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="install.sh indisponivel no servidor.")

    content = _inject_ca_fingerprint(content)
    content = _inject_addresses(content)

    return Response(
        content=content,
        media_type="text/x-shellscript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300"},
    )


# ── Desktop app for Windows ──────────────────────────────────────────────────
#
# The installer lives in the GitHub Releases (tag `desktop/v*`) of the repository in
# DESKTOP_RELEASES_REPO, published by the desktop-windows.yml workflow. These two
# endpoints exist so the dashboard can offer the download without the user
# needing to know where to look. Without the repository configured, there is no offer.
#
# The binary is NOT proxied: it is ~180 MB per download, and passing it through the
# backend would consume worker time and bandwidth for nothing. The redirect sends the
# browser straight to GitHub's CDN.

_DESKTOP_TAG_PREFIX = "desktop/v"
_DESKTOP_CACHE_TTL = 300  # segundos

# Per-worker in-memory cache. The GitHub query is slow and has a rate limit of
# 60/h without a token — without a cache, a handful of users opening the OTP
# dialog would exhaust the quota and the download button would vanish for everyone.
_desktop_cache: dict = {"em": 0.0, "dados": None}


async def _latest_desktop_release() -> dict | None:
    """Metadata of the latest Windows installer, or None if there is none.

    Never raises: the absence of a release is a normal state (none published
    yet), and a network failure with GitHub must not bring down the executors
    page.
    """
    import time as _time
    from app.core.config import DESKTOP_RELEASES_REPO

    if not DESKTOP_RELEASES_REPO:
        return None

    agora = _time.monotonic()
    if _desktop_cache["dados"] is not None and agora - _desktop_cache["em"] < _DESKTOP_CACHE_TTL:
        return _desktop_cache["dados"]

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as cliente:
            r = await cliente.get(
                f"https://api.github.com/repos/{DESKTOP_RELEASES_REPO}/releases",
                params={"per_page": 30},
            )
        if r.status_code != 200:
            return _desktop_cache["dados"]
        releases = r.json()
    except Exception as exc:
        logger.warning("Falha ao consultar releases do app desktop: %s", exc)
        return _desktop_cache["dados"]

    for rel in releases:
        tag = rel.get("tag_name") or ""
        if not tag.startswith(_DESKTOP_TAG_PREFIX) or rel.get("draft"):
            continue
        for asset in rel.get("assets") or []:
            nome = asset.get("name") or ""
            if nome.lower().endswith(".exe"):
                dados = {
                    "versao": tag[len(_DESKTOP_TAG_PREFIX):],
                    "url": asset.get("browser_download_url"),
                    "tamanho": asset.get("size"),
                    "publicado_em": rel.get("published_at"),
                    "nome": nome,
                }
                _desktop_cache.update({"em": agora, "dados": dados})
                return dados

    _desktop_cache.update({"em": agora, "dados": None})
    return None


@router.get("/install/windows/latest.json",
            summary="Metadados do instalador Windows (publico)")
@limiter.limit("60/minute")
async def desktop_latest(request: Request):
    """Installer version, size and URL — for the UI to show before the click."""
    dados = await _latest_desktop_release()
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma versão do app desktop foi publicada ainda.",
        )
    return dados


@router.get("/install/windows", summary="Baixar o app desktop para Windows (publico)")
@limiter.limit("60/minute")
async def desktop_install(request: Request):
    """Redirects to the `.exe` installer of the latest `desktop/v*` release."""
    from fastapi.responses import RedirectResponse

    dados = await _latest_desktop_release()
    if not dados or not dados.get("url"):
        raise HTTPException(
            status_code=404,
            detail="Nenhuma versão do app desktop foi publicada ainda.",
        )
    # 302 and not 301: the asset URL changes with each release, and a permanent one
    # would get stuck in the browser cache pointing to the old version.
    return RedirectResponse(url=dados["url"], status_code=302)


@router.get("/my", summary="Listar executores acessíveis ao usuário autenticado")
async def my_agents(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Returns default + dedicated executors assigned via the user's workspaces."""
    executores = await user_executor_service.get_user_accessible_agents(db, current_user.id_hash)
    online, capacities = await _live_state([ag["id_hash"] for ag in executores])
    for ag in executores:
        ag["online"] = online[ag["id_hash"]]
        ag["capacity"] = capacities.get(ag["id_hash"])
        ag["connected_at"] = _connected_since(ag["online"], ag.get("last_seen_at"))
    return executores


@router.get("/my/count", summary="Quantidade de executores acessíveis ao usuário")
async def my_agents_count(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lightweight count (no presence check) — used to decide whether the UI
    shows the executors menu to the user."""
    executores = await user_executor_service.get_user_accessible_agents(db, current_user.id_hash)
    return {"count": len(executores)}


@router.get("", summary="Listar todos os executores")
async def list_agents(
    executor_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Lists all executors."""
    executores = await executor_service.list_agents(db)
    filtered = [ag for ag in executores if not executor_type or ag.executor_type == executor_type]
    online, capacities = await _live_state([ag.id_hash for ag in filtered])
    return [
        _serialize_agent(ag, online=online[ag.id_hash], capacidade=capacities.get(ag.id_hash))
        for ag in filtered
    ]


@router.get("/{executor_id}/status", summary="Status de um executor (mTLS do próprio executor, ou admin/dono)")
async def agent_status(
    executor_id: str,
    db: AsyncSession = Depends(get_db),
    quem=Depends(agent_mtls_or_user_auth),
    ag=Depends(get_agent_or_404),
):
    _assert_pode_ler_executor(quem, ag)

    # Resolve the workspaces available to the executor (GeoSync)
    agent_workspaces = await _get_agent_workspaces(db, ag)
    resolved_ws_id = None
    if agent_workspaces:
        # Auto-select: default first, otherwise the first in the list
        default_ws = next((w for w in agent_workspaces if w["is_default"]), None)
        resolved_ws_id = (default_ws or agent_workspaces[0])["id_hash"]

    return {
        "executor_id":      executor_id,
        "status":        ag.status,
        "workspace_id":  resolved_ws_id,
        "workspaces":    agent_workspaces,
        "online":        await executor_registry.is_online(executor_id),
        "last_seen_at":  ag.last_seen_at.isoformat() if ag.last_seen_at else None,
    }


@router.get("/{executor_id}/workspaces", summary="Workspaces disponíveis para o executor")
async def agent_workspaces_endpoint(
    executor_id: str,
    db: AsyncSession = Depends(get_db),
    quem=Depends(agent_mtls_or_user_auth),
    ag=Depends(get_agent_or_404),
):
    """Returns workspaces accessible to the executor (via the assigned user).

    Auth: the executor's own mTLS, or JWT of an admin/owner of the executor.
    """
    _assert_pode_ler_executor(quem, ag)
    return await _get_agent_workspaces(db, ag)


async def _get_agent_workspaces(db: AsyncSession, ag) -> list[dict]:
    """
    Returns workspaces available to the executor (used by GeoSync for auto-detection).

    Rules:
      - Default executor → [] (GeoSync disabled; the scope of all workspaces is too broad)
      - Dedicated executor with >1 workspace → [] (requires explicit EXECUTOR_WORKSPACE_ID)
      - Dedicated executor with 0 or 1 workspace → returns normally
    """
    if ag.is_default:
        return []

    # Legacy pointer ∪ policy tiers: GeoSync needs the workspace
    # whose jobs this executor actually receives.
    from app.services.workspace_executor_service import workspace_ids_for_executor
    ids = await workspace_ids_for_executor(db, ag.id_hash)
    workspaces = []
    if ids:
        ws_result = await db.execute(
            select(Workspace).where(Workspace.id_hash.in_(ids), Workspace.deleted_at.is_(None))
        )
        workspaces = ws_result.scalars().all()

    if len(workspaces) > 1:
        return []

    return [
        {"id_hash": ws.id_hash, "name": ws.name, "is_default": ws.is_default}
        for ws in workspaces
    ]


@router.get("/{executor_id}/users", summary="[Admin] Listar usuários atribuídos ao executor")
async def list_agent_users(
    executor_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
    _ag=Depends(get_agent_or_404),
):
    """Returns users who have this executor assigned directly by the admin."""
    return await user_executor_service.list_agent_users(db, executor_id)


class UserExecutorAssignRequest(BaseModel):
    user_id: str = Field(..., description="id_hash do usuário")


@router.post("/{executor_id}/users", status_code=201, summary="[Admin] Atribuir executor a usuário")
async def assign_agent_to_user(
    executor_id: str,
    payload: UserExecutorAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    _ag=Depends(get_agent_or_404),
):
    """Assigns a dedicated executor directly to a user."""
    try:
        await user_executor_service.assign_user_to_agent(
            db, executor_id, payload.user_id, assigned_by=current_user.id_hash
        )
    except ValueError as exc:
        msg = str(exc)
        if "já está atribuído" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "não encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    logger.info(
        "Admin '%s' atribuiu executor '%s' ao usuário '%s'.",
        current_user.username, executor_id, payload.user_id,
    )
    return {"executor_id": executor_id, "user_id": payload.user_id}


@router.delete("/{executor_id}/users/{user_id}", status_code=204, summary="[Admin] Remover atribuição de executor a usuário")
async def remove_agent_user(
    executor_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Removes the direct assignment of an executor to a user."""
    try:
        await user_executor_service.remove_user_from_agent(db, executor_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    logger.info(
        "Admin '%s' removeu atribuição do executor '%s' ao usuário '%s'.",
        current_user.username, executor_id, user_id,
    )


@router.patch("/{executor_id}", summary="[Admin] Editar nome/descrição do executor")
@limiter.limit("10/minute")
async def patch_agent(
    request: Request,
    executor_id: str,
    payload: ExecutorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    changed = payload.model_dump(exclude_none=True)
    if not changed:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")
    try:
        ag = await executor_service.update_agent(db, executor_id, changed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info("Usuário '%s' editou executor '%s': %s", current_user.username, executor_id, list(changed.keys()))
    return ExecutorOut.from_model(ag)


@router.delete("/{executor_id}", status_code=204, summary="Revogar executor")
async def revoke_executor(
    executor_id: str,
    force: bool = Query(
        False,
        description="Retira o executor dos níveis de política mesmo que isso esvazie "
                    "o nível principal de algum workspace (os donos são avisados).",
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    ag=Depends(get_agent_or_404),
):
    _assert_can_manage_executor(current_user, ag)
    # Execution policy (spec §4.4): a revoked executor drops out of the tiers; if
    # that would empty someone's main tier, 409 — unless `force`. The
    # steps (tiers, status, cert, notice to owners, session dropped) are those of
    # every path that revokes — see `executor_service.revogar_executor`.
    revogacao = await executor_service.revogar_executor(
        db, ag, force=force, actor_id=current_user.id_hash, motivo="revoked",
        aviso="Executor revogado pelo administrador.", fechamento="Executor revogado.",
    )
    await db.commit()
    await executor_service.complete_revocations([revogacao])

    logger.info("Usuário '%s' revogou executor '%s'.", current_user.username, executor_id)


@router.delete("/{executor_id}/permanent", status_code=204, summary="Remover executor (soft-delete)")
async def delete_agent(
    executor_id: str,
    force: bool = Query(False, description="Ver DELETE /executores/{id}."),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    ag=Depends(get_agent_or_404),
):
    """
    Soft-delete of a revoked executor.

    Fills deleted_at and hides the executor from listings.
    Only executors with status='revoked' can be removed.
    """
    _assert_can_manage_executor(current_user, ag)
    from app.services import workspace_executor_service as politica
    afetados = await politica.detach_executor(
        db, executor_id, force=force, actor_id=current_user.id_hash, reason="deleted",
    )
    try:
        await executor_service.delete_agent(db, executor_id)
    except ValueError:
        raise HTTPException(status_code=409, detail="Executor precisa estar revogado para ser removido.")
    executor_service.notify_owners_of_emptied_tiers(afetados, executor_name=getattr(ag, "name", "?"))

    logger.info("Usuário '%s' removeu executor '%s' (soft-delete).", current_user.username, executor_id)


# ── Assignment of executors to users (admin) ─────────────────────────────

@router.post("/set-default", summary="[Admin] Definir executor padrão da plataforma")
async def set_default(
    payload: SetDefaultRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    # Read BEFORE the promotion: it tells which main tiers will be emptied
    # (the promotion removes the executor from all tiers — Q3).
    from app.services import workspace_executor_service as politica
    afetados = await politica.workspaces_depending_on(db, payload.executor_id)
    try:
        ag = await user_executor_service.set_default_agent(
            db, payload.executor_id, force=payload.force, actor_id=current_user.id_hash,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="Não foi possível definir o executor padrão.")
    executor_service.notify_owners_of_emptied_tiers(afetados, executor_name=getattr(ag, "name", "?"))
    logger.info("Admin '%s' adicionou executor '%s' ao pool padrão.", current_user.username, payload.executor_id)
    return ExecutorOut.from_model(ag).model_dump()


@router.post("/unset-default", summary="[Admin] Remover executor do pool padrão")
async def unset_default(
    payload: SetDefaultRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    try:
        ag = await user_executor_service.unset_default_agent(db, payload.executor_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Não foi possível remover o executor do pool padrão.")
    logger.info("Admin '%s' removeu executor '%s' do pool padrão.", current_user.username, payload.executor_id)
    return ExecutorOut.from_model(ag).model_dump()


# ── Enrollment + Renewal + Revocation (mTLS) ──────────────────────────────────

@router.post("/{executor_id}/enroll-otp",
             response_model=EnrollmentOTPResponse,
             status_code=201,
             summary="[Admin] Gerar OTP de uso unico para enrollment de executor")
@limiter.limit("10/hour")
async def admin_create_enrollment_otp(
    request: Request,
    executor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    ag=Depends(get_agent_or_404),
):
    """
    Generates a 32-byte urlsafe OTP that the operator uses to
    enroll the executor. Expiration: 24h. Single use.

    Accessible to the global admin or to the executor's owner (created_by).

    The plaintext appears ONLY ONCE — store it in a secure channel
    (1Password, Signal). Afterwards only the HMAC stays in the DB.
    """
    _assert_can_manage_executor(current_user, ag)
    otp, expires_at = await executor_enrollment_service.create_enrollment_otp(
        db, executor_id, created_by=current_user.id_hash,
    )
    logger.info("Admin '%s' gerou OTP para executor '%s'.", current_user.username, executor_id)
    from app.core.config import AGENTS_URL, FRONTEND_URL
    return EnrollmentOTPResponse(
        otp=otp, expires_at=expires_at, executor_id=executor_id,
        server_url=AGENTS_URL, public_url=FRONTEND_URL.rstrip("/"),
    )


@router.post("/enroll",
             response_model=EnrollResponse,
             summary="[Executor] Trocar OTP por cert mTLS")
@limiter.limit("10/hour")
async def agent_enroll(
    request: Request,
    payload: EnrollRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    The only endpoint without mTLS. Accepts a Bearer OTP, validates the CSR, asks
    step-ca to sign it and returns cert + chain + CA.

    After the first successful call the OTP is marked as consumed and
    cannot be reused. On failure (invalid CSR, step-ca down),
    the OTP is NOT marked as consumed — the operator can try again.
    """
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer ausente.")
    otp = authorization[7:].strip()
    if not otp:
        raise HTTPException(status_code=401, detail="OTP ausente.")

    # Behind Traefik, `request.client.host` is the PROXY's IP for everyone —
    # the enrollment audit trail (`consumed_from_ip`) always recorded the
    # same address and was useless forensically. `get_client_ip` only accepts
    # X-Forwarded-For when the peer is a trusted proxy.
    from app.core.trusted_proxy import get_client_ip
    from_ip = get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
    )

    # Validations that do NOT consume the OTP — failing early avoids burning valid attempts.
    try:
        executor_enrollment_service.parse_and_validate_csr(payload.csr_pem)
    except ValueError as exc:
        logger.warning("CSR invalido no enrollment de %s: %s", from_ip, exc)
        raise HTTPException(status_code=400, detail=f"CSR invalido: {exc}")

    # The X25519 key is used to encrypt every job sent to this executor —
    # validating here avoids persisting a PEM that only breaks at dispatch.
    try:
        executor_enrollment_service.validate_x25519_public_key(payload.public_key_pem)
    except ValueError as exc:
        logger.warning("public_key_pem invalida no enrollment de %s: %s", from_ip, exc)
        raise HTTPException(status_code=400, detail=f"Chave publica invalida: {exc}")

    # Consumes the OTP (atomic) — past this point, a step-ca failure burns the attempt.
    try:
        executor_id = await executor_enrollment_service.consume_otp(db, otp, from_ip)
    except ValueError:
        raise HTTPException(status_code=401, detail="OTP invalido, expirado ou ja utilizado.")

    # Request a signature from the internal CA.
    try:
        cert_data = await executor_enrollment_service.sign_csr_via_stepca(payload.csr_pem, executor_id)
    except RuntimeError as exc:
        logger.error("Falha ao assinar CSR para executor '%s': %s", executor_id, exc)
        raise HTTPException(status_code=503, detail="CA interna indisponivel — tente novamente.")

    # Persists the cert metadata on the executor + the CSR's X25519 public key.
    await executor_enrollment_service.attach_cert_to_agent(db, executor_id, cert_data)
    await executor_enrollment_service.attach_public_key_to_agent(db, executor_id, payload.public_key_pem)

    logger.info("Executor '%s' enrolado com cert serial '%s'.", executor_id, cert_data["serial"])

    return EnrollResponse(
        cert_pem=cert_data["cert_pem"],
        chain_pem=cert_data["chain_pem"],
        ca_pem=cert_data["ca_pem"],
        serial=cert_data["serial"],
        fingerprint=cert_data["fingerprint"],
        issued_at=cert_data["issued_at"],
        expires_at=cert_data["expires_at"],
        server_signing_public_key=get_server_signing_public_key_b64(),
    )


def _executor_key_from_mtls(request: Request) -> str:
    """Rate-limit bucket per executor (the cert CN that Traefik forwards),
    not per IP: a fleet behind the same NAT, enrolled on the same day, renews
    on the same day. The limit is only checked after the route's dependencies, so
    it only counts requests that already passed mTLS. Without the header, it falls back to the IP."""
    cn, _ = _parse_traefik_client_cert(request.headers.get("x-forwarded-tls-client-cert-info", ""))
    return f"cert:{cn}" if cn else _client_key(request)


@router.post("/renew-cert",
             response_model=EnrollResponse,
             summary="[Executor] Renovar cert mTLS antes do vencimento")
# A legitimate executor renews every ~83 days and tries at most once per hour.
# Without a limit, an authenticated executor made step-ca sign nonstop, and each
# renewal leaves the previous serial in the Redis blacklist for up to 90 days.
@limiter.limit("6/hour;30/day", key_func=_executor_key_from_mtls)
async def agent_renew_cert(
    request: Request,
    payload: RenewRequest,
    db: AsyncSession = Depends(get_db),
    executor=Depends(get_agent_from_mtls),
):
    """
    Renews the cert using the current valid cert + a new CSR. Without mTLS returns 401.
    If the executor is revoked while step-ca is signing, the new cert is
    discarded and the response is 409.
    """
    try:
        executor_enrollment_service.parse_and_validate_csr(payload.csr_pem)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"CSR invalido: {exc}")

    try:
        cert_data = await executor_enrollment_service.sign_csr_via_stepca(payload.csr_pem, executor.id_hash)
    except RuntimeError as exc:
        logger.error("Falha ao renovar cert do executor '%s': %s", executor.id_hash, exc)
        raise HTTPException(status_code=503, detail="CA interna indisponivel.")

    # Before attaching the new cert, revoke the old serial in the Redis blacklist.
    # The TTL follows the cert's remaining validity (prevents a revoked cert from being
    # accepted after the TTL expires, until the cert expires naturally).
    if executor.cert_serial:
        await executor_enrollment_service.revoke_cert(
            executor.cert_serial, cert_expires_at=executor.cert_expires_at,
        )

    renovou = await executor_enrollment_service.renovar_cert_do_executor(
        db, executor.id_hash, executor.cert_serial, cert_data,
    )
    if not renovou:
        # Revoked (or renewed in parallel) while step-ca was signing. The
        # database stayed as the revocation left it; the newly issued cert must not
        # be valid. The blacklist is belt and suspenders: mTLS already rejects it,
        # because its serial is not the one in the database.
        try:
            await executor_enrollment_service.revoke_cert(
                cert_data["serial"], cert_expires_at=cert_data["expires_at"],
            )
        except Exception as exc:
            logger.warning("Falha ao anular o cert recem-emitido '%s': %s", cert_data["serial"], exc)
        logger.warning(
            "Renovacao do executor '%s' descartada: ele mudou durante a assinatura (revogado?).",
            executor.id_hash,
        )
        raise HTTPException(
            status_code=409,
            detail="O executor mudou durante a renovacao (revogado?). Cert novo descartado.",
        )
    logger.info("Executor '%s' renovou cert: serial novo '%s'.", executor.id_hash, cert_data["serial"])

    return EnrollResponse(
        cert_pem=cert_data["cert_pem"],
        chain_pem=cert_data["chain_pem"],
        ca_pem=cert_data["ca_pem"],
        serial=cert_data["serial"],
        fingerprint=cert_data["fingerprint"],
        issued_at=cert_data["issued_at"],
        expires_at=cert_data["expires_at"],
        server_signing_public_key=get_server_signing_public_key_b64(),
    )


@router.delete("/admin/executores/{executor_id}/cert", status_code=204,
               summary="[Admin] Revogar apenas o cert atual do executor")
async def admin_revoke_cert(
    executor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    ag=Depends(get_agent_or_404),
):
    """
    Revokes the current mTLS cert without changing the executor's status. Useful to force
    rotation without deactivating the executor. For full revocation, use DELETE /executores/{id}.
    """
    if not ag.cert_serial:
        raise HTTPException(status_code=404, detail="Executor sem cert ativo.")

    # Only the cert: status and policy tiers stay. The rest is that of every
    # revocation (`executor_service.complete_revocations`), after the commit:
    # blacklist, `control: revoked` and the 4403 close — which relays through Redis
    # when the WS is in another worker, and is what makes the executor stop. Without
    # the session's listener subscribed (Redis restarting), the session watchdog
    # drops it when it sees the cert voided in the database.
    revogacao = executor_service.Revocation(
        executor_id=executor_id, nome=ag.name, serial=ag.cert_serial,
        serial_expira_em=ag.cert_expires_at,
        aviso="Cert revogado pelo administrador.", fechamento="Cert revogado.",
    )
    ag.cert_serial = None
    await db.commit()
    await executor_service.complete_revocations([revogacao])

    logger.info(
        "Admin '%s' revogou cert serial '%s' do executor '%s'.",
        current_user.username, revogacao.serial, executor_id,
    )
