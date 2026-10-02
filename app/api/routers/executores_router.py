# app/api/routers/executores_router.py
"""
Endpoints REST para gerenciamento de Executores externos.

Fluxo de uso (mTLS + Bootstrap OTP):
  1. Admin   → POST /executores/                  → cria executor em status=pending
  2. Admin   → POST /executores/{id}/enroll-otp   → gera OTP de uso unico (24h)
  3. Operador entrega o OTP ao executor via canal seguro
  4. Executor   → POST /executores/enroll            → Bearer OTP + CSR, recebe cert mTLS
  5. Executor   → WS   /ws/executores/{id}           → conecta via mTLS (ver executor_ws_router.py)
  6. Executor   → POST /executores/renew-cert        → mTLS, renova cert antes do vencimento

Endpoints administrativos (requerem JWT de usuario com role=admin):
  GET    /executores/                          — lista executores
  DELETE /executores/{id}                      — revoga executor + cert
  DELETE /executores/{id}/permanent            — soft-delete (somente se status=revoked)
  DELETE /admin/executores/{id}/cert       — revoga apenas o cert atual
  POST   /executores/{id}/enroll-otp           — gera OTP para enrollment
  GET    /executores/server-public-key         — chave publica Ed25519 do servidor
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
    """Lança 403 se o usuário não for admin global nem dono (created_by) do executor."""
    if current_user.role != "admin" and ag.created_by != current_user.id_hash:
        raise HTTPException(status_code=403, detail="Acesso negado a este executor.")


def _assert_pode_gerenciar_executor(current_user, ag) -> None:
    """Como `_assert_executor_owner_or_admin`, mas para operações de GESTÃO
    (gerar OTP de enrollment, revogar): auditoria SEG-94.

    Um executor promovido ao pool padrão (`is_default`) atende TODOS os
    inquilinos. O dono original não pode mais gerar OTP nem revogá-lo — só um
    admin da plataforma. A LEITURA do próprio executor continua permitida ao
    dono (`_assert_executor_owner_or_admin`); só a gestão é restrita.
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
    """Autoriza a leitura de UM executor por mTLS do próprio executor ou por
    admin/dono.

    Estas rotas dependiam apenas de `agent_mtls_or_user_auth`, que só autentica —
    qualquer conta ativa lia o status e, pior, a lista de workspaces (id_hash +
    nome) de qualquer executor da plataforma, enquanto as rotas irmãs
    (`GET /executores/{id}` e `/{id}/users`) já exigiam admin.

    Função pura, testável sem subir a aplicação — mesmo padrão de
    `_assert_executor_owner_or_admin`.
    """
    if quem.is_executor:
        # Um executor só fala de si mesmo. Sem isto, um executor enrolado
        # (qualquer usuário pode criar um) enumeraria a frota inteira.
        if quem.executor.id_hash != ag.id_hash:
            raise HTTPException(status_code=403, detail="Acesso negado a este executor.")
        return
    _assert_executor_owner_or_admin(quem.user, ag)


# O estado AO VIVO de um executor — online, capacidade, desde quando está
# conectado — só existe inteiro no worker da API que segura o WebSocket dele.
# A tela lia `executor_registry.get(id)`, que é LOCAL: com `--workers 4`, 3 em
# cada 4 atualizações (a lista refaz a consulta a cada 15 s) mostravam um
# executor lotado como ocioso ("0/4") e um conectado há dias como "visto há 2
# dias". Aqui cada dado vem de onde todos os workers o enxergam — o Redis e o
# banco —, inclusive no worker do WebSocket: a memória dele tem valores alguns
# segundos mais novos, e misturá-los fazia a resposta mudar conforme o worker.

_CONTADORES_DA_CAPACIDADE = ("queued", "running", "max_concurrent", "max_queue")
_MEDIDAS_DA_CAPACIDADE = ("disk_free_gb", "ram_available_gb")


def _capacidade_para_a_tela(cap) -> dict | None:
    """A cópia do Redis revalidada no formato que o worker do WebSocket grava
    (`_sanitize_capacity`): só os campos do contrato, com o tipo certo. Este
    módulo não confia no que lê do Redis (o relay é assinado pelo mesmo motivo),
    e o valor vai para a tela de todo usuário. Contador inválido descarta a
    capacidade inteira; medida inválida vira None."""
    if not isinstance(cap, dict):
        return None
    erros: list[str] = []
    saida = {campo: _coerce_count(cap.get(campo), campo, erros) for campo in _CONTADORES_DA_CAPACIDADE}
    if erros:
        return None
    saida.update({campo: _coerce_gauge(cap.get(campo)) for campo in _MEDIDAS_DA_CAPACIDADE})
    return saida


