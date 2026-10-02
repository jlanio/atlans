# app/api/routers/internal_email_router.py
"""
Endpoint interno para envio de e-mail via Resend.
Autenticado via cert mTLS do executor (usado por executores executando workflows).
"""
from app.core.utils.logger import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import email_transporte
from app.api.dependencies import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


# ── Schemas ──────────────────────────────────────────────────────────────────

# Teto de destinatarios por chamada e de chamadas por executor/hora. O endpoint
# usa a conta Resend da plataforma e um dominio verificado: sem cota, qualquer
# executor enrolado (e QUALQUER usuario pode criar+enrolar um executor dedicado)
# vira um relay de spam/phishing com remetente legitimo.
_MAX_RECIPIENTS = 50
_MAX_EMAILS_PER_HOUR = 100

# Allowlist do corpo HTML. O que nao esta aqui e removido pelo nh3 — nao ha
# lista de "tags perigosas" a manter atualizada.
_TAGS_PERMITIDAS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "div", "em",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p",
    "pre", "small", "span", "strong", "sub", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "u", "ul",
}

# `style` fica de fora de proposito: e o vetor de exfiltracao por CSS
# (background-image: url(...)) e nao e necessario para o corpo de um e-mail
# transacional gerado por workflow.
_ATRIBUTOS_PERMITIDOS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan", "align"},
    "th": {"colspan", "rowspan", "align"},
    "table": {"width", "border", "cellpadding", "cellspacing"},
}

# Sem `data:` — data: URI em <img> serve para contrabandear SVG com script em
# clientes que renderizam. `mailto:` cobre o link de contato.
_PROTOCOLOS_PERMITIDOS = {"http", "https", "mailto"}


class SendEmailRequest(BaseModel):
    to: list[str]
    subject: str
    html: str
    # Ata o envio a uma execucao real (auditoria SEG-07). Opcionais no schema para
    # nao quebrar chamadas em voo durante o deploy; o handler recusa quando faltam.
    workspace_id: Optional[str] = None
    task_id: Optional[str] = None
    # SEG: `from_email` NAO e mais aceito do cliente. O remetente e sempre
    # EMAIL_FROM — deixar o executor escolher permitia forjar qualquer
    # endereco do dominio verificado da plataforma.

    @field_validator("html")
    @classmethod
    def sanitize_html(cls, v: str) -> str:
        """Reduz o HTML a uma allowlist de tags, atributos e protocolos.

        Antes eram quatro `re.sub` de blacklist em passada unica — e passada
        unica de remocao RECONSTROI o padrao a partir das bordas: a entrada
        `javjavascript:ascript:` saia como `javascript:` intacto, e
        `<scr<script>ipt>` remontava a tag. A mesma classe de bypass valia para
        `\\bon\\w+\\s*=`. Alem disso a lista nao cobria `<svg>`, `<math>`,
        `srcdoc` nem atributo `style`.

        O nh3 (ammonia, em Rust) faz o caminho oposto: parseia o HTML de verdade
        e mantem so o que esta na allowlist. O impacto que isso fecha nao e
        script em cliente de e-mail moderno — e phishing com HTML arbitrario
        saindo do dominio verificado da plataforma, com SPF e DKIM validos.
        """
        import nh3

        return nh3.clean(
            v,
            tags=_TAGS_PERMITIDAS,
            attributes=_ATRIBUTOS_PERMITIDOS,
            url_schemes=_PROTOCOLOS_PERMITIDOS,
            link_rel="noopener noreferrer",
        )

    @field_validator("html")
    @classmethod
    def validate_html_not_empty(cls, v: str) -> str:
        """Rejeita html vazio antes de chamar o Resend.

        Antes: html="" passava daqui, ia ao Resend, voltava com
        "Missing html or text field" e o except generico em send_email
        convertia em 502 — operador nao tinha pista da causa real.

        Roda DEPOIS de sanitize_html (ordem de declaracao no Pydantic v2)
        para cobrir tambem o caso de body que so tinha tags perigosas e
        ficou vazio apos sanitizacao.
        """
        if not v or not v.strip():
            raise ValueError("Campo 'html' não pode ser vazio.")
        return v

    @field_validator("to")
    @classmethod
    def validate_to(cls, v: list[str]) -> list[str]:
        cleaned = [addr.strip() for addr in v if addr.strip()]
        if not cleaned:
            raise ValueError("Lista de destinatários não pode ser vazia.")
        if len(cleaned) > _MAX_RECIPIENTS:
            raise ValueError(f"Máximo de {_MAX_RECIPIENTS} destinatários por envio.")
        # Um endereço por item: o teto acima conta itens, e um item com
        # vírgulas (ou um grupo `g: a@x, b@y;`) seria vários destinatários.
        for addr in cleaned:
            email_transporte.endereco(addr)
        return cleaned

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Assunto não pode ser vazio.")
        return v.strip()


