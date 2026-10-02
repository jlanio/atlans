# app/services/email_service.py
"""
Serviço de envio de email do próprio servidor (verificação, senha, alertas).

O envio sai pelo transporte configurado (`email_transporte.py`: Resend, SMTP
ou log), em thread pool. Sem transporte (desenvolvimento), loga o conteúdo.
"""
import asyncio
import re
from app.core.utils.logger import get_logger

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.extensoes import registro
from app.services import email_transporte

logger = get_logger(__name__)

_template_env: Environment | None = None


def _ambiente() -> Environment:
    """Jinja2 — templates em app/templates/email/ e nas pastas das extensões
    (`Registro.templates`), nessa ordem. Montado no primeiro uso: as pastas das
    extensões só se conhecem depois do registro."""
    global _template_env
    if _template_env is None:
        pastas = ["app/templates/email", *(str(pasta) for pasta in registro().templates)]
        _template_env = Environment(
            loader=FileSystemLoader(pastas),
            autoescape=select_autoescape(["html"]),
        )
    return _template_env


_CHAVE_SENSIVEL = re.compile(r"token|url|link|senha|password|otp", re.IGNORECASE)


def _contexto_sem_segredos(context: dict) -> dict:
    """O contexto do e-mail como pode ir para o log: links, tokens e senhas
    viram «***» (o nome do campo fica, para se saber o que o e-mail levava)."""
    return {chave: ("***" if _CHAVE_SENSIVEL.search(str(chave)) else valor) for chave, valor in context.items()}


async def send_email(to: str, subject: str, template: str, context: dict) -> None:
    """Renderiza template Jinja2 e envia email (async via thread pool)."""
    html = _ambiente().get_template(template).render(**context)

    if not email_transporte.ativo():
        # Sem transporte, o e-mail inteiro ia para o log — com o link de
        # redefinição de senha e o token de verificação. Quem lê o log (um
        # agregador, um `docker logs` colado numa issue) tomaria qualquer
        # conta pedindo um reset. O WARNING mostra os campos com os links e
        # tokens mascarados; o contexto completo só sai em DEBUG (LOG_LEVEL),
        # que é o que o desenvolvimento local usa para clicar no link.
        logger.warning(
            "[EMAIL-DEV] Nenhum transporte de e-mail configurado. Email NÃO enviado.\n"
            "  Para: %s\n  Assunto: %s\n  Contexto: %s",
            to, subject, _contexto_sem_segredos(context),
        )
        logger.debug("[EMAIL-DEV] Contexto completo: %s", context)
        return

    await asyncio.to_thread(email_transporte.enviar, [to], subject, html)


def send_email_background(to: str, subject: str, template: str, context: dict) -> None:
    """Fire-and-forget: cria task asyncio para envio em background."""

    async def _task() -> None:
        try:
            await send_email(to, subject, template, context)
            logger.info("Email enviado para %s (template=%s)", to, template)
        except Exception:
            logger.exception("Falha ao enviar email para %s", to)

    asyncio.create_task(_task())