async def _estado_ao_vivo(ids: list[str]) -> tuple[dict[str, bool], dict[str, dict | None]]:
    """(online por executor, capacidade dos online), do mesmo retrato do Redis
    em qualquer worker (ver `read_presence_and_capacities`), com a capacidade
    revalidada (`_capacidade_para_a_tela`)."""
    online, publicadas = await executor_registry.read_presence_and_capacities(ids)
    return online, {i: _capacidade_para_a_tela(cap) for i, cap in publicadas.items()}


def _conectado_desde(online: bool, last_seen_at) -> str | None:
    """Início da sessão WebSocket atual, em ISO com fuso. Offline não tem sessão.

    É o `last_seen_at` do banco: gravado no handshake de cada sessão e, no fim
    dela, só se o último contato for posterior (`registrar_fim_da_sessao`) — o
    fim de uma sessão substituída não apaga o início da nova. A renovação do
    cert não o toca. O `connected_at` da conexão diria o mesmo com milissegundos
    de diferença, mas só no worker do WebSocket."""
    if not online or not last_seen_at:
        return None
    if isinstance(last_seen_at, str):
        last_seen_at = datetime.fromisoformat(last_seen_at)
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)  # coluna em UTC sem fuso
    return last_seen_at.isoformat()


def _serialize_agent(ag, *, online: bool, capacidade: dict | None) -> dict:
    """Serializa executor com status online, capacidade ao vivo e system_info.

    `online` e `capacidade` vêm de `_estado_ao_vivo`, que lê de onde todos os
    workers enxergam (ver acima)."""
    data = {
        **ExecutorOut.from_model(ag).model_dump(),
        "online":       online,
        "capacity":     capacidade,
        "connected_at": _conectado_desde(online, ag.last_seen_at),
    }
    # Mescla o system_info estático (do banco, gravado no primeiro handshake da
    # conexão) com as métricas dinâmicas da capacidade.
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
    Cria um executor em status=pending.

    Admin global cria qualquer tipo (default/dedicated) sem restrição. Usuário
    comum cria apenas executores dedicados, limitado pela sua cota individual
    (User.agent_quota); o executor é vinculado automaticamente a ele.

    Para finalizar o enrollment, gere um OTP via
    POST /executores/{executor_id}/enroll-otp e entregue ao operador.
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
    """Lista completa de jobs em voo — inclui recentes (<15s) que ainda podem
    receber ACK. Útil para visão em tempo real do que o servidor despachou
    e ainda não foi confirmado pelo executor.
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
    """Retorna apenas jobs cujo ACK ultrapassou o limiar (default 15s).

    Útil para diagnóstico quando um workflow fica "running" sem progresso:
    permite ver se o job saiu do server mas nunca chegou ao executor (frame
    TCP perdido, executor crashou após receber, relay sem listener ativo).
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
    Retorna o root cert da CA interna (step-ca) em formato PEM.

    Endpoint publico — root cert e' info publica por design. Todo executor
    precisa dele para validar a chain TLS do host dos executores (assinada
    pela CA privada).

    Usado pelo script `install.sh` durante o onboarding: executor novo baixa
    o root daqui e adiciona ao trust store local antes do enroll.
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


_LINHA_PIN_CA = 'CA_SHA256_PIN="${ATLANS_CA_SHA256:-}"'


_RE_FINGERPRINT = "0123456789abcdef"


def _normalizar_fingerprint(bruto: str) -> str:
    """Hex minusculo, sem ':' nem espacos — o formato que o install.sh compara.

    `step certificate fingerprint` devolve hex puro e `openssl x509 -fingerprint`
    devolve com ':'. O operador cola o que tiver em maos.

    Aceita VARIOS fingerprints separados por virgula e devolve a lista
    normalizada, tambem separada por virgula. Sem isso, o valor de rotacao que a
    documentacao prescreve (`<fp_antigo>,<fp_novo>`) era rejeitado pela
    validacao de tamanho e o install.sh saia SEM pinning — TOFU puro exatamente
    na janela em que a CA esta trocando.
    """
    partes = [
        "".join(p.split()).replace(":", "").lower()
        for p in bruto.replace(";", ",").split(",")
    ]
    return ",".join(p for p in partes if p)