class SendEmailResponse(BaseModel):
    sent: bool
    recipients: int
    # O id da mensagem no transporte (Resend ou SMTP). O nome e o do contrato
    # com o executor, de quando so havia a Resend.
    resend_id: Optional[str] = None


# ── Autenticação de Executor ────────────────────────────────────────────────────

async def _auth_agent(request: Request, db: AsyncSession):
    """Autentica executor via cert mTLS (validado por Traefik)."""
    from app.api.dependencies import get_agent_from_mtls
    return await get_agent_from_mtls(request, db)


async def _assert_envio_vinculado_a_run(db: AsyncSession, executor, workspace_id, task_id) -> None:
    """Recusa o envio que não corresponde a uma execução real (auditoria SEG-07).

    Exige que o executor atenda o `workspace_id` informado e que exista um
    `WorkflowRun` com esse `task_id` NESSE workspace. Assim o envio fica atado a
    uma execução legítima e auditável, e um executor não emite e-mail com o
    domínio da plataforma fora do contexto de um run de um workspace que serve.
    """
    if not workspace_id or not task_id:
        raise HTTPException(
            status_code=400,
            detail="Envio de e-mail exige workspace_id e task_id do run.",
        )
    from app.services.user_executor_service import get_agent_workspace_ids
    servidos = await get_agent_workspace_ids(db, executor.id_hash, executor.is_default)
    if workspace_id not in servidos:
        raise HTTPException(status_code=403, detail="Executor não atende este workspace.")

    from sqlalchemy import select
    from app.models.workflow_run import WorkflowRun
    existe = await db.execute(
        select(WorkflowRun.id).where(
            WorkflowRun.task_id == task_id,
            WorkflowRun.workspace_id == workspace_id,
        ).limit(1)
    )
    if existe.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Nenhuma execução corresponde a este envio.")


async def _enforce_agent_quota(executor_id: str) -> None:
    """Cota de envios por executor, numa janela fixa de 1 h. Fail-closed se o Redis cair."""
    from app.core.redis import contar_na_janela
    key = f"ratelimit:send_email:{executor_id}"
    try:
        count, _ = await contar_na_janela(key, 3600)
    except Exception as exc:
        logger.error("Cota de e-mail indisponível (Redis) para executor '%s': %s", executor_id, exc)
        raise HTTPException(status_code=503, detail="Serviço de e-mail temporariamente indisponível.")
    if count > _MAX_EMAILS_PER_HOUR:
        logger.warning("Executor '%s' excedeu a cota de %d e-mails/hora.", executor_id, _MAX_EMAILS_PER_HOUR)
        raise HTTPException(status_code=429, detail="Cota de envio de e-mail excedida para este executor.")


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/send-email", response_model=SendEmailResponse)
async def send_email(
    body: SendEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Envia e-mail pelo transporte configurado (Resend ou SMTP).
    Autenticado via cert mTLS do executor.
    """
    executor = await _auth_agent(request, db)

    if not email_transporte.ativo():
        raise HTTPException(
            status_code=503,
            detail="Nenhum transporte de e-mail configurado no servidor (EMAIL_BACKEND, RESEND_API_KEY ou SMTP_HOST).",
        )

    # Auditoria (SEG-07): o endpoint autentica o EXECUTOR, mas o pool atende
    # todos os inquilinos, então sem amarração qualquer conta transformava o
    # executor num relay de phishing com o domínio verificado da plataforma.
    # Exige uma execução REAL: o workspace precisa ser atendido pelo executor e
    # precisa existir um run com esse task_id nesse workspace. Sem isso não há
    # envio. (Política de destinatários/plano fica como follow-up do dono.)
    await _assert_envio_vinculado_a_run(db, executor, body.workspace_id, body.task_id)
    await _enforce_agent_quota(executor.id_hash)

    import asyncio

    transporte = email_transporte.backend()
    try:
        id_da_mensagem = await asyncio.to_thread(email_transporte.enviar, body.to, body.subject, body.html)
    except Exception as e:
        logger.error("Erro ao enviar e-mail (%s): %s", transporte, e)
        raise HTTPException(status_code=502, detail=f"Erro ao enviar o e-mail ({transporte}): {e}")

    logger.info(
        "E-mail enviado (%s) para %d destinatário(s) (id=%s, executor=%s)",
        transporte, len(body.to), id_da_mensagem, executor.id_hash,
    )
    return SendEmailResponse(
        sent=True,
        recipients=len(body.to),
        resend_id=id_da_mensagem,
    )
