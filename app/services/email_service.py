# app/services/email_service.py
"""
The server's own email sending service (verification, password, alerts).

Sending goes out through the configured transport (`email_transporte.py`: Resend,
SMTP or log), in a thread pool. With no transport (development), it logs the content.
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
    """Jinja2 — templates in app/templates/email/ and in the extensions' folders
    (`Registro.templates`), in that order. Built on first use: the extensions'
    folders are only known after registration."""
    global _template_env
    if _template_env is None:
        pastas = ["app/templates/email", *(str(pasta) for pasta in registro().templates)]
        _template_env = Environment(
            loader=FileSystemLoader(pastas),
            autoescape=select_autoescape(["html"]),
        )
    return _template_env


_SENSITIVE_KEY = re.compile(r"token|url|link|senha|password|otp", re.IGNORECASE)


def _context_without_secrets(context: dict) -> dict:
    """The email context as it can go to the log: links, tokens and passwords
    become "***" (the field name stays, so one knows what the email carried)."""
    return {chave: ("***" if _SENSITIVE_KEY.search(str(chave)) else valor) for chave, valor in context.items()}


async def send_email(to: str, subject: str, template: str, context: dict) -> None:
    """Renderiza template Jinja2 e envia email (async via thread pool)."""
    html = _ambiente().get_template(template).render(**context)

    if not email_transporte.ativo():
        # With no transport, the whole email went to the log — with the password
        # reset link and the verification token. Whoever reads the log (an
        # aggregator, a `docker logs` pasted into an issue) could take over any
        # account by requesting a reset. The WARNING shows the fields with the
        # links and tokens masked; the full context only goes out at DEBUG
        # (LOG_LEVEL), which is what local development uses to click the link.
        logger.warning(
            "[EMAIL-DEV] Nenhum transporte de e-mail configurado. Email NÃO enviado.\n"
            "  Para: %s\n  Assunto: %s\n  Contexto: %s",
            to, subject, _context_without_secrets(context),
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