def _injetar_fingerprint_da_ca(script: str) -> str:
    """Publica STEPCA_ROOT_FINGERPRINT como default no install.sh servido.

    Sem isto, `STEPCA_ROOT_FINGERPRINT` era lida da config e nunca usada: o
    executor tem suporte a pinning (`ATLANS_CA_SHA256`, ver
    executor/_ca_bootstrap.py), mas o script era servido estatico e nunca o
    definia. O download do ca-bundle ficava sendo TOFU, enquanto docs/
    mtls-bootstrap.md afirmava que o backend usava o valor "ao montar o
    install.sh". Este e o codigo que torna aquela frase verdadeira.

    Config vazia devolve o script intacto — o cliente avisa e segue sem pinning,
    que e o comportamento anterior.
    """
    from app.core.config import STEPCA_ROOT_FINGERPRINT

    fp = _normalizar_fingerprint(STEPCA_ROOT_FINGERPRINT or "")
    if not fp:
        return script

    # Um valor que nao seja hex de 32 bytes nao e um fingerprint SHA-256; injeta-lo
    # so faria o instalador abortar com uma comparacao que nunca casa. Cada
    # fingerprint da lista e validado separadamente.
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

    if _LINHA_PIN_CA not in script:
        logger.error(
            "install.sh nao contem a linha de pinning esperada — servido sem "
            "fingerprint. Verifique static/install.sh.",
        )
        return script

    return script.replace(_LINHA_PIN_CA, f'CA_SHA256_PIN="${{ATLANS_CA_SHA256:-{fp}}}"', 1)


# Os enderecos que o install.sh servido traz como padrao. Uma linha de cada
# (`SERVER=""` etc., no inicio da linha) e substituida pelo valor desta
# instalacao; o arquivo no repositorio nao aponta para nenhuma.
_ENDERECO_SEGURO = re.compile(r"(?:https?|wss?)://[A-Za-z0-9.-]+(?::[0-9]{1,5})?(?:/[A-Za-z0-9._~/-]*)?")


def _injetar_enderecos(script: str) -> str:
    """Preenche SERVER, PUBLIC_SERVER e REPO_URL com a config deste servidor.

    So entra um valor que seja URL simples (esquema, host, porta e caminho, sem
    aspas, `$` nem espaco): ele vai dentro de aspas duplas num script que o
    operador roda com `bash`. Um valor fora disso, ou vazio, deixa a linha
    vazia, e o script pede a flag.
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
        if not _ENDERECO_SEGURO.fullmatch(valor):
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
    Retorna o script bash de instalacao do executor (self-contained).

    Uso pelo operador (o comando pronto sai da tela de matricula):
        curl -fsSL https://<site>/executores/install | bash -s -- \\
            --executor-id=<ID> --otp=<OTP>

    O script:
      1. Verifica docker + git
      2. Clona o repo (se ausente) em ~/atlans-executor
      3. Baixa root cert via /executores/ca-bundle
      4. Builda imagem + roda enroll + sobe service

    O script em si nao tem segredos; e' a mesma coisa que o operador
    montaria a mao seguindo o README. O fingerprint da CA injetado abaixo
    tambem nao e segredo — e o hash de um certificado publico, e serve para o
    cliente detectar que baixou a CA ERRADA.
    """
    from pathlib import Path
    script_path = Path(__file__).resolve().parent.parent.parent.parent / "static" / "install.sh"
    try:
        content = script_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="install.sh indisponivel no servidor.")

    content = _injetar_fingerprint_da_ca(content)
    content = _injetar_enderecos(content)

    return Response(
        content=content,
        media_type="text/x-shellscript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300"},
    )


# ── App desktop para Windows ─────────────────────────────────────────────────
#
# O instalador vive nos GitHub Releases (tag `desktop/v*`) do repositório em
# DESKTOP_RELEASES_REPO, publicados pelo workflow desktop-windows.yml. Estes dois
# endpoints existem para que o painel ofereça o download sem que o usuário
# precise saber onde procurar. Sem o repositório configurado, não há oferta.
#
# O binário NÃO é proxiado: são ~180 MB por download, e passá-los pelo backend
# consumiria worker e banda por nada. O redirect manda o navegador direto ao
# CDN do GitHub.

_DESKTOP_TAG_PREFIX = "desktop/v"
_DESKTOP_CACHE_TTL = 300  # segundos

# Cache em memória por worker. A consulta ao GitHub é lenta e tem rate limit de
# 60/h sem token — sem cache, um punhado de usuários abrindo o diálogo de OTP
# esgotaria a cota e o botão de download sumiria para todo mundo.
_desktop_cache: dict = {"em": 0.0, "dados": None}


async def _ultima_release_desktop() -> dict | None:
    """Metadados do instalador Windows mais recente, ou None se não houver.

    Nunca levanta: a ausência de release é estado normal (nenhuma publicada
    ainda), e uma falha de rede com o GitHub não pode derrubar a página de
    executores.
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
    """Versão, tamanho e URL do instalador — para a UI mostrar antes do clique."""
    dados = await _ultima_release_desktop()
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma versão do app desktop foi publicada ainda.",
        )
    return dados


@router.get("/install/windows", summary="Baixar o app desktop para Windows (publico)")
@limiter.limit("60/minute")
async def desktop_install(request: Request):
    """Redireciona para o instalador `.exe` da última release `desktop/v*`."""
    from fastapi.responses import RedirectResponse

    dados = await _ultima_release_desktop()
    if not dados or not dados.get("url"):
        raise HTTPException(
            status_code=404,
            detail="Nenhuma versão do app desktop foi publicada ainda.",
        )
    # 302 e não 301: a URL do asset muda a cada release, e um permanente ficaria
    # cravado no cache do navegador apontando para a versão antiga.
    return RedirectResponse(url=dados["url"], status_code=302)


@router.get("/my", summary="Listar executores acessíveis ao usuário autenticado")
async def my_agents(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retorna executores default + dedicated atribuídos via workspaces do usuário."""
    executores = await user_executor_service.get_user_accessible_agents(db, current_user.id_hash)
    online, capacidades = await _estado_ao_vivo([ag["id_hash"] for ag in executores])
    for ag in executores:
        ag["online"] = online[ag["id_hash"]]
        ag["capacity"] = capacidades.get(ag["id_hash"])
        ag["connected_at"] = _conectado_desde(ag["online"], ag.get("last_seen_at"))
    return executores


@router.get("/my/count", summary="Quantidade de executores acessíveis ao usuário")
async def my_agents_count(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Contagem leve (sem checagem de presença) — usada para decidir se a UI
    exibe o menu de executores ao usuário."""
    executores = await user_executor_service.get_user_accessible_agents(db, current_user.id_hash)
    return {"count": len(executores)}


@router.get("", summary="Listar todos os executores")
async def list_agents(
    executor_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Lista todos os executores."""
    executores = await executor_service.list_agents(db)
    filtered = [ag for ag in executores if not executor_type or ag.executor_type == executor_type]
    online, capacidades = await _estado_ao_vivo([ag.id_hash for ag in filtered])
    return [
        _serialize_agent(ag, online=online[ag.id_hash], capacidade=capacidades.get(ag.id_hash))
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

    # Resolver workspaces disponíveis para o executor (GeoSync)
    agent_workspaces = await _get_agent_workspaces(db, ag)
    resolved_ws_id = None
    if agent_workspaces:
        # Auto-seleciona: default primeiro, senão o primeiro da lista
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
    """Retorna workspaces acessíveis ao executor (via usuário atribuído).

    Auth: mTLS do próprio executor, ou JWT de admin/dono do executor.
    """
    _assert_pode_ler_executor(quem, ag)
    return await _get_agent_workspaces(db, ag)


async def _get_agent_workspaces(db: AsyncSession, ag) -> list[dict]:
    """
    Retorna workspaces disponíveis para o executor (usado pelo GeoSync para auto-detecção).

    Regras:
      - Executor default → [] (GeoSync desabilitado; escopo de todos os workspaces é amplo demais)
      - Executor dedicated com >1 workspace → [] (requer EXECUTOR_WORKSPACE_ID explícito)
      - Executor dedicated com 0 ou 1 workspace → retorna normalmente
    """
    if ag.is_default:
        return []

    # Ponteiro legado ∪ níveis da política: o GeoSync precisa do workspace
    # cujos jobs este executor de fato recebe.
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
    """Retorna usuários que têm este executor atribuído diretamente pelo admin."""
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
    """Atribui um executor dedicated diretamente a um usuário."""
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
    """Remove a atribuição direta de um executor a um usuário."""
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
    _assert_pode_gerenciar_executor(current_user, ag)
    # Política de execução (spec §4.4): um executor revogado some dos níveis; se
    # isso esvaziaria o nível principal de alguém, 409 — salvo `force`. Os
    # passos (níveis, status, cert, aviso aos donos, sessão derrubada) são os de
    # todo caminho que revoga — ver `executor_service.revogar_executor`.
    revogacao = await executor_service.revogar_executor(
        db, ag, force=force, actor_id=current_user.id_hash, motivo="revoked",
        aviso="Executor revogado pelo administrador.", fechamento="Executor revogado.",
    )
    await db.commit()
    await executor_service.concluir_revogacoes([revogacao])

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
    Soft-delete de um executor revogado.

    Preenche deleted_at e oculta o executor das listagens.
    Somente executores com status='revoked' podem ser removidos.
    """
    _assert_pode_gerenciar_executor(current_user, ag)
    from app.services import workspace_executor_service as politica
    afetados = await politica.detach_executor(
        db, executor_id, force=force, actor_id=current_user.id_hash, reason="deleted",
    )
    try:
        await executor_service.delete_agent(db, executor_id)
    except ValueError:
        raise HTTPException(status_code=409, detail="Executor precisa estar revogado para ser removido.")
    executor_service.avisar_donos_de_niveis_esvaziados(afetados, executor_name=getattr(ag, "name", "?"))

    logger.info("Usuário '%s' removeu executor '%s' (soft-delete).", current_user.username, executor_id)


# ── Atribuição de executores a usuários (admin) ──────────────────────────

@router.post("/set-default", summary="[Admin] Definir executor padrão da plataforma")
async def set_default(
    payload: SetDefaultRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    # Lido ANTES da promoção: é o que diz quais níveis principais vão esvaziar
    # (a promoção retira o executor de todos os níveis — Q3).
    from app.services import workspace_executor_service as politica
    afetados = await politica.workspaces_depending_on(db, payload.executor_id)
    try:
        ag = await user_executor_service.set_default_agent(
            db, payload.executor_id, force=payload.force, actor_id=current_user.id_hash,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="Não foi possível definir o executor padrão.")
    executor_service.avisar_donos_de_niveis_esvaziados(afetados, executor_name=getattr(ag, "name", "?"))
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


# ── Enrollment + Renewal + Revogacao (mTLS) ──────────────────────────────────

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
    Gera um OTP de 32 bytes urlsafe que o operador usa para fazer
    enrollment do executor. Expiracao: 24h. Uso unico.

    Acessível ao admin global ou ao dono do executor (created_by).

    O plaintext aparece UMA UNICA VEZ — armazene em canal seguro
    (1Password, Signal). Subsequentemente so o HMAC fica no DB.
    """
    _assert_pode_gerenciar_executor(current_user, ag)
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
    Unico endpoint sem mTLS. Aceita Bearer OTP, valida CSR, pede a step-ca
    para assinar e devolve cert + chain + CA.

    Apos a primeira chamada bem-sucedida o OTP e marcado como consumido e
    nao pode ser reutilizado. Em caso de falha (CSR invalido, step-ca down),
    o OTP NAO e marcado como consumido — operador pode tentar de novo.
    """
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer ausente.")
    otp = authorization[7:].strip()
    if not otp:
        raise HTTPException(status_code=401, detail="OTP ausente.")

    # Atras do Traefik, `request.client.host` e o IP do PROXY para todo mundo —
    # a trilha de auditoria do enrollment (`consumed_from_ip`) gravava sempre o
    # mesmo endereco e nao servia para nada forense. `get_client_ip` so aceita o
    # X-Forwarded-For quando o peer e um proxy confiavel.
    from app.core.trusted_proxy import get_client_ip
    from_ip = get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
    )

    # Validacoes que NAO consomem o OTP — falhar antes evita queimar tentativas validas.
    try:
        executor_enrollment_service.parse_and_validate_csr(payload.csr_pem)
    except ValueError as exc:
        logger.warning("CSR invalido no enrollment de %s: %s", from_ip, exc)
        raise HTTPException(status_code=400, detail=f"CSR invalido: {exc}")

    # A chave X25519 e usada para cifrar todo job enviado a este executor —
    # validar aqui evita persistir um PEM que so quebra no dispatch.
    try:
        executor_enrollment_service.validate_x25519_public_key(payload.public_key_pem)
    except ValueError as exc:
        logger.warning("public_key_pem invalida no enrollment de %s: %s", from_ip, exc)
        raise HTTPException(status_code=400, detail=f"Chave publica invalida: {exc}")

    # Consome OTP (atomico) — apos este ponto, falha do step-ca queima a tentativa.
    try:
        executor_id = await executor_enrollment_service.consume_otp(db, otp, from_ip)
    except ValueError:
        raise HTTPException(status_code=401, detail="OTP invalido, expirado ou ja utilizado.")

    # Pede assinatura na CA interna.
    try:
        cert_data = await executor_enrollment_service.sign_csr_via_stepca(payload.csr_pem, executor_id)
    except RuntimeError as exc:
        logger.error("Falha ao assinar CSR para executor '%s': %s", executor_id, exc)
        raise HTTPException(status_code=503, detail="CA interna indisponivel — tente novamente.")

    # Persiste metadata do cert no executor + chave publica X25519 do CSR.
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


def _chave_do_executor_no_mtls(request: Request) -> str:
    """Balde de rate limit por executor (o CN do cert que o Traefik repassa),
    nao por IP: uma frota atras do mesmo NAT, matriculada no mesmo dia, renova
    no mesmo dia. O limite so e conferido depois das dependencias da rota, entao
    so conta requests que ja passaram pelo mTLS. Sem o header, cai no IP."""
    cn, _ = _parse_traefik_client_cert(request.headers.get("x-forwarded-tls-client-cert-info", ""))
    return f"cert:{cn}" if cn else _client_key(request)


@router.post("/renew-cert",
             response_model=EnrollResponse,
             summary="[Executor] Renovar cert mTLS antes do vencimento")
# Um executor legitimo renova a cada ~83 dias e tenta no maximo 1x por hora.
# Sem limite, um executor autenticado fazia o step-ca assinar sem parar, e cada
# renovacao deixa o serial anterior na blacklist do Redis por ate 90 dias.
@limiter.limit("6/hour;30/day", key_func=_chave_do_executor_no_mtls)
async def agent_renew_cert(
    request: Request,
    payload: RenewRequest,
    db: AsyncSession = Depends(get_db),
    executor=Depends(get_agent_from_mtls),
):
    """
    Renova o cert usando o cert atual valido + novo CSR. Sem mTLS retorna 401.
    Se o executor for revogado enquanto o step-ca assina, o cert novo e
    descartado e a resposta e 409.
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

    # Antes de atachar o novo cert, revoga o serial antigo no Redis blacklist.
    # TTL acompanha a validade restante do cert (impede que cert revogado seja
    # aceito apos o TTL expirar, ate o cert expirar naturalmente).
    if executor.cert_serial:
        await executor_enrollment_service.revoke_cert(
            executor.cert_serial, cert_expires_at=executor.cert_expires_at,
        )

    renovou = await executor_enrollment_service.renovar_cert_do_executor(
        db, executor.id_hash, executor.cert_serial, cert_data,
    )
    if not renovou:
        # Revogado (ou renovado em paralelo) enquanto o step-ca assinava. O
        # banco ficou como a revogacao deixou; o cert recem-emitido nao pode
        # valer. A blacklist e cinto duplo: o mTLS ja o recusa, porque o serial
        # dele nao e o do banco.
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
    Revoga o cert mTLS atual sem alterar o status do executor. Util para forcar
    rotacao sem desativar o executor. Para revogacao completa, use DELETE /executores/{id}.
    """
    if not ag.cert_serial:
        raise HTTPException(status_code=404, detail="Executor sem cert ativo.")

    # So o cert: status e niveis da politica ficam. O resto e o de toda
    # revogacao (`executor_service.concluir_revogacoes`), depois do commit:
    # blacklist, `control: revoked` e o close 4403 — que faz relay pelo Redis
    # quando o WS esta em outro worker, e e o que faz o executor parar. Sem o
    # listener da sessao inscrito (Redis reiniciando), a vigia da sessao a
    # derruba ao ver o cert anulado no banco.
    revogacao = executor_service.Revogacao(
        executor_id=executor_id, nome=ag.name, serial=ag.cert_serial,
        serial_expira_em=ag.cert_expires_at,
        aviso="Cert revogado pelo administrador.", fechamento="Cert revogado.",
    )
    ag.cert_serial = None
    await db.commit()
    await executor_service.concluir_revogacoes([revogacao])

    logger.info(
        "Admin '%s' revogou cert serial '%s' do executor '%s'.",
        current_user.username, revogacao.serial, executor_id,
    )
